import time
import csv
import os
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

# ===================== [설정 영역] =====================
UDID = "00008120-001E34DC3EB8201E"
BUNDLE_ID = "kr.co.jobkorea.jobkorea1"
DEVICE_NAME = "iPhone"
APPIUM_SERVER_URL = "http://127.0.0.1:4723"

REPEAT_COUNT = 10
KEYWORD = "청년"

# ✅ 경로 설정 (.py 파일과 같은 위치)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = SCRIPT_DIR

# 🎯 타겟 이미지 (검색 결과 화면의 상단 필터/카운트 영역)
TARGET_IMAGE_PATH = os.path.join(SCRIPT_DIR, "jobkorea_test.png")

# 🔍 검사할 영역 (ROI) 설정 
# 잡코리아 검색 결과는 상단(헤더 바로 아래)에 필터/개수 정보가 뜨므로 상단부 집중 검사
ROI_X_PCT = 0      # 가로
ROI_Y_PCT = 0.15   # 세로
ROI_W_PCT = 1      # 너비
ROI_H_PCT = 0.10    # 높이

# =======================================================

# 이미지 파일 확인
if not os.path.exists(TARGET_IMAGE_PATH):
    print(f"❌ [오류] 타겟 이미지 파일이 없습니다: {TARGET_IMAGE_PATH}")
    print("   👉 검색 결과 화면 상단을 캡처해서 'jobkorea_search_done.png'로 저장해주세요.")
    exit()

# 타겟 이미지 미리 로드
target_img_cv = cv2.imread(TARGET_IMAGE_PATH)

options = XCUITestOptions()
options.platform_name = "iOS"
options.automation_name = "XCUITest"
options.udid = UDID
options.bundle_id = BUNDLE_ID
options.device_name = DEVICE_NAME
options.no_reset = True
options.new_command_timeout = 300
options.auto_accept_alerts = True
options.set_capability("waitForQuiescence", False) # UI 안정화 대기 끄기 (속도 향상)

# ---------------------------------------------------------
# [함수] 이미지 매칭 (로딩 완료 판단)
# ---------------------------------------------------------
def check_search_complete(driver):
    try:
        # 1. 스크린샷 캡처 (메모리)
        screenshot_base64 = driver.get_screenshot_as_base64()
        image = Image.open(io.BytesIO(base64.b64decode(screenshot_base64)))

        # 2. ROI 잘라내기
        img_w, img_h = image.size
        left = int(img_w * ROI_X_PCT)
        top = int(img_h * ROI_Y_PCT)
        right = int(left + (img_w * ROI_W_PCT))
        bottom = int(top + (img_h * ROI_H_PCT))

        roi_image = image.crop((left, top, right, bottom))
        roi_cv = cv2.cvtColor(np.array(roi_image), cv2.COLOR_RGB2BGR)

        # 3. 크기 보정
        if target_img_cv.shape != roi_cv.shape:
            roi_cv = cv2.resize(roi_cv, (target_img_cv.shape[1], target_img_cv.shape[0]))

        # 4. 매칭
        res = cv2.matchTemplate(roi_cv, target_img_cv, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        
        return max_val # 일치율 리턴
    except:
        return 0.0

# ---------------------------------------------------------
# [메인 실행]
# ---------------------------------------------------------
def run_ios_jobkorea_search_image_match():
    print(f"--- [iOS] 잡코리아 검색 속도 (이미지 매칭) {REPEAT_COUNT}회 시작 ---")
    
    driver = None
    test_results = []

    try:
        driver = webdriver.Remote(APPIUM_SERVER_URL, options=options)
        wait = WebDriverWait(driver, 20)

        print("📱 앱 실행 및 메인 화면 진입...")
        driver.activate_app(BUNDLE_ID)
        time.sleep(3)

        # 메인 검색 버튼(돋보기) 요소 미리 찾기용 Locator
        search_btn_locator = (AppiumBy.ACCESSIBILITY_ID, "new_main_search_blue")

        for i in range(1, REPEAT_COUNT + 1):
            measured_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                print(f"\n[Iter {i}/{REPEAT_COUNT}] 측정 시작...")

                # 1. 메인 검색 버튼 클릭 (좌표 타격 권장, 실패시 요소 검색)
                # 잡코리아 메인 상단 돋보기 좌표 (iPhone 기종따라 확인 필요, 예: 340, 125)
                # 안전하게 요소 찾기로 하되, 못 찾으면 좌표
                try:
                    driver.find_element(*search_btn_locator).click()
                except:
                    print("   ⚠️ 돋보기 버튼 못 찾음 -> 좌표 클릭 시도")
                    driver.tap([(340, 125)]) 
                
                # 2. 검색어 입력창 대기 (화면 전환)
                # 입력창은 어쩔 수 없이 찾아야 함 (텍스트 입력 위해)
                search_input = wait.until(EC.visibility_of_element_located(
                    (AppiumBy.CLASS_NAME, "XCUIElementTypeTextField")
                ))
                
                search_input.clear()
                # 텍스트만 먼저 입력 (엔터는 아직)
                search_input.send_keys(KEYWORD)
                
                print(f"   ⌨️ 키워드 입력 완료. 엔터 대기 중...")
                time.sleep(0.5) # 키보드 안정화

                # 3. ★ 측정 시작 ★ (엔터 누르는 순간부터)
                
                # 엔터 입력 (검색 실행)
                search_input.send_keys("\n")
                start_time = time.time()
                
                # 4. 이미지 매칭 루프 (최대 20초)
                is_loaded = False
                while (time.time() - start_time) < 20:
                    score = check_search_complete(driver)
                    
                    # 일치율 85% 이상이면 로딩 끝
                    if score > 0.85:
                        end_time = time.time()
                        duration = end_time - start_time
                        print(f"   ⚡ 검색 완료! 소요시간: {duration:.4f}초 (일치율: {score*100:.1f}%)")
                        test_results.append([i, "성공", measured_at, duration])
                        is_loaded = True
                        break
                    
                    time.sleep(0.01) # 부하 조절

                if not is_loaded:
                    print("   ❌ 실패: 로딩 시간 초과 (이미지 매칭 실패)")
                    test_results.append([i, "실패", measured_at, 0])

                # 5. 메인 화면 복귀 (다음 회차 준비)
                print("   🔙 메인으로 복귀")
                
                # 뒤로가기 1 (검색결과 -> 검색창)
                try:
                    driver.find_element(AppiumBy.ACCESSIBILITY_ID, "advanced search back").click()
                except:
                    driver.tap([(20, 60)]) # 좌상단 좌표

                time.sleep(1)

                # 뒤로가기 2 (검색창 -> 메인)
                try:
                    driver.find_element(AppiumBy.ACCESSIBILITY_ID, "Jams/system_back").click()
                except:
                    driver.tap([(20, 60)])
                
                # 메인 돋보기 보일 때까지 대기
                try:
                    wait.until(EC.presence_of_element_located(search_btn_locator))
                except:
                    pass
                
                time.sleep(1)

            except Exception as e:
                print(f"❌ {i}회차 에러: {e}")
                test_results.append([i, "실패", measured_at, 0])
                # 앱 재기동
                driver.terminate_app(BUNDLE_ID)
                time.sleep(1)
                driver.activate_app(BUNDLE_ID)
                time.sleep(3)

        # ===================== CSV 저장 =====================
        if test_results:
            durations = [row[3] for row in test_results if row[1] == "성공" and row[3] > 0]
            if durations:
                avg_val = statistics.mean(durations)
                min_val = min(durations)
                max_val = max(durations)
                std_val = statistics.pstdev(durations) if len(durations) > 1 else 0.0
            else:
                avg_val = min_val = max_val = std_val = 0.0
            
            file_path = os.path.join(SCRIPT_DIR, "ios_jobkorea_search_image_result.csv")

            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["회차", "상태", "측정시간", "검색반응속도(초)", "평균(초)", "최소(초)", "최대(초)", "표준편차(초)"])
                for it, st, tm, dur in test_results:
                    writer.writerow([it, st, tm, f"{dur:.4f}" if dur > 0 else "", "", "", "", ""])
                writer.writerow(["통계", "", "", "", f"{avg_val:.4f}", f"{min_val:.4f}", f"{max_val:.4f}", f"{std_val:.4f}"])

            print(f"\n✅ 저장 완료: {file_path}")

    except Exception as e:
        print(f"⛔ 치명적 오류: {e}")

    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    run_ios_jobkorea_search_image_match()