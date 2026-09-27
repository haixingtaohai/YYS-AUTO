"""场景模块共用的点击、日志与滑动辅助。

重构前这 5 个 helper 在 15 个场景文件里各抄了一份（``_click_random_xy`` 甚至出现
了两种同名不同签名的版本），这里统一成一份实现。

点击抖动幅度统一为 ±10 像素；``random.randint`` 的调用顺序与重构前逐字保持一致，
因为主循环的坐标可复现性依赖该顺序。
"""

from __future__ import annotations

import random
import subprocess
from typing import NamedTuple

# 点击坐标的随机抖动半径（像素）
CLICK_JITTER = 10


def click_center(recognizer, result):
    """点击识别结果的中心点，XY 各随机偏移 ±10 像素。"""
    x, y = result['center']
    click_xy(recognizer, x, y)


def click_xy(recognizer, x=None, y=None):
    """点击坐标并加随机抖动。

    不传坐标时使用 ``recognizer.click_x`` / ``recognizer.click_y``——这是重构前
    两种同名 helper 的行为差异，统一到这里由参数有无区分。
    """
    if x is None or y is None:
        x, y = recognizer.click_x, recognizer.click_y
    random_x = x + random.randint(-CLICK_JITTER, CLICK_JITTER)
    random_y = y + random.randint(-CLICK_JITTER, CLICK_JITTER)
    recognizer.click(random_x, random_y)


def click_center_in_results(recognizer, results, name_filter):
    """在结果列表里找第一个名字含 ``name_filter`` 的目标并点击其中心。

    返回是否命中。结界突破场景专用。
    """
    for r in results:
        if name_filter in r['name'].lower():
            click_center(recognizer, r)
            return True
    return False


def log_results(results, log):
    """把识别到的图片名（去掉 .png 后缀）逐条写进日志。"""
    for r in results:
        log(r['name'].replace('.png', ''))


def swipe_screen(recognizer, log, device):
    """未识别到图片时把屏幕从右往左滑一次，重新寻找目标。

    困28单人和困28队长用。滑动失败不影响主流程。
    """
    log("滑动屏幕")
    try:
        sx = 1100 + random.randint(-8, 8)
        sy = 360 + random.randint(-8, 8)
        ex = 200 + random.randint(-8, 8)
        ey = 360 + random.randint(-8, 8)

        mx = 650 + random.randint(-20, 20)
        my = 360 + random.randint(-10, 10)

        cmd1 = [recognizer.adb_path, "-s", device, "shell", "input", "swipe",
                str(sx), str(sy), str(mx), str(my), str(random.randint(180, 260))]
        cmd2 = [recognizer.adb_path, "-s", device, "shell", "input", "swipe",
                str(mx), str(my), str(ex), str(ey), str(random.randint(220, 320))]

        subprocess.run(cmd1, capture_output=True, timeout=5)
        subprocess.run(cmd2, capture_output=True, timeout=5)
    except Exception:
        pass


# 挑战计数结果
COUNT_OK = "ok"
COUNT_REACHED = "count"      # 达到目标挑战次数
COUNT_ANOMALY = "anomaly"    # 连续点击多次仍未识别到奖励


def count_challenge(ctx, last_clicked_attr="last_clicked_tiaozhan", anomaly_limit=4):
    """通用的「挑战次数统计 + 连续点击异常检测」。

    连续两次点到挑战不计入次数（第二次只提示）。返回 :data:`COUNT_OK`、
    :data:`COUNT_REACHED` 或 :data:`COUNT_ANOMALY`；后两者由调用方负责停止并
    跳出本轮识别结果循环。
    """
    state = ctx.state
    recognizer = ctx.recognizer
    last_clicked = getattr(state, last_clicked_attr)

    if state.count_challenge:
        if not last_clicked:
            recognizer.tiaozhan_count += 1
            state.current_count = recognizer.tiaozhan_count
            ctx.log(f"  挑战次数: {state.current_count}/{state.target_count}")
            if state.target_count > 0 and state.current_count >= state.target_count:
                ctx.log(f"达到目标挑战次数 {state.target_count}，结束脚本")
                recognizer.stop_reason = "count"
                return COUNT_REACHED
        else:
            ctx.log("  连续点击挑战，不计入次数")

    setattr(state, last_clicked_attr, True)
    state.consecutive_challenge += 1
    if state.consecutive_challenge >= anomaly_limit:
        ctx.log(f"挑战失败：连续点击{anomaly_limit}次未识别到奖励")
        recognizer.stop_reason = "anomaly"
        return COUNT_ANOMALY
    return COUNT_OK


# boss/putong 计数结果
BOSS_COUNT_OK = "ok"            # 已计入，调用方应设置 need_wait
BOSS_COUNT_DEDUPED = "deduped"  # 本轮已计过，只更新了点击标记
BOSS_COUNT_REACHED = "count"    # 达到目标挑战次数
BOSS_COUNT_ANOMALY = "anomaly"  # 连续多次未识别到奖励
BOSS_STOP_OUTCOMES = (BOSS_COUNT_REACHED, BOSS_COUNT_ANOMALY)

# 困28 系列连续点击挑战多少次未识别到奖励就判为异常
BOSS_ANOMALY_LIMIT = 4


class BossChallenge(NamedTuple):
    """一次 boss/putong 计数的结果。"""

    outcome: str
    consecutive: int
    recorded: bool


def count_boss_challenge(ctx, consecutive, recorded, dedupe_round=False):
    """困28 系列的 boss/putong 挑战计数。

    与 :func:`count_challenge` 的区别：只有 boss/putong 才计数；``consecutive`` 是
    **一次调用内**的连续计数（不跨轮），所以由调用方持有并回传，不能放进 SceneState。

    ``dedupe_round=True`` 时同一轮识别结果里只计一次——困28队长用，因为一轮可能同时
    识别到 boss 和 putong。
    """
    state = ctx.state
    recognizer = ctx.recognizer
    log = ctx.log

    if dedupe_round and recorded:
        # 本轮已经计过一次，后续结果只更新点击标记
        state.last_clicked_putong_boss = True
        return BossChallenge(BOSS_COUNT_DEDUPED, consecutive, recorded)

    if not state.last_clicked_putong_boss:
        recognizer.tiaozhan_count += 1
        state.current_count = recognizer.tiaozhan_count
        log(f"  挑战次数: {state.current_count}/{state.target_count}")
        if state.target_count > 0 and state.current_count >= state.target_count:
            log(f"达到目标挑战次数 {state.target_count}，结束脚本")
            recognizer.stop_reason = "count"
            return BossChallenge(BOSS_COUNT_REACHED, consecutive, recorded)
    else:
        log("  连续点击挑战，不计入次数")

    state.last_clicked_putong_boss = True
    consecutive += 1
    recorded = True
    if consecutive >= BOSS_ANOMALY_LIMIT:
        log(f"挑战失败：连续点击{BOSS_ANOMALY_LIMIT}次未识别到奖励")
        recognizer.stop_reason = "anomaly"
        return BossChallenge(BOSS_COUNT_ANOMALY, consecutive, recorded)
    return BossChallenge(BOSS_COUNT_OK, consecutive, recorded)
