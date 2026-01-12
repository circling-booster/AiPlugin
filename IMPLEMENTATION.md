# **🏗️ AiPlugs Implementation Details (v2.6)**

이 문서는 \*\*AiPlugs Platform (v2.6 Multi-Tab & Native Edition)\*\*의 내부 아키텍처, 디렉토리 구조, 상세 컴포넌트 분석 및 플러그인 개발 가이드를 다룹니다.

이번 버전은 **멀티 탭 브라우징**을 위한 BrowserView 관리 시스템이 완성되었으며, **On-Demand Proxy** 아키텍처를 통해 프록시 의존성을 선택적으로 제거할 수 있게 되었습니다. 동시에 Dual Mode를 위한 기존의 고도화된 프록시 처리 로직과 데이터 스키마 명세도 유지됩니다.

## **시스템 아키텍처 (Architecture)**

graph TD

subgraph "User Interaction"  
    User \--\> |Click/Type| UI\[Electron Renderer UI\]  
    UI \--\> |IPC: tab-create/switch| Main\[Electron Main Process\]  
end

subgraph "Multi-Tab Manager (Electron)"  
    Main \--\> |Manage| Map\[Tab Map \<ID, BrowserView\>\]  
    Main \--\> |Active Filter| View\[Active BrowserView\]  
    View \--\> |Event: did-navigate| Main  
end

subgraph "Dual-Pipeline Injection System"  
    Main \-- 1\. Match Request \--\> API\_Server\[Python API Server\]  
    API\_Server \-- 2\. Query Patterns \--\> PluginLoader  
    PluginLoader \-- 3\. Return Scripts \--\> API\_Server  
    API\_Server \-- 4\. Response \--\> Main  
    Main \-- 5\. ExecuteJavaScript \--\> View  
end

subgraph "AiPlugs Core (Python)"  
    Orch\[Orchestrator\] \--\> API\_Server  
    API\_Server \--\> SmartRouter\[Smart Sandboxing Router\]  
    SmartRouter \--\> |Auto-Wrap| PluginFiles\[Plugin JS Files\]

    API\_Server \--\> InfRouter\[Inference Router\]  
    InfRouter \--\> RuntimeMgr\[Runtime Manager\]  
    RuntimeMgr \--\> |Check/DL| ModelRegistry\[/models Directory/\]  
    RuntimeMgr \--\> WorkerMgr\[Worker Manager\]  
    WorkerMgr \--\> LocalProc\[Local Plugin Process\]  
end

subgraph "Optional Proxy Layer (Dual Mode)"  
    Orch \-.-\> |Condition: system\_mode=dual| Mitmproxy  
    Mitmproxy \-.-\> |Normalization| TrafficNorm\[Traffic Normalizer\]  
    Mitmproxy \-.-\> |Sanitize| Security\[Security Sanitizer\]  
end

## **📂 프로젝트 구조 (Directory Structure)**

AiPlugs-Project/  
├── config/  
│   ├── config.json         \# 시스템 포트 설정  
│   └── settings.json       \# \[New\] system\_mode (native-only/dual) 설정  
├── electron/  
│   ├── main/  
│   │   ├── index.js        \# \[Core\] 멀티 탭 관리자 및 주입 로직  
│   │   ├── process-manager.js \# \[New\] 모드별 Python 실행 인자 제어  
│   │   ├── cert-handler.js \# \[Legacy\] Mac/Win 인증서 설치 핸들러  
│   │   └── preload.js      \# Context Bridge  
│   └── renderer/  
│       ├── index.html      \# 탭 바(Tab Bar) UI 포함  
│       └── renderer.js     \# \[New\] TabManager 프론트엔드 로직  
├── plugins/  
│   ├── spa-connection-tester/  
│   │   └── manifest.json   \# \[New\] requires\_proxy 필드 예시  
│   └── ...  
├── python/  
│   ├── main.py             \# \[Core\] Proxy 인자 파싱 및 Fail-Safe 실행  
│   ├── core/  
│   │   ├── api\_server.py   \# Smart Router & Match Endpoint  
│   │   ├── orchestrator.py \# \[Core\] 시스템 프록시 강제 초기화 로직  
│   │   ├── proxy\_server.py \# \[Legacy\] Traffic Normalizer  
│   │   ├── security.py     \# \[Legacy\] Header Sanitizer  
│   │   └── schemas.py      \# \[Core\] Pydantic Data Models  
│   └── ...  
└── ...

## **🚀 상세 컴포넌트 분석 (Deep Dive)**

### **1\. 멀티 탭 관리 시스템 (Multi-Tab Manager)**

electron/main/index.js는 단순한 윈도우 관리를 넘어 복잡한 탭 상태 관리자 역할을 수행합니다.

* **Tab Data Structure**:  
  * Map\<Integer, Object\> 구조를 사용하여 탭 ID와 탭 정보(BrowserView, title, url)를 관리합니다.  
  * 배열 대신 Map을 사용하여 탭 닫기/전환 시 O(1) 접근 속도를 보장합니다.  
* **Active Tab Filter (UI 격리)**:  
  * 모든 네비게이션 이벤트 리스너(did-navigate)는 if (tabId \=== activeTabId) 조건을 포함합니다.  
  * 이를 통해 백그라운드 탭에서 발생하는 URL 변경이나 타이틀 업데이트가 현재 사용자가 보고 있는 주소창 UI를 덮어쓰지 않도록 방지합니다.  
* **View Switching Strategy**:  
  * mainWindow.setBrowserView(view)를 사용하여 탭 전환 시 뷰를 교체합니다.  
  * updateViewBounds()가 윈도우 리사이징에 맞춰 현재 활성 뷰의 크기를 동적으로 재조정합니다.

### **2\. 네이티브 전용 모드 (Native-Only Mode)**

프록시 서버 실행 없이도 동작 가능한 모드입니다.

* **Process Manager (process-manager.js)**:  
  * settings.json의 system\_mode가 native-only일 경우, Python Core 실행 시 \--no-proxy 및 \--proxy-port 0 인자를 전달합니다.  
  * 불필요한 포트 점유를 막고 프로세스 리소스를 절약합니다.  
* **Fail-Safe Logic (orchestrator.py)**:  
  * 앱 시작 시 force\_clear\_system\_proxy()를 호출하여, 이전에 비정상 종료되어 남아있을 수 있는 윈도우 프록시 레지스트리 설정을 강제로 초기화합니다.  
  * 이는 "앱을 켰는데 인터넷이 안 돼요"라는 사용자 경험을 방지하는 핵심 안전장치입니다.

### **3\. 스마트 샌드박싱 미들웨어 (api\_server.py)**

Electron이 주입하는 스크립트(src="...")는 Python API 서버가 서빙합니다. 이때 **지능형 미들웨어**가 개입하여 코드를 격리합니다.

* **IIFE 자동 래핑**:  
  * .js 파일 요청 시, 서버가 즉시 내용을 (function() { ... })();로 감싸 전역 스코프 오염을 방지합니다.  
  * //\# sourceURL=aiplugs://... 주석을 추가하여 디버깅 편의성을 제공합니다.  
* **Path Traversal 방어**:  
  * os.path.abspath 검증을 통해 플러그인 디렉토리를 벗어나는 파일 접근(../../windows/system32 등)을 차단합니다.

### **4\. 트래픽 정규화 및 보안 (Dual Mode / Legacy Support)**

dual 모드에서 동작하는 proxy\_server.py는 데이터 무결성을 위한 고급 처리를 담당합니다.

* **Traffic Normalizer**:  
  * **Mandatory Decoding**: flow.response.decode()를 호출하여 Gzip/Brotli 등으로 압축된 데이터를 평문으로 변환합니다.  
  * **Header Normalization**: 스크립트 주입으로 본문 길이가 늘어날 경우, Content-Length를 재계산하여 갱신하고 Transfer-Encoding: chunked 헤더를 제거하여 브라우저의 Hanging 문제를 방지합니다.  
  * **Non-Blocking I/O**: 성능 저하를 막기 위해 동기식 파일 쓰기 로직은 제거되었습니다.  
* **Security Sanitizer (security.py)**:  
  * 프록시를 통과하는 트래픽에 대해 Content-Security-Policy, X-Frame-Options 등의 보안 헤더를 2차적으로 제거합니다.  
  * 이는 Electron의 session.webRequest만으로 커버되지 않는 엣지 케이스를 방어합니다.

### **5\. 데이터 스키마 (schemas.py)**

이중 주입 통신 및 플러그인 구조를 정의하는 전체 Pydantic 모델입니다.

\# \--- Dual-Pipeline Communication \---  
class MatchRequest(BaseModel):  
    """Electron \-\> Python: 현재 URL 질의"""  
    url: str

class MatchResponse(BaseModel):  
    """Python \-\> Electron: 주입할 스크립트 리스트 반환"""  
    scripts: List\[str\] \# 예: "http://localhost:5000/plugins/my-plugin/content.js"

\# \--- Plugin Manifest Definition \---  
class ModelRequirement(BaseModel):  
    key: str              \# 환경변수 키 (예: "YOLO\_MODEL")  
    filename: str         \# models/ 폴더 내 파일명  
    source\_url: Optional\[str\] \= None  
    sha256: Optional\[str\] \= None

class InferenceConfig(BaseModel):  
    supported\_modes: List\[str\] \= \["local"\]  
    default\_mode: str \= "local"  
    local\_entry: str \= "backend.py"  
    web\_entry: str \= "web\_backend.py"  
    models: List\[ModelRequirement\] \= \[\]

class ContentScript(BaseModel):  
    matches: List\[str\] \= \["\<all\_urls\>"\]  
    js: List\[str\] \= \["content.js"\]  
    run\_at: Literal\["document\_start", "document\_end", "document\_idle"\] \= "document\_end"  
    all\_frames: bool \= False

class PluginManifest(BaseModel):  
    manifest\_version: int \= 3  
    id: str  
    name: str \= "Unknown Plugin"  
    requires\_proxy: bool \= False  \# \[New\] 프록시 의존성 여부 (Default: False)  
    inference: InferenceConfig \= InferenceConfig()  
    content\_scripts: List\[ContentScript\] \= \[\]

## **🔍 심층 구현 기술 (Undocumented Details)**

코드 곳곳에 숨겨진 중요 구현 사항들입니다.

### **1\. Iframe 지원 전략**

did-frame-navigate 이벤트를 활용하여 메인 프레임뿐만 아니라 Iframe 내부의 네비게이션도 감지합니다. checkAndInject 함수는 frameRoutingId를 인자로 받아, 특정 프레임에만 정확히 스크립트를 주입하도록 설계되어 있습니다.

### **2\. Fetch API 활용 (Performance)**

Electron 28 버전의 Main Process는 fetch API를 기본 지원합니다. 따라서 별도의 axios나 request 모듈 설치 없이 Python Core와 가볍고 빠른 HTTP 통신이 가능합니다.

### **3\. 정교한 주입 필터링 (Fetch Metadata)**

proxy\_server.py는 브라우저의 Sec-Fetch-Dest 헤더를 검사합니다.

* **Logic**: AJAX/Fetch 요청(dest="empty"), CORS 요청, WebSocket 연결 등에는 스크립트 주입을 방어합니다.  
* **Benefit**: 불필요한 JSON 데이터 손상을 막고 시스템 안정성을 보장합니다.

### **4\. 적극적인 캐시 무효화 (Aggressive Cache Busting)**

* **Logic**: 프록시 서버 및 API 서버는 응답 헤더에서 Cache-Control, Expires, ETag를 강제로 삭제하거나 no-cache로 설정합니다.  
* **Benefit**: 플러그인 개발 시 수정 사항이 새로고침 한 번으로 즉시 반영됩니다.

### **5\. Mac OS 인증서 설치 자동화**

* **Logic**: cert-handler.js는 osascript를 활용하여 macOS의 관리자 권한 팝업을 띄우고, 시스템 키체인에 프록시 인증서를 '신뢰할 수 있는 루트'로 등록합니다.

## **👨‍💻 플러그인 개발 가이드 (Plugin Development)**

### **A. Manifest 작성 (v2.6 Spec)**

이제 플러그인이 프록시를 필요로 하는지 명시해야 합니다.

{  
    "manifest\_version": 3,  
    "id": "packet\_analyzer",  
    "name": "Advanced Packet Tool",  
    "requires\_proxy": true,  // \[New\] 프록시 필수 여부 (기본값: false)  
    "inference": {  
        "default\_mode": "local",  
        "local\_entry": "backend.py"  
    },  
    "content\_scripts": \[ ... \]  
}

### **B. Native-Only 호환성 체크**

플러그인을 개발할 때 다음 사항을 고려하십시오.

1. **헤더 조작 불가**: Native 모드에서는 요청/응답 헤더를 수정할 수 없습니다. 필요한 경우 window.fetch 등을 오버라이딩하여 클라이언트 사이드에서 처리해야 합니다.  
2. **직접 통신**: 스크립트는 window.AIPLUGS\_API\_PORT를 통해 로컬 Python Core와 직접 통신합니다. 이 통신은 프록시를 거치지 않습니다.

### **C. 멀티 탭 환경 테스트**

플러그인 개발 시 반드시 여러 탭을 열어둔 상태에서 테스트해야 합니다.

* **전역 변수 오염**: window 객체에 변수를 할당할 때 다른 탭이나 메인 프레임과 충돌하지 않는지 확인하십시오.  
* **백그라운 동작**: 탭이 비활성화되었을 때 requestAnimationFrame이나 setInterval 동작이 브라우저에 의해 스로틀링(Throttling)될 수 있음을 인지하십시오.