const { app, session } = require('electron');

/**
 * 와일드카드 패턴 매칭 (예: *youtube.com -> www.youtube.com 매칭)
 */
function isMatch(url, patterns) {
    if (!patterns || patterns.length === 0) return false;
    if (patterns.includes('*')) return true;
    
    try {
        const hostname = new URL(url).hostname;
        return patterns.some(pattern => {
            const regex = new RegExp('^' + pattern.replace(/\./g, '\\.').replace(/\*/g, '.*') + '$');
            return regex.test(hostname);
        });
    } catch (e) {
        return false;
    }
}

/**
 * [1단계] 앱 시작 전 적용해야 하는 커맨드라인 스위치 설정
 * (Autoplay, SSL 무시 등은 브라우저 엔진 초기화 시점에 필요)
 */
function initAppSwitches(config) {
    const policy = config.system_settings?.security_policy || {};

    // 1. 오디오/비디오 자동 재생 정책 우회 (사용자 제스처 없이 재생)
    if (policy.allow_autoplay) {
        app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');
    }

    // 2. SSL 인증서 오류 무시 (자가 서명 인증서, 만료된 인증서 허용)
    if (policy.allow_insecure_cert) {
        app.commandLine.appendSwitch('ignore-certificate-errors');
        app.commandLine.appendSwitch('allow-insecure-localhost');
    }

    // 3. 렌더러 프로세스 재사용 방지 (보안 격리보다는 안정성 및 독립적 인젝션을 위함)
    app.commandLine.appendSwitch('disable-site-isolation-trials');
}

/**
 * [2단계] 세션(Network/Permission) 레벨의 보안 정책 우회 설정
 */
function setupSessionBypass(targetSession, config) {
    const policy = config.system_settings?.security_policy || {};
    const targetPatterns = policy.apply_to || config.system_settings?.trusted_types_bypass || [];
    
    // 패턴이 없으면 적용하지 않음 (단, 정책에 따라 *가 포함될 수 있음)
    if (targetPatterns.length === 0 && !policy.apply_to) return;

    // 1. 권한 요청 자동 승인 (마이크, 카메라, 알림 등)
    if (policy.auto_grant_permissions) {
        targetSession.setPermissionRequestHandler((webContents, permission, callback) => {
            callback(true); 
        });
        targetSession.setPermissionCheckHandler((webContents, permission) => {
            return true;
        });
    }

    // 2. HTTP 헤더 조작을 통한 보안 무력화 (CSP, CORS, FrameOptions)
    targetSession.webRequest.onHeadersReceived((details, callback) => {
        const url = details.url;
        
        // 설정된 도메인 패턴에 맞지 않으면 건너뜀
        if (!isMatch(url, targetPatterns)) {
            return callback({ responseHeaders: details.responseHeaders });
        }

        const newHeaders = Object.assign({}, details.responseHeaders);

        // [A] CSP (Content-Security-Policy) & Trusted Types 우회
        if (policy.bypass_csp) {
            delete newHeaders['content-security-policy'];
            delete newHeaders['content-security-policy-report-only'];
            delete newHeaders['x-webkit-csp'];
            delete newHeaders['x-content-security-policy'];
        }

        // [B] Iframe 차단 우회 (X-Frame-Options)
        if (policy.bypass_frame_options) {
            delete newHeaders['x-frame-options'];
            delete newHeaders['x-content-type-options']; // MIME sniffing 차단 해제
        }

        // [C] CORS (Cross-Origin Resource Sharing) 우회
        if (policy.bypass_cors) {
            // 기존 CORS 헤더 제거 (중복 방지)
            delete newHeaders['access-control-allow-origin'];
            delete newHeaders['access-control-allow-methods'];
            delete newHeaders['access-control-allow-headers'];
            delete newHeaders['access-control-allow-credentials'];

            // 모든 오리진 허용 헤더 주입
            newHeaders['Access-Control-Allow-Origin'] = ['*'];
            newHeaders['Access-Control-Allow-Methods'] = ['GET, POST, OPTIONS, PUT, PATCH, DELETE'];
            newHeaders['Access-Control-Allow-Headers'] = ['*'];
        }

        callback({
            responseHeaders: newHeaders,
            statusLine: details.statusLine
        });
    });

    console.log(`[SecurityBypass] Applied policies to patterns: ${JSON.stringify(targetPatterns)}`);
}

module.exports = { initAppSwitches, setupSessionBypass };