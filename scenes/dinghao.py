"""被顶号（账号在别处登录）的处理流程。

检测到顶号弹窗后：关闭游戏 → 重新启动 → 倒数等待进入游戏 → 点一次屏幕进游戏。
"""

from __future__ import annotations

import random
import subprocess
import time

# 游戏包名
GAME_PACKAGE = "com.netease.onmyoji.wyzymnqsd_cps"


def handle_dinghao(recognizer, log, wait_seconds=30, device=None):
    """处理顶号流程：关闭游戏 → 启动游戏 → 等待 → 点击坐标。"""
    log("检测到顶号，开始处理...")

    adb_path = getattr(recognizer, 'adb_path', 'adb')

    def build_adb_cmd(cmd_list):
        """拼出带 -s 设备参数的 adb 命令。"""
        cmd = [adb_path]
        if device:
            cmd.extend(["-s", device])
        cmd.extend(cmd_list)
        return cmd

    # 1. 关闭游戏
    log("  关闭游戏...")
    try:
        cmd = build_adb_cmd(["shell", "am", "force-stop", GAME_PACKAGE])
        subprocess.run(cmd, capture_output=True, timeout=5)
    except Exception as e:
        log(f"  关闭游戏失败: {e}")

    time.sleep(1)

    # 2. 启动游戏
    log("  启动游戏...")
    try:
        cmd = build_adb_cmd(["shell", "monkey", "-p", GAME_PACKAGE,
                             "-c", "android.intent.category.LAUNCHER", "1"])
        subprocess.run(cmd, capture_output=True, timeout=10)
    except Exception as e:
        log(f"  启动游戏失败: {e}")

    # 3. 等待进入游戏（倒计时）
    for remaining in range(wait_seconds, 0, -1):
        log(f"  等待进入游戏... {remaining}s")
        time.sleep(1)

    # 4. 点击坐标进入游戏
    log("  点击进入游戏...")
    random_x = 635 + random.randint(-10, 10)
    random_y = 591 + random.randint(-10, 10)
    recognizer.click(random_x, random_y)

    log("顶号处理完成")
