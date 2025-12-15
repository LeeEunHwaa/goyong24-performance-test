# 터미널에서
# appium --use-plugins=images

import time
import os
import base64
import io
from PIL import Image
from appium import webdriver
from appium.options.ios import XCUITestOptions

# 설정
BUNDLE_ID = "kr.co.jobkorea.jobkorea1"
UDID = "-------"  # [UDID 입력 필수]

# ⭐ 좌표기준 설정(로그인 확인용) ⭐
ROI_X_PCT = 0.0      # 가로 시작
ROI_Y_PCT = 0.055    # 세로 시작
ROI_W_PCT = 1.0      # 가로 길이
ROI_H_PCT = 0.05     # 세로 높이

# # ⭐ 좌표기준 설정(앱실행 확인용) ⭐
# ROI_X_PCT = 0.0
# ROI_Y_PCT = 0.44
# ROI_W_PCT = 1.0
# ROI_H_PCT = 0.12

options = XCUITestOptions()
options.platform_name = "iOS"
options.automation_name = "XCUITest"
options.bundle_id = BUNDLE_ID
options.udid = UDID
options.no_reset = True 

driver = webdriver.Remote("http://127.0.0.1:4723", options=options)

try:
    print("📸 기준 이미지 생성 중...")
    driver.activate_app(BUNDLE_ID)
    time.sleep(5)  # 로딩 대기

    # 스크린샷 찍고 자르기
    screenshot_base64 = driver.get_screenshot_as_base64()
    image = Image.open(io.BytesIO(base64.b64decode(screenshot_base64)))
    
    img_w, img_h = image.size
    left = int(img_w * ROI_X_PCT)
    top = int(img_h * ROI_Y_PCT)
    right = int(left + (img_w * ROI_W_PCT))
    bottom = int(top + (img_h * ROI_H_PCT))

    target_crop = image.crop((left, top, right, bottom))
    
    # ✅ 현재 .py 파일이 있는 폴더에 저장
    script_dir = os.path.dirname(os.path.abspath(__file__))
    save_path = os.path.join(script_dir, "jobkorea_login.png")
    target_crop.save(save_path)

    print(f"✅ 기준 이미지 저장 완료: {save_path} (크기: {right-left}x{bottom-top})")
    print("👉 이 이미지가 성능 테스트의 기준이 됩니다.")

finally:
    driver.quit()
