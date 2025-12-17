import time
import pandas as pd
import os
import statistics
from datetime import datetime
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ===================== [설정 영역: 고용24] =====================
APP_PACKAGE = "kr.or.keis.mo"
APP_ACTIVITY = "kr.or.keis.mo.MainActivity"
DEVICE_NAME = "Galaxy S25"
APPIUM_SERVER_URL = "http://127.0.0.1:4723"

# 반복횟수
REPEAT_COUNT = 10

# 검색어 입력값
KEYWORD = "청년"

# ✅ 이 파일이 있는 폴더 경로
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 메인 테스트

def run_work24_search_test():
    options = UiAutomator2Options()
    options.device_name = DEVICE_NAME
    options.app_package = APP_PACKAGE
    options.app_activity = APP_ACTIVITY
    options.automation_name = "UiAutomator2"
    options.no_reset = True
    options.new_command_timeout = 300
    
    # ⚡ [속도 최적화 옵션]
    options.set_capability("waitForIdleTimeout", 0) 
    options.set_capability("ignoreUnimportantViews", True)
    
    options.set_capability("connectHardwareKeyboard", True)

    print(f"--- 고용24(Work24) 검색 성능 측정 ({REPEAT_COUNT}회) 시작 ---")
    
    driver = None
    test_results = []

    try:
        driver = webdriver.Remote(APPIUM_SERVER_URL, options=options)
        wait = WebDriverWait(driver, 20)

        print("📱 앱 실행 및 메인 화면 대기 중...")
        # 메인 검색창 대기 (Resource ID 사용)
        wait.until(EC.visibility_of_element_located(
            (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().resourceId("top-topQueryMain")')
        ))

        # ===================== 반복 측정 루프 =====================
        for i in range(1, REPEAT_COUNT + 1):
            measured_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                print(f"\n[Running] {i}/{REPEAT_COUNT}회차 측정 진행 중...")

                # ---------------------------------------------------------
                # Step 1. 검색어 입력 (메인화면 검색창)
                # ---------------------------------------------------------
                search_input = wait.until(EC.visibility_of_element_located(
                    (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().resourceId("top-topQueryMain")')
                ))
                
                search_input.click()
                search_input.clear()
                search_input.send_keys(KEYWORD)
                
                # ---------------------------------------------------------
                # Step 2. 검색 버튼 클릭 (측정 시작 T1)
                # ---------------------------------------------------------
                # 검색 버튼 Resource ID: top-findSearchDataMain
                search_btn = wait.until(EC.element_to_be_clickable(
                    (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().resourceId("top-findSearchDataMain")')
                ))
                
                # [Time Start] 클릭 직전
                search_btn.click()
                start_time = time.time() 
                
                # ---------------------------------------------------------
                # Step 3. [초고속 완료 인식] Raw Loop + UiSelector
                # ---------------------------------------------------------
                # "검색 결과" 텍스트가 포함된 뷰가 뜰 때까지 대기
                target_selector = 'new UiSelector().textContains("검색 결과")'
                
                while True:
                    # find_elements는 에러 없이 빈 리스트 반환 (가장 빠름)
                    res = driver.find_elements(AppiumBy.ANDROID_UIAUTOMATOR, target_selector)
                    
                    if res:
                        break # 찾았으면 즉시 탈출
                    
                    # 안전장치: 20초 타임아웃
                    if time.time() - start_time > 20:
                        raise Exception("Timeout: 검색 결과 미표시")
                
                # [Time End]
                end_time = time.time()
                
                duration = end_time - start_time
                print(f"⏱️ {i}회차 소요 시간: {duration:.4f}초")

                test_results.append([i, "성공", measured_at, duration])

                # ---------------------------------------------------------
                # Step 4. 메인 화면 복귀 (뒤로 가기)
                # ---------------------------------------------------------
                print("🔙 하드웨어 뒤로가기 키 입력")
                driver.press_keycode(4) # Back Button

                # 메인 화면 복귀 확인
                wait.until(EC.visibility_of_element_located(
                    (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().resourceId("top-topQueryMain")')
                ))
                
                time.sleep(1) # 안정화 대기

            except Exception as e:
                print(f"❌ {i}회차 실행 중 에러 발생: {e}")
                test_results.append([i, "실패", measured_at, 0])
                try:
                    driver.press_keycode(4) # 에러 시 뒤로가기 시도
                except:
                    pass

        # ===================== CSV 저장 로직 (통일된 포맷) =====================
        print("\n" + "=" * 50)
        print("💾 결과 저장 중...")

        # 성공한 케이스만 통계 계산
        durations = [row[3] for row in test_results if row[1] == "성공" and row[3] > 0]

        if durations:
            avg = statistics.mean(durations)
            mn = min(durations)
            mx = max(durations)
            std = statistics.pstdev(durations) if len(durations) > 1 else 0.0
        else:
            avg = mn = mx = std = 0.0

        # 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"work24_search_perf_{REPEAT_COUNT}runs_{timestamp}.csv"
        
        # ✅ [핵심] 현재 폴더에 저장
        output_path = os.path.join(SCRIPT_DIR, file_name)

        if test_results:
            df = pd.DataFrame(test_results, columns=["회차", "상태", "측정시간", "검색반응속도(초)"])
            
            # 통계용 컬럼 추가
            df["평균(초)"] = ""
            df["최소(초)"] = ""
            df["최대(초)"] = ""
            df["표준편차(초)"] = ""

            # 요약 행 추가
            summary = {
                "회차": "요약",
                "상태": "",
                "측정시간": "",
                "검색반응속도(초)": "",
                "평균(초)": round(avg, 4),
                "최소(초)": round(mn, 4),
                "최대(초)": round(mx, 4),
                "표준편차(초)": round(std, 4)
            }
            
            df = pd.concat([df, pd.DataFrame([summary])], ignore_index=True)
            df.to_csv(output_path, index=False, encoding="utf-8-sig")

            print(f"✅ 저장 완료: {output_path}")
            print(df)
        else:
            print("ℹ️ 저장할 데이터가 없습니다.")

    except Exception as e:
        print(f"⛔ 치명적 오류: {e}")

    finally:
        if driver:
            driver.quit()

# 테스트 실행
if __name__ == "__main__":
    run_work24_search_test()