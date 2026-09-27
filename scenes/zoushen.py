"""随机暂停状态：模拟真实玩家无法实时观察屏幕的行为

包含两部分：
1. 运行期逻辑：随机抽取触发时间，到点暂停当前标签页的识别与点击，倒计时结束后恢复
2. 设置页UI：随机暂停设置区（开关/参数/白名单）与白名单勾选弹窗
"""
import random
import time
import tkinter as tk
from tkinter import ttk

from adb import get_gui_logger

gui_logger = get_gui_logger()

# 推荐默认值
DEFAULT_ENABLED = False
DEFAULT_TRIGGER_MIN = 60      # 随机暂停触发时间起始值（秒）
DEFAULT_TRIGGER_MAX = 180     # 随机暂停触发时间最终值（秒）
DEFAULT_DURATION_MIN = 5      # 随机暂停持续时间起始值（秒）
DEFAULT_DURATION_MAX = 15     # 随机暂停持续时间最终值（秒）
TRIGGER_MAX_LIMIT = 3600      # 触发时间上限（秒）
DURATION_MAX_LIMIT = 600      # 持续时间上限（秒）


# ---------------------------- 运行期逻辑 ----------------------------

def get_params(parent):
    """读取随机暂停参数（带兜底与区间归一化）
    返回 (启用, 触发下限, 触发上限, 持续下限, 持续上限)
    """
    def _get(name, default, max_value):
        """从设置页变量读一个整数，非法时回退到默认值。"""
        try:
            value = int(getattr(parent, name, default))
        except (TypeError, ValueError):
            return default
        # 单值至少1秒，避免0间隔导致每轮都触发；同时限制上界
        return max(1, min(max_value, value))
    
    enabled = bool(getattr(parent, 'zoushen_enabled', DEFAULT_ENABLED))
    trigger_min = _get('zoushen_trigger_min', DEFAULT_TRIGGER_MIN, TRIGGER_MAX_LIMIT)
    trigger_max = _get('zoushen_trigger_max', DEFAULT_TRIGGER_MAX, TRIGGER_MAX_LIMIT)
    duration_min = _get('zoushen_duration_min', DEFAULT_DURATION_MIN, DURATION_MAX_LIMIT)
    duration_max = _get('zoushen_duration_max', DEFAULT_DURATION_MAX, DURATION_MAX_LIMIT)
    # 起始值大于最终值时按区间归一化，防止 random.randint 抛 ValueError
    if trigger_min > trigger_max:
        trigger_min, trigger_max = trigger_max, trigger_min
    if duration_min > duration_max:
        duration_min, duration_max = duration_max, duration_min
    return enabled, trigger_min, trigger_max, duration_min, duration_max


def is_whitelisted(parent, preset):
    """场景是否在随机暂停白名单内（白名单内场景不触发随机暂停）"""
    whitelist = getattr(parent, 'zoushen_whitelist', None) or []
    return preset in whitelist


def schedule_next(tab):
    """抽取下一次随机暂停触发时间；未启用或场景在白名单内时清空"""
    enabled, trigger_min, trigger_max, _, _ = get_params(tab.parent)
    if not enabled or is_whitelisted(tab.parent, tab.current_preset):
        tab.zoushen_next_trigger_time = None
        return
    interval = random.randint(trigger_min, trigger_max)
    tab.zoushen_next_trigger_time = time.time() + interval


def wait(tab, seconds):
    """随机暂停等待：分片检查tab.running，停止/重启ADB时可立即退出
    返回True=等待完成，False=已被停止
    """
    if seconds <= 0:
        return True
    tab.log(f"随机暂停状态：暂停 {seconds} 秒")
    start_time = time.time()
    next_remain = seconds - 1  # 下一次要输出的剩余秒数
    while True:
        if not tab.running:
            return False
        time.sleep(0.3)
        elapsed = time.time() - start_time
        if elapsed >= seconds:
            break
        if next_remain > 0 and elapsed >= seconds - next_remain:
            tab.log(f"随机暂停状态：剩余 {next_remain} 秒")
            next_remain -= 1
    return True


def handle(tab):
    """主循环顶部的随机暂停检查；返回True表示等待期间被停止，需要退出循环"""
    if tab.zoushen_next_trigger_time is None:
        # 未调度时尝试调度（未启用或白名单场景会在内部直接清空）
        schedule_next(tab)
    elif is_whitelisted(tab.parent, tab.current_preset):
        # 切换到白名单场景：取消本次随机暂停
        tab.zoushen_next_trigger_time = None
    elif time.time() >= tab.zoushen_next_trigger_time:
        enabled, _, _, duration_min, duration_max = get_params(tab.parent)
        if enabled:
            pause_seconds = random.randint(duration_min, duration_max)
            if not wait(tab, pause_seconds):
                return True
            tab.log("随机暂停状态结束，恢复任务")
        schedule_next(tab)
    return False


# ---------------------------- 设置页 ----------------------------

def create_variables(settings_tab):
    """创建设置页随机暂停参数变量"""
    parent = settings_tab.parent
    settings_tab.settings_zoushen_enabled_var = tk.BooleanVar(value=parent.zoushen_enabled)
    settings_tab.settings_zoushen_trigger_min_var = tk.StringVar(value=str(parent.zoushen_trigger_min))
    settings_tab.settings_zoushen_trigger_max_var = tk.StringVar(value=str(parent.zoushen_trigger_max))
    settings_tab.settings_zoushen_duration_min_var = tk.StringVar(value=str(parent.zoushen_duration_min))
    settings_tab.settings_zoushen_duration_max_var = tk.StringVar(value=str(parent.zoushen_duration_max))


def apply_settings(settings_tab):
    """把设置页的随机暂停参数写回父对象"""
    parent = settings_tab.parent
    old_enabled = parent.zoushen_enabled
    parent.zoushen_enabled = settings_tab.settings_zoushen_enabled_var.get()
    settings_tab._log_change(old_enabled, parent.zoushen_enabled,
                            "随机暂停已启用", "随机暂停已关闭")
    
    # 随机暂停参数：非数字/负数/越界一律忽略并保留旧值
    _apply_int(settings_tab, settings_tab.settings_zoushen_trigger_min_var,
               'zoushen_trigger_min', TRIGGER_MAX_LIMIT, "随机暂停触发时间起始值")
    _apply_int(settings_tab, settings_tab.settings_zoushen_trigger_max_var,
               'zoushen_trigger_max', TRIGGER_MAX_LIMIT, "随机暂停触发时间最终值")
    _apply_int(settings_tab, settings_tab.settings_zoushen_duration_min_var,
               'zoushen_duration_min', DURATION_MAX_LIMIT, "随机暂停持续时间起始值")
    _apply_int(settings_tab, settings_tab.settings_zoushen_duration_max_var,
               'zoushen_duration_max', DURATION_MAX_LIMIT, "随机暂停持续时间最终值")


def _apply_int(settings_tab, var, attr_name, max_value, label):
    """应用单个随机暂停整数参数：非法值忽略并保留旧值（与dinghao_wait等参数一致）"""
    try:
        value = int(var.get().strip())
    except:
        return
    if value < 0 or value > max_value:
        return
    parent = settings_tab.parent
    if getattr(parent, attr_name, None) != value:
        setattr(parent, attr_name, value)
        if len(parent.tabs) > 0:
            parent.tabs[0].log(f"{label}已设置为 {value} 秒")


def reset_defaults(settings_tab):
    """重置随机暂停参数为推荐值"""
    gui_logger.info("[设置] 点击按钮: 重置随机暂停推荐值")
    defaults = (
        ('zoushen_trigger_min', DEFAULT_TRIGGER_MIN, settings_tab.settings_zoushen_trigger_min_var),
        ('zoushen_trigger_max', DEFAULT_TRIGGER_MAX, settings_tab.settings_zoushen_trigger_max_var),
        ('zoushen_duration_min', DEFAULT_DURATION_MIN, settings_tab.settings_zoushen_duration_min_var),
        ('zoushen_duration_max', DEFAULT_DURATION_MAX, settings_tab.settings_zoushen_duration_max_var),
    )
    # 先直接同步到父对象，避免逐个参数触发变更日志，只输出一条汇总提示
    for attr_name, value, var in defaults:
        setattr(settings_tab.parent, attr_name, value)
        var.set(str(value))
    settings_tab.save_settings()
    if len(settings_tab.parent.tabs) > 0:
        settings_tab.parent.tabs[0].log(
            f"已重置随机暂停推荐值（触发{DEFAULT_TRIGGER_MIN}~{DEFAULT_TRIGGER_MAX}秒，"
            f"持续{DEFAULT_DURATION_MIN}~{DEFAULT_DURATION_MAX}秒）")


def create_section(settings_tab, parent_frame):
    """构建随机暂停设置区"""
    zoushen_group = ttk.LabelFrame(parent_frame, text="随机暂停设置", padding="8")
    zoushen_group.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
    settings_tab._add_section_help(zoushen_group,
        "模拟真实玩家无法一直盯着屏幕：到时间后暂停当前标签页的识别与点击，倒计时结束再恢复。\n"
        "触发时间：任务开始后在该区间内随机取一个值作为倒计时，到点进入随机暂停状态；\n"
        "持续时间：进入随机暂停状态后在该区间内随机取一个值作为暂停时长。\n"
        "白名单：勾选的场景不会触发随机暂停。\n"
        "暂停期间点“停止”或“重启ADB”会立即中断随机暂停。\n"
        "推荐值：触发 60~180 秒，持续 5~15 秒（可点“重置推荐值”恢复）。")

    top_row = ttk.Frame(zoushen_group)
    top_row.pack(fill=tk.X, pady=2)
    ttk.Checkbutton(top_row, text="启用随机暂停状态", variable=settings_tab.settings_zoushen_enabled_var,
                    command=settings_tab.save_settings).pack(side=tk.LEFT)
    ttk.Button(top_row, text="重置推荐值", command=lambda: reset_defaults(settings_tab),
               width=10).pack(side=tk.LEFT, padx=(8, 0))

    # 随机暂停触发时间区间（秒）
    trigger_row = ttk.Frame(zoushen_group)
    trigger_row.pack(fill=tk.X, pady=2)
    ttk.Label(trigger_row, text="触发时间:", font=('Microsoft YaHei', 9)).pack(side=tk.LEFT, padx=2)
    settings_tab.zoushen_trigger_min_entry = ttk.Entry(trigger_row, textvariable=settings_tab.settings_zoushen_trigger_min_var, width=5)
    settings_tab.zoushen_trigger_min_entry.pack(side=tk.LEFT, padx=2)
    settings_tab.zoushen_trigger_min_entry.bind('<FocusOut>', lambda e: settings_tab.save_settings())
    ttk.Label(trigger_row, text="~", font=('Microsoft YaHei', 9)).pack(side=tk.LEFT)
    settings_tab.zoushen_trigger_max_entry = ttk.Entry(trigger_row, textvariable=settings_tab.settings_zoushen_trigger_max_var, width=5)
    settings_tab.zoushen_trigger_max_entry.pack(side=tk.LEFT, padx=2)
    settings_tab.zoushen_trigger_max_entry.bind('<FocusOut>', lambda e: settings_tab.save_settings())
    ttk.Label(trigger_row, text="秒", font=('Microsoft YaHei', 9)).pack(side=tk.LEFT, padx=2)

    # 随机暂停持续时间区间（秒）
    duration_row = ttk.Frame(zoushen_group)
    duration_row.pack(fill=tk.X, pady=2)
    ttk.Label(duration_row, text="持续时间:", font=('Microsoft YaHei', 9)).pack(side=tk.LEFT, padx=2)
    settings_tab.zoushen_duration_min_entry = ttk.Entry(duration_row, textvariable=settings_tab.settings_zoushen_duration_min_var, width=5)
    settings_tab.zoushen_duration_min_entry.pack(side=tk.LEFT, padx=2)
    settings_tab.zoushen_duration_min_entry.bind('<FocusOut>', lambda e: settings_tab.save_settings())
    ttk.Label(duration_row, text="~", font=('Microsoft YaHei', 9)).pack(side=tk.LEFT)
    settings_tab.zoushen_duration_max_entry = ttk.Entry(duration_row, textvariable=settings_tab.settings_zoushen_duration_max_var, width=5)
    settings_tab.zoushen_duration_max_entry.pack(side=tk.LEFT, padx=2)
    settings_tab.zoushen_duration_max_entry.bind('<FocusOut>', lambda e: settings_tab.save_settings())
    ttk.Label(duration_row, text="秒", font=('Microsoft YaHei', 9)).pack(side=tk.LEFT, padx=2)

    # 随机暂停白名单（白名单内场景不触发随机暂停）
    whitelist_row = ttk.Frame(zoushen_group)
    whitelist_row.pack(fill=tk.X, pady=2)
    ttk.Label(whitelist_row, text="白名单:", font=('Microsoft YaHei', 9)).pack(side=tk.LEFT, padx=2)
    settings_tab.zoushen_whitelist_label = ttk.Label(whitelist_row, text="未设置", font=('Microsoft YaHei', 9))
    settings_tab.zoushen_whitelist_label.pack(side=tk.LEFT, padx=2)
    ttk.Button(whitelist_row, text="设置", width=6,
               command=lambda: show_whitelist_dialog(settings_tab)).pack(side=tk.LEFT, padx=2)
    refresh_whitelist_label(settings_tab)


def refresh_whitelist_label(settings_tab):
    """刷新白名单状态显示"""
    if hasattr(settings_tab, 'zoushen_whitelist_label'):
        count = len(getattr(settings_tab.parent, 'zoushen_whitelist', None) or [])
        settings_tab.zoushen_whitelist_label.config(text="未设置" if count == 0 else f"{count}个场景")


def apply_whitelist(settings_tab, scenes):
    """应用随机暂停白名单并输出日志"""
    settings_tab.parent.zoushen_whitelist = list(scenes)
    refresh_whitelist_label(settings_tab)
    settings_tab.save_settings()
    if len(settings_tab.parent.tabs) > 0:
        if scenes:
            settings_tab.parent.tabs[0].log(f"随机暂停白名单已设置：{'、'.join(scenes)}")
        else:
            settings_tab.parent.tabs[0].log("随机暂停白名单已清空（所有场景均会随机暂停）")


def show_whitelist_dialog(settings_tab):
    """弹窗设置随机暂停白名单场景"""
    gui_logger.info("[设置] 点击按钮: 设置随机暂停白名单")
    scenes = list(settings_tab.parent.presets.keys())
    current = set(getattr(settings_tab.parent, 'zoushen_whitelist', None) or [])

    dialog = tk.Toplevel(settings_tab.parent.root)
    dialog.title("随机暂停白名单设置")
    dialog.resizable(False, False)
    dialog.transient(settings_tab.parent.root)
    dialog.grab_set()

    ttk.Label(dialog, text="勾选的场景不会触发随机暂停状态:", font=('Microsoft YaHei', 9)).pack(padx=20, pady=(15, 5))

    list_frame = ttk.Frame(dialog)
    list_frame.pack(padx=20, pady=5)
    scene_vars = {}
    columns = 3
    for i, scene in enumerate(scenes):
        var = tk.BooleanVar(value=scene in current)
        scene_vars[scene] = var
        row, col = divmod(i, columns)
        ttk.Checkbutton(list_frame, text=scene, variable=var).grid(row=row, column=col, sticky=tk.W, padx=6, pady=2)

    def select_all(value):
        """全选或全不选白名单。"""
        for var in scene_vars.values():
            var.set(value)

    tools_frame = ttk.Frame(dialog)
    tools_frame.pack(pady=(5, 5))
    ttk.Button(tools_frame, text="全选", command=lambda: select_all(True), width=8).pack(side=tk.LEFT, padx=5)
    ttk.Button(tools_frame, text="清空", command=lambda: select_all(False), width=8).pack(side=tk.LEFT, padx=5)

    def on_ok():
        """应用白名单选择并关闭对话框。"""
        apply_whitelist(settings_tab, [s for s in scenes if scene_vars[s].get()])
        dialog.destroy()

    btn_frame = ttk.Frame(dialog)
    btn_frame.pack(pady=(5, 15))
    ttk.Button(btn_frame, text="确定", command=on_ok, width=8).pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="取消", command=dialog.destroy, width=8).pack(side=tk.LEFT, padx=5)

    dialog.update_idletasks()
    main_x = settings_tab.parent.root.winfo_x()
    main_y = settings_tab.parent.root.winfo_y()
    main_w = settings_tab.parent.root.winfo_width()
    main_h = settings_tab.parent.root.winfo_height()
    d_w = dialog.winfo_width()
    d_h = dialog.winfo_height()
    x = main_x + (main_w - d_w) // 2
    y = main_y + (main_h - d_h) // 2
    dialog.geometry(f"+{x}+{y}")