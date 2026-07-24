import random
import time

def _click_random_center(recognizer, result):
    x, y = result['center']
    random_x = x + random.randint(-10, 10)
    random_y = y + random.randint(-10, 10)
    recognizer.click(random_x, random_y)

def _click_random_xy(recognizer, x, y):
    random_x = x + random.randint(-10, 10)
    random_y = y + random.randint(-10, 10)
    recognizer.click(random_x, random_y)

def _log_results(results, log):
    for r in results:
        name = r['name'].replace('.png', '')
        log(name)

def handle_scene(results, recognizer, log, current_count, target_count, count_challenge, consecutive_challenge, last_clicked_tiaozhan, dj_jinsheng_stop=False):
    stop_flag = False
    
    has_jinsheng = any('jinsheng' in r['name'].lower() for r in results)
    has_jixu = any('jixu' in r['name'].lower() for r in results)
    
    if has_jinsheng:
        if dj_jinsheng_stop:
            log("识别到jinsheng，斗技段位晋升结束程序")
            recognizer.stop_reason = "image"
            stop_flag = True
            return stop_flag, current_count, consecutive_challenge, False
        else:
            log("识别到jinsheng，点击1202 55")
            _click_random_xy(recognizer, 1202, 55)
            consecutive_challenge = 0
            return stop_flag, current_count, consecutive_challenge, False
    
    _log_results(results, log)
    
    for r in results:
        name_lower = r['name'].lower()
        
        if 'jujue' in name_lower:
            _click_random_center(recognizer, r)
            consecutive_challenge = 0
            continue
        
        if 'jieshu' in name_lower or 'jixu' in name_lower:
            _click_random_xy(recognizer, recognizer.click_x, recognizer.click_y)
            consecutive_challenge = 0
            continue
        
        _click_random_center(recognizer, r)
        
        if count_challenge and 'zhandou' in name_lower:
            recognizer.tiaozhan_count += 1
            current_count = recognizer.tiaozhan_count
            log(f"  挑战次数: {current_count}/{target_count}")
            if target_count > 0 and current_count >= target_count:
                log(f"达到目标挑战次数 {target_count}，结束脚本")
                recognizer.stop_reason = "count"
                stop_flag = True
                break
        
        consecutive_challenge = 0
    
    return stop_flag, current_count, consecutive_challenge, False

def handle_no_recognition():
    return False, 0, False
