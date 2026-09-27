"""DeviceTab 的运行循环与场景调用。

做成 mixin 而不是独立类，是为了不改动 DeviceTab 里大量的 ``self.*`` 引用，
同时把主循环从 UI 代码里分离出来。
"""

from __future__ import annotations

import os
import threading
import time
import tkinter as tk

import wav
from adb import get_gui_logger
from scenes import dinghao, guanbijiacheng, zoushen
from scenes.registry import (
    ALWAYS_NOTIFY_NO_RECOGNITION,
    NO_RECOGNITION_THRESHOLD,
    SLIDE_ON_NO_RECOGNITION,
    get_module,
)
from scenes.scene_api import SceneContext, SceneOptions, SceneState

gui_logger = get_gui_logger()

# 达到目标次数后需要关闭御魂加成的场景
CLOSE_JIACHENG_PRESETS = ("司机", "队员", "魂土单人")
# 点击 boss/putong 后额外等待的时长（秒）
BOSS_WAIT_SECONDS = 3
# 大富翁点击 chufa 后额外等待的时长（秒）
BIG_RICHMAN_WAIT_SECONDS = 5
# 普通一轮识别之间的间隔（秒）
ROUND_WAIT_SECONDS = 2
# 未识别到图片时的轮询间隔（秒）
IDLE_POLL_SECONDS = 1


class SceneRunnerMixin:
    """标签页的运行循环、场景调用与队员司机联动回调。"""

    # ---- 队员司机联动回调 ----

    def _mark_ready(self):
        """队员场景：识别到 duiwu，标记本标签已准备。"""
        self.is_ready = True
        self.log("  队员已准备")

    def _mark_unready(self):
        """队员场景：识别到奖励，标记本标签回到未准备。"""
        self.is_ready = False
        self.log("  队员未准备")

    def _check_teammates_ready(self):
        """司机场景：至少有一个队员标签且全部已准备才算就绪。"""
        if not getattr(self.parent, 'link_enabled', False):
            return True
        ready_count = 0
        total_teammates = 0
        for tab in self.parent.tabs:
            if tab.current_preset == "队员":
                total_teammates += 1
                if tab.is_ready:
                    ready_count += 1
        return total_teammates > 0 and ready_count == total_teammates

    def _mark_all_teammates_unready(self):
        """司机场景：点过挑战后把所有队员标签重置为未准备。"""
        if not getattr(self.parent, 'link_enabled', False):
            return
        for tab in self.parent.tabs:
            if tab.current_preset == "队员":
                tab.is_ready = False
                tab.log("  队员已重置为未准备")

    # ---- 场景调用 ----

    def _build_scene_options(self):
        """从标签页与父窗口的当前设置构造场景选项。"""
        parent = self.parent
        return SceneOptions(
            huijuan_mode=getattr(parent, 'huijuan_mode', False),
            link_enabled=getattr(parent, 'link_enabled', False),
            dj_jinsheng_stop=getattr(parent, 'dj_jinsheng_stop', False),
            ql_fangqi=getattr(parent, 'ql_fangqi', False),
            ql_zaici=getattr(parent, 'ql_zaici', False),
            on_ready=self._mark_ready,
            on_unready=self._mark_unready,
            check_teammates_ready=self._check_teammates_ready,
            mark_teammates_unready=self._mark_all_teammates_unready,
        )

    def _make_scene_context(self, results):
        """组装一次场景调用所需的上下文。"""
        return SceneContext(
            results=results,
            recognizer=self.recognizer,
            log=self.log,
            state=self.scene_state,
            options=self._build_scene_options(),
        )

    def _dispatch_scene(self, results):
        """按当前场景处理一轮识别结果。

        返回 ``(stop_flag, need_wait, switched)``；``switched`` 为 True 表示本轮
        发生了场景切换，主循环应直接进入下一轮、跳过等待。
        """
        module = get_module(self.current_preset)
        if module is None:
            return False, False, False

        result = module.handle_scene(self._make_scene_context(results))
        self.current_count = self.scene_state.current_count

        if result.switch_to:
            self._apply_scene_switch(result.switch_to)
            return result.stop, result.need_wait, True
        return result.stop, result.need_wait, False

    def _apply_scene_switch(self, target):
        """原地切换到另一个场景，并重建 recognizer 的识别参数。

        ``on_preset_change()`` 必须在 ``current_preset`` 改完之后调用——它会用新的
        场景名写回 preset_thresholds，顺序反过来会改变持久化的阈值。
        """
        if self.scene_start_time is not None:
            elapsed = int(time.time() - self.scene_start_time)
            self.parent.record_usage(self.current_preset, elapsed)
            self.scene_start_time = time.time()

        self.log(f"切换到{target}场景")
        self.current_preset_var.set(target)
        self.current_preset = target
        self.on_preset_change()

        preset = self._preset_config(target)
        self.recognizer.png_folder = os.path.join(self.png_base_folder, preset.get("folder", ""))
        self.recognizer.click_x = preset.get("click_x", 0)
        self.recognizer.click_y = preset.get("click_y", 0)
        self.recognizer.threshold = self._read_threshold()

        self.scene_state.count_challenge = preset.get("count_challenge", True)
        self.scene_state.target_count = self._read_target_count()

        # 只重置即将进入的场景所关心的标记，保持与切换前一致
        if target in SLIDE_ON_NO_RECOGNITION:
            self.scene_state.recognition_attempts = 0
            self.scene_state.last_clicked_putong_boss = False
        else:
            self.scene_state.last_clicked_tiaozhan = False

    def _handle_no_recognition(self):
        """未识别到图片时的场景钩子。

        困28单人和困28队长累计 5 次未识别才滑一次屏；结界突破每轮都调用，用于重置
        内部的 jingong 连续计数。其余场景没有这个钩子。
        """
        preset = self.current_preset
        if preset in SLIDE_ON_NO_RECOGNITION:
            self.scene_state.last_clicked_putong_boss = False
            self.scene_state.recognition_attempts += 1
            if self.scene_state.recognition_attempts < NO_RECOGNITION_THRESHOLD:
                return
            self.scene_state.recognition_attempts = 0
        elif preset not in ALWAYS_NOTIFY_NO_RECOGNITION:
            return

        module = get_module(preset)
        if module is not None and hasattr(module, 'handle_no_recognition'):
            module.handle_no_recognition(self._make_scene_context([]))

    # ---- 运行循环 ----

    def _init_scene_state(self):
        """重置一次运行的场景状态。

        每次开始都新建：挑战次数、连续点击标记、未识别计数必须从零开始，
        否则第二次运行会继承上一轮的值。
        """
        preset = self._preset_config()
        self.scene_state = SceneState()
        self.scene_state.count_challenge = preset.get("count_challenge", True)
        self.scene_state.target_count = self._read_target_count()
        self.current_count = 0

    # ---- 运行循环的各个环节 ----

    def _handle_dinghao(self, results):
        """顶号弹窗优先级最高，处理完直接跳过本轮。返回是否已处理。"""
        if not any('dinghao' in r['name'].lower() for r in results):
            return False
        dinghao.handle_dinghao(
            self.recognizer, self.log, self.parent.dinghao_wait,
            getattr(self.recognizer, 'device', None))
        return True

    def _tabs_for_close_jiacheng(self):
        """需要执行关闭加成的标签：司机连带所有队员，其余只有自己。"""
        if self.current_preset != "司机":
            return [self]
        tabs = [self]
        for tab in self.parent.tabs:
            if tab is not self and getattr(tab, 'current_preset', None) == "队员":
                tabs.append(tab)
        return tabs

    def _close_jiacheng_for_tabs(self, tabs):
        """并行对每个标签执行关闭加成，全部完成后返回。"""
        jiacheng_folder = os.path.join(self.png_base_folder, "jiacheng")

        def process_tab(tab):
            """对单个标签执行关闭加成，完成后停止它。"""
            name = getattr(tab, 'tab_name', '?')
            try:
                if not os.path.exists(jiacheng_folder):
                    tab.log("警告：未找到jiacheng文件夹")
                    return
                device = None
                if hasattr(tab, 'device_combo'):
                    device = tab.device_combo.get()
                if getattr(tab, 'recognizer', None):
                    device = tab.recognizer.device
                guanbijiacheng.handle_close_jiacheng(
                    tab.recognizer, tab.log, jiacheng_folder, device)
                # 关闭加成完成后停止该标签的运行
                tab.stop_loop()
            except Exception as e:
                # 这里原来是一句 `except: pass`——关闭加成失败会静默消失，
                # 表现为标签页一直不停止，很难查。改成写进 GUI 日志。
                gui_logger.error(f"[{name}] 关闭加成失败: {e}")

        threads = []
        for tab in tabs:
            thread = threading.Thread(target=process_tab, args=(tab,))
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join()

    def _handle_stop(self):
        """场景判定停止后的收尾：提示音、系统通知、可选的关闭加成。"""
        # 非手动停止时播放提示音和发送系统通知
        if not self.manual_stop:
            wav.play(self)
            if getattr(self.recognizer, 'stop_reason', ''):
                self.send_notification(self.recognizer.stop_reason)

        self.running = False

        if getattr(self.parent, 'close_jiacheng_enabled', False) \
                and self.current_preset in CLOSE_JIACHENG_PRESETS:
            self.log(f"挑战次数达成，等待{self.parent.close_jiacheng_wait}秒...")
            time.sleep(self.parent.close_jiacheng_wait)
            self._close_jiacheng_for_tabs(self._tabs_for_close_jiacheng())

    def _sleep_after_round(self, need_wait):
        """本轮点击后等待多久。

        困28 系列点完 boss/putong 要多等一会儿；结界突破可能通过 skip_sleep
        指定本次的间隔（用完即清）。
        """
        if need_wait:
            time.sleep(BIG_RICHMAN_WAIT_SECONDS if self.current_preset == "大富翁"
                       else BOSS_WAIT_SECONDS)
        elif getattr(self.recognizer, 'skip_sleep', False):
            skip = self.recognizer.skip_sleep
            self.recognizer.skip_sleep = False
            time.sleep(skip if isinstance(skip, (int, float)) else 1)
        else:
            time.sleep(ROUND_WAIT_SECONDS)

    def _finish_run(self):
        """循环结束后的统一收尾：记录时长、恢复按钮、解锁控件。"""
        if self.scene_start_time is not None:
            elapsed = int(time.time() - self.scene_start_time)
            if hasattr(self.parent, 'record_usage'):
                self.parent.record_usage(self.current_preset, elapsed)
            self.scene_start_time = None
        gui_logger.info(
            f"[{self.tab_name}] 运行循环结束 | 场景: {self.current_preset} "
            f"| 手动停止: {self.manual_stop}")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.unlock_controls()

    def run_loop_thread(self):
        """标签页的运行循环，跑在独立线程里。"""
        self._init_scene_state()

        gui_logger.info(
            f"[{self.tab_name}] 开始运行循环 | 场景: {self.current_preset} "
            f"| 目标次数: {self.scene_state.target_count}")

        # 初始化随机暂停状态调度
        self.zoushen_next_trigger_time = None
        zoushen.schedule_next(self)

        while self.running:
            # 随机暂停状态：模拟玩家离开，暂停当前标签页的识别与点击
            if zoushen.handle(self):
                break  # 暂停期间被停止/重启ADB，走循环末尾既有的解锁收尾

            results = self.recognizer.run_once()

            if not results:
                # 未识别到就每秒识别一次，重置连续点击标记后交给场景钩子
                self.scene_state.last_clicked_tiaozhan = False
                self._handle_no_recognition()
                time.sleep(IDLE_POLL_SECONDS)
                continue

            if self._handle_dinghao(results):
                continue

            stop_flag, need_wait, switched = self._dispatch_scene(results)
            if switched:
                # 切换场景后直接进入下一轮，不再等待
                continue

            if stop_flag:
                self._handle_stop()
                break

            self._sleep_after_round(need_wait)

        self._finish_run()
    
    def stop_loop(self):
        """手动停止本标签的运行。"""
        gui_logger.info(f"[{self.tab_name}] 点击按钮: 停止")
        self.manual_stop = True  # 标记为手动停止
        self.running = False
        
        # 记录使用时长
        if self.scene_start_time is not None:
            elapsed = int(time.time() - self.scene_start_time)
            if hasattr(self.parent, 'record_usage'):
                self.parent.record_usage(self.current_preset, elapsed)
            self.scene_start_time = None
        if self.recognizer:
            self.recognizer.running = False
        
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        # 解锁所有控件
        self.unlock_controls()
        
        # 挑战次数以 recognizer 上的计数为准（场景只写它，不写 scene_state）
        if self._preset_config().get("count_challenge", True) and self.recognizer:
            self.log(f"挑战次数: {self.recognizer.tiaozhan_count}")
        self.log("已停止")
        
        # 保存当前标签配置
        self.save_tab_config()
