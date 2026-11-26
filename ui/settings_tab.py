"""设置标签页：左侧分类导航 + 右侧设置面板。

所有设置集中在本页：功能开关、设备连接、提示音与通知、随机暂停、日志与更新。
原菜单栏「设置(T)」中的功能项、日志操作和软件更新入口都已并入这里。
"""

from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
import webbrowser
from tkinter import ttk

import wav
from adb import get_gui_logger, set_logging_enabled
from image_recognizer import ImageRecognizer
from notification import set_notify_enabled, test_complete, test_error
from scenes import zoushen
from ui.widgets import ToolTip

gui_logger = get_gui_logger()

# 侧栏分类：(内部键, 显示名, 页面说明)
NAV_ITEMS = (
    ("func", "功能开关", "任务流程、账号联动与等待时间，改动立即生效"),
    ("adb", "设备连接", "ADB 连接地址、常用端口与连接操作"),
    ("notify", "提示音与通知", "任务结束时的声音与 Windows 系统通知"),
    ("zoushen", "随机暂停", "模拟真实玩家无法一直盯着屏幕的行为"),
    ("misc", "日志与更新", "日志记录、软件更新与问题反馈"),
)

# 设置页配色：白色页面，灰色区域使用原生 ttk 背景色
PAGE_BG = "#ffffff"
MUTED_COLOR = "SystemGrayText"


class SettingsTab:
    def __init__(self, parent):
        """初始化设置页并创建全部设置变量。"""
        self.parent = parent
        self.frame = ttk.Frame(parent.notebook)
        self._create_variables()
        self.setup_ui()

    def _create_variables(self):
        """创建 settings_* 变量，初值取自 parent 上的当前设置。"""
        self.settings_ip_var = tk.StringVar(value=self.parent.adb_ip)
        self.settings_port_var = tk.StringVar(value=self.parent.adb_port)
        self.settings_link_var = tk.BooleanVar(value=self.parent.link_enabled)
        self.settings_close_jiacheng_var = tk.BooleanVar(value=self.parent.close_jiacheng_enabled)
        self.settings_close_jiacheng_wait_var = tk.StringVar(value=str(self.parent.close_jiacheng_wait))
        self.settings_dinghao_wait_var = tk.StringVar(value=str(self.parent.dinghao_wait))
        self.settings_huijuan_mode_var = tk.BooleanVar(value=self.parent.huijuan_mode)
        self.settings_dj_jinsheng_stop_var = tk.BooleanVar(value=self.parent.dj_jinsheng_stop)
        self.settings_ql_fangqi_var = tk.BooleanVar(value=self.parent.ql_fangqi)
        self.settings_ql_zaici_var = tk.BooleanVar(value=self.parent.ql_zaici)
        self.settings_logging_var = tk.BooleanVar(value=self.parent.logging_enabled)
        self.settings_notify_var = tk.BooleanVar(value=self.parent.notify_enabled)

        # 提示音设置
        wav.create_variables(self)

        # 随机暂停状态设置
        zoushen.create_variables(self)

    # ---------------------------- 通用控件 ----------------------------

    def _create_group(self, parent, title, help_text=None):
        """创建一个浅灰卡片分组，返回内容区 Frame。"""
        card = tk.Frame(parent, bg=self._card_bg, bd=0)
        card.pack(fill=tk.X, pady=(0, 10))

        header = ttk.Frame(card, style="Card.TFrame")
        header.pack(fill=tk.X, padx=10, pady=(7, 0))
        ttk.Label(header, text=title, style="CardTitle.TLabel").pack(side=tk.LEFT)
        if help_text:
            q_btn = ttk.Label(header, text="?", style="CardMuted.TLabel", cursor="hand2")
            q_btn.pack(side=tk.LEFT, padx=(3, 0))
            ToolTip(q_btn, help_text)

        body = ttk.Frame(card, style="Card.TFrame")
        body.pack(fill=tk.X, padx=10, pady=(3, 6))
        return body

    def _add_row_separator(self, parent):
        """在组内的设置项之间加一条细分隔线。"""
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(3, 3))

    def _make_row(self, parent, title, desc=None, help_text=None):
        """一行设置：左侧标题/说明，右侧留给控件。返回该行 Frame。"""
        if any(getattr(child, "_settings_row", False) for child in parent.winfo_children()):
            self._add_row_separator(parent)

        row = ttk.Frame(parent, style="Card.TFrame")
        row._settings_row = True
        row.pack(fill=tk.X, pady=2)

        text_box = ttk.Frame(row, style="Card.TFrame")
        text_box.pack(side=tk.LEFT, fill=tk.X, expand=True)

        title_line = ttk.Frame(text_box, style="Card.TFrame")
        title_line.pack(anchor=tk.W)
        ttk.Label(title_line, text=title, style="Card.TLabel").pack(side=tk.LEFT)
        if help_text:
            q_btn = ttk.Label(title_line, text="?", style="CardMuted.TLabel", cursor="hand2")
            q_btn.pack(side=tk.LEFT, padx=(3, 0))
            ToolTip(q_btn, help_text)

        if desc:
            ttk.Label(text_box, text=desc, style="CardMuted.TLabel",
                      wraplength=220, justify=tk.LEFT).pack(anchor=tk.W, pady=(1, 0))
        return row

    def _add_toggle_row(self, parent, title, desc, var, help_text=None, command=None):
        """一行开关设置，勾选框放在行尾。"""
        row = self._make_row(parent, title, desc, help_text)
        ttk.Checkbutton(row, variable=var, style="Card.TCheckbutton",
                        command=command or self.save_settings).pack(side=tk.RIGHT, padx=(10, 0))
        return row

    def _add_buttons_row(self, parent, title, desc, buttons, help_text=None):
        """一行操作按钮设置。buttons 为 (文字, 回调) 列表。"""
        row = self._make_row(parent, title, desc, help_text)
        box = ttk.Frame(row, style="Card.TFrame")
        box.pack(side=tk.RIGHT, padx=(10, 0))
        for text, command in buttons:
            ttk.Button(box, text=text, command=command).pack(side=tk.LEFT, padx=(0, 4))
        return row

    def _add_wait_row(self, parent, title, desc, var, help_text=None):
        """一行秒数输入设置，失焦或回车时保存。"""
        row = self._make_row(parent, title, desc, help_text)
        box = ttk.Frame(row, style="Card.TFrame")
        box.pack(side=tk.RIGHT, padx=(10, 0))
        entry = ttk.Entry(box, textvariable=var, width=6)
        entry.pack(side=tk.LEFT)
        ttk.Label(box, text="秒", style="CardMuted.TLabel").pack(side=tk.LEFT, padx=(4, 0))
        entry.bind("<FocusOut>", lambda e: self.save_settings())
        entry.bind("<Return>", lambda e: self.save_settings())
        return entry

    # ---------------------------- 页面框架 ----------------------------

    def setup_ui(self):
        """搭建设置页：左侧分类导航 + 右侧当前分类面板。"""
        style = ttk.Style(self.parent.root)
        # 灰色区域统一使用原生 ttk 背景色
        self._card_bg = (style.lookup("TFrame", "background")
                         or self.parent.root.cget("background"))
        style.configure("Card.TFrame", background=self._card_bg)
        style.configure("Card.TLabel", background=self._card_bg,
                        font=('Microsoft YaHei', 9))
        style.configure("CardMuted.TLabel", background=self._card_bg,
                        foreground=MUTED_COLOR, font=('Microsoft YaHei', 8))
        style.configure("CardTitle.TLabel", background=self._card_bg,
                        font=('Microsoft YaHei', 9, 'bold'))
        style.configure("Card.TCheckbutton", background=self._card_bg,
                        font=('Microsoft YaHei', 9))
        style.map("Card.TCheckbutton",
                  background=[("active", self._card_bg)],
                  foreground=[("disabled", MUTED_COLOR)])

        outer = tk.Frame(self.frame, bg=PAGE_BG)
        outer.pack(fill=tk.BOTH, expand=True)

        sidebar = tk.Frame(outer, bg=self._card_bg, width=132)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)
        ttk.Separator(outer, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(sidebar, text="设置分类", bg=self._card_bg, fg=MUTED_COLOR,
                 font=('Microsoft YaHei', 8)).pack(anchor=tk.W, padx=10, pady=(8, 4))
        ttk.Separator(sidebar, orient=tk.HORIZONTAL).pack(
            fill=tk.X, padx=8, pady=(0, 6))

        self._nav_buttons = {}
        for index, (key, label, _) in enumerate(NAV_ITEMS):
            if index > 0:
                ttk.Separator(sidebar, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10)
            btn = tk.Button(sidebar, text=label, anchor=tk.W, bd=1, relief=tk.FLAT,
                            bg=self._card_bg, activebackground=self._card_bg,
                            cursor="hand2", font=('Microsoft YaHei', 9),
                            padx=10, pady=5,
                            command=lambda k=key: self._select_panel(k))
            btn.pack(fill=tk.X, padx=6, pady=2)
            self._nav_buttons[key] = btn



        content = tk.Frame(outer, bg=PAGE_BG)
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=8)

        header = tk.Frame(content, bg=PAGE_BG)
        header.pack(fill=tk.X)
        title_box = tk.Frame(header, bg=PAGE_BG)
        title_box.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._page_title = tk.Label(title_box, text="功能开关", bg=PAGE_BG,
                                    font=('Microsoft YaHei', 12, 'bold'))
        self._page_title.pack(anchor=tk.W)
        self._page_sub = tk.Label(title_box, text="任务流程、账号联动与等待时间，改动立即生效",
                                  bg=PAGE_BG, fg=MUTED_COLOR,
                                  font=('Microsoft YaHei', 8))
        self._page_sub.pack(anchor=tk.W, pady=(1, 0))

        ttk.Separator(content, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(8, 8))

        # 固定窗口下内容会超出高度，用 Canvas + Scrollbar 承载设置面板
        scroll_wrap = tk.Frame(content, bg=PAGE_BG)
        scroll_wrap.pack(fill=tk.BOTH, expand=True)

        self._canvas = tk.Canvas(scroll_wrap, bg=PAGE_BG, highlightthickness=0, bd=0)
        self._scrollbar = ttk.Scrollbar(scroll_wrap, orient=tk.VERTICAL,
                                        command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._scrollbar.set)
        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._panel_container = tk.Frame(self._canvas, bg=PAGE_BG)
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._panel_container, anchor="nw")
        self._panel_container.bind("<Configure>", self._on_panel_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        self._panels = {
            "func": self._create_func_panel(),
            "adb": self._create_adb_panel(),
            "notify": self._create_notify_panel(),
            "zoushen": self._create_zoushen_panel(),
            "misc": self._create_misc_panel(),
        }
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)
        self._bind_mousewheel(self._panel_container)
        self._current_panel = None
        self._select_panel("func")

    def _new_panel(self):
        """创建一个未显示的设置面板。"""
        return tk.Frame(self._panel_container, bg=PAGE_BG)

    def _select_panel(self, key):
        """切换到指定分类。"""
        if key not in self._panels:
            return
        self._current_panel = key

        for panel in self._panels.values():
            panel.pack_forget()
        self._panels[key].pack(fill=tk.BOTH, expand=True)
        self._canvas.yview_moveto(0)

        for nav_key, btn in self._nav_buttons.items():
            if nav_key == key:
                btn.config(relief=tk.SUNKEN, font=('Microsoft YaHei', 9, 'bold'))
            else:
                btn.config(relief=tk.FLAT, font=('Microsoft YaHei', 9))

        for nav_key, label, subtitle in NAV_ITEMS:
            if nav_key == key:
                self._page_title.config(text=label)
                self._page_sub.config(text=subtitle)
                break

    def _on_panel_configure(self, event=None):
        """面板内容尺寸变化时更新滚动范围。"""
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        """画布尺寸变化时让面板宽度跟随。"""
        self._canvas.itemconfigure(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        """鼠标滚轮滚动设置内容。"""
        self._canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def _bind_mousewheel(self, widget):
        """把滚轮事件递归绑定到设置内容的所有控件上。"""
        widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
        for child in widget.winfo_children():
            self._bind_mousewheel(child)

    # ---------------------------- 各分类面板 ----------------------------

    def _create_func_panel(self):
        """功能开关：任务行为、契灵行为、等待时间。"""
        panel = self._new_panel()

        behavior = self._create_group(panel, "任务行为",
            "任务流程的全局开关，勾选后立即生效并写入配置。")
        self._add_toggle_row(behavior, "队员司机联动",
            "队员标签与司机标签联动准备、开始；刚打开时会重置队员标签的已准备状态。",
            self.settings_link_var)
        self._add_toggle_row(behavior, "绘卷模式", "绘卷玩法使用专用流程。",
            self.settings_huijuan_mode_var)
        self._add_toggle_row(behavior, "斗技段位晋升结束程序",
            "达到晋升段位后停止任务并结束程序。", self.settings_dj_jinsheng_stop_var)
        self._add_toggle_row(behavior, "挑战结束后关闭御魂加成",
            "任务结束时自动关闭御魂加成。", self.settings_close_jiacheng_var)

        ql_group = self._create_group(panel, "契灵行为",
            "放弃结契与再次结契互斥，至少要保留一个。")
        ql_row = self._make_row(ql_group, "结契方式", "契灵玩法遇到结契界面时的处理方式。")
        ql_box = ttk.Frame(ql_row, style="Card.TFrame")
        ql_box.pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Checkbutton(ql_box, text="放弃结契", variable=self.settings_ql_fangqi_var,
                        style="Card.TCheckbutton",
                        command=self._on_ql_fangqi).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Checkbutton(ql_box, text="再次结契", variable=self.settings_ql_zaici_var,
                        style="Card.TCheckbutton",
                        command=self._on_ql_zaici).pack(side=tk.LEFT)

        wait_group = self._create_group(panel, "等待时间",
            "非数字或负数会被忽略并保留原值。")
        self._add_wait_row(wait_group, "关闭御魂加成等待",
            "挑战结束后等待该秒数再关闭加成。", self.settings_close_jiacheng_wait_var)
        self._add_wait_row(wait_group, "被顶号后等待",
            "被顶号下线后等待进入游戏的秒数。", self.settings_dinghao_wait_var)
        return panel

    def _create_adb_panel(self):
        """设备连接面板。"""
        panel = self._new_panel()
        self._create_adb_section(panel)
        return panel

    def _create_notify_panel(self):
        """提示音与系统通知面板。"""
        panel = self._new_panel()
        wav.create_section(self, panel)
        self._create_notify_section(panel)
        return panel

    def _create_zoushen_panel(self):
        """随机暂停面板。"""
        panel = self._new_panel()
        zoushen.create_section(self, panel)
        return panel

    def _create_misc_panel(self):
        """日志与更新面板。"""
        panel = self._new_panel()

        log_group = self._create_group(panel, "日志",
            "开启后把运行日志写入 logs 目录。")
        self._add_toggle_row(log_group, "启用日志记录", "切换后立即同步给日志模块。",
                             self.settings_logging_var)
        self._add_buttons_row(log_group, "日志文件",
            "清空日志会删除日志目录下所有 .log 文件。",
            [("打开日志文件夹", self._open_log_folder), ("清空日志", self._clear_logs)])

        update_group = self._create_group(panel, "软件更新", "网盘提取密码：62m8。")
        self._add_buttons_row(update_group, "网盘更新", "打开网盘下载最新版本。",
            [("复制网盘密码", self._copy_password), ("打开更新页", self._open_update_link)])
        self._add_buttons_row(update_group, "GitHub 仓库", "查看源码、提交 Issue。",
            [("打开仓库", self._open_github)])

        feedback_group = self._create_group(panel, "问题反馈",
            "遇到问题可复制群号或邮箱联系作者。")
        self._add_buttons_row(feedback_group, "Bug 反馈与建议",
            "复制 QQ 交流群号 647871264 或作者邮箱。",
            [("复制QQ群号", self._copy_qq_group), ("复制邮箱", self._copy_email)])
        return panel

    # ---------------------------- 契灵联动 ----------------------------

    def _on_ql_fangqi(self):
        """放弃结契勾选变化：保持与再次结契互斥后保存。"""
        self._toggle_ql_fangqi()
        self.save_settings()

    def _on_ql_zaici(self):
        """再次结契勾选变化：保持与放弃结契互斥后保存。"""
        self._toggle_ql_zaici()
        self.save_settings()

    def _toggle_ql_fangqi(self):
        """契灵「放弃」与「再次」互斥。"""
        if self.settings_ql_fangqi_var.get():
            self.settings_ql_zaici_var.set(False)
        else:
            self.settings_ql_zaici_var.set(True)

    def _toggle_ql_zaici(self):
        """契灵「再次」与「放弃」互斥。"""
        if self.settings_ql_zaici_var.get():
            self.settings_ql_fangqi_var.set(False)
        else:
            self.settings_ql_fangqi_var.set(True)

    # ---------------------------- 设置应用 ----------------------------

    def _log_change(self, old_value, new_value, enabled_msg, disabled_msg):
        """设置项发生变化时往运行日志写一行。"""
        if old_value != new_value and len(self.parent.tabs) > 0:
            msg = enabled_msg if new_value else disabled_msg
            self.parent.tabs[0].log(msg)

    def _apply_wait_time(self, var, attr):
        """把输入框里的等待秒数写回 parent，非数字或负数时保持原值。"""
        try:
            wait_time = int(var.get())
            if wait_time >= 0:
                setattr(self.parent, attr, wait_time)
        except (TypeError, ValueError):
            pass

    def _apply_link_enabled(self):
        """队员司机联动开关。刚打开时把已有队员标签重置为未准备。"""
        old = self.parent.link_enabled
        self.parent.link_enabled = self.settings_link_var.get()
        if old != self.parent.link_enabled and self.parent.link_enabled:
            for tab in self.parent.tabs:
                if getattr(tab, 'current_preset', None) == "队员":
                    tab.is_ready = False
        self._log_change(old, self.parent.link_enabled,
                         "队员司机联动已启用", "队员司机联动已关闭")

    def _apply_close_jiacheng(self):
        """关闭御魂加成开关与等待时间。"""
        old = self.parent.close_jiacheng_enabled
        self.parent.close_jiacheng_enabled = self.settings_close_jiacheng_var.get()
        self._apply_wait_time(self.settings_close_jiacheng_wait_var, 'close_jiacheng_wait')
        if old != self.parent.close_jiacheng_enabled:
            msg = (f"关闭加成功能已启用，等待{self.parent.close_jiacheng_wait}秒"
                   if self.parent.close_jiacheng_enabled else "关闭御魂加成功能已关闭")
            self._log_change(old, self.parent.close_jiacheng_enabled, msg, msg)

    def _apply_mode_toggles(self):
        """绘卷模式与斗技段位晋升结束程序。"""
        old_huijuan = self.parent.huijuan_mode
        self.parent.huijuan_mode = self.settings_huijuan_mode_var.get()
        self._log_change(old_huijuan, self.parent.huijuan_mode,
                         "绘卷模式已启用", "绘卷模式已关闭")

        old_jinsheng = self.parent.dj_jinsheng_stop
        self.parent.dj_jinsheng_stop = self.settings_dj_jinsheng_stop_var.get()
        self._log_change(old_jinsheng, self.parent.dj_jinsheng_stop,
                         "斗技段位晋升结束程序已启用", "斗技段位晋升结束程序已关闭")

        self.parent.ql_fangqi = self.settings_ql_fangqi_var.get()
        self.parent.ql_zaici = self.settings_ql_zaici_var.get()

    def _apply_logging(self):
        """日志记录开关，变化时同步给日志模块。"""
        old = self.parent.logging_enabled
        self.parent.logging_enabled = self.settings_logging_var.get()
        if old != self.parent.logging_enabled:
            set_logging_enabled(self.parent.logging_enabled)
            self._log_change(old, self.parent.logging_enabled,
                             "日志记录已开启", "日志记录已关闭")

    def _apply_notify(self):
        """系统通知开关。"""
        old = self.parent.notify_enabled
        self.parent.notify_enabled = self.settings_notify_var.get()
        set_notify_enabled(self.parent.notify_enabled)
        self._log_change(old, self.parent.notify_enabled,
                         "系统通知已开启", "系统通知已关闭")

    def save_settings(self):
        """把设置页上的所有选项写回 parent，并落盘配置。"""
        self.parent.adb_ip = self.settings_ip_var.get()
        self.parent.adb_port = self.settings_port_var.get()

        self._apply_link_enabled()
        self._apply_close_jiacheng()
        self._apply_wait_time(self.settings_dinghao_wait_var, 'dinghao_wait')
        self._apply_mode_toggles()

        wav.apply_settings(self)
        self._apply_logging()
        self._apply_notify()
        zoushen.apply_settings(self)

        self.parent.save_config()

    # ---------------------------- ADB 连接 ----------------------------

    def _create_adb_section(self, parent_frame):
        """构建「ADB 设备连接」设置区。"""
        self.adb_group_frame = self._create_group(parent_frame, "ADB设备连接",
            "填写模拟器/手机的 ADB 连接地址与端口，点击“连接”后生效。\n"
            "ip地址：如果是本机模拟器连接，填写“127.0.0.1”；如果是局域网其他设备连接，填写设备的IP地址。\n"
            "常用端口：16384（MuMu）、16416（MuMu）、7555（雷电）、62001（夜神旧版）、5555（USB调试）。\n"
            "连接成功后，设备会出现在控制页的“设备选择”下拉框中；\n"
            "若下拉框没有设备，先点“重启ADB”再重新连接。\n"
            "运行中重启ADB会先停止所有标签的任务，期间连接区域会锁定。")

        addr_row = self._make_row(self.adb_group_frame, "连接地址",
            "本机模拟器填 127.0.0.1，局域网设备填设备 IP。")
        addr_box = ttk.Frame(addr_row, style="Card.TFrame")
        addr_box.pack(side=tk.RIGHT, padx=(10, 0))
        self.ip_entry = ttk.Entry(addr_box, textvariable=self.settings_ip_var, width=13)
        self.ip_entry.pack(side=tk.LEFT, padx=2)
        self.ip_entry.bind('<FocusOut>', lambda e: self.save_settings())
        ttk.Label(addr_box, text=":", style="Card.TLabel").pack(side=tk.LEFT)
        self.port_entry = ttk.Entry(addr_box, textvariable=self.settings_port_var, width=6)
        self.port_entry.pack(side=tk.LEFT, padx=2)
        self.port_entry.bind('<FocusOut>', lambda e: self.save_settings())

        port_row = self._make_row(self.adb_group_frame, "常用端口", "点击快捷填入端口号。")
        port_box = ttk.Frame(port_row, style="Card.TFrame")
        port_box.pack(side=tk.RIGHT, padx=(10, 0))
        self.port_btn_1 = ttk.Button(port_box, text="16384", width=7,
                                     command=lambda: self._set_port("16384"))
        self.port_btn_1.pack(side=tk.LEFT, padx=(0, 4))
        self.port_btn_2 = ttk.Button(port_box, text="16416", width=7,
                                     command=lambda: self._set_port("16416"))
        self.port_btn_2.pack(side=tk.LEFT)

        action_row = self._make_row(self.adb_group_frame, "连接操作",
            "连接成功后设备会出现在各设备标签页的下拉框中。")
        action_box = ttk.Frame(action_row, style="Card.TFrame")
        action_box.pack(side=tk.RIGHT, padx=(10, 0))
        self.connect_btn = ttk.Button(action_box, text="连接", width=9,
                                      command=self._connect_device)
        self.connect_btn.pack(side=tk.LEFT, padx=(0, 4))
        self.restart_adb_btn = ttk.Button(action_box, text="重启ADB", width=9,
                                          command=self._restart_adb)
        self.restart_adb_btn.pack(side=tk.LEFT)

        self._add_row_separator(self.adb_group_frame)
        ttk.Label(self.adb_group_frame,
                  text="重启 ADB 会先停止所有标签任务，完成后自动刷新设备列表。",
                  style="CardMuted.TLabel").pack(anchor=tk.W, pady=(2, 0))

        # ADB启动状态控件列表
        self._adb_controls = [
            self.ip_entry, self.port_entry, self.port_btn_1, self.port_btn_2,
            self.connect_btn, self.restart_adb_btn
        ]

    def _set_port(self, port):
        """写入常用端口并立即保存。"""
        gui_logger.info(f"[设置] 点击按钮: 设置端口 {port}")
        self.settings_port_var.set(port)
        self.save_settings()

    def _connect_device(self):
        """在后台线程里连接指定 ip:port 的设备。"""
        ip = self.settings_ip_var.get().strip()
        port = self.settings_port_var.get().strip()
        if not ip or not port:
            return
        gui_logger.info(f"[设置] 点击按钮: 连接设备 {ip}:{port}")
        self.connect_btn.config(state=tk.DISABLED, text="连接中...")

        def _worker():
            """后台线程体。"""
            try:
                ir = ImageRecognizer()
                ir.device = f"{ip}:{port}"
                ir.connect_device()
            except Exception:
                pass
            finally:
                self.parent.root.after(0, lambda: self.connect_btn.config(state=tk.NORMAL, text="连接"))

        threading.Thread(target=_worker, daemon=True).start()

    def _restart_adb(self):
        """重启ADB服务"""
        gui_logger.info("[设置] 点击按钮: 重启ADB")
        # 停止所有标签运行
        self.parent.stop_all_tabs()
        # 锁定UI
        self.lock_adb_section()
        for tab in self.parent.tabs:
            tab.lock_for_adb_starting()
            tab.log("正在重启ADB，请稍候...")

        def _worker():
            """后台线程体。"""
            import subprocess
            try:
                ir = ImageRecognizer()
                subprocess.run([ir.adb_path, "kill-server"], capture_output=True, timeout=10)
                subprocess.run([ir.adb_path, "start-server"], capture_output=True, timeout=10)
            except Exception:
                pass
            # 刷新设备列表
            try:
                for tab in self.parent.tabs:
                    tab.refresh_devices()
            except Exception:
                pass
            # 回到主线程解锁并提示
            self.parent.root.after(0, self._on_adb_restarted)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_adb_restarted(self):
        """ADB重启完成后的回调"""
        gui_logger.info("[设置] ADB重启完成")
        self.unlock_adb_section()
        for tab in self.parent.tabs:
            tab.unlock_after_adb_started()
            tab.log("ADB已重启")

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

    # ---------------------------- 系统通知 ----------------------------

    def _create_notify_section(self, parent_frame):
        """构建「系统通知」设置区。"""
        notify_group = self._create_group(parent_frame, "系统通知",
            "任务结束时发送 Windows 系统通知（屏幕右下角弹窗）。\n"
            "任务完成、次数达成、识别到指定图片时发送完成通知；\n"
            "连续点击异常、被顶号等异常停止时发送错误通知。\n"
            "“完成提示”/“错误提示”按钮用于测试通知能否正常弹出。\n"
            "手动点击“停止”结束任务时不会发送通知。")

        toggle_row = self._make_row(notify_group, "启用系统通知",
            "任务完成、次数达成时发送完成通知；异常停止时发送错误通知。")
        ttk.Checkbutton(toggle_row, variable=self.settings_notify_var,
                        style="Card.TCheckbutton",
                        command=self.save_settings).pack(side=tk.RIGHT, padx=(10, 0))

        test_row = self._make_row(notify_group, "通知测试", "确认 Windows 通知能否正常弹出。")
        test_box = ttk.Frame(test_row, style="Card.TFrame")
        test_box.pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(test_box, text="完成提示", width=9,
                   command=self._test_notify_complete).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(test_box, text="错误提示", width=9,
                   command=self._test_notify_error).pack(side=tk.LEFT)

    def _test_notify_complete(self):
        """发一条完成通知做测试。"""
        gui_logger.info("[设置] 点击按钮: 测试完成通知")
        test_complete()

    def _test_notify_error(self):
        """发一条错误通知做测试。"""
        gui_logger.info("[设置] 点击按钮: 测试错误通知")
        test_error()

    # ---------------------------- 日志与更新 ----------------------------

    def _open_log_folder(self):
        """在资源管理器里打开日志目录。"""
        gui_logger.info("[设置] 点击按钮: 打开日志文件夹")
        import subprocess
        from adb import get_log_dir
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
        """删除日志目录下的所有 .log 文件。"""
        gui_logger.info("[设置] 点击按钮: 清空日志")
        from adb import get_log_dir
        log_dir = get_log_dir()
        cleared = 0
        try:
            filenames = os.listdir(log_dir)
        except OSError as e:
            # 日志目录不可读（被占用/权限不足）时不要抛到 Tk 事件循环
            if len(self.parent.tabs) > 0:
                self.parent.tabs[0].log(f"读取日志目录失败: {e}")
            return
        for filename in filenames:
            if filename.endswith('.log'):
                try:
                    file_path = os.path.join(log_dir, filename)
                    os.remove(file_path)
                    cleared += 1
                except OSError:
                    pass
        if len(self.parent.tabs) > 0:
            self.parent.tabs[0].log(f"已清空 {cleared} 个日志文件")

    def _copy_password(self):
        """复制网盘密码到剪贴板。"""
        gui_logger.info("[设置] 点击按钮: 复制网盘密码")
        self.parent.root.clipboard_clear()
        self.parent.root.clipboard_append("62m8")
        self.parent.root.update()

    def _open_url(self, url, action):
        """用系统默认浏览器打开链接。

        机器上没有可用浏览器时 webbrowser.open 会抛 webbrowser.Error，
        这里吞掉并把失败写进日志与运行日志，不让它冒泡到 Tk 事件循环。
        """
        gui_logger.info(f"[设置] 点击按钮: {action}")
        try:
            webbrowser.open(url)
        except Exception as e:
            gui_logger.error(f"打开链接失败 {url}: {e}")
            if len(self.parent.tabs) > 0:
                self.parent.tabs[0].log(f"打开链接失败: {e}")

    def _open_update_link(self):
        """打开网盘更新页。"""
        self._open_url("https://wwbet.lanzoum.com/b00ct17efa", "更新软件")

    def _open_github(self):
        """打开 GitHub 仓库页。"""
        self._open_url("https://github.com/haixingtaohai/YYS-AUTO", "打开GitHub仓库")

    def _copy_qq_group(self):
        """复制 QQ 群号到剪贴板。"""
        gui_logger.info("[设置] 点击按钮: 复制QQ群号")
        self.parent.root.clipboard_clear()
        self.parent.root.clipboard_append("647871264")
        self.parent.root.update()

    def _copy_email(self):
        """复制作者邮箱到剪贴板。"""
        gui_logger.info("[设置] 点击按钮: 复制作者邮箱")
        self.parent.root.clipboard_clear()
        self.parent.root.clipboard_append("haixingtaohai@163.com")
        self.parent.root.update()
