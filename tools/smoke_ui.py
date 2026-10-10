"""GUI 冒烟测试 + 路径回归检查。

两件事：

1. **路径回归**：``__file__`` 相对路径一旦从项目根目录搬到 ``ui/`` 子包，就会静默变成
   ``<root>/ui/config.json`` 之类，表现为"配置和标签页全没了"。这里逐个断言路径常量
   仍指向重构前的绝对位置。
2. **构造冒烟**：真的建一个 ``tk.Tk()`` 并实例化 ``AutoClickerUI``，跑完 __init__ →
   setup_ui → 菜单 → 设置页 → 设备页的全过程，断言关键属性都在。

不会写任何文件：config / usage 路径被指向临时目录。

用法::

    python tools/smoke_ui.py
"""

from __future__ import annotations

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

FAILURES = []


def check(label, condition, detail=""):
    if condition:
        print(f"  [OK]   {label}")
    else:
        print(f"  [FAIL] {label} {detail}")
        FAILURES.append(label)


def check_paths():
    """路径常量的绝对位置必须与重构前一致。"""
    print("路径回归检查")

    import paths

    expected = {
        "ROOT_DIR": ROOT,
        "ICON_PATH": os.path.join(ROOT, "icon.ico"),
        "PNG_BASE_FOLDER": os.path.join(ROOT, "png"),
        "CONFIG_FILE": os.path.join(ROOT, "config.json"),
        "USAGE_RECORDS_FILE": os.path.join(ROOT, "usage_records.json"),
        "DOC_FOLDER": os.path.join(ROOT, "使用文档第一次使用必看"),
        "PLATFORM_TOOLS_DIR": os.path.join(ROOT, "platform-tools"),
        "ADB_EXE": os.path.join(ROOT, "platform-tools", "adb.exe"),
    }
    for name, want in expected.items():
        got = getattr(paths, name, None)
        check(f"{name} == {want}", got == want, f"(实际 {got})")

    check("png 目录存在", os.path.isdir(paths.PNG_BASE_FOLDER))
    check("文档目录存在", os.path.isdir(paths.DOC_FOLDER))


def check_no_duplicate_scene_modules():
    """scenes 必须是唯一的包，不能同时存在顶层同名模块。"""
    print("场景模块唯一性检查")

    import scenes  # noqa: F401
    from scenes import registry

    for preset, module in registry.SCENE_MODULES.items():
        name = module.__name__
        check(f"{preset} -> {name}", name.startswith("scenes."), f"(实际 {name})")

    duplicated = [n for n in sys.modules
                  if n in ("yyh", "htdr", "sj", "dy", "dj", "dg", "k28", "k281",
                           "k280", "yjsl", "yl", "ql", "dfw", "jjtp", "hdpt", "pcgd",
                           "zoushen", "dinghao", "guanbijiacheng")]
    check("没有顶层的重复场景模块", not duplicated, f"(发现 {duplicated})")


def check_no_import_side_effects():
    """导入阶段不应该隐藏控制台。"""
    print("导入副作用检查")

    import main  # noqa: F401

    check("main 模块可导入", True)
    check("main 未在导入期隐藏控制台", getattr(main, "_CONSOLE_HIDDEN", False) is False)


def check_gui_constructs():
    """真正构造一次 GUI。"""
    print("GUI 构造冒烟")

    import tkinter as tk

    import paths
    from ui.app import AutoClickerUI

    with tempfile.TemporaryDirectory() as tmp:
        # 把配置/记录指向临时目录，绝不碰真实文件
        paths.CONFIG_FILE = os.path.join(tmp, "config.json")
        paths.USAGE_RECORDS_FILE = os.path.join(tmp, "usage_records.json")

        root = tk.Tk()
        root.withdraw()
        try:
            app = AutoClickerUI(root)
            check("AutoClickerUI 构造成功", True)
            check("notebook 已建立", hasattr(app, "notebook"))
            check("settings_tab 已建立", hasattr(app, "settings_tab"))
            check("tabs 非空", len(app.tabs) > 0, f"(实际 {len(app.tabs)})")
            check("presets 有 14 个场景", len(app.presets) == 14,
                  f"(实际 {len(app.presets)})")
            check("saved_config 是 dict", isinstance(app.saved_config, dict))

            tab = app.tabs[0]
            for attr in ("device_combo", "threshold_entry", "target_count_var",
                         "start_btn", "stop_btn", "log_text", "current_preset"):
                check(f"DeviceTab.{attr} 存在", hasattr(tab, attr))

            # 场景注册表与预设表必须一一对应
            from scenes.registry import SCENE_MODULES
            missing = set(app.presets) - set(SCENE_MODULES)
            extra = set(SCENE_MODULES) - set(app.presets)
            check("预设与场景模块一一对应", not missing and not extra,
                  f"(缺 {missing} / 多 {extra})")

            # 跑一段事件循环：after(0) 恢复窗口位置、after(50) 设置标签名、
            # after(500) 恢复选中标签都挂在这上面，不泵一次就测不到。
            import time as _time
            deadline = _time.time() + 1.2
            errors = []
            root.report_callback_exception = lambda *a: errors.append(a[1])
            while _time.time() < deadline:
                root.update()
                _time.sleep(0.02)
            check("事件循环无回调异常", not errors, f"(实际 {errors[:2]})")

            # 菜单栏各命令至少能取到，避免 build 完但函数名写错
            check("有菜单栏", bool(root.cget("menu")))

            # 拆分函数时容易把原函数的尾巴留在新函数里：_kill_adb_server 曾经
            # 带着一句 on_window_close()，导致「重启ADB并重启程序」会先把窗口关掉。
            import inspect
            from ui.app import AutoClickerUI
            for name in ("_kill_adb_server", "_reexec", "_kill_adb_and_exit"):
                src = inspect.getsource(getattr(AutoClickerUI, name))
                if name == "_kill_adb_server":
                    check(f"{name} 不会关闭窗口", "on_window_close" not in src)
                else:
                    check(f"{name} 只有一处收尾调用",
                          src.count("on_window_close") + src.count("_reexec") <= 1)

            # 锁定/解锁是成对的，成对调用后控件必须回到可用状态
            tab = app.tabs[0]
            tab.lock_controls()
            locked = str(tab.threshold_entry.cget("state"))
            tab.unlock_controls()
            unlocked = str(tab.threshold_entry.cget("state"))
            check("lock_controls 会禁用控件", locked == "disabled", f"(实际 {locked})")
            check("unlock_controls 会恢复控件", unlocked == "normal", f"(实际 {unlocked})")

            # 这些动作不该抛异常
            for action, call in (("reset_defaults", tab.reset_defaults),
                                 ("refresh_all_devices", tab.refresh_all_devices),
                                 ("restore_tab_selection", app.restore_tab_selection)):
                try:
                    call()
                    check(f"{action}() 不抛异常", True)
                except Exception as exc:  # noqa: BLE001
                    check(f"{action}() 不抛异常", False, f"({exc!r})")
        finally:
            root.destroy()


def main():
    check_paths()
    print()
    check_no_duplicate_scene_modules()
    print()
    check_no_import_side_effects()
    print()
    check_gui_constructs()
    print()

    if FAILURES:
        print(f"FAIL: {len(FAILURES)} 项未通过")
        for item in FAILURES:
            print("  - " + item)
        return 1
    print("PASS: 全部检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
