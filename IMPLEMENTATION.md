# **🏗️ AiPlugs Implementation Details (v2.5 Dual-Pipeline)**

이 문서는 \*\*AiPlugs Platform (v2.5 Dual-Pipeline Edition)\*\*의 내부 아키텍처, 디렉토리 구조, 상세 컴포넌트 분석 및 플러그인 개발 가이드를 다룹니다.

이번 버전은 **Electron Native Hook**과 **Python Core API**가 협력하는 이중 파이프라인 구조로 개선되어, HTTPS 호환성과 주입 속도를 비약적으로 향상시켰습니다. 동시에 기존의 프록시 기반 기술들도 백업 시스템으로 유지됩니다.

## **시스템 아키텍처 (Architecture)**

graph TD

subgraph "Web Traffic Flow"

User

$$User Browser$$  
\<--\> |Native Request| WebServer

$$Target Web Server$$  
end

subgraph "Dual-Pipeline Injection System"    
    User \\-- Event: did-navigate \\--\\\> ElectronMain\\\[Electron Main Process\\\]    
        
    ElectronMain \\-- 1\\. Match Request (POST /v1/match) \\--\\\> API\\\_Server\\\[Python API Server\\\]    
    API\\\_Server \\-- 2\\. Query Patterns \\--\\\> PluginLoader\\\[Plugin Loader\\\]    
    PluginLoader \\-- 3\\. Return Scripts \\--\\\> API\\\_Server    
    API\\\_Server \\-- 4\\. MatchResponse (Script URLs) \\--\\\> ElectronMain    
        
    ElectronMain \\-- 5\\. ExecuteJavaScript (Injection) \\--\\\> User    
end

subgraph "AiPlugs Core (Python)"    
    Orch\\\[Orchestrator\\\] \\--\\\> API\\\_Server    
    API\\\_Server \\--\\\> SmartRouter\\\[Smart Sandboxing Router\\\]    
    SmartRouter \\--\\\> |Auto-Wrap| PluginFiles\\\[Plugin JS Files\\\]

    API\\\_Server \\--\\\> InfRouter\\\[Inference Router\\\]    
    InfRouter \\--\\\> |Request Proc| RuntimeMgr\\\[Runtime Manager\\\]    
    RuntimeMgr \\-- Check/Download \\--\\\> ModelRegistry\\\[/models Directory/\\\]    
    RuntimeMgr \\--\\\> |Inject Env| WorkerMgr\\\[Worker Manager\\\]    
    WorkerMgr \\--\\\> |Spawn| LocalProc\\\[Local Plugin Process\\\]    
end

subgraph "Legacy Proxy Support"    
    Mitmproxy\\\[Python Proxy Core\\\] \\-.-\\\> |Backup/Analyze| User    
    Mitmproxy \\--\\\> |Normalization| TrafficNorm\\\[Traffic Normalizer\\\]    
    Mitmproxy \\--\\\> |Sanitize| Security\\\[Security Sanitizer\\\]    
end

## **📂 프로젝트 구조 (Directory Structure)**

AiPlugs-Project/

├── .gitattributes

├── .gitignore

├── IMPLEMENTATION.md \# 아키텍처 및 구현 상세 문서

├── README.md \# 프로젝트 개요 및 실행 가이드

├── package-lock.json

├── package.json \# Electron 의존성 정의

├── bat/

│ └── reset\_proxy.bat \#

$$Utils$$  
윈도우 프록시 강제 초기화 스크립트

├── config/

│ ├── config.json \# 시스템 설정 (API/Proxy 포트, 외부 클라우드 URL)

│ └── settings.json \# 사용자 설정 (활성화된 플러그인, 동작 모드)

├── electron/

│ ├── main/ \# Electron 메인 프로세스

│ │ ├── cert-handler.js \# 인증서 설치 핸들러 (AppleScript 포함)

│ │ ├── index.js \#

$$Core$$  
네비게이션 훅 및 주입 로직 (Dual-Pipeline)

│ │ ├── preload.js \# Context Bridge (Renderer \<-\> Main)

│ │ └── process-manager.js \# Python Core 생명주기 관리

│ └── renderer/ \# Electron 렌더러 (UI)

│ ├── index.html \# 대시보드 HTML

│ └── renderer.js \# 대시보드 로직

├── models/ \# AI 모델 중앙 저장소 (Auto-Provisioning)

│ └── .gitkeep

├── plugins/ \# 플러그인 디렉토리

│ ├── captcha\_solver/ \#

$$Example$$  
캡차 해결 플러그인

│ │ ├── backend.py \# 로컬 추론 백엔드

│ │ ├── content.js \# 주입용 콘텐츠 스크립트

│ │ └── manifest.json \# 플러그인 명세서

│ ├── cloud-secure-translator/ \#

$$Example$$  
클라우드 번역 (Web Mode)

│ │ ├── content.js

│ │ ├── manifest.json

│ │ └── web\_backend.py \# 웹 모드용 백엔드 (클라우드 Relay)

│ ├── heavy-math-solver/ \#

$$Example$$  
연산 플러그인

│ │ ├── backend.py

│ │ ├── manifest.json

│ │ └── thisscript.js

│ └── spa-connection-tester/ \#

$$Example$$  
SPA 테스트 플러그인

│ ├── backend.py

│ ├── content.js

│ └── manifest.json

└── python/ \# Python Core Engine

├── main.py \# 엔트리포인트

├── requirements.txt \# Python 의존성

├── core/ \# 핵심 모듈

│ ├── api\_server.py \#

$$Core$$  
/v1/match, 스마트 라우터

│ ├── connection\_manager.py\# WebSocket 관리 및 Zombie Connection 제거

│ ├── inference\_router.py \# 추론 요청 라우팅 (Local/Web 분기)

│ ├── injector.py \#

$$Legacy$$  
HTML 스크립트 주입기

│ ├── orchestrator.py \# 시스템 조율 (API \+ Proxy 실행)

│ ├── plugin\_loader.py \#

$$Core$$  
플러그인 로드 및 정규식 컴파일

│ ├── proxy\_server.py \#

$$Legacy/Backup$$  
트래픽 정규화 프록시

│ ├── runtime\_manager.py \# 모델 자동 다운로드 및 검증

│ ├── schemas.py \#

$$New$$  
데이터 모델 (MatchRequest, Manifest 등)

│ ├── security.py \#

$$Legacy$$  
보안 헤더(CSP) 정화 로직

│ └── worker\_manager.py \# 로컬 프로세스 격리 실행

└── utils/

└── system\_proxy.py \# 시스템 프록시 설정 (Win/Mac)

## **🚀 상세 컴포넌트 분석 (Deep Dive)**

### **1\. 이중 주입 파이프라인 (Dual-Pipeline Injection)**

\*\*기존 방식(v2.4)\*\*은 Mitmproxy가 모든 패킷을 가로채어 HTML Body를 수정했습니다. 이는 HTTPS 인증서 문제와 속도 저하를 유발했습니다.

\*\*새로운 방식(v2.5)\*\*은 Electron의 이벤트 훅을 활용하여 브라우저 레벨에서 직접 스크립트를 주입합니다.

* **Electron Main Process (index.js)**:  
  * **Navigation Hooks**:  
    * did-navigate: 메인 프레임 이동 감지 (새로고침, URL 입력)  
    * did-frame-navigate: Iframe 내부 이동 감지  
    * did-navigate-in-page$$New$$  
      : History API를 사용하는 SPA(Single Page App) 내부 이동 감지  
  * **Matching Query**: 이동한 URL을 http://127.0.0.1:API\_PORT/v1/match로 전송하여 주입할 스크립트 목록을 받아옵니다.  
  * **Execution**: 받아온 스크립트 URL을 webContents.executeJavaScript()를 통해 페이지에 동적으로 삽입합니다. 이는 **Cross-Origin** 제약 없이 동작합니다.  
* **Python API Server (api\_server.py)**:  
  * Lifespan Management$$New$$  
    : 서버 시작 시(startup 이벤트) PluginLoader를 통해 모든 플러그인을 미리 로드하고 정규식을 컴파일하여 검색 속도를 최적화합니다.  
  * **/v1/match 엔드포인트**: Electron의 요청(URL)을 받아 PluginLoader에 미리 컴파일된 정규식 패턴(compiled\_patterns)과 대조합니다. 매칭되는 플러그인의 스크립트 리스트를 반환합니다.

### **2\. 데이터 스키마 (schemas.py)**

$$Enhanced$$  
이중 주입 통신 및 플러그인 구조를 정의하는 전체 Pydantic 모델입니다.

\# \--- Dual-Pipeline Communication \---

class MatchRequest(BaseModel):

"""Electron \-\> Python: 현재 URL 질의"""

url: str

class MatchResponse(BaseModel):

"""Python \-\> Electron: 주입할 스크립트 리스트 반환"""

scripts: List

$$str$$  
\# 예:

$$"http://localhost:5000/plugins/my-plugin/content.js"$$  
\# \--- Plugin Manifest Definition \---

class ModelRequirement(BaseModel):

key: str \# 환경변수 키 (예: "YOLO\_MODEL")

filename: str \# models/ 폴더 내 파일명

source\_url: Optional

$$str$$  
\= None

sha256: Optional

$$str$$  
\= None

class InferenceConfig(BaseModel):

supported\_modes: List

$$str$$  
\=

$$"local"$$  
default\_mode: str \= "local"

local\_entry: str \= "backend.py"

web\_entry: str \= "web\_backend.py"

models: List

$$ModelRequirement$$  
\=

class ContentScript(BaseModel):

matches: List

$$str$$  
\=

$$"\\\<all\\\_urls\\\>"$$  
js: List

$$str$$  
\=

$$"content.js"$$  
run\_at: Literal

$$"document\\\_start", "document\\\_end", "document\\\_idle"$$  
\= "document\_end"

all\_frames: bool \= False

class PluginManifest(BaseModel):

manifest\_version: int \= 3

id: str

name: str \= "Unknown Plugin"

inference: InferenceConfig \= InferenceConfig()

content\_scripts: List

$$ContentScript$$  
\=

### **3\. 스마트 샌드박싱 미들웨어 (api\_server.py)**

Electron이 주입하는 스크립트(src="...")는 Python API 서버가 서빙합니다. 이때 **지능형 미들웨어**가 개입하여 코드를 격리합니다.

* **IIFE 자동 래핑**:  
  * .js 파일 요청 시, 서버가 즉시 내용을 (function() { ... })();로 감싸 전역 스코프 오염을 방지합니다.  
  * //\# sourceURL=aiplugs://... 주석을 추가하여 디버깅 편의성을 제공합니다.  
* **Path Traversal 방어**:  
  * os.path.abspath 검증을 통해 플러그인 디렉토리를 벗어나는 파일 접근을 차단합니다.

### **4\. 다중 보안 정책 우회 (Multi-Layer Security Bypass)**

* **Layer 1: CSP 제거 (Electron)**:  
  * session.webRequest.onHeadersReceived에서 Content-Security-Policy, X-Frame-Options 등의 헤더를 제거합니다.  
  * 이를 통해 로컬호스트(API 서버)에서 제공하는 스크립트가 외부 상용 사이트(멜론, 유튜브 등)에서도 차단되지 않고 로드됩니다.  
* **Layer 2: Header Sanitizer (Python/Legacy)**:  
  * security.py 모듈은 프록시를 통과하는 트래픽에 대해 잔존하는 보안 헤더를 2차적으로 제거하여, 레거시 모드에서의 호환성을 보장합니다.

### **5\.**

$$Legacy$$  
Traffic Normalizer (proxy\_server.py)

프록시 모드 사용 시 데이터 무결성을 보장하기 위한 정규화 로직입니다. 현재는 백업 시스템으로 동작합니다.

* **강제 디코딩 (Mandatory Decoding)**:  
  * flow.response.decode()를 호출하여 Gzip, Brotli 등으로 압축된 데이터를 평문으로 변환합니다.  
* **헤더 정규화 (Header Normalization)**:  
  * **Content-Length 재계산**: 스크립트 주입으로 본문 길이가 늘어날 경우, 바이트 길이를 정확히 재계산하여 헤더를 갱신합니다. 이를 통해 **Hanging(무한 로딩)** 문제를 방지합니다.  
  * **Transfer-Encoding 제거**: 충돌을 방지하기 위해 Chunked 인코딩 헤더를 삭제합니다.  
* **I/O 최적화 (Non-Blocking)**:  
  * 디버깅용 파일 쓰기 로직을 제거하여 고성능 Non-Blocking I/O를 보장합니다.

### **6\. BrowserView 기반 임베디드 브라우저 (Embedded Browser Architecture)**

Electron의 BrowserView를 사용하여 브라우저 UI(Shell)와 웹 콘텐츠(Content)를 분리한 구조입니다.

* **View Management**:  
  * BrowserWindow는 껍데기 역할(주소창, 컨트롤러)만 수행하며, 실제 웹 페이지는 BrowserView 객체로 생성되어 윈도우 위에 오버레이됩니다.  
  * updateViewBounds() 함수가 윈도우 리사이징 이벤트를 감지하여 뷰의 크기를 동적으로 조절합니다.  
* **Global Security Context**:  
  * BrowserView와 BrowserWindow는 session.defaultSession을 공유합니다.  
  * CSP(Content Security Policy) 제거 리스너를 세션 전역에 등록하여, 메인 페이지뿐만 아니라 팝업 창에서도 외부 스크립트 로딩이 차단되지 않도록 합니다.  
* **IPC Bridge**:  
  * 렌더러 프로세스(UI)는 Maps-to, browser-control 채널을 통해 메인 프로세스에 명령을 전달하고, 메인 프로세스가 실제 BrowserView를 제어합니다.

## **🔍 심층 구현 분석 (Undocumented Implementation Details)**

### **1\. Iframe 지원 전략**

did-frame-navigate 이벤트를 활용하여 메인 프레임뿐만 아니라 Iframe 내부의 네비게이션도 감지합니다. checkAndInject 함수는 frameRoutingId를 인자로 받아, 특정 프레임에만 정확히 스크립트를 주입하도록 설계되어 있습니다.

### **2\. Fetch API 활용**

Electron 28 버전의 Main Process는 fetch API를 기본 지원합니다. 따라서 별도의 axios나 request 모듈 설치 없이 Python Core와 가볍고 빠른 HTTP 통신이 가능합니다.

### **3\. 정교한 주입 필터링 (Smart Injection via Fetch Metadata)**

* **분석**: proxy\_server.py는 브라우저의 Sec-Fetch-Dest, Sec-Fetch-Mode 헤더를 검사합니다.  
* **동작**: AJAX/Fetch 요청(dest="empty"), CORS 요청, WebSocket 연결 등에는 스크립트 주입을 방어하여 JSON 데이터 손상을 막습니다. 이는 프록시 모드 활성화 시 데이터 안정성을 위한 핵심 로직입니다.

### **4\. 적극적인 캐시 무효화 (Aggressive Cache Busting)**

* **분석**: 프록시 서버는 응답 헤더에서 Cache-Control, Expires, ETag를 강제로 삭제합니다.  
* **의미**: 브라우저가 스크립트 파일을 캐싱하지 못하게 하여, 플러그인 개발/업데이트 사항이 즉시 반영되도록 보장합니다.

### **5\. Mac OS 인증서 설치 자동화 (AppleScript 활용)**

* **분석**: electron/main/cert-handler.js에는 macOS를 위한 osascript 호출 로직이 포함되어 있습니다.  
* **동작**: 관리자 권한(sudo) 팝업을 띄우고 시스템 키체인에 프록시 인증서를 '신뢰할 수 있는 루트'로 등록하는 스크립트를 실행합니다.

## **👨‍💻 플러그인 개발 가이드 (Plugin Development)**

### **A. manifest.json 작성 (구조 상세화)**

v2.5 스펙을 준수하는 완전한 Manifest 예시입니다. inference.models 섹션은 로컬 실행 모드일 때만 필수입니다.

{

"manifest\_version": 3,

"id": "captcha\_solver",

"name": "Melon Captcha Solver",

"inference": {

"supported\_modes":

$$"local", "web"$$  
,

"default\_mode": "web",

"local\_entry": "backend.py",

"models": \[

{

"key": "MODEL\_MELON",

"filename": "model\_melon.pt",

"source\_url": "http://localhost:8000/models/model\_melon.pt",

"sha256": "SKIP\_VERIFICATION"

}

\]

},

"content\_scripts": \[

{

"matches": \[

"\*://

$$ticket.melon.com/$$  
(https://ticket.melon.com/)\*",

"\*://\*

$$.interpark.com/$$  
(https://.interpark.com/)\*"

\],

"js":

$$"content.js"$$  
,

"run\_at": "document\_end",

"all\_frames": true

}

\]

}

### **B. 스크립트 주입 테스트**

1. 앱 실행 후 대시보드 로그 확인.  
2. manifest.json에 정의된 사이트 접속.  
3. 개발자 도구(F12) Console 탭에서$$Electron$$  
   Injecting... 메시지 확인.  
4. 동작하지 않을 경우 bat/reset\_proxy.bat 실행 후 재시도.