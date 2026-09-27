"""设置标签页：ADB 连接、提示音、系统通知、随机暂停、日志与关于信息。"""

from __future__ import annotations

import os
import subprocess
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
    
    def _add_section_help(self, group_frame, text):
        """给设置页功能区的标题加上❓提示（悬停显示详细说明，与控制页运行参数一致）"""
        title_frame = ttk.Frame(group_frame)
        ttk.Label(title_frame, text=group_frame.cget("text")).pack(side=tk.LEFT)
        q_btn = ttk.Label(title_frame, text="❓", font=('Microsoft YaHei', 9), cursor="hand2")
        q_btn.pack(side=tk.LEFT, padx=(2, 0))
        ToolTip(q_btn, text)
        # 用自定义标题替换LabelFrame默认标题，使❓紧跟在区域名后
        group_frame.configure(labelwidget=title_frame)
        return q_btn

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
            """后台线程体。"""
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
    
    def _test_notify_complete(self):
        """发一条完成通知做测试。"""
        gui_logger.info("[设置] 点击按钮: 测试完成通知")
        test_complete()

    def _test_notify_error(self):
        """发一条错误通知做测试。"""
        gui_logger.info("[设置] 点击按钮: 测试错误通知")
        test_error()

    def _create_notify_section(self, parent_frame):
        """构建「系统通知」设置区。"""
        notify_group = ttk.LabelFrame(parent_frame, text="系统通知", padding="8")
        notify_group.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        self._add_section_help(notify_group,
            "任务结束时发送 Windows 系统通知（屏幕右下角弹窗）。\n"
            "任务完成、次数达成、识别到指定图片时发送完成通知；\n"
            "连续点击异常、被顶号等异常停止时发送错误通知。\n"
            "“完成提示”/“错误提示”按钮用于测试通知能否正常弹出。\n"
            "手动点击“停止”结束任务时不会发送通知。")

        top_row = ttk.Frame(notify_group)
        top_row.pack(fill=tk.X, pady=2)
        ttk.Checkbutton(top_row, text="启用系统通知", variable=self.settings_notify_var,
                        command=self.save_settings).pack(side=tk.LEFT)

        btn_row = ttk.Frame(notify_group)
        btn_row.pack(fill=tk.X, pady=2)
        ttk.Button(btn_row, text="完成提示", command=self._test_notify_complete, width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_row, text="错误提示", command=self._test_notify_error, width=10).pack(side=tk.LEFT)

    def _create_adb_section(self, parent_frame):
        """构建「ADB 连接」设置区。"""
        self.adb_group_frame = ttk.LabelFrame(parent_frame, text="ADB设备连接", padding="8")
        self.adb_group_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        self._add_section_help(self.adb_group_frame,
            "填写模拟器/手机的 ADB 连接地址与端口，点击“连接”后生效。\n"
            "ip地址：如果是本机模拟器连接，填写“127.0.0.1”；如果是局域网其他设备连接，填写设备的IP地址。\n"
            "常用端口：16384（MuMu）、16416（MuMu）、7555（雷电）、62001（夜神旧版）、5555（USB调试）。\n"
            "连接成功后，设备会出现在控制页的“设备选择”下拉框中；\n"
            "若下拉框没有设备，先点“重启ADB”再重新连接。\n"
            "运行中重启ADB会先停止所有标签的任务，期间连接区域会锁定。")

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
            """确认输入并关闭对话框。"""
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
    
    def _set_dinghao_wait(self):
        """弹窗设置被顶号后等待进入游戏时间"""
        gui_logger.info("[设置] 点击按钮: 设置被顶号后等待秒数")
        dialog = tk.Toplevel(self.parent.root)
        dialog.title("设置等待秒数")
        dialog.resizable(False, False)
        dialog.transient(self.parent.root)
        dialog.grab_set()

        ttk.Label(dialog, text="被顶号后等待进入游戏秒数:", font=('Microsoft YaHei', 9)).pack(padx=20, pady=(15, 5))

        entry_var = tk.StringVar(value=self.settings_dinghao_wait_var.get())
        entry = ttk.Entry(dialog, textvariable=entry_var, width=10)
        entry.pack(padx=20, pady=5)
        entry.focus_set()

        def on_ok():
            """确认输入并关闭对话框。"""
            try:
                val = int(entry_var.get())
                if val >= 0:
                    self.settings_dinghao_wait_var.set(str(val))
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
    
    def _open_log_folder(self):
        """在资源管理器里打开日志目录。"""
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
    
    def setup_ui(self):
        """搭建设置页：ADB、提示音、系统通知、随机暂停。"""
        main_frame = ttk.Frame(self.frame, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="YYS-AUTO 设置", font=('Microsoft YaHei', 12, 'bold')).pack(pady=(0, 10))
        
        # ADB连接和提示音在同一行，各占一半
        groups_container = ttk.Frame(main_frame)
        groups_container.pack(fill=tk.X, pady=(0, 10))
        self._create_adb_section(groups_container)
        wav.create_section(self, groups_container)

        # 系统通知区 + 随机暂停设置区，同一行各占一半
        notify_row = ttk.Frame(main_frame)
        notify_row.pack(fill=tk.X, pady=(0, 10))
        self._create_notify_section(notify_row)
        zoushen.create_section(self, notify_row)
