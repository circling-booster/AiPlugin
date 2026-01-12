# **🔌 AiPlugs Platform (v2.5 Dual-Pipeline Injection)**

**AiPlugs**는 로컬 PC에서 실행되는 지능형 AI 플러그인 오케스트레이션 플랫폼입니다.

사용자의 웹 브라우징 문맥을 파악하여, 적절한 AI 기능(스크립트)을 웹 페이지에 자동으로 주입(Injection)합니다.

이번 **v2.5 업데이트**는 기존 프록시(Mitmproxy) 의존성에서 벗어나, **Electron 네이티브 훅**을 결합한 **이중 주입(Dual-Pipeline Injection)** 아키텍처를 도입했습니다. 이를 통해 HTTPS 인증서 호환성 문제와 네트워크 속도 저하를 근본적으로 해결했습니다.

상세한 아키텍처 분석, 프로젝트 구조, 그리고 플러그인 개발 가이드는

$$\*\*IMPLEMENTATION.md\*\*$$  
파일을 참고하십시오.

## **💡 핵심 변경 사항 (v2.5 Highlights)**

### **1\. 이중 주입 아키텍처 (Dual-Pipeline Injection)**

$$NEW$$  
기존에는 모든 트래픽을 프록시가 가로채어 본문(Body)을 수정하는 방식이었으나, 이제 **Electron Native Hook**이 주입을 전담합니다.

* **HTTPS/HSTS 완벽 호환**: 프록시 인증서(CA) 설치 없이도, 멜론 티켓이나 유튜브 같은 강력한 보안(Pinned Cert) 사이트에서 스크립트가 100% 동작합니다.  
* **Zero-Latency**: 프록시가 본문을 디코딩하고 재암호화하는 병목 현상이 제거되어, 브라우징 속도가 네이티브와 동일하게 유지됩니다.  
* **Electron Event Hook**: did-navigate, did-frame-navigate 이벤트를 감지하여, 페이지 이동 즉시 Python Core에 "이 URL에 필요한 플러그인이 있는가?"를 질의(match)하고 스크립트를 주입합니다.

### **2\. 스마트 샌드박싱 (Smart Sandboxing)**

* **자동 코드 격리 (Auto-IIFE Wrapping)**:  
  * API 서버가 자바스크립트 파일을 제공할 때, 자동으로 (function() { ... })(); 형태의 즉시 실행 함수로 감싸서 전송합니다.  
  * 이를 통해 플러그인 개발자가 var name 같은 흔한 변수명을 사용하더라도, 원본 웹 페이지나 다른 플러그인의 변수와 충돌하지 않는 **완벽한 스코프 격리**를 보장합니다.  
* **동적 인터셉트 라우팅**:  
  * 지능형 라우터를 사용하여 파일 확장자를 분석하고 Path Traversal 공격(../../windows/system32)을 원천 차단합니다.

### **3\. 프로토콜 정규화 및 성능 최적화 (Legacy Proxy Support)**

백업 모드(프록시 사용 시)를 위한 트래픽 정규화 기술도 유지됩니다.

* **강제 디코딩 (Mandatory Decoding)**:  
  * 서버가 압축(Gzip, Brotli)하거나 조각내어(Chunked) 보낸 데이터를 프록시 레벨에서 분석 가능한 형태로 복원합니다.  
* **헤더 재설계 (Header Recalculation)**:  
  * 스크립트 주입으로 변경된 본문 길이에 맞춰 Content-Length를 재계산하여 브라우저의 무한 로딩(Hanging) 문제를 방지합니다.  
* **I/O 블로킹 제거 (Non-Blocking)**:  
  * 디스크 쓰기 작업을 제거하여 프록시 서버의 처리 지연(Latency)을 최소화했습니다.

### **4\. 다중 레이어 보안 우회 (Multi-Layer Security Bypass)**

* **Layer 1 (Electron \- Main)**:  
  * session.webRequest API를 통해 Content-Security-Policy(CSP), X-Frame-Options 헤더를 제거하여 외부 스크립트 로딩을 허용합니다.  
* **Layer 2 (Python \- Backup)**:  
  * 프록시를 경유하는 트래픽에 대해 security.py 모듈이 2차적으로 보안 헤더를 정화(Sanitize)하여 이중 안전장치를 제공합니다.

### **5\. 기타 핵심 기능**

* **Auto-Provisioning**: 필요한 AI 모델(YOLO, CRNN 등)이 없으면 중앙 저장소(models/)에 자동으로 다운로드하고 해시(SHA256)를 검증합니다.  
* **SPA 지원**: History API 후킹 및 Zombie Connection Killer를 통해 React/Vue 기반의 동적 웹사이트에서도 안정적으로 동작합니다.

### **6\. 보안 내장 브라우저 (Secure Embedded Browser)**

$$NEW$$  
단순한 웹뷰 방식을 넘어, **BrowserView**를 활용한 독립적인 브라우징 환경을 제공합니다.

* **UI/Content 분리**: 주소창/대시보드(UI)와 웹 콘텐츠(View)가 물리적으로 분리되어, 웹 페이지 부하가 UI 반응성에 영향을 주지 않습니다.  
* **강력한 팝업 제어**: PG 결제창이나 소셜 로그인 등 window.open을 사용하는 팝업을 네이티브 핸들러로 제어하여 호환성을 보장합니다.  
* **환경 변수 동적 주입**: window.AIPLUGS\_API\_PORT를 브라우저 컨텍스트에 직접 주입하여, 플러그인이 로컬 Core와 즉시 통신할 수 있도록 지원합니다.

## **🛠️ 설치 및 실행 (How to Run)**

### **1\. 필수 요구 사항**

* Node.js v16+ (Electron v28 권장)  
* Python 3.9+ (가상환경 권장)  
* **인터넷 연결 (모델 최초 다운로드 시 필수)**

### **2\. 의존성 설치**

새로운 아키텍처 구동을 위한 의존성을 설치합니다.

\# Python Core 의존성

pip install \-r python/requirements.txt

\# Electron 의존성

npm install

### **3\. 애플리케이션 시작**

npm start

### **4\. 초기 실행 확인**

* 앱이 실행되면 대시보드에서 API 포트와 Proxy 포트를 확인합니다.  
* **(선택 사항)** "Install CA Certificate" 버튼:  
  * **기본 사용**: 인증서 설치 없이도 **스크립트 주입 및 플러그인 기능은 정상 동작**합니다 (Dual-Pipeline 덕분).  
  * **고급 분석**: 만약 프록시를 통해 패킷 내용을 직접 분석하거나 레거시 모드를 사용하려면 인증서를 설치하십시오.  
* 테스트를 위해 플러그인이 적용된 사이트(예: 유튜브)에 접속하여 콘솔(F12)에$$Electron$$  
  Injecting... 로그가 뜨는지 확인하십시오.

## **⚠️ 문제 해결 (Troubleshooting)**

* **스크립트 주입 안 됨**:  
  * 접속한 사이트가 manifest.json의 matches 패턴에 포함되어 있는지 확인하십시오.  
  * Python API 서버가 정상적으로 실행 중인지 대시보드 로그를 확인하십시오.  
* **모델 다운로드 실패 (Hash Mismatch)**:  
  * 인터넷 연결을 확인하고 models/ 폴더 내의 .part 임시 파일을 삭제 후 재시도하십시오.  
* **외부 서버 연결 실패**:  
  * config/config.json의 base\_url 설정을 확인하십시오.  
* **인터넷 연결 끊김 (프록시 잔존)**:  
  * 앱 비정상 종료 시 프록시 설정이 남을 수 있습니다. bat/reset\_proxy.bat 파일을 **관리자 권한**으로 실행하여 초기화하십시오.