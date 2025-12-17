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
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==========================================
# 1. 설정 (Configuration)
# ==========================================
ITERATIONS = 10
keyword = "청년"

options = XCUITestOptions()
options.udid = "00008120-001E34DC3EB8201E"
options.platform_name = "iOS"
options.automation_name = "XCUITest"
options.bundle_id = "kr.or.keis.mo"
options.no_reset = True

# ⚡ [속도 최적화]
options.set_capability("waitForQuiescence", False)
options.set_capability("waitForIdleTimeout", 0)
options.set_capability("simpleIsVisibleCheck", True)
options.set_capability("mjpegServerScreenshotQuality", 20) # 스크린샷 전송 속도 향상 (화질 낮춤)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 🎯 타겟 이미지 파일명 (같은 폴더에 있어야 함)
TARGET_IMAGE_NAME = "work24_test.png"
TARGET_IMAGE_PATH = os.path.join(SCRIPT_DIR, TARGET_IMAGE_NAME)

# 🔍 검사할 영역 (ROI): 화면 상단 15% ~ 35% (검색창 바로 아래 결과 나오는 부분)
ROI_X_PCT = 0      # 가로
ROI_Y_PCT = 0.44   # 세로
ROI_W_PCT = 1      # 너비
ROI_H_PCT = 0.05    # 높이

# 이미지 로드 확인
if not os.path.exists(TARGET_IMAGE_PATH):
    print(f"❌ 오류: '{TARGET_IMAGE_NAME}' 파일이 없습니다.")
    print("   👉 검색 결과 화면의 특징적인 부분(예: 상단 탭, 총 건수 등)을 캡처해서 넣어주세요.")
    exit()

# 템플릿 이미지 로드 (컬러)
template_img = cv2.imread(TARGET_IMAGE_PATH)


# ---------------------------------------------------------
# [함수] 이미지 매칭 로직
# ---------------------------------------------------------
def wait_for_image_match(driver, start_time, timeout=20):
    while True:
        try:
            # 1. 스크린샷 (메모리 로드)
            screenshot_base64 = driver.get_screenshot_as_base64()
            image = Image.open(io.BytesIO(base64.b64decode(screenshot_base64)))

            # 2. ROI 잘라내기 (속도 향상 및 오탐지 방지)
            img_w, img_h = image.size
            left = int(img_w * ROI_X_PCT)
            top = int(img_h * ROI_Y_PCT)
            right = int(left + (img_w * ROI_W_PCT))
            bottom = int(top + (img_h * ROI_H_PCT))
            
            roi_image = image.crop((left, top, right, bottom))
            roi_cv = cv2.cvtColor(np.array(roi_image), cv2.COLOR_RGB2BGR)

            # 3. 크기 보정 (템플릿과 스크린샷 해상도가 다를 경우 대비)
            if template_img.shape != roi_cv.shape:
                roi_cv = cv2.resize(roi_cv, (template_img.shape[1], template_img.shape[0]))

            # 4. 매칭 수행
            res = cv2.matchTemplate(roi_cv, template_img, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)

            # 일치율 80% 이상이면 성공
            if max_val > 0.8:
                return True

            # 타임아웃 체크
            if time.time() - start_time > timeout:
                return False
            
            # 0.05초 대기 (CPU 과부하 방지)
            time.sleep(0.02)

        except Exception as e:
            print(f"   ⚠️ 이미지 분석 중 에러: {e}")
            pass

# ==========================================
# 2. 테스트 실행
# ==========================================
driver = None
test_results = []

try:
    print(f"🚀 [고용24] 성능 테스트 (이미지 매칭 Ver) 시작")
    print(f"   🎯 타겟 이미지: {TARGET_IMAGE_NAME}")
    
    driver = webdriver.Remote("http://127.0.0.1:4723", options=options)
    driver.update_settings({"waitForIdleTimeout": 0})
    wait = WebDriverWait(driver, 20)

    for i in range(1, ITERATIONS + 1):
        print(f"\n--- [Iter {i}/{ITERATIONS}] ---")
        measured_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            # [Step 1] 검색어 입력
            search_input = wait.until(EC.element_to_be_clickable((AppiumBy.ACCESSIBILITY_ID, "통합검색 검색어 입력")))
            search_input.click()
            search_input.send_keys(keyword)
            
            # [Step 2] 검색 버튼 찾기
            search_btn_locator = (AppiumBy.ACCESSIBILITY_ID, "검색")
            search_button = driver.find_element(*search_btn_locator)

            # -----------------------------------------------------------
            # ✅ [Time Start] 클릭 -> 측정 시작
            # -----------------------------------------------------------
            search_button.click()
            start_time = time.time()

            # [Step 3] 이미지 매칭으로 로딩 완료 확인
            if wait_for_image_match(driver, start_time):
                end_time = time.time()
                duration = end_time - start_time
                print(f"✅ {i}회차 소요 시간: {duration:.4f}초")
                test_results.append([i, "성공", measured_at, duration])
            else:
                print(f"❌ {i}회차 실패: 타임아웃 (이미지 매칭 실패)")
                test_results.append([i, "실패", measured_at, 0])
                # 실패 시 스크린샷 저장해보기 (디버깅용)
                driver.save_screenshot(os.path.join(SCRIPT_DIR, f"fail_{i}.png"))

            # [Step 4] 복귀 로직 (기존 유지)
            if driver.is_keyboard_shown():
                try:
                    driver.hide_keyboard()
                except:
                    driver.tap([(100, 100)])
                time.sleep(1)

            home_xpath = '//XCUIElementTypeStaticText[@name="홈"]'
            wait.until(EC.element_to_be_clickable((AppiumBy.XPATH, home_xpath))).click()
            
            wait.until(EC.element_to_be_clickable((AppiumBy.ACCESSIBILITY_ID, "통합검색 검색어 입력")))
            time.sleep(1)

        except Exception as e:
            print(f"❌ {i}회차 에러: {e}")
            test_results.append([i, "실패", measured_at, 0])
            try:
                # 홈 버튼 강제 클릭 시도
                driver.find_element(AppiumBy.XPATH, '//XCUIElementTypeStaticText[@name="홈"]').click()
                time.sleep(2)
            except:
                pass

except Exception as e:
    print(f"❌ 전체 오류: {e}")

finally:
    if driver:
        driver.quit()

# ==========================================
# 3. 결과 저장
# ==========================================
durations = [row[3] for row in test_results if row[1] == "성공" and row[3] > 0]

if durations:
    avg_val = statistics.mean(durations)
    max_val = max(durations)
    min_val = min(durations)
    stdev_val = statistics.pstdev(durations) if len(durations) > 1 else 0.0
else:
    avg_val = min_val = max_val = stdev_val = 0.0

output_path = os.path.join(SCRIPT_DIR, "ios_work24_search_image_result.csv")

with open(output_path, mode='w', newline='', encoding='utf-8-sig') as file:
    writer = csv.writer(file)
    writer.writerow(["회차", "상태", "측정시간", "검색반응속도(초)", "평균(초)", "최소(초)", "최대(초)", "표준편차(초)"])
    for r in test_results:
        writer.writerow([r[0], r[1], r[2], f"{r[3]:.4f}" if r[3] > 0 else "", "", "", "", ""])
    writer.writerow(["통계", "", "", "", f"{avg_val:.4f}", f"{min_val:.4f}", f"{max_val:.4f}", f"{stdev_val:.4f}"])

print(f"\n💾 저장 완료: {output_path}")