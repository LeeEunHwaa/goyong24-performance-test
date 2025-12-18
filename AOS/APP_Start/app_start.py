import time
import csv
import os
import statistics
from datetime import datetime
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy

# ==========================================
# [설정] 앱 및 타겟 정보 (UiSelector 사용)
# ==========================================
APPS = [
    {
        "name": "고용24",
        "package": "kr.or.keis.mo",
        "activity": "kr.or.keis.mo.MainActivity",
        "target_selector": 'new UiSelector().text("전체메뉴")' 
    },
    {
        "name": "정부24",
        "package": "kr.go.minwon.m",
        "activity": "kr.go.minwon.m.BrowserActivity",
        "target_selector": 'new UiSelector().resourceId("kr.go.minwon.m:id/kics_browser_webview")'
    },
    {
        "name": "잡코리아",
        "package": "com.jobkorea.app",
        "activity": None, 
        "target_selector": 'new UiSelector().text("앗!뜨공")'
    }
]

DEVICE_NAME = "Galaxy S25"
APPIUM_SERVER_URL = "http://127.0.0.1:4723"
REPEAT_COUNT = 10

# 파일 저장 경로 (.py 파일과 같은 위치)
SAVE_DIR = os.path.dirname(os.path.abspath(__file__))

def measure_3apps_detail_save():
    
    for app in APPS:
        print(f"\n" + "="*60)
        print(f"🚀 [{app['name']}] 앱 실행 측정 시작 ({REPEAT_COUNT}회)")
        print(f"="*60)

        options = UiAutomator2Options()
        options.device_name = DEVICE_NAME
        options.app_package = app['package']
        if app['activity']:
            options.app_activity = app['activity']
        options.app_wait_activity = "*"
        options.automation_name = "UiAutomator2"
        options.no_reset = True 
        
        # ⚡ [속도 최적화]
        options.set_capability("waitForIdleTimeout", 0)
        options.set_capability("ignoreUnimportantViews", True)

        driver = webdriver.Remote(APPIUM_SERVER_URL, options=options)
        
        # [초기화] 이전 실행 앱 종료
        try: driver.terminate_app(app['package'])
        except: pass
        time.sleep(1)
        
        # 결과 담을 리스트: [회차, 상태, 측정시간, 소요시간]
        test_results = []

        try:
            for i in range(1, REPEAT_COUNT + 1):
                print(f"🔄 [ {i}/{REPEAT_COUNT} ] 측정 중...")
                
                # 측정 시간 기록
                measured_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                try:
                    # 1. 앱 종료 (Cold Start)
                    driver.terminate_app(app['package'])
                    time.sleep(2)

                    # 2. 앱 실행
                    driver.activate_app(app['package'])

                    # 3. 측정 시작
                    start_time = time.time()

                    # 4. [초광속 인식] Raw Loop + UiSelector
                    target = app['target_selector']
                    
                    while True:
                        res = driver.find_elements(AppiumBy.ANDROID_UIAUTOMATOR, target)
                        if res:
                            break
                        
                        if time.time() - start_time > 20:
                            raise Exception("Timeout")

                    end_time = time.time()
                    duration = end_time - start_time
                    
                    print(f"   ✅ 성공: {duration:.4f} 초")
                    test_results.append([i, "성공", measured_at, duration])

                except Exception as e:
                    print(f"   ❌ 실패: {e}")
                    test_results.append([i, "실패", measured_at, 0])

                time.sleep(1)

        except Exception as e:
            print(f"❌ {app['name']} 전체 에러: {e}")

        finally:
            # 앱 종료 (Cleanup)
            try:
                print(f"   🧹 [Cleanup] {app['name']} 종료")
                driver.terminate_app(app['package'])
                time.sleep(1)
            except: pass

            if driver:
                driver.quit()

        # ==========================================
        # 4. 저장 (앱 별로 개별 파일 저장)
        # ==========================================
        durations = [row[3] for row in test_results if row[1] == "성공" and row[3] > 0]

        if durations:
            avg_val = statistics.mean(durations)
            max_val = max(durations)
            min_val = min(durations)
            std_val = statistics.pstdev(durations) if len(durations) > 1 else 0.0
        else:
            avg_val = max_val = min_val = std_val = 0.0

        # 파일명: android_앱이름_launch_result.csv
        file_name = f"android_{app['name']}_launch_result.csv"
        output_path = os.path.join(SAVE_DIR, file_name)
        
        print(f"\n💾 CSV 저장 경로: {output_path}")

        try:
            with open(output_path, mode='w', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file)
                # 헤더
                writer.writerow([
                    "회차", "상태", "측정시간", "앱실행반응속도(초)",
                    "평균(초)", "최소(초)", "최대(초)", "표준편차(초)"
                ])

                # 데이터 행
                for iteration, status, measured_at, duration in test_results:
                    writer.writerow([
                        iteration,
                        status,
                        measured_at,
                        f"{duration:.4f}" if duration > 0 else "",
                        "", "", "", "" # 통계 칸 비움
                    ])

                # 통계 행
                writer.writerow([
                    "통계", "", "", "",
                    f"{avg_val:.4f}" if durations else "",
                    f"{min_val:.4f}" if durations else "",
                    f"{max_val:.4f}" if durations else "",
                    f"{std_val:.4f}" if durations else ""
                ])
            print("✅ 저장 완료")
            
        except Exception as e:
            print(f"❌ 파일 저장 실패: {e}")

    print("\n✅ 모든 앱 측정 완료.")

if __name__ == "__main__":
    measure_3apps_detail_save()
