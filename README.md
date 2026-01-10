# **🔌 AiPlugs Platform (v2.4 Stability & Protocol Upgrade)**

**AiPlugs**는 로컬 PC에서 실행되는 지능형 AI 플러그인 오케스트레이션 플랫폼입니다.

사용자의 웹 브라우징 트래픽을 투명하게 가로채어(Intercept), 문맥에 맞는 AI 기능을 웹 페이지에 주입(Injection)합니다.

이번 **v2.4 업데이트**는 단순한 기능 추가를 넘어, 상용 웹 서비스(멜론 티켓 등)와의 **프로토콜 호환성**을 극대화하고 플러그인 코드의 \*\*안전한 격리(Sandboxing)\*\*를 보장하는 아키텍처 레벨의 개선이 적용되었습니다.

상세한 아키텍처 분석, 프로젝트 구조, 그리고 플러그인 개발 가이드는 \[**IMPLEMENTATION.md**\] 파일을 참고하십시오.

## **💡 핵심 변경 사항 (v2.4 Highlights)**

### **1\. 스마트 샌드박싱 (Smart Sandboxing)**

* **자동 코드 격리 (Auto-IIFE Wrapping)**:  
  * API 서버가 자바스크립트 파일을 제공할 때, 자동으로 (function() { ... })(); 형태의 즉시 실행 함수로 감싸서 전송합니다.  
  * 이를 통해 플러그인 개발자가 var name 같은 흔한 변수명을 사용하더라도, 원본 웹 페이지나 다른 플러그인의 변수와 충돌하지 않는 **완벽한 스코프 격리**를 보장합니다.  
* **동적 인터셉트 라우팅**:  
  * 단순 정적 파일 서빙 대신 지능형 라우터를 사용하여, 파일 확장자를 분석하고 Path Traversal 공격(../../windows/system32)을 원천 차단합니다.

### **2\. 프로토콜 정규화 (Protocol Normalization)**

* **강제 디코딩 (Mandatory Decoding)**:  
  * 서버(멜론)가 압축(Gzip, Brotli)하거나 조각내어(Chunked) 보낸 데이터를 프록시 레벨에서 **완전한 평문**으로 복원한 뒤 스크립트를 주입합니다. 파일 깨짐 현상을 원천적으로 방지합니다.  
* **헤더 재설계 (Header Recalculation)**:  
  * 스크립트 주입으로 변경된 본문(Body) 길이에 맞춰 Content-Length를 정밀하게 재계산하여 브라우저의 **무한 로딩(Hanging)** 문제를 해결했습니다.  
* **I/O 블로킹 제거 (Non-Blocking)**:  
  * 디스크 쓰기 작업을 제거하여 프록시 서버의 처리 지연(Latency)을 최소화했습니다.

### **3\. 기존 핵심 기능 (v2.3 포함)**

* **Auto-Provisioning**: 필요한 AI 모델이 없으면 중앙 저장소(models/)에 자동으로 다운로드하고 해시(SHA256)를 검증합니다.  
* **SPA 지원**: History API 후킹 및 Zombie Connection Killer를 통해 동적 웹사이트에서도 안정적으로 동작합니다.  
* **보안 우회**: Electron과 Python 이중 레이어에서 CSP(Content Security Policy)를 무력화하여 플러그인 실행을 보장합니다.

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
  * config/config.json의 base\_url 설정을 확인하십시오.  
* **인터넷 연결 끊김 (프록시 잔존)**:  
  * 앱이 비정상 종료된 경우 Windows 프록시 설정이 남아있을 수 있습니다.  
  * bat/reset\_proxy.bat 파일을 **관리자 권한**으로 실행하여 네트워크 설정을 초기화하십시오.