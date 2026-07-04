import random
import time

def _click_random_center(recognizer, r):
    x, y = r['center']
    random_x = x + random.randint(-10, 10)
    random_y = y + random.randint(-10, 10)
    recognizer.click(random_x, random_y)

def _click_random_xy(recognizer, x, y):
    random_x = x + random.randint(-10, 10)
    random_y = y + random.randint(-10, 10)
    recognizer.click(random_x, random_y)

def _log_results(results, log):
    for r in results:
        log(r['name'].replace('.png', ''))

def _has_dengdai(results):
    return any('dengdaigz' in r['name'].lower() or 'dengdaikz' in r['name'].lower() for r in results)

def handle_scene(results, recognizer, log, current_count, target_count, count_challenge, consecutive_challenge, last_clicked_tiaozhan):
    if not hasattr(recognizer, 'tiaozhan_count_dg'):
        recognizer.tiaozhan_count_dg = 0
    tiaozhan_count = recognizer.tiaozhan_count_dg
    stop_flag = False

    _log_results(results, log)

    # 识别到dengdaigz或dengdaikz时，屏蔽tiaozhan点击，等待5秒
    if _has_dengdai(results):
        log("识别到等待状态，等待5秒")
        time.sleep(5)
        return stop_flag, current_count, consecutive_challenge, False

    for r in results:
        name_lower = r['name'].lower()

        if 'jujue' in name_lower:
            _click_random_center(recognizer, r)
            consecutive_challenge = 0
        elif 'tiaozhan' in name_lower:
            tiaozhan_count += 1
            _click_random_center(recognizer, r)
            consecutive_challenge = 0

            if tiaozhan_count >= 5:
                log("连续点击挑战五次，进入冷却倒计时60秒")
                for i in range(60, 0, -1):
                    log(f"冷却倒计时: {i}秒")
                    time.sleep(1)
                    if stop_flag or not getattr(recognizer, 'running', True):
                        break
                log("冷却结束，继续识别")
                tiaozhan_count = 0
        elif 'zhunbei' in name_lower:
            _click_random_center(recognizer, r)
            consecutive_challenge = 0
        elif 'yxnjc' in name_lower:
            log("识别到yxnjc，任务完成，停止运行")
            stop_flag = True
            return stop_flag, current_count, consecutive_challenge, False
        elif 'shengli' in name_lower or 'jiangli' in name_lower or 'shibai' in name_lower or 'jiesuan' in name_lower:
            _click_random_xy(recognizer, recognizer.click_x, recognizer.click_y)
            consecutive_challenge = 0
            tiaozhan_count = 0

    recognizer.tiaozhan_count_dg = tiaozhan_count
    return stop_flag, current_count, consecutive_challenge, False

def handle_no_recognition():
    return False, 0, False
