import random

def _click_random_center(recognizer, result):
    x, y = result['center']
    random_x = x + random.randint(-10, 10)
    random_y = y + random.randint(-10, 10)
    recognizer.click(random_x, random_y)

def _click_random_xy(recognizer, x, y):
    random_x = x + random.randint(-10, 10)
    random_y = y + random.randint(-10, 10)
    recognizer.click(random_x, random_y)

def handle_scene(results, recognizer, log, current_count, target_count, count_challenge, consecutive_challenge, last_clicked_chufa):
    stop_flag = False
    need_wait = False

    # 先记录日志
    for r in results:
        name = r['name'].replace('.png', '')
        log(name)

    # 预检测：suoding出现时，屏蔽低优先级图片
    has_suoding = any('suoding' in r['name'].lower() for r in results)

    qiangduo_coords = [(202, 492), (529, 568), (789, 566), (1069, 419)]

    # 处理逻辑
    for r in results:
        name_lower = r['name'].lower()

        # 通用识别：jujue 优先级最高
        if 'jujue' in name_lower:
            _click_random_center(recognizer, r)
            consecutive_challenge = 0
            last_clicked_chufa = False
            continue

        # exit：视为任务完成，停止任务
        if 'exit' in name_lower:
            log("识别到exit，任务完成")
            recognizer.stop_reason = "count"
            stop_flag = True
            break

        # suoding：优先级最高
        if 'suoding' in name_lower:
            _click_random_center(recognizer, r)
            consecutive_challenge = 0
            last_clicked_chufa = False
            continue

        # tishi：点击固定坐标
        if 'tishi' in name_lower:
            _click_random_xy(recognizer, 1186, 80)
            consecutive_challenge = 0
            last_clicked_chufa = False
            continue

        # touzhi：点击固定坐标
        if 'touzhi' in name_lower:
            _click_random_xy(recognizer, 1084, 537)
            consecutive_challenge = 0
            last_clicked_chufa = False
            continue

        # qiangduo：随机点击四组坐标其中一个
        if 'qiangduo' in name_lower:
            x, y = random.choice(qiangduo_coords)
            _click_random_xy(recognizer, x, y)
            consecutive_challenge = 0
            last_clicked_chufa = False
            continue

        # chufa：记录挑战次数，点击后由主循环等待3秒再截图
        if 'chufa' in name_lower and not has_suoding:
            _click_random_center(recognizer, r)
            need_wait = True
            if count_challenge:
                if not last_clicked_chufa:
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
            last_clicked_chufa = True
            consecutive_challenge += 1
            if consecutive_challenge >= 15:
                log("挑战失败：连续点击15次未识别到奖励")
                recognizer.stop_reason = "anomaly"
                stop_flag = True
                break
            continue

        # dfwrk/hdrk/tiaozhan/tiaozhan2：点击图片坐标，不记录次数
        if any(x in name_lower for x in ['dfwrk', 'hdrk', 'tiaozhan']):
            _click_random_center(recognizer, r)
            consecutive_challenge = 0
            last_clicked_chufa = False
            continue

        # rkjl/jiangli/jiangli2/jiangli3/shengli：点击通用坐标
        if any(x in name_lower for x in ['rkjl', 'jiangli', 'shengli']):
            _click_random_xy(recognizer, recognizer.click_x, recognizer.click_y)
            consecutive_challenge = 0
            last_clicked_chufa = False
            continue

    return stop_flag, current_count, consecutive_challenge, last_clicked_chufa, need_wait

def handle_no_recognition():
    return False, 0, False
