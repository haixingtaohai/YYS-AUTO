"""困28单人场景处理。

比其它场景多两层判断：

- 同时识别到 boss 和 putong 时屏蔽 putong（避免一次战斗点两次）
- 连续点击挑战 4 次未识别到奖励判为异常；这个计数是**函数内局部量**，每次调用
  都从 0 开始，不跨轮累积

绘卷模式下识别到 30q 会切换到结界突破场景。
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

# 点击后计入挑战次数、并需要主循环等待的图片
CHALLENGE_NAMES = ('putong', 'boss')
# 点击图片中心即可的图片（不计次数）
CLICKABLE_NAMES = ('boss', 'putong', 'tansuo', 'xuanze')
# 点击预设坐标的奖励类图片
REWARD_NAMES = ('jiangli', 'shengli', 'jianglik28')
# 切到结界突破的场景名
SWITCH_TARGET = "结界突破"


def handle_scene(ctx):
    """处理一轮识别结果。"""
    state = ctx.state
    recognizer = ctx.recognizer
    log = ctx.log
    results = ctx.results
    stop = False
    need_wait = False

    # 每次调用都重置：这是本轮内的连续计数，不跨轮
    consecutive_putong_boss = 0

    has_boss = any('boss' in r['name'].lower() for r in results)
    has_putong = any('putong' in r['name'].lower() for r in results)

    # 绘卷模式：识别到 30q 直接切到结界突破
    if ctx.options.huijuan_mode and any('30q' in r['name'].lower() for r in results):
        log("识别到30q，绘卷模式：切换到结界突破场景")
        return SceneResult(switch_to=SWITCH_TARGET)

    log_results(results, log)

    for r in results:
        name_lower = r['name'].lower()

        if 'jujue' in name_lower:
            click_center(recognizer, r)
            state.consecutive_challenge = 0
            continue

        if 'jjtp' in name_lower:
            click_xy(recognizer, 1205, 135)
            state.consecutive_challenge = 0
            continue

        if 'ssl' in name_lower:
            click_xy(recognizer, 46, 31)
            state.consecutive_challenge = 0
            continue

        # boss 和 putong 同时出现时只处理 boss
        if has_boss and has_putong and 'putong' in name_lower:
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
                # 单人场景不做"一轮只计一次"，每个 boss/putong 都走一遍
                outcome = count_boss_challenge(ctx, consecutive_putong_boss, False)
                consecutive_putong_boss = outcome.consecutive
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
