"""主窗口：标签页容器、菜单栏、配置持久化与各类对话框。"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk

import paths
from adb import get_gui_logger
from presets import PRESETS
from ui import config_store, ime
from ui.device_tab import DeviceTab
from ui.dialogs import DialogsMixin
from ui.settings_tab import SettingsTab

gui_logger = get_gui_logger()


def _adb_path():
    """优先用自带的 adb，找不到时退回 PATH 上的 adb。"""
    return paths.ADB_EXE if os.path.exists(paths.ADB_EXE) else "adb"


class AutoClickerUI(DialogsMixin):
    def __init__(self, root):
        """构建主窗口：先备好状态与路径，再建 notebook、菜单栏和设备标签页。"""
        self.root = root
        self.root.title("YYS-AUTOv2.17")
        self.root.geometry("640x460")
        self.root.minsize(640, 460)  # 设置最小尺寸

        # 初始化标志
        self.initialized = False
        
        # 再次确保设置窗口图标（使用已准备好的 icon 路径）
        if paths.ICON_PATH:
            try:
                self.root.iconbitmap(paths.ICON_PATH)
            except:
                try:
                    self.root.iconbitmap(default=paths.ICON_PATH)
                except:
                    pass

        self.png_base_folder = paths.PNG_BASE_FOLDER

        # 场景预设表见 presets.py；这里复制一份，避免运行中被外部改动影响
        self.presets = dict(PRESETS)
        
        self.tab_count = 0
        self.tabs = []
        
        # 队员司机联动开关
        self.link_enabled = False
        
        # 关闭加成设置
        self.close_jiacheng_enabled = False
        self.close_jiacheng_wait = 30  # 默认30秒
        
        # 被顶号后等待进入游戏设置
        self.dinghao_wait = 30  # 默认30秒
        
        # 绘卷模式设置
        self.huijuan_mode = False
        
        # 斗技段位晋升结束程序设置
        self.dj_jinsheng_stop = False

        # 契灵结契选择
        self.ql_fangqi = True
        self.ql_zaici = False

        # 提示音设置
        self.sound_enabled = False
        self.sound_file = ""  # 选中的音效文件名
        
        # 日志设置
        self.logging_enabled = False
        
        # 系统通知设置
        self.notify_enabled = True
        
        # 随机暂停状态设置
        self.zoushen_enabled = False        # 默认关闭
        self.zoushen_trigger_min = 60       # 随机暂停触发时间起始值（秒）
        self.zoushen_trigger_max = 180      # 随机暂停触发时间最终值（秒）
        self.zoushen_duration_min = 5       # 随机暂停持续时间起始值（秒）
        self.zoushen_duration_max = 15      # 随机暂停持续时间最终值（秒）
        self.zoushen_whitelist = []         # 随机暂停白名单场景（白名单内场景不触发随机暂停）
        
        # ADB设置
        self.adb_ip = "127.0.0.1"
        self.adb_port = "16384"
        
        # 加载保存的配置
        self.config_file = paths.CONFIG_FILE
        self.usage_records_file = paths.USAGE_RECORDS_FILE
        self.usage_records = self._load_usage_records()
        self.saved_config = self.load_config()

        # 恢复窗口位置（延迟到窗口显示后执行，避免被窗口管理器覆盖）
        if "window_geometry" in self.saved_config:
            saved_geometry = self.saved_config["window_geometry"]
            self.root.after(0, lambda g=saved_geometry: self.root.geometry(g))

        self.setup_ui()

        # 输入法控制：默认禁用，仅输入框获得焦点时启用。
        # 这些 bind_class 只能注册一次——它们在 root 上追加全局处理器，
        # 放进 DeviceTab/SettingsTab 会变成每个标签页注册一遍，焦点事件触发 N 次。
        ime.init_ime(self.root.winfo_id())
        self.root.bind('<FocusIn>', ime.on_root_focus_in, add='+')
        self.root.bind('<Button-1>', self._on_root_click)  # 点击空白区域取消输入框聚焦
        self.root.bind_class('Entry', '<FocusIn>', ime.on_entry_focus_in, add='+')
        self.root.bind_class('Entry', '<FocusOut>', ime.on_entry_focus_out, add='+')
        self.root.bind_class('Text', '<FocusIn>', ime.on_entry_focus_in, add='+')
        self.root.bind_class('Text', '<FocusOut>', ime.on_entry_focus_out, add='+')
        self.root.bind_class('TEntry', '<FocusIn>', ime.on_entry_focus_in, add='+')
        self.root.bind_class('TEntry', '<FocusOut>', ime.on_entry_focus_out, add='+')
        self.root.bind_class('TCombobox', '<FocusIn>', ime.on_entry_focus_in, add='+')
        self.root.bind_class('TCombobox', '<FocusOut>', ime.on_entry_focus_out, add='+')

        self.restore_tab_selection()

        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)

        # 标记初始化完成
        self.initialized = True

    def load_config(self):
        """加载保存的配置。

        返回值保留文件里的全部键（包括 tabs / window_geometry 等本类不认识的），
        save_config 会把它整体写回，避免清空标签页配置。
        """
        config = config_store.load(self.config_file)
        config_store.apply(config, self)
        return config

    def save_config(self):
        """保存当前配置。任何一步失败都静默跳过，不影响正在运行的任务。"""
        config = self.saved_config
        config_store.collect(self, config)

        try:
            config["window_geometry"] = self.root.geometry()
        except Exception:
            pass
        try:
            config["last_tab"] = self.notebook.index(self.notebook.select())
        except Exception:
            pass

        config_store.write(config, self.config_file)

    def _load_usage_records(self):
        """加载运行时长记录"""
        return config_store.load_usage_records(self.usage_records_file)

    def _save_usage_records(self):
        """保存运行时长记录"""
        config_store.save_usage_records(self.usage_records, self.usage_records_file)

    def record_usage(self, preset_name, seconds):
        """记录场景使用时长（累加）"""
        if seconds <= 0:
            return
        if preset_name not in self.usage_records:
            self.usage_records[preset_name] = 0
        self.usage_records[preset_name] += seconds
        self._save_usage_records()
    
    def _restart_adb_and_app(self):
        """重启ADB并重启程序"""
        gui_logger.info("点击菜单: 重启ADB并重启程序")
        self.stop_all_tabs()
        self.save_config()
        ime.enable_ime()
        self._kill_adb_server()
        self._reexec(sys.executable)

    def _reexec(self, python):
        """用同一个解释器和同一份参数重新启动本程序。"""
        try:
            os.execl(python, python, *sys.argv)
        except OSError as e:
            gui_logger.error(f"重启程序失败: {e}")
            if self.tabs:
                self.tabs[0].log(f"重启程序失败: {e}")

    def _restart_app(self):
        """重启工具"""
        gui_logger.info("点击菜单: 重启工具")
        self.stop_all_tabs()
        self.save_config()
        ime.enable_ime()
        self._reexec(sys.executable)

    def _kill_adb_and_exit(self):
        """关闭ADB进程并退出程序"""
        gui_logger.info("点击菜单: 关闭ADB并退出")
        # 先停止所有标签任务
        self.stop_all_tabs()
        self._kill_adb_server()
        # 退出程序
        self.on_window_close()

    def _kill_adb_server(self):
        """结束 adb 服务进程。失败不影响后续流程。"""
        try:
            subprocess.run([_adb_path(), "kill-server"], capture_output=True, timeout=10)
        except Exception as e:
            gui_logger.error(f"关闭ADB失败: {e}")

    def on_window_close(self):
        """窗口关闭：恢复输入法、保存配置、销毁窗口。"""
        ime.enable_ime()
        self.save_config()
        self.root.destroy()
    
    def restore_tab_selection(self):
        """延时把焦点切回上次使用的标签页。"""
        # 恢复上次选择的标签（注意：第0位是设置标签）
        last_tab = self.saved_config.get("last_tab", 1)

        # 确保last_tab在有效范围内
        if last_tab >= 0 and last_tab < self.notebook.index('end'):
            # 使用after方法确保在UI完全初始化后再选择标签
            def select_tab():
                """按序号选中标签页。"""
                try:
                    self.notebook.select(last_tab)
                except Exception as e:
                    pass
            self.root.after(500, select_tab)
        else:
            pass
    
    def on_tab_changed(self, event):
        """标签页切换时更新窗口标题。"""
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

        # 程序菜单
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="重启工具", command=self._restart_app)
        file_menu.add_separator()
        file_menu.add_command(label="重启ADB并重启程序", command=self._restart_adb_and_app)
        file_menu.add_command(label="关闭ADB并退出", command=self._kill_adb_and_exit)
        file_menu.add_separator()
        file_menu.add_command(label="退出程序 (Alt+F4)", command=self.on_window_close)
        menubar.add_cascade(label="程序(P)", menu=file_menu, underline=3)

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
        func_menu.add_separator()
        func_menu.add_checkbutton(label="契灵放弃结契",
                                  variable=self.settings_tab.settings_ql_fangqi_var,
                                  command=lambda: [self.settings_tab._toggle_ql_fangqi(), self.settings_tab.save_settings()])
        func_menu.add_checkbutton(label="契灵再次结契",
                                  variable=self.settings_tab.settings_ql_zaici_var,
                                  command=lambda: [self.settings_tab._toggle_ql_zaici(), self.settings_tab.save_settings()])
        func_menu.add_separator()
        func_menu.add_checkbutton(label="挑战结束后关闭御魂加成",
                                  variable=self.settings_tab.settings_close_jiacheng_var,
                                  command=self.settings_tab.save_settings)
        func_menu.add_separator()
        func_menu.add_command(label="设置关闭加成等待秒数",
                              command=self.settings_tab._set_close_jiacheng_wait)
        func_menu.add_command(label="设置被顶号后等待秒数",
                              command=self.settings_tab._set_dinghao_wait)
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
        update_menu.add_command(label="跳转网盘更新软件", command=self.settings_tab._open_update_link)
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
        run_menu.add_separator()
        run_menu.add_command(label="运行时长记录", command=self._show_usage_records)
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
        """搭建主界面：notebook → 设置页 → 菜单栏 → 设备标签页 → 刷新设备。"""
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

        # 恢复上次选择的标签统一放在 __init__ 末尾做，这里不再重复调用，
        # 否则会往 after 队列里塞两次同样的延时选中。

        # 统一处理所有标签的设备选择（子线程，不阻塞UI）
        self._setup_all_devices()

        # 禁用窗口大小调整（放在setup_ui末尾，所有widget布局完毕后设置，
        # 避免在__init__开头设置时改变窗口框架样式干扰Notebook初始渲染）
        self.root.resizable(False, False)
    
    def _setup_all_devices(self):
        """在子线程里统一刷新所有标签页的设备下拉框，不阻塞界面。"""
        # 锁定UI并提示ADB正在启动
        self.settings_tab.lock_adb_section()
        for tab in self.tabs:
            tab.lock_for_adb_starting()
            tab.log("ADB正在启动中，请稍候...")

        # 在子线程中执行ADB设备刷新，避免阻塞主线程
        def _worker():
            """后台线程体。"""
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
        """新建一个设备标签页并切换到它。"""
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
        """清空所有标签页已选的设备。"""
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
        already_running = 0   # 点击前已在运行的标签数
        no_device = 0         # 未选择设备而跳过的标签数
        failed = 0            # 启动失败的标签数
        started = 0           # 本次成功启动的标签数
        for tab in self.tabs:
            if tab.running:
                already_running += 1
                continue
            if not (hasattr(tab, 'device_combo') and tab.device_combo.get()):
                no_device += 1
                continue
            try:
                tab.start_loop()
            except:
                failed += 1
                continue
            if tab.running:
                started += 1
            else:
                failed += 1
        
        # 提示输出到所有标签，避免未选中的标签看不到结果
        msg = f"全部开始：成功启动 {started} 个标签"
        extra = []
        if already_running > 0:
            extra.append(f"点击前已有 {already_running} 个在运行")
        if no_device > 0:
            extra.append(f"{no_device} 个未选择设备")
        if failed > 0:
            extra.append(f"{failed} 个启动失败")
        if extra:
            msg += f"（{'，'.join(extra)}）"
        for tab in self.tabs:
            tab.log(msg)

    def stop_all_tabs(self):
        """一键停止所有标签任务"""
        gui_logger.info("点击按钮: 全部停止")
        already_stopped = 0   # 点击前已停止的标签数
        failed = 0            # 停止失败的标签数
        stopped = 0           # 本次成功停止的标签数
        for tab in self.tabs:
            if not tab.running:
                already_stopped += 1
                continue
            try:
                tab.stop_loop()
            except:
                failed += 1
                continue
            if tab.running:
                failed += 1
            else:
                stopped += 1
        
        # 提示输出到所有标签，避免未选中的标签看不到结果
        msg = f"全部停止：成功停止 {stopped} 个标签"
        extra = []
        if already_stopped > 0:
            extra.append(f"点击前已有 {already_stopped} 个未运行")
        if failed > 0:
            extra.append(f"{failed} 个停止失败")
        if extra:
            msg += f"（{'，'.join(extra)}）"
        for tab in self.tabs:
            tab.log(msg)
    
    def delete_current_tab(self):
        """删除当前标签页（至少保留一个）。"""
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
        """重命名当前标签页。"""
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
