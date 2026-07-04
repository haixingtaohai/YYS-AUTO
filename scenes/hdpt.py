import random
import time

def _click_random_center(recognizer, results, name_filter):
    """随机点击识别结果的中心"""
    for r in results:
        name_lower = r['name'].lower()
        if name_filter in name_lower:
            if 'center' in r:
                x, y = r['center']
                random_x = x + random.randint(-10, 10)
                random_y = y + random.randint(-10, 10)
                recognizer.click(random_x, random_y)
                return True
    return False

def _click_random_xy(recognizer, x, y):
    """随机点击指定坐标"""
    random_x = x + random.randint(-10, 10)
    random_y = y + random.randint(-10, 10)
    recognizer.click(random_x, random_y)

def _log_results(results, log, current_count=0):
    """记录识别结果，只显示图片名字（不带.png），tiaozhan显示已挑战次数"""
    if results:
        for r in results:
            name_without_ext = r['name'].replace('.png', '')
            if 'tiaozhan' in name_without_ext.lower():
                log(f"{name_without_ext} (已挑战: {current_count}次)")
            else:
                log(name_without_ext)

def _check_has_images(results):
    """检查识别结果中是否有各种图像"""
    has_suoding = any('suoding' in r['name'].lower() for r in results)
    has_tiaozhan = any('tiaozhan' in r['name'].lower() for r in results)
    has_jiangli = any('jiangli' in r['name'].lower() for r in results)
    has_shengli = any('shengli' in r['name'].lower() for r in results)
    has_jujue = any('jujue' in r['name'].lower() for r in results)
    has_exit = any('exit' in r['name'].lower() for r in results)
    return has_suoding, has_tiaozhan, has_jiangli, has_shengli, has_jujue, has_exit

def handle_scene(results, recognizer, log, current_count, target_count, count_challenge, consecutive_challenge, last_clicked_tiaozhan, huijuan_mode=False):
    """处理活动爬塔场景"""
    stop_flag = False

    recognizer.skip_sleep = True

    if not hasattr(recognizer, 'hdpt_consecutive_tiaozhan'):
        recognizer.hdpt_consecutive_tiaozhan = 0

    _log_results(results, log, current_count)

    has_suoding, has_tiaozhan, has_jiangli, has_shengli, has_jujue, has_exit = _check_has_images(results)

    if has_exit:
        log("任务完成")
        recognizer.stop()
        stop_flag = True
        return stop_flag, current_count, 0, False

    # jujue优先级最高
    if has_jujue:
        if _click_random_center(recognizer, results, 'jujue'):
            recognizer.hdpt_consecutive_tiaozhan = 0
            return stop_flag, current_count, consecutive_challenge, last_clicked_tiaozhan

    if has_suoding:
        if _click_random_center(recognizer, results, 'suoding'):
            recognizer.hdpt_consecutive_tiaozhan = 0
            return stop_flag, current_count, 0, False

    if has_tiaozhan:
        if _click_random_center(recognizer, results, 'tiaozhan'):
            recognizer.hdpt_consecutive_tiaozhan += 1
            if count_challenge:
                current_count += 1
                if current_count >= target_count:
                    log("挑战完成")
                    stop_flag = True
            if recognizer.hdpt_consecutive_tiaozhan >= 4:
                log("程序异常")
                recognizer.stop()
                stop_flag = True
            return stop_flag, current_count, 0, False

    if has_jiangli:
        _click_random_xy(recognizer, recognizer.click_x, recognizer.click_y)
        recognizer.hdpt_consecutive_tiaozhan = 0
        return stop_flag, current_count, 0, False

    if has_shengli:
        _click_random_xy(recognizer, recognizer.click_x, recognizer.click_y)
        recognizer.hdpt_consecutive_tiaozhan = 0
        return stop_flag, current_count, 0, False

    if not (has_suoding or has_tiaozhan or has_jiangli or has_shengli or has_jujue or has_exit):
        recognizer.hdpt_consecutive_tiaozhan = 0

    return stop_flag, current_count, consecutive_challenge, last_clicked_tiaozhan

def handle_no_recognition(recognizer, log, device):
    """处理无识别结果的情况"""
    if hasattr(recognizer, 'hdpt_consecutive_tiaozhan'):
        recognizer.hdpt_consecutive_tiaozhan = 0
    return False, 0, False
