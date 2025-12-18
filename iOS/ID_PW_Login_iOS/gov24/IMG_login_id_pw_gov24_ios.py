import time
import csv
import base64
import io
import cv2
import numpy as np
import warnings
import os
import statistics  # ✅ 통계 계산용 추가
from PIL import Image
from urllib3.exceptions import NotOpenSSLWarning
from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

warnings.simplefilter('ignore', NotOpenSSLWarning)

# ---------------------------------------------------------
# [설정] 정부24 계정 정보
# ---------------------------------------------------------
# 정부24 아이디 비밀번호 입력
GOV_ID = "-------" 
GOV_PW = "-------"
REPEAT_COUNT = 10

# ✅ 캡쳐 스크립트에서 저장한 이미지 위치 (현재 .py 파일이 있는 폴더 기준)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_IMAGE_PATH = os.path.join(SCRIPT_DIR, "gov24_test.png")  # 참조 이미지

MATCH_THRESHOLD = 0.90 

# [ROI 좌표 설정] (화면 하단 10% 영역)
ROI_CONFIG = {'x': 0, 'y': 0.88, 'w': 1, 'h': 0.1}

options = XCUITestOptions()
options.platform_name = "iOS"
options.automation_name = "XCUITest"
UDID = "------------------------"  # [UDID 입력 필수]
options.bundle_id = "kr.go.dcsc.minwon24" 
options.udid = UDID

options.set_capability("noReset", True)
options.set_capability("wdaLaunchTimeout", 60000)
options.set_capability("wdaConnectionTimeout", 60000)
options.set_capability("waitForQuiescence", False) 

driver = webdriver.Remote('http://127.0.0.1:4723', options=options)
wait = WebDriverWait(driver, 20)

# ---------------------------------------------------------
# [함수] 이미지 비교 (ROI 영역 크롭 -> 매칭)
# ---------------------------------------------------------
def check_login_success_by_roi(driver, ref_image_path, roi):
    try:
        # 디버그용: 참조 이미지 존재 여부 체크
        if not os.path.exists(ref_image_path):
            print(f"   ⚠️ 참조 이미지 없음: {ref_image_path}")
            return False

        screenshot_base64 = driver.get_screenshot_as_base64()
        image = Image.open(io.BytesIO(base64.b64decode(screenshot_base64)))
        img_w, img_h = image.size
        
        left = int(img_w * roi['x'])
        top = int(img_h * roi['y'])
        width = int(img_w * roi['w'])
        height = int(img_h * roi['h'])
        
        current_crop = image.crop((left, top, left + width, top + height))
        current_cv = cv2.cvtColor(np.array(current_crop), cv2.COLOR_RGB2BGR)
        
        ref_cv = cv2.imread(ref_image_path)
        if ref_cv is None:
            print(f"   ⚠️ cv2.imread 실패: {ref_image_path}")
            return False

        # 크기 맞추기
        if current_cv.shape != ref_cv.shape:
            ref_cv = cv2.resize(ref_cv, (current_cv.shape[1], current_cv.shape[0]))

        res = cv2.matchTemplate(current_cv, ref_cv, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, _, _ = cv2.minMaxLoc(res)
        # print(f"   🔍 match score: {max_val:.4f}")  # 필요하면 주석 해제
        return max_val >= MATCH_THRESHOLD
    except Exception as e:
        print(f"   ⚠️ 이미지 비교 중 예외: {e}")
        return False

# ---------------------------------------------------------
# [함수] 광속 스크롤 (로그아웃 찾기용)
# ---------------------------------------------------------
def blind_scroll_to_bottom():
    print("   📜 하단으로 스크롤...")
    size = driver.get_window_size()
    center_x = size['width'] * 0.5
    start_y = size['height'] * 0.75
    end_y = size['height'] * 0.15
    
    # 4번 연속 빠르게 스크롤
    for _ in range(4):
        driver.execute_script('mobile: dragFromToForDuration', {
            'fromX': center_x, 'fromY': start_y,
            'toX': center_x, 'toY': end_y,
            'duration': 0.05
        })
        time.sleep(0.1)

# ---------------------------------------------------------
# [메인 루프]
# ---------------------------------------------------------
# test_results: [회차, 상태, 측정시간(문자열), 로그인반응속도(초)]
test_results = []

try:
    print("🚀 정부24 ID/PW 로그인 테스트 시작")
    print(f"   🎯 사용 참조 이미지: {TARGET_IMAGE_PATH}")
    time.sleep(5)

    for i in range(1, REPEAT_COUNT + 1):
        print(f"\n[{i}/{REPEAT_COUNT} 회차] 진행 중...")
        # 각 회차 측정 시간
        measured_at = time.strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            # 1. [메인] 로그인 클릭
            print("   📲 [1단계] 메인 -> 로그인")
            wait.until(EC.element_to_be_clickable((
                AppiumBy.IOS_CLASS_CHAIN, 
                '**/XCUIElementTypeLink/XCUIElementTypeStaticText[`name == "로그인"`]'
            ))).click()

            # 2. [로그인선택] 하단 스크롤 후 '아이디 로그인' 클릭
            print("   📲 [3~4단계] 하단 스크롤 및 아이디 로그인 선택")
            print("      ⬇️ 스크롤 다운")
            driver.execute_script('mobile: swipe', {'direction': 'up'})
            time.sleep(1)
            
            try:
                id_login_btn = wait.until(EC.element_to_be_clickable((
                    AppiumBy.IOS_CLASS_CHAIN, 
                    '**/XCUIElementTypeStaticText[`name == "아이디 로그인"`]'
                )))
                print(f"      🎯 '아이디 로그인' 발견! 좌표: {id_login_btn.location}")
                id_login_btn.click()
            except:
                print("      ⚠️ StaticText 실패 -> ACCESSIBILITY_ID 시도")
                driver.find_element(AppiumBy.ACCESSIBILITY_ID, "아이디 로그인").click()

            # 3. [입력] 아이디 -> [다음] -> 비밀번호
            print("   ⌨️ [5~6단계] 아이디/비밀번호 입력")
            
            # (1) 아이디 입력
            id_input = wait.until(EC.presence_of_element_located((
                AppiumBy.IOS_CLASS_CHAIN, 
                '**/XCUIElementTypeTextField[`value == "아이디를 입력하세요."`]'
            )))
            id_input.click()
            id_input.clear()
            id_input.send_keys(GOV_ID)
            
            if driver.is_keyboard_shown():
                driver.execute_script('mobile: tap', {'x': 200, 'y': 100})
            time.sleep(1)

            # (2) '다음' 버튼 클릭
            print("      👉 '다음' 버튼 클릭")
            try:
                next_btn = wait.until(EC.element_to_be_clickable((
                    AppiumBy.IOS_CLASS_CHAIN, 
                    '**/XCUIElementTypeButton[`name == "다음"`]'
                )))
                next_btn.click()
            except:
                print("      ⚠️ '다음' 버튼 찾기 실패 -> 좌표(195, 314) 타격")
                driver.execute_script('mobile: tap', {'x': 195, 'y': 314})
            
            time.sleep(1)
            
            # (3) 비밀번호 입력
            pw_input = wait.until(EC.presence_of_element_located((
                AppiumBy.IOS_CLASS_CHAIN, 
                '**/XCUIElementTypeSecureTextField[`value == "비밀번호를 입력하세요."`]'
            )))
            pw_input.click()
            pw_input.clear()
            pw_input.send_keys(GOV_PW)
            
            # 4. [보안문자] 사용자 수동 입력
            print("\n   🛑 [7~8단계] 보안문자 입력 대기중... (화면을 보고 입력하세요)")
            captcha_code = input("   👉 보안문자 입력: ")
            
            print(f"   ⌨️ 입력값 '{captcha_code}' 전송 중...")
            captcha_input = driver.find_element(AppiumBy.ACCESSIBILITY_ID, "아래의 숫자를 입력하세요.")
            captcha_input.click()
            captcha_input.send_keys(captcha_code)
            
            # 5. [로그인 요청]
            print("   ⏱️ [9~10단계] 로그인 버튼 클릭 (시간 측정 시작)")
            login_btn = wait.until(EC.element_to_be_clickable((
                AppiumBy.IOS_CLASS_CHAIN, '**/XCUIElementTypeButton[`name == "로그인"`]'
            )))
            
            login_btn.click()
            start_time = time.time()

            # 6. [성공 검증] 이미지 비교
            print("   📸 [11~12단계] 메인화면 로딩 대기 (이미지 비교)")
            success = False
            for _ in range(100):  # 20초 대기 (0.01 * 100 * 2 근사)
                if check_login_success_by_roi(driver, TARGET_IMAGE_PATH, ROI_CONFIG):
                    end_time = time.time()
                    duration = end_time - start_time
                    print(f"   🎉 로그인 성공! (이미지 매칭) | 소요 시간: {duration:.4f}초")
                    test_results.append([i, "성공", measured_at, duration])
                    success = True
                    break
                time.sleep(0.01)
            
            if not success:
                print("   ❌ 이미지 매칭 실패 (시간 초과)")
                test_results.append([i, "실패", measured_at, 0])
                raise Exception("로그인 검증 실패")

            # 7. [메뉴 진입]
            print("   🚪 [13단계] 전체메뉴 클릭")
            try:
                wait.until(EC.element_to_be_clickable(
                    (AppiumBy.ACCESSIBILITY_ID, "전체메뉴"))
                ).click()
            except:
                driver.execute_script('mobile: tap', {'x': 335, 'y': 93}) 
            
            time.sleep(2)

            # 8. [로그아웃]
            print("   📜 [14단계] 최하단 스크롤")
            blind_scroll_to_bottom()
            
            print("   🚪 [15단계] 로그아웃 클릭")
            try:
                driver.find_element(AppiumBy.ACCESSIBILITY_ID, "로그아웃").click()
            except:
                blind_scroll_to_bottom()
                size = driver.get_window_size()
                driver.execute_script('mobile: tap', {'x': size['width']*0.5, 'y': size['height']*0.9})

            # 로그아웃 확인 팝업 (있다면)
            try:
                time.sleep(1)
                driver.find_element(AppiumBy.ACCESSIBILITY_ID, "확인").click()
            except:
                pass

            print("   ✅ 초기화면 복귀 완료")
            time.sleep(3)

        except Exception as e:
            print(f"   ❌ {i}회차 실패: {str(e)}")
            # 실패도 타임스탬프 포함해서 기록
            test_results.append([i, "실패", measured_at, 0])
            print("   ⚠️ 앱 재실행")
            driver.terminate_app(driver.capabilities['bundleId'])
            time.sleep(2)
            driver.activate_app(driver.capabilities['bundleId'])
            time.sleep(5)

finally:
    # -----------------------------------------------------
    # ★ 통계 계산 (성공 케이스 기준)
    # -----------------------------------------------------
    durations = [row[3] for row in test_results if row[1] == "성공" and row[3] > 0]

    if durations:
        avg_val = statistics.mean(durations)
        min_val = min(durations)
        max_val = max(durations)
        std_val = statistics.pstdev(durations) if len(durations) > 1 else 0.0
    else:
        avg_val = min_val = max_val = std_val = 0.0

    # ✅ 이 스크립트와 같은 폴더에 저장
    output_path = os.path.join(SCRIPT_DIR, 'ios_gov24_idpw_result.csv')
    print(f"📁 CSV 저장 경로: {output_path}")

    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        # 한글 헤더 + 통계 칸
        writer.writerow(['회차', '상태', '측정시간', '로그인반응속도(초)', '평균(초)', '최소(초)', '최대(초)', '표준편차(초)'])
        
        # 1) 각 회차 기록 (통계 칸은 비워둠)
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

        # 2) 마지막에 통계 요약 행 한 줄만 추가
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

    if driver:
        driver.quit()
