"""斗技场景处理。

识别到 jinsheng（段位晋升）时：开启"晋升结束程序"就直接停止，否则点右上角继续。
其余结果里 jujue 优先，其次 jieshu/jixu，剩下的都点图片中心；只有 zhandou
（战斗）计入挑战次数，且不做连续点击异常检测。
"""

from __future__ import annotations

from scenes.scene_api import SceneResult
from scenes.scene_common import click_center, click_xy, log_results


def handle_scene(ctx):
    """处理一轮识别结果。"""
    state = ctx.state
    recognizer = ctx.recognizer
    log = ctx.log
    results = ctx.results
    options = ctx.options

    # 斗技场景永远把"上次点击挑战"标记复位（与重构前的返回值一致）
    state.last_clicked_tiaozhan = False

    if any('jinsheng' in r['name'].lower() for r in results):
        if options.dj_jinsheng_stop:
            log("识别到jinsheng，斗技段位晋升结束程序")
            recognizer.stop_reason = "image"
            return SceneResult(stop=True)
        log("识别到jinsheng，点击1202 55")
        click_xy(recognizer, 1202, 55)
        state.consecutive_challenge = 0
        return SceneResult()

    log_results(results, log)

    for r in results:
        name_lower = r['name'].lower()

        if 'jujue' in name_lower:
            click_center(recognizer, r)
            state.consecutive_challenge = 0
            continue

        if 'jieshu' in name_lower or 'jixu' in name_lower:
            click_xy(recognizer)
            state.consecutive_challenge = 0
            continue

        click_center(recognizer, r)

        if state.count_challenge and 'zhandou' in name_lower:
            recognizer.tiaozhan_count += 1
            state.current_count = recognizer.tiaozhan_count
            log(f"  挑战次数: {state.current_count}/{state.target_count}")
            if state.target_count > 0 and state.current_count >= state.target_count:
                log(f"达到目标挑战次数 {state.target_count}，结束脚本")
                recognizer.stop_reason = "count"
                return SceneResult(stop=True)

        state.consecutive_challenge = 0

    return SceneResult()
