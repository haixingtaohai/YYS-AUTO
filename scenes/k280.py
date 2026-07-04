import random
import time

def handle_scene(results, recognizer, log, current_count, target_count, count_challenge, consecutive_challenge, last_clicked_tiaozhan):
    stop_flag = False
    
    for r in results:
        name = r['name'].replace('.png', '')
        log(name)
        
        name_lower = r['name'].lower()
        
        # 保留识别通用图片jujue.png点击图片坐标
        if 'jujue' in name_lower:
            x, y = r['center']
            random_x = x + random.randint(-10, 10)
            random_y = y + random.randint(-10, 10)
            recognizer.click(random_x, random_y)
            consecutive_challenge = 0
        # 点击图片坐标的图片：baozang、jieshou
        elif 'baozang' in name_lower or 'jieshou' in name_lower:
            x, y = r['center']
            random_x = x + random.randint(-10, 10)
            random_y = y + random.randint(-10, 10)
            recognizer.click(random_x, random_y)
            consecutive_challenge = 0
            last_clicked_tiaozhan = False
        # 点击通用指定坐标的图片：jiangli、jianglik28、shengli
        elif 'jiangli' in name_lower or 'jianglik28' in name_lower or 'shengli' in name_lower:
            random_x = recognizer.click_x + random.randint(-10, 10)
            random_y = recognizer.click_y + random.randint(-10, 10)
            recognizer.click(random_x, random_y)
            consecutive_challenge = 0
            last_clicked_tiaozhan = False
    
    return stop_flag, current_count, consecutive_challenge, last_clicked_tiaozhan

def handle_no_recognition(recognizer, log, device):
    return False, 0, False
