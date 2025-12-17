from selenium.common.exceptions import TimeoutException
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from appium.options.android import UiAutomator2Options
from appium import webdriver

import pandas as pd
from datetime import datetime
import time
import os  # [추가] 파일 경로 설정을 위해 필요

# ===================== 설정 =====================
# 정부24 패키지 / 액티비티
APP_PACKAGE = "kr.go.minwon.m"
APP_ACTIVITY = "kr.go.minwon.m.BrowserActivity"

APPIUM_SERVER_URL = "http://127.0.0.1:4723"
DEVICE_NAME = "Android"

# 테스트에 사용할 아이디 / 비밀번호
LOGIN_ID = "sh200220"       # ← 정부24 아이디
LOGIN_PW = "!sh17052002"       # ← 정부24 비밀번호

# 반복 횟수
REPEAT_COUNT = 10

# 메인화면 기준 로그인 버튼 좌표
LOGIN_BTN_X = 813
LOGIN_BTN_Y = 216

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

    # 메인화면 로딩 확인용 요소 (혜택알림) - 로그인 전이라 안전하게 Wait 사용
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().descriptionContains("혜택알림")')
            )
        )
        print("   ✅ 메인화면 로드 확인 완료")
    except TimeoutException:
        print("   ⚠️ 메인화면 확인용 요소를 찾지 못했습니다. 그래도 로그인 버튼 탭 시도")

    # 로그인 버튼 탭
    try:
        tap_by_coordinates(driver, LOGIN_BTN_X, LOGIN_BTN_Y)
        print(f"   ✅ ({LOGIN_BTN_X}, {LOGIN_BTN_Y}) 위치 로그인 버튼 탭 완료")
    except Exception as e:
        print(f"   ❌ 로그인 버튼 좌표 탭 실패: {e}")
        raise

    time.sleep(2)


def tap_id_login(driver, wait):
    """'아이디 로그인' 선택"""
    print("📲 [2단계] '아이디 로그인' 선택")

    # 화면 스크롤
    try:
        print("   ↕ 화면 스크롤 (1041, 1822) → (1041, 446)")
        driver.swipe(1041, 1822, 1041, 446, 500)   # 휴대폰 기종에 따라 좌표 수정 필요
        time.sleep(1)
    except Exception as e:
        print(f"   ⚠️ 스크롤 중 오류 발생: {e}")

    # '아이디 로그인' 버튼 클릭
    try:
        btn = wait.until(
            EC.element_to_be_clickable(
                (AppiumBy.XPATH, '//android.view.View[@content-desc="아이디 로그인"]')
            )
        )
        btn.click()
        print("   ✅ '아이디 로그인' 버튼 클릭 완료")
    except TimeoutException as e:
        print("   ❌ '아이디 로그인' 버튼을 찾지 못했습니다.")
        raise RuntimeError("'아이디 로그인' 진입에 실패했습니다.") from e

    time.sleep(1)


def fill_id(driver, wait):
    """아이디 입력 + '다음' 버튼 클릭"""
    print("⌨️ [3단계] 아이디 입력")

    # 아이디 입력
    try:
        id_input = wait.until(
            EC.element_to_be_clickable(
                (AppiumBy.XPATH, '//android.widget.EditText[@resource-id="input_id"]')
            )
        )
        id_input.clear()
        id_input.send_keys(LOGIN_ID)
        print("   ✅ 아이디 입력 완료")
    except TimeoutException as e:
        print("   ❌ 아이디 입력창을 찾지 못했습니다.")
        raise RuntimeError("아이디 입력창을 찾지 못했습니다.") from e

    # '다음' 버튼
    try:
        next_btn = wait.until(
            EC.element_to_be_clickable(
                (AppiumBy.XPATH, '//android.widget.Button[@text="다음"]')
            )
        )
        next_btn.click()
        print("   ✅ '다음' 버튼 클릭 완료")
    except TimeoutException as e:
        print("   ❌ '다음' 버튼을 찾지 못했습니다.")
        raise RuntimeError("'다음' 버튼을 찾지 못했습니다.") from e

    time.sleep(1)


def fill_pwd_and_security(driver, wait, attempt_idx=None):
    """
    비밀번호 자동 입력 + 보안숫자(캡차)는 사용자에게 콘솔로 입력받아 진행
    """
    print("⌨️ [4단계] 비밀번호 / 보안숫자 입력")

    # 1) 비밀번호 입력
    try:
        pw_input = wait.until(
            EC.element_to_be_clickable(
                (AppiumBy.XPATH, '//android.widget.EditText[@resource-id="input_pwd"]')
            )
        )
        pw_input.clear()
        pw_input.send_keys(LOGIN_PW)
        print("   ✅ 비밀번호 입력 완료")
    except TimeoutException as e:
        print("   ❌ 비밀번호 입력창을 찾지 못했습니다.")
        raise RuntimeError("비밀번호 입력창을 찾지 못했습니다.") from e

    # 2) 콘솔에서 보안숫자 입력 받고, 엔터 칠 때까지 대기
    attempt_str = f"{attempt_idx}회차" if attempt_idx is not None else ""

    print("\n----------------------------------------")
    print("📌 비밀번호 아래 이미지에 보이는 '보안숫자'를 입력해야 합니다.")
    print("   휴대폰 화면의 숫자를 보고, 콘솔에 그대로 입력해 주세요.")
    if attempt_str:
        print(f"   현재 로그인 시도: {attempt_str}")
    security_num = input("👉 보안숫자(예: 940483)를 입력 후 Enter: ").strip()
    print("----------------------------------------\n")

    if not security_num:
        print("   ℹ️ 콘솔 입력 없음 → 휴대폰 직접 입력 간주")
        return

    # 3) 보안숫자 입력창 찾기
    sec_input = None

    # 3-1) 기존 resource-id 시도
    try:
        sec_input = wait.until(
            EC.element_to_be_clickable(
                (AppiumBy.XPATH, '//android.widget.EditText[@resource-id="label_05_01"]')
            )
        )
        print("   ✅ 보안숫자 입력창 찾음")
    except TimeoutException:
        print("   ℹ️ 기준 보안숫자 입력창 못 찾음 → 대체 방법 시도")

    # 3-2) 대체 방법 (EditText 목록 중 PW 아닌 것)
    if sec_input is None:
        try:
            inputs = wait.until(
                EC.presence_of_all_elements_located(
                    (AppiumBy.CLASS_NAME, "android.widget.EditText")
                )
            )
            if len(inputs) >= 2:
                candidate = None
                for el in inputs:
                    rid = (el.get_attribute("resourceId") or "")
                    if "input_pwd" not in rid:
                        candidate = el
                        break
                if candidate is None:
                    candidate = inputs[1]

                sec_input = candidate
                print("   ✅ 두 번째 EditText를 보안숫자 입력창으로 사용")
        except TimeoutException:
            pass

    if sec_input is None:
        print("   ⚠️ 보안숫자 입력창을 찾지 못했습니다.")
        print("      → 휴대폰에서 직접 입력 후 로그인 버튼을 눌러주세요.")
        return

    # 4) 보안숫자 자동 입력
    try:
        sec_input.clear()
        sec_input.send_keys(security_num)
        print("   ✅ 보안숫자 자동 입력 완료")
    except Exception as e:
        print(f"   ⚠️ 보안숫자 자동 입력 중 오류: {e}")

    time.sleep(1)


def click_login_and_wait_main(driver, wait):
    """
    [측정 기준]
    - 시작: 로그인 버튼 클릭 직전
    - 끝: 메인화면 요소(혜택알림)가 감지되는 순간 (초고속 인식)
    """
    print("🚀 [5단계] 로그인 버튼 클릭 후 메인화면 대기")

    # 로그인 버튼
    try:
        login_btn = wait.until(
            EC.element_to_be_clickable(
                (AppiumBy.XPATH, '//android.widget.Button[contains(@text, "로그인")]')
            )
        )
    except TimeoutException as e:
        print("   ❌ 로그인 버튼을 찾지 못했습니다.")
        raise RuntimeError("로그인 버튼을 찾지 못했습니다.") from e

    # ★ 측정 시작
    print("⏱ 측정 시작 (로그인 버튼 클릭 직전)")
    login_btn.click()
    start_time = time.time()
    print("   ✅ 로그인 버튼 클릭 완료")

    # ---------------------------------------------------------
    # 🔥 [수정됨] 초고속 완료 인식 (Raw Loop + UiSelector)
    # ---------------------------------------------------------
    # 목표: '혜택알림' 설명이 포함된 요소 (메인화면 상징)
    target_selector = 'new UiSelector().descriptionContains("혜택알림")'
    
    try:
        while True:
            # find_elements는 에러 없이 빈 리스트 반환 (가장 빠름)
            res = driver.find_elements(AppiumBy.ANDROID_UIAUTOMATOR, target_selector)
            
            if res:
                break # 찾았으면 즉시 탈출
            
            # 안전장치: 30초 타임아웃
            if time.time() - start_time > 30:
                raise TimeoutException("메인화면 로딩 타임아웃")

        end_time = time.time()
        elapsed = end_time - start_time

        print("🎉 메인화면 로드 확인 (UiSelector 인식)")
        print(f"⏱ 측정 시간: {elapsed:.4f} 초")

        status_msg = "메인화면 로드 완료"
        return elapsed, status_msg

    except TimeoutException:
        end_time = time.time()
        elapsed = end_time - start_time
        print("   ⚠️ 메인화면 확인용 요소를 찾지 못했습니다.(타임아웃)")
        status_msg = "메인화면 미확인(타임아웃)"
        return elapsed, status_msg


def perform_login_once(driver, wait, attempt_idx=None):
    """
    로그인 시나리오 1회
    """
    print("\n🚀 [로그인 시나리오] 1회 시작")

    open_login_section(driver)
    tap_id_login(driver, wait)
    fill_id(driver, wait)
    fill_pwd_and_security(driver, wait, attempt_idx)
    elapsed, status_msg = click_login_and_wait_main(driver, wait)

    return elapsed, status_msg


def logout_to_main(driver):
    """
    [로그아웃] 전체 메뉴 → 스크롤 2번 → 로그아웃 좌표 탭
    """
    print("\n🔚 [로그아웃] 진행")

    try:
        # 1) 전체 메뉴 탭
        print("   📍 (955, 274) 좌표 탭 (전체메뉴)")
        tap_by_coordinates(driver, 955, 274)
        time.sleep(2)

        # 2) 스크롤 두 번
        print("   ↕ 스크롤 1회")
        driver.swipe(1040, 1825, 1040, 242, 500)
        time.sleep(2)

        print("   ↕ 스크롤 2회")
        driver.swipe(1040, 1825, 1040, 242, 500)
        time.sleep(2)

        # 3) 로그아웃 버튼 좌표 탭
        print("   📍 로그아웃 좌표 탭 (502, 1811)")
        tap_by_coordinates(driver, 502, 1811)

        # 4) 메인화면 복귀 확인 (혜택알림)
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


# ===================== 메인 테스트 + CSV 저장 =====================
def test_login_minwon(repeat_count=REPEAT_COUNT):
    options = UiAutomator2Options()
    options.device_name = DEVICE_NAME
    options.app_package = APP_PACKAGE
    options.app_activity = APP_ACTIVITY
    options.automation_name = "UiAutomator2"
    options.new_command_timeout = 300
    options.no_reset = True 

    # ⚡ [속도 최적화 옵션]
    options.set_capability("waitForIdleTimeout", 0) 
    options.set_capability("ignoreUnimportantViews", True)

    print("--- [정부24] ID/PW 로그인 성능 테스트 (초고속 인식) ---")
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
                    print(f"   ⚠️ 로그아웃 실패: {e}")
                    break

    except Exception as e:
        print("\n❌ 테스트 도중 실패")
        print(f"에러 내용: {e}")

    finally:
        driver.quit()
        print("\n✅ 드라이버 종료 완료")

    # ===================== CSV + 통계 저장 =====================
    print("\n" + "=" * 50)
    print("💾 로그인 성능 결과 CSV 저장 중...")

    if results:
        df = pd.DataFrame(results)

        # 통계 계산
        speeds = df["로그인반응속도(초)"].dropna()
        if len(speeds) > 0:
            mean_val = round(speeds.mean(), 4)
            min_val = round(speeds.min(), 4)
            max_val = round(speeds.max(), 4)
            std_val = round(speeds.std(ddof=1), 4) if len(speeds) >= 2 else 0.0
        else:
            mean_val = min_val = max_val = std_val = 0.0

        print("\n📊 통계 요약")
        print(f"   평균: {mean_val} 초")
        print(f"   최소: {min_val} 초")
        print(f"   최대: {max_val} 초")
        print(f"   표준편차: {std_val} 초")

        summary_row = {
            "회차": "요약",
            "측정시각": "",
            "로그인반응속도(초)": "",
            "팝업메시지": "",
            "평균(초)": mean_val,
            "최소(초)": min_val,
            "최대(초)": max_val,
            "표준편차(초)": std_val,
        }

        # 팝업메시지 컬럼 제거 (선택사항)
        if "팝업메시지" in df.columns:
            df = df.drop(columns=["팝업메시지"])
            del summary_row["팝업메시지"]

        df = pd.concat([df, pd.DataFrame([summary_row])], ignore_index=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"minwon24_idpw_login_perf_{repeat_count}runs_{timestamp}.csv"
        
        # 🔥 [핵심 수정] 현재 폴더에 저장
        current_dir = os.path.dirname(os.path.abspath(__file__))
        save_path = os.path.join(current_dir, file_name)
        
        df.to_csv(save_path, index=False, encoding="utf-8-sig")

        print(f"\n✅ CSV 저장 완료! 경로: {save_path}")
        print(df)
    else:
        print("ℹ️ 저장할 측정 결과가 없어 CSV는 생성되지 않습니다.")

if __name__ == "__main__":
    test_login_minwon()