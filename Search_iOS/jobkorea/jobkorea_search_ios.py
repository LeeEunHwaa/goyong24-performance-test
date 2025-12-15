import time
import csv
import os
import statistics
from datetime import datetime
from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ===================== [iOS 설정 영역] =====================
UDID = "------------"
BUNDLE_ID = "kr.co.jobkorea.jobkorea1"
DEVICE_NAME = "iPhone"
APPIUM_SERVER_URL = "http://127.0.0.1:4723"

REPEAT_COUNT = 10
KEYWORD = "디자이너"
# =======================================================

# ✅ 이 .py 파일이 있는 폴더 기준 경로
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def run_ios_jobkorea_test():
    options = XCUITestOptions()
    options.platform_name = "iOS"
    options.automation_name = "XCUITest"
    options.udid = UDID
    options.bundle_id = BUNDLE_ID
    options.device_name = DEVICE_NAME
    options.no_reset = True
    options.new_command_timeout = 300
    options.auto_accept_alerts = True  # 알림창 자동 수락

    print(f"--- [iOS] 잡코리아 검색 성능 측정 ({REPEAT_COUNT}회, No Restart) 시작 ---")
    
    driver = None
    # ✅ 결과: [회차, 상태("성공"/"실패"), 측정시간, 검색반응속도(초)]
    test_results = []

    try:
        driver = webdriver.Remote(APPIUM_SERVER_URL, options=options)
        wait = WebDriverWait(driver, 20)

        print("📱 앱 실행 및 메인 화면 대기 중...")
        # 최초 1회는 앱을 실행
        driver.activate_app(BUNDLE_ID)
        
        # 메인 검색 버튼(파란 돋보기) 대기
        search_btn_locator = (AppiumBy.ACCESSIBILITY_ID, "new_main_search_blue")
        wait.until(EC.presence_of_element_located(search_btn_locator))

        for i in range(1, REPEAT_COUNT + 1):
            measured_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                print(f"\n[Running] {i}/{REPEAT_COUNT}회차 측정 진행 중...")

                # Step 1. 메인 검색 버튼 클릭
                print("   🔍 메인 검색 버튼 클릭")
                try:
                    driver.find_element(*search_btn_locator).click()
                except:
                    print("   ⚠️ 요소 클릭 실패 -> 좌표 타격")
                    driver.tap([(340, 125)]) 

                # Step 2. 검색어 입력창 찾기
                time.sleep(1)  # 화면 전환 대기
                search_input = wait.until(EC.visibility_of_element_located(
                    (AppiumBy.CLASS_NAME, "XCUIElementTypeTextField")
                ))
                
                # 기존 텍스트 지우기
                search_input.clear()
                
                # Step 3. 타이머 시작 & 검색 실행
                print(f"   ⌨️ 검색어 '{KEYWORD}' 입력 및 엔터")
                
                start_time = time.time()  # START
                search_input.send_keys(KEYWORD + "\n")
                
                # Step 4. 결과 확인 (검색 완료 판단)
                try:
                    wait.until(EC.presence_of_element_located(
                        (AppiumBy.ACCESSIBILITY_ID, "검색조건 저장")
                    ))
                except:
                    # 백업: '경력' 필터 버튼
                    wait.until(EC.presence_of_element_located(
                        (AppiumBy.ACCESSIBILITY_ID, "경력")
                    ))
                
                end_time = time.time()  # END
                
                duration = end_time - start_time
                print(f"   ⏱️ {i}회차 소요 시간: {duration:.4f}초")

                test_results.append([
                    i,               # 회차
                    "성공",          # 상태
                    measured_at,     # 측정시간
                    duration         # 검색반응속도(초)
                ])

                # Step 5. 메인화면 복귀 (뒤로가기 버튼 사용)
                print("   🔙 메인화면 복귀 (뒤로가기)")
                
                try:
                    back_btn = driver.find_element(AppiumBy.ACCESSIBILITY_ID, "advanced search back")
                    back_btn.click()
                except:
                    print("   ⚠️ 뒤로가기 버튼 못 찾음 -> 좌표(20, 60) 타격")
                    driver.execute_script('mobile: tap', {'x': 20, 'y': 60})

                # 메인으로 한 번 더 뒤로가기 (Jams/system_back)
                try:
                    main_back_btn = driver.find_element(AppiumBy.ACCESSIBILITY_ID, "Jams/system_back")
                    main_back_btn.click()
                except:
                    print("   ⚠️ 메인 뒤로가기 버튼(Jams/system_back) 찾기 실패")

                # 메인 화면 복귀 확인
                wait.until(EC.presence_of_element_located(search_btn_locator))
                time.sleep(1)  # 다음 회차 준비

            except Exception as e:
                print(f"❌ {i}회차 실행 중 에러: {e}")
                # 에러도 실패로 기록 (시간 0)
                test_results.append([
                    i,
                    "실패",
                    measured_at,
                    0
                ])
                # 앱 재실행으로 복구
                try:
                    driver.terminate_app(BUNDLE_ID)
                    time.sleep(1)
                    driver.activate_app(BUNDLE_ID)
                    time.sleep(5)
                except:
                    pass

        # ===================== CSV 저장 (통일 포맷) =====================
        if test_results:
            # 성공 케이스만 통계 계산
            durations = [row[3] for row in test_results if row[1] == "성공" and row[3] > 0]

            if durations:
                avg_val = statistics.mean(durations)
                min_val = min(durations)
                max_val = max(durations)
                std_val = statistics.pstdev(durations) if len(durations) > 1 else 0.0
            else:
                avg_val = min_val = max_val = std_val = 0.0
            
            # ✅ 현재 .py 파일과 같은 위치에 저장
            file_path = os.path.join(SCRIPT_DIR, "ios_jobkorea_search_result.csv")

            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                # 공통 헤더 형식
                writer.writerow([
                    "회차", "상태", "측정시간", "검색반응속도(초)",
                    "평균(초)", "최소(초)", "최대(초)", "표준편차(초)"
                ])

                # 회차별 기록
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

                # 통계 한 줄
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

            print(f"\n✅ CSV 저장 완료! 경로: {file_path}")
        else:
            print("ℹ️ 저장할 데이터가 없습니다.")

    except Exception as e:
        print(f"⛔ 전체 에러: {e}")

    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    run_ios_jobkorea_test()
