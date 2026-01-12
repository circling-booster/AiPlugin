const { session } = require('electron');

/**
 * 와일드카드 패턴 매칭 (예: *youtube.com -> www.youtube.com 매칭)
 */
function isMatch(url, pattern) {
    if (pattern === '*') return true;
    const regex = new RegExp('^' + pattern.replace(/\*/g, '.*') + '$');
    try {
        return regex.test(new URL(url).hostname);
    } catch (e) {
        return false; 
    }
}

/**
 * 보안 정책 우회 설정
 * @param {Electron.Session} targetSession - 적용할 세션 (보통 session.defaultSession)
 * @param {Object} config - 전체 설정 객체
 */
function setupSecurityBypass(targetSession, config) {
    const bypassList = (config.system_settings && config.system_settings.trusted_types_bypass) || [];
    
    if (bypassList.length === 0) return;

    // 1. 헤더 변조를 통한 CSP(Trusted Types 포함) 무력화
    targetSession.webRequest.onHeadersReceived((details, callback) => {
        const url = details.url;
        const shouldBypass = bypassList.some(pattern => isMatch(url, pattern));

        if (shouldBypass) {
            // CSP 관련 헤더 제거 (가장 강력한 우회 방법)
            const newHeaders = { ...details.responseHeaders };
            delete newHeaders['content-security-policy'];
            delete newHeaders['content-security-policy-report-only'];
            delete newHeaders['x-webkit-csp'];
            delete newHeaders['x-content-security-policy'];

            callback({
                responseHeaders: newHeaders,
                statusLine: details.statusLine
            });
        } else {
            callback({ responseHeaders: details.responseHeaders });
        }
    });

    console.log(`[SecurityBypass] Active for: ${bypassList.join(', ')}`);
}

module.exports = { setupSecurityBypass };