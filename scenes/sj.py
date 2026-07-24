import random
import time

def handle_scene(results, recognizer, log, current_count, target_count, count_challenge, consecutive_challenge, last_clicked_tiaozhan, link_enabled=False, check_teammates_ready=None, mark_teammates_unready=None):
    stop_flag = False
    
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
        elif 'tiaozhan' in name_lower or 'tiaoszhan' in name_lower:
            # 司机队员联动模式：检查队员是否已准备
            if link_enabled and check_teammates_ready and not check_teammates_ready():
                log("  队员未准备，等待队员")
                continue
            # 点击图片坐标（图片内随机）
            x, y = r['center']
            random_x = x + random.randint(-10, 10)
            random_y = y + random.randint(-10, 10)
            recognizer.click(random_x, random_y)
            # 司机点击tiaozhan后，队员回到未准备状态
            if link_enabled and mark_teammates_unready:
                mark_teammates_unready()
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
            random_x = recognizer.click_x + random.randint(-10, 10)
            random_y = recognizer.click_y + random.randint(-10, 10)
            recognizer.click(random_x, random_y)
            consecutive_challenge = 0
            last_clicked_tiaozhan = False  # 重置连续点击状态
        elif 'baozang' in name_lower:
            # 魂土系列预设：识别到baozang点击指定坐标
            random_x = recognizer.click_x + random.randint(-10, 10)
            random_y = recognizer.click_y + random.randint(-10, 10)
            recognizer.click(random_x, random_y)
            consecutive_challenge = 0
            last_clicked_tiaozhan = False  # 重置连续点击状态
        elif 'yaoqing' in name_lower:
            # 魂土司机：识别到yaoqing先点击560,360，间隔一秒再次点击750,430
            # 第一次点击
            random_x1 = 560 + random.randint(-10, 10)
            random_y1 = 360 + random.randint(-10, 10)
            recognizer.click(random_x1, random_y1)
            # 间隔一秒
            time.sleep(1)
            # 第二次点击
            random_x2 = 750 + random.randint(-10, 10)
            random_y2 = 430 + random.randint(-10, 10)
            recognizer.click(random_x2, random_y2)
            consecutive_challenge = 0
            last_clicked_tiaozhan = False  # 重置连续点击状态
    
    return stop_flag, current_count, consecutive_challenge, last_clicked_tiaozhan

def handle_no_recognition():
    return False, 0, False