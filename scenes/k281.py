"""困28队长场景处理。

与困28单人（k28）的区别：没有 30q/绘卷切换，可点击的图片集合不同，并且多了
has_recorded_challenge —— 同一轮里出现多个 boss/putong 时只有第一个计入次数。

和 k28 一样，"连续点击挑战 4 次未识别到奖励"的计数是函数内局部量，每次调用从 0 开始。
"""

from __future__ import annotations

import time

from scenes.scene_api import SceneResult
from scenes.scene_common import (
    BOSS_COUNT_OK,
    BOSS_STOP_OUTCOMES,
    click_center,
    click_xy,
    count_boss_challenge,
    log_results,
    swipe_screen,
)

# 点击后需要主循环等待的图片
CHALLENGE_NAMES = ('putong', 'boss')
# 点击图片中心即可的图片（不计次数）
CLICKABLE_NAMES = ('boss', 'jinru', 'putong', 'yaoqing')
# 点击预设坐标的奖励类图片
REWARD_NAMES = ('jiangli', 'jianglik28', 'shengli')


def handle_scene(ctx):
    """处理一轮识别结果。"""
    state = ctx.state
    recognizer = ctx.recognizer
    log = ctx.log
    results = ctx.results
    stop = False
    need_wait = False

    # 本轮的局部计数，不跨轮
    consecutive_putong_boss = 0
    has_recorded_challenge = False

    has_boss = any('boss' in r['name'].lower() for r in results)
    has_putong = any('putong' in r['name'].lower() for r in results)

    log_results(results, log)

    for r in results:
        name_lower = r['name'].lower()

        if 'jujue' in name_lower:
            click_xy(recognizer, 870, 583)
            state.consecutive_challenge = 0
            continue

        # boss 和 putong 同时出现时只处理 boss
        if has_boss and has_putong and 'putong' in name_lower:
            continue

        if 'ssl' in name_lower:
            click_xy(recognizer, 46, 31)
            state.consecutive_challenge = 0
            continue

        if 'baozang' in name_lower:
            click_center(recognizer, r)
            time.sleep(0.5)
            click_xy(recognizer)
            state.consecutive_challenge = 0
            continue

        if any(x in name_lower for x in CLICKABLE_NAMES):
            click_center(recognizer, r)
            state.consecutive_challenge = 0

            if state.count_challenge and any(x in name_lower for x in CHALLENGE_NAMES):
                # 队长一轮里可能同时识别到 boss 和 putong，只计第一次
                outcome = count_boss_challenge(ctx, consecutive_putong_boss,
                                               has_recorded_challenge, dedupe_round=True)
                consecutive_putong_boss = outcome.consecutive
                has_recorded_challenge = outcome.recorded
                if outcome.outcome in BOSS_STOP_OUTCOMES:
                    stop = True
                    break
                if outcome.outcome == BOSS_COUNT_OK:
                    need_wait = True
            else:
                state.last_clicked_putong_boss = False
                consecutive_putong_boss = 0
            continue

        if any(x in name_lower for x in REWARD_NAMES):
            click_xy(recognizer)
            state.consecutive_challenge = 0
            consecutive_putong_boss = 0
            state.last_clicked_putong_boss = False

    return SceneResult(stop=stop, need_wait=need_wait)


def handle_no_recognition(ctx):
    """连续 5 次没识别到图片时滑一次屏，重新找目标。"""
    swipe_screen(ctx.recognizer, ctx.log, ctx.recognizer.device)
