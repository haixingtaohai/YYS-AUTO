"""英杰试炼场景处理。

分支优先级：jujue > suoding > 其他固定图片 > tiaozhan > jiangli/shengli。
有 suoding 时不点 tiaozhan。
"""

from __future__ import annotations

from scenes.scene_api import SceneResult
from scenes.scene_common import COUNT_OK, click_center, click_xy, count_challenge, log_results

# 识别到即点击图片中心、不影响挑战计数的图片
OTHER_NAMES = [
    'gbyw', 'jytx', 'zhunbei', 'tansuoye', 'ccsl',
    'cixinleyuan-tansuo', 'huanxin-tansuo', 'moren-tansuo',
    '100-tansuo', 'zhimenglianting-tansuo',
]


def handle_scene(ctx):
    """处理一轮识别结果：先处理高优先级图片，挑战则计入次数。"""
    state = ctx.state
    recognizer = ctx.recognizer
    log = ctx.log
    results = ctx.results
    stop = False

    has_suoding = any('suoding' in r['name'].lower() for r in results)

    log_results(results, log)

    for r in results:
        name_lower = r['name'].lower()

        if 'jujue' in name_lower:
            click_xy(recognizer, 870, 583)
            state.consecutive_challenge = 0
            continue

        if 'suoding' in name_lower:
            click_center(recognizer, r)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
            continue

        if any(x in name_lower for x in OTHER_NAMES):
            click_center(recognizer, r)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
            continue

        if ('tiaozhan' in name_lower or 'tiaoszhan' in name_lower) and not has_suoding:
            click_center(recognizer, r)
            if count_challenge(ctx) != COUNT_OK:
                stop = True
                break
            continue

        if 'jiangli' in name_lower or 'shengli' in name_lower:
            click_xy(recognizer)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
            continue

    return SceneResult(stop=stop)
