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
from appium import webdriver
from datetime import datetime
from appium.options.ios import XCUITestOptions
from appium.webdriver.common.appiumby import AppiumBy

# ==========================================
# 1. 설정
# ==========================================
ITERATIONS = 10
BUNDLE_ID = "kr.go.dcsc.minwon24"  # 정부24 번들 ID
APP_ICON_NAME = "정부24"            # 홈 화면 앱 이름
UDID = "00008120-001E34DC3EB8201E" # 테스트 디바이스 UDID

# ✅ 이 .py 파일이 있는 폴더 기준으로 경로 설정
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ✅ 결과 저장 폴더 = 현재 .py 파일과 같은 폴더
SAVE_DIR = SCRIPT_DIR

# 타겟 이미지 경로 (.py 파일과 같은 위치)
TARGET_IMAGE_PATH = os.path.join(SCRIPT_DIR, "gov24_test.png")

# Step 1에서 사용한 ROI 좌표
ROI_X_PCT = 0      # 가로
ROI_Y_PCT = 0.88   # 세로
ROI_W_PCT = 1      # 너비
ROI_H_PCT = 0.1    # 높이

if not os.path.exists(TARGET_IMAGE_PATH):
    print(f"❌ 타겟 이미지 파일이 없습니다: {TARGET_IMAGE_PATH}")
    exit()

target_img_cv = cv2.imread(TARGET_IMAGE_PATH)

options = XCUITestOptions()
options.platform_name = "iOS"
options.automation_name = "XCUITest"
options.udid = UDID
options.set_capability("autoLaunch", False)
options.set_capability("waitForQuiescence", False)

# ==========================================
# 2. 이미지 매칭 함수
# ==========================================
def check_loading_complete(driver):
    try:
        screenshot_base64 = driver.get_screenshot_as_base64()
        image = Image.open(io.BytesIO(base64.b64decode(screenshot_base64)))

        img_w, img_h = image.size
        left = int(img_w * ROI_X_PCT)
        top = int(img_h * ROI_Y_PCT)
        right = int(left + (img_w * ROI_W_PCT))
        bottom = int(top + (img_h * ROI_H_PCT))

        roi_image = image.crop((left, top, right, bottom))
        roi_cv = cv2.cvtColor(np.array(roi_image), cv2.COLOR_RGB2BGR)

        if target_img_cv.shape != roi_cv.shape:
            roi_cv = cv2.resize(roi_cv, (target_img_cv.shape[1], target_img_cv.shape[0]))

        res = cv2.matchTemplate(roi_cv, target_img_cv, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        return max_val
    except:
        return 0.0

# ==========================================
# 3. 테스트 루프
# ==========================================
driver = None
test_results = []

try:
    print(f"🚀 [정부24 실행 속도 테스트] 터치 실행 방식 ({ITERATIONS}회)")
    driver = webdriver.Remote("http://127.0.0.1:4723", options=options)

    for i in range(1, ITERATIONS + 1):
        print(f"\n--- [Iter {i}/{ITERATIONS}] ---")
        measured_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            try:
                driver.terminate_app(BUNDLE_ID)
            except:
                pass
            time.sleep(1)

            driver.execute_script("mobile: pressButton", {"name": "home"})
            time.sleep(1)

            try:
                icon = driver.find_element(AppiumBy.ACCESSIBILITY_ID, APP_ICON_NAME)
            except:
                print(f"❌ '{APP_ICON_NAME}' 아이콘을 못 찾았습니다. 홈 화면 1페이지에 두세요.")
                break

            icon.click()
            start_time = time.time()

            is_loaded = False
            while (time.time() - start_time) < 20:
                score = check_loading_complete(driver)

                if score > 0.8:
                    end_time = time.time()
                    duration = end_time - start_time
                    print(f"⚡ 로딩 완료: {duration:.4f}초 (일치율: {score*100:.1f}%)")
                    test_results.append([i, "성공", measured_at, duration])
                    is_loaded = True
                    break
                time.sleep(0.01)

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
# 4. 저장 (✅ .py 파일과 같은 폴더에 저장)
# ==========================================
durations = [row[3] for row in test_results if row[1] == "성공" and row[3] > 0]

if durations:
    avg_val = statistics.mean(durations)
    max_val = max(durations)
    min_val = min(durations)
    std_val = statistics.pstdev(durations) if len(durations) > 1 else 0.0
else:
    avg_val = max_val = min_val = std_val = 0.0

# ✅ 결과 파일을 .py 파일과 같은 위치에 저장
output_path = os.path.join(SAVE_DIR, "ios_gov24_launch_result.csv")
print(f"\n📁 CSV 저장 경로: {output_path}")

with open(output_path, mode='w', newline='', encoding='utf-8-sig') as file:
    writer = csv.writer(file)
    writer.writerow([
        "회차", "상태", "측정시간", "앱실행반응속도(초)",
        "평균(초)", "최소(초)", "최대(초)", "표준편차(초)"
    ])

    for iteration, status, measured_at, duration in test_results:
        writer.writerow([
            iteration,
            status,
            measured_at,
            f"{duration:.4f}" if duration > 0 else "",
            "", "", "", ""
        ])

    writer.writerow([
        "통계", "", "", "",
        f"{avg_val:.4f}" if durations else "",
        f"{min_val:.4f}" if durations else "",
        f"{max_val:.4f}" if durations else "",
        f"{std_val:.4f}" if durations else ""
    ])

print("✅ 저장 완료")
