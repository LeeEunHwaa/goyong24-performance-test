from selenium.common.exceptions import TimeoutException
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from appium.options.android import UiAutomator2Options
from appium import webdriver
import os

import pandas as pd
from datetime import datetime
import time

# ===================== 설정 =====================
APP_PACKAGE = "kr.go.minwon.m"
APP_ACTIVITY = "kr.go.minwon.m.BrowserActivity"

APPIUM_SERVER_URL = "http://127.0.0.1:4723"
DEVICE_NAME = "Android"

# 🔐 금융인증서 6자리 비밀번호
CERT_PW = "------" 

# 반복 횟수
REPEAT_COUNT = 10

# 메인화면 기준 로그인 버튼 좌표
LOGIN_BTN_X = 813
LOGIN_BTN_Y = 216

# 전체메뉴 버튼 좌표
MENU_BTN_X = 985
MENU_BTN_Y = 266


# ===================== 공통 유틸 함수 =====================
def tap_by_coordinates(driver, x, y, duration_ms=200):
    """좌표 탭: swipe를 start=end로 주면 탭처럼 동작"""
    try:
        driver.swipe(x, y, x, y, duration_ms)
    except Exception as e:
        print(f"   ❌ 좌표 탭 실패: {e}")
        raise


# ===================== 정부24 전용 동작 함수 =====================
def open_login_section(driver):
    """메인 화면에서 로그인 버튼을 좌표 탭"""
    print("📲 [1단계] 메인화면 로그인 버튼 탭")

    # 메인화면 로딩 확인용 요소 (혜택알림)
    # 여기는 로그인 전이라 속도 측정이 아니므로 안전하게 wait 사용
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().descriptionContains("혜택알림")')
            )
        )
        print("   ✅ 메인화면 로드 확인 완료")
    except TimeoutException:
        print("   ⚠️ 메인화면 확인용 요소를 찾지 못했습니다. 그래도 로그인 버튼 탭 시도")

    try:
        time.sleep(1)
        tap_by_coordinates(driver, LOGIN_BTN_X, LOGIN_BTN_Y)
        print(f"   ✅ ({LOGIN_BTN_X}, {LOGIN_BTN_Y}) 위치 로그인 버튼 탭 완료")
    except Exception as e:
        print(f"   ❌ 로그인 버튼 좌표 탭 실패: {e}")
        raise

    time.sleep(2)


def tap_cert_login(driver):
    """로그인 선택 화면에서 '금융인증서' 경로로 진입"""
    print("📲 [2단계] '금융인증서' 로그인 선택")

    # 1) '금융인증서' 버튼 탭
    try:
        print("   📍 (780, 1552) 금융인증서 버튼 탭")
        tap_by_coordinates(driver, 780, 1552)
    except Exception as e:
        print(f"   ❌ 금융인증서 버튼 탭 실패: {e}")
        raise

    time.sleep(2)

    # 2) 비밀번호 입력 영역 탭
    try:
        print("   📍 (500, 1172) 비밀번호 입력 영역 탭")
        tap_by_coordinates(driver, 500, 1172)
    except Exception as e:
        print(f"   ❌ 비밀번호 입력 영역 탭 실패: {e}")
        raise

    time.sleep(1)


def enter_cert_pw_and_wait_menu(driver, wait, attempt_idx=None):
    """
    [측정 구간]
    - 시작: 6번째 숫자 클릭 직후
    - 끝: 메인화면 요소('혜택알림')가 감지되는 순간 (초고속 인식)
    """
    print("🔐 [3단계] 금융인증서 비밀번호 입력 및 메인화면 대기(측정)")

    start_time = None

    # 1) 자동 입력 시도
    pw = CERT_PW.strip()
    if pw and pw.isdigit() and len(pw) == 6:
        try:
            print("   🤖 금융인증서 비밀번호 자동 입력 시도")
            for idx, digit in enumerate(pw):
                # UiSelector 사용
                selector = f'new UiSelector().description("{digit}")'
                btn = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((AppiumBy.ANDROID_UIAUTOMATOR, selector))
                )
                btn.click()
                # print(f"      ✅ {idx + 1}번째 숫자 클릭")

                # 6번째(마지막) 숫자 클릭 직후 측정 시작
                if idx == len(pw) - 1:
                    start_time = time.time()
                    print("⏱ 측정 시작 (6번째 숫자 클릭 직후)")
        except Exception as e:
            print(f"   ⚠️ 비밀번호 자동 입력 중 오류: {e}")
            start_time = None
    else:
        print("   ⚠️ CERT_PW 값이 비어있거나 6자리 숫자가 아닙니다.")

    # 2) 수동 입력 fallback
    if start_time is None:
        input("      휴대폰에서 입력 후 마지막 숫자 누를 때 Enter...")
        start_time = time.time()

    # -------------------------------------------------------------
    # 🔥 [수정됨] 3) 초고속 완료 인식 (Raw Loop + UiSelector)
    # -------------------------------------------------------------
    try:
        # 기존 XPath: '//android.widget.ImageView[@content-desc="혜택알림 메뉴 바로가기 링크"]'
        # -> UiSelector로 변경 (훨씬 빠름)
        target_selector = 'new UiSelector().descriptionContains("혜택알림")'
        
        while True:
            # find_elements는 에러 없이 빈 리스트 반환 (try-catch 오버헤드 제거)
            res = driver.find_elements(AppiumBy.ANDROID_UIAUTOMATOR, target_selector)
            
            if res:
                break # 찾았으면 즉시 탈출
            
            # 안전장치: 30초 타임아웃
            if time.time() - start_time > 30:
                raise TimeoutException("메인화면 로딩 타임아웃 (30초)")

        end_time = time.time()
        elapsed = end_time - start_time

        print("🎉 메인화면 로드 확인 (UiSelector 인식)")
        print(f"⏱ 측정 시간: {elapsed:.4f} 초")

        # 측정이 끝난 뒤 전체메뉴를 실제로 한 번 열어 둔다.
        try:
            print(f"   📍 ({MENU_BTN_X}, {MENU_BTN_Y}) 전체메뉴 탭 (로그아웃 준비)")
            tap_by_coordinates(driver, MENU_BTN_X, MENU_BTN_Y)
            time.sleep(2)
        except Exception as e:
            print(f"   ⚠️ 전체메뉴 탭 중 오류 (그래도 측정값은 유지): {e}")

        status_msg = "성공"
        return elapsed, status_msg

    except TimeoutException:
        end_time = time.time()
        elapsed = end_time - start_time
        print("   ⚠️ 메인화면 확인용 요소를 찾지 못했습니다.(타임아웃)")
        status_msg = "타임아웃"
        return elapsed, status_msg


def logout_to_main(driver):
    """
    [로그아웃] 스크롤 2번 → 로그아웃 버튼 좌표 탭 → 메인화면 복귀 확인
    """
    print("\n🔚 [로그아웃] 진행")

    try:
        # 1) 스크롤 두 번
        print("   ↕ 스크롤 1회")
        driver.swipe(1040, 1825, 1040, 242, 500)
        time.sleep(2)

        print("   ↕ 스크롤 2회")
        driver.swipe(1040, 1825, 1040, 242, 500)
        time.sleep(2)

        # 2) 로그아웃 버튼 좌표 탭
        print("   📍 로그아웃 좌표 탭 (502, 1811)")
        tap_by_coordinates(driver, 502, 1811)

        # 3) 메인화면 복귀 확인
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().descriptionContains("혜택알림")')
                )
            )
            print("   ✅ 로그아웃 후 메인화면 복귀 확인")
        except TimeoutException:
            print("   ⚠️ 로그아웃 후 메인화면 요소를 찾지 못했습니다.")

    except Exception as e:
        print(f"   ❌ 로그아웃 동작 중 오류 발생: {e}")
        raise


# ===================== 로그인 1회 시나리오 =====================
def perform_login_once(driver, wait, attempt_idx=None):
    print("\n🚀 [로그인 시나리오] 1회 시작")
    open_login_section(driver)
    tap_cert_login(driver)
    elapsed, status_msg = enter_cert_pw_and_wait_menu(driver, wait, attempt_idx)
    return elapsed, status_msg


# ===================== 메인 테스트 + CSV 저장 =====================
def test_login_minwon(repeat_count=REPEAT_COUNT):
    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.device_name = DEVICE_NAME
    options.app_package = APP_PACKAGE
    options.app_activity = APP_ACTIVITY
    options.automation_name = "UiAutomator2"
    options.new_command_timeout = 300
    options.no_reset = True 

    # 🔥 [추가됨] 속도 최적화 옵션
    options.set_capability("waitForIdleTimeout", 0)       # 딜레이 없이 강제 실행
    options.set_capability("ignoreUnimportantViews", True) # DOM 경량화

    print("--- [정부24] 금융인증서 로그인 성능 테스트 (초고속 인식) ---")
    driver = webdriver.Remote(APPIUM_SERVER_URL, options=options)
    wait = WebDriverWait(driver, 20)

    results = []

    try:
        for i in range(1, repeat_count + 1):
            print("\n" + "=" * 60)
            print(f"🔁 로그인 시도 {i}/{repeat_count}")
            print("=" * 60)

            elapsed, status_msg = perform_login_once(driver, wait, attempt_idx=i)

            results.append(
                {
                    "회차": i,
                    "측정시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "로그인반응속도(초)": round(elapsed, 4),
                    "팝업메시지": status_msg,
                }
            )

            if i < repeat_count:
                print("\n📴 [다음 회차 준비] 로그아웃 진행")
                try:
                    logout_to_main(driver)
                except Exception as e:
                    print(f"   ❌ 로그아웃 중 오류 발생: {e}")
                    break

    finally:
        print("\n🧹 드라이버 종료")
        driver.quit()

    # ===================== CSV 저장 =====================
    if results:
        df = pd.DataFrame(results)

        # 요약 행 추가 (평균, 최소, 최대, 표준편차)
        valid_elapsed = [row["로그인반응속도(초)"] for row in results if row["팝업메시지"] == "성공"]
        
        if valid_elapsed:
            mean_val = sum(valid_elapsed) / len(valid_elapsed)
            min_val = min(valid_elapsed)
            max_val = max(valid_elapsed)
            std_val = (sum((x - mean_val) ** 2 for x in valid_elapsed) / len(valid_elapsed)) ** 0.5
        else:
            mean_val = min_val = max_val = std_val = 0.0

        summary_row = {
            "회차": "통계",
            "측정시각": "-",
            "로그인반응속도(초)": "",
            "평균(초)": round(mean_val, 4),
            "최소(초)": round(min_val, 4),
            "최대(초)": round(max_val, 4),
            "표준편차(초)": round(std_val, 4),
        }
        
        if "팝업메시지" in df.columns:
            df = df.drop(columns=["팝업메시지"])

        df = pd.concat([df, pd.DataFrame([summary_row])], ignore_index=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"gov24_certficate_login_{repeat_count}runs_{timestamp}.csv"

        # 🔥 [핵심 수정] 현재 파일(.py)이 있는 폴더 경로 가져오기
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 🔥 폴더 경로 + 파일 이름 합치기
        save_path = os.path.join(current_dir, file_name)

        # 합친 경로(save_path)로 저장
        df.to_csv(save_path, index=False, encoding="utf-8-sig")

        print(f"\n✅ CSV 저장 완료! 경로: {save_path}")
        print(df)
    else:
        print("ℹ️ 저장할 데이터가 없습니다.")

if __name__ == "__main__":
    test_login_minwon()