# 터미널에서 플러그인 필요 시: appium --use-plugins=images
# pip install opencv-python numpy pillow

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
# 1. 설정 (고용24 맞춤 설정)
# ==========================================
ITERATIONS = 10
BUNDLE_ID = "kr.or.keis.mo"       # 고용24 번들 ID
APP_ICON_NAME = "고용24"           # 홈 화면에 보이는 아이콘 이름
UDID = "----------------" # 사용자 아이폰 UDID

# ✅ 이 .py 파일이 있는 폴더 기준으로 경로 설정
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = SCRIPT_DIR

# 🎯 타겟 이미지 (고용24 로딩 완료 화면의 하단 탭바 캡처본)
TARGET_IMAGE_PATH = os.path.join(SCRIPT_DIR, "work24_test.png")

# 🔍 검사할 영역 (ROI) 설정 - 하단 탭바 영역 집중 감시
# (전체 화면을 비교하면 상단 배너가 바뀔 때 실패할 수 있어서 하단이 안전함)
ROI_X_PCT = 0      # 왼쪽 끝 (0%)
ROI_Y_PCT = 0.88   # 위에서 88% 지점 (하단 탭바 위치)
ROI_W_PCT = 1      # 너비 100%
ROI_H_PCT = 0.1   # 높이 12% (바닥까지)

# 이미지 파일 존재 확인
if not os.path.exists(TARGET_IMAGE_PATH):
    print(f"❌ [오류] 타겟 이미지 파일이 없습니다: {TARGET_IMAGE_PATH}")
    print("   👉 고용24 로딩 완료 화면의 하단 부분을 캡처해서 'work24_test.png'로 저장해주세요.")
    exit()

# 타겟 이미지 미리 로드 (흑백 변환 안 함, 컬러 매칭)
target_img_cv = cv2.imread(TARGET_IMAGE_PATH)

options = XCUITestOptions()
options.platform_name = "iOS"
options.automation_name = "XCUITest"
options.udid = UDID
# 앱을 Appium이 켜지 않고, 우리가 직접 터치로 켤 것이므로 autoLaunch False
options.set_capability("autoLaunch", False)
options.set_capability("waitForQuiescence", False)

# ==========================================
# 2. 이미지 매칭 함수 (OpenCV)
# ==========================================
def check_loading_complete(driver):
    try:
        # 1. 현재 화면 캡처 (메모리로 바로 로드)
        screenshot_base64 = driver.get_screenshot_as_base64()
        image = Image.open(io.BytesIO(base64.b64decode(screenshot_base64)))

        # 2. ROI(검사 영역) 잘라내기
        img_w, img_h = image.size
        left = int(img_w * ROI_X_PCT)
        top = int(img_h * ROI_Y_PCT)
        right = int(left + (img_w * ROI_W_PCT))
        bottom = int(top + (img_h * ROI_H_PCT))

        roi_image = image.crop((left, top, right, bottom))
        
        # 3. OpenCV 포맷으로 변환 (RGB -> BGR)
        roi_cv = cv2.cvtColor(np.array(roi_image), cv2.COLOR_RGB2BGR)

        # 4. 크기가 다르면 리사이즈 (해상도 차이 보정)
        if target_img_cv.shape != roi_cv.shape:
            roi_cv = cv2.resize(roi_cv, (target_img_cv.shape[1], target_img_cv.shape[0]))

        # 5. 템플릿 매칭 수행
        res = cv2.matchTemplate(roi_cv, target_img_cv, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        
        return max_val # 일치율 (0.0 ~ 1.0)
    except Exception as e:
        # 캡처 실패 등 에러 발생 시 아직 로딩 중으로 간주
        return 0.0

# ==========================================
# 3. 테스트 루프
# ==========================================
driver = None
test_results = []

try:
    print(f"🚀 [고용24 실행 속도 테스트] 이미지 매칭 방식 ({ITERATIONS}회)")
    print(f"   🎯 타겟 이미지: {TARGET_IMAGE_PATH}")
    
    driver = webdriver.Remote("http://127.0.0.1:4723", options=options)

    for i in range(1, ITERATIONS + 1):
        print(f"\n--- [Iter {i}/{ITERATIONS}] ---")
        measured_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            # 1. 앱 종료 (초기화)
            try:
                driver.terminate_app(BUNDLE_ID)
            except:
                pass
            time.sleep(1.5)

            # 2. 홈 화면으로 이동
            driver.execute_script("mobile: pressButton", {"name": "home"})
            time.sleep(1)

            # 3. 아이콘 찾기 (못 찾으면 스크롤 필요할 수 있음)
            try:
                icon = driver.find_element(AppiumBy.ACCESSIBILITY_ID, APP_ICON_NAME)
            except:
                print(f"❌ '{APP_ICON_NAME}' 아이콘을 홈 화면에서 찾을 수 없습니다.")
                break

            # 4. 앱 실행 (터치 & 타이머 시작)
            icon.click()
            start_time = time.time()

            # 5. 로딩 검사 (최대 20초 대기)
            is_loaded = False
            while (time.time() - start_time) < 20:
                score = check_loading_complete(driver)

                # 일치율 80% 이상이면 로딩 완료로 판단
                if score > 0.8:
                    end_time = time.time()
                    duration = end_time - start_time
                    print(f"⚡ 로딩 완료: {duration:.4f}초 (일치율: {score*100:.1f}%)")
                    test_results.append([i, "성공", measured_at, duration])
                    is_loaded = True
                    break
                
                # 너무 자주 찍으면 부하 걸리므로 0.05초 대기
                time.sleep(0.01)

            if not is_loaded:
                print("❌ 실패: 시간 초과 (이미지 매칭 실패)")
                test_results.append([i, "실패", measured_at, 0])

        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            test_results.append([i, "실패", measured_at, 0])

finally:
    if driver:
        driver.quit()

# ==========================================
# 4. 결과 저장 (CSV)
# ==========================================
durations = [row[3] for row in test_results if row[1] == "성공" and row[3] > 0]

if durations:
    avg_val = statistics.mean(durations)
    max_val = max(durations)
    min_val = min(durations)
    std_val = statistics.pstdev(durations) if len(durations) > 1 else 0.0
else:
    avg_val = max_val = min_val = std_val = 0.0

output_path = os.path.join(SAVE_DIR, "ios_work24_launch_result.csv")
print(f"\n📁 CSV 저장 경로: {output_path}")

with open(output_path, mode='w', newline='', encoding='utf-8-sig') as file:
    writer = csv.writer(file)
    # 헤더
    writer.writerow([
        "회차", "상태", "측정시간", "앱실행반응속도(초)",
        "평균(초)", "최소(초)", "최대(초)", "표준편차(초)"
    ])

    # 데이터
    for iteration, status, measured_at, duration in test_results:
        writer.writerow([
            iteration,
            status,
            measured_at,
            f"{duration:.4f}" if duration > 0 else "",
            "", "", "", ""
        ])

    # 통계 요약
    writer.writerow([
        "통계", "", "", "",
        f"{avg_val:.4f}" if durations else "",
        f"{min_val:.4f}" if durations else "",
        f"{max_val:.4f}" if durations else "",
        f"{std_val:.4f}" if durations else ""
    ])

print("✅ 저장 완료")
