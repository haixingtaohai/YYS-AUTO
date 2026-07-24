import random
import time
import subprocess


def handle_dinghao(recognizer, log, wait_seconds=30, device=None):
    """处理顶号流程：关闭游戏 → 启动游戏 → 等待 → 点击坐标"""
    log("检测到顶号，开始处理...")

    # 获取adb路径
    adb_path = "adb"
    try:
        adb_path = getattr(recognizer, 'adb_path', 'adb')
    except:
        pass

    def build_adb_cmd(cmd_list):
        cmd = [adb_path]
        if device:
            cmd.extend(["-s", device])
        cmd.extend(cmd_list)
        return cmd

    # 1. 关闭游戏
    log("  关闭游戏...")
    try:
        cmd = build_adb_cmd(["shell", "am", "force-stop", "com.netease.onmyoji.wyzymnqsd_cps"])
        subprocess.run(cmd, capture_output=True, timeout=5)
    except Exception as e:
        log(f"  关闭游戏失败: {e}")

    time.sleep(1)

    # 2. 启动游戏
    log("  启动游戏...")
    try:
        cmd = build_adb_cmd(["shell", "monkey", "-p", "com.netease.onmyoji.wyzymnqsd_cps",
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
