"""契灵场景处理。

分支优先级：jujue > suoding > 探查/结契挑战 > jiangli 系列 > fangqi/zaici。
有 suoding 时不点挑战。fangqi 与 zaici 互为互斥选项：选了一个就屏蔽另一个。
"""

from __future__ import annotations

from scenes.scene_api import SceneResult
from scenes.scene_common import COUNT_OK, click_center, click_xy, count_challenge, log_results


def handle_scene(ctx):
    """处理一轮识别结果：先处理高优先级图片，挑战则计入次数。"""
    state = ctx.state
    recognizer = ctx.recognizer
    log = ctx.log
    results = ctx.results
    options = ctx.options
    stop = False

    log_results(results, log)

    # 预检测：suoding 和挑战同时出现时，只点 suoding
    has_suoding = any('suoding' in r['name'].lower() for r in results)

    for r in results:
        name_lower = r['name'].lower()

        if 'jujue' in name_lower:
            click_center(recognizer, r)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
            continue

        if 'suoding' in name_lower:
            click_center(recognizer, r)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
            continue

        if ('tancha-tiaozhan' in name_lower or 'jieqi-tiaozhan' in name_lower) and not has_suoding:
            click_center(recognizer, r)
            if count_challenge(ctx) != COUNT_OK:
                stop = True
                break
            continue

        if 'jiangli' in name_lower or 'shengli' in name_lower or 'jiangli4' in name_lower:
            click_xy(recognizer)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
            continue

        # fangqi：再次结契模式下屏蔽
        if 'fangqi' in name_lower and not options.ql_zaici:
            click_center(recognizer, r)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
            continue

        # zaici：放弃结契模式下屏蔽
        if 'zaici' in name_lower and not options.ql_fangqi:
            click_center(recognizer, r)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
            continue

    return SceneResult(stop=stop)
