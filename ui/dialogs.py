"""主窗口的弹出对话框：关于、快捷键说明、运行时长记录，以及外部链接/文档。

做成 mixin 挂在 AutoClickerUI 上，这样 ``self.root`` / ``self.tabs`` 等引用不用改。

居中逻辑（``_center_dialog``）原来在三个对话框里各抄了一遍，这里合并成一份。
"""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk

import paths
from adb import get_gui_logger

gui_logger = get_gui_logger()

# 运行时长记录窗口的固定尺寸
USAGE_WINDOW_WIDTH = 600
USAGE_WINDOW_HEIGHT = 420

# 排行榜前三名的颜色（名次标签 / 数据条各一套）
RANK_TEXT_COLORS = {1: "#eab308", 2: "#94a3b8", 3: "#cd853f"}
RANK_BAR_COLORS = {1: "#6c5ce7", 2: "#3b82f6", 3: "#10b981"}
RANK_TEXT_FALLBACK = "#64748b"
RANK_BAR_FALLBACK = "#4a5568"

# 数据条满格宽度（像素）
BAR_MAX_WIDTH = 180

SHORTCUTS = [
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


def _format_hms(seconds):
    """把秒数格式化成 HH:MM:SS。"""
    return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"


def _format_hm(seconds):
    """把秒数格式化成 HH:MM（总计时长只精确到分钟）。"""
    return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}"


def _percent(value, total):
    """百分比字符串，分母为 0 时返回 0.00%。"""
    return f"{value / total * 100:.2f}%" if total > 0 else "0.00%"


class DialogsMixin:
    """对话框与外部链接。"""

    def _center_dialog(self, top, width=None, height=None):
        """把对话框居中到主窗口上。

        不传宽高时用对话框当前的实测尺寸，传了就同时设置尺寸。
        """
        top.update_idletasks()
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_w = self.root.winfo_width()
        main_h = self.root.winfo_height()
        top_w = width if width is not None else top.winfo_width()
        top_h = height if height is not None else top.winfo_height()
        x = main_x + (main_w - top_w) // 2
        y = main_y + (main_h - top_h) // 2
        if width is not None and height is not None:
            top.geometry(f"{top_w}x{top_h}+{x}+{y}")
        else:
            top.geometry(f"+{x}+{y}")

    def _show_about(self):
        """显示关于对话框，居中于主窗口"""
        gui_logger.info("点击菜单: 关于")
        top = tk.Toplevel(self.root)
        top.title("关于")
        top.resizable(False, False)
        top.transient(self.root)
        top.grab_set()

        # 标题区
        ttk.Label(top, text="YYS-AUTO  v2.16", font=('Microsoft YaHei', 16, 'bold')).pack(padx=40, pady=(20, 2))
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

        self._center_dialog(top)

    def _show_shortcuts(self):
        """显示快捷键说明窗口，居中于主窗口"""
        gui_logger.info("点击菜单: 快捷键说明")
        top = tk.Toplevel(self.root)
        top.title("快捷键说明")
        top.resizable(False, False)
        top.transient(self.root)
        top.grab_set()

        ttk.Label(top, text="快捷键说明", font=('Microsoft YaHei', 12, 'bold')).pack(padx=30, pady=(15, 10))

        frame = ttk.Frame(top)
        frame.pack(padx=20, pady=(0, 10))

        for key, desc in SHORTCUTS:
            row = ttk.Frame(frame)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=key, font=('Microsoft YaHei', 10, 'bold'), width=12, anchor=tk.E).pack(side=tk.LEFT, padx=(0, 15))
            ttk.Label(row, text=desc, font=('Microsoft YaHei', 10)).pack(side=tk.LEFT)

        ttk.Button(top, text="确定", command=top.destroy, width=10).pack(pady=(5, 15))

        self._center_dialog(top)

    # ---- 运行时长记录 ----

    def _build_usage_header(self, parent, total_seconds):
        """标题行：左边标题，右边总计时长。"""
        header = ttk.Frame(parent, padding="8")
        header.pack(fill=tk.X)
        ttk.Label(header, text="运行时长记录",
                  font=('Microsoft YaHei', 12, 'bold')).pack(side=tk.LEFT)
        if total_seconds > 0:
            ttk.Label(header, text=f"总计: {_format_hm(total_seconds)}",
                      font=('Microsoft YaHei', 9)).pack(side=tk.RIGHT)

    def _build_usage_columns(self, parent):
        """表头 + 分隔线。"""
        col_frame = ttk.Frame(parent, padding="0")
        col_frame.pack(fill=tk.X, padx=15, pady=(8, 2))
        for text, width in (("排名", 5), ("场景", 12), ("使用时长", 10)):
            ttk.Label(col_frame, text=text, width=width,
                      font=('Microsoft YaHei', 9, 'bold')).pack(side=tk.LEFT)
        ttk.Label(col_frame, text="", width=2).pack(side=tk.LEFT)
        for text, width in (("占比", 7), ("相对时长", 9)):
            ttk.Label(col_frame, text=text, width=width,
                      font=('Microsoft YaHei', 9, 'bold')).pack(side=tk.LEFT)

        ttk.Frame(parent, height=1, style="TSeparator").pack(fill=tk.X, padx=12)

    def _build_usage_scroll_area(self, parent):
        """可滚动的排行榜容器，返回内部用于放行的 Frame。"""
        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        canvas = tk.Canvas(canvas_frame, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", tags="inner")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.bind("<MouseWheel>",
                    lambda event: canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))
        canvas.bind("<Configure>",
                    lambda event: canvas.itemconfig("inner", width=event.width))

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        return scrollable_frame

    def _build_usage_row(self, parent, rank, scene_name, seconds, total_seconds, max_seconds):
        """排行榜的一行：名次、场景、时长、占比、相对时长、数据条。"""
        row_frame = ttk.Frame(parent)
        row_frame.pack(fill=tk.X, padx=8, pady=2)

        ttk.Label(row_frame, text=f"#{rank}", width=5,
                  foreground=RANK_TEXT_COLORS.get(rank, RANK_TEXT_FALLBACK),
                  font=('Microsoft YaHei', 9, 'bold')).pack(side=tk.LEFT)
        ttk.Label(row_frame, text=scene_name, width=12,
                  font=('Microsoft YaHei', 9)).pack(side=tk.LEFT)
        ttk.Label(row_frame, text=_format_hms(seconds), width=10,
                  font=('Microsoft YaHei', 9)).pack(side=tk.LEFT)
        ttk.Label(row_frame, text="", width=2).pack(side=tk.LEFT)
        # 占比：该场景时长占总运行时间
        ttk.Label(row_frame, text=_percent(seconds, total_seconds), width=7,
                  font=('Microsoft YaHei', 8)).pack(side=tk.LEFT)
        # 相对时长：以第一名为 100%
        ttk.Label(row_frame, text=_percent(seconds, max_seconds), width=9,
                  font=('Microsoft YaHei', 8)).pack(side=tk.LEFT)

        bar_frame = tk.Frame(row_frame, height=16)
        bar_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        bar_frame.pack_propagate(False)

        bar_canvas = tk.Canvas(bar_frame, height=16, highlightthickness=0, bd=0)
        bar_canvas.pack(fill=tk.BOTH, expand=True)

        bar_width = int((seconds / max_seconds) * BAR_MAX_WIDTH) if max_seconds > 0 else 0
        if bar_width > 0:
            bar_canvas.create_rectangle(
                0, 1, bar_width, 15,
                fill=RANK_BAR_COLORS.get(rank, RANK_BAR_FALLBACK), outline=""
            )

    def _show_usage_records(self):
        """显示运行时长记录排行榜窗口"""
        gui_logger.info("点击菜单: 运行时长记录")
        top = tk.Toplevel(self.root)
        top.title("运行时长记录")
        top.transient(self.root)
        top.minsize(480, 320)

        # 重新加载最新记录
        self.usage_records = self._load_usage_records()

        if paths.ICON_PATH:
            try:
                top.iconbitmap(paths.ICON_PATH)
            except Exception:
                pass

        total_seconds = sum(self.usage_records.values())
        self._build_usage_header(top, total_seconds)

        if not self.usage_records:
            ttk.Label(top, text="暂无运行时长记录",
                      font=('Microsoft YaHei', 11)).pack(expand=True, pady=60)
        else:
            self._build_usage_columns(top)
            scrollable_frame = self._build_usage_scroll_area(top)

            sorted_records = sorted(self.usage_records.items(),
                                    key=lambda item: item[1], reverse=True)
            max_seconds = sorted_records[0][1] if sorted_records else 1
            for rank, (scene_name, seconds) in enumerate(sorted_records, 1):
                self._build_usage_row(scrollable_frame, rank, scene_name,
                                      seconds, total_seconds, max_seconds)

        btn_frame = ttk.Frame(top, padding="8")
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="关闭", command=top.destroy,
                   width=10).pack(side=tk.RIGHT, padx=5)

        self._center_dialog(top, USAGE_WINDOW_WIDTH, USAGE_WINDOW_HEIGHT)

    # ---- 外部链接与文档 ----

    def _open_url(self, url, action):
        """用系统默认浏览器打开链接，失败写日志而不是抛到 Tk 事件循环。"""
        gui_logger.info(f"点击菜单: {action}")
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception as e:
            gui_logger.error(f"打开链接失败 {url}: {e}")
            if self.tabs:
                self.tabs[0].log(f"打开链接失败: {e}")

    def _open_uu_remote(self):
        """打开UU远程官网"""
        self._open_url("https://uuyc.163.com/", "UU远程官网")

    def _open_doc_folder(self):
        """打开使用说明文档文件夹"""
        gui_logger.info("点击菜单: 打开使用说明文档")
        doc_folder = paths.DOC_FOLDER
        try:
            if not os.path.exists(doc_folder):
                if self.tabs:
                    self.tabs[0].log("使用说明文档文件夹不存在")
                return
            if sys.platform.startswith('win'):
                os.startfile(doc_folder)
            else:
                subprocess.Popen(['xdg-open', doc_folder])
        except Exception as e:
            if self.tabs:
                self.tabs[0].log(f"打开文档文件夹失败: {e}")
