# **🔌 AiPlugs Platform (v2.3 Auto-Provisioning Edition)**

**AiPlugs**는 로컬 PC에서 실행되는 지능형 AI 플러그인 오케스트레이션 플랫폼입니다.

사용자의 웹 브라우징 트래픽을 투명하게 가로채어(Intercept), 문맥에 맞는 AI 기능을 웹 페이지에 주입(Injection)합니다.

이번 **v2.3 버전**은 대용량 AI 모델을 효율적으로 관리하기 위한 \*\*중앙 모델 저장소(Model Registry)\*\*와 실행 시점에 필요한 리소스를 자동으로 확보하는 **자동 프로비저닝(Auto-Provisioning)** 아키텍처가 도입되었습니다.

상세한 아키텍처 분석, 프로젝트 구조, 그리고 플러그인 개발 가이드는 [**IMPLEMENTATION.md**](https://www.google.com/search?q=./IMPLEMENTATION.md) 파일을 참고하십시오.

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