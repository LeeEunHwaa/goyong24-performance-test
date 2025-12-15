import time
import csv
import warnings
import os  # ★ 추가: 파일 저장 경로용
from urllib3.exceptions import NotOpenSSLWarning
from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import statistics  # ★ 통계 계산용

warnings.simplefilter('ignore', NotOpenSSLWarning)

# ---------------------------------------------------------
# [설정] 계정 정보
# ---------------------------------------------------------

# 고용24 아이디 비밀번호 입력
LOGIN_ID = "0000000" 
LOGIN_PW = "0000000"

options = XCUITestOptions()
options.platform_name = "iOS"
options.automation_name = "XCUITest"
options.udid = "-----------"  # 테스트기기 udid 입력
options.bundle_id = "kr.or.keis.mo"         # 고용24 앱 Bundle ID

# [중요] 보안 키패드 입력을 위해 하드웨어 키보드 연결 해제 (소프트웨어 키보드 강제 노출)
options.set_capability("connectHardwareKeyboard", False)
options.set_capability("noReset", True)
options.set_capability("wdaLaunchTimeout", 60000)
options.set_capability("wdaConnectionTimeout", 60000)

driver = webdriver.Remote('http://127.0.0.1:4723', options=options)
wait = WebDriverWait(driver, 20)

# ★ 이 파일이 있는 폴더 (CSV를 여기에 저장할 것)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------
# [매핑] 보안 키패드 특수문자 한글 ID (XML 분석 결과 기반)
# ---------------------------------------------------------
SPECIAL_CHAR_MAP = {
    '!': '느낌표', '@': '골뱅이', '#': '우물정', '$': '달러기호', '%': '퍼센트',
    '^': '꺽쇠', '&': '엠퍼샌드', '*': '별표', '(': '왼쪽괄호', ')': '오른쪽괄호',
    '-': '빼기', '_': '밑줄', '=': '등호', '+': '더하기',
    '[': '왼쪽대괄호', '{': '왼쪽중괄호', ']': '오른쪽대괄호', '}': '오른쪽중괄호',
    '\\': '역슬래시', '|': '수직막대', ';': '세미콜론', ':': '콜론',
    '/': '슬래시', '?': '물음표', ',': '쉼표', '.': '마침표',
    '<': '왼쪽꺽쇠괄호', '>': '오른쪽꺽쇠괄호',
    "'": '작은따옴표', '"': '따옴표', '~': '물결표시', '`': '어금기호'
}

# ---------------------------------------------------------
# [함수] 보안 키패드 입력 (좌표 X, 오직 ID만 사용)
# ---------------------------------------------------------
def type_secure_password(driver, password):
    print(f"   🔐 보안 키패드 입력 시작: {len(password)}자리 (ID 방식)")
    
    # 변환 버튼 ID 후보 (XML에서 확인된 이름들)
    TOGGLE_IDS = ["특수키"]
    
    current_mode = "normal"  # normal(영/수), special(특수)

    for char in password:
        target_id = char  # 기본: 글자 그대로 (예: 's', 'h', '2')
        is_special = False

        # 1. 특수문자인지 확인하고 ID 변환
        if char in SPECIAL_CHAR_MAP:
            target_id = SPECIAL_CHAR_MAP[char]
            is_special = True
        
        # 2. 모드 전환 로직
        # (A) 특수문자인데 현재 일반모드인 경우 -> 변환 버튼 클릭
        if is_special and current_mode == "normal":
            print(f"   🔣 특수문자 '{char}' 입력을 위해 모드 전환 시도")
            clicked = False
            for t_id in TOGGLE_IDS:
                try:
                    driver.find_element(AppiumBy.ACCESSIBILITY_ID, t_id).click()
                    clicked = True
                    break
                except:
                    continue
            
            if not clicked:
                raise Exception("특수문자 변환 버튼(특수키/a/@)을 찾을 수 없습니다.")
            
            time.sleep(1.0)
            current_mode = "special"

        # (B) 일반문자인데 현재 특수모드인 경우 -> 복귀
        elif not is_special and current_mode == "special":
            print(f"   🔄 일반문자 '{char}' 입력을 위해 복귀 시도")
            clicked = False
            for t_id in TOGGLE_IDS:
                try:
                    driver.find_element(AppiumBy.ACCESSIBILITY_ID, t_id).click()
                    clicked = True
                    break
                except:
                    continue
            
            if not clicked:
                raise Exception("일반 모드 복귀 버튼을 찾을 수 없습니다.")
            
            time.sleep(0.5)
            current_mode = "normal"

        # 3. 키 클릭 (ID로 찾기)
        try:
            btn = driver.find_element(AppiumBy.ACCESSIBILITY_ID, target_id)
            btn.click()
            time.sleep(0.2)
        except Exception:
            raise Exception(f"키패드에서 버튼 '{target_id}'을(를) 찾을 수 없습니다.")

    print("   ✅ 비밀번호 입력 완료")

# ---------------------------------------------------------
# [테스트 루프]
# ---------------------------------------------------------
# test_results: [회차, 상태, 측정시간(문자열), 로그인반응속도(초)]
test_results = []
REPEAT_COUNT = 10

try:
    print("🚀 테스트 시작")
    time.sleep(8)

    for i in range(1, REPEAT_COUNT + 1):
        print(f"\n[{i}/{REPEAT_COUNT} 회차] 진행 중...")
        # ★ 이 회차 측정 시간 기록
        measured_at = time.strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            # -------------------------------------------------------
            # 1. 메인 -> 로그인 진입
            # -------------------------------------------------------
            print("   📲 [1단계] 하단 탭 '로그인' 텍스트 클릭")
            login_tab_text = wait.until(EC.element_to_be_clickable((
                AppiumBy.IOS_CLASS_CHAIN, 
                '**/XCUIElementTypeLink/XCUIElementTypeStaticText[`name == "로그인"`]'
            )))
            login_tab_text.click()

            # -------------------------------------------------------
            # 2. HRD 버튼 클릭
            # -------------------------------------------------------
            print("   📲 [2단계] HRD 버튼 클릭")
            hrd_btn = wait.until(EC.element_to_be_clickable((
                AppiumBy.ACCESSIBILITY_ID, "아이디/비밀번호(HRD 출결용)"
            )))
            hrd_btn.click()

            # -------------------------------------------------------
            # 3. ID/PW 입력
            # -------------------------------------------------------
            print("   ⌨️ [3단계] 정보 입력")
            
            # (아이디 입력은 생략: 저장 기능 사용 중)
            # 비밀번호 입력
            pw_input = wait.until(EC.presence_of_element_located((
                AppiumBy.IOS_CLASS_CHAIN, '**/XCUIElementTypeSecureTextField[`value == "개인회원 비밀번호를 입력해주세요."`]'
            )))
            pw_input.click()
            time.sleep(2)  # 키패드 올라올 때까지 대기

            # 보안 키패드 입력
            type_secure_password(driver, LOGIN_PW)
            
            # 입력 완료 버튼이 있다면 클릭
            try:
                driver.find_element(AppiumBy.ACCESSIBILITY_ID, "입력완료").click()
            except:
                pass

            # -------------------------------------------------------
            # 4. 로그인 버튼 클릭
            # -------------------------------------------------------
            print("   ⏱️ [4단계] 로그인 요청")
            login_submit_btn = wait.until(EC.element_to_be_clickable((
                AppiumBy.IOS_CLASS_CHAIN, 
                '**/XCUIElementTypeButton[`name == "로그인"`]'
            )))
            
            start_time = time.time()  # START
            login_submit_btn.click()

            # -------------------------------------------------------
            # 5. 결과 확인 ('Ok' 팝업)
            # -------------------------------------------------------
            print("   👀 [5단계] 팝업 대기 ('Ok' 버튼)")
            confirm_btn = wait.until(EC.element_to_be_clickable((
                AppiumBy.ACCESSIBILITY_ID, "Ok"
            )))
            
            end_time = time.time()  # END
            duration = end_time - start_time
            
            print(f"   🎉 로그인 성공! 소요 시간: {duration:.4f}초")
            # ★ 성공 기록: 상태=성공, 측정시간, 소요시간
            test_results.append([i, "성공", measured_at, duration])
            
            confirm_btn.click()  # 팝업 닫기
            
            # 메인화면 리프레시 대기
            time.sleep(4)

            # -------------------------------------------------------
            # 6. 로그아웃 (전체메뉴 -> 로그아웃)
            # -------------------------------------------------------
            print("   🚪 [6단계] 로그아웃")

            # 6-1. 전체메뉴
            menu_btn = wait.until(EC.element_to_be_clickable((
                AppiumBy.ACCESSIBILITY_ID, "전체메뉴"
            )))
            menu_btn.click()
            
            time.sleep(2)  # 메뉴 열림 대기

            # 6-2. 로그아웃
            logout_btn = wait.until(EC.element_to_be_clickable((
                AppiumBy.ACCESSIBILITY_ID, "로그아웃"
            )))
            logout_btn.click()

            # 6-3. 로그아웃 확인 (있다면)
            try:
                time.sleep(1)
                driver.find_element(AppiumBy.ACCESSIBILITY_ID, "확인").click()
            except:
                pass

            print("   ✅ 초기 화면 복귀 대기...")
            time.sleep(3)
            
        except Exception as e:
            print(f"   ❌ {i}회차 실패: {str(e)}")
            # ★ 실패도 한글 상태 + 측정시간 기록, 시간은 0
            test_results.append([i, "실패", measured_at, 0])
            
            # 실패 시 복구: 앱 재실행
            print("   ⚠️ 앱 재실행으로 상태 초기화")
            driver.terminate_app(driver.capabilities['bundleId'])
            time.sleep(2)
            driver.activate_app(driver.capabilities['bundleId'])
            time.sleep(5)

finally:
    # -----------------------------------------------------
    # ★ 통계 계산 (성공 케이스 기준)
    # -----------------------------------------------------
    durations = [row[3] for row in test_results if row[1] == "성공" and row[3] > 0]

    if durations:
        avg_val = statistics.mean(durations)
        min_val = min(durations)
        max_val = max(durations)
        std_val = statistics.pstdev(durations) if len(durations) > 1 else 0.0
    else:
        avg_val = min_val = max_val = std_val = 0.0

    # ★ 이 스크립트와 같은 폴더에 저장
    output_path = os.path.join(BASE_DIR, 'work24_idpw_login_result.csv')
    print(f"📁 CSV 저장 경로: {output_path}")

    # CSV 저장 (Excel 호환 위해 utf-8-sig)
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        # 한글 헤더 + 통계 칸
        writer.writerow(['회차', '상태', '측정시간', '로그인반응속도(초)', '평균(초)', '최소(초)', '최대(초)', '표준편차(초)'])
        
        # 1) 각 회차 기록 (통계 칸 비워두기)
        for iteration, status, measured_at, duration in test_results:
            writer.writerow([
                iteration,
                status,
                measured_at,
                f"{duration:.4f}" if duration > 0 else "",
                "",  # 평균(초)
                "",  # 최소(초)
                "",  # 최대(초)
                ""   # 표준편차(초)
            ])

        # 2) 마지막에 통계 요약 행 한 줄만 추가
        writer.writerow([
            "통계",      # 회차 자리 대신 '통계' 표기
            "",          # 상태
            "",          # 측정시간
            "",          # 로그인반응속도(초)
            f"{avg_val:.4f}" if durations else "",
            f"{min_val:.4f}" if durations else "",
            f"{max_val:.4f}" if durations else "",
            f"{std_val:.4f}" if durations else ""
        ])

    print("\n테스트 종료 및 결과 저장 완료")
    if driver:
        driver.quit()
