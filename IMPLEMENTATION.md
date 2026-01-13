# **🏗️ AiPlugs Implementation Details (v3.0 Hybrid SOA & v2.6 Multi-Tab)**

이 문서는 AiPlugs Platform의 내부 아키텍처를 상세히 다룹니다.  
v3.0의 \*\*Hybrid AI SOA (Service Oriented Architecture)\*\*와 v2.6의 Multi-Tab Manager가 어떻게 유기적으로 결합되어 있는지 기술적 세부 사항을 포함합니다.

## **🏛️ 통합 시스템 아키텍처 (Unified Architecture)**

시스템은 크게 **사용자 인터페이스(Electron)**, **탭 관리자(Multi-Tab Manager)**, 그리고 \*\*하이브리드 AI 백엔드(Python Core)\*\*로 구성됩니다.

### **Architecture Diagram**

graph TD  
    subgraph "Electron Main Process"  
        UI\[Renderer UI\] \-- IPC \--\> TabMgr\[Tab Manager\]  
        TabMgr \-- Manage \--\> Views\[BrowserViews (Multi-Tab)\]  
        Bypass\[Security Bypass\] \-- Intercept \--\> Views  
    end

    subgraph "Web Content"  
        Page\[Web Page\] \-- 1\. Fetch (AJAX) \--\> Gateway\[API Server\]  
        Page \-- Injected \--\> Var\[window.\_\_AI\_API\_BASE\_URL\_\_\]  
    end

    subgraph "Python Core (Hybrid)"  
        Gateway \-- Route \--\> Router{Execution Type?}  
          
        %% v3.0 SOA Path  
        Router \-- "None (SOA)" \--\> Engine\[Core AI Engine\]  
        Engine \-- Direct Call \--\> Model\[Shared PyTorch Model\]  
          
        %% v2.6 Legacy Path  
        Router \-- "Process (Legacy)" \--\> IPC\[Process Manager\]  
        IPC \-- Pipe \--\> Worker\[Plugin Subprocess\]  
          
        %% Orchestration  
        Orch\[Orchestrator\] \-- Control \--\> Gateway  
        Orch \-- Control \--\> Proxy\[Optional Proxy Server\]  
    end

## **🧩 주요 컴포넌트 상세 (Component Details)**

### **1\. Hybrid AI Engine (python/core/ai\_engine.py) \[v3.0\]**

* **역할**: 시스템 전체에서 공유되는 고성능 AI 모델의 호스팅 컨테이너입니다.  
* **Lazy Loading & Persistence**: 요청 시 모델을 메모리에 로드하고, 글로벌 변수를 통해 워커 프로세스 내에 캐싱하여 재사용합니다.  
* **Concurrency Model**: ProcessPoolExecutor(max\_workers=1)를 사용하여 단일 워커로 동작합니다. 이는 다수의 플러그인이 동시에 실행될 때 발생하던 메모리 부족(OOM) 및 CPU 스레싱(Thrashing)을 방지합니다.

### **2\. Multi-Tab Manager (electron/main/managers/tab-manager.js) \[v2.6\]**

* **BrowserView 격리**: Electron의 BrowserView API를 사용하여 각 탭을 독립된 프로세스 뷰로 관리합니다.  
* **State Sync**: 탭 전환 시 active 탭과 background 탭의 뷰 포트를 즉시 교체(swap)하며, URL 및 타이틀 상태를 Renderer 프로세스와 동기화합니다.  
* **Memory Management**: 닫힌 탭의 BrowserView는 즉시 파괴(destroy)되어 누수를 방지합니다.

### **3\. Dynamic Injection & Security (injector.py & security-bypass.js) \[Integrated\]**

* **Injection**: injector.py는 HTML 응답에 window.\_\_AI\_API\_BASE\_URL\_\_ (동적 API 포트)을 주입합니다.  
* **CORS/CSP Bypass**: security-bypass.js는 Electron의 onHeadersReceived 이벤트를 훅(Hook)하여, 웹 페이지가 로컬 API 서버(127.0.0.1)로 데이터를 전송할 때 차단되지 않도록 보안 헤더(Content-Security-Policy)를 제거합니다.

### **4\. API Gateway & Router (api\_server.py) \[Updated\]**

* **Unified Endpoint**: 모든 추론 요청은 /v1/inference/{plugin\_id}/{function\_name}으로 수신됩니다.  
* **Smart Routing**: runtime\_manager를 통해 플러그인 타입을 확인하고, **Direct Call (SOA)** 또는 **IPC Relay (Legacy)** 중 적절한 경로로 요청을 전달합니다.

## **📂 디렉토리 및 파일 구조 (Directory Structure)**

전체 시스템의 폴더 구조는 다음과 같습니다.

AiPlugs/  
├── config/  
│   ├── config.json            \# \[Updated\] AI 엔진 및 시스템 설정  
│   └── settings.json          \# \[Retained\] 사용자 테마 및 플러그인 활성화 설정  
├── electron/  
│   ├── main/  
│   │   ├── managers/  
│   │   │   └── tab-manager.js \# \[v2.6\] 멀티 탭 관리자  
│   │   ├── security-bypass.js \# \[v3.0\] CSP/CORS 보안 우회  
│   │   ├── process-manager.js \# Python 프로세스 생명주기 관리  
│   │   └── index.js           \# Electron 진입점  
│   └── renderer/              \# UI 소스코드  
├── python/  
│   ├── core/  
│   │   ├── ai\_engine.py       \# \[v3.0\] 중앙 AI 추론 엔진 (PyTorch)  
│   │   ├── api\_server.py      \# \[Updated\] 통합 API 게이트웨이  
│   │   ├── injector.py        \# \[Updated\] 동적 포트 주입기  
│   │   ├── orchestrator.py    \# 시스템 오케스트레이터  
│   │   ├── plugin\_loader.py   \# 플러그인 로더  
│   │   ├── proxy\_server.py    \# \[v2.6\] 레거시 지원용 프록시 서버  
│   │   ├── worker\_manager.py  \# 프로세스/더미 워커 관리  
│   │   └── schemas.py         \# 데이터 모델 (Pydantic)  
│   ├── utils/  
│   └── main.py                \# Python 진입점  
├── plugins/  
│   ├── captcha\_solver/        \# \[v3.0 SOA Example\]  
│   │   ├── manifest.json  
│   │   └── content.js  
│   └── legacy\_plugin/         \# \[v2.6 Process Example\]  
│       └── backend.py  
├── requirements.txt           \# \[Updated\] Torch 등 의존성 목록  
├── package.json  
├── README.md  
└── IMPLEMENTATION.md

## **👨‍💻 플러그인 개발 가이드 (Unified Guide)**

v3.0 환경에서는 플러그인의 목적에 따라 두 가지 개발 방식을 선택할 수 있습니다.

### **Type A. SOA Mode (권장: AI 추론 위주)**

중앙 AI 엔진을 활용하여 가볍고 빠르게 동작합니다.

**1\. manifest.json**

{  
  "id": "my\_ai\_tool",  
  "inference": {  
    "execution\_type": "none",  // 프로세스 생성 안 함  
    "models": \[{ "key": "MY\_MODEL", "filename": "model.pt" }\]  
  }  
}

**2\. content.js (Frontend)**

async function analyze(data) {  
    const apiBase \= window.\_\_AI\_API\_BASE\_URL\_\_;  
    const res \= await fetch(\`${apiBase}/v1/inference/my\_ai\_tool/run\`, {  
        method: "POST",  
        body: JSON.stringify({ payload: data })  
    });  
    return await res.json();  
}

### **Type B. Legacy Process Mode (상태 관리 위주)**

v2.6 방식 그대로, 독립된 프로세스에서 복잡한 로직을 수행합니다.

**1\. manifest.json**

{  
  "id": "complex\_tool",  
  "requires\_proxy": true,      // (선택) 프록시 필요 시  
  "inference": {  
    "execution\_type": "process", // 프로세스 생성 (기본값)  
    "local\_entry": "backend.py"  
  }  
}

**2\. backend.py (Python)**

def run(payload):  
    \# 독립 프로세스에서 실행됨  
    return {"status": "processed\_in\_legacy\_mode"}  
