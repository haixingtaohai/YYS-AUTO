"""大富翁场景处理。

先整轮记日志，再按顺序处理。多数提示图点固定坐标；qiangduo 在四组坐标里随机选
一组；只有 chufa（出发）计入挑战次数，且连续点击 15 次未识别到奖励才判异常
（比其他场景宽松，因为大富翁流程本身较长）。
"""

from __future__ import annotations

import random

from scenes.scene_api import SceneResult
from scenes.scene_common import COUNT_OK, click_center, click_xy, count_challenge

# qiangduo 随机点击的四组坐标
QIANGDUO_COORDS = [(202, 492), (529, 568), (789, 566), (1069, 419)]

# 连续点击 chufa 多少次未识别到奖励就判为异常
CHUFA_ANOMALY_LIMIT = 15


def handle_scene(ctx):
    """处理一轮识别结果：chufa 计入次数并请求主循环多等一会儿。"""
    state = ctx.state
    recognizer = ctx.recognizer
    log = ctx.log
    results = ctx.results
    stop = False
    need_wait = False

    for r in results:
        log(r['name'].replace('.png', ''))

    # 预检测：有 suoding 时屏蔽 chufa
    has_suoding = any('suoding' in r['name'].lower() for r in results)

    for r in results:
        name_lower = r['name'].lower()

        if 'jujue' in name_lower:
            click_center(recognizer, r)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
            continue

        if 'exit' in name_lower:
            log("识别到exit，任务完成")
            recognizer.stop_reason = "count"
            stop = True
            break

        if 'suoding' in name_lower:
            click_center(recognizer, r)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
            continue

        if 'tishi' in name_lower:
            click_xy(recognizer, 1186, 80)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
            continue

        if 'touzhi' in name_lower:
            click_xy(recognizer, 1084, 537)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
            continue

        if 'qiangduo' in name_lower:
            x, y = random.choice(QIANGDUO_COORDS)
            click_xy(recognizer, x, y)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
            continue

        if 'chufa' in name_lower and not has_suoding:
            click_center(recognizer, r)
            need_wait = True
            if count_challenge(ctx, anomaly_limit=CHUFA_ANOMALY_LIMIT) != COUNT_OK:
                stop = True
                break
            continue

        if any(x in name_lower for x in ('dfwrk', 'hdrk', 'tiaozhan')):
            click_center(recognizer, r)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
            continue

        if any(x in name_lower for x in ('rkjl', 'jiangli', 'shengli')):
            click_xy(recognizer)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
            continue

    return SceneResult(stop=stop, need_wait=need_wait)
