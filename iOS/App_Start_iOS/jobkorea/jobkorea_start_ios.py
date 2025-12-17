# 터미널에서
# appium --use-plugins=images

import time
import os
import csv
import base64
import io
import cv2
import numpy as np
import statistics
from PIL import Image
from datetime import datetime
from appium import webdriver
from appium.options.ios import XCUITestOptions

# ==========================================
# 1. 설정 (Configuration)
# ==========================================
ITERATIONS = 10
BUNDLE_ID = "kr.co.jobkorea.jobkorea1"
UDID = "00008120-001E34DC3EB8201E"  # [UDID 입력 필수]

# ✅ 이 .py 파일이 있는 폴더 기준
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ✅ 결과 파일 및 타겟 이미지를 모두 현재 파일과 같은 위치에서 사용
SAVE_DIR = SCRIPT_DIR
TARGET_IMAGE_PATH = os.path.join(SCRIPT_DIR, "jobkorea_start.png")

# ⭐ 황금 좌표 (ROI) 설정 ⭐
ROI_X_PCT = 0.0
ROI_Y_PCT = 0.45
ROI_W_PCT = 1.0
ROI_H_PCT = 0.13

if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)
if not os.path.exists(TARGET_IMAGE_PATH):
    print(f"❌ 오류: '{TARGET_IMAGE_PATH}' 파일이 없습니다. target_jobkorea.png가 현재 .py와 같은 폴더에 있는지 확인하세요.")
    exit()

# 타겟 이미지 로드 (OpenCV)
target_img_cv = cv2.imread(TARGET_IMAGE_PATH)

options = XCUITestOptions()
options.platform_name = "iOS"
options.automation_name = "XCUITest"
options.bundle_id = BUNDLE_ID
options.udid = UDID
options.no_reset = True
options.set_capability("waitForQuiescence", False)

# ==========================================
# 2. 이미지 매칭 함수
# ==========================================
def check_loading_complete(driver):
    try:
        # 전체 스크린샷 (메모리)
        screenshot_base64 = driver.get_screenshot_as_base64()
        image = Image.open(io.BytesIO(base64.b64decode(screenshot_base64)))
        
        # ROI 좌표 계산
        img_w, img_h = image.size
        left = int(img_w * ROI_X_PCT)
        top = int(img_h * ROI_Y_PCT)
        right = int(left + (img_w * ROI_W_PCT))
        bottom = int(top + (img_h * ROI_H_PCT))
        
        # 관심 영역만 크롭
        roi_image = image.crop((left, top, right, bottom))
        roi_cv = cv2.cvtColor(np.array(roi_image), cv2.COLOR_RGB2BGR)

        # 안전장치: 크기가 다르면 리사이즈
        if target_img_cv.shape != roi_cv.shape:
            roi_cv = cv2.resize(roi_cv, (target_img_cv.shape[1], target_img_cv.shape[0]))

        # 이미지 비교 (Template Matching)
        res = cv2.matchTemplate(roi_cv, target_img_cv, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        return max_val  # 유사도 리턴
    except Exception as e:
        print(f"   ⚠️ 이미지 비교 중 오류: {e}")
        return 0.0

# ==========================================
# 3. 테스트 실행 Loop
# ==========================================
driver = None
# ✅ test_results: [회차, 상태("성공"/"실패"), 측정시간, 앱실행반응속도(초)]
test_results = []

try:
    print(f"🚀 [잡코리아 앱 실행 성능 테스트] 시작")
    driver = webdriver.Remote("http://127.0.0.1:4723", options=options)
    
    # 웜업
    driver.get_window_size()

    for i in range(1, ITERATIONS + 1):
        print(f"\n--- [Iter {i}/{ITERATIONS}] ---")
        measured_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # ⏱ 회차별 측정시간

        try:
            # 1. 앱 종료
            try:
                driver.terminate_app(BUNDLE_ID)
            except:
                pass
            time.sleep(2)

            # 2. 앱 실행 + 시간 측정
            driver.activate_app(BUNDLE_ID)
            start_time = time.time()

            is_loaded = False
            # 0.01초 간격 검사 (최대 20초)
            while (time.time() - start_time) < 20:
                score = check_loading_complete(driver)
                
                # 유사도 90% 이상이면 로딩 완료
                if score > 0.9:
                    end_time = time.time()
                    duration = end_time - start_time
                    print(f"⚡ 로딩 완료: {duration:.4f}초 (일치율: {score*100:.1f}%)")
                    test_results.append([i, "성공", measured_at, duration])
                    is_loaded = True
                    break
                
                time.sleep(0.01)  # CPU 부하 방지

            if not is_loaded:
                print("❌ 실패: 시간 초과")
                test_results.append([i, "실패", measured_at, 0])

        except Exception as e:
            print(f"❌ 오류: {e}")
            test_results.append([i, "실패", measured_at, 0])

finally:
    if driver:
        driver.quit()

# ==========================================
# 4. CSV 저장 (다른 스크립트와 동일 포맷)
# ==========================================
# 성공 케이스 기준 통계
durations = [row[3] for row in test_results if row[1] == "성공" and row[3] > 0]

if durations:
    avg_val = statistics.mean(durations)
    max_val = max(durations)
    min_val = min(durations)
    std_val = statistics.pstdev(durations) if len(durations) > 1 else 0.0
else:
    avg_val = max_val = min_val = std_val = 0.0

output_path = os.path.join(SCRIPT_DIR, "ios_jobkorea_launch_result.csv")
print(f"\n📁 CSV 저장 경로: {output_path}")

with open(output_path, mode='w', newline='', encoding='utf-8-sig') as file:
    writer = csv.writer(file)
    # ✅ 한글 헤더 + 통계 컬럼
    writer.writerow([
        "회차", "상태", "측정시간", "앱실행반응속도(초)",
        "평균(초)", "최소(초)", "최대(초)", "표준편차(초)"
    ])

    # 각 회차 기록 (통계 칸은 비워둠)
    for iteration, status, measured_at, duration in test_results:
        writer.writerow([
            iteration,
            status,
            measured_at,
            f"{duration:.4f}" if duration > 0 else "",
            "",  # 평균(초)
            "",  # 최소(초)
            "",  # 최대(초)
            ""   # 표준편차(초)
        ])

    # 마지막 통계 한 줄
    writer.writerow([
        "통계",
        "",
        "",
        "",
        f"{avg_val:.4f}" if durations else "",
        f"{min_val:.4f}" if durations else "",
        f"{max_val:.4f}" if durations else "",
        f"{std_val:.4f}" if durations else ""
    ])

print("✅ 저장 완료")
