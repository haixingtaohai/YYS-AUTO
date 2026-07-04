import cv2
import numpy as np
import subprocess
import os
import sys
import time
import logging
from adb import LOG_SUFFIX, get_log_dir, get_adb_logger, _FilterDisabled

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
        self.template_filter = None
        self.skip_sleep = False
        self.pg0_threshold = 0.99
        self.q0_threshold = 0.99
        
        # 缓存优化：缓存已加载的模板图像
        self._template_cache = {}

        self.logger = get_adb_logger()
        self.image_logger = get_image_logger()

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
            return True
        except Exception as e:
            self.logger.error(f"命令: {' '.join(cmd)} | 异常: {e}")
            return False

    def _get_cached_template(self, template_path):
        """获取缓存的模板，如果不存在则加载并缓存"""
        if template_path in self._template_cache:
            return self._template_cache[template_path]
        
        # 加载模板
        template = cv2.imread(template_path)
        if template is None:
            return None
        
        # 预转换为灰度图，避免每次都转换
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        w, h = template_gray.shape[::-1]
        
        # 缓存结果
        self._template_cache[template_path] = (template_gray, w, h)
        return (template_gray, w, h)
    
    def find_template(self, screenshot, template_path, template_name=None):
        # 使用缓存的模板
        cached = self._get_cached_template(template_path)
        if cached is None:
            return None
        
        template_gray, w, h = cached
        
        if screenshot is None:
            return None
        
        # 只转换一次截图为灰度图
        screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        
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

    def _find_template_with_gray(self, screenshot_gray, template_path, template_name=None):
        """使用已转换的灰度图进行匹配，避免重复转换"""
        cached = self._get_cached_template(template_path)
        if cached is None:
            return None
        
        template_gray, w, h = cached
        
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
    
    def run_once(self):
        screenshot = self.get_screenshot()
        if screenshot is None:
            return None

        # 只转换一次截图为灰度图
        screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        
        templates = self.get_all_templates()

        results = []
        for tmpl in templates:
            result = self._find_template_with_gray(screenshot_gray, tmpl['path'], tmpl['name'])
            if result:
                center, top_left, (w, h), confidence = result
                results.append({
                    'name': tmpl['name'],
                    'center': center,
                    'confidence': confidence
                })

        # 记录本次识别到的所有图片及坐标等数值
        if results:
            detail = "; ".join(
                f"{r['name']}(中心:{r['center']}, 置信度:{r['confidence']:.4f})"
                for r in results
            )
            self.image_logger.info(f"识别到 {len(results)} 项: {detail}")
        else:
            self.image_logger.info("未识别到任何图片")

        return results
