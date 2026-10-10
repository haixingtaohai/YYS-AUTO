"""场景注册表：预设名 -> 场景模块。

重构前这一步是 main.py 里一条约 130 行的 if/elif 派发链，每个场景单独写一段
拆包/回填代码。现在主循环只需要 ``SCENE_MODULES[preset].handle_scene(ctx)``。

新增场景的步骤：写一个 scenes/xxx.py，实现 ``handle_scene(ctx) -> SceneResult``，
在 presets.py 里加一条预设，再在这里登记。
"""

from __future__ import annotations

from scenes import (
    dg,
    dj,
    dy,
    htdr,
    jjtp,
    k28,
    k280,
    k281,
    pcgd,
    ql,
    sj,
    yjsl,
    yl,
    yyh,
)

# 预设名 -> 场景模块。键必须与 presets.PRESETS 的键一致。
SCENE_MODULES = {
    "业原火": yyh,
    "魂土单人": htdr,
    "司机": sj,
    "队员": dy,
    "斗技": dj,
    "道馆": dg,
    "困28单人": k28,
    "困28队长": k281,
    "困28队员": k280,
    "英杰试炼": yjsl,
    "御灵": yl,
    "契灵": ql,
    "结界突破": jjtp,
    "磐长故地": pcgd,
}

# 未识别到图片时需要调用 handle_no_recognition 的场景。
# 困28单人和困28队长累计 5 次未识别才滑一次屏（计数在 SceneState.recognition_attempts），
# 结界突破每轮都调用以重置内部的 jingong 连续计数。
SLIDE_ON_NO_RECOGNITION = frozenset({"困28单人", "困28队长"})
ALWAYS_NOTIFY_NO_RECOGNITION = frozenset({"结界突破"})
NO_RECOGNITION_PRESETS = SLIDE_ON_NO_RECOGNITION | ALWAYS_NOTIFY_NO_RECOGNITION

# 困28 系列累计多少次未识别就滑一次屏
NO_RECOGNITION_THRESHOLD = 5


def get_module(preset):
    """取预设对应的场景模块；未登记时返回 ``None``。"""
    return SCENE_MODULES.get(preset)
