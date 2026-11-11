"""超鬼王场景处理。

按图片类型点击：zhaohuan、zhunbei、tiaozhan 点击图片坐标，jixu 点击通用坐标。
识别到 zhaohuan 计入运行次数（日志输出「召唤次数: n/目标」），达到目标次数后停止。
"""

from __future__ import annotations

from scenes.scene_api import SceneResult
from scenes.scene_common import COUNT_OK, click_center, click_xy, count_challenge, log_results

# 连续点击召唤/挑战多少次未识别到其它画面就判为异常
ANOMALY_LIMIT = 4


def handle_scene(ctx):
    """处理一轮识别结果：召唤计入运行次数，挑战与继续按坐标点击。"""
    state = ctx.state
    recognizer = ctx.recognizer
    results = ctx.results
    stop = False

    log_results(results, ctx.log)

    for r in results:
        name_lower = r['name'].lower()

        if 'jujue' in name_lower:
            click_xy(recognizer, 870, 583)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
            continue

        if 'cgw' in name_lower:
            click_center(recognizer, r)
            state.consecutive_challenge = 0
            continue

        if 'zhaohuan' in name_lower:
            click_center(recognizer, r)
            if count_challenge(ctx, label="召唤次数", action="召唤",
                               anomaly_limit=ANOMALY_LIMIT) != COUNT_OK:
                stop = True
                break
            continue

        if 'zhunbei' in name_lower:
            click_center(recognizer, r)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
            continue

        if 'tiaozhan' in name_lower:
            click_center(recognizer, r)
            state.last_clicked_tiaozhan = False
            state.consecutive_challenge += 1
            if state.consecutive_challenge >= ANOMALY_LIMIT:
                ctx.log("连续点击挑战四次，异常停止")
                recognizer.stop_reason = "anomaly"
                stop = True
                break
            continue

        if 'jixu' in name_lower:
            click_xy(recognizer)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False

    return SceneResult(stop=stop)
