# **🔌 AiPlugs Platform (v3.0 Hybrid AI SOA & Multi-Tab Edition)**

**AiPlugs**는 로컬 PC에서 실행되는 지능형 AI 플러그인 오케스트레이션 플랫폼입니다.

사용자의 웹 브라우징 문맥을 파악하여 적절한 AI 기능(스크립트)을 웹 페이지에 자동으로 주입(Injection)하며, **v3.0**에서는 \*\*중앙 집중형 AI 엔진(SOA)\*\*을 도입하여 시스템 효율성을 혁신했습니다. 동시에 **v2.6**에서 확립된 **멀티 탭(Multi-Tab)** 환경과 **프록시 없는 네이티브 모드**도 완벽하게 지원합니다.

## **🚀 v3.0 핵심 변경 사항 (New Features)**

### **1\. Hybrid AI Engine (Centralized Intelligence)**

* **Single-Load, Multi-Use**: 무거운 AI 모델(PyTorch/TensorFlow)을 python/core/ai\_engine.py에서 중앙 관리합니다.  
* **Memory Efficiency**: 기존에 플러그인 프로세스마다 별도로 로드되던 모델을 통합하여 RAM 사용량을 획기적으로 절감했습니다.  
* **SOA Architecture**: 플러그인은 이제 무거운 연산을 직접 하지 않고, 경량 클라이언트(Thin Client)로서 중앙 엔진에 API 요청을 보냅니다.

### **2\. Dual-Pipeline Architecture**

플러그인의 성격에 따라 두 가지 실행 모드를 모두 지원합니다.

* **SOA Mode (execution\_type: "none")**: 별도 프로세스 없이 Core API를 직접 호출합니다. (예: Captcha Solver, Image Recognition)  
* **Legacy Process Mode (execution\_type: "process")**: 기존처럼 독립된 Python 프로세스로 실행됩니다. (예: 복잡한 상태 관리가 필요한 구형 플러그인)

### **3\. Dynamic Connectivity**

* **Auto Port Allocation**: API 서버 포트가 0(Auto)으로 설정되어 충돌 없이 자동 할당됩니다.  
* **Context Injection**: window.\_\_AI\_API\_BASE\_URL\_\_을 웹 페이지에 동적으로 주입하여, 프론트엔드에서 백엔드로 즉시 연결합니다.

## **💡 v2.6 유지 기능 (Retained Features)**

### **1\. 안전한 멀티 탭 브라우징 (Secure Multi-Tab)**

* **BrowserView 격리**: 각 탭은 독립적인 BrowserView 프로세스로 격리되어 상호 간섭이 없습니다.  
* **Active Tab Filter**: 백그라운드 탭(유튜브 음악 등)이 현재 활성화된 탭의 UI 상태를 방해하지 않도록 이벤트가 필터링됩니다.

### **2\. 네이티브 & 듀얼 시스템 모드 (System Modes)**

네트워크 패킷 감청 필요 여부에 따라 시스템 모드를 선택할 수 있습니다.

* **Native-Only Mode (권장)**: 프록시 서버를 띄우지 않고 Electron 훅으로만 동작하여 속도와 호환성이 뛰어납니다.  
* **Dual Mode**: requires\_proxy: true인 플러그인을 위해 로컬 프록시 서버를 활성화하여 HTTP 헤더 조작 및 패킷 분석을 수행합니다.

## **🛠️ 설정 및 실행 (How to Run)**

### **1\. 필수 요구 사항**

* Node.js v16+ (Electron v28 권장)  
* Python 3.9+ (가상환경 권장)  
* **PyTorch & Dependencies**: v3.0 AI 엔진 구동을 위한 필수 라이브러리

### **2\. 설치 (Installation)**

**Python 의존성 설치 (AI 엔진 포함)**

pip install \-r python/requirements.txt

**Electron 의존성 설치**

npm install

### **3\. 설정 (Configuration) \- config/config.json**

system\_settings 섹션에서 AI 엔진 리소스와 네트워크/보안 정책을 통합 관리합니다.

{  
  "system\_settings": {  
    "proxy\_port": "auto",      // Dual Mode 사용 시 포트 (auto 권장)  
    "api\_port": "auto",        // AI API 서버 포트 (auto 권장)  
      
    // \[v3.0 New\] AI 엔진 리소스 관리  
    "ai\_engine": {  
      "host": "127.0.0.1",  
      "port": 0,  
      "workers": 1             // CPU 과부하 방지를 위해 1로 고정 권장  
    },

    // \[v3.0 New\] 웹 보안 정책 우회 설정  
    "security\_policy": {  
      "bypass\_csp": true,      // Content-Security-Policy 우회 (필수)  
      "bypass\_cors": false     // CORS 정책 우회 (선택)  
    }  
  },  
  "user\_settings": {  
    "theme": "dark",  
    "auto\_start": false  
  }  
}

### **4\. 실행 (Usage)**

npm start

## **📂 프로젝트 구조 (Project Structure)**

### **Python Core (Backend)**

* python/core/ai\_engine.py: **\[New\]** 중앙 AI 추론 엔진 (PyTorch 모델 호스팅)  
* python/core/api\_server.py: **\[Updated\]** SOA 및 레거시 요청을 처리하는 통합 API 게이트웨이  
* python/core/injector.py: **\[Updated\]** 동적 포트 정보(\_\_AI\_API\_BASE\_URL\_\_) 주입기  
* python/core/orchestrator.py: **\[Retained\]** 전체 시스템 수명 주기 및 프로세스 관리  
* python/core/proxy\_server.py: **\[Retained\]** Dual Mode용 로컬 프록시 서버

### **Electron (Frontend)**

* electron/main/managers/tab-manager.js: **\[Retained\]** 멀티 탭 생성, 전환, 상태 관리  
* electron/main/security-bypass.js: **\[New\]** 로컬 API 통신을 위한 CSP/CORS 보안 해제  
* electron/renderer/: **\[Retained\]** 사용자 UI 및 탭 렌더링 로직

## **⚠️ 문제 해결 (Troubleshooting)**

Q. "Torch dependencies missing" 오류가 발생합니다.  
A. v3.0부터는 AI 엔진이 PyTorch를 직접 사용합니다. pip install torch torchvision numpy pillow 또는 requirements.txt를 통해 의존성을 설치해 주세요.  
Q. 기존 플러그인이 동작하지 않습니다.  
A. v2.6 기반 플러그인은 execution\_type이 지정되지 않았으므로 자동으로 process 모드(레거시)로 실행됩니다. Python 프로세스가 정상적으로 뜨는지 로그를 확인하세요.  
Q. 프록시 오류가 발생합니다.  
A. config.json에서 proxy\_port 설정을 확인하거나, bat/reset\_proxy.bat를 실행하여 시스템 프록시 설정을 초기화하세요.