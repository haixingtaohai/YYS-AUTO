"""结界突破场景处理。

比其它场景复杂，因为存在两套模式：

- **普通模式**：按 jujue / tansuo / suoding / jingong / jiangli / 数字图 的优先级点击。
  数字图（0~5）表示剩余次数，此时把 skip_sleep 设成 0.55 秒加快节奏。
  连续 4 轮只识别到 jingong 视为卡死，异常停止。
- **card57 模式**：识别到 pg0 后进入，按 0~9 步的固定阶梯点击，中途吞掉任何异常并
  退出该模式。这一步依赖挂在 recognizer 上的 jjtp_card57_* 状态跨轮推进。

绘卷模式下识别到 0q/exit 会切换到困28单人。
"""

from __future__ import annotations

import time
from typing import NamedTuple

from scenes.scene_api import SceneResult
from scenes.scene_common import click_center, click_center_in_results, click_xy, log_results

# 切到困28单人的场景名
SWITCH_TARGET = "困28单人"
# 识别到数字图时的识别间隔（秒）
NUMBER_SLEEP = 0.55
# 连续多少轮只识别到 jingong 就判为异常
JINGONG_ANOMALY_LIMIT = 4

# tansuo 系列图片：点击图片中心
TANSUO_NAMES = ('cixinleyuan-tansuo', 'huanxin-tansuo', 'moren-tansuo',
                '100-tansuo', 'zhimenglianting-tansuo')

# card57 模式的四组点击坐标（每两步一组）
ROUND_CONFIGS = [
    {'click1': (300, 200), 'click2': (380, 390)},
    {'click1': (650, 200), 'click2': (714, 390)},
    {'click1': (1000, 200), 'click2': (1050, 390)},
    {'click1': (300, 350), 'click2': (389, 523)},
]


class Flags(NamedTuple):
    """一轮识别结果的分类汇总。"""

    has_suoding: bool
    has_jiangli: bool
    has_numbers: bool
    has_tansuo: bool
    has_pg0: bool
    has_jingong: bool
    has_queren: bool
    has_0q: bool
    has_exit: bool
    has_tuichu: bool
    has_shibai: bool


def detect(results):
    """把识别结果归类成若干布尔标志。"""
    def has(*keywords):
        """结果里是否出现任一关键字。"""
        return any(k in r['name'].lower() for k in keywords for r in results)

    return Flags(
        has_suoding=has('suoding'),
        has_jiangli=has('jiangli', 'shengli'),
        has_numbers=any(str(i) in r['name'] for i in range(6) for r in results),
        has_tansuo=has('tansuo'),
        has_pg0=has('pg0'),
        has_jingong=has('jingong'),
        has_queren=has('queren'),
        has_0q=has('0q'),
        has_exit=has('exit'),
        has_tuichu=has('tuichu', 'tuichu2'),
        has_shibai=has('shibai'),
    )


def _init_card57_state(recognizer):
    """确保 recognizer 上挂着 card57 的跨轮状态。"""
    if not hasattr(recognizer, 'jjtp_card57_mode'):
        recognizer.jjtp_card57_mode = False
        recognizer.jjtp_card57_step = 0
        recognizer.jjtp_card57_round = 0


def _reset_card57_state(recognizer):
    """退出 card57 模式并清空其步进状态。"""
    recognizer.jjtp_card57_mode = False
    recognizer.jjtp_card57_step = 0
    recognizer.jjtp_card57_round = 0


def _handle_switch(ctx, flags):
    """处理 0q/exit：绘卷模式下切场景，否则任务完成。

    返回 SceneResult；``None`` 表示不需要提前返回。
    """
    if not flags.has_0q and not flags.has_exit:
        return None
    recognizer = ctx.recognizer
    if ctx.options.huijuan_mode:
        ctx.log("切换困28")
        return SceneResult(switch_to=SWITCH_TARGET)
    recognizer.stop_reason = "image"
    recognizer.stop()
    return SceneResult(stop=True)


def _enter_card57_mode(ctx, flags):
    """识别到 pg0 时进入 card57 模式。"""
    recognizer = ctx.recognizer
    if flags.has_pg0 and not recognizer.jjtp_card57_mode:
        recognizer.jjtp_card57_mode = True
        recognizer.jjtp_card57_step = 0
        recognizer.jjtp_card57_round = 0
        recognizer.skip_sleep = True


def _step_pick_round(recognizer, log, index):
    """card57 的第 1/3/5/7 步：点一组固定坐标。"""
    config = ROUND_CONFIGS[index]
    log(f"{config['click1']}")
    recognizer.click(config['click1'][0], config['click1'][1])
    time.sleep(0.5)
    log(f"{config['click2']}")
    recognizer.click(config['click2'][0], config['click2'][1])


def _step_exit_battle(recognizer, log, results, flags):
    """card57 的第 2/4/6/8 步：识别到 tuichu 时退出战斗。"""
    if not flags.has_tuichu:
        return False
    click_center_in_results(recognizer, results, 'tuichu')
    click_center_in_results(recognizer, results, 'tuichu2')
    time.sleep(0.5)
    log("(749, 422)")
    recognizer.click(749, 422)
    time.sleep(1.5)
    click_xy(recognizer)
    return True


def _step_0(recognizer, log):
    """进入 card57 界面。"""
    for _ in range(2):
        log("(266, 605)")
        recognizer.click(266, 605)
        time.sleep(0.8)
    log("(831, 597)")
    recognizer.click(831, 597)


def _step_9(recognizer, log):
    """card57 收尾，退出该模式。"""
    log("(831, 597)")
    recognizer.click(831, 597)
    time.sleep(0.5)
    log("(650, 350)")
    recognizer.click(650, 350)
    time.sleep(0.5)
    log("(720, 525)")
    recognizer.click(720, 525)


def _handle_card57_mode(ctx, results, flags):
    """推进 card57 阶梯。返回是否已处理（处理了就不再走普通模式）。"""
    recognizer = ctx.recognizer
    log = ctx.log

    step = recognizer.jjtp_card57_step
    if step not in range(10):
        _reset_card57_state(recognizer)
        return False

    try:
        if step == 0:
            _step_0(recognizer, log)
        elif step in (1, 3, 5, 7):
            _step_pick_round(recognizer, log, (step - 1) // 2)
        elif step in (2, 4, 6, 8):
            if not _step_exit_battle(recognizer, log, results, flags):
                return False
        else:
            _step_9(recognizer, log)
            _reset_card57_state(recognizer)
            return True
    except Exception:
        # card57 阶梯里任何异常都视为该模式失效，退回普通模式
        _reset_card57_state(recognizer)
        return False

    recognizer.jjtp_card57_step = step + 1
    return True


def _handle_normal_mode(ctx, results, flags):
    """普通模式的点击优先级。返回 (consecutive_challenge, last_clicked, 是否已处理)。"""
    state = ctx.state
    recognizer = ctx.recognizer

    # jujue 统一点固定坐标，不按识别框中心
    if any('jujue' in r['name'].lower() for r in results):
        click_xy(recognizer, 870, 583)
        return 0, False, False

    for name in TANSUO_NAMES:
        if click_center_in_results(recognizer, results, name):
            return 0, False, True

    if flags.has_tansuo:
        recognizer.click(30, 37)
        return 0, False, True

    if flags.has_suoding:
        if click_center_in_results(recognizer, results, 'suoding'):
            return 0, False, True

    if flags.has_numbers and flags.has_jingong:
        if click_center_in_results(recognizer, results, 'jingong'):
            return 0, False, True

    if flags.has_jiangli:
        click_xy(recognizer)
        return 0, False, True

    if flags.has_numbers:
        # 点剩余次数最大的那张数字图
        numbers = []
        for r in results:
            for i in range(6):
                if str(i) in r['name']:
                    numbers.append((i, r))
        if numbers:
            numbers.sort(key=lambda item: item[0], reverse=True)
            click_center(recognizer, numbers[0][1])
            return 0, False, True

    for r in results:
        name_lower = r['name'].lower()

        if 'shibai' in name_lower:
            click_xy(recognizer)
            return 0, False, False
        if 'queren' in name_lower:
            if click_center_in_results(recognizer, results, 'queren'):
                return 0, False, False
        elif 'jingong' in name_lower or 'jinru' in name_lower:
            click_center_in_results(recognizer, results, 'jingong')
            click_center_in_results(recognizer, results, 'jinru')
            return 0, False, False

    return state.consecutive_challenge, state.last_clicked_tiaozhan, False


def handle_scene(ctx):
    """处理一轮识别结果，必要时切换场景。"""
    state = ctx.state
    recognizer = ctx.recognizer
    log = ctx.log
    results = ctx.results

    _init_card57_state(recognizer)

    if not hasattr(recognizer, 'jjtp_consecutive_jingong'):
        recognizer.jjtp_consecutive_jingong = 0

    # 非 card57 模式下忽略 tuichu 系列图片
    if not recognizer.jjtp_card57_mode:
        results = [r for r in results
                   if 'tuichu' not in r['name'].lower() and 'tuichu2' not in r['name'].lower()]

    log_results(results, log)

    flags = detect(results)

    if flags.has_numbers:
        recognizer.skip_sleep = NUMBER_SLEEP

    result = _handle_switch(ctx, flags)
    if result is not None:
        return result

    _enter_card57_mode(ctx, flags)

    if recognizer.jjtp_card57_mode:
        if _handle_card57_mode(ctx, results, flags):
            return SceneResult()

    if flags.has_jingong:
        recognizer.jjtp_consecutive_jingong += 1
    else:
        recognizer.jjtp_consecutive_jingong = 0

    if recognizer.jjtp_consecutive_jingong >= JINGONG_ANOMALY_LIMIT:
        log("连续点击jingong四次，异常停止")
        recognizer.stop_reason = "anomaly"
        recognizer.stop()
        return SceneResult(stop=True)

    consecutive, last_clicked, _handled = _handle_normal_mode(ctx, results, flags)
    state.consecutive_challenge = consecutive
    state.last_clicked_tiaozhan = last_clicked
    return SceneResult()


def handle_no_recognition(ctx):
    """未识别到图片时重置 jingong 连续计数。"""
    recognizer = ctx.recognizer
    _init_card57_state(recognizer)
    if not hasattr(recognizer, 'jjtp_consecutive_jingong'):
        recognizer.jjtp_consecutive_jingong = 0
    recognizer.jjtp_consecutive_jingong = 0
