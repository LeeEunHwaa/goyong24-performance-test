import time
import csv
import warnings
import os
import base64
import io
import cv2
import numpy as np
import statistics
from PIL import Image
from urllib3.exceptions import NotOpenSSLWarning
from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

warnings.simplefilter('ignore', NotOpenSSLWarning)

# ---------------------------------------------------------
# [설정] 계정 정보 및 이미지 설정
# ---------------------------------------------------------
LOGIN_ID = "------" 
LOGIN_PW = "------"
REPEAT_COUNT = 10

# ✅ [이미지 설정] 로그인 성공 팝업(Ok 버튼 등) 캡처 파일명
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_IMAGE_NAME = "work24_login.png" 
TARGET_IMAGE_PATH = os.path.join(SCRIPT_DIR, TARGET_IMAGE_NAME)

# ✅ [ROI 설정] 팝업이 뜨는 화면 중앙부 집중 검사 (속도 향상)
# (전체 화면을 검사하려면 X=0, Y=0, W=1, H=1 로 설정하세요)
ROI_X_PCT = 0.0      # 가로 시작
ROI_Y_PCT = 0.55    # 세로 시작
ROI_W_PCT = 1.0      # 가로 길이
ROI_H_PCT = 0.05     # 세로 높이

options = XCUITestOptions()
options.platform_name = "iOS"
options.automation_name = "XCUITest"
options.udid = "-----------------------------"
options.bundle_id = "kr.or.keis.mo"

options.set_capability("connectHardwareKeyboard", False)
options.set_capability("noReset", True)
options.set_capability("wdaLaunchTimeout", 60000)
options.set_capability("wdaConnectionTimeout", 60000)
# ⚡ 이미지 처리 속도 최적화 옵션
options.set_capability("waitForQuiescence", False)
options.set_capability("waitForIdleTimeout", 0)
options.set_capability("mjpegServerScreenshotQuality", 20)

driver = webdriver.Remote('http://127.0.0.1:4723', options=options)
# 강제 설정
driver.update_settings({"waitForIdleTimeout": 0}) 
wait = WebDriverWait(driver, 20)

# 이미지 파일 확인
if not os.path.exists(TARGET_IMAGE_PATH):
    print(f"❌ 오류: '{TARGET_IMAGE_NAME}' 파일이 없습니다.")
    print("   👉 로그인 성공 팝업을 캡처해서 같은 폴더에 넣어주세요.")
    exit()

# 템플릿 이미지 로드
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

            if max_val > 0.8:  # 일치율 80% 이상 시 성공
                return True

            if time.time() - start_time > timeout:
                return False
            
            time.sleep(0.01) # CPU 과부하 방지

        except Exception:
            pass

# ---------------------------------------------------------
# [매핑] 보안 키패드 특수문자
# ---------------------------------------------------------
SPECIAL_CHAR_MAP = {
    '!': '느낌표', '@': '골뱅이', '#': '우물정', '$': '달러기호', '%': '퍼센트',
    '^': '꺽쇠', '&': '엠퍼샌드', '*': '별표', '(': '왼쪽괄호', ')': '오른쪽괄호',
    '-': '빼기', '_': '밑줄', '=': '등호', '+': '더하기',
    '[': '왼쪽대괄호', '{': '왼쪽중괄호', ']': '오른쪽대괄호', '}': '오른쪽중괄호',
    '\\': '역슬래시', '|': '수직막대', ';': '세미콜론', ':': '콜론',
    '/': '슬래시', '?': '물음표', ',': '쉼표', '.': '마침표',
    '<': '왼쪽꺽쇠괄호', '>': '오른쪽꺽쇠괄호',
    "'": '작은따옴표', '"': '따옴표', '~': '물결표시', '`': '어금기호'
}

# ---------------------------------------------------------
# [함수] 보안 키패드 입력 (기존 유지)
# ---------------------------------------------------------
def type_secure_password(driver, password):
    print(f"   🔐 보안 키패드 입력 시작: {len(password)}자리")
    TOGGLE_IDS = ["특수키"]
    current_mode = "normal"

    for char in password:
        target_id = char
        is_special = False
        if char in SPECIAL_CHAR_MAP:
            target_id = SPECIAL_CHAR_MAP[char]
            is_special = True
        
        if is_special and current_mode == "normal":
            for t_id in TOGGLE_IDS:
                try:
                    driver.find_element(AppiumBy.ACCESSIBILITY_ID, t_id).click()
                    break
                except: continue
            time.sleep(1.0)
            current_mode = "special"
        elif not is_special and current_mode == "special":
            for t_id in TOGGLE_IDS:
                try:
                    driver.find_element(AppiumBy.ACCESSIBILITY_ID, t_id).click()
                    break
                except: continue
            time.sleep(0.5)
            current_mode = "normal"

        try:
            driver.find_element(AppiumBy.ACCESSIBILITY_ID, target_id).click()
            time.sleep(0.2)
        except Exception:
            pass
    print("   ✅ 비밀번호 입력 완료")

# ---------------------------------------------------------
# [메인 루프]
# ---------------------------------------------------------
test_results = []

try:
    print("🚀 테스트 시작 (이미지 매칭 Ver)")
    time.sleep(8)

    for i in range(1, REPEAT_COUNT + 1):
        print(f"\n[{i}/{REPEAT_COUNT} 회차] 진행 중...")
        measured_at = time.strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            # 1. 로그인 진입
            print("   📲 [1단계] 로그인 탭 클릭")
            login_tab_text = wait.until(EC.element_to_be_clickable((
                AppiumBy.IOS_CLASS_CHAIN, 
                '**/XCUIElementTypeLink/XCUIElementTypeStaticText[`name == "로그인"`]'
            )))
            login_tab_text.click()
            time.sleep(1)

            # 2. HRD 버튼
            driver.execute_script("mobile: swipe", {"direction": "up"})
            time.sleep(1)
            print("   📲 [2단계] HRD 버튼 클릭")
            hrd_btn = wait.until(EC.element_to_be_clickable((
                AppiumBy.ACCESSIBILITY_ID, "아이디/비밀번호(HRD 출결용)"
            )))
            hrd_btn.click()

            # 3. 비밀번호 입력
            print("   ⌨️ [3단계] 비밀번호 입력")
            pw_input = wait.until(EC.presence_of_element_located((
                AppiumBy.IOS_CLASS_CHAIN, '**/XCUIElementTypeSecureTextField[`value == "개인회원 비밀번호를 입력해주세요."`]'
            )))
            pw_input.click()
            time.sleep(2)
            type_secure_password(driver, LOGIN_PW)
            
            try: driver.find_element(AppiumBy.ACCESSIBILITY_ID, "입력완료").click()
            except: pass

            # 4. 로그인 버튼 클릭
            print("   ⏱️ [4단계] 로그인 요청 (측정 시작)")
            login_submit_btn = wait.until(EC.element_to_be_clickable((
                AppiumBy.IOS_CLASS_CHAIN, '**/XCUIElementTypeButton[`name == "로그인"`]'
            )))
            
            # ★ 클릭 -> 시간 측정 (순서 유지)
            login_submit_btn.click()
            start_time = time.time()

            # 5. [수정됨] 이미지 매칭으로 성공 판단
            print("   👀 [5단계] 로그인 성공 확인 (이미지 매칭)")
            if wait_for_image_match(driver, start_time):
                end_time = time.time()
                duration = end_time - start_time
                print(f"   🎉 로그인 성공! 소요 시간: {duration:.4f}초")
                test_results.append([i, "성공", measured_at, duration])
                
                # 측정 끝났으니 로그아웃을 위해 팝업 닫기 (Ok 버튼 클릭)
                try:
                    driver.find_element(AppiumBy.ACCESSIBILITY_ID, "Ok").click()
                except:
                    pass
            else:
                print("   ❌ 실패: 타임아웃 (이미지 매칭 실패)")
                test_results.append([i, "실패", measured_at, 0])

            time.sleep(4)

            # 6. 로그아웃 (기존 유지)
            print("   🚪 [6단계] 로그아웃")
            menu_btn = wait.until(EC.element_to_be_clickable((
                AppiumBy.ACCESSIBILITY_ID, "전체메뉴"
            )))
            menu_btn.click()
            time.sleep(2)

            logout_btn = wait.until(EC.element_to_be_clickable((
                AppiumBy.ACCESSIBILITY_ID, "로그아웃"
            )))
            logout_btn.click()

            try:
                time.sleep(1)
                driver.find_element(AppiumBy.ACCESSIBILITY_ID, "확인").click()
            except: pass

            print("   ✅ 초기 화면 복귀...")
            time.sleep(3)
            
        except Exception as e:
            print(f"   ❌ {i}회차 실패: {str(e)}")
            test_results.append([i, "실패", measured_at, 0])
            driver.terminate_app(driver.capabilities['bundleId'])
            time.sleep(2)
            driver.activate_app(driver.capabilities['bundleId'])
            time.sleep(5)

finally:
    # -----------------------------------------------------
    # 결과 저장 (기존 포맷 유지)
    # -----------------------------------------------------
    durations = [row[3] for row in test_results if row[1] == "성공" and row[3] > 0]

    if durations:
        avg_val = statistics.mean(durations)
        min_val = min(durations)
        max_val = max(durations)
        std_val = statistics.pstdev(durations) if len(durations) > 1 else 0.0
    else:
        avg_val = min_val = max_val = std_val = 0.0

    output_path = os.path.join(SCRIPT_DIR, 'work24_idpw_image_result.csv')
    print(f"📁 CSV 저장 경로: {output_path}")

    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['회차', '상태', '측정시간', '로그인반응속도(초)', '평균(초)', '최소(초)', '최대(초)', '표준편차(초)'])
        for iteration, status, measured_at, duration in test_results:
            writer.writerow([
                iteration, status, measured_at,
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

    if driver:
        driver.quit()
