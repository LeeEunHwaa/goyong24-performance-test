# 📱 AW 고용24 성능 테스트

**고용24(Goyong24) 모바일 앱 성능 자동화 테스트 프로젝트**

이 프로젝트는 **Appium**과 **Python**을 활용하여 공공기관 앱(고용24)의 실행 및 로그인 성능을 측정하고, 민간 앱(잡코리아) 및 타 공공 앱(정부24)과의 성능을 비교 분석하기 위해 구축되었습니다.

- 고용24 주요 사용자 시나리오의 응답 시간을 AOS/iOS 실기기에서 정량 측정
- 작년 결과 및 다른 유사 앱과 비교
- 성능 수준을 평가하고 개선 우선순위를 도출

-----

## 📂 0. 테스트 케이스 & 코드 바로가기

| ID | 테스트 항목 | 코드 바로가기(AOS) |코드 바로가기(iOS) | 
|:---:|:-----------|:-------------|:-------------|
| **TC-01** | 앱 실행 속도 |[🔗 코드 보기](https://github.com/LeeEunHwaa/goyong24-performance-test/tree/main/AOS/APP_Start) |[🔗 코드 보기](https://github.com/LeeEunHwaa/goyong24-performance-test/tree/main/iOS/App_Start_iOS) |
| **TC-02** | 로그인 속도 (ID/PW) | [🔗 코드 보기](https://github.com/LeeEunHwaa/goyong24-performance-test/tree/main/AOS/IDPW_Login) | [🔗 코드 보기](https://github.com/LeeEunHwaa/goyong24-performance-test/tree/main/iOS/ID_PW_Login_iOS) |
| **TC-03** | 로그인 속도 (인증서) | [🔗 코드 보기](https://github.com/LeeEunHwaa/goyong24-performance-test/tree/main/AOS/Certificate_Login) | [🔗 코드 보기](https://github.com/LeeEunHwaa/goyong24-performance-test/tree/main/iOS/Certificate_Login_iOS) |
| **TC-04** | 검색 속도 | [🔗 코드 보기](https://github.com/LeeEunHwaa/goyong24-performance-test/tree/main/AOS/Search) |[🔗 코드 보기](https://github.com/LeeEunHwaa/goyong24-performance-test/tree/main/iOS/Search_iOS) |


-----

## 🎯 1. 테스트 범위 (Test Scope)

본 프로젝트는 사용자 경험(UX)에 직접적인 영향을 미치는 주요 지표를 측정합니다.

| ID | 테스트 항목 | 측정 구간 | 비고 |
|:---:|:---|:---|:---|
| **TC-01** | **앱 실행 속도** | 앱 아이콘 클릭(Start) \~ 메인 요소 로딩 완료(End) | Cold Start 기준 (캐시 제거) |
| **TC-02** | **로그인 속도 (ID/PW)** | 로그인 버튼 클릭 \~ 로그인 완료 팝업/화면 등장 | 정부24 반자동(Semi-auto) |
| **TC-03** | **로그인 속도 (인증서)** | 인증서 완료 버튼 클릭 \~ 로그인 완료 | 잡코리아 인증서 로그인 X |
| **TC-04** | **검색 속도** | 검색어 입력 후 버튼 클릭 \~ 결과 리스트 로딩 완료 | - |

-----

## 🛠 2. 테스트 환경 (Environment)

### Hardware

  * **PC OS**: Windows 10/11
  * **Test Device**: Samsung Galaxy S25 (AOS 16)

  * **MAC OS**: 15.7.2
  * **Test Device**: iPhone 15 (iOS 18.6.2)​

### Software & Tools

  * **Language**: Python 3.x
  * **Framework**: Appium (UiAutomator2 Driver)
  * **Libraries**:
      * `Appium-Python-Client`
      * `Selenium`
      * `Pandas` (데이터 분석 및 CSV 저장용)
      * `OpenCV` : 화면 렌더링 완료 시점을 검증하는 이미지 프로세싱 라이브러리​
  * **Others**: Android SDK Platform-Tools (ADB)

-----

## 🚀 3. 주요 기능 및 전략 (Key Strategies)

### 1\) 공정한 성능 비교 (Fairness)

  * **Cold Start 환경 조성**: 매 테스트 회차마다 `terminate_app`을 통해 백그라운드 프로세스를 강제 종료하고 메모리를 정리한 후 측정을 시작합니다.
  * **반복 측정 및 통계**: 10회 반복 측정 후 \*\*평균(Mean), 최소(Min), 최대(Max), 표준편차(Std Dev)\*\*를 산출하여 데이터 신뢰성을 확보합니다.

### 2\) 보안 솔루션 우회 (Security Bypass)

  * **반자동(Semi-Auto) 로그인**: 금융/공공 앱의 보안 키패드(TouchEn mTranskey 등) 및 캡차(Captcha)로 인한 자동화 불가능 영역을 해결하기 위해, **'사용자 입력 대기 -\> 기계적 시간 측정'** 방식을 적용했습니다.
  * **Hybrid App 대응**: Native 요소와 WebView 요소가 혼재된 환경에서 `XPath`, `Resource-ID`, `Accessibility-ID`를 상황에 맞춰 선별적으로 사용했습니다.

-----

## 📂 4. 프로젝트 구조 (Project Structure)

```bash
goyong24-performance-test/
├─ AOS/                              # Android 성능 테스트
│  ├─ APP_Start/                     # TC-01 앱 실행 속도
│  ├─ IDPW_Login/                    # TC-02 로그인 속도 (ID/PW)
│  ├─ Certificate_Login/             # TC-03 로그인 속도 (인증서)
│  └─ Search/                        # TC-04 검색(통합검색) 속도
├─ iOS/                              # iOS 성능 테스트
│  ├─ App_Start_iOS/                 # TC-01 앱 실행 속도
│  ├─ ID_PW_Login_iOS/               # TC-02 로그인 속도 (ID/PW)
│  ├─ Certificate_Login_iOS/          # TC-03 로그인 속도 (인증서)
│  └─ Search_iOS/                    # TC-04 검색(통합검색) 속도
└─ README.md                         # 프로젝트 문서
```

-----

## ⚙️ 5. 설치 및 실행 (Installation & Usage)

### 사전 준비

1.  **Node.js & Appium 설치**
    ```bash
    npm install -g appium
    appium driver install uiautomator2
    ```
2.  **Python 라이브러리 설치**
    ```bash
    pip install Appium-Python-Client pandas
    ```
3.  **ADB 환경 변수 설정** (`ANDROID_HOME`, `Path`)

### 실행 방법

1.  **Appium 서버 실행** (CMD)
    ```bash
    appium
    ```
2.  **테스트 스크립트 실행**
    ```bash
    python compare_3apps_launch.py
    ```


### 🔎 상세 내용
👉 [Notion에서 자세히 보기](https://hospitable-syrup-c6f.notion.site/cced123c3ef248d4b5e89e5f23091608)



-----

![그림2](https://github.com/user-attachments/assets/b6f83858-cf14-44c4-b6d5-06e09410bce4)   <img width="109" height="15" alt="그림1" src="https://github.com/user-attachments/assets/ffeea423-6030-4663-a132-d292ae70b854" />




