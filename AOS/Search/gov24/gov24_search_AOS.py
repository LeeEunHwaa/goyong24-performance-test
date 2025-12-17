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

# ===================== [설정 영역] =====================
APP_PACKAGE = "kr.go.minwon.m"
APP_ACTIVITY = "kr.go.minwon.m.BrowserActivity"
DEVICE_NAME = "Galaxy S24"
APPIUM_SERVER_URL = "http://127.0.0.1:4723"

# 반복 횟수
REPEAT_COUNT = 10

# 검색어 입력값
KEYWORD = "청년"

# ✅ 이 파일이 있는 폴더 경로
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 메인 테스트
def run_gov24_search_test():
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
    
    # 키보드 관련 설정
    options.set_capability("connectHardwareKeyboard", True)

    print(f"--- 정부24 검색 성능 측정 ({REPEAT_COUNT}회) 시작 ---")
    
    driver = None
    # 결과 저장용 리스트: [회차, 상태, 측정시간, 소요시간]
    test_results = []

    try:
        driver = webdriver.Remote(APPIUM_SERVER_URL, options=options)
        wait = WebDriverWait(driver, 20)

        print("📱 앱 실행 및 메인 화면 대기 중...")
        
        # 메인 검색창 대기 (Resource ID 사용)
        wait.until(EC.visibility_of_element_located(
            (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().resourceId("mainSearch")')
        ))

        # ===================== 반복 측정 루프 =====================
        for i in range(1, REPEAT_COUNT + 1):
            measured_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[Running] {i}/{REPEAT_COUNT}회차 측정 진행 중...")

            try:
                # 1. 메인 검색창 찾기 (UiSelector)
                # resourceId("mainSearch")가 가장 정확하고 빠름
                search_input = wait.until(EC.visibility_of_element_located(
                    (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().resourceId("mainSearch")')
                ))
                
                search_input.click() 
                search_input.clear()
                search_input.send_keys(KEYWORD)
                
                # 2. 검색 버튼 찾기 (UiSelector)
                # 텍스트가 "검색"인 버튼 찾기
                search_btn = wait.until(EC.element_to_be_clickable(
                    (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().text("검색")')
                ))
                
                # [Time Start] 클릭 직전
                search_btn.click()
                start_time = time.time() 
                
                # 3. [초고속 완료 인식] Raw Loop + UiSelector
                # 목표: "검색 결과" 텍스트가 포함된 요소 감지
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
                
                print(f"   🎉 검색 완료! ({duration:.4f}초)")
                test_results.append([i, "성공", measured_at, duration])

                # ==========================================================
                # 4. 복귀 (하드웨어 뒤로가기)
                # ==========================================================
                print("   🔙 하드웨어 뒤로가기 키 입력")
                driver.press_keycode(4) 

                # 5. 메인 화면 복귀 확인 (검색창이 다시 뜰 때까지)
                wait.until(EC.visibility_of_element_located(
                    (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().resourceId("mainSearch")')
                ))
                
                time.sleep(1) # 안정성을 위한 짧은 대기

            except Exception as e:
                print(f"❌ {i}회차 실패: {e}")
                test_results.append([i, "실패", measured_at, 0])
                
                # 에러 발생 시 복구 시도 (뒤로가기)
                try: driver.press_keycode(4)
                except: pass
                time.sleep(2)

        # ===================== CSV 저장 (통일된 포맷) =====================
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
        file_name = f"gov24_search_perf_{REPEAT_COUNT}runs_{timestamp}.csv"
        
        # ✅ [핵심] 현재 폴더에 저장
        output_path = os.path.join(SCRIPT_DIR, file_name)

        if test_results:
            df = pd.DataFrame(test_results, columns=["회차", "상태", "측정시간", "검색반응속도(초)"])
            
            # 통계용 컬럼 추가 (포맷 통일)
            df["평균(초)"] = ""
            df["최소(초)"] = ""
            df["최대(초)"] = ""
            df["표준편차(초)"] = ""

            # 요약 행 추가
            summary = {
                "회차": "통계",
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
    run_gov24_search_test()