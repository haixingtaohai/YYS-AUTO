"""道馆场景处理。

不统计目标次数，改用独立的 tiaozhan_count_dg 做节流：连续点到 5 次挑战就进入
60 秒冷却（期间可被停止打断）。识别到 dengdaigz/dengdaikz 时整轮跳过并等 5 秒。
"""

from __future__ import annotations

import time

from scenes.scene_api import SceneResult
from scenes.scene_common import click_center, click_xy, log_results

# 连续点击挑战多少次后进入冷却
COOLDOWN_TRIGGER = 5
# 冷却时长（秒）
COOLDOWN_SECONDS = 60
# 识别到等待状态时暂停的时长（秒）
WAIT_SECONDS = 5


def _has_dengdai(results):
    """是否识别到等待中的提示图。"""
    return any('dengdaigz' in r['name'].lower() or 'dengdaikz' in r['name'].lower()
               for r in results)


def _cooldown(ctx):
    """倒数 60 秒，期间若被停止则提前退出。"""
    recognizer = ctx.recognizer
    for remaining in range(COOLDOWN_SECONDS, 0, -1):
        ctx.log(f"冷却倒计时: {remaining}秒")
        time.sleep(1)
        if not getattr(recognizer, 'running', True):
            break
    ctx.log("冷却结束，继续识别")


def handle_scene(ctx):
    """处理一轮识别结果。"""
    state = ctx.state
    recognizer = ctx.recognizer
    log = ctx.log
    results = ctx.results

    if not hasattr(recognizer, 'tiaozhan_count_dg'):
        recognizer.tiaozhan_count_dg = 0
    tiaozhan_count = recognizer.tiaozhan_count_dg

    log_results(results, log)

    if _has_dengdai(results):
        log("识别到等待状态，等待5秒")
        time.sleep(WAIT_SECONDS)
        return SceneResult()

    for r in results:
        name_lower = r['name'].lower()

        if 'jujue' in name_lower:
            click_xy(recognizer, 870, 583)
            state.consecutive_challenge = 0
        elif 'tiaozhan' in name_lower:
            tiaozhan_count += 1
            click_center(recognizer, r)
            state.consecutive_challenge = 0
            if tiaozhan_count >= COOLDOWN_TRIGGER:
                log("连续点击挑战五次，进入冷却倒计时60秒")
                _cooldown(ctx)
                tiaozhan_count = 0
        elif 'zhunbei' in name_lower:
            click_center(recognizer, r)
            state.consecutive_challenge = 0
        elif 'yxnjc' in name_lower:
            log("识别到yxnjc，任务完成，停止运行")
            recognizer.stop_reason = "image"
            # 注意：这条路径不写回 tiaozhan_count_dg（与重构前一致）
            return SceneResult(stop=True)
        elif any(x in name_lower for x in ('shengli', 'jiangli', 'shibai', 'jiesuan')):
            click_xy(recognizer)
            state.consecutive_challenge = 0
            tiaozhan_count = 0

    recognizer.tiaozhan_count_dg = tiaozhan_count
    return SceneResult()
