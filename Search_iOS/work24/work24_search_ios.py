import time
import os
import csv
import statistics
from datetime import datetime
from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==========================================
# 1. 설정 (Configuration)
# ==========================================
ITERATIONS = 10  # 반복 횟수
keyword = "실업"

options = XCUITestOptions()
options.udid = "----------"  # 실제 기기 UDID 입력
options.platform_name = "iOS"
options.automation_name = "XCUITest"
options.bundle_id = "kr.or.keis.mo"
options.no_reset = True  # 앱 재실행 안 함

# ✅ 이 .py 파일이 있는 폴더 기준
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ==========================================
# 2. 테스트 실행 (Test Execution)
# ==========================================
driver = None
# ✅ [회차, 상태("성공"/"실패"), 측정시간, 검색반응속도(초)]
test_results = []

try:
    print(f"🚀 [성능 테스트 시작] 총 {ITERATIONS}회 반복합니다.")
    driver = webdriver.Remote("http://127.0.0.1:4723", options=options)
    wait = WebDriverWait(driver, 20)

    for i in range(1, ITERATIONS + 1):
        print(f"\n--- [Iter {i}/{ITERATIONS}] 테스트 진행 중 ---")
        measured_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            # [Step 2 & 3] 검색창 터치 및 검색어 입력
            search_input_locator = (AppiumBy.ACCESSIBILITY_ID, "통합검색 검색어 입력")
            search_field = wait.until(EC.element_to_be_clickable(search_input_locator))
            search_field.click()
            search_field.send_keys(keyword)
            
            # 검색 버튼 찾기
            search_btn_locator = (AppiumBy.ACCESSIBILITY_ID, "검색")
            search_button = driver.find_element(*search_btn_locator)

            # [Step 4] 시간 재기 시작
            start_time = time.time()

            # [Step 5] 검색 버튼 터치
            search_button.click()

            # [Step 6] 검색 화면 로드 확인 (성능 측정의 핵심)
            result_validator_locator = (AppiumBy.ACCESSIBILITY_ID, "검색 결과")
            wait.until(EC.presence_of_element_located(result_validator_locator))

            # [Step 7] 시간 재기 종료
            end_time = time.time()
            duration = end_time - start_time
            print(f"✅ {i}회차 소요 시간: {duration:.4f}초")

            # ✅ 성공 기록
            test_results.append([
                i,              # 회차
                "성공",         # 상태
                measured_at,    # 측정시간
                duration        # 검색반응속도(초)
            ])

            # [Step 8] 홈 버튼 클릭 및 복귀 (다음 반복을 위한 준비)
            # 1) 키보드 닫기
            if driver.is_keyboard_shown():
                try:
                    driver.hide_keyboard()
                except:
                    driver.tap([(100, 100)])  # 빈 공간 터치
                time.sleep(1)

            # 2) 홈 버튼 클릭 (XPath 사용)
            home_xpath = '//XCUIElementTypeStaticText[@name="홈"]'
            home_button = wait.until(EC.element_to_be_clickable((AppiumBy.XPATH, home_xpath)))
            home_button.click()
            
            # 메인 화면 복귀 대기
            wait.until(EC.element_to_be_clickable(search_input_locator))
            time.sleep(1)

        except Exception as e:
            print(f"❌ {i}회차 실패: {str(e)}")
            # 실패도 한 줄 기록 (시간 0)
            test_results.append([
                i,
                "실패",
                measured_at,
                0
            ])
            # 실패했더라도 홈으로 돌아가서 다음 루프 시도
            try:
                home_xpath = '//XCUIElementTypeStaticText[@name="홈"]'
                driver.find_element(AppiumBy.XPATH, home_xpath).click()
                time.sleep(2)
            except:
                pass

    print("\n🏁 모든 테스트가 종료되었습니다.")

except Exception as e:
    print(f"❌ 치명적 오류 발생: {str(e)}")

finally:
    if driver:
        driver.quit()

# ==========================================
# 3. 결과 저장 (Save Results) - 공통 형식
# ==========================================
# 유효한 데이터만 필터링 (성공 + duration > 0)
durations = [row[3] for row in test_results if row[1] == "성공" and row[3] > 0]

if durations:
    # 통계 계산
    avg_val = statistics.mean(durations)
    max_val = max(durations)
    min_val = min(durations)
    stdev_val = statistics.pstdev(durations) if len(durations) > 1 else 0.0
else:
    avg_val = min_val = max_val = stdev_val = 0.0

# ✅ 실행 파일과 같은 위치에 고정 파일명으로 저장
output_path = os.path.join(SCRIPT_DIR, "ios_work24_search_result.csv")

try:
    with open(output_path, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        
        # 공통 헤더
        writer.writerow([
            "회차", "상태", "측정시간", "검색반응속도(초)",
            "평균(초)", "최소(초)", "최대(초)", "표준편차(초)"
        ])
        
        # 개별 데이터 작성 (통계 칸은 비워둠)
        for iteration, status, measured_at, duration in test_results:
            writer.writerow([
                iteration,
                status,
                measured_at,
                f"{duration:.4f}" if duration > 0 else "",
                "", "", "", ""
            ])
        
        # 마지막 통계 요약 행
        writer.writerow([
            "통계",
            "",
            "",
            "",
            f"{avg_val:.4f}" if durations else "",
            f"{min_val:.4f}" if durations else "",
            f"{max_val:.4f}" if durations else "",
            f"{stdev_val:.4f}" if durations else ""
        ])

    print(f"\n💾 결과가 저장되었습니다: {output_path}")
        
except Exception as e:
    print(f"파일 저장 중 오류 발생: {e}")
