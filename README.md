# **🔌 AiPlugs Platform (v2.0 Refactored)**

**AiPlugs**는 로컬 PC에서 실행되는 **AI 플러그인 오케스트레이션 플랫폼**입니다.

사용자의 웹 브라우징 트래픽을 투명하게 가로채어(Intercept), 문맥에 맞는 AI 기능을 웹 페이지에 주입(Injection)합니다.

**💡 핵심 업그레이드 사항**

* **SPA (Single Page Application) 완벽 지원**: WebSocket 및 History API 후킹을 통한 동적 페이지 대응.  
* **CSP (Content Security Policy) 이중 우회**: Electron 및 Mitmproxy 레벨에서의 강력한 보안 정책 무력화.  
* **Hybrid Inference**: 로컬 GPU(PyTorch)와 클라우드 API 간의 유연한 스위칭.  
* **Lazy Loading**: 리소스 절약을 위한 온디맨드(On-Demand) 프로세스 실행 전략.

## **🏗️ 시스템 아키텍처 (Architecture)**

이 프로젝트는 **Electron(Controller)**, **Python(Core Logic)**, **Mitmproxy(Traffic Handler)** 세 가지 핵심 축으로 구성됩니다.

graph TD  
    User\[User Browser / System\] \<--\> |Proxy :8080| Mitmproxy\[Python: Mitmproxy Core\]  
    Mitmproxy \--\> |Filter & Inject| Injector\[HTML Injection Engine\]  
      
    subgraph "AiPlugs Core (Python)"  
        API\[FastAPI Server :5000\]  
        PluginMgr\[Plugin Loader & Process Manager\]  
        LocalWorker\[Local Inference Process\]  
    end  
      
    subgraph "Electron App"  
        UI\[Dashboard UI\]  
        ProcMgr\[Process Manager\]  
        CertHandler\[Cert Installer\]  
    end  
      
    Injector \--\> |Load Script| API  
    UI \--\> |IPC| ProcMgr \--\> |Spawn/Kill| API  
    UI \--\> |IPC| CertHandler  
    API \--\> |WebSocket| User  
    API \--\> |Route: Web| Cloud\[Cloud Server\]  
    API \--\> |Route: Local| PluginMgr \--\> |Spawn| LocalWorker

## **📂 프로젝트 구조 (Directory Structure)**

현재 구현된 전체 프로젝트의 파일 구조와 역할입니다.

AiPlugs-Project/  
├── .gitignore                   \# Git 제외 설정 (logs, venv 등)  
├── package.json                 \# Electron 프로젝트 의존성 및 스크립트  
├── bat/                         \# \[Utils\] 유틸리티 배치 파일  
│   └── reset\_proxy.bat          \# 프록시 설정 강제 초기화 (긴급 복구용)  
├── config/                      \# \[Config\] 설정 파일  
│   ├── config.json              \# 시스템 설정 (포트, SSL 패스스루, 클라우드 URL)  
│   └── settings.json            \# 사용자 설정 (테마, 활성 플러그인 목록)  
├── electron/                    \# \[Electron\] UI & Process Controller  
│   ├── main/                    \# 메인 프로세스 (Backend)  
│   │   ├── index.js             \# 앱 진입점, CSP 우회(L1), 포트 할당, 윈도우 생성  
│   │   ├── process-manager.js   \# Python Core 및 Cloud Server 프로세스 생명주기 관리  
│   │   ├── cert-handler.js      \# 인증서 설치 (Windows certutil 래퍼)  
│   │   └── preload.js           \# Context Bridge (Renderer \<-\> Main IPC 보안 통신)  
│   └── renderer/                \# 렌더러 프로세스 (Frontend)  
│       ├── index.html           \# 대시보드 UI HTML  
│       └── renderer.js          \# 대시보드 로직 (로그 표시, 상태 모니터링, IPC 호출)  
├── python/                      \# \[Core\] Python Engine (Localhost)  
│   ├── main.py                  \# Python 진입점 (Mitmproxy \+ API Server 구동)  
│   ├── requirements.txt         \# Core용 Python 의존성 (mitmproxy, fastapi 등)  
│   ├── core/                    \# 핵심 비즈니스 로직  
│   │   ├── api\_server.py        \# FastAPI Gateway (WebSocket 관리, 추론 라우팅)  
│   │   ├── proxy\_server.py      \# Mitmproxy 애드온 (트래픽 필터링, CSP 우회 L2)  
│   │   ├── injector.py          \# 고속 HTML 파싱 및 스크립트 주입 (Regex, SPA Hook)  
│   │   └── plugin\_loader.py     \# 플러그인 로드, 유효성 검사(Manifest V3), Lazy Loading  
│   └── utils/                   \# 시스템 유틸리티  
│       └── system\_proxy.py      \# Windows 시스템 프록시 제어 (WinINet API 직접 호출)  
├── cloud\_server/                \# \[Cloud\] Web Inference Simulator  
│   ├── main.py                  \# Cloud API 서버 (Web Mode 요청 중계 테스트용)  
│   └── requirements.txt         \# Cloud 서버용 의존성  
└── plugins/                     \# \[Plugins\] 확장 기능 (Manifest V3 표준)  
    ├── cloud-secure-translator/ \# \[Web-Only\] 보안 번역기 플러그인  
    │   ├── manifest.json  
    │   ├── content.js  
    │   └── web\_backend.py       \# 클라우드 번역 API 호출 핸들러  
    ├── heavy-math-solver/       \# \[Local-Only\] 고연산 작업 플러그인  
    │   ├── manifest.json  
    │   ├── content.js  
    │   └── backend.py           \# Lazy Loading 테스트용 (3초 지연 초기화 시뮬레이션)  
    └── spa-connection-tester/   \# \[Test\] SPA 페이지 이동 감지 테스트  
        ├── manifest.json  
        ├── content.js           \# History API 이벤트 리스너 포함  
        └── backend.py           \# WebSocket 연결 유지 테스트용

### **📁 주요 파일 역할 상세 분석**

#### **1\. 🖥️ Electron (electron/)**

애플리케이션의 껍데기이자 관리자 역할을 합니다.

* **process-manager.js**: Python 백엔드가 죽지 않도록 감시하고, 앱 종료 시 tree-kill을 통해 자식 프로세스까지 깔끔하게 정리합니다. 로그를 실시간으로 UI로 파이핑(Piping)합니다.  
* **cert-handler.js**: HTTPS 트래픽 복호화를 위해 필수적인 Mitmproxy 루트 인증서를 사용자의 '신뢰할 수 있는 루트 인증 기관' 저장소에 등록합니다.  
* **index.js**: 브라우저 세션(session.webRequest) 레벨에서 보안 헤더를 조작하여 플러그인 스크립트 실행을 차단하는 CSP를 1차적으로 무력화합니다.

#### **2\. 🐍 Python Core (python/)**

실제 트래픽을 처리하고 AI를 구동하는 엔진입니다.

* **main.py**: API Server(스레드)와 Mitmproxy(비동기 루프)를 동시에 실행하는 오케스트레이터입니다.  
* **core/proxy\_server.py**: RequestFilter 클래스를 통해 정규식 기반으로 주입 대상 URL을 고속으로 판별(O(1))합니다. 응답 헤더에서 Content-Security-Policy를 제거하는 2차 우회 로직이 포함되어 있습니다.  
* **core/injector.py**: BeautifulSoup 대신 정규식(re)을 사용하여 HTML 파싱 오버헤드를 최소화했습니다. 특히 history.pushState를 후킹하는 스크립트를 주입하여 SPA 사이트에서의 동작을 보장합니다.  
* **core/plugin\_loader.py**: 플러그인을 메모리에 로드하고, ensure\_process\_running을 통해 요청이 있을 때만 로컬 프로세스를 생성(Lazy Loading)하여 메모리를 절약합니다.  
* **utils/system\_proxy.py**: winreg와 ctypes를 사용하여 윈도우 시스템 설정을 직접 제어, 별도 설정 없이 브라우저 트래픽을 잡을 수 있게 합니다.

#### **3\. 🧩 Plugins (plugins/)**

각각의 기능을 담은 독립적인 모듈들입니다. Manifest V3 구조를 따릅니다.

* **manifest.json**: 플러그인의 권한, 타겟 URL, 실행 모드(local 또는 web)를 정의합니다.  
* **backend.py (Local)**: 로컬 Python 프로세스에서 실행될 코드입니다. Lazy Loading에 의해 호출 시점에 메모리에 적재됩니다.  
* **web\_backend.py (Cloud)**: Cloud Server 환경에서 실행될 코드로, 클라이언트의 요청을 받아 처리합니다.

## **🚀 주요 기능 및 작동 흐름 (Workflow)**

### **1\. 트래픽 가로채기 및 스크립트 주입**

1. 사용자가 브라우저에서 웹사이트 접속.  
2. **Mitmproxy**가 요청을 가로채고 RequestFilter가 URL 패턴 매칭.  
3. 매칭 성공 시 injector.py가 동작하여 HTML에 다음을 주입:  
   * **Loader Script**: SPA 탐지용 History Hook, WebSocket 설정.  
   * **Content Script**: 플러그인별 UI/로직 JS.  
4. 동시에 **CSP Bypass** 로직이 응답 헤더의 보안 정책을 삭제하여 스크립트 차단을 방지.

### **2\. 하이브리드 추론 (Hybrid Inference)**

* **Local Mode**: 사용자가 기능을 실행하면 PluginLoader가 해당 플러그인의 backend.py를 독립 프로세스로 실행(Lazy Load)하고 결과를 반환.  
* **Web Mode**: api\_server가 요청을 받아 설정된 config.json의 클라우드 주소로 HTTP 요청을 중계(Relay).

## **🛠️ 개발 및 실행 가이드**

### **1\. 필수 요구 사항 (Prerequisites)**

* **Node.js**: v16 이상  
* **Python**: 3.9 이상  
* **Windows**: 10/11 (시스템 프록시 제어 API 호환성)

### **2\. 설치 및 실행 (Installation)**

\# 1\. 의존성 설치 (Root 디렉토리)  
npm install

\# 2\. Python 가상환경 설정 (권장)  
python \-m venv .venv  
\# 윈도우:  
.venv\\Scripts\\activate   
\# 라이브러리 설치  
pip install \-r python/requirements.txt  
pip install \-r cloud\_server/requirements.txt

\# 3\. 애플리케이션 실행  
npm start  
