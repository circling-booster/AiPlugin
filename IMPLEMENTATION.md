# **🏗️ AiPlugs Implementation Details**

이 문서는 \*\*AiPlugs Platform (v2.4 Stability Edition)\*\*의 내부 아키텍처, 디렉토리 구조, 상세 컴포넌트 분석 및 플러그인 개발 가이드를 다룹니다.

## **시스템 아키텍처 (Architecture)**

graph TD  
    User\[User Browser\] \<--\> |Proxy :8080| Mitmproxy\[Python Proxy Core\]  
    Mitmproxy \--\> |Normalization| TrafficNorm\[Traffic Normalizer\]  
    TrafficNorm \--\> |Inject| Injector\[HTML Injector\]  
    Mitmproxy \--\> |Sanitize| Security\[Security Sanitizer\]

    subgraph "AiPlugs Core (Python)"  
        Orch\[Orchestrator\] \--\> API\_Main\[API Server :5000\]  
          
        API\_Main \--\> SmartRouter\[Smart Sandboxing Router\]  
        SmartRouter \--\> |Auto-Wrap| PluginFiles\[Plugin JS Files\]

        API\_Main \--\> InfRouter\[Inference Router\]  
          
        InfRouter \--\> |Request Proc| RuntimeMgr\[Runtime Manager\]  
          
        RuntimeMgr \-- Check/Download \--\> ModelRegistry\[/models Directory/\]  
        RuntimeMgr \--\> |Inject Env| WorkerMgr\[Worker Manager\]  
          
        WorkerMgr \--\> |Spawn| LocalProc\[Local Plugin Process\]  
        LocalProc \-.- \--\> |Load| ModelRegistry  
              
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
│   ├── cloud-secure-translator/ \# \[예시\] 클라우드 번역 플러그인 (Web Mode)  
│   ├── heavy-math-solver/       \# \[예시\] 연산 플러그인 (Local Mode)  
│   └── spa-connection-tester/   \# \[예시\] SPA 연결 테스트 플러그인  
└── python/                      \# Python Core Engine  
    ├── main.py                  \# Python 엔트리포인트 (Orchestrator 실행)  
    ├── requirements.txt         \# Python 의존성 목록  
    ├── core/                    \# 핵심 모듈  
    │   ├── api\_server.py        \# \[Enhanced\] 스마트 샌드박싱 라우터 탑재  
    │   ├── connection\_manager.py \# WebSocket 연결 관리 (Zombie Killer 포함)  
    │   ├── inference\_router.py  \# 추론 요청 라우팅 (Local/Web 분기)  
    │   ├── injector.py          \# HTML 스크립트 주입기 (SPA Hook 포함)  
    │   ├── orchestrator.py      \# 전체 시스템 조율 (API 서버 \+ Proxy 서버 실행)  
    │   ├── plugin\_loader.py     \# 플러그인 메타데이터 로드 및 관리  
    │   ├── proxy\_server.py      \# \[Enhanced\] 프로토콜 정규화 및 최적화  
    │   ├── runtime\_manager.py   \# 모델 자동 다운로드 및 무결성 검증  
    │   ├── schemas.py           \# Pydantic 데이터 모델 (Manifest 등)  
    │   ├── security.py          \# 보안 헤더(CSP) 정화 로직  
    │   └── worker\_manager.py    \# 로컬 플러그인 프로세스 격리 실행  
    └── utils/  
        └── system\_proxy.py      \# 시스템 프록시 설정 (Win/Mac 레지스트리/네트워크 설정)

## **🚀 상세 컴포넌트 분석 (Deep Dive)**

### **1\. Smart Sandboxing Middleware (api\_server.py)**

기존의 단순 정적 파일 서빙(StaticFiles) 방식은 플러그인 간 전역 변수 충돌(Global Namespace Pollution) 위험이 있었습니다. v2.4에서는 **지능형 미들웨어**가 이를 해결합니다.

* **IIFE 자동 래핑 (Auto-Wrapping)**:  
  * .js 파일 요청 시, 서버가 즉시 파일 내용을 읽어 (function() { ... })(); 블록으로 감쌉니다.  
  * **효과**: 플러그인 개발자가 var config \= ...;와 같이 코딩하더라도, 이 변수는 해당 함수 스코프 내에 갇히게 되어 멜론 티켓 등 원본 사이트의 변수와 충돌하지 않습니다.  
  * **디버깅 지원**: //\# sourceURL=aiplugs://... 주석을 자동으로 추가하여, 개발자 도구에서는 원본 파일명으로 깔끔하게 표시됩니다.  
* **Path Traversal 방어**:  
  * os.path.abspath를 사용하여 요청된 경로가 플러그인 디렉토리를 벗어나려는 시도(../../system32)를 엄격하게 차단합니다.

### **2\. Traffic Normalizer (proxy\_server.py)**

mitmproxy를 통한 트래픽 조작 시 가장 큰 문제는 **데이터 무결성**과 **프로토콜 호환성**입니다. v2.4는 이를 위한 정규화 로직을 탑재했습니다.

* **강제 디코딩 (Mandatory Decoding)**:  
  * flow.response.decode()를 호출하여 Gzip, Brotli 등으로 압축된 데이터를 평문으로 변환합니다. 이는 스크립트 주입 시 바이너리 데이터가 깨지는 현상을 방지합니다.  
* **헤더 정규화 (Header Normalization \- Plan A)**:  
  * **Content-Length 재계산**: 스크립트 주입으로 본문 길이가 늘어나면 브라우저가 데이터를 덜 읽거나 무한 대기(Hanging)하는 문제가 발생합니다. 수정된 본문의 바이트 길이를 정확히 계산하여 헤더를 갱신합니다.  
  * **Transfer-Encoding 제거**: 데이터 길이를 명시(Content-Length)했으므로, 충돌을 방지하기 위해 chunked 인코딩 헤더를 삭제합니다.  
* **I/O 최적화**: 디버깅용 파일 쓰기 로직을 제거하여 고성능 Non-Blocking I/O를 보장합니다.

### **3\. Runtime Manager (Auto-Provisioning Engine)**

* **역할**: 플러그인이 실행(Lazy Loading)되기 직전에 개입하여, manifest.json의 inference.models 섹션을 분석합니다.  
* **Atomic Download**:  
  * requests 라이브러리를 사용해 스트리밍 다운로드를 수행하며, .part 임시 파일을 사용하여 다운로드 중단 시 불완전 파일 생성을 방지합니다.  
  * 다운로드 완료 후 SHA256 해시를 검증하고, 검증에 성공해야만 원래 파일명으로 변경(shutil.move)합니다.  
* **Environment Mapping**: 준비된 모델 파일의 절대 경로를 환경변수(예: MATH\_MODEL\_PATH)로 변환하여 Worker Manager에게 전달합니다.

### **4\. 기존 보안 및 인젝션 로직 (Legacy Core)**

* **Security Separation (다중 레이어 보안 우회)**:  
  * **Layer 1 (Electron)**: session.webRequest를 통해 브라우저 세션 레벨의 1차 필터링을 수행합니다.  
  * **Layer 2 (Python)**: security.py 모듈이 mitmproxy를 통해 남은 보안 헤더(CSP 등)를 정밀하게 제거하여 주입된 스크립트 실행을 보장합니다.  
* **SPA Injector**: injector.py는 브라우저의 History API를 후킹하는 코드를 함께 주입하여, 페이지 새로고침 없는 URL 변경도 감지합니다.

## **🔍 심층 구현 분석 (Undocumented Implementation Details)**

### **1\. 정교한 주입 필터링 (Smart Injection via Fetch Metadata)**

* **분석**: proxy\_server.py의 response 메서드는 브라우저의 Sec-Fetch-Dest, Sec-Fetch-Mode 헤더를 검사합니다.  
* **동작**: AJAX/Fetch 요청(dest="empty"), CORS 요청, WebSocket 연결 등에는 스크립트를 주입하지 않도록 방어 로직이 구현되어 있습니다. 이는 JSON 응답이나 이미지 데이터가 주입된 스크립트로 인해 손상되는 것을 막는 매우 중요한 로직입니다.

### **2\. 적극적인 캐시 무효화 (Aggressive Cache Busting)**

* **분석**: proxy\_server.py는 응답 헤더에서 Cache-Control, Expires, ETag를 강제로 삭제합니다.  
* **의미**: 브라우저는 성능을 위해 한 번 받은 파일(스크립트 포함)을 캐싱하려 합니다. 플러그인 개발/업데이트 시 변경 사항이 즉시 반영되도록 강제하기 위해 캐시 관련 헤더를 제거합니다.

### **3\. Mac OS 인증서 설치 자동화 (AppleScript 활용)**

* **분석**: electron/main/cert-handler.js를 보면 macOS의 경우 osascript를 호출하여 구현되어 있습니다.  
* **동작**: 관리자 권한(sudo) 팝업을 띄우고 시스템 키체인에 인증서를 '신뢰할 수 있는 루트'로 등록하는 고급 스크립트가 백그라운드에서 실행됩니다.

## **👨‍💻 플러그인 개발 가이드 (Plugin Development)**

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
