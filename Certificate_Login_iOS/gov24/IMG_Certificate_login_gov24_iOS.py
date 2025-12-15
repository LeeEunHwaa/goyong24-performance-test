import time
import csv
import base64
import io
import cv2
import numpy as np
import warnings
from PIL import Image
from urllib3.exceptions import NotOpenSSLWarning
from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import statistics  # ★ 통계 계산용 추가

warnings.simplefilter('ignore', NotOpenSSLWarning)

# ---------------------------------------------------------
# [설정] 정부24 계정 및 테스트 설정
# ---------------------------------------------------------
CERTI_PASSWORD = "000000"  # 금융인증서 6자리 비밀번호
REPEAT_COUNT = 10          # 반복횟수

# [이미지 검증 설정]
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # 이 파이썬 파일이 있는 폴더
TARGET_IMAGE_PATH = os.path.join(BASE_DIR, "gov24_test.png")  # 테스터용 이미지파일 이름
MATCH_THRESHOLD = 0.90  # 90% 이상 일치 시 성공

# [ROI 좌표 설정] (하단 영역 10%)
ROI_CONFIG = {
    'x': 0,         # 가로 시작
    'y': 0.88,      # 세로 시작 (88% 지점)
    'w': 1,         # 가로 너비 (100%)
    'h': 0.1        # 세로 높이 (10%)
}

options = XCUITestOptions()
options.platform_name = "iOS"
options.automation_name = "XCUITest"
options.udid = "-------------"  # 테스트기기 UDID 설정
options.bundle_id = "kr.go.dcsc.minwon24"

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
        # 1. 현재 화면 캡처
        screenshot_base64 = driver.get_screenshot_as_base64()
        image = Image.open(io.BytesIO(base64.b64decode(screenshot_base64)))
        
        # 2. ROI 영역 계산 및 자르기
        img_w, img_h = image.size
        left = int(img_w * roi['x'])
        top = int(img_h * roi['y'])
        width = int(img_w * roi['w'])
        height = int(img_h * roi['h'])
        
        current_crop = image.crop((left, top, left + width, top + height))
        current_cv = cv2.cvtColor(np.array(current_crop), cv2.COLOR_RGB2BGR)
        
        # 3. 정답 이미지 로드
        ref_cv = cv2.imread(ref_image_path)
        if ref_cv is None:
            print(f"   ⚠️ 오류: 정답 이미지({ref_image_path})를 읽을 수 없습니다.")
            return False

        # 4. 크기 보정 (혹시 1픽셀 정도 오차가 있을 경우 대비)
        if current_cv.shape != ref_cv.shape:
            ref_cv = cv2.resize(ref_cv, (current_cv.shape[1], current_cv.shape[0]))

        # 5. 유사도 비교
        res = cv2.matchTemplate(current_cv, ref_cv, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, _, _ = cv2.minMaxLoc(res)
        
        # print(f"      📊 현재 화면 유사도: {max_val:.4f}") # 디버깅용
        return max_val >= MATCH_THRESHOLD

    except Exception as e:
        print(f"   ⚠️ 이미지 비교 에러: {e}")
        return False

# ---------------------------------------------------------
# [함수] 핀번호 입력 (5자리 -> 타이머 -> 6자리)
# ---------------------------------------------------------
def type_password_and_measure(driver, password):
    print(f"   🔐 핀번호 입력 ({len(password)}자리)")
    
    # 앞 5자리
    for char in password[:-1]:
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, char).click()
        time.sleep(0.01)
        
    print("   ⏱️ 5자리 입력 완료. 시간 측정 시작!")
    start_time = time.time()
    
    # 마지막 6번째
    driver.find_element(AppiumBy.ACCESSIBILITY_ID, password[-1]).click()
    
    return start_time

# ---------------------------------------------------------
# [함수] 광속 스크롤 (로그아웃 버튼 찾기)
# ---------------------------------------------------------
def blind_scroll_to_bottom():
    size = driver.get_window_size()
    center_x = size['width'] * 0.5
    # 길게 스크롤 (화면의 75% 이동)
    start_y = size['height'] * 0.8
    end_y = size['height'] * 0.15 
    
    print("   📜 하단으로 스크롤...")
    for _ in range(3):
        driver.execute_script('mobile: dragFromToForDuration', {
            'fromX': center_x, 'fromY': start_y,
            'toX': center_x, 'toY': end_y,
            'duration': 0.05
        })
        time.sleep(0.02)

# ---------------------------------------------------------
# [메인 테스트 루프]
# ---------------------------------------------------------
# test_results: [회차, 상태, 측정시간(문자열), 로그인반응속도(초)]
test_results = []

try:
    print("🚀 정부24 금융인증서 로그인 테스트 시작 (이미지 검증)")
    time.sleep(5)

    for i in range(1, REPEAT_COUNT + 1):
        print(f"\n[{i}/{REPEAT_COUNT} 회차] 진행 중...")
        # ★ 측정 시각 기록 (각 회차 시작 시)
        measured_at = time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            # 1. [메인] 로그인 클릭 (Link 안의 StaticText)
            print("   📲 [1단계] 메인 -> 로그인")
            wait.until(EC.element_to_be_clickable((
                AppiumBy.IOS_CLASS_CHAIN, 
                '**/XCUIElementTypeLink/XCUIElementTypeStaticText[`name == "로그인"`]'
            ))).click()

            # 2. [로그인선택] 금융인증서
            print("   📲 [2단계] 금융인증서 선택")
            wait.until(EC.element_to_be_clickable((
                AppiumBy.ACCESSIBILITY_ID, "금융인증서"
            ))).click()

            # 3. [인증서선택] 내 인증서
            print("   👤 [3단계] 사용자 인증서 선택")
            wait.until(EC.element_to_be_clickable((
                AppiumBy.IOS_CLASS_CHAIN, 
                '**/XCUIElementTypeButton[`name CONTAINS "금융인증서를 선택합니다"`]'
            ))).click()

            # 4. [비밀번호] 핀번호 입력 및 타이머 시작
            print("   ⌨️ [4단계] 핀번호 입력 화면 대기")
            wait.until(EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "1")))
            
            # 입력 함수 호출 (여기서 start_time 반환)
            start_time = type_password_and_measure(driver, CERTI_PASSWORD)

            # 5. [성공 검증] 이미지 매칭 (ROI 비교)
            print("   📸 [5단계] 메인화면 로딩 대기 (이미지 비교)")
            
            success = False
            # 최대 20초간 반복 검사
            for _ in range(100): 
                if check_login_success_by_roi(driver, TARGET_IMAGE_PATH, ROI_CONFIG):
                    end_time = time.time()
                    duration = end_time - start_time
                    print(f"   🎉 로그인 성공! (이미지 매칭됨) | 소요 시간: {duration:.4f}초")
                    # ★ 성공 기록 (한국어 상태, 측정시간 포함)
                    test_results.append([i, "성공", measured_at, duration])
                    success = True
                    break
                time.sleep(0.01) # 0.01초 간격 체크
            
            if not success:
                print("   ❌ 이미지 매칭 실패 (시간 초과)")
                # 실패는 여기서 예외만 던지고, 아래 except에서 한 번만 기록
                raise Exception("로그인 검증 실패")

            # 6. [메뉴 진입] 전체메뉴 클릭
            print("   🚪 [6단계] 전체메뉴 클릭")
            # 이미지 매칭 성공 직후이므로, 화면에 요소가 떴을 것임
            try:
                wait.until(EC.element_to_be_clickable((
                    AppiumBy.ACCESSIBILITY_ID, "전체메뉴"
                ))).click()
            except:
                # 혹시 클릭 씹히면 좌표 탭 (우측 상단 햄버거 메뉴 위치 추정)
                driver.execute_script('mobile: tap', {'x': 335, 'y': 93})  # XML 기준 좌표

            time.sleep(2)

            # 7. [로그아웃] 광속 스크롤 및 클릭
            print("   📜 [7단계] 하단 스크롤 및 로그아웃")
            blind_scroll_to_bottom()  # Y=2040까지 내리기
            
            try:
                # 로그아웃 버튼 찾아서 클릭
                driver.find_element(AppiumBy.ACCESSIBILITY_ID, "로그아웃").click()
            except:
                # 안 되면 한번 더 스크롤 후 좌표 타격 (백업)
                blind_scroll_to_bottom()
                size = driver.get_window_size()
                driver.execute_script('mobile: tap', {'x': size['width']*0.5, 'y': size['height']*0.9})

            # 로그아웃 확인 팝업 (혹시 있다면)
            try:
                time.sleep(1)
                driver.find_element(AppiumBy.ACCESSIBILITY_ID, "확인").click()
            except:
                pass

            print("   ✅ 초기화면 복귀 완료")
            time.sleep(3)

        except Exception as e:
            print(f"   ❌ {i}회차 실패: {str(e)}")
            # ★ 실패 기록 (한국어 상태, 측정시간 포함, 시간 0)
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

    # ★ 스크립트와 같은 폴더에 저장되도록 경로 지정
    output_path = os.path.join(BASE_DIR, 'IMG_gov24_result_ios.csv')
    print(f"📁 CSV 저장 경로: {output_path}")

    # 현재 디렉토리에 저장 (Excel 호환 위해 utf-8-sig)
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
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
            "통계",      # 회차 자리 대신 '통계' 표기
            "",          # 상태
            "",          # 측정시간
            "",          # 로그인반응속도(초)
            f"{avg_val:.4f}" if durations else "",
            f"{min_val:.4f}" if durations else "",
            f"{max_val:.4f}" if durations else "",
            f"{std_val:.4f}" if durations else ""
        ])

    if driver:
        driver.quit()
