"""队员（魂土队员）场景处理。

不统计目标次数：识别到 jieshou 直接累加一次挑战。识别到 duiwu 视为已准备，
识别到奖励则回到未准备状态，两个状态变化通过回调通知标签页。
"""

from __future__ import annotations

from scenes.scene_api import SceneResult
from scenes.scene_common import click_center, click_xy


def handle_scene(ctx):
    """处理一轮识别结果，并通过回调同步队员准备状态。"""
    state = ctx.state
    recognizer = ctx.recognizer
    log = ctx.log
    results = ctx.results
    options = ctx.options

    for r in results:
        log(r['name'].replace('.png', ''))
        name_lower = r['name'].lower()

        if 'jujue' in name_lower:
            click_xy(recognizer, 870, 583)
            state.consecutive_challenge = 0
        elif 'duiwu' in name_lower:
            # 识别到 duiwu 视为队员已准备
            if options.on_ready:
                options.on_ready()
        elif 'jiangli' in name_lower or 'shengli' in name_lower:
            click_xy(recognizer)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
            # 识别到奖励后回到未准备状态
            if options.on_unready:
                options.on_unready()
        elif 'baozang' in name_lower:
            click_xy(recognizer)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
        elif 'jieshou' in name_lower:
            click_center(recognizer, r)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
            # 队员不设目标次数，识别到 jieshou 就直接计一次
            if state.count_challenge:
                recognizer.tiaozhan_count += 1
                state.current_count = recognizer.tiaozhan_count
                log(f"  挑战次数: {state.current_count}/无")

    return SceneResult()
