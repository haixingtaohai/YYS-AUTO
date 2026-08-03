"""
图像识别加速模块
使用 Numba JIT 加速灰度转换和模板匹配，PyTurboJPEG 加速 JPEG 解码
"""
import numpy as np

# ============================================================
# Numba 加速（可选依赖）
# ============================================================
try:
    from numba import jit, prange
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False

    # 如果 Numba 未安装，提供一个空的装饰器
    def jit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

    def prange(n):
        return range(n)


# ============================================================
# PyTurboJPEG 加速（可选依赖）
# ============================================================
try:
    from turbojpeg import TurboJPEG
    try:
        _turbojpeg = TurboJPEG()
        HAS_TURBOJPEG = True
    except RuntimeError:
        # turbojpeg DLL 未找到（Windows 常见），优雅降级
        _turbojpeg = None
        HAS_TURBOJPEG = False
except ImportError:
    _turbojpeg = None
    HAS_TURBOJPEG = False


# ============================================================
# Raw 截图解析
# ============================================================

def parse_raw_screencap(data: bytes):
    """
    解析 adb exec-out screencap 返回的 raw RGBA 数据。
    
    数据格式：
    - 4 bytes: width  (little-endian uint32)
    - 4 bytes: height (little-endian uint32)
    - 4 bytes: pixel_format (little-endian uint32)
    - width*height*4 bytes: RGBA_8888 像素数据
    
    返回: (image_bgr, width, height)
    image_bgr 是 uint8 numpy 数组，shape=(height, width, 3)，BGR 顺序（兼容 OpenCV）
    """
    if len(data) < 12:
        return None

    import struct
    width = struct.unpack_from('<I', data, 0)[0]
    height = struct.unpack_from('<I', data, 4)[0]
    pixel_format = struct.unpack_from('<I', data, 8)[0]

    expected_size = 12 + width * height * 4
    if len(data) < expected_size:
        return None

    # 提取像素数据并 reshape 为 RGBA
    pixels = np.frombuffer(data, dtype=np.uint8, offset=12, count=width * height * 4)
    rgba = pixels.reshape((height, width, 4))

    # RGBA → BGR: 取 RGB 通道并重排为 BGR（OpenCV 格式）
    bgr = rgba[:, :, :3][:, :, ::-1].copy()
    return bgr


# ============================================================
# Raw 截图 → 灰度（一步到位，跳过 BGR 中间步骤）
# ============================================================

def parse_raw_screencap_to_gray(data: bytes):
    """
    从 raw 截图数据直接生成灰度图，跳过 BGR 中间步骤。
    使用 cv2.cvtColor(RGBA2GRAY) 一步到位（实测稳定 ~1ms，
    比 Numba 并行版更稳定——Numba 线程调度开销会导致 0.2~25ms 波动）。
    
    返回: numpy 灰度图像数组 (H, W) uint8，失败返回 None
    """
    if len(data) < 12:
        return None

    import struct
    width = struct.unpack_from('<I', data, 0)[0]
    height = struct.unpack_from('<I', data, 4)[0]

    expected_size = 12 + width * height * 4
    if len(data) < expected_size:
        return None

    import cv2
    rgba = np.frombuffer(data, dtype=np.uint8, offset=12, count=width * height * 4).reshape((height, width, 4))
    return cv2.cvtColor(rgba, cv2.COLOR_RGBA2GRAY)


# ============================================================
# Numba JIT 加速：RGBA → Gray 转换
# ============================================================

@jit(nopython=True, cache=True, parallel=True)
def _rgba_to_gray_numba(rgba_image, gray_image, height, width):
    """
    Numba JIT 加速的 RGBA→Gray 转换（并行版）。
    使用加权法：Gray = 0.299*R + 0.587*G + 0.114*B
    """
    for y in prange(height):
        for x in range(width):
            r = rgba_image[y, x, 0]
            g = rgba_image[y, x, 1]
            b = rgba_image[y, x, 2]
            gray_image[y, x] = np.uint8(0.299 * r + 0.587 * g + 0.114 * b)


def rgba_to_gray(rgba_image: np.ndarray) -> np.ndarray:
    """
    将 RGBA uint8 numpy 数组转为灰度图。
    rgba_image: shape=(H, W, 4)
    返回: shape=(H, W) uint8
    """
    if not HAS_NUMBA:
        r, g, b = rgba_image[:, :, 0], rgba_image[:, :, 1], rgba_image[:, :, 2]
        return (0.299 * r + 0.587 * g + 0.114 * b).astype(np.uint8)

    height, width = rgba_image.shape[:2]
    gray = np.empty((height, width), dtype=np.uint8)
    _rgba_to_gray_numba(rgba_image, gray, height, width)
    return gray


# ============================================================
# Numba JIT 加速：BGR → Gray 转换
# ============================================================

@jit(nopython=True, cache=True)
def _bgr_to_gray_numba(bgr_pixels, gray_pixels, height, width):
    """
    Numba JIT 加速的 BGR→Gray 转换。
    OpenCV 使用：Gray = 0.114*B + 0.587*G + 0.299*R
    BGR 顺序下: idx+0=B, idx+1=G, idx+2=R
    """
    for y in range(height):
        for x in range(width):
            idx = (y * width + x) * 3
            b = bgr_pixels[idx]
            g = bgr_pixels[idx + 1]
            r = bgr_pixels[idx + 2]
            gray_pixels[y, x] = np.uint8(0.114 * b + 0.587 * g + 0.299 * r)


def bgr_to_gray(bgr_image: np.ndarray) -> np.ndarray:
    """
    将 BGR uint8 numpy 数组转为灰度图。
    比 cv2.cvtColor(..., COLOR_BGR2GRAY) 的 Numba 替代版本。
    """
    if not HAS_NUMBA:
        import cv2
        return cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)

    height, width = bgr_image.shape[:2]
    bgr_flat = bgr_image.ravel()
    gray = np.empty((height, width), dtype=np.uint8)
    _bgr_to_gray_numba(bgr_flat, gray, height, width)
    return gray


# ============================================================
# Numba JIT 加速：归一化互相关模板匹配 (TM_CCOEFF_NORMED)
# ============================================================

@jit(nopython=True, cache=True)
def _match_template_numba(image_gray, template_gray, img_h, img_w, tpl_h, tpl_w):
    """
    Numba JIT 加速的归一化互相关模板匹配。
    
    实现 TM_CCOEFF_NORMED:
    R(x,y) = Σ(T' * I'(x,y)) / sqrt(ΣT'² * ΣI'(x,y)²)
    其中 T' = T - mean(T), I' = I - mean(I)
    
    返回: (max_val, max_loc_y, max_loc_x)
    """
    # 预计算模板的均值和去均值模板
    tpl_mean = 0.0
    for y in range(tpl_h):
        for x in range(tpl_w):
            tpl_mean += template_gray[y, x]
    tpl_mean /= (tpl_h * tpl_w)

    # 模板去均值
    tpl_demean = np.empty((tpl_h, tpl_w), dtype=np.float64)
    tpl_sqsum = 0.0
    for y in range(tpl_h):
        for x in range(tpl_w):
            val = float(template_gray[y, x]) - tpl_mean
            tpl_demean[y, x] = val
            tpl_sqsum += val * val

    # 如果模板是均匀的（方差为零），避免除以零
    if tpl_sqsum < 1e-10:
        return 0.0, 0, 0

    tpl_denom_inv = 1.0 / np.sqrt(tpl_sqsum)

    max_val = -1.0
    max_loc_y = 0
    max_loc_x = 0

    result_h = img_h - tpl_h + 1
    result_w = img_w - tpl_w + 1

    for y in range(result_h):
        for x in range(result_w):
            # 计算图像窗口的均值
            win_sum = 0.0
            for ty in range(tpl_h):
                for tx in range(tpl_w):
                    win_sum += image_gray[y + ty, x + tx]
            win_mean = win_sum / (tpl_h * tpl_w)

            # 计算分子和分母
            numerator = 0.0
            win_sqsum = 0.0
            for ty in range(tpl_h):
                for tx in range(tpl_w):
                    i_val = float(image_gray[y + ty, x + tx]) - win_mean
                    t_val = tpl_demean[ty, tx]
                    numerator += t_val * i_val
                    win_sqsum += i_val * i_val

            if win_sqsum < 1e-10:
                val = 0.0
            else:
                val = numerator * tpl_denom_inv / np.sqrt(win_sqsum)

            if val > max_val:
                max_val = val
                max_loc_y = y
                max_loc_x = x

    return max_val, max_loc_y, max_loc_x


def match_template(image_gray: np.ndarray, template_gray: np.ndarray):
    """
    Numba 加速的模板匹配（替代 cv2.matchTemplate + cv2.minMaxLoc）。

    image_gray: 灰度截图 (H, W) uint8
    template_gray: 灰度模板 (h, w) uint8

    返回: (max_val, max_loc_y, max_loc_x)
    """
    if not HAS_NUMBA:
        import cv2
        result = cv2.matchTemplate(image_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        return max_val, max_loc[1], max_loc[0]

    img_h, img_w = image_gray.shape
    tpl_h, tpl_w = template_gray.shape

    if img_h < tpl_h or img_w < tpl_w:
        return 0.0, 0, 0

    return _match_template_numba(image_gray, template_gray, img_h, img_w, tpl_h, tpl_w)


# ============================================================
# PyTurboJPEG 解码（用于 JPEG 格式截图的快速解码）
# ============================================================

def decode_jpeg(data: bytes):
    """
    使用 PyTurboJPEG 解码 JPEG 数据为 numpy BGR 数组。
    比 cv2.imdecode 快 2-5 倍。
    
    返回: numpy BGR 图像数组 (H, W, 3)，失败返回 None
    """
    if not HAS_TURBOJPEG:
        import cv2
        nparr = np.frombuffer(data, np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    try:
        # TurboJPEG 解码为 BGR（与 OpenCV 兼容的格式）
        return _turbojpeg.decode(data, pixel_format=0)  # 0 = TJPF_BGR
    except Exception:
        return None


def decode_jpeg_to_gray(data: bytes):
    """
    使用 PyTurboJPEG 解码 JPEG 数据为灰度 numpy 数组。
    一步到位，比解码为 BGR 再转灰度更快。
    
    返回: numpy 灰度图像数组 (H, W)，失败返回 None
    """
    if not HAS_TURBOJPEG:
        import cv2
        nparr = np.frombuffer(data, np.uint8)
        bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if bgr is None:
            return None
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    try:
        # TurboJPEG 直接解码为灰度
        return _turbojpeg.decode(data, pixel_format=1)  # 1 = TJPF_GRAY
    except Exception:
        return None


# ============================================================
# 状态查询
# ============================================================

def get_acceleration_status():
    """获取加速功能状态"""
    return {
        'numba': HAS_NUMBA,
        'turbojpeg': HAS_TURBOJPEG,
    }
