from selenium.common.exceptions import TimeoutException
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from appium.options.android import UiAutomator2Options
from appium import webdriver

import pandas as pd
from datetime import datetime
import time
import statistics
import os  # ✅ [3] 경로 저장을 위해 추가

# ===================== 설정 =====================
APP_PACKAGE = "kr.or.keis.mo"

# 금융인증서 비밀번호 6자리
CERT_PASSWORD = "------"

APPIUM_SERVER_URL = "http://127.0.0.1:4723"
DEVICE_NAME = "Android"

# 반복 횟수
REPEAT_COUNT = 10   # 필요하면 숫자만 바꿔서 사용


# ===================== 공통 유틸 함수 =====================
def tap_by_coordinates(driver, x, y):
    """좌표(x, y)를 탭 - Appium 2 방식"""
    try:
        driver.execute_script("mobile: clickGesture", {"x": x, "y": y})
        print(f"   ✅ 좌표 탭 ({x}, {y})")
    except Exception as e:
        print(f"   ❌ 좌표 탭 실패: {e}")


def close_one_popup_if_exists(driver, wait_sec=2):
    """현재 떠 있는 팝업이 있으면 확인 버튼을 한 번 눌러 닫음"""
    try:
        ok_btn = WebDriverWait(driver, wait_sec).until(
            EC.element_to_be_clickable((AppiumBy.ID, "android:id/button1"))
        )
        ok_btn.click()
        print("   ✅ 팝업 버튼(android:id/button1) 클릭")
        return True
    except TimeoutException:
        pass

    try:
        ok_btn2 = WebDriverWait(driver, wait_sec).until(
            EC.element_to_be_clickable(
                (AppiumBy.ANDROID_UIAUTOMATOR,
                 'new UiSelector().className("android.widget.Button").textContains("확인")')
            )
        )
        ok_btn2.click()
        print("   ✅ 팝업 버튼('확인') 클릭")
        return True
    except TimeoutException:
        return False


def close_all_extra_popups(driver, max_count=5):
    """로그인 이후 추가로 뜨는 팝업들을 최대 max_count개까지 모두 닫는다."""
    for i in range(max_count):
        closed = close_one_popup_if_exists(driver, wait_sec=2)
        if not closed:
            if i == 0:
                print("   ℹ️ 추가 팝업 없음")
            else:
                print(f"   ℹ️ 더 이상 팝업 없음 (총 {i}개 닫음)")
            break
        time.sleep(1)


# ===================== 로그인 진입 =====================
def open_login_section(driver, wait):
    """
    '전체메뉴' → '로그인을 해 주세요' 버튼까지 이동.
    """
    print("📲 [1단계] '로그인을 해 주세요'로 이동")

    try:
        # 이미 전체메뉴 화면에 있고 '로그인을 해 주세요'가 보이는 경우
        print("   ℹ️ '로그인을 해 주세요'가 바로 보이는지 확인")
        login_please = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable(
                (AppiumBy.ACCESSIBILITY_ID, "로그인을 해 주세요")
            )
        )
        print("   ✅ 전체메뉴 화면에서 바로 '로그인을 해 주세요' 발견")
    except TimeoutException:
        # 메인에서 전체메뉴 버튼 클릭 후 다시 찾기
        print("   ℹ️ '로그인을 해 주세요'가 안 보여서 전체메뉴부터 클릭")
        all_menu_btn = wait.until(
            EC.element_to_be_clickable(
                (AppiumBy.XPATH, "//android.widget.Button[@text='전체메뉴']")
            )
        )
        all_menu_btn.click()
        print("   ✅ '전체메뉴' 버튼 클릭")

        login_please = wait.until(
            EC.element_to_be_clickable(
                (AppiumBy.ACCESSIBILITY_ID, "로그인을 해 주세요")
            )
        )

    login_please.click()
    print("   ✅ '로그인을 해 주세요' 클릭 완료")


def tap_certificate_menu(driver, wait):
    """
    로그인 수단 화면에서:
    1) 4초 대기 후 좌표 (540, 1800) 탭 → '금융인증서' 버튼 클릭
    2) 금융인증서 화면 로딩을 위해 3초 대기
    3) 좌표 (509, 1246) 탭 → '000님의 금융인증서' 카드 선택
    이후 비밀번호 입력 단계로 넘어감.
    """
    print("💳 [2단계] '금융인증서' 버튼 및 인증서 카드 선택 (좌표)")

    # 1) 로그인 수단 화면 로딩 대기 후 금융인증서 버튼 클릭
    print("⏳ 로그인수단 화면 로딩을 위해 3초 대기...")
    time.sleep(3)
    tap_by_coordinates(driver, 540, 1800)
    print("   ✅ '금융인증서' 버튼 클릭")

    # 2) 금융인증서 앱 화면 로딩 대기
    print("⏳ 금융인증서 선택 화면 로딩을 위해 3초 대기...")
    time.sleep(3)

    # 3) 인증서 카드(이은화님의 금융인증서) 클릭
    tap_by_coordinates(driver, 509, 1246)
    print("   ✅ 인증서 카드 클릭")


# ===================== 비밀번호 입력 =====================
def input_certificate_password(driver, wait):
    """
    금융인증서 비밀번호 6자리 입력.
    ✅ [1] 6번째 숫자를 누른 '직후'에 시간 측정 시작.
    """
    print("⌨️ [3단계] 금융인증서 비밀번호 입력")

    # 보안 키패드 준비될 때까지 대기
    try:
        wait.until(
            EC.presence_of_element_located(
                (AppiumBy.ANDROID_UIAUTOMATOR,
                 'new UiSelector().className("android.widget.Button").description("0")')
            )
        )
        print("   ✅ 보안 키패드 로딩 확인")
    except TimeoutException as e:
        print("   ❌ 보안 키패드를 찾지 못했습니다.")
        raise RuntimeError("보안 키패드가 보이지 않습니다.") from e

    digits = list(CERT_PASSWORD)
    start_time = None

    for idx, d in enumerate(digits):
        print(f"   ▶ 숫자 입력 시도 ({idx+1}/{len(digits)})")
        btn = wait.until(
            EC.element_to_be_clickable((AppiumBy.ACCESSIBILITY_ID, d))
        )

        # 클릭 먼저 수행
        btn.click()
        
        # ✅ [1] 수정됨: 클릭 직후에 시간 측정 (마지막 숫자인 경우)
        if idx == len(digits) - 1:
            start_time = time.time()
            print(f"   ⏱️ 측정 시작 (6번째 숫자 클릭 직후)")
        
        # print(f"   ✅ 숫자 입력 완료")

    if start_time is None:
        raise RuntimeError("타이머 시작 시점을 설정하지 못했습니다.")

    return start_time


# ===================== 로그아웃 =====================
def logout_for_next_run(driver, wait):
    """다음 회차를 위해 로그인 상태라면 로그아웃까지 수행."""
    print("🚪 [마무리] 다음 회차를 위한 로그아웃 수행")

    try:
        all_menu_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (AppiumBy.XPATH, "//android.widget.Button[@text='전체메뉴']")
            )
        )
        all_menu_btn.click()
        print("   ✅ '전체메뉴' 버튼 클릭")
    except TimeoutException:
        print("   ℹ️ '전체메뉴' 버튼을 찾지 못했습니다. 이미 전체메뉴 화면일 수도 있음")

    try:
        logout_label = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(
                (AppiumBy.ANDROID_UIAUTOMATOR,
                 'new UiSelector().text("로그아웃")')
            )
        )
        print("   ✅ '로그아웃' 라벨 발견")
    except TimeoutException:
        print("   ℹ️ '로그아웃' 텍스트를 찾지 못했습니다. (이미 로그아웃 상태일 수 있음)")
        return

    try:
        logout_label.click()
        print("   ✅ '로그아웃' 클릭")
    except Exception:
        try:
            driver.execute_script("mobile: clickGesture", {"elementId": logout_label.id})
            print("   ✅ clickGesture로 '로그아웃' 클릭")
        except Exception as e:
            print(f"   ❌ '로그아웃' 클릭 실패: {e}")
            return

    closed = close_one_popup_if_exists(driver, wait_sec=3)
    if not closed:
        print("   ℹ️ 별도 로그아웃 확인 팝업 없음")

    time.sleep(2)


# ===================== 로그인 시도 1회 =====================
def perform_login_once(driver, wait):
    """
    1) 전체메뉴 → '로그인을 해 주세요'
    2) 금융인증서 버튼 클릭 후 인증서 카드 클릭
    3) 비밀번호 6자리 입력 (6번째 숫자 클릭 직후 타이머 시작)
    4) ✅ [2] 초고속 인식: 팝업 메시지(android:id/message)가 뜨는 순간 측정 종료
    5) 팝업 정리 및 로그아웃
    """
    print("🚀 [로그인 시나리오] 시작")

    # 1단계
    open_login_section(driver, wait)

    # 2단계
    tap_certificate_menu(driver, wait)

    # 3단계 (입력 및 타이머 시작)
    start_time = input_certificate_password(driver, wait)

    # 4단계: ✅ [2] 초고속 완료 인식 (Raw Loop + UiSelector)
    print("⏳ [4단계] 로그인 결과 팝업 대기 (초고속 인식)...")
    
    # 기존 코드에서 팝업 메시지 ID: android:id/message
    target_selector = 'new UiSelector().resourceId("android:id/message")'
    
    try:
        while True:
            # find_elements는 에러 없이 빈 리스트 반환 (가장 빠른 방식)
            res = driver.find_elements(AppiumBy.ANDROID_UIAUTOMATOR, target_selector)
            
            if res:
                break # 찾았으면 즉시 루프 탈출
            
            # 안전장치: 30초 타임아웃
            if time.time() - start_time > 30:
                raise TimeoutException("로그인 팝업 대기 타임아웃 (30초)")

        end_time = time.time()
        
    except TimeoutException as e:
        print("   ❌ 로그인 결과 팝업을 찾지 못했습니다.")
        raise RuntimeError("로그인 결과 팝업을 찾지 못했습니다.") from e

    elapsed = end_time - start_time
    print(f"\n🎉 로그인 응답 수신! 반응 속도: {elapsed:.4f} 초")

    # 팝업 정리
    close_one_popup_if_exists(driver, wait_sec=1)
    close_all_extra_popups(driver, max_count=4)

    # 로그아웃
    logout_for_next_run(driver, wait)

    time.sleep(2)
    return elapsed


# ===================== 메인 테스트 루프 =====================
def test_login_security_safe(repeat_count=REPEAT_COUNT):
    """
    금융인증서 로그인 반복 테스트.
    """
    options = UiAutomator2Options()
    options.device_name = DEVICE_NAME
    options.app_package = APP_PACKAGE
    options.app_activity = ".MainActivity"
    options.automation_name = "UiAutomator2"
    options.new_command_timeout = 300
    options.no_reset = True
    
    # ⚡ [속도 최적화 옵션 추가]
    options.set_capability("waitForIdleTimeout", 0) 
    options.set_capability("ignoreUnimportantViews", True)

    print("--- [금융인증서] 로그인 성능 테스트 (반복) ---")
    driver = webdriver.Remote(APPIUM_SERVER_URL, options=options)
    wait = WebDriverWait(driver, 20)

    results = []
    valid_times = []

    try:
        for i in range(1, repeat_count + 1):
            print("\n==============================")
            print(f"🔁 로그인 시도 {i}/{repeat_count}")
            print("==============================")

            measured_at = datetime.now().strftime("%Y-%m-%d %H:%M")

            try:
                elapsed = perform_login_once(driver, wait)
                elapsed_rounded = round(elapsed, 4)
                valid_times.append(elapsed)

                results.append(
                    {
                        "회차": i,
                        "측정시각": measured_at,
                        "로그인반응속도(초)": elapsed_rounded,
                        "평균(초)": "",
                        "최소(초)": "",
                        "최대(초)": "",
                        "표준편차(초)": "",
                    }
                )
            except Exception as e:
                print(f"   ❌ 로그인 시도 {i} 중 오류 발생: {e}")
                results.append(
                    {
                        "회차": i,
                        "측정시각": measured_at,
                        "로그인반응속도(초)": "",
                        "평균(초)": "",
                        "최소(초)": "",
                        "최대(초)": "",
                        "표준편차(초)": "",
                    }
                )

            time.sleep(3)

    finally:
        driver.quit()
        print("\n📴 드라이버 종료")

    # ----- CSV + 통계 -----
    if results:
        df = pd.DataFrame(
            results,
            columns=["회차", "측정시각", "로그인반응속도(초)",
                     "평균(초)", "최소(초)", "최대(초)", "표준편차(초)"]
        )

        if valid_times:
            avg_time = statistics.mean(valid_times)
            min_time = min(valid_times)
            max_time = max(valid_times)
            std_time = statistics.stdev(valid_times) if len(valid_times) >= 2 else 0.0

            summary_row = {
                "회차": "요약",
                "측정시각": "",
                "로그인반응속도(초)": "",
                "평균(초)": round(avg_time, 4),
                "최소(초)": round(min_time, 4),
                "최대(초)": round(max_time, 4),
                "표준편차(초)": round(std_time, 4),
            }
            df = pd.concat([df, pd.DataFrame([summary_row])], ignore_index=True)

            print("\n📊 통계 요약")
            print(f"   - 평균  : {avg_time:.4f} 초")
            print(f"   - 최소  : {min_time:.4f} 초")
            print(f"   - 최대  : {max_time:.4f} 초")
            print(f"   - 표준편차: {std_time:.4f} 초")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"work24_cert_login_perf_{repeat_count}runs_{timestamp}.csv"
        
        # ✅ [3] 현재 폴더에 저장 (os.path 사용)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        save_path = os.path.join(current_dir, file_name)
        
        df.to_csv(save_path, index=False, encoding="utf-8-sig")

        print(f"\n✅ CSV 저장 완료! 경로: {save_path}")
        print(df)
    else:
        print("\nℹ️ 저장할 측정 결과가 없어 CSV는 생성되지 않았습니다.")

    print("\n✅ 금융인증서 로그인 반복 테스트 및 CSV 저장까지 모두 완료되었습니다.")

if __name__ == "__main__":
    test_login_security_safe()