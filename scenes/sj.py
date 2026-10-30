"""司机（魂土队长）场景处理。

与队员联动：点击挑战前先确认所有队员已准备，点击后把队员重置为未准备。
识别到 yaoqing 时先点 560,360，间隔一秒再点 750,430。
"""

from __future__ import annotations

import time

from scenes.scene_api import SceneResult
from scenes.scene_common import COUNT_OK, click_center, click_xy, count_challenge


def handle_scene(ctx):
    """处理一轮识别结果：挑战前校验队员状态，挑战则计入次数。"""
    state = ctx.state
    recognizer = ctx.recognizer
    log = ctx.log
    results = ctx.results
    options = ctx.options
    stop = False

    for r in results:
        log(r['name'].replace('.png', ''))
        name_lower = r['name'].lower()

        if 'jujue' in name_lower:
            click_xy(recognizer, 870, 583)
            state.consecutive_challenge = 0
        elif 'tiaozhan' in name_lower or 'tiaoszhan' in name_lower:
            # 联动模式：队员没准备好就等下一轮
            if options.link_enabled and options.check_teammates_ready \
                    and not options.check_teammates_ready():
                log("  队员未准备，等待队员")
                continue
            click_center(recognizer, r)
            # 司机点了挑战，队员回到未准备状态
            if options.link_enabled and options.mark_teammates_unready:
                options.mark_teammates_unready()
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
        elif 'yaoqing' in name_lower:
            click_xy(recognizer, 560, 360)
            time.sleep(1)
            click_xy(recognizer, 750, 430)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False

    return SceneResult(stop=stop)
