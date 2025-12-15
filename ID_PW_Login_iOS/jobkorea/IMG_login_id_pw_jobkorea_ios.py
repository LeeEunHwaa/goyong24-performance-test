import time
import csv
import base64
import io
import cv2
import numpy as np
import warnings
import os  # ✅ 추가
import statistics  # ✅ 통계 계산용
from PIL import Image
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
LOGIN_ID = "-----"
LOGIN_PW = "-----"
REPEAT_COUNT = 10

# ✅ 스크립트(.py) 파일이 있는 폴더 기준 경로 설정
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_IMAGE_PATH = os.path.join(SCRIPT_DIR, "jobkorea_login.png")  # ← 같은 폴더의 이미지

MATCH_THRESHOLD = 0.90  # 90% 이상 일치하면 성공으로 간주

# [ROI 좌표 설정] (사용자 지정 비율)
ROI_X_PCT = 0.0      # 시작 X
ROI_Y_PCT = 0.055    # 시작 Y (상단 헤더 부근)
ROI_W_PCT = 1.0      # 가로 길이
ROI_H_PCT = 0.05     # 세로 높이

# [팝업 X버튼 좌표]
POPUP_X_PCT = 0.90
POPUP_Y_PCT = 0.825

options = XCUITestOptions()
options.platform_name = "iOS"
options.automation_name = "XCUITest"
UDID = "------"  # [UDID 입력 필수]
options.bundle_id = "kr.co.jobkorea.jobkorea1"

options.set_capability("udid", UDID)

options.set_capability("noReset", True)
options.set_capability("wdaLaunchTimeout", 60000)
options.set_capability("wdaConnectionTimeout", 60000)
options.set_capability("waitForQuiescence", False) 

driver = webdriver.Remote('http://127.0.0.1:4723', options=options)
wait = WebDriverWait(driver, 15)

# ---------------------------------------------------------
# [핵심 함수] 현재 화면의 ROI를 잘라서 정답 이미지와 비교
# ---------------------------------------------------------
def check_login_success_by_image(driver, ref_image_path, roi):
    try:
        # ✅ 참조 이미지 존재 여부 체크
        if not os.path.exists(ref_image_path):
            print(f"   ⚠️ 참조 이미지가 존재하지 않습니다: {ref_image_path}")
            return False

        # 1. 현재 화면 캡처
        screenshot_base64 = driver.get_screenshot_as_base64()
        screenshot_data = base64.b64decode(screenshot_base64)
        
        # PIL 이미지로 변환 및 ROI 크롭
        image = Image.open(io.BytesIO(screenshot_data))
        img_w, img_h = image.size
        
        left = int(img_w * roi['x'])
        top = int(img_h * roi['y'])
        width = int(img_w * roi['w'])
        height = int(img_h * roi['h'])
        
        current_crop = image.crop((left, top, left + width, top + height))
        
        # OpenCV 포맷으로 변환 (RGB -> BGR)
        current_cv = cv2.cvtColor(np.array(current_crop), cv2.COLOR_RGB2BGR)
        
        # 2. 정답 이미지 로드
        ref_cv = cv2.imread(ref_image_path)
        if ref_cv is None:
            print(f"   ⚠️ 오류: 정답 이미지({ref_image_path})를 읽을 수 없습니다.")
            return False

        # 3. 크기 맞추기
        if current_cv.shape != ref_cv.shape:
            ref_cv = cv2.resize(ref_cv, (current_cv.shape[1], current_cv.shape[0]))

        # 4. 이미지 유사도 비교
        res = cv2.matchTemplate(current_cv, ref_cv, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        # print(f"      📊 이미지 유사도: {max_val:.4f}")
        
        return max_val >= MATCH_THRESHOLD

    except Exception as e:
        print(f"   ⚠️ 이미지 비교 중 에러: {e}")
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
roi_config = {'x': ROI_X_PCT, 'y': ROI_Y_PCT, 'w': ROI_W_PCT, 'h': ROI_H_PCT}

try:
    print("🚀 잡코리아 로그인 테스트 시작 (이미지 ROI 비교 모드)")
    print(f"   🎯 사용 기준 이미지: {TARGET_IMAGE_PATH}")
    time.sleep(3)

    for i in range(1, REPEAT_COUNT + 1):
        print(f"\n[{i}/{REPEAT_COUNT} 회차] 진행 중...")
        # 회차별 측정 시간
        measured_at = time.strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            # 1. [메인] MY 버튼
            print("   📲 [1단계] MY 버튼 클릭")
            try:
                wait.until(EC.element_to_be_clickable(
                    (AppiumBy.ACCESSIBILITY_ID, "MY"))
                ).click()
            except:
                wait.until(EC.element_to_be_clickable((
                    AppiumBy.IOS_CLASS_CHAIN, '**/XCUIElementTypeStaticText[`name == "MY"`]'
                ))).click()

            # 2. [로그인 시작]
            print("   📲 [2단계] 다른 아이디로 로그인")
            wait.until(EC.element_to_be_clickable((
                AppiumBy.IOS_CLASS_CHAIN, '**/XCUIElementTypeButton[`name == "다른 아이디로 로그인"`]'
            ))).click()

            # 3. [입력]
            print("   ⌨️ [3단계] 정보 입력")
            wait.until(EC.presence_of_element_located((
                AppiumBy.IOS_CLASS_CHAIN, '**/XCUIElementTypeTextField[`value == "No.1 잡코리아·알바몬 통합 ID"`]'
            ))).send_keys(LOGIN_ID)
            
            wait.until(EC.presence_of_element_located((
                AppiumBy.IOS_CLASS_CHAIN, '**/XCUIElementTypeSecureTextField[`value == "비밀번호"`]'
            ))).send_keys(LOGIN_PW)
            
            # 4. [로그인 요청]
            print("   ⏱️ [4단계] 로그인 버튼 클릭 (시간 측정 시작)")
            login_btn = wait.until(EC.element_to_be_clickable((
                AppiumBy.IOS_CLASS_CHAIN, '**/XCUIElementTypeButton[`name == "로그인"`]'
            )))
            
            start_time = time.time()
            login_btn.click()

            # 5. [성공 검증] 이미지 ROI 비교
            print("   📸 [5단계] 이미지 비교 시작...")
            
            login_success = False
            for _ in range(100):
                if check_login_success_by_image(driver, TARGET_IMAGE_PATH, roi_config):
                    end_time = time.time()
                    duration = end_time - start_time
                    print(f"   🎉 로그인 성공 (이미지 매칭)! | 소요 시간: {duration:.4f}초")
                    # ✅ 성공 기록: [회차, 상태, 측정시간, 소요시간]
                    test_results.append([i, "성공", measured_at, duration])
                    login_success = True
                    break
                time.sleep(0.01)
            
            if not login_success:
                print("   ❌ 이미지 매칭 실패 (시간 초과)")
                # 실패 기록은 아래 except에서 한 번만 처리
                raise Exception("로그인 검증 실패")

            # 6. [팝업 제거]
            print("   ✖️ [6단계] 팝업 제거")
            size = driver.get_window_size()
            driver.execute_script('mobile: tap', {
                'x': size['width'] * POPUP_X_PCT, 
                'y': size['height'] * POPUP_Y_PCT
            })
            time.sleep(1)

            # 7. [로그아웃]
            print("   🚪 [7단계] 하단 스크롤 및 로그아웃")
            try:
                driver.find_element(
                    AppiumBy.IOS_CLASS_CHAIN, 
                    '**/XCUIElementTypeStaticText[`name == "로그아웃"`]'
                ).click()
            except:
                driver.execute_script('mobile: tap', {
                    'x': size['width']*0.5,
                    'y': size['height']*0.9
                })

            # 8. [최종 확인]
            print("   🔔 [8단계] 로그아웃 확인")
            time.sleep(1)
            try:
                driver.find_element(
                    AppiumBy.IOS_CLASS_CHAIN, 
                    '**/XCUIElementTypeButton[`name == "로그아웃"`]'
                ).click()
            except:
                pass

            print("   ✅ 초기화면 복귀 완료")
            time.sleep(3)

        except Exception as e:
            print(f"   ❌ {i}회차 실패: {str(e)}")
            # ✅ 실패 기록: [회차, 상태, 측정시간, 0]
            test_results.append([i, "실패", measured_at, 0])
            print("   ⚠️ 앱 재실행")
            driver.terminate_app(driver.capabilities['bundleId'])
            time.sleep(1)
            driver.activate_app(driver.capabilities['bundleId'])
            time.sleep(5)

finally:
    # -----------------------------------------------------
    # ✅ 통계 계산 (성공 케이스 기준)
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
    output_path = os.path.join(SCRIPT_DIR, 'ios_jobkorea_idpwlogin_result.csv')
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
