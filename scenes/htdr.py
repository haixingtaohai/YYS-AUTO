"""魂土单人场景处理。

分支优先级：jujue > suoding > tansuoye > bqds > tansuo 系列 > tiaozhan >
jiangli/shengli > baozang。suoding 与 tiaozhan 同时出现时只点 suoding。
"""

from __future__ import annotations

from scenes.scene_api import SceneResult
from scenes.scene_common import COUNT_OK, click_center, click_xy, count_challenge


def handle_scene(ctx):
    """处理一轮识别结果：先处理高优先级图片，挑战则计入次数。"""
    state = ctx.state
    recognizer = ctx.recognizer
    log = ctx.log
    results = ctx.results
    stop = False

    # 预检测：有 suoding 时不点 tiaozhan
    has_suoding = any('suoding' in r['name'].lower() for r in results)

    for r in results:
        log(r['name'].replace('.png', ''))
        name_lower = r['name'].lower()

        if 'jujue' in name_lower:
            click_xy(recognizer, 870, 583)
            state.consecutive_challenge = 0
        elif 'suoding' in name_lower:
            click_center(recognizer, r)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
        elif 'tansuoye' in name_lower:
            click_center(recognizer, r)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
        elif 'bqds' in name_lower:
            click_center(recognizer, r)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
        elif 'tansuo' in name_lower:
            click_center(recognizer, r)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
        elif ('tiaozhan' in name_lower or 'tiaoszhan' in name_lower) and not has_suoding:
            click_center(recognizer, r)
            if count_challenge(ctx) != COUNT_OK:
                stop = True
                break
        elif 'jiangli' in name_lower or 'shengli' in name_lower:
            click_xy(recognizer)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
        elif 'baozang' in name_lower:
            click_xy(recognizer)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False

    return SceneResult(stop=stop)
