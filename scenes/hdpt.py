"""活动爬塔场景处理。

识别结果按分支优先级处理：jujue > exit > suoding/tiaozhan > 其它。
suoding 与 tiaozhan 同时出现时只点 suoding（先锁定再挑战）。
"""

from __future__ import annotations

from scenes.scene_api import SceneResult
from scenes.scene_common import COUNT_OK, click_center, click_xy, count_challenge

# 点击图片中心、不影响挑战计数的图片。注意 hdrk 会连带命中 hdrk1~hdrk4，
# 而 tiaozhan 已被上面的分支拦截，列在这里只是为了保留原有的匹配集合。
PASS_THROUGH_NAMES = ['dfwrk', 'hdrk', 'tiaozhan', 'pt', 'rukou']


def handle_scene(ctx):
    """处理一轮识别结果：先处理高优先级图片，挑战则计入次数。"""
    state = ctx.state
    recognizer = ctx.recognizer
    log = ctx.log
    results = ctx.results
    stop = False

    # 预检测：有 tiaozhan 时不点 suoding（先挑战后锁定）
    has_tiaozhan = any('tiaozhan' in r['name'].lower() or 'tiaoszhan' in r['name'].lower()
                       for r in results)

    for r in results:
        log(r['name'].replace('.png', ''))
        name_lower = r['name'].lower()

        if 'jujue' in name_lower:
            click_center(recognizer, r)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
        elif 'exit' in name_lower:
            log("任务完成")
            recognizer.stop_reason = "image"
            stop = True
            break
        elif 'suoding' in name_lower and not has_tiaozhan:
            click_center(recognizer, r)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
        elif 'tiaozhan' in name_lower or 'tiaoszhan' in name_lower:
            click_center(recognizer, r)
            if count_challenge(ctx) != COUNT_OK:
                stop = True
                break
        elif any(x in name_lower for x in PASS_THROUGH_NAMES):
            click_center(recognizer, r)
            state.consecutive_challenge = 0
            continue
        elif 'jiangli' in name_lower or 'shengli' in name_lower:
            click_xy(recognizer)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
        elif 'buji' in name_lower:
            # buji：点击固定坐标 1112, 201
            click_xy(recognizer, 1112, 201)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
        elif 'rkjl' in name_lower:
            # 走到这里只可能是 rkjl —— jiangli/shengli 已在上面被拦截
            click_xy(recognizer)
            state.consecutive_challenge = 0
            continue

    return SceneResult(stop=stop)
