import cv2
import numpy as np
import subprocess
import os
import sys
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from adb import LOG_SUFFIX, get_log_dir, get_adb_logger, get_gui_logger, _FilterDisabled

# 导入加速模块
try:
    from image_accelerator import (
        parse_raw_screencap_to_gray,
        parse_raw_screencap,
        bgr_to_gray,
        match_template as numba_match_template,
        decode_jpeg,
        decode_jpeg_to_gray,
        get_acceleration_status,
        HAS_NUMBA,
        HAS_TURBOJPEG,
    )
except ImportError:
    HAS_NUMBA = False
    HAS_TURBOJPEG = False
    parse_raw_screencap_to_gray = None
    parse_raw_screencap = None
    bgr_to_gray = None
    numba_match_template = None
    decode_jpeg = None
    decode_jpeg_to_gray = None

    def get_acceleration_status():
        return {'numba': False, 'turbojpeg': False}

def get_image_logger():
    """获取识图日志记录器，只写入本地文件，不输出到终端"""
    logger = logging.getLogger("image")
    logger.setLevel(logging.INFO)
    # 防止重复添加handler导致日志重复写入
    if not logger.handlers:
        log_file = os.path.join(get_log_dir(), f"image_{LOG_SUFFIX}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        file_handler.addFilter(_FilterDisabled())
        logger.addHandler(file_handler)
    logger.propagate = False
    return logger

class ImageRecognizer:
    def __init__(self):
        self.adb_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "platform-tools", "adb.exe")
        if not os.path.exists(self.adb_path):
            self.adb_path = "adb"

        self.device = "127.0.0.1:16384"
        self.png_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "png")
        self.folder = None  # 用于临时切换识别文件夹
        self.threshold = 0.90
        self.running = True
        self.click_x = 785
        self.click_y = 672
        self.tiaozhan_count = 0
        self.stop_reason = ""  # 停止原因: "count"=次数达成, "anomaly"=连续点击异常, "image"=识别到特定图片
        self.template_filter = None
        self.skip_sleep = False
        self.pg0_threshold = 0.99
        self.q0_threshold = 0.99
        
        # 加速配置
        self.use_raw_screencap = True    # 使用 raw 截图（跳过 PNG 编解码，~2-3x 加速）
        self.use_numba_gray = HAS_NUMBA  # 使用 Numba 加速灰度转换
        self.use_numba_match = False     # 使用 Numba 加速模板匹配（小模板时可能有用，大模板 OpenCV 的 FFT 更快）

        # 详细日志开关：记录每个模板的匹配详情和性能统计
        self.log_detail = True

        # 模板匹配并行线程数（OpenCV matchTemplate 释放 GIL，多线程加速明显）
        self.match_workers = min(8, max(1, (os.cpu_count() or 1)))

        # 性能统计记录（供 run_once 汇总日志使用）
        self._last_screenshot_mode = "unknown"  # 截图方式: raw / png / raw(失败) 等
        self._last_screenshot_bytes = 0         # 截图数据字节数
        self._last_screenshot_time = 0.0        # 截图耗时 ms
        self._last_gray_time = 0.0              # 灰度转换耗时 ms
        self._last_match_time = 0.0             # 模板匹配总耗时 ms
        self._last_matches_detail = []          # 每个模板的匹配详情 [(name, confidence, hit)]

        # 缓存优化：缓存已加载的模板图像
        self._template_cache = {}

        self.logger = get_adb_logger()
        self.image_logger = get_image_logger()
        self.gui_logger = get_gui_logger()

        # 输出加速状态（记录到 image 日志和 GUI 日志）
        accel = get_acceleration_status()
        self.image_logger.info(
            f"加速模块状态: Numba={'可用' if accel['numba'] else '不可用'}, "
            f"PyTurboJPEG={'可用' if accel['turbojpeg'] else '不可用'}"
        )
        self.image_logger.info(
            f"加速配置: raw截图={'开启' if self.use_raw_screencap else '关闭'}, "
            f"Numba灰度={'开启' if self.use_numba_gray else '关闭'}, "
            f"Numba匹配={'开启' if self.use_numba_match else '关闭'}, 阈值={self.threshold}"
        )
        if accel['numba']:
            self.gui_logger.info(f"加速模块已加载: Numba JIT + {'PyTurboJPEG' if accel['turbojpeg'] else ''}")
        elif accel['turbojpeg']:
            self.gui_logger.info(f"加速模块已加载: PyTurboJPEG")

    def connect_device(self):
        try:
            cmd = [self.adb_path, "connect", self.device]
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            success = result.returncode == 0
            # 尝试使用UTF-8解码，如果失败则使用GBK，最终用replace处理无法解码的字符
            try:
                message = result.stdout.decode('utf-8').strip()
            except:
                try:
                    message = result.stdout.decode('gbk').strip()
                except:
                    message = result.stdout.decode('utf-8', errors='replace').strip()
            self.logger.info(f"命令: {' '.join(cmd)} | 返回: {message}")
            return success, message
        except Exception as e:
            self.logger.error(f"命令: {' '.join(cmd)} | 异常: {e}")
            return False, str(e)

    def get_screenshot(self):
        """获取截图。优先使用 raw 格式（快速），失败时 fallback 到 PNG"""
        if self.use_raw_screencap and parse_raw_screencap is not None:
            result = self._get_screenshot_raw()
            if result is not None:
                return result
            self.logger.info("raw 截图失败，fallback 到 PNG 截图")
        return self._get_screenshot_png()

    def _get_screenshot_raw(self):
        """使用 adb exec-out screencap 获取 raw RGBA 截图。
        跳过 PNG 编解码，比 PNG 方式快 2-3 倍。"""
        try:
            cmd = [self.adb_path, "-s", self.device, "exec-out", "screencap"]
            result = subprocess.run(cmd, capture_output=True, timeout=5)

            if result.returncode != 0 or len(result.stdout) < 12:
                return None

            self.logger.info(f"命令: {' '.join(cmd)} | 返回码: {result.returncode} | 数据长度: {len(result.stdout)}字节 (raw)")

            image = parse_raw_screencap(result.stdout)
            return image
        except Exception as e:
            self.logger.error(f"raw 截图异常: {e}")
            return None

    def get_screenshot_gray(self):
        """获取截图并直接返回灰度图（最快路径：raw → 灰度，跳过 BGR）。
        同时记录截图耗时、灰度转换耗时、截图模式，供 run_once 汇总日志。"""
        t_start = time.perf_counter()

        if self.use_raw_screencap and parse_raw_screencap_to_gray is not None:
            try:
                cmd = [self.adb_path, "-s", self.device, "exec-out", "screencap"]
                result = subprocess.run(cmd, capture_output=True, timeout=5)

                if result.returncode != 0 or len(result.stdout) < 12:
                    self._last_screenshot_mode = "raw(失败)"
                    self.image_logger.info("raw 截图失败，fallback 到 PNG 截图")
                else:
                    self.logger.info(f"命令: {' '.join(cmd)} | 返回码: {result.returncode} | 数据长度: {len(result.stdout)}字节 (raw->gray)")

                    self._last_screenshot_mode = "raw"
                    self._last_screenshot_bytes = len(result.stdout)

                    t_gray = time.perf_counter()
                    gray = parse_raw_screencap_to_gray(result.stdout)
                    self._last_gray_time = (time.perf_counter() - t_gray) * 1000

                    if gray is not None:
                        self._last_screenshot_time = (time.perf_counter() - t_start) * 1000
                        return gray
                    self._last_screenshot_mode = "raw(解析失败)"
            except Exception as e:
                self.logger.error(f"raw 截图灰度转换异常: {e}")
                self._last_screenshot_mode = "raw(异常)"

        # fallback：PNG 截图 + 灰度转换
        screenshot = self._get_screenshot_png()
        if screenshot is None:
            return None
        self._last_screenshot_mode = "png"
        t_gray = time.perf_counter()
        gray = self._cvt_to_gray(screenshot)
        self._last_gray_time = (time.perf_counter() - t_gray) * 1000
        self._last_screenshot_time = (time.perf_counter() - t_start) * 1000
        return gray

    def _cvt_to_gray(self, bgr_image):
        """BGR 转灰度，优先使用 Numba 加速"""
        if self.use_numba_gray and bgr_to_gray is not None:
            return bgr_to_gray(bgr_image)
        return cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)

    def _get_screenshot_png(self):
        """原有的 PNG 截图方法（fallback）"""
        try:
            cmd = [self.adb_path, "-s", self.device, "shell", "screencap", "-p"]
            result = subprocess.run(cmd, capture_output=True)
            self.logger.info(f"命令: {' '.join(cmd)} | 返回码: {result.returncode} | 数据长度: {len(result.stdout)}字节")

            if result.returncode != 0:
                return None

            screenshot_data = result.stdout.replace(b'\r\n', b'\n')

            nparr = np.frombuffer(screenshot_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            return image
        except Exception as e:
            self.logger.error(f"命令: {' '.join(cmd)} | 异常: {e}")
            print(f"获取ADB截图失败: {e}")
            return None

    def click(self, x, y):
        try:
            cmd = [self.adb_path, "-s", self.device, "shell", "input", "tap", str(x), str(y)]
            result = subprocess.run(cmd, capture_output=True, timeout=5)
            self.logger.info(f"命令: {' '.join(cmd)} | 返回码: {result.returncode}")
            self.gui_logger.info(f"发送点击指令: tap ({x}, {y}) | 设备: {self.device}")
            return True
        except Exception as e:
            self.logger.error(f"命令: {' '.join(cmd)} | 异常: {e}")
            self.gui_logger.error(f"点击指令失败: tap ({x}, {y}) | 异常: {e}")
            return False

    def _get_cached_template(self, template_path):
        """获取缓存的模板，如果不存在则加载并缓存"""
        if template_path in self._template_cache:
            return self._template_cache[template_path]
        
        # 加载模板
        template = cv2.imread(template_path)
        if template is None:
            self.image_logger.info(f"模板加载失败: {os.path.basename(template_path)}")
            return None
        
        # 预转换为灰度图，避免每次都转换
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        w, h = template_gray.shape[::-1]
        
        # 缓存结果
        self._template_cache[template_path] = (template_gray, w, h)
        self.image_logger.info(f"模板加载: {os.path.basename(template_path)} ({w}x{h})")
        return (template_gray, w, h)
    
    def find_template(self, screenshot, template_path, template_name=None):
        # 使用缓存的模板
        cached = self._get_cached_template(template_path)
        if cached is None:
            return None
        
        template_gray, w, h = cached
        
        if screenshot is None:
            return None
        
        # 使用加速版灰度转换
        screenshot_gray = self._cvt_to_gray(screenshot)
        
        result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        # pg0和0q使用单独的高阈值
        use_threshold = self.threshold
        if template_name:
            if 'pg0' in template_name.lower():
                use_threshold = self.pg0_threshold
            elif '0q' in template_name.lower():
                use_threshold = self.q0_threshold
        
        if max_val >= use_threshold:
            top_left = max_loc
            center_x = top_left[0] + w // 2
            center_y = top_left[1] + h // 2
            return (center_x, center_y), top_left, (w, h), max_val
        else:
            return None

    def get_all_templates(self):
        templates = []
        
        # 使用folder如果设置了，否则使用png_folder
        current_folder = self.folder if self.folder else self.png_folder

        for filename in os.listdir(current_folder):
            if filename.lower().endswith('.png'):
                if self.template_filter and self.template_filter not in filename.lower():
                    continue
                template_path = os.path.join(current_folder, filename)
                templates.append({
                    'name': filename,
                    'path': template_path
                })

        # 如果没有设置folder，才添加主png文件夹的内容
        if not self.folder:
            main_png_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "png")
            if self.png_folder != main_png_folder:
                for filename in os.listdir(main_png_folder):
                    if filename.lower().endswith('.png'):
                        if self.template_filter and self.template_filter not in filename.lower():
                            continue
                        template_path = os.path.join(main_png_folder, filename)
                        if not any(t['path'] == template_path for t in templates):
                            templates.append({
                                'name': filename,
                                'path': template_path
                            })

        return templates

    def stop(self):
        self.running = False
        print("\n正在停止...")

    def _match_template_worker(self, tmpl, screenshot_gray):
        """单模板匹配（线程安全，不修改 self 状态，供 run_once 并行调用）。
        返回: (tmpl, result_or_None, detail_or_None)
        detail = (name, max_val, hit) 用于汇总日志"""
        cached = self._get_cached_template(tmpl['path'])
        if cached is None:
            return tmpl, None, None
        
        template_gray, w, h = cached
        template_name = tmpl['name']
        
        # pg0和0q使用单独的高阈值
        use_threshold = self.threshold
        if template_name:
            if 'pg0' in template_name.lower():
                use_threshold = self.pg0_threshold
            elif '0q' in template_name.lower():
                use_threshold = self.q0_threshold

        if self.use_numba_match and numba_match_template is not None:
            # Numba 加速的模板匹配
            max_val, loc_y, loc_x = numba_match_template(screenshot_gray, template_gray)
        else:
            # OpenCV 模板匹配（默认，使用了 FFT 加速）
            result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            loc_x, loc_y = max_loc

        detail = (template_name, max_val, max_val >= use_threshold)

        if max_val >= use_threshold:
            center_x = loc_x + w // 2
            center_y = loc_y + h // 2
            return tmpl, {
                'name': template_name,
                'center': (center_x, center_y),
                'confidence': max_val
            }, detail
        return tmpl, None, detail
    
    def run_once(self):
        # 重置上一轮的匹配详情
        self._last_matches_detail = []
        t_total_start = time.perf_counter()

        # 使用最快路径：raw 截图 → 灰度（跳过 BGR 和 PNG 编解码）
        screenshot_gray = self.get_screenshot_gray()
        if screenshot_gray is None:
            self.image_logger.info("截图获取失败，本次识别跳过")
            return None
        
        templates = self.get_all_templates()

        # 预热模板缓存（串行加载，避免多线程首次重复加载；已缓存时开销极小）
        for tmpl in templates:
            self._get_cached_template(tmpl['path'])

        # 模板匹配（多线程并行，OpenCV matchTemplate 释放 GIL）
        t_match_start = time.perf_counter()
        results = []
        workers = max(1, min(self.match_workers, len(templates)))
        if workers > 1:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                # executor.map 保持结果顺序与模板顺序一致
                for tmpl, result, detail in executor.map(
                        lambda t: self._match_template_worker(t, screenshot_gray), templates):
                    if detail:
                        self._last_matches_detail.append(detail)
                    if result:
                        results.append(result)
        else:
            for tmpl in templates:
                tmpl, result, detail = self._match_template_worker(tmpl, screenshot_gray)
                if detail:
                    self._last_matches_detail.append(detail)
                if result:
                    results.append(result)
        self._last_match_time = (time.perf_counter() - t_match_start) * 1000
        total_time = (time.perf_counter() - t_total_start) * 1000

        # 记录性能统计日志
        h, w = screenshot_gray.shape[:2]
        gray_mode = "numba" if (self.use_numba_gray and bgr_to_gray is not None) else "cv2"
        if self._last_screenshot_mode == "raw":
            gray_mode = "cv2(raw)"
        self.image_logger.info(
            f"性能: 截图方式={self._last_screenshot_mode}({self._last_screenshot_bytes}字节), "
            f"截图={self._last_screenshot_time:.1f}ms, 灰度({gray_mode})={self._last_gray_time:.1f}ms, "
            f"匹配={self._last_match_time:.1f}ms, 总耗时={total_time:.1f}ms, "
            f"分辨率={w}x{h}, 模板数={len(templates)}"
        )

        # 记录每个模板的匹配详情（含未命中的置信度）
        if self.log_detail and self._last_matches_detail:
            detail_parts = [
                f"{name}={val:.3f}{'[命中]' if hit else ''}"
                for name, val, hit in self._last_matches_detail
            ]
            self.image_logger.info(f"模板匹配详情: {'; '.join(detail_parts)}")

        # 记录本次识别到的所有图片及坐标等数值
        if results:
            detail = "; ".join(
                f"{r['name']}(中心:{r['center']}, 置信度:{r['confidence']:.4f})"
                for r in results
            )
            self.image_logger.info(f"识别到 {len(results)} 项: {detail}")
            # GUI日志记录识别分析
            names = [r['name'].replace('.png', '') for r in results]
            self.gui_logger.info(f"识别到 {len(results)} 项图片: {', '.join(names)} | 设备: {self.device}")
        else:
            self.image_logger.info("未识别到任何图片")
            self.gui_logger.info(f"未识别到任何图片 | 设备: {self.device}")

        return results
