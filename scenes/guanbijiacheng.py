import random
import time
import os

def handle_close_jiacheng(recognizer, log, jiacheng_folder, device=None):
    # 处理关闭加成流程
    
    # 获取adb路径
    adb_path = "adb"
    try:
        adb_path = getattr(recognizer, 'adb_path', 'adb')
    except:
        pass
    
    # 构建adb命令
    def build_adb_cmd(cmd_list):
        cmd = [adb_path]
        if device:
            cmd.extend(["-s", device])
        cmd.extend(cmd_list)
        return cmd
    
    # 1. 关闭游戏
    try:
        import subprocess
        cmd = build_adb_cmd(["shell", "am", "force-stop", "com.netease.onmyoji.wyzymnqsd_cps"])
        subprocess.run(cmd, capture_output=True, timeout=5)
    except Exception as e:
        pass
    
    time.sleep(1)
    
    # 2. 打开游戏
    try:
        import subprocess
        cmd = build_adb_cmd(["shell", "monkey", "-p", "com.netease.onmyoji.wyzymnqsd_cps", 
                            "-c", "android.intent.category.LAUNCHER", "1"])
        subprocess.run(cmd, capture_output=True, timeout=10)
    except Exception as e:
        pass
    
    # 等待游戏加载
    time.sleep(10)
    
    # 设置识别文件夹为jiacheng
    original_folder = recognizer.folder
    recognizer.folder = jiacheng_folder
    
    yxnjc_completed = False
    max_attempts = 60  # 最多尝试60次（约2分钟）
    attempts = 0
    
    while not yxnjc_completed and attempts < max_attempts:
        attempts += 1
        results = recognizer.run_once()
        
        if results:
            for r in results:
                name = r['name'].replace('.png', '')
                log(name)
                
                name_lower = r['name'].lower()
                
                if 'guanbi' in name_lower:
                    # 识别到guanbi点击图片坐标
                    x, y = r['center']
                    random_x = x + random.randint(-10, 10)
                    random_y = y + random.randint(-10, 10)
                    recognizer.click(random_x, random_y)
                    time.sleep(2)
                elif 'jinru' in name_lower:
                    # 识别到jinru点击图片坐标
                    x, y = r['center']
                    random_x = x + random.randint(-10, 10)
                    random_y = y + random.randint(-10, 10)
                    recognizer.click(random_x, random_y)
                    time.sleep(2)
                elif 'yxnjc' in name_lower:
                    # 识别到yxnjc先点击图片坐标
                    x, y = r['center']
                    random_x = x + random.randint(-10, 10)
                    random_y = y + random.randint(-10, 10)
                    recognizer.click(random_x, random_y)
                    time.sleep(1)
                    
                    # 等待一秒后点击822 222
                    random_x1 = 822 + random.randint(-10, 10)
                    random_y1 = 222 + random.randint(-10, 10)
                    recognizer.click(random_x1, random_y1)
                    time.sleep(2)
                    
                    # 再等待两秒后点击777 666
                    random_x2 = 777 + random.randint(-10, 10)
                    random_y2 = 666 + random.randint(-10, 10)
                    recognizer.click(random_x2, random_y2)
                    
                    yxnjc_completed = True
                    break
        
        time.sleep(2)
    
    # 恢复原始文件夹
    recognizer.folder = original_folder
    
    return yxnjc_completed
