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

def _handle_swipe_screen(recognizer, log, device):
    log("滑动屏幕")
    try:
        sx = 1100 + random.randint(-8, 8)
        sy = 360 + random.randint(-8, 8)
        ex = 200 + random.randint(-8, 8)
        ey = 360 + random.randint(-8, 8)
        
        mx = 650 + random.randint(-20, 20)
        my = 360 + random.randint(-10, 10)
        
        cmd1 = [recognizer.adb_path, "-s", device, "shell", "input", "swipe", str(sx), str(sy), str(mx), str(my), str(random.randint(180, 260))]
        cmd2 = [recognizer.adb_path, "-s", device, "shell", "input", "swipe", str(mx), str(my), str(ex), str(ey), str(random.randint(220, 320))]
        
        __import__('subprocess').run(cmd1, capture_output=True, timeout=5)
        __import__('subprocess').run(cmd2, capture_output=True, timeout=5)
    except Exception as e:
        pass
    return False, 0, False

def handle_scene(results, recognizer, log, current_count, target_count, count_challenge, consecutive_challenge, last_clicked_putong_boss):
    consecutive_putong_boss = 0
    stop_flag = False
    need_wait = False
    
    has_boss = any('boss' in r['name'].lower() for r in results)
    has_putong = any('putong' in r['name'].lower() for r in results)
    has_recorded_challenge = False
    
    _log_results(results, log)
    
    for r in results:
        name_lower = r['name'].lower()
        
        if 'jujue' in name_lower:
            _click_random_center(recognizer, r)
            consecutive_challenge = 0
            continue
        
        if has_boss and has_putong and 'putong' in name_lower:
            continue

        if 'ssl' in name_lower:
            _click_random_xy(recognizer, 46, 31)
            consecutive_challenge = 0
            continue
        
        if 'baozang' in name_lower:
            _click_random_center(recognizer, r)
            time.sleep(0.5)
            _click_random_xy(recognizer, recognizer.click_x, recognizer.click_y)
            consecutive_challenge = 0
            continue
        
        clickable = ['boss', 'jinru', 'putong', 'yaoqing']
        if any(x in name_lower for x in clickable):
            _click_random_center(recognizer, r)
            consecutive_challenge = 0
            
            if count_challenge and ('putong' in name_lower or 'boss' in name_lower):
                if not has_recorded_challenge:
                    if not last_clicked_putong_boss:
                        recognizer.tiaozhan_count += 1
                        current_count = recognizer.tiaozhan_count
                        log(f"  挑战次数: {current_count}/{target_count}")
                        if target_count > 0 and current_count >= target_count:
                            log(f"达到目标挑战次数 {target_count}，结束脚本")
                            recognizer.stop_reason = "count"
                            stop_flag = True
                            break
                    else:
                        log("  连续点击挑战，不计入次数")
                    last_clicked_putong_boss = True
                    consecutive_putong_boss += 1
                    has_recorded_challenge = True
                    if consecutive_putong_boss >= 4:
                        log("挑战失败：连续点击4次未识别到奖励")
                        recognizer.stop_reason = "anomaly"
                        stop_flag = True
                        break
                    if 'putong' in name_lower or 'boss' in name_lower:
                        need_wait = True
                else:
                    last_clicked_putong_boss = True
            else:
                last_clicked_putong_boss = False
                consecutive_putong_boss = 0
            continue
        
        reward_names = ['jiangli', 'jianglik28', 'shengli']
        if any(x in name_lower for x in reward_names):
            _click_random_xy(recognizer, recognizer.click_x, recognizer.click_y)
            consecutive_challenge = 0
            consecutive_putong_boss = 0
            last_clicked_putong_boss = False
    
    return stop_flag, current_count, consecutive_challenge, last_clicked_putong_boss, need_wait

def handle_no_recognition(recognizer, log, device):
    return _handle_swipe_screen(recognizer, log, device)
