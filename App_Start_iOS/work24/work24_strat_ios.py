import os
import time
import csv
import statistics
from datetime import datetime
from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ===================== [기본 설정] =====================
UDID = "----------"
BUNDLE_ID = "kr.or.keis.mo"  # 고용24
APPIUM_URL = "http://127.0.0.1:4723"
REPEAT_COUNT = 10

# ✅ 이 .py 파일이 있는 폴더 기준
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# =======================================================

def run_work24_full_scan():
    print(f"🚀 [고용24] 전체 UI 스캔 실행 속도 측정 ({REPEAT_COUNT}회)")
    print("   (상단/중단/하단 17개 요소를 모두 검증합니다)")
    
    options = XCUITestOptions()
    options.platform_name = "iOS"
    options.automation_name = "XCUITest"
    options.udid = UDID
    options.bundle_id = BUNDLE_ID
    options.no_reset = True
    options.auto_accept_alerts = True
    options.use_prebuilt_wda = True
    
    driver = None
    # ✅ 통합 결과: [회차, 상태("성공"/"실패"), 측정시간, 앱실행반응속도(초)]
    test_results = []

    # [검증 리스트] XML 분석 기반 정확한 XPath 매핑
    check_list = [
        # --- 상단 (Header) ---
        ("상단_로고(이미지)", AppiumBy.XPATH, '//XCUIElementTypeImage[@name="고용24"]'),
        ("상단_개인", AppiumBy.XPATH, '//XCUIElementTypeLink[@name="개인"]'),
        ("상단_기업", AppiumBy.XPATH, '//XCUIElementTypeLink[@name="기업"]'),
        ("상단_설정", AppiumBy.XPATH, '//XCUIElementTypeButton[@name="환경설정"]'),
        ("상단_전체메뉴", AppiumBy.XPATH, '//XCUIElementTypeButton[@name="전체메뉴"]'),

        # --- 중단 (Body) ---
        ("중단_검색창", AppiumBy.CLASS_NAME, "XCUIElementTypeTextField"),
        ("중단_일자리찾기", AppiumBy.XPATH, '//XCUIElementTypeButton[@name="일자리 찾기"]'),
        ("중단_구직신청", AppiumBy.XPATH, '//XCUIElementTypeButton[@name="구직신청"]'),
        ("중단_구직관리", AppiumBy.XPATH, '//XCUIElementTypeButton[@name="구직관리"]'),
        ("중단_맞춤채용", AppiumBy.XPATH, '//XCUIElementTypeButton[@name="맞춤채용정보"]'),
        ("중단_AI추천", AppiumBy.XPATH, '//XCUIElementTypeButton[@name="AI추천(일자리)"]'),
        ("중단_채용행사", AppiumBy.XPATH, '//XCUIElementTypeButton[@name="채용행사"]'),

        # --- 하단 (Footer / TabBar) ---
        ("하단_정책제도", AppiumBy.XPATH, '//XCUIElementTypeLink[@name="정책/제도"]'),
        ("하단_통합검색", AppiumBy.XPATH, '//XCUIElementTypeLink[@name="통합검색"]'),
        ("하단_홈", AppiumBy.XPATH, '//XCUIElementTypeLink[@name="홈"]'),
        ("하단_이용안내", AppiumBy.XPATH, '//XCUIElementTypeLink[@name="이용안내"]'),
        ("하단_로그인", AppiumBy.XPATH, '//XCUIElementTypeLink[@name="로그인"]')
    ]

    try:
        driver = webdriver.Remote(APPIUM_URL, options=options)
        # 요소가 많으므로 전체 로딩 대기 시간을 넉넉히 60초로 설정
        wait = WebDriverWait(driver, 60)

        for i in range(1, REPEAT_COUNT + 1):
            measured_at = datetime.now().strftime("%H:%M:%S")
            try:
                print(f"\n[{i}/{REPEAT_COUNT}] 측정 시작 (17개 요소 스캔 중...)")
                
                # 1. 앱 종료
                driver.terminate_app(BUNDLE_ID)
                time.sleep(3)

                # 2. 앱 실행 (Start)
                start_time = time.time()
                driver.activate_app(BUNDLE_ID)

                # 3. 모든 요소 순차 검증 (하나라도 안 보이면 대기)
                for name, by, value in check_list:
                    wait.until(EC.visibility_of_element_located((by, value)))
                    # print(f"   - {name} 확인됨")

                # 4. 측정 종료 (End)
                end_time = time.time()
                duration = end_time - start_time
                
                print(f"   ✅ [완료] 소요시간: {duration:.4f}초")

                test_results.append([
                    i,               # 회차
                    "성공",          # 상태
                    measured_at,     # 측정시간
                    round(duration, 4)  # 앱실행반응속도(초)
                ])

            except Exception as e:
                print(f"   ❌ {i}회차 실패 (요소 미확인): {e}")
                test_results.append([
                    i,
                    "실패",
                    measured_at,
                    0  # 실패는 0초로 기록 (통계 계산에서 제외)
                ])

        # ============== CSV 저장 (다른 스크립트와 동일 포맷) ==============
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
            
            # ✅ 결과를 현재 .py 파일과 같은 위치에 저장
            file_path = os.path.join(SCRIPT_DIR, "ios_work24_launch_fullscan_result.csv")

            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                # 헤더
                writer.writerow([
                    "회차", "상태", "측정시간", "앱실행반응속도(초)",
                    "평균(초)", "최소(초)", "최대(초)", "표준편차(초)"
                ])

                # 각 회차 기록 (통계 칸 비움)
                for iteration, status, measured_at, duration in test_results:
                    writer.writerow([
                        iteration,
                        status,
                        measured_at,
                        f"{duration:.4f}" if duration > 0 else "",
                        "", "", "", ""
                    ])

                # 마지막 통계 행
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

            print("\n📊 [고용24] 평균 실행 속도")
            if durations:
                print(f"   👉 {avg_val:.4f} 초")
            else:
                print("   👉 유효한 성공 데이터가 없습니다.")
            print(f"\n✅ 저장 완료: {file_path}")

    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    run_work24_full_scan()
