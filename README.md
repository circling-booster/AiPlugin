# **🔌 AiPlugs Platform (v2.1 Refactored)**

AiPlugs는 로컬 PC에서 실행되는 AI 플러그인 오케스트레이션 플랫폼입니다.  
사용자의 웹 브라우징 트래픽을 투명하게 가로채어(Intercept), 문맥에 맞는 AI 기능을 웹 페이지에 주입(Injection)합니다.  
이번 리팩토링 버전은 \*\*단일 책임 원칙(SRP)\*\*에 따라 코어 로직을 분리하고, **프로세스 관리의 안정성**을 강화하는 데 초점을 맞추었습니다.

## **💡 핵심 변경 사항 (Refactoring Highlights)**

1. **모듈화된 API 서버 (Modularized Server)**:  
   * 기존의 비대했던 api\_server.py를 기능별로 분해했습니다.  
   * **WebSocket 관리** $\\rightarrow$ connection\_manager.py (Zombie Connection 방지 로직 포함)  
   * **추론 라우팅** $\\rightarrow$ inference\_router.py (Local/Web 모드 분기 처리)  
2. **고도화된 런타임 관리 (Advanced Runtime Management)**:  
   * 단순한 플러그인 로딩을 넘어, 프로세스의 생명주기(Spawn/Kill)를 전담하는 runtime\_manager.py와 worker\_manager.py를 도입했습니다.  
   * **Lazy Loading**: 요청이 들어오는 순간에만 프로세스를 생성하여 리소스를 최적화합니다.  
3. **보안 로직 분리 (Security Separation)**:  
   * Mitmproxy 내부에 섞여 있던 CSP(Content Security Policy) 우회 로직을 security.py로 독립시켰습니다.

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
          
        InfRouter \--\> |Relay| Cloud\[Cloud Server\]  
    end

    subgraph "Electron App"  
        ProcessMgr\[Process Manager\] \--\> |Exec| Orch  
        Level1\_CSP\[L1 CSP Bypass\]  
    end

## **📂 프로젝트 구조 (Directory Structure)**

변경된 역할에 맞춰 파일 구조를 재정의했습니다.

AiPlugs-Project/  
├── .gitignore                   \# Git 제외 설정  
├── package.json                 \# Electron 의존성 및 스크립트  
├── bat/                         \# \[Utils\] 긴급 복구용 스크립트  
│   └── reset\_proxy.bat          \# 프록시 설정 강제 초기화  
├── config/                      \# \[Config\] 설정 파일  
│   ├── config.json              \# 시스템 설정 (포트, 클라우드 URL)  
│   └── settings.json            \# 사용자 설정 (활성 플러그인 등)  
├── electron/                    \# \[Controller\] Electron UI & Process Control  
│   ├── main/  
│   │   ├── index.js             \# 앱 진입점, L1 CSP 우회, 윈도우 관리  
│   │   ├── process-manager.js   \# Python Core/Cloud 프로세스 생명주기 관리  
│   │   └── cert-handler.js      \# HTTPS 인증서 설치 (certutil)  
│   └── renderer/                \# 대시보드 UI  
├── python/                      \# \[Core Engine\]  
│   ├── main.py                  \# Python 진입점 (Orchestrator 실행)  
│   ├── requirements.txt         \# Python 의존성  
│   ├── core/                    \# \*\*핵심 비즈니스 로직 (Refactored)\*\*  
│   │   ├── api\_server.py        \# FastAPI 진입점 (Router 조립)  
│   │   ├── connection\_manager.py\# WebSocket 연결 관리 및 좀비 커넥션 제거  
│   │   ├── inference\_router.py  \# 추론 요청 분기 (Local Process vs Cloud)  
│   │   ├── runtime\_manager.py   \# \[New\] 플러그인 프로세스 상태 관리 (Singleton)  
│   │   ├── worker\_manager.py    \# \[New\] Multiprocessing 워커 생성/관리  
│   │   ├── security.py          \# \[New\] HTTP 헤더 정화 (CSP 제거)  
│   │   ├── proxy\_server.py      \# Mitmproxy 애드온 (트래픽 필터링)  
│   │   ├── injector.py          \# SPA Hook 및 스크립트 주입  
│   │   └── plugin\_loader.py     \# 메타데이터(Manifest) 로드 및 파싱 (SRP 준수)  
│   └── utils/  
│       └── system\_proxy.py      \# Windows 시스템 프록시 제어 (WinINet)  
├── cloud\_server/                \# \[Simulation\] 클라우드 추론 서버  
└── plugins/                     \# \[Extensions\] Manifest V3 플러그인  
    ├── cloud-secure-translator/ \# Web Mode 예시  
    ├── heavy-math-solver/       \# Local Mode (Lazy Loading) 예시  
    └── spa-connection-tester/   \# SPA 대응 테스트

## **🚀 상세 컴포넌트 분석 (Deep Dive)**

### **1\. Core Logic 분리 (Python)**

기존 api\_server.py의 비대화를 해결하기 위해 역할을 분담했습니다.

* **connection\_manager.py**:  
  * SPA(Single Page Application) 특성상 페이지 이동 시 잦은 연결 끊김/재연결이 발생합니다.  
  * 이 모듈은 오래된 '좀비 연결'을 강제로 정리하고, 새로운 WebSocket 연결을 안정적으로 유지합니다.  
* **inference\_router.py**:  
  * /v1/inference/... 요청을 받아 플러그인의 모드(local vs web)를 확인합니다.  
  * **Web 모드**: cloud\_server로 요청을 Relay 합니다.  
  * **Local 모드**: runtime\_manager에게 실행 가능한 프로세스가 있는지 문의합니다.  
* **runtime\_manager.py & worker\_manager.py**:  
  * 플러그인 로더(plugin\_loader)는 이제 단순히 메타데이터만 읽습니다.  
  * 실제 프로세스 생성(spawn)과 관리(terminate)는 runtime\_manager가 담당하며, worker\_manager를 통해 독립된 메모리 공간에서 안전하게 코드를 실행합니다.

### **2\. 다중 레이어 보안 우회 (Multi-Layer Security Bypass)**

브라우저의 강력한 보안 정책(CSP)으로 인해 주입된 스크립트가 실행되지 않는 문제를 해결하기 위해 이중으로 처리합니다.

* **Layer 1 (Electron)**: index.js에서 브라우저 세션(session.webRequest) 레벨의 헤더를 1차 필터링합니다.  
* **Layer 2 (Python)**: proxy\_server.py가 트래픽을 가로채고, security.py 모듈인 **SecuritySanitizer**를 통해 남은 보안 헤더(x-frame-options 등)를 정밀하게 제거합니다.

### **3\. SPA 대응 주입기 (Injector)**

* **injector.py**: 단순 HTML 파싱을 넘어, 브라우저의 History API(pushState, replaceState)를 후킹하는 스크립트를 주입합니다.  
* 이를 통해 페이지 새로고침 없는 SPA 사이트(YouTube 등)에서도 플러그인이 정상적으로 재로드됩니다.

## **🛠️ 실행 방법 (How to Run)**

### **1\. 필수 요구 사항**

* Node.js v16+  
* Python 3.9+ (가상환경 권장)  
* Windows 10/11 (시스템 프록시 제어 API)

### **2\. 설치 및 실행**

1. **의존성 설치**:  
   \# Python 의존성  
   pip install \-r python/requirements.txt  
   pip install \-r cloud\_server/requirements.txt

   \# Electron 의존성  
   npm install

2. **애플리케이션 시작**:  
   npm start

   * Electron이 실행되면서 자동으로 Python Core와 Cloud Server를 자식 프로세스로 구동합니다.  
3. **인증서 설치 (최초 1회)**:  
   * 앱 대시보드에서 **"Install CA Certificate"** 버튼을 클릭하여 HTTPS 트래픽 복호화 권한을 획득합니다.

## **⚠️ 문제 해결 (Troubleshooting)**

* **인터넷이 끊긴 경우**:  
  * 앱이 비정상 종료되어 프록시 설정이 남아있을 수 있습니다.  
  * bat/reset\_proxy.bat 파일을 관리자 권한으로 실행하여 복구하십시오.  
* **플러그인 로딩 실패**:  
  * plugin\_loader.py는 manifest.json의 문법을 엄격하게 검사합니다. JSON 형식을 확인하세요.