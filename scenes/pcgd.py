"""磐长故地场景处理。

模板处理见 ``png/pcgd/模板处理.txt``：

- suoding：图片坐标，优先级第一
- panchang / rukou / zhandou：图片坐标
- tiaozhan1 / tiaozhan5：图片坐标，记录挑战次数
- jixu：通用坐标

分支优先级：exit > jujue > suoding > panchang/rukou/zhandou > tiaozhan > jixu。
suoding 与 tiaozhan 同时出现时只点 suoding。

挑战计数复用通用的 :func:`count_challenge`：连续点击 tiaozhan 不重复计数，
连续点击 4 次未识别到其它画面视为异常并停止。jujue 为通用拒绝模板，保留识别处理。
识别到 exit 视为任务完成，直接停止运行。
"""

from __future__ import annotations

from scenes.scene_api import SceneResult
from scenes.scene_common import COUNT_OK, click_center, click_xy, count_challenge, log_results

# 点击图片中心、不影响挑战计数的图片
IMAGE_NAMES = ('panchang', 'rukou', 'zhandou')


def handle_scene(ctx):
    """处理一轮识别结果：先处理高优先级图片，挑战则计入次数。"""
    state = ctx.state
    recognizer = ctx.recognizer
    log = ctx.log
    results = ctx.results
    stop = False

    log_results(results, log)

    # 识别到 exit 视为任务完成，直接停止运行
    if any('exit' in r['name'].lower() for r in results):
        log("识别到exit，任务完成，停止运行")
        recognizer.stop_reason = "image"
        recognizer.stop()
        return SceneResult(stop=True)

    # 预检测：suoding 与 tiaozhan 同时出现时，只点 suoding
    has_suoding = any('suoding' in r['name'].lower() for r in results)

    for r in results:
        name_lower = r['name'].lower()

        # 通用拒绝模板，优先级最高
        if 'jujue' in name_lower:
            click_center(recognizer, r)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
            continue

        # suoding 优先级第一
        if 'suoding' in name_lower:
            click_center(recognizer, r)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
            continue

        if 'tiaozhan' in name_lower and not has_suoding:
            click_center(recognizer, r)
            if count_challenge(ctx) != COUNT_OK:
                stop = True
                break
            continue

        if any(x in name_lower for x in IMAGE_NAMES):
            click_center(recognizer, r)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
            continue

        # jixu 使用通用坐标点击
        if 'jixu' in name_lower:
            click_xy(recognizer)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
            continue

    return SceneResult(stop=stop)
