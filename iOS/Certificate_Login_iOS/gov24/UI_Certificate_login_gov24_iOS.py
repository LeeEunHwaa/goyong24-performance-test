import time
import csv
import warnings
import os  # ★ 추가: 파일 저장 경로용
from urllib3.exceptions import NotOpenSSLWarning
from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import statistics  # ★ 통계 계산용

warnings.simplefilter('ignore', NotOpenSSLWarning)

# ---------------------------------------------------------
# [설정] 정부24 계정 및 테스트 설정
# ---------------------------------------------------------
CERTI_PASSWORD = "000000"  # 금융인증서 6자리 비밀번호 입력
REPEAT_COUNT = 10

options = XCUITestOptions()
options.platform_name = "iOS"
options.automation_name = "XCUITest"

# [기억된 설정 적용]
options.bundle_id = "kr.go.dcsc.minwon24"       # 정부24 Bundle ID
options.udid = "----------"      # 테스트 기기 UDID

options.set_capability("noReset", True)
options.set_capability("wdaLaunchTimeout", 60000)
options.set_capability("wdaConnectionTimeout", 60000)
options.set_capability("waitForQuiescence", False)

driver = webdriver.Remote('http://127.0.0.1:4723', options=options)
wait = WebDriverWait(driver, 20)

# ★ 이 파일이 있는 폴더 (CSV를 여기에 저장)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------
# [함수] 핀번호 입력 (5자리 -> 타이머 -> 6자리)
# ---------------------------------------------------------
def type_password_and_measure(driver, password):
    print(f"   🔐 핀번호 입력 ({len(password)}자리)")
    
    # 앞 5자리 입력
    for char in password[:-1]:
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, char).click()
        time.sleep(0.1)
        
    print("   ⏱️ 5자리 입력 완료. 시간 측정 시작!")
    start_time = time.time()
    
    # 마지막 6번째 자리 입력
    driver.find_element(AppiumBy.ACCESSIBILITY_ID, password[-1]).click()
    
    return start_time

# ---------------------------------------------------------
# [함수] 광속 스크롤 (로그아웃 찾기용)
# ---------------------------------------------------------
def blind_scroll_to_bottom():
    print("   📜 하단으로 스크롤...")
    size = driver.get_window_size()
    center_x = size['width'] * 0.5
    start_y = size['height'] * 0.75
    end_y = size['height'] * 0.15
    
    # 5번 연속 빠르게 스크롤
    for _ in range(5):
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
    print("🚀 정부24 금융인증서 로그인 테스트 시작 (UI 인식)")
    time.sleep(5)

    for i in range(1, REPEAT_COUNT + 1):
        print(f"\n[{i}/{REPEAT_COUNT} 회차] 진행 중...")
        # ★ 이 회차 측정 시간 기록 (CSV '측정시간' 컬럼용)
        measured_at = time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            # 1. [메인] 로그인 클릭
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
            print("   ⌨️ [4단계] 핀번호 입력")
            wait.until(EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "1")))
            
            # 입력 함수 호출 (start_time 반환)
            start_time = type_password_and_measure(driver, CERTI_PASSWORD)

            # -------------------------------------------------------
            # 5. [성공 검증] 메인화면 UI 인식 (전체메뉴 버튼)
            # -------------------------------------------------------
            print("   👀 [5단계] 메인화면 로딩 대기 (UI 인식)")
            
            # 여기서 찾은 element는 '검증용' (클릭 X)
            wait.until(EC.presence_of_element_located((
                AppiumBy.ACCESSIBILITY_ID, "전체메뉴"
            )))
            
            end_time = time.time()
            duration = end_time - start_time
            print(f"   🎉 로그인 성공! ('전체메뉴' 버튼 활성화) | 소요 시간: {duration:.4f}초")
            # ★ 성공 기록 (상태: '성공', 측정시간, 소요시간)
            test_results.append([i, "성공", measured_at, duration])

            # -------------------------------------------------------
            # 6. [메뉴 진입] 전체메뉴 클릭 (재탐색 + 확인사살)
            # -------------------------------------------------------
            print("   🚪 [6단계] 전체메뉴 진입 시도")
            
            # 화면 안정화를 위해 잠시 대기
            time.sleep(2.0)
            
            menu_opened = False
            try:
                print("      👉 '전체메뉴' 버튼 재탐색 및 클릭")
                menu_btn = driver.find_element(AppiumBy.ACCESSIBILITY_ID, "전체메뉴")
                menu_btn.click()
                menu_opened = True
            except:
                print("      ⚠️ 버튼 클릭 실패 -> 좌표 강제 타격")
                driver.execute_script('mobile: tap', {'x': 350, 'y': 110})
                menu_opened = True

            print("      ⏳ 메뉴 열림 대기 (2초)")
            time.sleep(2.0)

            # 7. [로그아웃] 스크롤 및 클릭
            print("   📜 [7단계] 하단 스크롤 및 로그아웃")
            blind_scroll_to_bottom()
            
            try:
                # 로그아웃 버튼 찾아서 클릭
                driver.find_element(AppiumBy.ACCESSIBILITY_ID, "로그아웃").click()
            except:
                # 안 되면 좌표 타격 (백업)
                print("   ⚠️ 로그아웃 버튼 못 찾음 -> 좌표 타격")
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
            # ★ 실패도 한글 상태 + 측정시간 기록, 시간은 0
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

    # ★ 스크립트와 동일한 폴더에 저장되도록 경로 지정
    output_path = os.path.join(BASE_DIR, 'UI_gov24_result_ios.csv')
    print(f"📁 CSV 저장 경로: {output_path}")

    # CSV 저장 (Excel 호환 위해 utf-8-sig)
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
