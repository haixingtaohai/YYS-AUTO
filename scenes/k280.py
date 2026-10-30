"""困28队员场景处理。

队员不统计挑战次数，只按图片类型点击：jujue 点固定坐标 (870, 583)，
baozang / jieshou 点图片中心，jiangli 系列点预设坐标。
"""

from __future__ import annotations

from scenes.scene_api import SceneResult
from scenes.scene_common import click_center, click_xy

# 点击预设坐标（recognizer.click_x / click_y）的奖励类图片
REWARD_NAMES = ['jiangli', 'jianglik28', 'shengli']


def handle_scene(ctx):
    """处理一轮识别结果。"""
    state = ctx.state
    recognizer = ctx.recognizer
    log = ctx.log
    results = ctx.results

    for r in results:
        log(r['name'].replace('.png', ''))
        name_lower = r['name'].lower()

        if 'jujue' in name_lower:
            click_xy(recognizer, 870, 583)
            state.consecutive_challenge = 0
        elif 'baozang' in name_lower or 'jieshou' in name_lower:
            click_center(recognizer, r)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False
        elif any(x in name_lower for x in REWARD_NAMES):
            click_xy(recognizer)
            state.consecutive_challenge = 0
            state.last_clicked_tiaozhan = False

    return SceneResult()
