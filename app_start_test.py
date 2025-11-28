import time
import statistics
import pandas as pd
from datetime import datetime
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==========================================
# [설정] 잡코리아 Activity를 None으로 변경 (자동 찾기)
# ==========================================
APPS = [
    {
        "name": "고용24",
        "package": "kr.or.keis.mo",
        "activity": "kr.or.keis.mo.MainActivity",
        "type": "XPATH",
        "target": "//*[@text='전체메뉴']"
    },
    {
        "name": "정부24",
        "package": "kr.go.minwon.m",
        "activity": "kr.go.minwon.m.BrowserActivity",
        "type": "ID",
        "target": "kr.go.minwon.m:id/kics_browser_webview"
    },
    {
        "name": "잡코리아",
        "package": "com.jobkorea.app",
        "activity": None,  # [중요] 여기를 None으로 설정! (Appium이 알아서 정문 찾음)
        "type": "ID",
        "target": "com.jobkorea.app:id/mainLogo"
    }
]

DEVICE_NAME = "Galaxy S25"
APPIUM_SERVER_URL = "http://127.0.0.1:4723"

#반복 횟수
REPEAT_COUNT = 2

def clean_background_apps(driver):
    print("   🧹 [Clean Up] 백그라운드 앱 정리 중...")
    for target_app in APPS:
        try:
            driver.terminate_app(target_app['package'])
        except:
            pass
    time.sleep(1) 

def measure_3apps_fair_launch_v2():
    all_results = [] 

    for app in APPS:
        print(f"\n" + "="*60)
        print(f"🚀 [{app['name']}] 실행 성능 측정 시작 ({REPEAT_COUNT}회)")
        print(f"="*60)

        options = UiAutomator2Options()
        options.device_name = DEVICE_NAME
        options.app_package = app['package']
        
        # [수정] activity가 지정된 경우에만 옵션에 추가
        if app['activity']:
            options.app_activity = app['activity']
        
        # [추가] 어떤 화면이 뜨든 일단 기다려주는 관용 옵션
        options.app_wait_activity = "*"
        
        options.automation_name = "UiAutomator2"
        options.no_reset = True 

        driver = webdriver.Remote(APPIUM_SERVER_URL, options=options)
        wait = WebDriverWait(driver, 30)
        
        # 공정성 확보를 위한 클린업
        clean_background_apps(driver)
        
        execution_times = []

        try:
            for i in range(1, REPEAT_COUNT + 1):
                print(f"🔄 [ {i}/{REPEAT_COUNT} ] 측정 중...")

                # 1. 앱 종료 (Cold Start)
                driver.terminate_app(app['package'])
                time.sleep(2)

                # 2. 측정 시작
                start_time = time.time()
                
                # [수정] activate_app은 패키지명만 있으면 알아서 정문으로 들어갑니다
                driver.activate_app(app['package'])

                # 3. 로딩 완료 대기
                if app['type'] == "XPATH":
                    wait.until(EC.presence_of_element_located((AppiumBy.XPATH, app['target'])))
                else:
                    wait.until(EC.presence_of_element_located((AppiumBy.ID, app['target'])))

                end_time = time.time()
                
                elapsed = end_time - start_time
                execution_times.append(elapsed)
                print(f"   ✅ {elapsed:.4f} 초")
                time.sleep(1)

            # 통계 계산
            if execution_times:
                avg = statistics.mean(execution_times)
                std = statistics.stdev(execution_times) if len(execution_times) > 1 else 0
                
                result = {
                    "앱 이름": app['name'],
                    "평균(초)": round(avg, 4),
                    "최소(초)": round(min(execution_times), 4),
                    "최대(초)": round(max(execution_times), 4),
                    "표준편차": round(std, 4)
                }
                all_results.append(result)
                print(f"📊 {app['name']} 평균: {avg:.4f}초")

        except Exception as e:
            print(f"❌ {app['name']} 테스트 중 에러: {e}")

        finally:
            driver.quit()

    # CSV 저장
    print("\n" + "="*50)
    print("💾 CSV 저장 중...")
    
    if all_results:
        df = pd.DataFrame(all_results)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"fair_perf_result_v2_{timestamp}.csv"
        df.to_csv(file_name, index=False, encoding='utf-8-sig')
        print(f"✅ 저장 완료! 파일명: {file_name}")
        print(df) 
    else:
        print("❌ 저장할 데이터가 없습니다.")
    
    input("\n엔터 키를 누르면 종료합니다...")

if __name__ == "__main__":
    measure_3apps_fair_launch_v2()
