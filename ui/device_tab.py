"""单个设备标签页：设备选择、运行参数、场景选择、运行日志与运行控制。"""

from __future__ import annotations

import os
import threading
import time
import tkinter as tk
from tkinter import scrolledtext, ttk

from adb import ADBManager, get_gui_logger
from image_recognizer import ImageRecognizer
from notification import send_complete_notification, send_error_notification
from scenes.scene_api import SceneState
from ui.scene_runner import SceneRunnerMixin
from ui.widgets import ToolTip

gui_logger = get_gui_logger()

# 识别阈值的兜底值（输入框内容非法时使用）
DEFAULT_THRESHOLD = 0.8
# 目标挑战次数的兜底值
DEFAULT_TARGET_COUNT = 200

# 运行期间需要禁用的控件（unlock_controls 用同一份列表恢复）。
# "全部锁定"不包含 start_btn / stop_btn——它们由 main 循环单独控制。
FULL_LOCK_WIDGETS = (
    'device_combo', 'threshold_entry', 'target_count_entry', 'match_workers_entry',
    'refresh_btn', 'clear_device_btn', 'reset_btn', 'copy_params_btn', 'copy_scene_btn',
)

# 重启 ADB 期间需要禁用的控件
ADB_LOCK_WIDGETS = (
    'device_combo', 'refresh_btn', 'clear_device_btn', 'start_btn', 'start_all_btn',
)


class DeviceTab(SceneRunnerMixin):
    def __init__(self, parent, tab_name, png_base_folder, presets):
        """初始化标签页：建控件变量、搭界面、加载保存的配置。"""
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
        self.match_workers_var = tk.StringVar(value="1")   # 默认1线程
        self.current_count = 0
        self.tab_index = 0  # 标签索引
        self.saved_device = None  # 保存的设备（用于初始化）
        self.preset_thresholds = {}  # 每个场景记住用户设置的阈值
        
        # 队员准备状态（仅用于队员场景）
        self.is_ready = False
        
        # 场景使用计时
        self.scene_start_time = None
        
        # 随机暂停状态：下次进入随机暂停的时间戳（None=未启用/未调度）
        self.zoushen_next_trigger_time = None
        
        self.setup_ui(tab_name)
    
    def save_tab_config(self):
        """把本标签的设备、场景与运行参数写进全局配置。"""
        # 只保存tab_index>0的设备标签（tab0是设置标签，不保存）
        if not hasattr(self, 'tab_index') or self.tab_index <= 0:
            return
        # 保存当前选择的设备
        current_device = self.device_combo.get() if hasattr(self, 'device_combo') else ''
        config = {
            "tab_name": self.tab_name if hasattr(self, 'tab_name') else "",
            "preset": self.current_preset,
            "target_count": self.target_count_var.get(),
            "match_workers": self.match_workers_var.get(),
            "threshold": self.threshold_entry.get(),
            "preset_thresholds": self.preset_thresholds,
            "device": current_device
        }
        self.parent.saved_config.setdefault("tabs", {})[str(self.tab_index)] = config
        self.parent.save_config()

    def load_tab_config(self, config):
        """从配置恢复本标签的设备、场景与运行参数。"""
        # 立即设置 tab_name，避免延迟导致丢失
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
        if config.get("target_count"):
            self.target_count_var.set(config["target_count"])
        if config.get("match_workers"):
            self.match_workers_var.set(config["match_workers"])
        if config.get("threshold"):
            self.threshold_entry.delete(0, tk.END)
            self.threshold_entry.insert(0, config["threshold"])
        if config.get("preset_thresholds"):
            self.preset_thresholds = config["preset_thresholds"]
    
    def _set_tab_name(self, tab_name):
        """设置标签名并同步到 notebook 与标题。"""
        self.tab_name = tab_name
        try:
            self.parent.notebook.tab(self.frame, text=tab_name)
        except:
            pass
        self._update_title_label()
    
    def _update_title_label(self):
        """刷新标题上的「版本号|标签名」。"""
        # 标题处显示 版本号|标签名
        if hasattr(self, 'title_label'):
            self.title_label.config(text=f"YYS-AUTOv2.17|{self.tab_name}")
    
    def on_tab_name_changed(self, event=None):
        """标签名变化回调：弹出重命名对话框。"""
        # 标签名称改变时保存 - 改为弹出窗口方式
        self.show_rename_tab_dialog()
    
    def show_rename_tab_dialog(self):
        """弹出修改标签名称的对话框。"""
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
            """应用新的标签名并保存配置。"""
            new_name = entry.get().strip()
            if new_name:
                gui_logger.info(f"[{self.tab_name}] 标签重命名为: {new_name}")
                self.tab_name = new_name
                try:
                    self.parent.notebook.tab(self.frame, text=new_name)
                    self.tab_name_label.config(text=new_name)
                except:
                    pass
                self._update_title_label()
                self.save_tab_config()
            dialog.destroy()
        
        def on_enter(event):
            """回车等同于点「确定」。"""
            confirm_rename()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="确定", command=confirm_rename).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        entry.bind("<Return>", on_enter)
        entry.bind("<Escape>", lambda e: dialog.destroy())
        dialog.bind("<Escape>", lambda e: dialog.destroy())
    
    def _set_device_combo(self, device):
        """把设备下拉框的选中项设为指定设备。"""
        try:
            if hasattr(self, 'device_combo') and device in self.device_combo["values"]:
                self.device_combo.current(self.device_combo["values"].index(device))
        except:
            pass

    def setup_ui(self, tab_name):
        """搭建本标签界面：设备卡片、场景选择、日志区、运行控制。"""
        main_frame = ttk.Frame(self.frame, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 顶部：标题
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=2)
        self.title_label = ttk.Label(title_frame, text=f"YYS-AUTOv2.17|{self.tab_name}", font=('Microsoft YaHei', 16, 'bold'))
        self.title_label.pack(anchor=tk.CENTER)
        
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
        q_btn = ttk.Label(threshold_frame, text="❓", font=('Microsoft YaHei', 9), cursor="hand2")
        q_btn.pack(side=tk.LEFT, padx=0)
        ToolTip(q_btn, "识别阈值控制图片匹配的严格程度。\n"
                       "阈值越低，匹配越宽松（容易误识别）；\n"
                       "阈值越高，匹配越严格（可能漏识别）。\n"
                       "建议范围：0.7 ~ 0.9，默认 0.8。")
        self.threshold_entry = ttk.Entry(threshold_frame, width=6)
        self.threshold_entry.pack(side=tk.LEFT, padx=2)
        self.threshold_entry.bind('<FocusOut>', lambda e: self.save_tab_config())
        
        # 运行次数
        count_frame = ttk.Frame(device_card)
        count_frame.pack(fill=tk.X, pady=2)
        ttk.Label(count_frame, text="运行次数：", font=('Microsoft YaHei', 9)).pack(side=tk.LEFT, padx=2)
        q_btn2 = ttk.Label(count_frame, text="❓", font=('Microsoft YaHei', 9), cursor="hand2")
        q_btn2.pack(side=tk.LEFT, padx=0)
        ToolTip(q_btn2, "当前设备标签页脚本的循环执行次数。\n"
                        "设为 0 表示无限循环，直到手动停止。")
        self.target_count_entry = ttk.Entry(count_frame, width=6, textvariable=self.target_count_var)
        self.target_count_entry.pack(side=tk.LEFT, padx=2)
        self.target_count_entry.bind('<FocusOut>', lambda e: self.save_tab_config())
        
        # 匹配线程数
        workers_frame = ttk.Frame(device_card)
        workers_frame.pack(fill=tk.X, pady=2)
        ttk.Label(workers_frame, text="匹配线程：", font=('Microsoft YaHei', 9)).pack(side=tk.LEFT, padx=2)
        q_btn3 = ttk.Label(workers_frame, text="❓", font=('Microsoft YaHei', 9), cursor="hand2")
        q_btn3.pack(side=tk.LEFT, padx=0)
        ToolTip(q_btn3, "模板匹配的并行线程数。\n"
                        "1 = 单线程（默认，兼容性最好）；\n"
                        "2~8 = 多线程并行匹配，显著提升识别速度。\n"
                        "OpenCV 的模板匹配会释放 GIL，多线程可真正并行。\n"
                        "建议：CPU 核心多时设 4~8，老设备保持 1。\n"
                        f"当前 CPU 核心数：{os.cpu_count() or '未知'}")
        self.match_workers_entry = ttk.Entry(workers_frame, width=6, textvariable=self.match_workers_var)
        self.match_workers_entry.pack(side=tk.LEFT, padx=2)
        self.match_workers_entry.bind('<FocusOut>', lambda e: self.save_tab_config())
        
        # 重置默认 & 一键应用按钮（同一行）
        btn_frame = ttk.Frame(device_card)
        btn_frame.pack(fill=tk.X, padx=2, pady=5)
        self.reset_btn = ttk.Button(btn_frame, text="重置默认", command=self.reset_defaults)
        self.reset_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        self.copy_params_btn = ttk.Button(btn_frame, text="一键应用到所有", command=self.copy_run_params)
        self.copy_params_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))
        
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
        
        # 复制场景选择按钮
        self.copy_scene_btn = ttk.Button(scene_card, text="一键应用到所有", command=self.copy_scene_selection)
        self.copy_scene_btn.pack(fill=tk.X, padx=2, pady=(5, 0))
        
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
        """把运行参数恢复成当前场景的预设默认值。"""
        gui_logger.info(f"[{self.tab_name}] 点击按钮: 重置默认")
        self.target_count_var.set("200")
        self.match_workers_var.set("1")
        self.preset_thresholds = {}  # 清除所有场景的阈值记忆
        # 直接用预设默认值设置阈值，避开on_preset_change的保存恢复逻辑
        preset = self._preset_config()
        self.threshold_entry.delete(0, tk.END)
        self.threshold_entry.insert(0, str(preset["threshold"]))
        self.save_tab_config()
        self.log("已重置默认参数")
    
    def copy_run_params(self):
        """将当前标签的运行参数（识别阈值、运行次数）复制到所有设备控制标签"""
        gui_logger.info(f"[{self.tab_name}] 点击按钮: 复制运行参数")
        threshold = self.threshold_entry.get().strip()
        target_count = self.target_count_var.get()
        match_workers = self.match_workers_var.get()
        applied = 0
        skipped = 0
        for tab in self.parent.tabs:
            if tab is self:
                continue
            if tab.running:
                skipped += 1
                continue
            tab.threshold_entry.delete(0, tk.END)
            tab.threshold_entry.insert(0, threshold)
            tab.target_count_var.set(target_count)
            tab.match_workers_var.set(match_workers)
            tab.save_tab_config()
            tab.log(f"运行参数已同步：阈值={threshold}，次数={target_count}，线程={match_workers}")
            applied += 1
        msg = f"已将运行参数应用到 {applied} 个标签"
        if skipped:
            msg += f"（{skipped} 个运行中标签已跳过）"
        self.log(msg)

    def copy_scene_selection(self):
        """将当前标签的场景选择复制到所有设备控制标签"""
        gui_logger.info(f"[{self.tab_name}] 点击按钮: 复制场景选择")
        current_preset = self.current_preset_var.get()
        current_threshold = self.threshold_entry.get().strip()
        applied = 0
        skipped = 0
        for tab in self.parent.tabs:
            if tab is self:
                continue
            if tab.running:
                skipped += 1
                continue
            tab.current_preset_var.set(current_preset)
            tab.on_preset_change(None)
            # 同步当前阈值到目标标签
            tab.threshold_entry.delete(0, tk.END)
            tab.threshold_entry.insert(0, current_threshold)
            tab.preset_thresholds[current_preset] = current_threshold
            tab.save_tab_config()
            tab.log(f"场景已同步为：{current_preset}")
            applied += 1
        msg = f"已将场景选择应用到 {applied} 个标签"
        if skipped:
            msg += f"（{skipped} 个运行中标签已跳过）"
        self.log(msg)
    
    def on_preset_change(self, event=None):
        """场景切换：记住旧场景阈值，载入新场景的阈值与参数。"""
        # 保存当前场景的阈值到记忆
        try:
            current_threshold = self.threshold_entry.get().strip()
            self.preset_thresholds[self.current_preset] = current_threshold
        except:
            pass
        
        self.current_preset = self.current_preset_var.get()
        gui_logger.info(f"[{self.tab_name}] 切换场景: {self.current_preset}")
        preset = self._preset_config()
        
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
        """刷新所有标签页的设备列表。"""
        gui_logger.info(f"[{self.tab_name}] 点击按钮: 刷新设备")
        for tab in self.parent.tabs:
            tab.refresh_devices()
    
    def on_device_changed(self, event=None):
        """设备下拉框变化后保存配置。"""
        # 设备选择变化时，更新 saved_device 并刷新所有标签的设备列表
        if hasattr(self, 'device_combo'):
            self.saved_device = self.device_combo.get()
            gui_logger.info(f"[{self.tab_name}] 选择设备: {self.saved_device}")
        # 设备选择变化时保存配置
        self.save_tab_config()
        self.refresh_all_devices()
    
    def _preset_config(self, name=None):
        """取场景预设。名字未知时返回空 dict，调用方按缺省值处理。"""
        return self.presets.get(name or self.current_preset) or {}

    def _read_threshold(self):
        """读识别阈值输入框。

        用户可能在框里留下非数字内容，这里回退到默认值而不是让 ValueError
        打断「开始」流程。
        """
        raw = self.threshold_entry.get().strip()
        try:
            return float(raw)
        except (TypeError, ValueError):
            self.log(f"阈值 {raw!r} 不是数字，已按 {DEFAULT_THRESHOLD} 处理")
            return DEFAULT_THRESHOLD

    def _read_target_count(self):
        """读目标挑战次数输入框，非法内容回退到默认值。"""
        try:
            return int(self.target_count_var.get().strip())
        except (TypeError, ValueError):
            return DEFAULT_TARGET_COUNT

    def _set_widget_state(self, names, state, radiobuttons=False):
        """按属性名批量设置控件状态；控件还没建出来时跳过。

        ``lock_controls`` / ``unlock_controls`` 原来是一对逐行镜像的 if 链，
        改一处漏一处就会让某个控件永远禁用，所以合成这一份。
        """
        for name in names:
            widget = getattr(self, name, None)
            if widget is not None:
                widget.config(state=state)
        if radiobuttons:
            for rb in getattr(self, 'preset_radiobuttons', ()):
                rb.config(state=state)

    def lock_controls(self):
        """运行期间锁定所有可编辑控件。"""
        self._set_widget_state(FULL_LOCK_WIDGETS, tk.DISABLED, radiobuttons=True)

    def unlock_controls(self):
        """运行结束后解锁所有可编辑控件。"""
        self._set_widget_state(FULL_LOCK_WIDGETS, tk.NORMAL, radiobuttons=True)

    def lock_for_adb_starting(self):
        """ADB启动期间锁定设备管理和运行控制"""
        self._set_widget_state(ADB_LOCK_WIDGETS, tk.DISABLED)

    def unlock_after_adb_started(self):
        """ADB启动完成后解锁设备管理和运行控制"""
        self._set_widget_state(ADB_LOCK_WIDGETS, tk.NORMAL)

    def log(self, message):
        """往本标签的运行日志区追加一行。"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        # 同步记录到GUI日志（场景分析输出）
        gui_logger.info(f"[{self.tab_name}] {message}")
    
    def send_notification(self, reason):
        """发送系统通知（非手动停止时调用）
        reason: "count"=次数达成, "anomaly"=连续点击异常, "image"=识别到特定图片
        """
        if reason == "anomaly":
            send_error_notification(
                f"异常停止 - {self.tab_name}",
                f"[{self.tab_name}] {self.current_preset} 连续点击异常，已停止运行"
            )
        else:
            send_complete_notification(
                f"任务完成 - {self.tab_name}",
                f"[{self.tab_name}] {self.current_preset} 任务已完成"
            )
    
    def clear_device(self):
        """清除本标签已选设备，并让其它标签刷新可选列表。"""
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

    def _device_used_by_other_tabs(self, device):
        """该设备是否已被其它标签页选中（含 saved_device 与下拉框当前值）。"""
        for tab in self.parent.tabs:
            if tab is self:
                continue
            if getattr(tab, 'saved_device', None) == device:
                return True
            combo = getattr(tab, 'device_combo', None)
            if combo is not None and combo.get() == device:
                return True
        return False

    def _apply_available_devices(self, current_device, available_devices):
        """把可用设备写进下拉框，并尽力恢复原来的选择。"""
        self.device_combo['values'] = available_devices

        # 优先使用当前选择的设备，其次使用保存的设备
        restore_device = current_device or self.saved_device
        if restore_device and restore_device in available_devices:
            self.device_combo.set(restore_device)
            if not current_device:
                # 是通过 saved_device 恢复的，清掉以免下次再恢复
                self.saved_device = None
        elif not current_device:
            # 没有保存的设备，留空让用户自己选
            self.device_combo.set("")
        else:
            self.device_combo.set("无设备")

        self.device_combo.update()

    def refresh_devices(self):
        """重新枚举 adb 设备，排除已被其它标签占用的。"""
        if not hasattr(self, 'device_combo'):
            return
        try:
            current_device = self.device_combo.get()
            devices = ADBManager().get_devices()
            available_devices = [d for d in devices
                                 if not self._device_used_by_other_tabs(d)]
            self._apply_available_devices(current_device, available_devices)
        except Exception as e:
            if hasattr(self, 'log'):
                self.log(f"获取设备列表失败: {e}")

    def start_loop(self):
        """校验输入并启动本标签的运行循环线程。"""
        device = self.device_combo.get()
        gui_logger.info(f"[{self.tab_name}] 点击按钮: 开始 | 设备: {device} | 场景: {self.current_preset}")
        if not device:
            self.log("请选择设备")
            return
        
        preset = self._preset_config()
        template_folder = os.path.join(self.png_base_folder, preset.get("folder", ""))

        if not os.path.exists(template_folder):
            self.log(f"模板文件夹不存在: {template_folder}")
            return
        
        self.recognizer = ImageRecognizer()
        self.recognizer.device = device
        self.recognizer.png_folder = template_folder
        self.recognizer.click_x = preset.get("click_x", 0)
        self.recognizer.click_y = preset.get("click_y", 0)
        # 场景状态每次运行都是全新的（run_loop_thread 里还会再重置一次）
        self.scene_state = SceneState()
        self.recognizer.threshold = self._read_threshold()
        
        # 设置模板匹配并行线程数
        try:
            workers = int(self.match_workers_var.get().strip())
            workers = max(1, min(8, workers))
        except (ValueError, AttributeError):
            workers = 1
        self.recognizer.match_workers = workers
        self.log(f"匹配线程数: {workers}")
        
        # 选择框中显示的设备已经是已连接状态，不再执行连接操作
        self.log(f"设备连接成功: {device}")
        
        # 检查设备分辨率（宽或高任意一个为720即可）
        def check_resolution():
            """检查设备分辨率宽或高是否为 720。"""
            try:
                adb_manager = ADBManager()
                return adb_manager.check_resolution(device)
            except Exception as e:
                self.log(f"检查分辨率失败: {e}")
                return False
        
        if not check_resolution():
            self.log("分辨率宽或高需为720（如1280*720、720*1280），请修改后再运行")
            return
        
        self.running = True
        self.manual_stop = False  # 重置手动停止标记
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        # 锁定所有控件
        self.lock_controls()
        
        self.scene_start_time = time.time()
        self.thread = threading.Thread(target=self.run_loop_thread, daemon=True)
        self.thread.start()
        
        self.log("已启动")
    