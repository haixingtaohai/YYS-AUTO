"""Windows 输入法（IME）控制。

GUI 需要在输入框获得焦点时才启用输入法、其余时间禁用——否则自动化过程中输入法
候选框会弹出并截获按键。仅在 Windows 上生效，其它平台全部退化为空操作。
"""

import ctypes
import os
import tkinter as tk
from tkinter import ttk


_ime_hwnd = None       # 主窗口句柄
_ime_original = None   # 原始输入法上下文
if os.name == 'nt':
    try:
        _imm32 = ctypes.WinDLL('imm32', use_last_error=True)
    except:
        _imm32 = None
else:
    _imm32 = None

def init_ime(hwnd):
    """初始化：保存原始输入法上下文并禁用"""
    global _ime_hwnd, _ime_original
    _ime_hwnd = hwnd
    if _imm32:
        try:
            _ime_original = _imm32.ImmAssociateContext(hwnd, 0)  # 关联NULL，禁用IME
        except:
            _ime_original = None

def disable_ime():
    """窗口级禁用输入法"""
    if _imm32 and _ime_hwnd:
        try:
            _imm32.ImmAssociateContext(_ime_hwnd, 0)
        except:
            pass

def enable_ime():
    """窗口级启用输入法"""
    if _imm32 and _ime_hwnd:
        try:
            # 传入原始句柄或0xFFFFFFFF让系统分配默认上下文
            ctx = _ime_original if _ime_original else 0xFFFFFFFF
            _imm32.ImmAssociateContext(_ime_hwnd, ctx)
        except:
            pass

def on_entry_focus_in(event):
    """输入框获得焦点时启用输入法"""
    enable_ime()

def on_entry_focus_out(event):
    """输入框失去焦点后延迟检查，仍在输入框则保持，否则禁用"""
    event.widget.after(10, check_focus_for_ime, event.widget)

def check_focus_for_ime(widget):
    """检查焦点是否仍在输入框内"""
    try:
        focused = widget.winfo_toplevel().focus_get()
        if isinstance(focused, (tk.Entry, tk.Text, ttk.Entry, ttk.Combobox)):
            return
    except:
        pass
    disable_ime()

def on_root_focus_in(event):
    """窗口重获焦点时，若不在输入框内则重新禁用IME"""
    event.widget.after(20, recheck_ime_on_focus, event.widget)

def recheck_ime_on_focus(widget):
    """重新检查并确保IME状态正确"""
    try:
        focused = widget.focus_get()
        if isinstance(focused, (tk.Entry, tk.Text, ttk.Entry, ttk.Combobox)):
            enable_ime()
        else:
            disable_ime()
    except:
        disable_ime()