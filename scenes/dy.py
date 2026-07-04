import random
import time

def handle_scene(results, recognizer, log, current_count, target_count, count_challenge, consecutive_challenge, last_clicked_tiaozhan, is_ready_callback=None, mark_unready_callback=None):
    stop_flag = False
    is_ready = False
    
    for r in results:
        name = r['name'].replace('.png', '')
        log(name)
        
        name_lower = r['name'].lower()
        
        # 通用识别：jujue.png
        if 'jujue' in name_lower:
            # 识别到jujue点击目标图片坐标（图片内随机）
            x, y = r['center']
            random_x = x + random.randint(-10, 10)
            random_y = y + random.randint(-10, 10)
            recognizer.click(random_x, random_y)
            consecutive_challenge = 0
        
        elif 'duiwu' in name_lower:
            # 识别到duiwu视为队员已准备状态
            is_ready = True
            if is_ready_callback:
                is_ready_callback()
        elif 'jiangli' in name_lower or 'shengli' in name_lower:
            # 点击指定坐标（XY各随机加减10）
            random_x = recognizer.click_x + random.randint(-10, 10)
            random_y = recognizer.click_y + random.randint(-10, 10)
            recognizer.click(random_x, random_y)
            consecutive_challenge = 0
            last_clicked_tiaozhan = False  # 重置连续点击状态
            # 识别到奖励后回到未准备状态
            if mark_unready_callback:
                mark_unready_callback()
        elif 'baozang' in name_lower:
            # 魂土系列预设：识别到baozang点击指定坐标
            random_x = recognizer.click_x + random.randint(-10, 10)
            random_y = recognizer.click_y + random.randint(-10, 10)
            recognizer.click(random_x, random_y)
            consecutive_challenge = 0
            last_clicked_tiaozhan = False  # 重置连续点击状态
        elif 'jieshou' in name_lower:
            # 魂土队员：识别到jieshou点击图片坐标
            x, y = r['center']
            random_x = x + random.randint(-10, 10)
            random_y = y + random.randint(-10, 10)
            recognizer.click(random_x, random_y)
            consecutive_challenge = 0
            last_clicked_tiaozhan = False  # 重置连续点击状态
            # 魂土队员：识别到jieshou时增加挑战次数
            if count_challenge:
                recognizer.tiaozhan_count += 1
                current_count = recognizer.tiaozhan_count
                log(f"  挑战次数: {current_count}/无")
    
    return stop_flag, current_count, consecutive_challenge, last_clicked_tiaozhan

def handle_no_recognition():
    return False, 0, False