# **🏗️ AiPlugs Implementation Details**

이 문서는 \*\*AiPlugs Platform (v2.3)\*\*의 내부 아키텍처, 디렉토리 구조, 상세 컴포넌트 분석 및 플러그인 개발 가이드를 다룹니다.

## **시스템 아키텍처 (Architecture)**

graph TD    
    User\[User Browser\] \<--\> |Proxy :8080| Mitmproxy\[Python Proxy Core\]    
    Mitmproxy \--\> |Sanitize| Security\[Security Sanitizer\]    
    Mitmproxy \--\> |Inject| Injector\[HTML Injector\]

    subgraph "AiPlugs Core (Python)"    
        Orch\[Orchestrator\] \--\> API\_Main\[API Server :5000\]    
            
        API\_Main \--\> InfRouter\[Inference Router\]    
            
        InfRouter \--\> |Request Proc| RuntimeMgr\[Runtime Manager\]    
            
        RuntimeMgr \-- Check/Download \--\> ModelRegistry\[/models Directory/\]    
        RuntimeMgr \--\> |Inject Env| WorkerMgr\[Worker Manager\]    
            
        WorkerMgr \--\> |Spawn| LocalProc\[Local Plugin Process\]    
        LocalProc \-.-\> |Load| ModelRegistry    
                
        InfRouter \--\> |Relay (HTTP)| External\_Cloud\[External AI Server\]    
    end

    subgraph "Electron App"    
        ProcessMgr\[Process Manager\] \--\> |Exec| Orch    
    end

## **📂 프로젝트 구조 (Directory Structure)**

AiPlugs-Project/  
├── .gitattributes  
├── .gitignore  
├── README.md  
├── package.json  
├── package-lock.json  
├── bat/  
│   └── reset\_proxy.bat          \# 윈도우 프록시 강제 초기화 스크립트  
├── config/  
│   ├── config.json              \# 시스템 설정 (포트, 클라우드 URL 등)  
│   └── settings.json            \# 사용자 설정 (활성화된 플러그인 등)  
├── electron/  
│   ├── main/                    \# Electron 메인 프로세스  
│   │   ├── index.js             \# 앱 진입점 (창 생성, 포트 할당)  
│   │   ├── process-manager.js   \# Python Core 및 자식 프로세스 생명주기 관리  
│   │   ├── cert-handler.js      \# HTTPS 인증서 설치 핸들러 (Win/Mac)  
│   │   └── preload.js           \# Context Bridge (Renderer \<-\> Main 통신)  
│   └── renderer/                \# Electron 렌더러 프로세스 (UI)  
│       ├── index.html           \# 대시보드 UI  
│       └── renderer.js          \# 로그 출력 및 상태 표시 로직  
├── models/                      \# \[NEW\] AI 모델 중앙 저장소 (Auto-Provisioning 대상)  
│   └── .gitkeep  
├── plugins/                     \# 플러그인 디렉토리  
│   ├── captchaSolver/           \# \[예시\] 캡챠 해결 플러그인  
│   │   ├── backend.py  
│   │   ├── manifest.json  
│   │   └── test.js  
│   ├── cloud-secure-translator/ \# \[예시\] 클라우드 번역 플러그인 (Web Mode)  
│   │   ├── content.js  
│   │   ├── manifest.json  
│   │   └── web\_backend.py  
│   ├── heavy-math-solver/       \# \[예시\] 연산 플러그인 (Local Mode)  
│   │   ├── backend.py  
│   │   ├── manifest.json  
│   │   └── thisscript.js  
│   └── spa-connection-tester/   \# \[예시\] SPA 연결 테스트 플러그인  
│       ├── backend.py  
│       ├── content.js  
│       └── manifest.json  
└── python/                      \# Python Core Engine  
    ├── main.py                  \# Python 엔트리포인트 (Orchestrator 실행)  
    ├── requirements.txt         \# Python 의존성 목록  
    ├── core/                    \# 핵심 모듈  
    │   ├── api\_server.py        \# FastAPI 서버 (플러그인 정적 파일 및 API 서빙)  
    │   ├── connection\_manager.py \# WebSocket 연결 관리 (Zombie Killer 포함)  
    │   ├── inference\_router.py  \# 추론 요청 라우팅 (Local/Web 분기)  
    │   ├── injector.py          \# HTML 스크립트 주입기 (SPA Hook 포함)  
    │   ├── orchestrator.py      \# 전체 시스템 조율 (API 서버 \+ Proxy 서버 실행)  
    │   ├── plugin\_loader.py     \# 플러그인 메타데이터 로드 및 관리  
    │   ├── proxy\_server.py      \# Mitmproxy 애드온 (트래픽 인터셉트 & 필터링)  
    │   ├── runtime\_manager.py   \# \[CORE\] 모델 자동 다운로드 및 무결성 검증  
    │   ├── schemas.py           \# Pydantic 데이터 모델 (Manifest 등)  
    │   ├── security.py          \# 보안 헤더(CSP) 정화 로직  
    │   └── worker\_manager.py    \# 로컬 플러그인 프로세스 격리 실행  
    └── utils/  
        └── system\_proxy.py      \# 시스템 프록시 설정 (Win/Mac 레지스트리/네트워크 설정)

## **🚀 상세 컴포넌트 분석 (Deep Dive)**

### **1\. Runtime Manager (Auto-Provisioning Engine)**

* **역할**: 플러그인이 실행(Lazy Loading)되기 직전에 개입하여, manifest.json의 inference.models 섹션을 분석합니다.  
* **Atomic Download**:  
  * requests 라이브러리를 사용해 스트리밍 다운로드를 수행합니다.  
  * 다운로드 중에는 filename.part라는 임시 이름을 사용하여, 다운로드가 불완전하게 끝난 파일이 사용되는 것을 방지합니다.  
  * 다운로드 완료 후 SHA256 해시를 검증하고, 검증에 성공해야만 원래 파일명으로 변경(shutil.move)합니다.  
* **Environment Mapping**: 준비된 모델 파일의 절대 경로를 키-값 쌍(예: {"MATH\_MODEL": "C:/.../models/math.pt"})으로 변환하여 Worker Manager에게 전달합니다.

### **2\. Manifest-Driven Architecture**

* 플러그인 개발자는 더 이상 수백 MB의 모델 파일을 저장소에 올릴 필요가 없습니다.  
* manifest.json에 **다운로드 URL**과 **해시값**만 명시하면, 나머지는 플랫폼이 알아서 처리합니다.

### **3\. 기존 보안 및 인젝션 로직 (Legacy Core)**

* **Security Separation (다중 레이어 보안 우회)**:  
  * **Layer 1 (Electron)**: index.js에서 session.webRequest를 통해 브라우저 세션 레벨의 1차 필터링을 수행합니다.  
  * **Layer 2 (Python)**: security.py 모듈이 mitmproxy를 통해 남은 보안 헤더(Content-Security-Policy, X-Frame-Options 등)를 정밀하게 제거하여 주입된 스크립트 실행을 보장합니다.  
* **SPA Injector**: injector.py는 브라우저의 History API를 후킹하는 코드를 함께 주입하여, 페이지 새로고침 없는 URL 변경도 감지합니다.

### **4\. Connection Manager (Websocket Control)**

* **좀비 연결 방지 (Zombie Connection Killer)**:  
  * connection\_manager.py는 SPA 환경 특성상 잦은 페이지 이동으로 발생하는 '좀비 연결' 문제를 해결합니다.  
  * 동일한 plugin\_id와 client\_id로 새로운 연결 요청이 오면, 기존의 오래된 WebSocket 세션을 강제로 종료하고 새 세션을 안정적으로 유지합니다.

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

* **분석**: electron/main/cert-handler.js를 보면 macOS의 경우 osascript를 호출하여 구현되어 있습니다.  
* **동작**: 관리자 권한(sudo) 팝업을 띄우고 시스템 키체인에 인증서를 '신뢰할 수 있는 루트'로 등록하는 고급 스크립트가 백그라운드에서 실행됩니다.

### **4\. 동적 포트 할당 (Dynamic Port Allocation)**

* **분석**: 실제 코드(electron/main/index.js)는 get-port 라이브러리를 사용해 5000\~5100, 8080\~8180 범위 내에서 사용 가능한 포트를 자동으로 탐색하여 할당합니다.  
* **연동**: 이 포트 정보는 window.AIPLUGS\_API\_PORT 전역 변수로 웹 페이지에 주입되어, 스크립트가 동적으로 코어 서버에 연결하도록 설계되었습니다.

### **5\. 환경 변수 우선권 (DevOps Friendly)**

* **분석**: python/core/inference\_router.py는 config.json 설정보다 시스템 환경변수 (SYSTEM\_API\_KEY, CLOUD\_BASE\_URL)를 우선시하도록 코딩되어 있습니다.  
* **의미**: 이는 배포 및 테스트 자동화 환경에서 설정을 유연하게 변경할 수 있도록 돕는 기능입니다.

## **👨‍💻 플러그인 개발 가이드 (Plugin Development)**

이제 모델 파일 없이 가볍게 플러그인을 배포할 수 있습니다.

### **A. manifest.json 작성**

inference 섹션에 models 리스트를 추가하십시오.

{    
    "manifest\_version": 3,    
    "id": "super-vision",    
    "name": "Super Vision Object Detector",    
    "inference": {    
        "default\_mode": "local",    
        "local\_entry": "backend.py",    
        "models": \[    
            {    
                "key": "YOLO\_MODEL\_PATH",    
                "filename": "yolov8n.pt",    
                "source\_url": "\[https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt\](https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt)",    
                "sha256": "d41d8cd98f00b204e9800998ecf8427e..."    
            }    
        \]    
    },    
    "content\_scripts": \[ ... \]    
}

### **B. backend.py 작성**

Core가 주입해 준 환경변수(key)를 통해 파일 경로에 접근합니다.

import os    
import sys

\# Core가 자동으로 다운로드하고 경로를 환경변수에 넣어줍니다.    
MODEL\_PATH \= os.getenv("YOLO\_MODEL\_PATH")

if not MODEL\_PATH or not os.path.exists(MODEL\_PATH):    
    print("Error: Model file not found\!", file=sys.stderr)    
    sys.exit(1)

print(f"Loading Model from: {MODEL\_PATH}")    
\# model \= load\_model(MODEL\_PATH)

def run(payload):    
    return {"result": "Model Loaded Successfully"}  
