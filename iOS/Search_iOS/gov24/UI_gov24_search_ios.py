import time
import csv
import os
import statistics
from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.webdriver.common.appiumby import AppiumBy

# ---------------------------------------------------------
# [설정]
# ---------------------------------------------------------
SEARCH_KEYWORD = "청년"
REPEAT_COUNT = 10

options = XCUITestOptions()
options.platform_name = "iOS"
options.automation_name = "XCUITest"
options.bundle_id = "kr.go.dcsc.minwon24"
options.udid = "------------------"

# ⚡ [속도 최적화 끝판왕 설정]
options.set_capability("noReset", True)
options.set_capability("waitForQuiescence", False)  # UI 안정화 대기 끔
options.set_capability("waitForIdleTimeout", 0)     # ★ 중요: 앱이 바쁘든 말든 명령 강제 수행
options.set_capability("simpleIsVisibleCheck", True)
options.set_capability("useJSONSource", True)
# 스크린샷 퀄리티를 낮춰서 네트워크 대역폭 확보 (이미지 안쓰지만 혹시 모를 오버헤드 방지)
options.set_capability("mjpegServerScreenshotQuality", 0) 

driver = webdriver.Remote('http://127.0.0.1:4723', options=options)
# 드라이버 설정으로 한 번 더 강제 (확실하게)
driver.update_settings({"waitForIdleTimeout": 0})

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
test_results = []

try:
    print("🚀 정부24 검색 성능 테스트 (NSPredicate Mode)")

    for i in range(1, REPEAT_COUNT + 1):
        print(f"\n[{i}/{REPEAT_COUNT} 회차]")
        measured_at = time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            # 1. 검색어 입력 (입력창 찾기)
            # 안전하게 루프로 찾음
            while True:
                # Predicate: 접근성 ID가 '검색어 입력'인 요소
                elems = driver.find_elements(
                    AppiumBy.IOS_PREDICATE, 
                    "name == '검색어 입력'"
                )
                if elems:
                    search_input = elems[0]
                    search_input.click()
                    search_input.clear()
                    search_input.send_keys(SEARCH_KEYWORD)
                    break
            
            # 2. 검색 버튼 찾기 (미리 찾아둠)
            # Predicate: 접근성 ID가 '검색'인 요소
            search_btns = driver.find_elements(AppiumBy.IOS_PREDICATE, "name == '검색'")
            if search_btns:
                search_btn = search_btns[0]
            else:
                raise Exception("검색 버튼 못 찾음")
            
            # -----------------------------------------------------------
            # ✅ [Time Start]
            # -----------------------------------------------------------
            
            search_btn.click()
            start_time = time.time()

            # 3. [검색 완료 판단] 🔥 iOS Native 언어 사용
            # 설명: "StaticText 타입이면서 AND 이름(name)이 '검색 결과'인 요소"
            # 이 문자열은 iOS 시스템에 그대로 전달되어 번역 딜레이가 '0'입니다.
            predicate_string = "type == 'XCUIElementTypeStaticText' AND name == '검색 결과'"
            
            while True:
                # find_elements는 에러를 안 뱉으므로 try-catch 오버헤드 없음
                res = driver.find_elements(AppiumBy.IOS_PREDICATE, predicate_string)
                
                if res:
                    break
                
                # 안전장치: 20초 지나면 타임아웃
                if time.time() - start_time > 20:
                    raise Exception("Timeout")

            end_time = time.time()
            # -----------------------------------------------------------
            
            duration = end_time - start_time
            print(f"   🎉 검색 완료! 소요 시간: {duration:.4f}초")
            test_results.append([i, "성공", measured_at, duration])

            # 4. [복귀] 이전 페이지
            # Predicate: Link 타입이면서 이름이 '이전 페이지'
            print("   🔙 이전 페이지 클릭")
            try:
                back_locator = "type == 'XCUIElementTypeLink' AND name == '이전 페이지'"
                back_elems = driver.find_elements(AppiumBy.IOS_PREDICATE, back_locator)
                
                if back_elems:
                    back_elems[0].click()
                else:
                    driver.tap([(30, 70)]) # 좌표 백업
            except:
                driver.tap([(30, 70)])

            time.sleep(1)

        except Exception as e:
            print(f"   ❌ {i}회차 실패: {e}")
            test_results.append([i, "실패", measured_at, 0])
            driver.terminate_app("kr.go.dcsc.minwon24")
            time.sleep(1)
            driver.activate_app("kr.go.dcsc.minwon24")
            time.sleep(3)

finally:
    # 저장 로직
    durations = [row[3] for row in test_results if row[1] == "성공" and row[3] > 0]
    if durations:
        avg = statistics.mean(durations)
        mn = min(durations)
        mx = max(durations)
        sd = statistics.pstdev(durations) if len(durations) > 1 else 0.0
    else:
        avg=mn=mx=sd=0.0

    output_path = os.path.join(SCRIPT_DIR, 'ios_gov24_search_result.csv')
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['회차','상태','측정시간','검색반응속도(초)','평균','최소','최대','표준편차'])
        for r in test_results:
            writer.writerow([r[0], r[1], r[2], f"{r[3]:.4f}" if r[3]>0 else "","","","",""])
        writer.writerow(["통계","","",f"{avg:.4f}",f"{avg:.4f}",f"{mn:.4f}",f"{mx:.4f}",f"{sd:.4f}"])
    
    print(f"\n✅ 저장 완료: {output_path}")
    if driver:
        driver.quit()
