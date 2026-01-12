# **🔌 AiPlugs Platform (v2.6 Multi-Tab & Native Mode)**

**AiPlugs**는 로컬 PC에서 실행되는 지능형 AI 플러그인 오케스트레이션 플랫폼입니다.

사용자의 웹 브라우징 문맥을 파악하여, 적절한 AI 기능(스크립트)을 웹 페이지에 자동으로 주입(Injection)합니다.

**v2.6 업데이트**는 **멀티 탭(Multi-Tab) 브라우징**을 완벽하게 지원하며, 사용자의 선택에 따라 프록시 서버 없이 동작하는 **Native-Only 모드**를 도입하여 안정성을 극대화했습니다. 동시에 기존의 강력한 프록시 분석 기술도 **Dual Mode**를 통해 계속 지원합니다.

상세한 아키텍처 분석, 프로젝트 구조, 그리고 플러그인 개발 가이드는 **IMPLEMENTATION.md** 파일을 참고하십시오.

## **💡 핵심 변경 사항 (Highlights)**

### **1\. 안전한 멀티 탭 브라우징 (Secure Multi-Tab)**

$$NEW$$

기존의 단일 뷰 방식을 넘어, 실제 브라우저처럼 여러 탭을 동시에 관리할 수 있습니다.

* **BrowserView 격리**: 각 탭은 독립적인 BrowserView 프로세스로 격리되어 상호 간섭이 없습니다.  
* **Active Tab Filter**: 백그라운드 탭(예: 유튜브 음악 재생)의 이벤트가 현재 활성화된 탭의 주소창이나 상태를 방해하지 않도록 필터링 기술이 적용되었습니다.  
* **State Management**: 탭 전환 시 스크롤 위치, 네비게이션 기록(Back/Forward)이 완벽하게 유지됩니다.

### **2\. 네이티브 전용 모드 (Native-Only Mode)**

$$NEW$$

프록시(Mitmproxy) 서버를 켜지 않고도 핵심 기능을 사용할 수 있는 모드입니다.

* **On-Demand Proxy**: settings.json 설정을 통해 프록시 사용 여부를 제어합니다.  
* **Stability**: 프록시 프로세스에 의존하지 않으므로, 네트워크 설정 꼬임이나 인증서 문제로부터 자유롭습니다.  
* **Fail-Safe**: 앱 시작 및 종료 시 윈도우 레지스트리에 잔존할 수 있는 시스템 프록시 설정을 강제로 정리하여 인터넷 끊김 사고를 방지합니다.

### **3\. 이중 주입 아키텍처 (Dual-Pipeline Injection)**

기존 방식과 결합하여 최적의 주입 경로를 자동으로 선택합니다.

* **Electron Native Hook**: did-navigate 이벤트를 감지하여 페이지 이동 즉시 Python Core에 질의(Match)하고 스크립트를 주입합니다. (Native Mode의 핵심)  
* **HTTPS/HSTS 호환**: 멜론 티켓, 유튜브 등 보안이 강력한 사이트에서도 인증서 설치 없이 스크립트가 동작합니다.  
* **Zero-Latency**: 프록시 병목 없이 브라우징 속도가 네이티브와 동일하게 유지됩니다.

### **4\. 강력한 프록시 지원 (Legacy Proxy Support)**

dual 모드 사용 시 활성화되는 백업 시스템입니다.

* **Protocol Normalization**: Gzip/Brotli 압축을 강제 해제하고, Chunked 인코딩을 평문으로 변환하여 플러그인이 패킷을 분석하기 쉽게 만듭니다.  
* **Header Recalculation**: 스크립트 주입으로 본문 길이가 변했을 때, Content-Length를 정밀하게 재계산하여 브라우저의 무한 로딩(Hanging)을 방지합니다.

### **5\. 스마트 샌드박싱 및 보안 (Security)**

* **Auto-IIFE Wrapping**: API 서버가 제공하는 모든 JS 파일은 (function() { ... })(); 형태로 자동 래핑되어 전역 변수 충돌을 방지합니다.  
* **Multi-Layer Security Bypass**: session.webRequest(Electron)와 security.py(Python)가 협력하여 CSP, X-Frame-Options 등 외부 스크립트 차단 정책을 이중으로 우회합니다.

## **🛠️ 설정 및 실행 (How to Run)**

### **1\. 필수 요구 사항**

* Node.js v16+ (Electron v28 권장)  
* Python 3.9+ (가상환경 권장)  
* **인터넷 연결 (모델 최초 다운로드 시 필수)**

### **2\. 시스템 모드 설정 (Configuration)**

config/settings.json 파일에서 시스템 동작 모드를 변경할 수 있습니다.

{  
  "system\_mode": "native-only",  // "native-only" (프록시 OFF) 또는 "dual" (프록시 ON)  
  "active\_plugins": \[ ... \]  
}

* **native-only (권장)**: 프록시 없이 Electron 훅으로만 동작. 빠르고 안정적이며 일반적인 사용에 적합합니다.  
* **dual**: 레거시 프록시 기능을 함께 사용. 패킷 분석이 필요한 플러그인(requires\_proxy: true)이나 정교한 헤더 조작이 필요할 때 사용합니다.

### **3\. 실행 방법**

**의존성 설치**

\# Python Core  
pip install \-r python/requirements.txt

\# Electron  
npm install

**애플리케이션 시작**

npm start

### **4\. 초기 실행 확인**

* 대시보드 상단에 탭 바가 표시되는지 확인합니다.  
* \+ 버튼을 눌러 새 탭을 생성하고, 여러 사이트를 동시에 탐색해 봅니다.  
* 플러그인이 적용된 사이트에 접속하여 콘솔(F12)에 Electron Injecting... 로그가 뜨는지 확인합니다.

## **⚠️ 문제 해결 (Troubleshooting)**

* **특정 플러그인 동작 안 함**:  
  * 해당 플러그인의 manifest.json에 "requires\_proxy": true가 있는지 확인하십시오.  
  * 이 경우 config/settings.json의 system\_mode를 "dual"로 변경하고 앱을 재시작해야 합니다.  
* **인터넷 연결 끊김 (프록시 잔존)**:  
  * 앱에는 자동 정리 기능(Fail-Safe)이 내장되어 있으나, 비정상 종료 시 설정이 남을 수 있습니다.  
  * bat/reset\_proxy.bat 파일을 **관리자 권한**으로 실행하여 초기화하십시오.  
* **모델 다운로드 실패**:  
  * models/ 폴더 내의 .part 임시 파일을 삭제 후 재시도하십시오.