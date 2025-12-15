import time
import csv
import warnings
import statistics
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
CERTI_PASSWORD = "000000"  # 금융인증서 비밀번호
REPEAT_COUNT = 10 # 반복횟수

options = XCUITestOptions()
options.platform_name = "iOS"
options.automation_name = "XCUITest"
options.udid = "------" # 테스트기기 udid
options.bundle_id = "kr.or.keis.mo" 

options.set_capability("connectHardwareKeyboard", False)
options.set_capability("noReset", True)
options.set_capability("wdaLaunchTimeout", 60000)
options.set_capability("wdaConnectionTimeout", 60000)

driver = webdriver.Remote('http://127.0.0.1:4723', options=options)
wait = WebDriverWait(driver, 20)

# ---------------------------------------------------------
# [함수] 금융인증서 핀번호 입력 (5자리 입력 -> 타이머 시작 -> 6자리 입력)
# ---------------------------------------------------------
def type_certi_password_with_timer(driver, password):
    print(f"   🔐 핀번호 입력 시작 ({len(password)}자리)")
    
    # 비밀번호를 [앞 5자리]와 [마지막 1자리]로 분리
    first_part = password[:-1]  # 예: "12345"
    last_digit = password[-1]   # 예: "6"
    
    # 1. 앞 5자리 입력
    for char in first_part:
        try:
            driver.find_element(AppiumBy.ACCESSIBILITY_ID, char).click()
            time.sleep(0.01) 
        except:
            raise Exception(f"숫자 '{char}'를 찾을 수 없습니다.")
            
    print("   ⏱️ 5자리 입력 완료. 마지막 한 자리 입력 직전 시간 측정 시작!")
    
    # 2. ★ 시간 측정 시작 ★
    start_time = time.time()
    
    # 3. 마지막 6번째 자리 클릭 (로그인 요청 트리거)
    try:
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, last_digit).click()
    except:
        raise Exception(f"마지막 숫자 '{last_digit}'를 찾을 수 없습니다.")
        
    return start_time  # 시작 시간(float, epoch) 반환

# ---------------------------------------------------------
# [메인 테스트 루프]
# ---------------------------------------------------------
# 각 원소: [iteration, status, start_time_str, duration]
test_results = []

try:
    print("🚀 금융인증서 로그인 테스트 시작")
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
            
            # 여기서 5자리 입력 -> 시간 측정 -> 6자리 입력 수행
            start_time = type_certi_password_with_timer(driver, CERTI_PASSWORD)
            # 측정 시작 시각(사람이 보기 좋은 형태)
            start_time_str = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')

            # 5. 결과 확인 (Ok 버튼 기준)
            print("   👀 [5단계] 로그인 완료 대기")
            cancel_btn = wait.until(EC.element_to_be_clickable((
                AppiumBy.ACCESSIBILITY_ID, "Ok"
            )))
            
            end_time = time.time()
            duration = end_time - start_time
            print(f"   🎉 로그인 성공! 소요 시간: {duration:.4f}초")
            # 회차별 결과: 시작시각 + 소요시간 저장
            test_results.append([i, "Success", start_time_str, duration])
            
            # 팝업 닫기
            cancel_btn.click()


            # # 추가 팝업(Ok) 처리
            # try:
            #     time.sleep(1.5)
            #     driver.find_element(AppiumBy.ACCESSIBILITY_ID, "Ok").click()
            #     print("   ℹ️ Ok 팝업 닫음")
            # except:
            #     pass

            print("   ⏳ 메인화면 복귀 대기 (4초)")
            time.sleep(4) 

            # -------------------------------------------------------
            # 6. 로그아웃 (안전장치 추가됨)
            # -------------------------------------------------------
            print("   🚪 [6단계] 로그아웃")
            
            menu_opened = False
            
            # 최대 3번 시도: 메뉴 버튼 누르고 -> 로그아웃 버튼 보이는지 확인
            for attempt in range(3):
                try:
                    # 1) 전체메뉴 클릭
                    print(f"      👉 전체메뉴 클릭 시도 ({attempt+1}/3)")
                    driver.find_element(AppiumBy.ACCESSIBILITY_ID, "전체메뉴").click()
                    
                    time.sleep(2)  # 메뉴 열림 대기
                    
                    # 2) 로그아웃 버튼 찾기 (검증)
                    logout_btn = driver.find_element(AppiumBy.ACCESSIBILITY_ID, "로그아웃")
                    print("      ✅ 메뉴 열림 확인됨")
                    
                    # 3) 로그아웃 클릭
                    logout_btn.click()
                    menu_opened = True
                    break  # 성공하면 반복문 탈출
                except:
                    print("      ⚠️ 메뉴가 안 열렸거나 로그아웃 버튼이 안 보임. 재시도...")
                    time.sleep(1)
            
            if not menu_opened:
                raise Exception("로그아웃 실패: 전체메뉴가 열리지 않았습니다.")

            # 로그아웃 확인 팝업
            try:
                time.sleep(1)
                driver.find_element(AppiumBy.ACCESSIBILITY_ID, "확인").click()
            except:
                pass

            print("   ✅ 초기화면 복귀 완료")
            time.sleep(3)
            
        except Exception as e:
            print(f"   ❌ {i}회차 실패: {str(e)}")
            # 실패한 경우에는 시작 시간은 공란, 소요시간 0으로 기록
            test_results.append([i, "Fail", "", 0])
            
            print("   ⚠️ 앱 재실행")
            driver.terminate_app(driver.capabilities['bundleId'])
            time.sleep(2)
            driver.activate_app(driver.capabilities['bundleId'])
            time.sleep(8)

finally:
    # -------------------------------
    # 통계 계산 (성공한 구간 기준)
    # -------------------------------
    durations = [row[3] for row in test_results if row[1] == "Success" and row[3] > 0]
    
    avg = min_v = max_v = std = 0.0
    if durations:
        avg = sum(durations) / len(durations)
        min_v = min(durations)
        max_v = max(durations)
        std = statistics.stdev(durations) if len(durations) > 1 else 0.0

    # -------------------------------
    # CSV 저장 (현재 실행 디렉토리)
    # -------------------------------
    output_filename = 'ios_login_certificate_result.csv'
    with open(output_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # 헤더
        writer.writerow([
            '회차', '상태', '측정시간', '로그인반응속도(초)',
            '평균(초)', '최소(초)', '최대(초)', '표준편차(초)'
        ])

        # 각 회차 데이터 (통계 컬럼은 비워둠)
        for row in test_results:
            writer.writerow(row + ["", "", "", ""])

        # 요약 행(전체 통계)
        writer.writerow([
            "Summary",
            "Stats",
            "",
            "",
            f"{avg:.4f}",
            f"{min_v:.4f}",
            f"{max_v:.4f}",
            f"{std:.4f}",
        ])
    
    print(f"\n테스트 종료 및 저장 완료: {output_filename}")
    if driver:
        driver.quit()
