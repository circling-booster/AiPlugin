# **🔌 AiPlugs Platform (v2.2 External Cloud Edition)**

AiPlugs는 로컬 PC에서 실행되는 AI 플러그인 오케스트레이션 플랫폼입니다.

사용자의 웹 브라우징 트래픽을 투명하게 가로채어(Intercept), 문맥에 맞는 AI 기능을 웹 페이지에 주입(Injection)합니다.

이번 버전은 \*\*외부 클라우드 서버(External Cloud Server)\*\*와의 연동을 전제로 경량화되었으며, 로컬 시뮬레이션 서버가 제거되었습니다.

## **💡 핵심 변경 사항 (v2.2 Highlights)**

1. **외부 클라우드 연동 강화 (External Cloud Integration)**:  
   * 기존의 로컬 cloud\_server 디렉터리 및 실행 로직이 제거되었습니다.  
   * 이제 config.json 설정을 통해 실제 운영 중인 외부 AI 서버와 직접 통신합니다.  
2. **모듈화된 API 서버 (Modularized Server)**:  
   * **WebSocket 관리**: connection\_manager.py (Zombie Connection 방지 로직 포함)  
   * **추론 라우팅**: inference\_router.py (Local Process vs External Cloud 분기 처리)  
3. **고도화된 런타임 관리 & 보안 (Advanced Runtime & Security)**:  
   * **Lazy Loading**: 요청이 들어오는 순간에만 로컬 프로세스를 생성하여 리소스를 최적화합니다.  
   * **Security Separation**: CSP 우회 로직을 security.py로 분리하여 관리합니다.

## **🏗️ 시스템 아키텍처 (Architecture)**

graph TD    
    User\[User Browser\] \<--\> |Proxy :8080| Mitmproxy\[Python Proxy Core\]    
    Mitmproxy \--\> |Sanitize| Security\[Security Sanitizer\]    
    Mitmproxy \--\> |Inject| Injector\[HTML Injector\]

    subgraph "AiPlugs Core (Python)"    
        Orch\[Orchestrator\] \--\> API\_Main\[API Server :5000\]    
        Orch \--\> Proxy\_Main\[Proxy Server\]    
            
        API\_Main \--\> ConnMgr\[Connection Manager\]    
        API\_Main \--\> InfRouter\[Inference Router\]    
            
        InfRouter \--\> |Request Proc| RuntimeMgr\[Runtime Manager\]    
        RuntimeMgr \--\> |Spawn| WorkerMgr\[Worker Manager\]    
        WorkerMgr \--\> |IPC| LocalProc\[Local Plugin Process\]    
            
        InfRouter \--\> |Relay (HTTP)| External\_Cloud\[External AI Server\]    
    end

    subgraph "Electron App"    
        ProcessMgr\[Process Manager\] \--\> |Exec| Orch    
        Level1\_CSP\[L1 CSP Bypass\]    
    end

## **📂 프로젝트 구조 (Directory Structure)**

AiPlugs-Project/    
├── .gitignore                   \# Git 제외 설정    
├── package.json                 \# Electron 의존성 및 스크립트    
├── bat/                         \# \[Utils\] 긴급 복구용 스크립트    
│   └── reset\_proxy.bat          \# 프록시 설정 강제 초기화    
├── config/                      \# \[Config\] 설정 파일    
│   ├── config.json              \# 시스템 설정 (외부 클라우드 URL 필수)    
│   └── settings.json            \# 사용자 설정 (활성 플러그인 등)    
├── electron/                    \# \[Controller\] Electron UI & Process Control    
│   ├── main/    
│   │   ├── index.js             \# 앱 진입점, L1 CSP 우회    
│   │   ├── process-manager.js   \# Python Core 프로세스 생명주기 관리    
│   │   └── cert-handler.js      \# HTTPS 인증서 설치    
│   └── renderer/                \# 대시보드 UI    
├── python/                      \# \[Core Engine\]    
│   ├── main.py                  \# Python 진입점    
│   ├── requirements.txt         \# Python 의존성    
│   ├── core/                    \# 핵심 비즈니스 로직    
│   │   ├── inference\_router.py  \# 외부 클라우드 릴레이 로직 포함    
│   │   ├── runtime\_manager.py   \# 로컬 플러그인 프로세스 관리    
│   │   ├── security.py          \# HTTP 헤더 정화 (CSP 제거)    
│   │   ├── injector.py          \# SPA Hook 및 스크립트 주입    
│   │   └── ...                  \# 기타 모듈    
│   └── utils/    
│       └── system\_proxy.py      \# 시스템 프록시 제어    
└── plugins/                     \# \[Extensions\] Manifest V3 플러그인    
    ├── cloud-secure-translator/ \# Web Mode 예시 (외부 API 사용)    
    ├── heavy-math-solver/       \# Local Mode 예시 (Lazy Loading)    
    └── spa-connection-tester/   \# SPA 대응 테스트

## **🚀 상세 컴포넌트 분석 (Deep Dive)**

### **1\. Core Logic 분리 (Python)**

기존 모놀리식 구조를 해결하기 위해 역할을 명확히 분담했습니다.

* **connection\_manager.py**: SPA 특성상 잦은 페이지 이동으로 발생하는 '좀비 연결'을 정리하고, WebSocket 세션을 안정적으로 유지합니다.  
* **inference\_router.py**: 플러그인 모드(local vs web)를 확인하여 요청을 라우팅합니다.  
  * **Web 모드**: config.json에 설정된 외부 클라우드 서버로 요청을 Relay 합니다.  
  * **Local 모드**: runtime\_manager를 통해 로컬 프로세스를 Lazy Loading 방식으로 구동합니다.

### **2\. 다중 레이어 보안 우회 (Multi-Layer Security Bypass)**

브라우저의 강력한 보안 정책(CSP)으로 인해 주입된 스크립트가 차단되는 문제를 이중으로 해결합니다.

* **Layer 1 (Electron)**: index.js에서 브라우저 세션(session.webRequest) 레벨의 헤더를 1차 필터링합니다.  
* **Layer 2 (Python)**: proxy\_server.py가 트래픽을 가로채고, security.py 모듈이 남은 보안 헤더(x-frame-options 등)를 정밀하게 제거합니다.

### **3\. SPA 대응 주입기 (Injector)**

* **injector.py**: 단순 HTML 파싱을 넘어, 브라우저의 History API (pushState, replaceState)를 후킹하는 스크립트를 함께 주입합니다.  
* 이를 통해 페이지 새로고침이 없는 SPA 사이트(YouTube 등)에서도 플러그인이 문맥에 맞춰 정상적으로 재로드됩니다.

## **🔍 심층 구현 분석 (Undocumented Implementation Details)**

개발자가 문서에 적지 않았지만, 코드 퀄리티나 보안/안정성 측면에서 중요한 구현 디테일들입니다.

### **1\. 정교한 주입 필터링 (Smart Injection via Fetch Metadata)**

README는 단순히 "트래픽을 가로채어 주입"한다고 되어 있지만, 코드는 훨씬 정교하게 설계되었습니다.

* **분석**: python/core/proxy\_server.py의 response 메서드는 브라우저의 Sec-Fetch-Dest, Sec-Fetch-Mode 헤더를 검사합니다.  
* **동작**: AJAX/Fetch 요청(dest="empty"), CORS 요청, WebSocket 연결 등에는 스크립트를 주입하지 않도록 방어 로직이 구현되어 있습니다. 이는 JSON 응답이나 이미지 데이터가 주입된 스크립트로 인해 손상되는 것을 막는 매우 중요한 로직입니다.

### **2\. 적극적인 캐시 무효화 (Aggressive Cache Busting)**

* **분석**: python/core/proxy\_server.py는 응답 헤더에서 Cache-Control, Expires, ETag를 강제로 삭제합니다.  
* **의미**: 브라우저가 원본 페이지를 로컬 캐시에 저장해버리면 프록시가 주입한 스크립트가 동작하지 않을 수 있습니다. 이를 방지하기 위해 캐시를 강제로 끄는 로직이 구현되어 있는데, 이는 문서에 없는 성능/동작 관련 핵심 트릭입니다.

### **3\. Mac OS 인증서 설치 자동화 (AppleScript 활용)**

* **분석**: README는 단순히 "버튼을 클릭하여 설치"라고만 했지만, electron/main/cert-handler.js를 보면 macOS의 경우 osascript를 호출하여 구현되어 있습니다.  
* **동작**: 관리자 권한(sudo) 팝업을 띄우고 시스템 키체인에 인증서를 '신뢰할 수 있는 루트'로 등록하는 고급 스크립트가 백그라운드에서 실행됩니다.

### **4\. 동적 포트 할당 (Dynamic Port Allocation)**

* **분석**: 아키텍처 다이어그램에는 포트가 8080, 5000으로 고정된 것처럼 보이지만, 실제 코드(electron/main/index.js)는 get-port 라이브러리를 사용해 5000\~5100, 8080\~8180 범위 내에서 사용 가능한 포트를 자동으로 탐색하여 할당합니다.  
* **연동**: 이 포트 정보는 window.AIPLUGS\_API\_PORT 전역 변수로 웹 페이지에 주입되어, 스크립트가 동적으로 코어 서버에 연결하도록 설계되었습니다.

### **5\. 환경 변수 우선권 (DevOps Friendly)**

* **분석**: python/core/inference\_router.py는 config.json 설정보다 시스템 환경변수 (SYSTEM\_API\_KEY, CLOUD\_BASE\_URL)를 우선시하도록 코딩되어 있습니다.  
* **의미**: 이는 개발자가 문서화하지 않았지만, 배포 및 테스트 자동화 환경에서 설정을 유연하게 변경할 수 있도록 돕는 배포 편의 기능입니다.

## **🚀 설정 가이드 (Configuration)**

외부 서버를 사용하기 위해 config/config.json을 반드시 설정해야 합니다.

{  
  "system\_settings": {  
    "cloud\_inference": {  
      "base\_url": "\[https://api.your-real-server.com\](https://api.your-real-server.com)",  
      "system\_api\_key": "your-secure-key"  
    }  
  }  
}

## **🛠️ 실행 방법 (How to Run)**

### **1\. 필수 요구 사항**

* Node.js v16+  
* Python 3.9+ (가상환경 권장)  
* Windows 10/11 또는 macOS

### **2\. 설치 및 실행**

**의존성 설치:**

\# Python Core 의존성    
pip install \-r python/requirements.txt

\# Electron 의존성    
npm install

**애플리케이션 시작:**

npm start

* Electron이 실행되면서 Python Core만 자식 프로세스로 구동합니다.  
* **주의:** 로컬 클라우드 서버는 더 이상 자동 실행되지 않습니다.

**인증서 설치 (최초 1회):**

* 앱 대시보드에서 **"Install CA Certificate"** 버튼을 클릭하여 HTTPS 트래픽 복호화 권한을 획득합니다.

## **⚠️ 문제 해결 (Troubleshooting)**

* **외부 서버 연결 실패**:  
  * config.json의 base\_url이 올바른지 확인하십시오.  
  * 네트워크 상태 및 API 키 유효성을 점검하십시오.  
* **인터넷이 끊긴 경우**:  
  * 앱 비정상 종료 시 프록시 설정이 남을 수 있습니다.  
  * bat/reset\_proxy.bat 파일을 관리자 권한으로 실행하여 복구하십시오.