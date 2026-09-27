"""自定义 Tk 小部件。"""

import tkinter as tk


class ToolTip:
    """鼠标悬停时显示提示文字"""
    def __init__(self, widget, text):
        """绑定鼠标进入/离开事件并记录提示文本。"""
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind('<Enter>', self._show)
        widget.bind('<Leave>', self._hide)

    def _show(self, event=None):
        """在控件下方弹出提示窗口。"""
        if self.tip_window:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=('Microsoft YaHei', 9), wraplength=300)
        label.pack()

    def _hide(self, event=None):
        """关闭提示窗口。"""
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None