import os
import subprocess
import logging
import datetime

# 每次运行生成统一的日志后缀，供 adb/image 日志共用
LOG_SUFFIX = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

# 全局日志开关，由设置页控制
enable_logging = False

class _FilterDisabled(logging.Filter):
    """当enable_logging为False时过滤掉所有日志"""
    def filter(self, record):
        return enable_logging

def get_log_dir():
    """获取日志目录"""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir

def get_adb_logger():
    """获取adb日志记录器，只写入本地文件，不输出到终端"""
    logger = logging.getLogger("adb")
    logger.setLevel(logging.INFO)
    # 防止重复添加handler导致日志重复写入
    if not logger.handlers:
        log_file = os.path.join(get_log_dir(), f"adb_{LOG_SUFFIX}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        file_handler.addFilter(_FilterDisabled())
        logger.addHandler(file_handler)
    logger.propagate = False
    return logger

def get_gui_logger():
    """获取GUI逻辑日志记录器，记录按钮点击、图片识别分析和点击指令，只写入本地文件"""
    logger = logging.getLogger("gui")
    logger.setLevel(logging.INFO)
    # 防止重复添加handler导致日志重复写入
    if not logger.handlers:
        log_file = os.path.join(get_log_dir(), f"GUIlog_{LOG_SUFFIX}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        file_handler.addFilter(_FilterDisabled())
        logger.addHandler(file_handler)
    logger.propagate = False
    return logger

def set_logging_enabled(enabled):
    """设置全局日志开关"""
    global enable_logging
    enable_logging = enabled

class ADBManager:
    def __init__(self):
        self.adb_path = self._get_adb_path()
        self.logger = get_adb_logger()
    
    def _get_adb_path(self):
        # 优先尝试调用同目录下platform-tools里的adb.exe
        adb_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "platform-tools", "adb.exe")
        if not os.path.exists(adb_path):
            # 最后尝试调用系统path中的adb
            adb_path = "adb"
        return adb_path
    
    def _decode_output(self, output_bytes):
        """尝试多种编码方式解码输出"""
        try:
            return output_bytes.decode('utf-8')
        except:
            try:
                return output_bytes.decode('gbk')
            except:
                return output_bytes.decode('utf-8', errors='replace')
    
    def get_devices(self):
        """
        获取已连接的设备列表
        """
        try:
            # 运行devices命令
            cmd = [self.adb_path, "devices"]
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            stdout = self._decode_output(result.stdout)
            self.logger.info(f"命令: {' '.join(cmd)} | 返回: {stdout.strip()}")
            
            lines = stdout.strip().split('\n')[1:]
            devices = []
            for line in lines:
                if line.strip():
                    device_info = line.split('\t')
                    if len(device_info) >= 2 and device_info[1].strip() == "device":
                        devices.append(device_info[0])
            return devices
        except Exception as e:
            self.logger.error(f"命令: {' '.join(cmd)} | 异常: {e}")
            raise Exception(f"获取设备列表失败: {e}")
    
    def connect_device(self, device):
        """
        连接设备
        """
        try:
            cmd = [self.adb_path, "connect", device]
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            stdout = self._decode_output(result.stdout)
            stderr = self._decode_output(result.stderr)
            self.logger.info(f"命令: {' '.join(cmd)} | 返回: {stdout.strip()} | 错误: {stderr.strip()}")
            if "connected to" in stdout or "already connected" in stderr:
                return True, "连接成功"
            else:
                return False, stderr.strip()
        except Exception as e:
            self.logger.error(f"命令: {' '.join(cmd)} | 异常: {e}")
            return False, str(e)
    
    def check_resolution(self, device):
        """
        检查设备分辨率是否为1280*720或720*1280
        """
        try:
            cmd = [self.adb_path, "-s", device, "shell", "wm", "size"]
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            output = self._decode_output(result.stdout).strip()
            self.logger.info(f"命令: {' '.join(cmd)} | 返回: {output}")
            if "Physical size:" in output:
                size_str = output.split("Physical size:")[1].strip()
                if size_str == "1280x720" or size_str == "720x1280":
                    return True
            return False
        except Exception as e:
            self.logger.error(f"命令: {' '.join(cmd)} | 异常: {e}")
            raise Exception(f"检查分辨率失败: {e}")