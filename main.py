"""YYS-AUTO 启动入口。

这里只做三件事：把项目根目录放进 sys.path、设置 Windows 进程标识与图标、
启动主窗口。界面逻辑在 ui/ 包里：

- ``ui/app.py``          主窗口、菜单栏、配置持久化、对话框
- ``ui/device_tab.py``   单个设备标签页
- ``ui/settings_tab.py`` 设置标签页
- ``ui/scene_runner.py`` 运行循环与场景调用
- ``ui/ime.py``          输入法控制
- ``ui/widgets.py``      自定义控件

场景处理逻辑在 ``scenes/`` 包里，场景名到模块的映射见 ``scenes/registry.py``。
"""

import os
import sys

# 必须最先执行：后面所有 `import adb` / `import wav` / `from scenes import ...`
# 都依赖项目根目录在 sys.path 上。
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import ctypes
import tkinter as tk

import notification
import paths
from ui.app import AutoClickerUI

# Windows AppUserModelID：任务栏图标与系统通知的归属都靠它，必须与
# notification._APP_ID 保持一致，并且要在创建任何窗口之前设置。
APP_USER_MODEL_ID = "yysauto.application.v2.17"

# 导入期是否隐藏过控制台。冒烟测试靠它确认没有副作用提前发生。
_CONSOLE_HIDDEN = False


def _hide_console():
    """隐藏 Windows 控制台窗口。"""
    global _CONSOLE_HIDDEN
    if os.name != 'nt':
        return
    try:
        ctypes.windll.user32.ShowWindow(
            ctypes.windll.kernel32.GetConsoleWindow(), 0
        )
        _CONSOLE_HIDDEN = True
    except Exception:
        pass


def _show_fatal_error(message):
    """启动失败时弹一个原生对话框。

    控制台此时已经隐藏，bat/run.bat 又会掉进 install.bat 的 pause 卡住，
    没有这个弹窗用户只会看到程序"闪一下就没了"。
    """
    if os.name == 'nt':
        try:
            ctypes.windll.user32.MessageBoxW(
                None, str(message), "YYS-AUTO 启动失败", 0x10
            )
            return
        except Exception:
            pass
    print(message, file=sys.stderr)


def main():
    """设置进程标识、隐藏控制台、创建主窗口。"""
    try:
        if os.name == 'nt':
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    APP_USER_MODEL_ID
                )
            except Exception:
                pass

        _hide_console()
        notification.ensure_registered()

        root = tk.Tk()
        if paths.ICON_PATH:
            try:
                root.iconbitmap(paths.ICON_PATH)
            except Exception:
                pass

        AutoClickerUI(root)
        root.mainloop()
    except Exception as exc:  # noqa: BLE001 - 启动期任何异常都要让用户看见
        import traceback
        _show_fatal_error(f"{exc}\n\n{traceback.format_exc()}")
        raise


if __name__ == "__main__":
    main()
