from selenium.common.exceptions import TimeoutException
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from appium.options.android import UiAutomator2Options
from appium import webdriver
import pandas as pd
from datetime import datetime
import time
import os  # [추가] 경로 저장을 위해

# ===================== 설정 =====================
APP_PACKAGE = "kr.or.keis.mo"

LOGIN_ID = "------" # 아이디 입력
LOGIN_PW = "-------" # 비밀번호 입력

APPIUM_SERVER_URL = "http://127.0.0.1:4723"
DEVICE_NAME = "Android"

# 반복 횟수
REPEAT_COUNT = 10


# ===================== 동작 함수 =====================

def tap_idpw_menu(driver, wait):
    """'아이디/비밀번호(HRD 출결용)' 버튼 클릭"""
    print("📲 [3단계] '아이디/비밀번호(HRD 출결용)' 버튼 클릭")

    # 화면 아래쪽 보이도록 한 번 스와이프
    try:
        driver.swipe(22, 942, 22, 650, 500)
        time.sleep(1)
        print("   ✅ 스와이프 수행 완료")
    except Exception as e:
        print(f"   ℹ️ 스와이프 중 오류(무시): {e}")

    try:
        btn = wait.until(
            EC.element_to_be_clickable(
                (AppiumBy.ANDROID_UIAUTOMATOR,
                 'new UiSelector().resourceId("btn_idpopup")')
            )
        )
        btn.click()
        print("   ✅ '아이디/비밀번호(HRD 출결용)' 버튼 클릭 성공")
    except TimeoutException as e:
        print("   ❌ '아이디/비밀번호(HRD 출결용)' 버튼을 찾지 못했습니다.")
        raise RuntimeError("ID/PW(HRD 출결용) 메뉴를 찾지 못했습니다.") from e


def fill_login_form(driver, wait):
    """로그인 화면에서 ID/PW 입력"""
    print("⌨️ [4단계] 아이디 / 비밀번호 자동 입력")

    def _two_edittexts(d):
        els = d.find_elements(AppiumBy.CLASS_NAME, "android.widget.EditText")
        return els if len(els) >= 2 else False

    try:
        inputs = wait.until(_two_edittexts)
        id_input, pw_input = inputs[0], inputs[1]

        id_input.clear()
        id_input.send_keys(LOGIN_ID)
        print("   ✅ ID 입력 완료")

        pw_input.clear()
        pw_input.send_keys(LOGIN_PW)
        print("   ✅ PW 입력 완료")
    except Exception as e:
        print("   ❌ 로그인 입력창을 찾지 못했습니다.")
        raise RuntimeError("로그인 ID/PW 입력창을 찾지 못했습니다.") from e


def open_login_section(driver, wait):
    """
    '로그인을 해 주세요' 영역을 눌러 로그인 수단 선택 화면으로 이동.
    """
    print("📲 [1단계] '로그인을 해 주세요'로 이동")

    try:
        login_please = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable(
                (AppiumBy.ACCESSIBILITY_ID, "로그인을 해 주세요")
            )
        )
        print("   ✅ 메뉴가 이미 열려 있음 → 바로 '로그인을 해 주세요' 클릭")
    except TimeoutException:
        print("   ℹ️ '로그인을 해 주세요'가 안 보여서 '전체메뉴' 버튼부터 클릭")
        all_menu_btn = wait.until(
            EC.element_to_be_clickable(
                (AppiumBy.XPATH, "//android.widget.Button[@text='전체메뉴']")
            )
        )
        all_menu_btn.click()

        login_please = wait.until(
            EC.element_to_be_clickable(
                (AppiumBy.ACCESSIBILITY_ID, "로그인을 해 주세요")
            )
        )

    login_please.click()
    print("   ✅ '로그인을 해 주세요' 클릭 완료")
    
    print("⏳ [1-1단계] 화면 전환 안정화를 위해 3초 대기...")
    time.sleep(3)


def logout_from_all_menu(driver, wait):
    """로그인을 위한 로그아웃 (전체메뉴 열기 -> 로그아웃 -> 확인)"""
    print("🚪 [로그아웃] 다음 회차 준비")
    try:
        # 전체메뉴 열기
        menu_btn = wait.until(EC.element_to_be_clickable((AppiumBy.XPATH, "//android.widget.Button[@text='전체메뉴']")))
        menu_btn.click()
        
        # 로그아웃 버튼 찾기
        logout_btn = wait.until(EC.presence_of_element_located((AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().text("로그아웃")')))
        logout_btn.click()
        
        # 확인 팝업 처리 (있을 경우)
        try:
            ok_btn = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().text("확인")')))
            ok_btn.click()
        except:
            pass
            
        time.sleep(2)
        print("   ✅ 로그아웃 완료")
    except Exception as e:
        print(f"   ⚠️ 로그아웃 실패 (무시하고 진행): {e}")


def perform_login_once(driver, wait):
    """
    로그인 시나리오 1회 수행.
    ✅ [변경됨] 로그인 버튼 클릭 후 '초고속 인식(Raw Loop)'으로 팝업 감지
    """
    print("🚀 [로그인 시나리오] 시작")

    # [1단계] '로그인을 해 주세요' 진입
    open_login_section(driver, wait)

    # [3단계] 아이디/비밀번호(HRD 출결용)
    tap_idpw_menu(driver, wait)

    # [4단계] ID/PW 입력
    fill_login_form(driver, wait)

    # [5단계] 로그인 버튼 클릭 + 응답 시간 측정
    print("⏱️ [5단계] 로그인 버튼 클릭 후 응답 속도 측정 시작")

    # 키보드 숨기기
    try:
        driver.hide_keyboard()
        time.sleep(0.5)
        print("   📱 소프트 키보드 숨김")
    except Exception:
        pass

    # 로그인 버튼 찾기
    login_btn = wait.until(
        EC.element_to_be_clickable(
            (AppiumBy.ANDROID_UIAUTOMATOR,
             'new UiSelector().resourceId("btnIndvIdLogin")')
        )
    )

    # 클릭 -> 시간 측정
    login_btn.click()
    start_time = time.time()

    # ---------------------------------------------------------
    # 🔥 [수정됨] 초고속 완료 인식 (Raw Loop + UiSelector)
    # ---------------------------------------------------------
    # 감지 대상: 팝업 메시지 본문 (android:id/message)
    target_selector = 'new UiSelector().resourceId("android:id/message")'
    
    try:
        while True:
            # find_elements는 에러 없이 빈 리스트 반환 (가장 빠름)
            res = driver.find_elements(AppiumBy.ANDROID_UIAUTOMATOR, target_selector)
            
            if res:
                # 찾았으면 텍스트(popup content) 저장 후 탈출
                popup_text = res[0].text
                break 
            
            # 안전장치: 30초 타임아웃
            if time.time() - start_time > 30:
                raise TimeoutException("로그인 팝업 대기 타임아웃")

        end_time = time.time()
        
    except TimeoutException:
        print("   ❌ 로그인 결과 팝업을 찾지 못했습니다.")
        raise RuntimeError("로그인 결과 팝업 타임아웃")

    elapsed = end_time - start_time
    popup_first_line = popup_text.splitlines()[0] if popup_text else ""

    print("\n🎉 로그인 응답 수신!")
    print(f"🚀 로그인 반응 속도: {elapsed:.4f} 초")
    print(f"📄 팝업 내용: {popup_first_line}")

    # 팝업 확인 버튼 닫기
    try:
        ok_btn = driver.find_element(AppiumBy.ID, "android:id/button1")
        ok_btn.click()
        print("   ✅ 팝업 확인 버튼 클릭")
    except Exception:
        print("   ℹ️ 팝업 확인 버튼을 찾지 못했습니다.")

    return elapsed, popup_first_line


# 메인 테스트
def test_login_security_safe(repeat_count=REPEAT_COUNT):

    options = UiAutomator2Options()
    options.device_name = DEVICE_NAME
    options.app_package = APP_PACKAGE
    options.app_activity = ".MainActivity"
    options.automation_name = "UiAutomator2"
    options.new_command_timeout = 300
    options.no_reset = True
    
    # ⚡ [속도 최적화]
    options.set_capability("waitForIdleTimeout", 0) 
    options.set_capability("ignoreUnimportantViews", True)

    print("--- 로그인 성능 테스트 (반복) ---")
    driver = webdriver.Remote(APPIUM_SERVER_URL, options=options)
    wait = WebDriverWait(driver, 20)

    results = []  # 각 회차 결과를 저장
    try:
        for i in range(1, repeat_count + 1):
            print("\n" + "=" * 60)
            print(f"🔁 로그인 시도 {i}/{repeat_count}")
            print("=" * 60)

            # 2번째 시도부터는 로그아웃 먼저 수행
            if i >= 2:
                logout_from_all_menu(driver, wait)

            # 로그인 1회 수행 + 시간 측정
            try:
                elapsed, popup_first_line = perform_login_once(driver, wait)

                results.append({
                    "회차": i,
                    "측정시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "로그인반응속도(초)": round(elapsed, 4),
                    "팝업메시지": popup_first_line,
                })
            except Exception as e:
                print(f"   ❌ 오류 발생: {e}")
                results.append({
                    "회차": i,
                    "측정시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "로그인반응속도(초)": "",
                    "팝업메시지": "실패",
                })

            # 회차 사이 약간의 대기
            time.sleep(2)

        print("\n✅ 모든 반복 로그인 테스트 완료")

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

        # ---- 통계 계산 ----
        # 성공한 값(숫자)만 추려내기
        speeds = pd.to_numeric(df["로그인반응속도(초)"], errors='coerce').dropna()

        if not speeds.empty:
            mean_val = speeds.mean()
            min_val = speeds.min()
            max_val = speeds.max()
            std_val = speeds.std(ddof=1) if len(speeds) >= 2 else 0.0
        else:
            mean_val = min_val = max_val = std_val = 0.0

        print("\n📊 통계 요약")
        print(f"   평균: {mean_val:.4f} 초")
        print(f"   최소: {min_val:.4f} 초")
        print(f"   최대: {max_val:.4f} 초")
        print(f"   표준편차: {std_val:.4f} 초")

        # ---- 요약 행 추가 ----
        summary_row = {
            "회차": "요약",
            "측정시각": "",
            "로그인반응속도(초)": "",
            "팝업메시지": "",
            "평균(초)": round(mean_val, 4),
            "최소(초)": round(min_val, 4),
            "최대(초)": round(max_val, 4),
            "표준편차(초)": round(std_val, 4),
        }
        
        # 팝업메시지 컬럼 제거 (선택사항 - 요청하신 포맷에 맞춤)
        if "팝업메시지" in df.columns:
            df = df.drop(columns=["팝업메시지"])
            del summary_row["팝업메시지"]

        df = pd.concat([df, pd.DataFrame([summary_row])], ignore_index=True)

        # ---- CSV 저장 (현재 폴더) ----
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"work24_idpw_login_perf_{repeat_count}runs_{timestamp}.csv"
        
        # 🔥 [핵심 수정] 현재 폴더 경로
        current_dir = os.path.dirname(os.path.abspath(__file__))
        save_path = os.path.join(current_dir, file_name)
        
        df.to_csv(save_path, index=False, encoding="utf-8-sig")

        print(f"\n✅ CSV 저장 완료! 경로: {save_path}")
        print(df)
    else:
        print("ℹ️ 저장할 측정 결과가 없어 CSV는 생성하지 않습니다.")

if __name__ == "__main__":
    test_login_security_safe()