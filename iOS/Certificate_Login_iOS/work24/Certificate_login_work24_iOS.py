import time
import csv
import warnings
import statistics
import os
import base64
import io
import cv2
import numpy as np
from PIL import Image
from datetime import datetime
from urllib3.exceptions import NotOpenSSLWarning
from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

warnings.simplefilter('ignore', NotOpenSSLWarning)

# ---------------------------------------------------------
# [설정] 
# ---------------------------------------------------------
CERTI_PASSWORD = "170520"  # 금융인증서 비밀번호
REPEAT_COUNT = 10 

options = XCUITestOptions()
options.platform_name = "iOS"
options.automation_name = "XCUITest"
options.udid = "00008120-001E34DC3EB8201E" 
options.bundle_id = "kr.or.keis.mo" 

options.set_capability("connectHardwareKeyboard", False)
options.set_capability("noReset", True)
options.set_capability("wdaLaunchTimeout", 60000)
options.set_capability("wdaConnectionTimeout", 60000)

# ⚡ 이미지 처리 속도 최적화
options.set_capability("waitForQuiescence", False)
options.set_capability("waitForIdleTimeout", 0)
options.set_capability("mjpegServerScreenshotQuality", 20)

driver = webdriver.Remote('http://127.0.0.1:4723', options=options)
# 강제 설정
driver.update_settings({"waitForIdleTimeout": 0})
wait = WebDriverWait(driver, 20)

# ✅ [이미지 설정] 로그인 완료 화면 캡처 파일명
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_IMAGE_NAME = "work24_login.png" 
TARGET_IMAGE_PATH = os.path.join(SCRIPT_DIR, TARGET_IMAGE_NAME)

# ✅ [ROI 설정] 화면 상단부 집중 검사
ROI_X_PCT = 0.0      # 가로 시작
ROI_Y_PCT = 0.54    # 세로 시작
ROI_W_PCT = 1.0      # 가로 길이
ROI_H_PCT = 0.05     # 세로 높이

# 이미지 파일 확인
if not os.path.exists(TARGET_IMAGE_PATH):
    print(f"❌ 오류: '{TARGET_IMAGE_NAME}' 파일이 없습니다.")
    print("   👉 로그인 완료 화면을 캡처해서 같은 폴더에 넣어주세요.")
    exit()

template_img = cv2.imread(TARGET_IMAGE_PATH)

# ---------------------------------------------------------
# [함수] 이미지 매칭 (성공 판단)
# ---------------------------------------------------------
def wait_for_image_match(driver, start_time, timeout=20):
    while True:
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

            if template_img.shape != roi_cv.shape:
                roi_cv = cv2.resize(roi_cv, (template_img.shape[1], template_img.shape[0]))

            res = cv2.matchTemplate(roi_cv, template_img, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)

            if max_val > 0.8:
                return True

            if time.time() - start_time > timeout:
                return False
            
            time.sleep(0.01)

        except Exception:
            pass

# ---------------------------------------------------------
# [함수] 금융인증서 핀번호 입력 (기존 로직 유지)
# ---------------------------------------------------------
def type_certi_password_with_timer(driver, password):
    print(f"   🔐 핀번호 입력 시작 ({len(password)}자리)")
    
    first_part = password[:-1]
    last_digit = password[-1]
    
    for char in first_part:
        try:
            driver.find_element(AppiumBy.ACCESSIBILITY_ID, char).click()
            time.sleep(0.01) 
        except:
            raise Exception(f"숫자 '{char}'를 찾을 수 없습니다.")
            
    print("   ⏱️ 5자리 입력 완료. 마지막 한 자리 입력 직전 시간 측정 시작!")
    
    try:
        last_btn = driver.find_element(AppiumBy.ACCESSIBILITY_ID, last_digit)
    except:
        raise Exception(f"마지막 숫자 '{last_digit}'를 찾을 수 없습니다.")
    
    # 클릭 -> 시간 측정 (순서 수정됨: 클릭이 먼저)
    last_btn.click()
    start_time = time.time()
        
    return start_time

# ---------------------------------------------------------
# [메인 테스트 루프]
# ---------------------------------------------------------
test_results = []

try:
    print("🚀 금융인증서 로그인 테스트 (이미지 매칭 Ver)")
    time.sleep(5)

    for i in range(1, REPEAT_COUNT + 1):
        print(f"\n[{i}/{REPEAT_COUNT} 회차] 진행 중...")
        
        try:
            # 1. 메인 -> 로그인
            print("   📲 [1단계] 로그인 진입")
            wait.until(EC.element_to_be_clickable((
                AppiumBy.IOS_CLASS_CHAIN, 
                '**/XCUIElementTypeLink/XCUIElementTypeStaticText[`name == "로그인"`]'
            ))).click()

            time.sleep(5)

            # 2. 금융인증서 메뉴
            print("   📲 [2단계] 금융인증서 선택")
            wait.until(EC.element_to_be_clickable((
                AppiumBy.ACCESSIBILITY_ID, "금융인증서"
            ))).click()

            # 3. 인증서 선택
            print("   👤 [3단계] 사용자 인증서 선택")
            wait.until(EC.element_to_be_clickable((
                AppiumBy.IOS_CLASS_CHAIN, 
                '**/XCUIElementTypeButton[`name CONTAINS "금융인증서를 선택합니다"`]'
            ))).click()

            # 4. 핀번호 입력 및 타이머 시작
            print("   ⌨️ [4단계] 핀번호 화면 대기")
            wait.until(EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "1")))
            
            # 입력 및 시간 측정 시작
            start_time = type_certi_password_with_timer(driver, CERTI_PASSWORD)
            start_time_str = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')

            # 5. [수정됨] 이미지 매칭으로 완료 확인
            print("   👀 [5단계] 로그인 완료 대기 (이미지 매칭)")
            if wait_for_image_match(driver, start_time):
                end_time = time.time()
                duration = end_time - start_time
                print(f"   🎉 로그인 성공! 소요 시간: {duration:.4f}초")
                test_results.append([i, "Success", start_time_str, duration])
                
                # 측정 완료 후 팝업(Cancel/Ok) 처리
                try: driver.find_element(AppiumBy.ACCESSIBILITY_ID, "Cancel").click()
                except: pass
                
                try:
                    time.sleep(1)
                    driver.find_element(AppiumBy.ACCESSIBILITY_ID, "Ok").click()
                except: pass
            else:
                print("   ❌ 실패: 타임아웃 (이미지 매칭 실패)")
                test_results.append([i, "Fail", start_time_str, 0])

            print("   ⏳ 메인화면 복귀 대기 (4초)")
            time.sleep(4) 

            # 6. 로그아웃 (기존 로직 유지)
            print("   🚪 [6단계] 로그아웃")
            menu_opened = False
            for attempt in range(3):
                try:
                    print(f"      👉 전체메뉴 클릭 시도 ({attempt+1}/3)")
                    driver.find_element(AppiumBy.ACCESSIBILITY_ID, "전체메뉴").click()
                    time.sleep(2)
                    logout_btn = driver.find_element(AppiumBy.ACCESSIBILITY_ID, "로그아웃")
                    print("      ✅ 메뉴 열림 확인됨")
                    logout_btn.click()
                    menu_opened = True
                    break
                except:
                    print("      ⚠️ 재시도...")
                    time.sleep(1)
            
            if not menu_opened:
                raise Exception("로그아웃 실패")

            try:
                time.sleep(1)
                driver.find_element(AppiumBy.ACCESSIBILITY_ID, "확인").click()
            except: pass

            print("   ✅ 초기화면 복귀 완료")
            time.sleep(3)
            
        except Exception as e:
            print(f"   ❌ {i}회차 실패: {str(e)}")
            test_results.append([i, "Fail", "", 0])
            driver.terminate_app(driver.capabilities['bundleId'])
            time.sleep(2)
            driver.activate_app(driver.capabilities['bundleId'])
            time.sleep(8)

finally:
    # -------------------------------
    # 통계 및 저장
    # -------------------------------
    durations = [row[3] for row in test_results if row[1] == "Success" and row[3] > 0]
    
    avg = min_v = max_v = std = 0.0
    if durations:
        avg = sum(durations) / len(durations)
        min_v = min(durations)
        max_v = max(durations)
        std = statistics.stdev(durations) if len(durations) > 1 else 0.0

    output_filename = os.path.join(SCRIPT_DIR, 'ios_login_certificate_image_result.csv')
    with open(output_filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['회차', '상태', '측정시간', '로그인반응속도(초)', '평균(초)', '최소(초)', '최대(초)', '표준편차(초)'])
        for row in test_results:
            writer.writerow(row + ["", "", "", ""])
        writer.writerow(["Summary", "Stats", "", "", f"{avg:.4f}", f"{min_v:.4f}", f"{max_v:.4f}", f"{std:.4f}"])
    
    print(f"\n테스트 종료 및 저장 완료: {output_filename}")
    if driver:
        driver.quit()