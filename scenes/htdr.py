import random
import time

def _click_random_center(recognizer, result):
    """点击图片中心，随机偏移±10像素"""
    x, y = result['center']
    random_x = x + random.randint(-10, 10)
    random_y = y + random.randint(-10, 10)
    recognizer.click(random_x, random_y)

def _click_random_xy(recognizer):
    """点击通用坐标，随机偏移±10像素"""
    random_x = recognizer.click_x + random.randint(-10, 10)
    random_y = recognizer.click_y + random.randint(-10, 10)
    recognizer.click(random_x, random_y)

def handle_scene(results, recognizer, log, current_count, target_count, count_challenge, consecutive_challenge, last_clicked_tiaozhan):
    stop_flag = False
    
    # 检查是否同时识别到suoding和tiaozhan
    has_suoding = any('suoding' in r['name'].lower() for r in results)
    has_tiaozhan = any('tiaozhan' in r['name'].lower() or 'tiaoszhan' in r['name'].lower() for r in results)
    
    for r in results:
        name = r['name'].replace('.png', '')
        log(name)
        
        name_lower = r['name'].lower()
        
        # 通用识别：jujue.png
        if 'jujue' in name_lower:
            _click_random_center(recognizer, r)
            consecutive_challenge = 0
        elif 'suoding' in name_lower:
            # suoding优先于tiaozhan处理
            _click_random_center(recognizer, r)
            consecutive_challenge = 0
            last_clicked_tiaozhan = False
        elif 'tansuoye' in name_lower:
            # 识别到tansuoye点击图片坐标
            _click_random_center(recognizer, r)
            consecutive_challenge = 0
            last_clicked_tiaozhan = False
        elif 'bqds' in name_lower:
            # 识别到bqds点击图片坐标
            _click_random_center(recognizer, r)
            consecutive_challenge = 0
            last_clicked_tiaozhan = False
        elif 'tansuo' in name_lower:
            # 识别到xx-tansuo系列图片点击图片坐标
            _click_random_center(recognizer, r)
            consecutive_challenge = 0
            last_clicked_tiaozhan = False
        elif ('tiaozhan' in name_lower or 'tiaoszhan' in name_lower) and not has_suoding:
            # 只有在没有识别到suoding时才处理tiaozhan
            _click_random_center(recognizer, r)
            if count_challenge:
                # 连续点击两次tiaozhan视为无效次数，不计入
                if not last_clicked_tiaozhan:
                    recognizer.tiaozhan_count += 1
                    current_count = recognizer.tiaozhan_count
                    # 显示当前次数/目标次数
                    log(f"  挑战次数: {current_count}/{target_count}")
                    # 检查是否达到目标次数
                    if target_count > 0 and current_count >= target_count:
                        log(f"达到目标挑战次数 {target_count}，结束脚本")
                        recognizer.stop_reason = "count"
                        stop_flag = True
                        break
                else:
                    log("  连续点击挑战，不计入次数")
            # 更新上一次点击状态
            last_clicked_tiaozhan = True
            consecutive_challenge += 1
            if consecutive_challenge >= 4:
                log("挑战失败：连续点击4次未识别到奖励")
                recognizer.stop_reason = "anomaly"
                stop_flag = True
                break
        elif 'jiangli' in name_lower or 'shengli' in name_lower:
            # 点击指定坐标（XY各随机加减10）
            _click_random_xy(recognizer)
            consecutive_challenge = 0
            last_clicked_tiaozhan = False  # 重置连续点击状态
        elif 'baozang' in name_lower:
            # 魂土系列预设：识别到baozang点击指定坐标
            _click_random_xy(recognizer)
            consecutive_challenge = 0
            last_clicked_tiaozhan = False  # 重置连续点击状态
    
    return stop_flag, current_count, consecutive_challenge, last_clicked_tiaozhan

def handle_no_recognition():
    return False, 0, False
