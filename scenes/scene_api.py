"""场景模块的公共数据结构。

重构前每个场景的 ``handle_scene`` 收 8~11 个位置参数、返回 4/5/6 元组，调用方
（``ui/scene_runner.py``）得为每个场景单独写一段拆包代码。这里把三类信息分开：

- :class:`SceneState`：跨轮持久的计数与标志，一次运行内复用
- :class:`SceneOptions`：从标签页读到的开关与回调，每轮重建
- :class:`SceneResult`：本轮结论（是否停止 / 是否等待 / 是否切换场景）

于是场景函数的签名统一成 ``handle_scene(ctx)``，返回值统一成 ``SceneResult``。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional


@dataclass
class SceneState:
    """一次运行内跨轮持久的状态。

    注意 ``last_clicked_tiaozhan`` 与 ``last_clicked_putong_boss`` 是两个独立槽位：
    困28 系列用后者，其余场景用前者，切换场景时各自只重置其中一个。合并成一个
    字段在当前调用序列下恰好等价，但会掩盖这个不变量，因此保持分开。

    ``recognition_attempts`` 只有困28单人和困28队长在用：未识别到图片时累加，
    累计到 5 次触发一次滑动屏幕。
    """

    current_count: int = 0
    target_count: int = 200
    count_challenge: bool = True
    consecutive_challenge: int = 0
    recognition_attempts: int = 0
    last_clicked_tiaozhan: bool = False
    last_clicked_putong_boss: bool = False


@dataclass
class SceneOptions:
    """从当前标签页读到的开关与回调，每轮识别前重建。"""

    huijuan_mode: bool = False
    link_enabled: bool = False
    dj_jinsheng_stop: bool = False
    ql_fangqi: bool = False
    ql_zaici: bool = False
    # 队员场景：识别到 duiwu 视为已准备，识别到奖励回到未准备
    on_ready: Optional[Callable[[], None]] = None
    on_unready: Optional[Callable[[], None]] = None
    # 司机场景：点击挑战前确认所有队员已准备；点击后把队员重置为未准备
    check_teammates_ready: Optional[Callable[[], bool]] = None
    mark_teammates_unready: Optional[Callable[[], None]] = None


@dataclass
class SceneContext:
    """一次 ``handle_scene`` 调用的全部输入。"""

    results: List[dict]
    recognizer: Any
    log: Callable[[str], None]
    state: SceneState = field(default_factory=SceneState)
    options: SceneOptions = field(default_factory=SceneOptions)


@dataclass
class SceneResult:
    """一轮场景处理的结论。

    ``switch_to`` 是目标场景名（如 ``"结界突破"`` / ``"困28单人"``），``None``
    表示不切换。调用方负责记录当前场景时长、切换预设并重建 recognizer 参数。
    """

    stop: bool = False
    need_wait: bool = False
    switch_to: Optional[str] = None
