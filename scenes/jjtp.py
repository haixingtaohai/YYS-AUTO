import random
import time

def _initialize_card57_mode(recognizer, log):
    if not hasattr(recognizer, 'jjtp_card57_mode'):
        recognizer.jjtp_card57_mode = False
        recognizer.jjtp_card57_step = 0
        recognizer.jjtp_card57_round = 0

def _check_has_images(results):
    has_suoding = any('suoding' in r['name'].lower() for r in results)
    has_jiangli = any('jiangli' in r['name'].lower() or 'shengli' in r['name'].lower() for r in results)
    has_numbers = any(str(i) in r['name'] for i in range(6) for r in results)
    has_tansuo = any('tansuo' in r['name'].lower() for r in results)
    has_pg0 = any('pg0' in r['name'].lower() for r in results)
    has_jingong = any('jingong' in r['name'].lower() for r in results)
    has_queren = any('queren' in r['name'].lower() for r in results)
    has_0q = any('0q' in r['name'].lower() for r in results)
    has_tuichu = any('tuichu' in r['name'].lower() or 'tuichu2' in r['name'].lower() for r in results)
    has_shibai = any('shibai' in r['name'].lower() for r in results)
    return has_suoding, has_jiangli, has_numbers, has_tansuo, has_pg0, has_jingong, has_queren, has_0q, has_tuichu, has_shibai

def _log_results(results, log):
    if results:
        for r in results:
            name_without_ext = r['name'].replace('.png', '')
            log(name_without_ext)

def _handle_0q(has_0q, huijuan_mode, log, recognizer):
    if not has_0q:
        return False, None, None
    if huijuan_mode:
        log("切换困28")
        return True, False, True
    recognizer.stop()
    return True, True, False

def _enter_card57_mode(has_pg0, recognizer, log):
    if has_pg0 and not recognizer.jjtp_card57_mode:
        recognizer.jjtp_card57_mode = True
        recognizer.jjtp_card57_step = 0
        recognizer.jjtp_card57_round = 0
        recognizer.skip_sleep = True

def _get_round_configs():
    return [
        {'click1': (300, 200), 'click2': (380, 390)},
        {'click1': (650, 200), 'click2': (714, 390)},
        {'click1': (1000, 200), 'click2': (1050, 390)},
        {'click1': (300, 350), 'click2': (389, 523)}
    ]

def _click_random_center(recognizer, results, name_filter):
    for r in results:
        if name_filter in r['name'].lower():
            x, y = r['center']
            random_x = x + random.randint(-10, 10)
            random_y = y + random.randint(-10, 10)
            recognizer.click(random_x, random_y)
            return True
    return False

def _click_random_xy(recognizer, x, y):
    random_x = x + random.randint(-10, 10)
    random_y = y + random.randint(-10, 10)
    recognizer.click(random_x, random_y)

def _handle_card57_step_0(recognizer, log):
    log("(266, 605)")
    recognizer.click(266, 605)
    time.sleep(0.8)
    log("(266, 605)")
    recognizer.click(266, 605)
    time.sleep(0.8)
    log("(831, 597)")
    recognizer.click(831, 597)
    recognizer.jjtp_card57_step = 1
    return True

def _handle_card57_step_1(recognizer, log, round_configs):
    config = round_configs[0]
    log(f"{config['click1']}")
    recognizer.click(config['click1'][0], config['click1'][1])
    time.sleep(0.5)
    log(f"{config['click2']}")
    recognizer.click(config['click2'][0], config['click2'][1])
    recognizer.jjtp_card57_step = 2
    return True

def _handle_card57_step_2(recognizer, log, results, has_tuichu):
    if not has_tuichu:
        return False
    _click_random_center(recognizer, results, 'tuichu')
    _click_random_center(recognizer, results, 'tuichu2')
    time.sleep(0.5)
    log("(749, 422)")
    recognizer.click(749, 422)
    recognizer.jjtp_card57_step = 3
    return True

def _handle_card57_step_3(recognizer, log, has_shibai):
    if not has_shibai:
        return False
    _click_random_xy(recognizer, recognizer.click_x, recognizer.click_y)
    time.sleep(1)
    recognizer.jjtp_card57_step = 4
    return True

def _handle_card57_step_4(recognizer, log, round_configs):
    config = round_configs[1]
    log(f"{config['click1']}")
    recognizer.click(config['click1'][0], config['click1'][1])
    time.sleep(0.5)
    log(f"{config['click2']}")
    recognizer.click(config['click2'][0], config['click2'][1])
    recognizer.jjtp_card57_step = 5
    return True

def _handle_card57_step_5(recognizer, log, results, has_tuichu):
    if not has_tuichu:
        return False
    _click_random_center(recognizer, results, 'tuichu')
    _click_random_center(recognizer, results, 'tuichu2')
    time.sleep(0.5)
    log("(749, 422)")
    recognizer.click(749, 422)
    recognizer.jjtp_card57_step = 6
    return True

def _handle_card57_step_6(recognizer, log, has_shibai):
    if not has_shibai:
        return False
    _click_random_xy(recognizer, recognizer.click_x, recognizer.click_y)
    time.sleep(1)
    recognizer.jjtp_card57_step = 7
    return True

def _handle_card57_step_7(recognizer, log, round_configs):
    config = round_configs[2]
    log(f"{config['click1']}")
    recognizer.click(config['click1'][0], config['click1'][1])
    time.sleep(0.5)
    log(f"{config['click2']}")
    recognizer.click(config['click2'][0], config['click2'][1])
    recognizer.jjtp_card57_step = 8
    return True

def _handle_card57_step_8(recognizer, log, results, has_tuichu):
    if not has_tuichu:
        return False
    _click_random_center(recognizer, results, 'tuichu')
    _click_random_center(recognizer, results, 'tuichu2')
    time.sleep(0.5)
    log("(749, 422)")
    recognizer.click(749, 422)
    recognizer.jjtp_card57_step = 9
    return True

def _handle_card57_step_9(recognizer, log, has_shibai):
    if not has_shibai:
        return False
    _click_random_xy(recognizer, recognizer.click_x, recognizer.click_y)
    time.sleep(1)
    recognizer.jjtp_card57_step = 10
    return True

def _handle_card57_step_10(recognizer, log, round_configs):
    config = round_configs[3]
    log(f"{config['click1']}")
    recognizer.click(config['click1'][0], config['click1'][1])
    time.sleep(0.5)
    log(f"{config['click2']}")
    recognizer.click(config['click2'][0], config['click2'][1])
    recognizer.jjtp_card57_step = 11
    return True

def _handle_card57_step_11(recognizer, log, results, has_tuichu):
    if not has_tuichu:
        return False
    _click_random_center(recognizer, results, 'tuichu')
    _click_random_center(recognizer, results, 'tuichu2')
    time.sleep(0.5)
    log("(749, 422)")
    recognizer.click(749, 422)
    recognizer.jjtp_card57_step = 12
    return True

def _handle_card57_step_12(recognizer, log, has_shibai):
    if not has_shibai:
        return False
    _click_random_xy(recognizer, recognizer.click_x, recognizer.click_y)
    time.sleep(1.5)
    recognizer.jjtp_card57_step = 13
    return True

def _handle_card57_step_13(recognizer, log):
    log("(831, 597)")
    recognizer.click(831, 597)
    time.sleep(0.5)
    log("(650, 350)")
    recognizer.click(650, 350)
    time.sleep(0.5)
    log("(720, 525)")
    recognizer.click(720, 525)
    recognizer.jjtp_card57_mode = False
    recognizer.jjtp_card57_step = 0
    recognizer.jjtp_card57_round = 0
    return True

def _handle_card57_mode(recognizer, log, results, has_tuichu, has_shibai):
    round_configs = _get_round_configs()
    
    step_handlers = {
        0: lambda: _handle_card57_step_0(recognizer, log),
        1: lambda: _handle_card57_step_1(recognizer, log, round_configs),
        2: lambda: _handle_card57_step_2(recognizer, log, results, has_tuichu),
        3: lambda: _handle_card57_step_3(recognizer, log, has_shibai),
        4: lambda: _handle_card57_step_4(recognizer, log, round_configs),
        5: lambda: _handle_card57_step_5(recognizer, log, results, has_tuichu),
        6: lambda: _handle_card57_step_6(recognizer, log, has_shibai),
        7: lambda: _handle_card57_step_7(recognizer, log, round_configs),
        8: lambda: _handle_card57_step_8(recognizer, log, results, has_tuichu),
        9: lambda: _handle_card57_step_9(recognizer, log, has_shibai),
        10: lambda: _handle_card57_step_10(recognizer, log, round_configs),
        11: lambda: _handle_card57_step_11(recognizer, log, results, has_tuichu),
        12: lambda: _handle_card57_step_12(recognizer, log, has_shibai),
        13: lambda: _handle_card57_step_13(recognizer, log),
    }
    
    step = recognizer.jjtp_card57_step
    if step in step_handlers:
        try:
            handled = step_handlers[step]()
            if handled:
                return True
        except Exception as e:
            recognizer.jjtp_card57_mode = False
            recognizer.jjtp_card57_step = 0
            recognizer.jjtp_card57_round = 0
    else:
        recognizer.jjtp_card57_mode = False
        recognizer.jjtp_card57_step = 0
        recognizer.jjtp_card57_round = 0
    
    return False

def _handle_normal_mode(results, recognizer, has_tansuo, has_suoding, has_numbers, has_jingong, has_jiangli, has_queren, consecutive_challenge, last_clicked_tiaozhan):
    if _click_random_center(recognizer, results, 'jujue'):
        return 0, False, False
    
    if has_tansuo:
        recognizer.click(30, 37)
        return 0, False, True
    
    if has_suoding:
        if _click_random_center(recognizer, results, 'suoding'):
            return 0, False, True
    
    if has_numbers and has_jingong:
        if _click_random_center(recognizer, results, 'jingong'):
            return 0, False, True
    
    if has_jiangli:
        _click_random_xy(recognizer, recognizer.click_x, recognizer.click_y)
        return 0, False, True
    
    if has_numbers:
        numbers = []
        for r in results:
            for i in range(6):
                if str(i) in r['name']:
                    numbers.append((i, r))
        if numbers:
            numbers.sort(key=lambda x: x[0], reverse=True)
            _, r = numbers[0]
            x, y = r['center']
            random_x = x + random.randint(-10, 10)
            random_y = y + random.randint(-10, 10)
            recognizer.click(random_x, random_y)
            return 0, False, True
    
    for r in results:
        name_lower = r['name'].lower()
        
        if 'shibai' in name_lower:
            _click_random_xy(recognizer, recognizer.click_x, recognizer.click_y)
            return 0, False, False
        elif 'queren' in name_lower:
            if _click_random_center(recognizer, results, 'queren'):
                return 0, False, False
        elif 'jingong' in name_lower or 'jinru' in name_lower:
            _click_random_center(recognizer, results, 'jingong')
            _click_random_center(recognizer, results, 'jinru')
            return 0, False, False
    
    return consecutive_challenge, last_clicked_tiaozhan, False

def handle_scene(results, recognizer, log, current_count, target_count, count_challenge, consecutive_challenge, last_clicked_tiaozhan, huijuan_mode=False):
    stop_flag = False
    switch_to_k28 = False

    recognizer.skip_sleep = True

    _initialize_card57_mode(recognizer, log)

    if not hasattr(recognizer, 'jjtp_consecutive_jingong'):
        recognizer.jjtp_consecutive_jingong = 0

    if not recognizer.jjtp_card57_mode:
        results = [r for r in results if 'tuichu' not in r['name'].lower() and 'tuichu2' not in r['name'].lower()]

    _log_results(results, log)

    has_suoding, has_jiangli, has_numbers, has_tansuo, has_pg0, has_jingong, has_queren, has_0q, has_tuichu, has_shibai = _check_has_images(results)

    should_return, stop_flag, switch_to_k28 = _handle_0q(has_0q, huijuan_mode, log, recognizer)
    if should_return:
        return stop_flag, current_count, consecutive_challenge, last_clicked_tiaozhan, switch_to_k28

    _enter_card57_mode(has_pg0, recognizer, log)

    if recognizer.jjtp_card57_mode:
        handled = _handle_card57_mode(recognizer, log, results, has_tuichu, has_shibai)
        if handled:
            return stop_flag, current_count, consecutive_challenge, last_clicked_tiaozhan, switch_to_k28

    if has_jingong:
        recognizer.jjtp_consecutive_jingong += 1
    else:
        recognizer.jjtp_consecutive_jingong = 0

    if recognizer.jjtp_consecutive_jingong >= 4:
        log("连续点击jingong四次，异常停止")
        recognizer.stop()
        return True, current_count, consecutive_challenge, last_clicked_tiaozhan, switch_to_k28

    new_consecutive, new_last_clicked, should_return = _handle_normal_mode(
        results, recognizer, has_tansuo, has_suoding, has_numbers, has_jingong, has_jiangli, has_queren, 
        consecutive_challenge, last_clicked_tiaozhan
    )
    
    if should_return:
        return stop_flag, current_count, new_consecutive, new_last_clicked, switch_to_k28

    return stop_flag, current_count, new_consecutive, new_last_clicked, switch_to_k28

def handle_no_recognition(recognizer, log, device):
    if not hasattr(recognizer, 'jjtp_card57_mode'):
        recognizer.jjtp_card57_mode = False
        recognizer.jjtp_card57_step = 0
        recognizer.jjtp_card57_round = 0

    if not hasattr(recognizer, 'jjtp_consecutive_jingong'):
        recognizer.jjtp_consecutive_jingong = 0
    recognizer.jjtp_consecutive_jingong = 0

    if recognizer.jjtp_card57_mode:
        return False, 0, False

    return False, 0, False
