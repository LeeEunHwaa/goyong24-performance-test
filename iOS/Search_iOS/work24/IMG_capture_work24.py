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
BUNDLE_ID = "kr.go.dcsc.minwon24"  # 정부24 Bundle ID
UDID = "-----------------"  # [UDID 입력 필수]

# ⭐ ROI 좌표 설정 (화면 중간의 고정된 아이콘/글자 노리기) ⭐
ROI_X_PCT = 0      # 가로
ROI_Y_PCT = 0.44   # 세로
ROI_W_PCT = 1      # 너비
ROI_H_PCT = 0.05    # 높이

# ROI_X_PCT = 0      # 가로
# ROI_Y_PCT = 0      # 세로
# ROI_W_PCT = 1      # 너비
# ROI_H_PCT = 1      # 높이

options = XCUITestOptions()
options.platform_name = "iOS"
options.automation_name = "XCUITest"
# [중요] 앱을 자동으로 실행하지 않고, 현재 화면 그대로 연결만 함
options.set_capability("autoLaunch", False)
options.udid = UDID

driver = webdriver.Remote("http://127.0.0.1:4723", options=options)

try:
    print("📸 [Step 1] 현재 화면 캡처 중...")
    # 앱이 켜져 있다고 가정하고 바로 찍습니다.
    
    screenshot_base64 = driver.get_screenshot_as_base64()
    image = Image.open(io.BytesIO(base64.b64decode(screenshot_base64)))
    
    img_w, img_h = image.size
    left = int(img_w * ROI_X_PCT)
    top = int(img_h * ROI_Y_PCT)
    right = int(left + (img_w * ROI_W_PCT))
    bottom = int(top + (img_h * ROI_H_PCT))

    target_crop = image.crop((left, top, right, bottom))

    # 📂 현재 파이썬 파일이 있는 폴더에 저장
    script_dir = os.path.dirname(os.path.abspath(__file__))
    save_path = os.path.join(script_dir, "work24_test.png")

    target_crop.save(save_path)
    print(f"✅ 캡처 이미지 저장 완료: {save_path}")
    print("👉 저장된 이미지가 '로딩 완료'로 판단할 만한 요소인지 확인하세요.")

finally:
    driver.quit()
