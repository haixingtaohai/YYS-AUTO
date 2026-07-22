import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
import os
import sys
import random
import json

# 在最开始就设置 Windows AppUserModelID，确保任务栏显示自定义图标
ICON_PATH = None
if os.name == 'nt':
    try:
        import ctypes
        # 设置应用程序用户模型 ID，这对 Windows 任务栏图标很重要
        myappid = 'yysauto.application.v2.8'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except:
        pass
    
    # 准备图标路径（优先使用根目录下的图标）
    try:
        # 先尝试根目录
        ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if not os.path.exists(ICON_PATH):
            # 再尝试 png 目录
            ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "png", "icon.ico")
            if not os.path.exists(ICON_PATH):
                ICON_PATH = None
    except:
        ICON_PATH = None

 #隐藏Windows终端窗口（暂时注释掉以查看调试信息）
if os.name == 'nt':
    ctypes.windll.user32.ShowWindow(
        ctypes.windll.kernel32.GetConsoleWindow(), 0
    )

# 输入法控制（仅 Windows）
_ime_hwnd = None       # 主窗口句柄
_ime_original = None   # 原始输入法上下文
if os.name == 'nt':
    try:
        _imm32 = ctypes.WinDLL('imm32', use_last_error=True)
    except:
        _imm32 = None
else:
    _imm32 = None

def _init_ime(hwnd):
    """初始化：保存原始输入法上下文并禁用"""
    global _ime_hwnd, _ime_original
    _ime_hwnd = hwnd
    if _imm32:
        try:
            _ime_original = _imm32.ImmAssociateContext(hwnd, 0)  # 关联NULL，禁用IME
        except:
            _ime_original = None

def _do_disable_ime():
    """窗口级禁用输入法"""
    if _imm32 and _ime_hwnd:
        try:
            _imm32.ImmAssociateContext(_ime_hwnd, 0)
        except:
            pass

def _do_enable_ime():
    """窗口级启用输入法"""
    if _imm32 and _ime_hwnd:
        try:
            # 传入原始句柄或0xFFFFFFFF让系统分配默认上下文
            ctx = _ime_original if _ime_original else 0xFFFFFFFF
            _imm32.ImmAssociateContext(_ime_hwnd, ctx)
        except:
            pass

def _on_entry_focus_in(event):
    """输入框获得焦点时启用输入法"""
    _do_enable_ime()

def _on_entry_focus_out(event):
    """输入框失去焦点后延迟检查，仍在输入框则保持，否则禁用"""
    event.widget.after(10, _check_focus_for_ime, event.widget)

def _check_focus_for_ime(widget):
    """检查焦点是否仍在输入框内"""
    try:
        focused = widget.winfo_toplevel().focus_get()
        if isinstance(focused, (tk.Entry, tk.Text, ttk.Entry, ttk.Combobox)):
            return
    except:
        pass
    _do_disable_ime()

def _on_root_focus_in(event):
    """窗口重获焦点时，若不在输入框内则重新禁用IME"""
    event.widget.after(20, _recheck_ime_on_focus, event.widget)

def _recheck_ime_on_focus(widget):
    """重新检查并确保IME状态正确"""
    try:
        focused = widget.focus_get()
        if isinstance(focused, (tk.Entry, tk.Text, ttk.Entry, ttk.Combobox)):
            _do_enable_ime()
        else:
            _do_disable_ime()
    except:
        _do_disable_ime()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from image_recognizer import ImageRecognizer
from adb import ADBManager, get_gui_logger



# 导入场景处理模块
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scenes'))
import yyh
import htdr
import sj
import dy
import dj
import dg
import k28
import k281
import k280
import yjsl
import jjtp
import hdpt
import guanbijiacheng

# GUI逻辑日志记录器
gui_logger = get_gui_logger()

class SettingsTab:
    def __init__(self, parent):
        self.parent = parent
        self.frame = ttk.Frame(parent.notebook)
        self._create_variables()
        self.setup_ui()
    
    def _create_variables(self):
        self.settings_ip_var = tk.StringVar(value=self.parent.adb_ip)
        self.settings_port_var = tk.StringVar(value=self.parent.adb_port)
        self.settings_link_var = tk.BooleanVar(value=self.parent.link_enabled)
        self.settings_close_jiacheng_var = tk.BooleanVar(value=self.parent.close_jiacheng_enabled)
        self.settings_close_jiacheng_wait_var = tk.StringVar(value=str(self.parent.close_jiacheng_wait))
        self.settings_huijuan_mode_var = tk.BooleanVar(value=self.parent.huijuan_mode)
        self.settings_dj_jinsheng_stop_var = tk.BooleanVar(value=self.parent.dj_jinsheng_stop)
        self.settings_sound_var = tk.BooleanVar(value=self.parent.sound_enabled)
        self.settings_sound_file_var = tk.StringVar(value=getattr(self.parent, 'sound_file', ''))
        self.settings_logging_var = tk.BooleanVar(value=self.parent.logging_enabled)
    
    def _log_change(self, old_value, new_value, enabled_msg, disabled_msg):
        if old_value != new_value and len(self.parent.tabs) > 0:
            msg = enabled_msg if new_value else disabled_msg
            self.parent.tabs[0].log(msg)
    
    def save_settings(self):
        self.parent.adb_ip = self.settings_ip_var.get()
        self.parent.adb_port = self.settings_port_var.get()
        
        old_link_enabled = self.parent.link_enabled
        self.parent.link_enabled = self.settings_link_var.get()
        
        if old_link_enabled != self.parent.link_enabled:
            if self.parent.link_enabled:
                for tab in self.parent.tabs:
                    if hasattr(tab, 'current_preset') and tab.current_preset == "队员":
                        tab.is_ready = False
            self._log_change(old_link_enabled, self.parent.link_enabled, 
                            "队员司机联动已启用", "队员司机联动已关闭")
        
        old_close_jiacheng_enabled = self.parent.close_jiacheng_enabled
        self.parent.close_jiacheng_enabled = self.settings_close_jiacheng_var.get()
        
        try:
            wait_time = int(self.settings_close_jiacheng_wait_var.get())
            if wait_time >= 0:
                self.parent.close_jiacheng_wait = wait_time
        except:
            pass
        
        if old_close_jiacheng_enabled != self.parent.close_jiacheng_enabled:
            if self.parent.close_jiacheng_enabled:
                msg = f"关闭加成功能已启用，等待{self.parent.close_jiacheng_wait}秒"
            else:
                msg = "关闭御魂加成功能已关闭"
            self._log_change(old_close_jiacheng_enabled, self.parent.close_jiacheng_enabled, msg, msg)
        
        old_huijuan_mode = self.parent.huijuan_mode
        self.parent.huijuan_mode = self.settings_huijuan_mode_var.get()
        self._log_change(old_huijuan_mode, self.parent.huijuan_mode, 
                        "绘卷模式已启用", "绘卷模式已关闭")
        
        old_dj_jinsheng_stop = self.parent.dj_jinsheng_stop
        self.parent.dj_jinsheng_stop = self.settings_dj_jinsheng_stop_var.get()
        self._log_change(old_dj_jinsheng_stop, self.parent.dj_jinsheng_stop,
                        "斗技段位晋升结束程序已启用", "斗技段位晋升结束程序已关闭")

        old_sound_enabled = self.parent.sound_enabled
        self.parent.sound_enabled = self.settings_sound_var.get()
        self.parent.sound_file = self.settings_sound_file_var.get()
        self._log_change(old_sound_enabled, self.parent.sound_enabled,
                        "提示音已开启", "提示音已关闭")
        
        # 日志设置
        old_logging_enabled = self.parent.logging_enabled
        self.parent.logging_enabled = self.settings_logging_var.get()
        if old_logging_enabled != self.parent.logging_enabled:
            from adb import set_logging_enabled
            set_logging_enabled(self.parent.logging_enabled)
            self._log_change(old_logging_enabled, self.parent.logging_enabled,
                            "日志记录已开启", "日志记录已关闭")
        
        self.parent.save_config()
    
    def _set_port(self, port):
        gui_logger.info(f"[设置] 点击按钮: 设置端口 {port}")
        self.settings_port_var.set(port)
        self.save_settings()
    
    def _connect_device(self):
        ip = self.settings_ip_var.get().strip()
        port = self.settings_port_var.get().strip()
        if not ip or not port:
            return
        gui_logger.info(f"[设置] 点击按钮: 连接设备 {ip}:{port}")
        self.connect_btn.config(state=tk.DISABLED, text="连接中...")
        def _worker():
            try:
                ir = ImageRecognizer()
                ir.device = f"{ip}:{port}"
                ir.connect_device()
            except:
                pass
            finally:
                self.parent.root.after(0, lambda: self.connect_btn.config(state=tk.NORMAL, text="连接"))
        threading.Thread(target=_worker, daemon=True).start()
    
    def _restart_adb(self):
        """重启ADB服务"""
        gui_logger.info("[设置] 点击按钮: 重启ADB")
        import subprocess
        # 停止所有标签运行
        self.parent.stop_all_tabs()
        # 锁定UI
        self.parent.settings_tab.lock_adb_section()
        for tab in self.parent.tabs:
            tab.lock_for_adb_starting()
            tab.log("正在重启ADB，请稍候...")
        # 子线程执行重启
        def _worker():
            try:
                ir = ImageRecognizer()
                subprocess.run([ir.adb_path, "kill-server"], capture_output=True, timeout=10)
                subprocess.run([ir.adb_path, "start-server"], capture_output=True, timeout=10)
            except:
                pass
            # 刷新设备列表
            try:
                for tab in self.parent.tabs:
                    tab.refresh_devices()
            except:
                pass
            # 回到主线程解锁并提示
            self.parent.root.after(0, self._on_adb_restarted)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_adb_restarted(self):
        """ADB重启完成后的回调"""
        gui_logger.info("[设置] ADB重启完成")
        self.parent.settings_tab.unlock_adb_section()
        for tab in self.parent.tabs:
            tab.unlock_after_adb_started()
            tab.log("ADB已重启")
    
    def _copy_password(self):
        gui_logger.info("[设置] 点击按钮: 复制网盘密码")
        self.parent.root.clipboard_clear()
        self.parent.root.clipboard_append("62m8")
        self.parent.root.update()

    def _open_update_link(self):
        gui_logger.info("[设置] 点击按钮: 更新软件")
        import webbrowser
        webbrowser.open("https://wwbet.lanzoum.com/b00ct17efa")

    def _open_github(self):
        gui_logger.info("[设置] 点击按钮: 打开GitHub仓库")
        import webbrowser
        webbrowser.open("https://github.com/haixingtaohai/YYS-AUTO")

    def _copy_qq_group(self):
        gui_logger.info("[设置] 点击按钮: 复制QQ群号")
        self.parent.root.clipboard_clear()
        self.parent.root.clipboard_append("647871264")
        self.parent.root.update()

    def _copy_email(self):
        gui_logger.info("[设置] 点击按钮: 复制作者邮箱")
        self.parent.root.clipboard_clear()
        self.parent.root.clipboard_append("haixingtaohai@163.com")
        self.parent.root.update()
    
    def _create_adb_section(self, parent_frame):
        self.adb_group_frame = ttk.LabelFrame(parent_frame, text="ADB设备连接", padding="8")
        self.adb_group_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        ip_port_frame = ttk.Frame(self.adb_group_frame)
        ip_port_frame.pack(fill=tk.X, pady=2)
        ttk.Label(ip_port_frame, text="IP:", font=('Microsoft YaHei', 9)).pack(side=tk.LEFT, padx=2)
        self.ip_entry = ttk.Entry(ip_port_frame, textvariable=self.settings_ip_var, width=12)
        self.ip_entry.pack(side=tk.LEFT, padx=2)
        self.ip_entry.bind('<FocusOut>', lambda e: self.save_settings())

        ttk.Label(ip_port_frame, text="端口:", font=('Microsoft YaHei', 9)).pack(side=tk.LEFT, padx=2)
        self.port_entry = ttk.Entry(ip_port_frame, textvariable=self.settings_port_var, width=6)
        self.port_entry.pack(side=tk.LEFT, padx=2)
        self.port_entry.bind('<FocusOut>', lambda e: self.save_settings())

        self.port_btn_frame = ttk.Frame(self.adb_group_frame)
        self.port_btn_frame.pack(fill=tk.X, pady=2)
        self.port_btn_1 = ttk.Button(self.port_btn_frame, text="16384", command=lambda: self._set_port("16384"), width=6)
        self.port_btn_1.pack(side=tk.LEFT, padx=1)
        self.port_btn_2 = ttk.Button(self.port_btn_frame, text="16416", command=lambda: self._set_port("16416"), width=6)
        self.port_btn_2.pack(side=tk.LEFT, padx=1)

        btn_frame = tk.Frame(self.adb_group_frame)
        btn_frame.pack(fill=tk.X, pady=2)
        self.connect_btn = tk.Button(btn_frame, text="连接", command=self._connect_device, width=8, height=2)
        self.connect_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 1))
        self.restart_adb_btn = tk.Button(btn_frame, text="重启ADB", command=self._restart_adb, width=8, height=2)
        self.restart_adb_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(1, 0))

        # ADB启动状态控件列表
        self._adb_controls = [
            self.ip_entry, self.port_entry, self.port_btn_1, self.port_btn_2,
            self.connect_btn, self.restart_adb_btn
        ]

    def lock_adb_section(self):
        """ADB启动期间锁定设置页ADB连接区域"""
        for ctrl in self._adb_controls:
            ctrl.config(state=tk.DISABLED)

    def unlock_adb_section(self):
        """ADB启动完成后解锁设置页ADB连接区域"""
        self.ip_entry.config(state=tk.NORMAL)
        self.port_entry.config(state=tk.NORMAL)
        self.port_btn_1.config(state=tk.NORMAL)
        self.port_btn_2.config(state=tk.NORMAL)
        self.connect_btn.config(state=tk.NORMAL, text="连接")
        self.restart_adb_btn.config(state=tk.NORMAL, text="重启ADB")

    def _set_close_jiacheng_wait(self):
        """弹窗设置关闭加成等待时间"""
        gui_logger.info("[设置] 点击按钮: 设置关闭加成等待秒数")
        dialog = tk.Toplevel(self.parent.root)
        dialog.title("设置等待秒数")
        dialog.resizable(False, False)
        dialog.transient(self.parent.root)
        dialog.grab_set()

        ttk.Label(dialog, text="挑战结束后关闭御魂加成等待秒数:", font=('Microsoft YaHei', 9)).pack(padx=20, pady=(15, 5))

        entry_var = tk.StringVar(value=self.settings_close_jiacheng_wait_var.get())
        entry = ttk.Entry(dialog, textvariable=entry_var, width=10)
        entry.pack(padx=20, pady=5)
        entry.focus_set()

        def on_ok():
            try:
                val = int(entry_var.get())
                if val >= 0:
                    self.settings_close_jiacheng_wait_var.set(str(val))
                    self.save_settings()
            except:
                pass
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=(5, 15))
        ttk.Button(btn_frame, text="确定", command=on_ok, width=8).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy, width=8).pack(side=tk.LEFT, padx=5)

        dialog.update_idletasks()
        main_x = self.parent.root.winfo_x()
        main_y = self.parent.root.winfo_y()
        main_w = self.parent.root.winfo_width()
        main_h = self.parent.root.winfo_height()
        d_w = dialog.winfo_width()
        d_h = dialog.winfo_height()
        x = main_x + (main_w - d_w) // 2
        y = main_y + (main_h - d_h) // 2
        dialog.geometry(f"+{x}+{y}")
    
    def _create_sound_section(self, parent_frame):
        sound_group = ttk.LabelFrame(parent_frame, text="提示音设置", padding="8")
        sound_group.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # 开关行
        top_row = ttk.Frame(sound_group)
        top_row.pack(fill=tk.X, pady=2)
        ttk.Checkbutton(top_row, text="启用提示音", variable=self.settings_sound_var,
                        command=self.save_settings).pack(side=tk.LEFT)

        # 音效文件选择
        file_row = ttk.Frame(sound_group)
        file_row.pack(fill=tk.X, pady=2)
        ttk.Label(file_row, text="音效:", font=('Microsoft YaHei', 9)).pack(side=tk.LEFT, padx=2)
        self.sound_combo = ttk.Combobox(file_row, width=14, state="readonly",
                                         textvariable=self.settings_sound_file_var)
        self.sound_combo.pack(side=tk.LEFT, padx=2)
        self.sound_combo.bind("<<ComboboxSelected>>", lambda e: self.save_settings())
        ttk.Button(file_row, text="试听", command=self._preview_sound, width=5).pack(side=tk.LEFT, padx=1)

        # 操作按钮
        btn_row = ttk.Frame(sound_group)
        btn_row.pack(fill=tk.X, pady=2)
        ttk.Button(btn_row, text="添加", command=self._add_sound_file, width=6).pack(side=tk.LEFT, padx=1)
        ttk.Button(btn_row, text="删除", command=self._delete_sound_file, width=6).pack(side=tk.LEFT, padx=1)
        ttk.Button(btn_row, text="刷新列表", command=self._refresh_sound_list, width=8).pack(side=tk.LEFT, padx=1)

        # 初始化音效列表
        self._refresh_sound_list()

    def _get_wav_folder(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "wav")

    def _refresh_sound_list(self):
        """刷新音效文件列表"""
        wav_folder = self._get_wav_folder()
        files = []
        if os.path.exists(wav_folder):
            for f in sorted(os.listdir(wav_folder)):
                if f.lower().endswith('.wav'):
                    files.append(f)
        self.sound_combo['values'] = files
        current = self.settings_sound_file_var.get()
        if current in files:
            self.sound_combo.set(current)
        elif files:
            self.sound_combo.set(files[0])
            self.settings_sound_file_var.set(files[0])

    def _add_sound_file(self):
        """添加音效文件"""
        gui_logger.info("[设置] 点击按钮: 添加音效文件")
        from tkinter import filedialog
        wav_folder = self._get_wav_folder()
        os.makedirs(wav_folder, exist_ok=True)
        file_path = filedialog.askopenfilename(
            title="选择WAV音频文件",
            filetypes=[("WAV音频", "*.wav"), ("所有文件", "*.*")]
        )
        if file_path:
            try:
                filename = os.path.basename(file_path)
                dest = os.path.join(wav_folder, filename)
                import shutil
                shutil.copy2(file_path, dest)
                self._refresh_sound_list()
                self.settings_sound_file_var.set(filename)
                self.save_settings()
            except Exception as e:
                pass

    def _delete_sound_file(self):
        """删除选中的音效文件"""
        gui_logger.info("[设置] 点击按钮: 删除音效文件")
        filename = self.settings_sound_file_var.get()
        if not filename:
            return
        wav_folder = self._get_wav_folder()
        filepath = os.path.join(wav_folder, filename)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                self._refresh_sound_list()
                self.save_settings()
            except Exception as e:
                pass

    def _preview_sound(self):
        """试听选中的音效文件"""
        gui_logger.info("[设置] 点击按钮: 试听音效")
        filename = self.settings_sound_file_var.get()
        if not filename or not filename.lower().endswith('.wav'):
            return
        wav_folder = self._get_wav_folder()
        wav_path = os.path.join(wav_folder, filename)
        if os.path.exists(wav_path):
            try:
                import winsound
                winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception as e:
                pass

    def _open_log_folder(self):
        gui_logger.info("[设置] 点击按钮: 打开日志文件夹")
        from adb import get_log_dir
        import subprocess
        log_dir = get_log_dir()
        try:
            if sys.platform.startswith('win'):
                os.startfile(log_dir)
            else:
                subprocess.Popen(['xdg-open', log_dir])
        except Exception as e:
            if len(self.parent.tabs) > 0:
                self.parent.tabs[0].log(f"打开日志文件夹失败: {e}")

    def _clear_logs(self):
        gui_logger.info("[设置] 点击按钮: 清空日志")
        from adb import get_log_dir
        log_dir = get_log_dir()
        cleared = 0
        for filename in os.listdir(log_dir):
            if filename.endswith('.log'):
                try:
                    file_path = os.path.join(log_dir, filename)
                    os.remove(file_path)
                    cleared += 1
                except Exception:
                    pass
        if len(self.parent.tabs) > 0:
            self.parent.tabs[0].log(f"已清空 {cleared} 个日志文件")
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.frame, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="YYS-AUTO 设置", font=('Microsoft YaHei', 12, 'bold')).pack(pady=(0, 10))
        
        # ADB连接和提示音在同一行，各占一半
        groups_container = ttk.Frame(main_frame)
        groups_container.pack(fill=tk.X, pady=(0, 10))
        self._create_adb_section(groups_container)
        self._create_sound_section(groups_container)

class DeviceTab:
    def __init__(self, parent, tab_name, png_base_folder, presets):
        self.parent = parent  # 现在parent是AutoClickerUI实例
        self.png_base_folder = png_base_folder
        self.presets = presets
        self.tab_name = tab_name  # 标签名称
        
        self.frame = ttk.Frame(parent.notebook)  # 使用notebook作为frame的父容器
        self.recognizer = None
        self.running = False
        self.thread = threading.Thread()
        self.manual_stop = False  # 标记是否是手动停止
        self.current_preset_var = tk.StringVar(value="业原火")
        self.current_preset = "业原火"
        self.target_count_var = tk.StringVar(value="200")  # 默认挑战200次
        self.current_count = 0
        self.tab_index = 0  # 标签索引
        self.saved_device = None  # 保存的设备（用于初始化）
        self.preset_thresholds = {}  # 每个场景记住用户设置的阈值
        
        # 队员准备状态（仅用于队员场景）
        self.is_ready = False
        
        self.setup_ui(tab_name)
    
    def save_tab_config(self):
        # 只保存tab_index>0的设备标签（tab0是设置标签，不保存）
        if not hasattr(self, 'tab_index') or self.tab_index <= 0:
            return
        # 保存当前选择的设备
        current_device = self.device_combo.get() if hasattr(self, 'device_combo') else ''
        config = {
            "tab_name": self.tab_name if hasattr(self, 'tab_name') else "",
            "preset": self.current_preset,
            "target_count": self.target_count_var.get(),
            "threshold": self.threshold_entry.get(),
            "preset_thresholds": self.preset_thresholds,
            "device": current_device
        }
        self.parent.saved_config.setdefault("tabs", {})[str(self.tab_index)] = config
        self.parent.save_config()

    def load_tab_config(self, config):
        # 加载保存的标签配置
        # 立即设置tab_name（避免延迟导致丢失）
        if config.get("tab_name"):
            self.tab_name = config["tab_name"]
            # 延迟设置UI（在setup_ui之后）
            self.parent.root.after(50, lambda: self._set_tab_name(config["tab_name"]))
        # 加载保存的设备
        saved_dev = config.get("device", "")
        if saved_dev:
            self.saved_device = saved_dev
        else:
            self.saved_device = None
        if config.get("preset"):
            self.current_preset = config["preset"]
            self.current_preset_var.set(config["preset"])
            # 延迟设置preset_combo（在setup_ui之后）
            self.parent.root.after(100, lambda: self._set_preset_combo(config["preset"]))
        if config.get("target_count"):
            self.target_count_var.set(config["target_count"])
        if config.get("threshold"):
            self.threshold_entry.delete(0, tk.END)
            self.threshold_entry.insert(0, config["threshold"])
        if config.get("preset_thresholds"):
            self.preset_thresholds = config["preset_thresholds"]
    
    def _set_tab_name(self, tab_name):
        # 设置标签名称
        self.tab_name = tab_name
        try:
            self.parent.notebook.tab(self.frame, text=tab_name)
        except:
            pass
    
    def on_tab_name_changed(self, event=None):
        # 标签名称改变时保存 - 改为弹出窗口方式
        self.show_rename_tab_dialog()
    
    def show_rename_tab_dialog(self):
        # 弹出窗口修改标签名称
        dialog = tk.Toplevel(self.parent.root)
        dialog.title("修改标签名称")
        dialog.geometry("300x120")
        dialog.transient(self.parent.root)
        dialog.grab_set()
        
        # 窗口相对于主窗口居中
        dialog.update_idletasks()
        dialog_width = dialog.winfo_width()
        dialog_height = dialog.winfo_height()
        main_x = self.parent.root.winfo_x()
        main_y = self.parent.root.winfo_y()
        main_width = self.parent.root.winfo_width()
        main_height = self.parent.root.winfo_height()
        x = main_x + (main_width // 2) - (dialog_width // 2)
        y = main_y + (main_height // 2) - (dialog_height // 2)
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        ttk.Label(dialog, text="请输入新的标签名称:").pack(pady=10)
        
        entry = ttk.Entry(dialog, width=25)
        entry.insert(0, self.tab_name)
        entry.pack(pady=5)
        entry.focus_set()
        
        def confirm_rename():
            new_name = entry.get().strip()
            if new_name:
                gui_logger.info(f"[{self.tab_name}] 标签重命名为: {new_name}")
                self.tab_name = new_name
                try:
                    self.parent.notebook.tab(self.frame, text=new_name)
                    self.tab_name_label.config(text=new_name)
                except:
                    pass
                self.save_tab_config()
            dialog.destroy()
        
        def on_enter(event):
            confirm_rename()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="确定", command=confirm_rename).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        entry.bind("<Return>", on_enter)
        entry.bind("<Escape>", lambda e: dialog.destroy())
        dialog.bind("<Escape>", lambda e: dialog.destroy())
    
    def _set_device_combo(self, device):
        # 设置device_combo的值
        try:
            if hasattr(self, 'device_combo') and device in self.device_combo["values"]:
                self.device_combo.current(self.device_combo["values"].index(device))
        except:
            pass
    
    def _set_preset_combo(self, preset):
        # 设置preset_combo的值
        try:
            if hasattr(self, 'preset_combo') and preset in self.preset_combo["values"]:
                self.preset_combo.current(self.preset_combo["values"].index(preset))
        except:
            pass
    
    def setup_ui(self, tab_name):
        main_frame = ttk.Frame(self.frame, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 顶部：标题
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=2)
        ttk.Label(title_frame, text="YYS-AUTOv2.8", font=('Microsoft YaHei', 16, 'bold')).pack(anchor=tk.CENTER)
        
        # 中间：三列布局
        middle_frame = ttk.Frame(main_frame)
        middle_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 第一列：设备管理
        device_card = ttk.LabelFrame(middle_frame, text="📱 设备管理", padding="5")
        device_card.pack(side=tk.LEFT, fill=tk.BOTH, padx=2)
        device_card.config(width=220)
        device_card.pack_propagate(False)
        
        # 刷新和清除按钮
        device_btn_frame = ttk.Frame(device_card)
        device_btn_frame.pack(fill=tk.X, pady=2)
        self.refresh_btn = ttk.Button(device_btn_frame, text="刷新", command=self.refresh_all_devices, width=8)
        self.refresh_btn.pack(side=tk.LEFT, padx=2)
        self.clear_device_btn = ttk.Button(device_btn_frame, text="清除", command=self.clear_device, width=8)
        self.clear_device_btn.pack(side=tk.LEFT, padx=2)
        
        # 设备选择
        device_combo_frame = ttk.Frame(device_card)
        device_combo_frame.pack(fill=tk.X, pady=2)
        ttk.Label(device_combo_frame, text="设备选择：", font=('Microsoft YaHei', 9)).pack(side=tk.LEFT, padx=2)
        # 暂时设置为可编辑状态，测试是否能显示设备
        self.device_combo = ttk.Combobox(device_combo_frame, width=20, state="normal")
        self.device_combo.pack(side=tk.LEFT, padx=2)
        self.device_combo.bind("<<ComboboxSelected>>", self.on_device_changed)
        
        ttk.Separator(device_card, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        
        # 运行参数
        ttk.Label(device_card, text="⚙️ 运行参数", font=('Microsoft YaHei', 9, 'bold')).pack(anchor=tk.W, padx=2, pady=(5, 2))
        
        # 识别阈值
        threshold_frame = ttk.Frame(device_card)
        threshold_frame.pack(fill=tk.X, pady=2)
        ttk.Label(threshold_frame, text="识别阈值：", font=('Microsoft YaHei', 9)).pack(side=tk.LEFT, padx=2)
        self.threshold_entry = ttk.Entry(threshold_frame, width=6)
        self.threshold_entry.pack(side=tk.LEFT, padx=2)
        self.threshold_entry.bind('<FocusOut>', lambda e: self.save_tab_config())
        
        # 运行次数
        count_frame = ttk.Frame(device_card)
        count_frame.pack(fill=tk.X, pady=2)
        ttk.Label(count_frame, text="运行次数：", font=('Microsoft YaHei', 9)).pack(side=tk.LEFT, padx=2)
        self.target_count_entry = ttk.Entry(count_frame, width=6, textvariable=self.target_count_var)
        self.target_count_entry.pack(side=tk.LEFT, padx=2)
        self.target_count_entry.bind('<FocusOut>', lambda e: self.save_tab_config())
        
        # 重置默认按钮
        self.reset_btn = ttk.Button(device_card, text="重置默认", command=self.reset_defaults, width=18)
        self.reset_btn.pack(fill=tk.X, padx=2, pady=5)
        
        # 第二列：场景选择
        scene_card = ttk.LabelFrame(middle_frame, text="🎮 场景选择", padding="5")
        scene_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        
        # 创建两列布局
        scene_frame = ttk.Frame(scene_card)
        scene_frame.pack(fill=tk.BOTH, expand=True)
        
        left_frame = ttk.Frame(scene_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        
        right_frame = ttk.Frame(scene_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        
        # 将场景平均分配到两列
        presets_list = list(self.presets.keys())
        mid = (len(presets_list) + 1) // 2
        
        # 保存所有Radiobutton引用以便锁定/解锁
        self.preset_radiobuttons = []
        
        for i, preset_name in enumerate(presets_list[:mid]):
            rb = ttk.Radiobutton(left_frame, text=preset_name, variable=self.current_preset_var, value=preset_name, 
                                command=self.on_preset_change)
            rb.pack(anchor=tk.W, padx=2, pady=1)
            self.preset_radiobuttons.append(rb)
        
        for i, preset_name in enumerate(presets_list[mid:]):
            rb = ttk.Radiobutton(right_frame, text=preset_name, variable=self.current_preset_var, value=preset_name, 
                                command=self.on_preset_change)
            rb.pack(anchor=tk.W, padx=2, pady=1)
            self.preset_radiobuttons.append(rb)
        
        # 第三列：日志
        log_card = ttk.LabelFrame(middle_frame, text="📋 运行日志", padding="5")
        log_card.pack(side=tk.LEFT, fill=tk.BOTH, padx=2)
        log_card.config(width=180)
        log_card.pack_propagate(False)
        
        self.log_text = scrolledtext.ScrolledText(log_card, height=10, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 底部：运行控制
        bottom_frame = ttk.LabelFrame(main_frame, text="🚀 运行控制", padding="5")
        bottom_frame.pack(fill=tk.X, pady=5)

        control_frame = ttk.Frame(bottom_frame)
        control_frame.pack(side=tk.LEFT, padx=2)

        # 四个按钮放同一行
        self.start_btn = ttk.Button(control_frame, text="开始", command=self.start_loop, width=10)
        self.start_btn.pack(side=tk.LEFT, padx=3)

        self.stop_btn = ttk.Button(control_frame, text="停止", command=self.stop_loop, width=10, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=3)

        self.start_all_btn = ttk.Button(control_frame, text="全部开始", command=self.parent.start_all_tabs, width=10)
        self.start_all_btn.pack(side=tk.LEFT, padx=3)
        ttk.Button(control_frame, text="全部停止", command=self.parent.stop_all_tabs, width=10).pack(side=tk.LEFT, padx=3)

        self.on_preset_change(None)
    
    def reset_defaults(self):
        # 重置默认值
        gui_logger.info(f"[{self.tab_name}] 点击按钮: 重置默认")
        self.target_count_var.set("200")
        self.preset_thresholds = {}  # 清除所有场景的阈值记忆
        # 直接用预设默认值设置阈值，避开on_preset_change的保存恢复逻辑
        preset = self.presets[self.current_preset]
        self.threshold_entry.delete(0, tk.END)
        self.threshold_entry.insert(0, str(preset["threshold"]))
        self.save_tab_config()
        self.log("已重置默认参数")
    
    def on_preset_change(self, event=None):
        # 保存当前场景的阈值到记忆
        try:
            current_threshold = self.threshold_entry.get().strip()
            self.preset_thresholds[self.current_preset] = current_threshold
        except:
            pass
        
        self.current_preset = self.current_preset_var.get()
        gui_logger.info(f"[{self.tab_name}] 切换场景: {self.current_preset}")
        preset = self.presets[self.current_preset]
        
        # 优先使用用户之前为该场景设置的阈值，否则使用预设默认值
        saved_threshold = self.preset_thresholds.get(self.current_preset, "")
        self.threshold_entry.delete(0, tk.END)
        if saved_threshold:
            self.threshold_entry.insert(0, saved_threshold)
        else:
            self.threshold_entry.insert(0, str(preset["threshold"]))
        # 场景选择变化时保存配置
        self.save_tab_config()
    
    def refresh_all_devices(self):
        # 刷新所有标签的设备列表
        gui_logger.info(f"[{self.tab_name}] 点击按钮: 刷新设备")
        for tab in self.parent.tabs:
            tab.refresh_devices()
    
    def on_device_changed(self, event=None):
        # 设备选择变化时，更新 saved_device 并刷新所有标签的设备列表
        if hasattr(self, 'device_combo'):
            self.saved_device = self.device_combo.get()
            gui_logger.info(f"[{self.tab_name}] 选择设备: {self.saved_device}")
        # 设备选择变化时保存配置
        self.save_tab_config()
        self.refresh_all_devices()
    
    def lock_controls(self):
        # 锁定所有控件
        if hasattr(self, 'device_combo'):
            self.device_combo.config(state=tk.DISABLED)
        if hasattr(self, 'threshold_entry'):
            self.threshold_entry.config(state=tk.DISABLED)
        if hasattr(self, 'target_count_entry'):
            self.target_count_entry.config(state=tk.DISABLED)
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.config(state=tk.DISABLED)
        if hasattr(self, 'clear_device_btn'):
            self.clear_device_btn.config(state=tk.DISABLED)
        if hasattr(self, 'reset_btn'):
            self.reset_btn.config(state=tk.DISABLED)
        # 锁定所有场景选择Radiobutton
        if hasattr(self, 'preset_radiobuttons'):
            for rb in self.preset_radiobuttons:
                rb.config(state=tk.DISABLED)
    
    def unlock_controls(self):
        # 解锁所有控件
        if hasattr(self, 'device_combo'):
            self.device_combo.config(state=tk.NORMAL)
        if hasattr(self, 'threshold_entry'):
            self.threshold_entry.config(state=tk.NORMAL)
        if hasattr(self, 'target_count_entry'):
            self.target_count_entry.config(state=tk.NORMAL)
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.config(state=tk.NORMAL)
        if hasattr(self, 'clear_device_btn'):
            self.clear_device_btn.config(state=tk.NORMAL)
        if hasattr(self, 'reset_btn'):
            self.reset_btn.config(state=tk.NORMAL)
        # 解锁所有场景选择Radiobutton
        if hasattr(self, 'preset_radiobuttons'):
            for rb in self.preset_radiobuttons:
                rb.config(state=tk.NORMAL)

    def lock_for_adb_starting(self):
        """ADB启动期间锁定设备管理和运行控制"""
        if hasattr(self, 'device_combo'):
            self.device_combo.config(state=tk.DISABLED)
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.config(state=tk.DISABLED)
        if hasattr(self, 'clear_device_btn'):
            self.clear_device_btn.config(state=tk.DISABLED)
        if hasattr(self, 'start_btn'):
            self.start_btn.config(state=tk.DISABLED)
        if hasattr(self, 'start_all_btn'):
            self.start_all_btn.config(state=tk.DISABLED)

    def unlock_after_adb_started(self):
        """ADB启动完成后解锁设备管理和运行控制"""
        if hasattr(self, 'device_combo'):
            self.device_combo.config(state="normal")
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.config(state=tk.NORMAL)
        if hasattr(self, 'clear_device_btn'):
            self.clear_device_btn.config(state=tk.NORMAL)
        if hasattr(self, 'start_btn'):
            self.start_btn.config(state=tk.NORMAL)
        if hasattr(self, 'start_all_btn'):
            self.start_all_btn.config(state=tk.NORMAL)
    
    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        # 同步记录到GUI日志（场景分析输出）
        gui_logger.info(f"[{self.tab_name}] {message}")

    def play_sound(self):
        """播放提示音（非手动停止时调用）"""
        if not hasattr(self.parent, 'sound_enabled') or not self.parent.sound_enabled:
            return
        try:
            wav_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wav")
            if not os.path.exists(wav_folder):
                return
            # 优先使用用户选择的音效文件
            sound_file = getattr(self.parent, 'sound_file', '')
            if sound_file and sound_file.lower().endswith('.wav'):
                wav_path = os.path.join(wav_folder, sound_file)
                if os.path.exists(wav_path):
                    import winsound
                    winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                    return
            # 没有选择文件或文件不存在，尝试播放第一个wav
            wav_files = [f for f in os.listdir(wav_folder) if f.lower().endswith('.wav')]
            if wav_files:
                wav_path = os.path.join(wav_folder, wav_files[0])
                import winsound
                winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception as e:
            pass
    
    def clear_device(self):
        # 清除当前标签选择的设备
        gui_logger.info(f"[{self.tab_name}] 点击按钮: 清除设备")
        if self.recognizer:
            self.recognizer.device = None
        # 清空选择框和 saved_device
        self.device_combo.set('')
        self.saved_device = None

        self.log("已清除当前设备")
        # 保存配置
        self.save_tab_config()
        # 刷新其他标签的设备列表（不刷新当前标签，避免重新选择）
        for tab in self.parent.tabs:
            if tab != self:
                tab.refresh_devices()

    def refresh_devices(self):
        try:
            # 确保device_combo属性存在
            if not hasattr(self, 'device_combo'):
                return
            
            # 先保存当前选择的设备
            current_device = self.device_combo.get()
            
            adb_manager = ADBManager()
            devices = adb_manager.get_devices()
            
            # 排除其他标签已选择的设备
            available_devices = []
            for device in devices:
                # 检查其他标签是否已选择此设备
                device_used = False
                try:
                    for tab in self.parent.tabs:
                        if tab != self:
                            # 检查其他标签的saved_device和当前选择的设备
                            if hasattr(tab, 'saved_device') and tab.saved_device == device:
                                device_used = True
                                break
                            if hasattr(tab, 'device_combo'):
                                selected_device = tab.device_combo.get()
                                if selected_device == device:
                                    device_used = True
                                    break
                except:
                    pass
                if not device_used:
                    available_devices.append(device)
            
            # 直接设置下拉框值
            self.device_combo['values'] = available_devices

            # 优先使用当前选择的设备，其次使用保存的设备
            restore_device = current_device or self.saved_device
            if restore_device and restore_device in available_devices:
                self.device_combo.set(restore_device)
                # 如果是通过saved_device恢复的，更新current_device
                if not current_device:
                    self.saved_device = None
            elif not current_device:
                # 没有保存的设备，留空让用户选择
                self.device_combo.set("")
            else:
                self.device_combo.set("无设备")
            
            # 强制更新UI
            self.device_combo.update()
        except Exception as e:
            if hasattr(self, 'log'):
                self.log(f"获取设备列表失败: {e}")
    
    def start_loop(self):
        device = self.device_combo.get()
        gui_logger.info(f"[{self.tab_name}] 点击按钮: 开始 | 设备: {device} | 场景: {self.current_preset}")
        if not device:
            self.log("请选择设备")
            return
        
        preset = self.presets[self.current_preset]
        template_folder = os.path.join(self.png_base_folder, preset["folder"])
        
        if not os.path.exists(template_folder):
            self.log(f"模板文件夹不存在: {template_folder}")
            return
        
        self.recognizer = ImageRecognizer()
        self.recognizer.device = device
        self.recognizer.png_folder = template_folder
        self.recognizer.click_x = preset["click_x"]
        self.recognizer.click_y = preset["click_y"]
        self.recognizer.threshold = float(self.threshold_entry.get().strip())
        
        # 选择框中显示的设备已经是已连接状态，不再执行连接操作
        self.log(f"设备连接成功: {device}")
        
        # 检查设备分辨率是否为1280*720
        def check_resolution():
            try:
                adb_manager = ADBManager()
                return adb_manager.check_resolution(device)
            except Exception as e:
                self.log(f"检查分辨率失败: {e}")
                return False
        
        if not check_resolution():
            self.log("分辨率不是1280*720或720*1280，请修改后再运行")
            return
        
        self.running = True
        self.manual_stop = False  # 重置手动停止标记
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        # 锁定所有控件
        self.lock_controls()
        
        self.thread = threading.Thread(target=self.run_loop_thread, daemon=True)
        self.thread.start()
        
        self.log("已启动")
    
    def run_loop_thread(self):
        preset = self.presets[self.current_preset]
        count_challenge = preset.get("count_challenge", True)

        # 获取目标挑战次数
        try:
            target_count = int(self.target_count_var.get().strip())
        except ValueError:
            target_count = 200  # 默认200次

        gui_logger.info(f"[{self.tab_name}] 开始运行循环 | 场景: {self.current_preset} | 目标次数: {target_count}")

        consecutive_challenge = 0
        self.current_count = 0
        last_clicked_tiaozhan = False  # 记录上一次是否点击了tiaozhan
        recognition_attempts = 0  # 困28场景下未识别到的尝试次数
        last_clicked_putong_boss = False  # 记录上一次是否点击了putong或boss
        
        # 队员准备状态回调
        def mark_ready():
            self.is_ready = True
            self.log("  队员已准备")
        
        def mark_unready():
            self.is_ready = False
            self.log("  队员未准备")
        
        # 检查队员是否已准备的回调（仅用于司机）
        def check_teammates_ready():
            if not hasattr(self.parent, 'link_enabled') or not self.parent.link_enabled:
                return True
            # 查找所有队员标签
            ready_count = 0
            total_teammates = 0
            for tab in self.parent.tabs:
                if tab.current_preset == "队员":
                    total_teammates += 1
                    if tab.is_ready:
                        ready_count += 1
            # 至少有一个队员且所有队员都准备好
            return total_teammates > 0 and ready_count == total_teammates
        
        # 标记所有队员为未准备（仅用于司机）
        def mark_all_teammates_unready():
            if hasattr(self.parent, 'link_enabled') and self.parent.link_enabled:
                for tab in self.parent.tabs:
                    if tab.current_preset == "队员":
                        tab.is_ready = False
                        tab.log("  队员已重置为未准备")
        
        while self.running:
            results = self.recognizer.run_once()
            
            if results:
                # 根据当前场景调用对应的处理函数
                stop_flag = False
                need_wait = False
                if self.current_preset == "业原火":
                    stop_flag, self.current_count, consecutive_challenge, last_clicked_tiaozhan = yyh.handle_scene(
                        results, self.recognizer, self.log, self.current_count, target_count, count_challenge, consecutive_challenge, last_clicked_tiaozhan
                    )
                elif self.current_preset == "魂土单人":
                    stop_flag, self.current_count, consecutive_challenge, last_clicked_tiaozhan = htdr.handle_scene(
                        results, self.recognizer, self.log, self.current_count, target_count, count_challenge, consecutive_challenge, last_clicked_tiaozhan
                    )
                elif self.current_preset == "司机":
                    link_enabled = hasattr(self.parent, 'link_enabled') and self.parent.link_enabled
                    stop_flag, self.current_count, consecutive_challenge, last_clicked_tiaozhan = sj.handle_scene(
                        results, self.recognizer, self.log, self.current_count, target_count, count_challenge, consecutive_challenge, last_clicked_tiaozhan,
                        link_enabled, check_teammates_ready, mark_all_teammates_unready
                    )
                elif self.current_preset == "队员":
                    stop_flag, self.current_count, consecutive_challenge, last_clicked_tiaozhan = dy.handle_scene(
                        results, self.recognizer, self.log, self.current_count, target_count, count_challenge, consecutive_challenge, last_clicked_tiaozhan,
                        mark_ready, mark_unready
                    )
                elif self.current_preset == "斗技":
                    stop_flag, self.current_count, consecutive_challenge, last_clicked_tiaozhan = dj.handle_scene(
                        results, self.recognizer, self.log, self.current_count, target_count, count_challenge, consecutive_challenge, last_clicked_tiaozhan,
                        hasattr(self.parent, 'dj_jinsheng_stop') and self.parent.dj_jinsheng_stop
                    )
                elif self.current_preset == "道馆":
                    stop_flag, self.current_count, consecutive_challenge, last_clicked_tiaozhan = dg.handle_scene(
                        results, self.recognizer, self.log, self.current_count, target_count, count_challenge, consecutive_challenge, last_clicked_tiaozhan
                    )
                elif self.current_preset == "困28单人":
                    stop_flag, self.current_count, consecutive_challenge, last_clicked_putong_boss, need_wait, switch_to_jjtp = k28.handle_scene(
                        results, self.recognizer, self.log, self.current_count, target_count, count_challenge, consecutive_challenge, last_clicked_putong_boss,
                        hasattr(self.parent, 'huijuan_mode') and self.parent.huijuan_mode
                    )
                    
                    # 检查是否需要切换到结界突破场景
                    if switch_to_jjtp:
                        self.log("切换到结界突破场景")
                        # 直接设置变量并调用on_preset_change来切换场景
                        self.current_preset_var.set("结界突破")
                        self.current_preset = "结界突破"
                        self.on_preset_change()
                        # 更新recognizer的参数
                        preset = self.presets[self.current_preset]
                        template_folder = os.path.join(self.png_base_folder, preset["folder"])
                        self.recognizer.png_folder = template_folder
                        self.recognizer.click_x = preset["click_x"]
                        self.recognizer.click_y = preset["click_y"]
                        self.recognizer.threshold = float(self.threshold_entry.get().strip())
                        # 更新循环变量
                        count_challenge = preset.get("count_challenge", True)
                        try:
                            target_count = int(self.target_count_var.get().strip())
                        except ValueError:
                            target_count = 200
                        # 重置相关变量
                        last_clicked_tiaozhan = False
                        # 继续循环，而不是返回，让下一轮使用新场景
                        continue
                elif self.current_preset == "困28队长":
                    stop_flag, self.current_count, consecutive_challenge, last_clicked_putong_boss, need_wait = k281.handle_scene(
                        results, self.recognizer, self.log, self.current_count, target_count, count_challenge, consecutive_challenge, last_clicked_putong_boss
                    )
                elif self.current_preset == "困28队员":
                    stop_flag, self.current_count, consecutive_challenge, last_clicked_tiaozhan = k280.handle_scene(
                        results, self.recognizer, self.log, self.current_count, target_count, count_challenge, consecutive_challenge, last_clicked_tiaozhan
                    )
                elif self.current_preset == "英杰试炼":
                    stop_flag, self.current_count, consecutive_challenge, last_clicked_tiaozhan = yjsl.handle_scene(
                        results, self.recognizer, self.log, self.current_count, target_count, count_challenge, consecutive_challenge, last_clicked_tiaozhan
                    )
                elif self.current_preset == "结界突破":
                    stop_flag, self.current_count, consecutive_challenge, last_clicked_tiaozhan, switch_to_k28 = jjtp.handle_scene(
                        results, self.recognizer, self.log, self.current_count, target_count, count_challenge, consecutive_challenge, last_clicked_tiaozhan, 
                        hasattr(self.parent, 'huijuan_mode') and self.parent.huijuan_mode
                    )
                    
                    # 检查是否需要切换到困28单人场景
                    if switch_to_k28:
                        self.log("切换到困28单人场景")
                        # 直接设置变量并调用on_preset_change来切换场景
                        self.current_preset_var.set("困28单人")
                        self.current_preset = "困28单人"
                        self.on_preset_change()
                        # 更新recognizer的参数
                        preset = self.presets[self.current_preset]
                        template_folder = os.path.join(self.png_base_folder, preset["folder"])
                        self.recognizer.png_folder = template_folder
                        self.recognizer.click_x = preset["click_x"]
                        self.recognizer.click_y = preset["click_y"]
                        self.recognizer.threshold = float(self.threshold_entry.get().strip())
                        # 更新循环变量
                        count_challenge = preset.get("count_challenge", True)
                        try:
                            target_count = int(self.target_count_var.get().strip())
                        except ValueError:
                            target_count = 200
                        # 重置困28相关变量
                        recognition_attempts = 0
                        last_clicked_putong_boss = False
                        # 继续循环，而不是返回，让下一轮使用新场景
                        continue
                elif self.current_preset == "活动爬塔":
                    stop_flag, self.current_count, consecutive_challenge, last_clicked_tiaozhan = hdpt.handle_scene(
                        results, self.recognizer, self.log, self.current_count, target_count, count_challenge, consecutive_challenge, last_clicked_tiaozhan
                    )
                
                if stop_flag:
                    # 非手动停止时播放提示音
                    if not self.manual_stop:
                        self.play_sound()
                    self.running = False
                    # 检查是否需要关闭加成
                    if hasattr(self.parent, 'close_jiacheng_enabled') and self.parent.close_jiacheng_enabled:
                        if self.current_preset in ["司机", "队员", "魂土单人"]:
                            self.log(f"挑战次数达成，等待{self.parent.close_jiacheng_wait}秒...")
                            time.sleep(self.parent.close_jiacheng_wait)
                            
                            # 收集需要执行关闭加成的标签
                            tabs_to_process = []
                            
                            # 如果是司机，还要包括所有队员
                            if self.current_preset == "司机":
                                # 先处理司机自己
                                tabs_to_process.append(self)
                                # 再添加所有队员标签
                                for tab in self.parent.tabs:
                                    if tab != self and hasattr(tab, 'current_preset') and tab.current_preset == "队员":
                                        tabs_to_process.append(tab)
                            else:
                                # 只处理当前标签
                                tabs_to_process.append(self)
                            
                            # 使用多线程同时执行每个标签的关闭加成
                            import threading
                            threads = []
                            
                            def process_tab(tab):
                                try:
                                    jiacheng_folder = os.path.join(self.png_base_folder, "jiacheng")
                                    if os.path.exists(jiacheng_folder):
                                        device = None
                                        if hasattr(tab, 'device_combo'):
                                            device = tab.device_combo.get()
                                        if hasattr(tab, 'recognizer') and tab.recognizer:
                                            device = tab.recognizer.device
                                        guanbijiacheng.handle_close_jiacheng(tab.recognizer, tab.log, jiacheng_folder, device)
                                        # 关闭加成完成后停止该标签的运行
                                        tab.stop_loop()
                                    else:
                                        tab.log("警告：未找到jiacheng文件夹")
                                except Exception as e:
                                    pass
                            
                            # 创建并启动所有线程
                            for tab in tabs_to_process:
                                thread = threading.Thread(target=process_tab, args=(tab,))
                                thread.start()
                                threads.append(thread)
                            
                            # 等待所有线程完成
                            for thread in threads:
                                thread.join()
                    break
                
                # 识别到图片执行点击后等待
                if need_wait:
                    # 困28单人和困28队长点击boss或putong后等待3秒
                    time.sleep(3)
                elif hasattr(self.recognizer, 'skip_sleep') and self.recognizer.skip_sleep:
                    self.recognizer.skip_sleep = False
                    time.sleep(1)
                else:
                    time.sleep(2)
            else:
                # 未识别到就每秒识别一次
                last_clicked_tiaozhan = False  # 重置连续点击状态
                
                # 根据当前场景调用对应的无识别处理函数
                if self.current_preset == "困28单人":
                    last_clicked_putong_boss = False  # 重置连续点击状态
                    recognition_attempts += 1
                    if recognition_attempts >= 5:
                        k28.handle_no_recognition(self.recognizer, self.log, self.recognizer.device)
                        recognition_attempts = 0  # 重置计数
                elif self.current_preset == "困28队长":
                    last_clicked_putong_boss = False  # 重置连续点击状态
                    recognition_attempts += 1
                    if recognition_attempts >= 5:
                        k281.handle_no_recognition(self.recognizer, self.log, self.recognizer.device)
                        recognition_attempts = 0  # 重置计数
                elif self.current_preset == "结界突破":
                    jjtp.handle_no_recognition(self.recognizer, self.log, self.recognizer.device)
                
                time.sleep(1)

        # 自然结束时也需要解锁控件
        gui_logger.info(f"[{self.tab_name}] 运行循环结束 | 场景: {self.current_preset} | 手动停止: {self.manual_stop}")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.unlock_controls()
    
    def stop_loop(self):
        gui_logger.info(f"[{self.tab_name}] 点击按钮: 停止")
        self.manual_stop = True  # 标记为手动停止
        self.running = False
        if self.recognizer:
            self.recognizer.running = False
        
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        # 解锁所有控件
        self.unlock_controls()
        
        preset = self.presets[self.current_preset]
        if preset.get("count_challenge", True) and self.recognizer:
            self.log(f"挑战次数: {self.recognizer.tiaozhan_count}")
        self.log("已停止")
        
        # 保存当前标签配置
        self.save_tab_config()

class AutoClickerUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YYS-AUTOv2.8")
        self.root.geometry("640x440")
        self.root.minsize(640, 440)  # 设置最小尺寸

        # 初始化标志
        self.initialized = False
        
        # 再次确保设置窗口图标（使用已准备好的 ICON_PATH）
        if ICON_PATH:
            try:
                self.root.iconbitmap(ICON_PATH)
            except:
                try:
                    self.root.iconbitmap(default=ICON_PATH)
                except:
                    pass
        
        self.png_base_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "png")
        
        self.presets = {
            "业原火": {
                "folder": "yyh",
                "click_x": 777,
                "click_y": 666,
                "threshold": 0.80,
                "count_challenge": True
            },
            "魂土单人": {
                "folder": "htdr",
                "click_x": 777,
                "click_y": 666,
                "threshold": 0.80,
                "count_challenge": True
            },
            "司机": {
                "folder": "sj",
                "click_x": 777,
                "click_y": 666,
                "threshold": 0.80,
                "count_challenge": True
            },
            "队员": {
                "folder": "dy",
                "click_x": 777,
                "click_y": 666,
                "threshold": 0.80,
                "count_challenge": False
            },
            "斗技": {
                "folder": "dj",
                "click_x": 777,
                "click_y": 666,
                "threshold": 0.80,
                "count_challenge": True
            },
            "道馆": {
                "folder": "dg",
                "click_x": 777,
                "click_y": 700,
                "threshold": 0.8,
                "count_challenge": False
            },
            "困28单人": {
                "folder": "k28",
                "click_x": 777,
                "click_y": 666,
                "threshold": 0.80,
                "count_challenge": True
            },
            "困28队长": {
                "folder": "k281",
                "click_x": 777,
                "click_y": 666,
                "threshold": 0.80,
                "count_challenge": True
            },
            "困28队员": {
                "folder": "k280",
                "click_x": 777,
                "click_y": 666,
                "threshold": 0.80,
                "count_challenge": False
            },
            "英杰试炼": {
                "folder": "yjsl",
                "click_x": 777,
                "click_y": 666,
                "threshold": 0.80,
                "count_challenge": True
            },
            "结界突破": {
                "folder": "jjtp",
                "click_x": 777,
                "click_y": 666,
                "threshold": 0.8,
                "count_challenge": False
            },
            "活动爬塔": {
                "folder": "hdpt",
                "click_x": 777,
                "click_y": 666,
                "threshold": 0.80,
                "count_challenge": True
            }
        }
        
        self.tab_count = 0
        self.tabs = []
        
        # 队员司机联动开关
        self.link_enabled = False
        
        # 关闭加成设置
        self.close_jiacheng_enabled = False
        self.close_jiacheng_wait = 30  # 默认30秒
        
        # 绘卷模式设置
        self.huijuan_mode = False
        
        # 斗技段位晋升结束程序设置
        self.dj_jinsheng_stop = False

        # 提示音设置
        self.sound_enabled = False
        self.sound_file = ""  # 选中的音效文件名
        
        # 日志设置
        self.logging_enabled = False
        
        # ADB设置
        self.adb_ip = "127.0.0.1"
        self.adb_port = "16384"
        
        # 加载保存的配置
        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        self.saved_config = self.load_config()

        # 恢复窗口位置（延迟到窗口显示后执行，避免被窗口管理器覆盖）
        if "window_geometry" in self.saved_config:
            saved_geometry = self.saved_config["window_geometry"]
            self.root.after(0, lambda g=saved_geometry: self.root.geometry(g))

        self.setup_ui()

        # 输入法控制：默认禁用，仅输入框获得焦点时启用
        _init_ime(self.root.winfo_id())
        self.root.bind('<FocusIn>', _on_root_focus_in, add='+')
        self.root.bind('<Button-1>', self._on_root_click)  # 点击空白区域取消输入框聚焦
        self.root.bind_class('Entry', '<FocusIn>', _on_entry_focus_in, add='+')
        self.root.bind_class('Entry', '<FocusOut>', _on_entry_focus_out, add='+')
        self.root.bind_class('Text', '<FocusIn>', _on_entry_focus_in, add='+')
        self.root.bind_class('Text', '<FocusOut>', _on_entry_focus_out, add='+')
        self.root.bind_class('TEntry', '<FocusIn>', _on_entry_focus_in, add='+')
        self.root.bind_class('TEntry', '<FocusOut>', _on_entry_focus_out, add='+')
        self.root.bind_class('TCombobox', '<FocusIn>', _on_entry_focus_in, add='+')
        self.root.bind_class('TCombobox', '<FocusOut>', _on_entry_focus_out, add='+')

        self.restore_tab_selection()

        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)

        # 标记初始化完成
        self.initialized = True

    def load_config(self):
        # 加载保存的配置
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 加载队员司机联动设置
                    if "link_enabled" in config:
                        self.link_enabled = config["link_enabled"]
                    # 加载关闭加成设置
                    if "close_jiacheng_enabled" in config:
                        self.close_jiacheng_enabled = config["close_jiacheng_enabled"]
                    if "close_jiacheng_wait" in config:
                        self.close_jiacheng_wait = config["close_jiacheng_wait"]
                    # 加载绘卷模式设置
                    if "huijuan_mode" in config:
                        self.huijuan_mode = config["huijuan_mode"]
                    # 加载斗技段位晋升结束程序设置
                    if "dj_jinsheng_stop" in config:
                        self.dj_jinsheng_stop = config["dj_jinsheng_stop"]
                    # 加载提示音设置
                    if "sound_enabled" in config:
                        self.sound_enabled = config["sound_enabled"]
                    if "sound_file" in config:
                        self.sound_file = config["sound_file"]
                    # 加载日志设置
                    if "logging_enabled" in config:
                        self.logging_enabled = config["logging_enabled"]
                        from adb import set_logging_enabled
                        set_logging_enabled(self.logging_enabled)
                    # 加载ADB设置
                    if "adb_ip" in config:
                        self.adb_ip = config["adb_ip"]
                    if "adb_port" in config:
                        self.adb_port = config["adb_port"]
                    return config
            except Exception as e:
                pass
        return {"last_tab": 0, "tabs": {}}
    
    def save_config(self):
        # 保存当前配置
        try:
            # 保存队员司机联动设置
            self.saved_config["link_enabled"] = self.link_enabled
            # 保存关闭加成设置
            self.saved_config["close_jiacheng_enabled"] = self.close_jiacheng_enabled
            self.saved_config["close_jiacheng_wait"] = self.close_jiacheng_wait
            # 保存绘卷模式设置
            self.saved_config["huijuan_mode"] = self.huijuan_mode
            # 保存斗技段位晋升结束程序设置
            self.saved_config["dj_jinsheng_stop"] = self.dj_jinsheng_stop
            # 保存提示音设置
            self.saved_config["sound_enabled"] = self.sound_enabled
            self.saved_config["sound_file"] = self.sound_file
            # 保存日志设置
            self.saved_config["logging_enabled"] = self.logging_enabled
            # 保存ADB设置
            self.saved_config["adb_ip"] = self.adb_ip
            self.saved_config["adb_port"] = self.adb_port
            # 保存窗口位置
            try:
                self.saved_config["window_geometry"] = self.root.geometry()
            except:
                pass
            # 保存当前选中的标签索引
            try:
                current_index = self.notebook.index(self.notebook.select())
                self.saved_config["last_tab"] = current_index
            except:
                pass
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.saved_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            pass
    
    def _kill_adb_and_exit(self):
        """关闭ADB进程并退出程序"""
        gui_logger.info("点击菜单: 关闭ADB并退出")
        import subprocess
        # 先停止所有标签任务
        self.stop_all_tabs()
        # 关闭ADB服务进程
        try:
            adb_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "platform-tools", "adb.exe")
            if not os.path.exists(adb_path):
                adb_path = "adb"
            subprocess.run([adb_path, "kill-server"], capture_output=True, timeout=10)
        except:
            pass
        # 退出程序
        self.on_window_close()

    def on_window_close(self):
        # 窗口关闭时恢复输入法并保存配置
        _do_enable_ime()
        self.save_config()
        self.root.destroy()
    
    def restore_tab_selection(self):
        # 恢复上次选择的标签（注意：第0位是设置标签）
        last_tab = self.saved_config.get("last_tab", 1)

        # 确保last_tab在有效范围内
        if last_tab >= 0 and last_tab < self.notebook.index('end'):
            # 使用after方法确保在UI完全初始化后再选择标签
            def select_tab():
                try:
                    self.notebook.select(last_tab)
                except Exception as e:
                    pass
            self.root.after(500, select_tab)
        else:
            pass
    
    def on_tab_changed(self, event):
        # 只有在初始化完成后才处理标签切换事件
        if not self.initialized:
            return
        
        # 标签切换时保存当前标签索引（注意：第0位是设置标签）
        current_index = self.notebook.index(self.notebook.select())

        self.saved_config["last_tab"] = current_index

        # 同时保存当前标签的配置（只有当是设备标签时）
        if current_index > 0 and (current_index - 1) < len(self.tabs):
            self.tabs[current_index - 1].save_tab_config()

        self.save_config()
    
    def _create_menubar(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)

        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="关闭ADB并退出", command=self._kill_adb_and_exit)
        file_menu.add_separator()
        file_menu.add_command(label="退出程序 (Alt+F4)", command=self.on_window_close)
        menubar.add_cascade(label="文件(F)", menu=file_menu, underline=3)

        # 设置菜单
        settings_menu = tk.Menu(menubar, tearoff=False)

        # 功能设置二级菜单
        func_menu = tk.Menu(settings_menu, tearoff=False)
        func_menu.add_checkbutton(label="队员司机联动",
                                  variable=self.settings_tab.settings_link_var,
                                  command=self.settings_tab.save_settings)
        func_menu.add_checkbutton(label="绘卷模式",
                                  variable=self.settings_tab.settings_huijuan_mode_var,
                                  command=self.settings_tab.save_settings)
        func_menu.add_checkbutton(label="斗技段位晋升结束程序",
                                  variable=self.settings_tab.settings_dj_jinsheng_stop_var,
                                  command=self.settings_tab.save_settings)
        func_menu.add_checkbutton(label="挑战结束后关闭御魂加成",
                                  variable=self.settings_tab.settings_close_jiacheng_var,
                                  command=self.settings_tab.save_settings)
        func_menu.add_separator()
        func_menu.add_command(label="设置关闭加成等待秒数",
                              command=self.settings_tab._set_close_jiacheng_wait)
        settings_menu.add_cascade(label="功能设置", menu=func_menu)

        # 日志二级菜单
        log_menu = tk.Menu(settings_menu, tearoff=False)
        self._log_menu = log_menu
        log_menu.add_checkbutton(label="启用日志记录",
                                 variable=self.settings_tab.settings_logging_var,
                                 command=self.settings_tab.save_settings)
        log_menu.add_separator()
        log_menu.add_command(label="打开日志文件夹", command=self.settings_tab._open_log_folder)
        log_menu.add_command(label="清空日志", command=self.settings_tab._clear_logs)
        settings_menu.add_cascade(label="日志", menu=log_menu)

        # 软件更新二级菜单
        update_menu = tk.Menu(settings_menu, tearoff=False)
        update_menu.add_command(label="复制网盘密码", command=self.settings_tab._copy_password)
        update_menu.add_command(label="更新软件", command=self.settings_tab._open_update_link)
        update_menu.add_command(label="GitHub仓库", command=self.settings_tab._open_github)
        settings_menu.add_cascade(label="软件更新", menu=update_menu)

        menubar.add_cascade(label="设置(T)", menu=settings_menu, underline=3)

        # 标签菜单
        tab_menu = tk.Menu(menubar, tearoff=False)
        tab_menu.add_command(label="新建标签 (Ctrl+T)", command=self.add_new_tab)
        tab_menu.add_command(label="删除当前标签 (Ctrl+W)", command=self.delete_current_tab)
        tab_menu.add_command(label="修改标签名字 (F2)", command=self.rename_current_tab)
        tab_menu.add_separator()
        tab_menu.add_command(label="清除全部标签设备", command=self.clear_all_devices)
        menubar.add_cascade(label="标签(B)", menu=tab_menu, underline=3)

        # 运行菜单
        run_menu = tk.Menu(menubar, tearoff=False)
        run_menu.add_command(label="开始当前标签 (R)", command=self._menu_start_current)
        run_menu.add_command(label="停止当前标签 (S)", command=self._menu_stop_current)
        run_menu.add_separator()
        run_menu.add_command(label="全部开始 (F5)", command=self.start_all_tabs)
        run_menu.add_command(label="全部停止 (F6)", command=self.stop_all_tabs)
        menubar.add_cascade(label="运行(R)", menu=run_menu, underline=3)

        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="打开使用说明文档", command=self._open_doc_folder)
        help_menu.add_command(label="快捷键说明", command=self._show_shortcuts)
        help_menu.add_command(label="UU远程官网", command=self._open_uu_remote)
        # Bug反馈二级菜单
        bug_menu = tk.Menu(help_menu, tearoff=False)
        bug_menu.add_command(label="复制QQ交流群号", command=self.settings_tab._copy_qq_group)
        bug_menu.add_command(label="复制作者邮箱", command=self.settings_tab._copy_email)
        help_menu.add_cascade(label="Bug反馈与建议", menu=bug_menu)
        help_menu.add_command(label="关于 YYS-AUTO", command=self._show_about)
        menubar.add_cascade(label="帮助(H)", menu=help_menu, underline=3)

        self.root.config(menu=menubar)

        # 快捷键绑定
        self.root.bind('<Control-t>', lambda e: self.add_new_tab())
        self.root.bind('<Control-w>', lambda e: self.delete_current_tab())
        self.root.bind('<F2>', lambda e: self.rename_current_tab())
        self.root.bind_all('<Key-r>', lambda e: self._safe_key('start'))
        self.root.bind_all('<Key-R>', lambda e: self._safe_key('start'))
        self.root.bind_all('<Key-s>', lambda e: self._safe_key('stop'))
        self.root.bind_all('<Key-S>', lambda e: self._safe_key('stop'))
        self.root.bind('<F5>', lambda e: self.start_all_tabs())
        self.root.bind('<F6>', lambda e: self.stop_all_tabs())
        # 数字键切换标签：1→设置，2-9→设备标签
        for i in range(1, 10):
            self.root.bind_all(f'<Key-{i}>', lambda e, idx=i: self._safe_key('tab', idx))

    def _on_root_click(self, event):
        """点击空白区域时取消输入框聚焦"""
        if not isinstance(event.widget, (tk.Entry, tk.Text, ttk.Entry, ttk.Combobox)):
            self.root.focus_set()

    def _safe_key(self, action, idx=None):
        """只在焦点不在输入框时响应快捷键"""
        focused = self.root.focus_get()
        if isinstance(focused, (tk.Entry, tk.Text, ttk.Entry)):
            return
        if action == 'start':
            self._menu_start_current()
        elif action == 'stop':
            self._menu_stop_current()
        elif action == 'tab':
            self._switch_to_tab(idx)

    def _show_about(self):
        """显示关于对话框，居中于主窗口"""
        gui_logger.info("点击菜单: 关于")
        top = tk.Toplevel(self.root)
        top.title("关于")
        top.resizable(False, False)
        top.transient(self.root)
        top.grab_set()
        
        # 标题区
        ttk.Label(top, text="YYS-AUTO  v2.8", font=('Microsoft YaHei', 16, 'bold')).pack(padx=40, pady=(20, 2))
        ttk.Label(top, text="阴阳师自动化辅助工具", font=('Microsoft YaHei', 9), foreground="#888").pack(padx=40, pady=(0, 8))
        
        # 装饰分隔线
        ttk.Label(top, text="·  ·  ✦  ·  ·", font=('Microsoft YaHei', 8), foreground="#ccc").pack(pady=2)
        
        # 信息区
        info_frame = tk.Frame(top, bg="#f8f8f8", padx=20, pady=12)
        info_frame.pack(fill=tk.X, padx=25, pady=(8, 0))
        
        ttk.Label(info_frame, text="交流群", font=('Microsoft YaHei', 8), foreground="#aaa").pack()
        tk.Label(info_frame, text="647871264", font=('Microsoft YaHei', 12, 'bold'), fg="#2196F3", bg="#f8f8f8", cursor="hand2").pack(pady=(0, 6))
        
        ttk.Label(info_frame, text="", font=('Microsoft YaHei', 1)).pack()  # 间距
        
        ttk.Label(info_frame, text="制作者", font=('Microsoft YaHei', 8), foreground="#aaa").pack()
        tk.Label(info_frame, text="凌ling妻", font=('Microsoft YaHei', 11, 'bold'), fg="#333", bg="#f8f8f8").pack(pady=(0, 2))
        
        tk.Label(info_frame, text="✦  Thanks to  Trae  ✦", font=('Microsoft YaHei', 8), fg="#bbb", bg="#f8f8f8").pack(pady=(4, 0))
        
        ttk.Button(top, text="确  定", command=top.destroy, width=12).pack(pady=(14, 18))

        # 居中于主窗口
        top.update_idletasks()
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_w = self.root.winfo_width()
        main_h = self.root.winfo_height()
        top_w = top.winfo_width()
        top_h = top.winfo_height()
        x = main_x + (main_w - top_w) // 2
        y = main_y + (main_h - top_h) // 2
        top.geometry(f"+{x}+{y}")

    def _show_shortcuts(self):
        """显示快捷键说明窗口，居中于主窗口"""
        gui_logger.info("点击菜单: 快捷键说明")
        top = tk.Toplevel(self.root)
        top.title("快捷键说明")
        top.resizable(False, False)
        top.transient(self.root)
        top.grab_set()

        shortcuts = [
            ("Alt+F4", "退出程序"),
            ("Ctrl+T", "新建标签"),
            ("Ctrl+W", "删除当前标签"),
            ("F2", "修改标签名字"),
            ("R", "运行当前标签"),
            ("S", "停止当前标签"),
            ("F5", "全部开始"),
            ("F6", "全部停止"),
            ("1", "切换到设置页"),
            ("2 ~ 9", "切换到对应设备标签"),
        ]

        ttk.Label(top, text="快捷键说明", font=('Microsoft YaHei', 12, 'bold')).pack(padx=30, pady=(15, 10))

        frame = ttk.Frame(top)
        frame.pack(padx=20, pady=(0, 10))

        for key, desc in shortcuts:
            row = ttk.Frame(frame)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=key, font=('Microsoft YaHei', 10, 'bold'), width=12, anchor=tk.E).pack(side=tk.LEFT, padx=(0, 15))
            ttk.Label(row, text=desc, font=('Microsoft YaHei', 10)).pack(side=tk.LEFT)

        ttk.Button(top, text="确定", command=top.destroy, width=10).pack(pady=(5, 15))

        # 居中于主窗口
        top.update_idletasks()
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_w = self.root.winfo_width()
        main_h = self.root.winfo_height()
        top_w = top.winfo_width()
        top_h = top.winfo_height()
        x = main_x + (main_w - top_w) // 2
        y = main_y + (main_h - top_h) // 2
        top.geometry(f"+{x}+{y}")

    def _open_uu_remote(self):
        """打开UU远程官网"""
        gui_logger.info("点击菜单: UU远程官网")
        import webbrowser
        webbrowser.open("https://uuyc.163.com/")

    def _open_doc_folder(self):
        """打开使用说明文档文件夹"""
        gui_logger.info("点击菜单: 打开使用说明文档")
        doc_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "使用文档第一次使用必看")
        try:
            if os.path.exists(doc_folder):
                if sys.platform.startswith('win'):
                    os.startfile(doc_folder)
                else:
                    import subprocess
                    subprocess.Popen(['xdg-open', doc_folder])
            else:
                if self.tabs:
                    self.tabs[0].log("使用说明文档文件夹不存在")
        except Exception as e:
            if self.tabs:
                self.tabs[0].log(f"打开文档文件夹失败: {e}")

    def _menu_start_current(self):
        """菜单栏：开始当前标签"""
        gui_logger.info("点击菜单/快捷键: 开始当前标签")
        current_idx = self.notebook.index("current")
        tab_idx = current_idx - 1  # 第一个标签是设置页
        if 0 <= tab_idx < len(self.tabs):
            self.tabs[tab_idx].start_loop()

    def _menu_stop_current(self):
        """菜单栏：停止当前标签"""
        gui_logger.info("点击菜单/快捷键: 停止当前标签")
        current_idx = self.notebook.index("current")
        tab_idx = current_idx - 1  # 第一个标签是设置页
        if 0 <= tab_idx < len(self.tabs):
            self.tabs[tab_idx].stop_loop()

    def _switch_to_tab(self, num):
        """数字键切换标签：1→设置，2-9→设备标签"""
        gui_logger.info(f"快捷键: 切换到标签 {num}")
        if num == 1:
            self.notebook.select(0)  # 设置页
        else:
            tab_idx = num - 2  # 2→tabs[0], 3→tabs[1]...
            if 0 <= tab_idx < len(self.tabs):
                self.notebook.select(tab_idx + 1)  # +1 跳过设置页

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 顶部标签栏
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # 标签切换时保存当前标签索引
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # 首先添加设置标签
        self.settings_tab = SettingsTab(self)
        self.notebook.add(self.settings_tab.frame, text="设置")

        # 创建菜单栏（在settings_tab创建之后，因为菜单需要引用settings_tab的变量）
        self._create_menubar()

        # 从配置中动态加载标签
        saved_tabs = self.saved_config.get("tabs", {})

        if saved_tabs:
            # 有保存的配置，按索引顺序加载标签（跳过索引0）
            # 先将tab索引转换为整数并排序
            tab_indices = sorted([int(k) for k in saved_tabs.keys() if int(k) > 0])
            self.tab_count = 0

            for tab_idx in tab_indices:
                self.tab_count = tab_idx
                tab_config = saved_tabs.get(str(tab_idx), {})
                tab_name = tab_config.get("tab_name", f"设备{tab_idx}")

                device_tab = DeviceTab(self, tab_name, self.png_base_folder, self.presets)
                device_tab.tab_index = tab_idx
                self.notebook.add(device_tab.frame, text=tab_name)
                self.tabs.append(device_tab)

                # 加载标签配置
                if tab_config:
                    device_tab.load_tab_config(tab_config)
        else:
            # 没有保存的配置，创建默认的设备1标签
            self.tab_count = 1
            device_tab = DeviceTab(self, "设备1", self.png_base_folder, self.presets)
            device_tab.tab_index = 1
            self.notebook.add(device_tab.frame, text="设备1")
            self.tabs.append(device_tab)

        # 恢复上次选择的标签
        self.restore_tab_selection()

        # 统一处理所有标签的设备选择（子线程，不阻塞UI）
        self._setup_all_devices()

        # 禁用窗口大小调整（放在setup_ui末尾，所有widget布局完毕后设置，
        # 避免在__init__开头设置时改变窗口框架样式干扰Notebook初始渲染）
        self.root.resizable(False, False)
    
    def _setup_all_devices(self):
        # 锁定UI并提示ADB正在启动
        self.settings_tab.lock_adb_section()
        for tab in self.tabs:
            tab.lock_for_adb_starting()
            tab.log("ADB正在启动中，请稍候...")

        # 在子线程中执行ADB设备刷新，避免阻塞主线程
        def _worker():
            try:
                for tab in self.tabs:
                    try:
                        tab.refresh_devices()
                    except Exception as e:
                        pass
            except Exception as e:
                pass
            # 回到主线程解锁UI并提示
            self.root.after(0, self._on_adb_started)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_adb_started(self):
        """ADB启动完成后的回调"""
        gui_logger.info("ADB启动完成")
        self.settings_tab.unlock_adb_section()
        for tab in self.tabs:
            tab.unlock_after_adb_started()
            tab.log("ADB已启动")
    
    def add_new_tab(self):
        gui_logger.info("点击按钮: 新建标签")
        self.tab_count += 1
        # 先检查配置中是否有标签名称（注意设置标签占了第0位，tab_count从1开始）
        tab_config = self.saved_config.get("tabs", {}).get(str(self.tab_count), {})
        tab_name = tab_config.get("tab_name", f"设备{self.tab_count}")

        try:
            device_tab = DeviceTab(self, tab_name, self.png_base_folder, self.presets)
            device_tab.tab_index = self.tab_count  # 设置标签索引
            self.notebook.add(device_tab.frame, text=tab_name)
            self.tabs.append(device_tab)

            # 加载保存的标签配置
            if tab_config:
                device_tab.load_tab_config(tab_config)

            # 选择新添加的标签（注意设置标签占了第0位）
            new_tab_index = len(self.tabs)  # notebook的索引：0是设置，1是第一个设备，2是第二个...
            self.notebook.select(new_tab_index)
        except Exception as e:
            pass

    def clear_all_devices(self):
        gui_logger.info("点击按钮: 清除全部标签设备")
        try:
            # 先清空所有标签的设备选择
            for tab in self.tabs:
                try:
                    if tab.recognizer:
                        tab.recognizer.device = None
                    # 清空选择框和 saved_device
                    tab.device_combo.set('')
                    tab.saved_device = None
                    tab.log("已清除设备")
                except Exception as e:
                    pass
            
            # 然后刷新所有标签的设备列表，确保设备排除被重置
            for tab in self.tabs:
                try:
                    tab.refresh_devices()
                except Exception as e:
                    pass
            
            if self.tabs:
                self.tabs[0].log("已清空全部设备")
        except Exception as e:
            pass

    def start_all_tabs(self):
        """一键开始所有标签任务"""
        gui_logger.info("点击按钮: 全部开始")
        for tab in self.tabs:
            if hasattr(tab, 'device_combo') and tab.device_combo.get() and not tab.running:
                try:
                    tab.start_loop()
                except Exception as e:
                    pass
        if self.tabs:
            self.tabs[0].log("已启动全部标签")

    def stop_all_tabs(self):
        """一键停止所有标签任务"""
        gui_logger.info("点击按钮: 全部停止")
        for tab in self.tabs:
            if tab.running:
                try:
                    tab.stop_loop()
                except Exception as e:
                    pass
        if self.tabs:
            self.tabs[0].log("已停止全部标签")
    
    def delete_current_tab(self):
        gui_logger.info("点击按钮: 删除当前标签")
        try:
            # 获取当前选中的标签索引（注意：第0位是设置标签）
            current_index = self.notebook.index(self.notebook.select())

            # 检查是否是设置标签
            if current_index == 0:
                if len(self.tabs) > 0:
                    self.tabs[0].log("设置标签不可删除")
                return

            # 设备标签索引是从1开始的，转换为tabs数组的索引（tabs数组不包含设置标签）
            tab_array_index = current_index - 1

            if tab_array_index < 0 or tab_array_index >= len(self.tabs):
                return

            if len(self.tabs) <= 1:
                if self.tabs:
                    self.tabs[0].log("至少保留一个标签")
                return

            # 获取当前标签
            current_tab = self.tabs[tab_array_index]

            # 如果正在运行，停止
            if current_tab.running:
                current_tab.stop_loop()

            # 从notebook中删除
            self.notebook.forget(current_index)

            # 从列表中删除
            self.tabs.pop(tab_array_index)

            # 删除保存的配置
            if str(current_tab.tab_index) in self.saved_config.get("tabs", {}):
                del self.saved_config["tabs"][str(current_tab.tab_index)]
                self.save_config()

            current_tab.frame.destroy()

            if self.tabs:
                self.tabs[0].log("已删除标签")
        except Exception as e:
            pass
    
    def rename_current_tab(self):
        gui_logger.info("点击按钮: 修改标签名字")
        try:
            # 获取当前选中的标签索引（注意：第0位是设置标签）
            current_index = self.notebook.index(self.notebook.select())

            # 检查是否是设置标签
            if current_index == 0:
                if len(self.tabs) > 0:
                    self.tabs[0].log("设置标签不可改名")
                return

            # 设备标签索引是从1开始的，转换为tabs数组的索引
            tab_array_index = current_index - 1

            if tab_array_index < 0 or tab_array_index >= len(self.tabs):
                return

            current_tab = self.tabs[tab_array_index]

            # 调用DeviceTab的弹出窗口方法
            current_tab.show_rename_tab_dialog()
        except Exception as e:
            pass


def main():
    # 使用普通 Tk
    root = tk.Tk()
    
    # 先尝试设置窗口图标
    if ICON_PATH:
        try:
            root.iconbitmap(ICON_PATH)
        except:
            try:
                root.iconbitmap(default=ICON_PATH)
            except:
                pass
    
    app = AutoClickerUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
