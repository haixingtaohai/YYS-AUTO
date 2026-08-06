import random

def _click_random_center(recognizer, result):
    x, y = result['center']
    random_x = x + random.randint(-10, 10)
    random_y = y + random.randint(-10, 10)
    recognizer.click(random_x, random_y)

def _click_random_xy(recognizer):
    random_x = recognizer.click_x + random.randint(-10, 10)
    random_y = recognizer.click_y + random.randint(-10, 10)
    recognizer.click(random_x, random_y)

def handle_scene(results, recognizer, log, current_count, target_count, count_challenge, consecutive_challenge, last_clicked_tiaozhan, ql_fangqi=False, ql_zaici=False):
    stop_flag = False

    # 先记录日志
    for r in results:
        name = r['name'].replace('.png', '')
        log(name)

    # 预检测：suoding和挑战同时出现时，只点suoding
    has_suoding = any('suoding' in r['name'].lower() for r in results)

    # 处理逻辑
    for r in results:
        name_lower = r['name'].lower()

        # 通用识别：jujue 优先级最高
        if 'jujue' in name_lower:
            _click_random_center(recognizer, r)
            consecutive_challenge = 0
            last_clicked_tiaozhan = False
            continue

        # suoding：仅在suoding出现时点击（优先级高于挑战）
        if 'suoding' in name_lower:
            _click_random_center(recognizer, r)
            consecutive_challenge = 0
            last_clicked_tiaozhan = False
            continue

        # tancha-tiaozhan / jieqi-tiaozhan：仅在没有suoding时才点击
        if ('tancha-tiaozhan' in name_lower or 'jieqi-tiaozhan' in name_lower) and not has_suoding:
            _click_random_center(recognizer, r)
            if count_challenge:
                if not last_clicked_tiaozhan:
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
            last_clicked_tiaozhan = True
            consecutive_challenge += 1
            if consecutive_challenge >= 4:
                log("挑战失败：连续点击4次未识别到奖励")
                recognizer.stop_reason = "anomaly"
                stop_flag = True
                break
            continue

        # jiangli/jiangli3/shengli：点击通用坐标
        if 'jiangli' in name_lower or 'shengli' in name_lower or "jiangli4" in name_lower:
            _click_random_xy(recognizer)
            consecutive_challenge = 0
            last_clicked_tiaozhan = False
            continue

        # fangqi：再次结契模式时屏蔽
        if 'fangqi' in name_lower and not ql_zaici:
            _click_random_center(recognizer, r)
            consecutive_challenge = 0
            last_clicked_tiaozhan = False
            continue

        # zaici：放弃结契模式时屏蔽
        if 'zaici' in name_lower and not ql_fangqi:
            _click_random_center(recognizer, r)
            consecutive_challenge = 0
            last_clicked_tiaozhan = False
            continue

    return stop_flag, current_count, consecutive_challenge, last_clicked_tiaozhan

def handle_no_recognition():
    return False, 0, False
