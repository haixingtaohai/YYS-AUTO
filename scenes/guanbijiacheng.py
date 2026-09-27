"""关闭御魂加成的独立流程。

与普通场景不同：它先重启游戏，再把识别目录临时切到 png/jiacheng，轮询等待
yxnjc（游戏内加成界面）出现并点掉，最后恢复原识别目录。

由主循环在"达到目标次数 + 开启关闭加成"时对相关标签页各起一个线程调用。
"""

from __future__ import annotations

import subprocess
import time

from scenes.scene_common import click_center, click_xy

# 游戏包名
GAME_PACKAGE = "com.netease.onmyoji.wyzymnqsd_cps"
# 轮询上限（约 2 分钟）
MAX_ATTEMPTS = 60
# 每轮轮询之间的间隔（秒）
POLL_INTERVAL = 2


def handle_close_jiacheng(recognizer, log, jiacheng_folder, device=None):
    """执行关闭加成流程，返回是否成功识别并点掉 yxnjc。"""
    adb_path = getattr(recognizer, 'adb_path', 'adb')

    def build_adb_cmd(cmd_list):
        """拼出带 -s 设备参数的 adb 命令。"""
        cmd = [adb_path]
        if device:
            cmd.extend(["-s", device])
        cmd.extend(cmd_list)
        return cmd

    # 1. 关闭游戏
    try:
        cmd = build_adb_cmd(["shell", "am", "force-stop", GAME_PACKAGE])
        subprocess.run(cmd, capture_output=True, timeout=5)
    except Exception:
        pass

    time.sleep(1)

    # 2. 打开游戏
    try:
        cmd = build_adb_cmd(["shell", "monkey", "-p", GAME_PACKAGE,
                             "-c", "android.intent.category.LAUNCHER", "1"])
        subprocess.run(cmd, capture_output=True, timeout=10)
    except Exception:
        pass

    # 等待游戏加载
    time.sleep(10)

    # 3. 临时把识别目录切到 jiacheng
    original_folder = recognizer.folder
    recognizer.folder = jiacheng_folder

    yxnjc_completed = False
    attempts = 0

    while not yxnjc_completed and attempts < MAX_ATTEMPTS:
        attempts += 1
        results = recognizer.run_once()

        if results:
            for r in results:
                log(r['name'].replace('.png', ''))
                name_lower = r['name'].lower()

                if 'guanbi' in name_lower:
                    click_center(recognizer, r)
                    time.sleep(2)
                elif 'jinru' in name_lower:
                    click_center(recognizer, r)
                    time.sleep(2)
                elif 'yxnjc' in name_lower:
                    click_center(recognizer, r)
                    time.sleep(1)
                    # 等待一秒后点 822,222
                    click_xy(recognizer, 822, 222)
                    time.sleep(2)
                    # 再等待两秒后点 777,666
                    click_xy(recognizer, 777, 666)
                    yxnjc_completed = True
                    break

        time.sleep(POLL_INTERVAL)

    # 4. 恢复原始识别目录
    recognizer.folder = original_folder

    return yxnjc_completed
