# **🔌 AiPlugs Platform (v2.3 Auto-Provisioning Edition)**

**AiPlugs**는 로컬 PC에서 실행되는 지능형 AI 플러그인 오케스트레이션 플랫폼입니다.

사용자의 웹 브라우징 트래픽을 투명하게 가로채어(Intercept), 문맥에 맞는 AI 기능을 웹 페이지에 주입(Injection)합니다.

이번 **v2.3 버전**은 대용량 AI 모델을 효율적으로 관리하기 위한 \*\*중앙 모델 저장소(Model Registry)\*\*와 실행 시점에 필요한 리소스를 자동으로 확보하는 **자동 프로비저닝(Auto-Provisioning)** 아키텍처가 도입되었습니다.

## **💡 핵심 변경 사항 (v2.3 Highlights)**

1. **중앙 모델 저장소 (Central Model Registry)**:  
   * 각 플러그인 폴더에 거대한 모델 파일(.pt, .onnx 등)을 포함할 필요가 없습니다.  
   * 모든 모델은 프로젝트 루트의 /models 디렉토리에서 중앙 관리되며, 플러그인 간에 공유될 수 있습니다.  
2. **자동 프로비저닝 & 무결성 검증 (Auto-Provisioning)**:  
   * **RuntimeManager**가 플러그인 실행 시점에 필요한 모델 파일의 존재 여부를 확인합니다.  
   * 파일이 없으면 manifest.json에 정의된 URL에서 **자동으로 다운로드**하며, **SHA256 해시**를 통해 무결성을 검증합니다.  
   * **Atomic Write**: 다운로드 중 중단되거나 동시 요청이 발생해도 파일이 깨지지 않도록 .part 파일과 이름 변경(Rename) 방식을 사용합니다.  
3. **환경변수 주입 (Environment Injection)**:  
   * 플러그인 코드는 모델 파일의 실제 물리적 경로를 알 필요가 없습니다.  
   * 플랫폼이 다운로드 완료된 모델의 절대 경로를 환경변수(예: MATH\_MODEL\_PATH)로 주입해 줍니다.  
4. **기존 핵심 기능 유지**:  
   * **SPA 지원**: YouTube 등 단일 페이지 애플리케이션에서도 정상 작동합니다.  
   * **보안 우회**: 강력한 CSP(Content Security Policy)를 Electron과 Python 이중 레이어에서 우회합니다.  
   * **스마트 인젝션**: Fetch/XHR 요청을 제외하고 HTML 문서에만 스크립트를 주입합니다.

## **🏗️ 시스템 아키텍처 (Architecture)**

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
├── models/                  \# \[NEW\] 중앙 모델 저장소 (Git 제외, .gitkeep만 유지)  
│   └── .gitkeep  
├── plugins/                 \# 플러그인 소스코드 (모델 파일 없음)  
│   ├── heavy-math-solver/   \# Manifest에 모델 URL만 선언  
│   └── ...  
├── python/                  \# \[Core Engine\]  
│   ├── core/  
│   │   ├── runtime\_manager.py \# \[CORE\] 모델 다운로드 및 검증, 경로 주입  
│   │   ├── worker\_manager.py  \# \[CORE\] 환경변수 주입 및 프로세스 실행  
│   │   ├── schemas.py         \# \[CORE\] 모델 의존성 스키마 정의  
│   │   ├── proxy\_server.py    \# \[CORE\] 스마트 인젝션 및 캐시 제어  
│   │   ├── security.py        \# \[CORE\] 보안 헤더 정화  
│   │   ├── connection\_manager.py \# \[CORE\] WebSocket 연결 관리  
│   │   ├── injector.py        \# \[CORE\] SPA Hook 및 스크립트 주입  
│   │   └── ...  
│   ├── requirements.txt     \# requests 라이브러리 추가됨  
│   └── ...  
├── config/                  \# 설정 파일  
└── electron/                \# UI 및 프로세스 제어

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

## **🛠️ 설치 및 실행 (How to Run)**

### **1\. 필수 요구 사항**

* Node.js v16+  
* Python 3.9+ (가상환경 권장)  
* **인터넷 연결 (모델 최초 다운로드 시 필수)**

### **2\. 의존성 설치**

새로운 requests 라이브러리 및 기타 의존성을 설치합니다.

\# Python Core 의존성  
pip install \-r python/requirements.txt

\# Electron 의존성  
npm install

### **3\. 애플리케이션 시작**

npm start

### **4\. 초기 실행 확인**

* 앱이 실행되면 대시보드에서 API 포트와 Proxy 포트를 확인합니다.  
* **"Install CA Certificate"** 버튼을 눌러 HTTPS 복호화 인증서를 설치합니다.  
* 플러그인을 처음 사용할 때(예: 버튼 클릭 시), 대시보드 로그에 **"Downloading model..."** 메시지가 뜨는지 확인하십시오.

## **⚠️ 문제 해결 (Troubleshooting)**

* **모델 다운로드 실패 (Hash Mismatch)**:  
  * 인터넷 연결이 불안정하거나 원본 파일이 변경되었을 수 있습니다.  
  * manifest.json의 sha256 값을 최신 파일 기준으로 업데이트하거나, models/ 폴더 내의 .part 파일을 삭제하고 다시 시도하십시오.  
* **외부 서버 연결 실패**:  
  * config.json의 base\_url 설정을 확인하십시오.  
* **인터넷 연결 끊김 (프록시 잔존)**:  
  * 앱이 비정상 종료된 경우 Windows 프록시 설정이 남아있을 수 있습니다.  
  * bat/reset\_proxy.bat 파일을 **관리자 권한**으로 실행하여 네트워크 설정을 초기화하십시오.