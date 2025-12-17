import time
import os
import csv
import statistics
from datetime import datetime
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# ===================== [설정 영역] =====================
APP_PACKAGE = "com.jobkorea.app"
APP_ACTIVITY = None  # 자동 감지
DEVICE_NAME = "Galaxy S25"
APPIUM_SERVER_URL = "http://127.0.0.1:4723"

# [계정 정보]
LOGIN_ID = "------"  # 아이디
LOGIN_PW = "-------"  # 비밀번호

# 반복 횟수
REPEAT_COUNT = 10

# [좌표 및 스크롤 설정]
POPUP_CLOSE_X = 957
POPUP_CLOSE_Y = 1856
scroll_num = 4
LOGOUT_X = 920
LOGOUT_Y = 1911

# ✅ 이 .py 파일이 있는 폴더
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def run_jobkorea_test():
    options = UiAutomator2Options()
    options.device_name = DEVICE_NAME
    options.app_package = APP_PACKAGE
    options.app_wait_activity = "*"
    options.automation_name = "UiAutomator2"
    options.no_reset = True
    options.new_command_timeout = 300
    
    # ⚡ [속도 최적화]
    options.set_capability("waitForIdleTimeout", 0) 
    options.set_capability("ignoreUnimportantViews", True)

    print(f"--- 잡코리아 로그인 성능 측정 (초고속 인식) ---")
    
    driver = webdriver.Remote(APPIUM_SERVER_URL, options=options)
    wait = WebDriverWait(driver, 20)
    
    # ✅ [회차, 상태("성공"/"실패"), 측정시간, 로그인반응속도(초)]
    test_results = []

    try:
        for i in range(1, REPEAT_COUNT + 1):
            print(f"\n🔄 [ {i} / {REPEAT_COUNT} ] 회차 수행 중...")
            measured_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            try:
                # ---------------------------------------------------------
                # 1. 메인 진입 & MY 클릭
                # ---------------------------------------------------------
                print("📲 [1] MY 메뉴 진입")
                try:
                    # 광고 등 임시 팝업 무시 시도
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located(
                            (AppiumBy.XPATH, "//*[@text='앗!뜨공' or contains(@content-desc, '앗!뜨공')]")
                        )
                    )
                except:
                    pass

                try:
                    wait.until(
                        EC.element_to_be_clickable((AppiumBy.ID, "com.jobkorea.app:id/rl_my"))
                    ).click()
                    print("   ✅ MY 버튼 클릭 완료")
                except:
                    print("   ❌ MY 버튼 찾기 실패")
                    test_results.append([i, "실패", measured_at, 0])
                    continue

                # ---------------------------------------------------------
                # 2. '다른 아이디로 로그인'
                # ---------------------------------------------------------
                try:
                    target_xpath = '//android.widget.TextView[@resource-id="com.jobkorea.app:id/tvAnotherLogin"]'
                    WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((AppiumBy.XPATH, target_xpath))
                    ).click()
                    print("   ✅ '다른 아이디로 로그인' 클릭")
                except:
                    pass

                # ---------------------------------------------------------
                # 3. 아이디 / 비밀번호 입력
                # ---------------------------------------------------------
                print("⌨️ [2] 정보 입력")
                try:
                    id_field = wait.until(
                        EC.presence_of_element_located(
                            (AppiumBy.ID, "com.jobkorea.app:id/editTextId")
                        )
                    )
                    id_field.clear()
                    id_field.send_keys(LOGIN_ID)
                    
                    pw_field = driver.find_element(
                        AppiumBy.ID, "com.jobkorea.app:id/editTextPassword"
                    )
                    pw_field.clear()
                    pw_field.send_keys(LOGIN_PW)
                except:
                    print("   ❌ 입력창 찾기 실패")
                    test_results.append([i, "실패", measured_at, 0])
                    continue

                try:
                    driver.hide_keyboard()
                except:
                    pass

                # ---------------------------------------------------------
                # 4. 로그인 수행 (측정)
                # ---------------------------------------------------------
                print("⏱️ [3] 로그인 시작")
                try:
                    login_btn = driver.find_element(
                        AppiumBy.ID, "com.jobkorea.app:id/bt_login"
                    )
                except:
                    print("   ❌ 로그인 버튼을 찾지 못했습니다.")
                    test_results.append([i, "실패", measured_at, 0])
                    continue

                
                login_btn.click()
                start_time = time.time()

                # ---------------------------------------------------------
                # 5. [초고속 완료 확인] Raw Loop + UiSelector
                # ---------------------------------------------------------
                # 감지 대상: '회원정보' 또는 '이력서 관리' 텍스트
                target_selector = 'new UiSelector().textContains("이력서 관리")'
                
                try:
                    while True:
                        # find_elements는 에러 없이 빈 리스트 반환 (가장 빠름)
                        res = driver.find_elements(AppiumBy.ANDROID_UIAUTOMATOR, target_selector)
                        
                        if res:
                            break # 찾았으면 즉시 루프 탈출
                        
                        # 안전장치: 30초 타임아웃
                        if time.time() - start_time > 30:
                            raise TimeoutException("로그인 완료 화면 대기 타임아웃")

                    end_time = time.time()
                    elapsed = end_time - start_time
                    
                    print(f"   🎉 로그인 성공! ({elapsed:.4f}초)")
                    test_results.append([i, "성공", measured_at, elapsed])
                    
                except TimeoutException:
                    print("   ❌ 로그인 시간 초과")
                    test_results.append([i, "실패", measured_at, 0])
                    continue

                # ---------------------------------------------------------
                # 6. 로그아웃 (팝업 좌표 닫기 -> 스크롤 -> 로그아웃 좌표 클릭)
                # ---------------------------------------------------------
                print("🚪 [4] 로그아웃 진행 (좌표 클릭)")
                
                # (1) 팝업 닫기 좌표 클릭
                time.sleep(1)
                print(f"   👆 팝업 닫기")
                try:
                    driver.tap([(POPUP_CLOSE_X, POPUP_CLOSE_Y)])
                    time.sleep(1)
                except Exception as e:
                    print(f"   ⚠️ 팝업 닫기 실패: {e}")

                # (2) 화면 끝까지 스크롤
                print(f"   📜 화면 최하단으로 스크롤 {scroll_num}회...")
                size = driver.get_window_size()
                for _ in range(scroll_num):
                    driver.swipe(
                        size['width'] * 0.5,
                        size['height'] * 0.8,
                        size['width'] * 0.5,
                        size['height'] * 0.2,
                        300
                    )
                time.sleep(1)

                # (3) 로그아웃 버튼 좌표 클릭
                print(f"   👆 로그아웃 버튼 클릭")
                driver.tap([(LOGOUT_X, LOGOUT_Y)])
                
                # (4) 확인 팝업 클릭
                try:
                    wait.until(
                        EC.element_to_be_clickable((AppiumBy.ID, "android:id/button1"))
                    ).click()
                    print("   ✅ 로그아웃 완료")
                except:
                    print("   ⚠️ 확인 팝업이 안 뜸 (좌표가 빗나갔을 수도 있음)")

                time.sleep(2)

            except Exception as e:
                print(f"   ❌ 예외 발생: {e}")
                test_results.append([i, "실패", measured_at, 0])
                continue

    except Exception as e:
        print(f"\n❌ 전체 에러 발생: {e}")

    finally:
        if driver:
            driver.quit()

    # ===================== CSV + 통계 저장 (통일 포맷) =====================
    print("\n" + "=" * 50)
    print("💾 로그인 성능 결과 CSV 저장 중...")

    # 성공 케이스만 통계 계산
    durations = [row[3] for row in test_results if row[1] == "성공" and row[3] > 0]

    if durations:
        avg = statistics.mean(durations)
        mn = min(durations)
        mx = max(durations)
        std = statistics.pstdev(durations) if len(durations) > 1 else 0.0
    else:
        avg = mn = mx = std = 0.0

    # ✅ 실행 파일과 같은 위치에 고정 파일명으로 저장
    output_path = os.path.join(SCRIPT_DIR, "jobkorea_login_result.csv")

    try:
        with open(output_path, mode='w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            # 공통 헤더
            writer.writerow([
                "회차", "상태", "측정시간", "로그인반응속도(초)",
                "평균(초)", "최소(초)", "최대(초)", "표준편차(초)"
            ])

            # 회차별 데이터
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
                f"{avg:.4f}" if durations else "",
                f"{mn:.4f}" if durations else "",
                f"{mx:.4f}" if durations else "",
                f"{std:.4f}" if durations else ""
            ])

        print(f"\n✅ CSV 저장 완료! 파일: {output_path}")

    except Exception as e:
        print(f"CSV 저장 중 오류: {e}")

    print("\n✅ 모든 테스트가 완료되었습니다.")

if __name__ == "__main__":
    run_jobkorea_test()