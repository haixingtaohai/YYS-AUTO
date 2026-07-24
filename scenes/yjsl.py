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
    
    # 检查是否有特定图片
    has_suoding = any('suoding' in r['name'].lower() for r in results)
    has_tiaozhan = any('tiaozhan' in r['name'].lower() or 'tiaoszhan' in r['name'].lower() for r in results)
    has_jiangli = any('jiangli' in r['name'].lower() or 'shengli' in r['name'].lower() for r in results)
    
    # 先记录日志
    for r in results:
        name = r['name'].replace('.png', '')
        log(name)
    
    # 处理逻辑
    for r in results:
        name_lower = r['name'].lower()
        
        # 通用识别：jujue.png
        if 'jujue' in name_lower:
            _click_random_center(recognizer, r)
            consecutive_challenge = 0
            continue
        
        # suoding优先于tiaozhan
        if 'suoding' in name_lower:
            _click_random_center(recognizer, r)
            consecutive_challenge = 0
            last_clicked_tiaozhan = False
            continue
        
        # 其他图片
        other_names = ['gbyw', 'jytx', 'zhunbei', 'tansuoye', 'ccsl', 'cixinleyuan-tansuo', 'huanxin-tansuo', 'moren-tansuo', '100-tansuo', 'zhimenglianting-tansuo']
        if any(x in name_lower for x in other_names):
            _click_random_center(recognizer, r)
            consecutive_challenge = 0
            last_clicked_tiaozhan = False
            continue
        
        # tiaozhan处理，只有在没有suoding时才处理
        if ('tiaozhan' in name_lower or 'tiaoszhan' in name_lower) and not has_suoding:
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
        
        # jiangli/shengli处理
        if 'jiangli' in name_lower or 'shengli' in name_lower:
            _click_random_xy(recognizer)
            consecutive_challenge = 0
            last_clicked_tiaozhan = False
            continue
    
    return stop_flag, current_count, consecutive_challenge, last_clicked_tiaozhan

def handle_no_recognition():
    return False, 0, False
