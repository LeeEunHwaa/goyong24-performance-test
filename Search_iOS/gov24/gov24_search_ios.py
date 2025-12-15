import time
import csv
import os
import statistics
from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ---------------------------------------------------------
# [설정] 테스트 정보
# ---------------------------------------------------------
SEARCH_KEYWORD = "취업"
REPEAT_COUNT = 10

# [비상용 좌표] (홈 아이콘, 상단 뒤로가기) - 현재는 사용 X
BACK_BTN_X = 30
BACK_BTN_Y = 60

options = XCUITestOptions()
options.platform_name = "iOS"
options.automation_name = "XCUITest"
# [저장된 설정]
options.bundle_id = "kr.go.dcsc.minwon24"
options.udid = "-------"

options.set_capability("noReset", True)
options.set_capability("wdaLaunchTimeout", 60000)
options.set_capability("wdaConnectionTimeout", 60000)
options.set_capability("waitForQuiescence", False)

driver = webdriver.Remote('http://127.0.0.1:4723', options=options)
wait = WebDriverWait(driver, 20)

# ✅ 이 스크립트(.py) 파일이 있는 폴더 기준 경로
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------
# [메인 루프]
# ---------------------------------------------------------
# test_results: [회차, 상태("성공"/"실패"), 측정시간, 검색반응속도(초)]
test_results = []

try:
    print("🚀 정부24 검색 성능 테스트 시작")

    for i in range(1, REPEAT_COUNT + 1):
        print(f"\n[{i}/{REPEAT_COUNT} 회차] 진행 중...")
        measured_at = time.strftime("%Y-%m-%d %H:%M:%S")  # 각 회차 측정 시간

        try:
            # 1. 검색어 입력
            print("   📲 [1~2단계] 검색어 입력")
            search_input = wait.until(EC.element_to_be_clickable((
                AppiumBy.ACCESSIBILITY_ID, "검색어 입력"
            )))
            search_input.click()
            search_input.clear()
            search_input.send_keys(SEARCH_KEYWORD)
            
            # 2. 검색 버튼 클릭
            print("   🔍 [3단계] 검색 버튼 클릭")
            search_btn = driver.find_element(AppiumBy.ACCESSIBILITY_ID, "검색")
            
            start_time = time.time()  # START
            search_btn.click()

            # 3. 검색 완료 확인
            print("   👀 [4단계] 검색 결과 대기")
            wait.until(EC.presence_of_element_located((
                AppiumBy.ACCESSIBILITY_ID, "검색 결과"
            )))
            
            end_time = time.time()  # END
            duration = end_time - start_time
            print(f"   🎉 검색 성공! 소요 시간: {duration:.4f}초")

            # ✅ 성공 기록
            test_results.append([
                i,              # 회차
                "성공",         # 상태
                measured_at,    # 측정시간
                duration        # 검색반응속도(초)
            ])

            # 4. 복귀 전략 실행
            try:
                back_btn = driver.find_element(AppiumBy.ACCESSIBILITY_ID, "이전 페이지")
                print(f"      👉 '이전 페이지' 버튼 클릭")
                back_btn.click()
            except Exception:
                print("      ⚠️ '이전 페이지' 버튼을 찾지 못했습니다. (복귀 스킵)")
            
            # 메인화면 복귀 확인 (검색창이 보이면 성공)
            time.sleep(2)
            driver.find_element(AppiumBy.ACCESSIBILITY_ID, "검색어 입력")
            print("      ✅ 버튼 클릭으로 복귀 성공")

        except Exception as e:
            print(f"   ❌ {i}회차 실패: {e}")
            # ✅ 실패 기록 (시간 0으로 기록, 통계 계산에서 제외)
            test_results.append([
                i,
                "실패",
                measured_at,
                0
            ])
            # 필요시 여기서 추가 복구 로직(예: 뒤로가기, 앱 재실행 등) 넣을 수 있음
            time.sleep(2)

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
    output_path = os.path.join(SCRIPT_DIR, 'ios_gov24_search_result.csv')
    print(f"\n📁 CSV 저장 경로: {output_path}")

    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        # 헤더: 다른 스크립트와 동일 포맷 (검색용 컬럼명만 변경)
        writer.writerow([
            '회차', '상태', '측정시간', '검색반응속도(초)',
            '평균(초)', '최소(초)', '최대(초)', '표준편차(초)'
        ])
        
        # 각 회차 기록 (통계 칸 비워둠)
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

        # 마지막에 통계 요약 행 한 줄만 추가
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
    
    print("\n테스트 종료 및 저장 완료")
    if driver:
        driver.quit()
