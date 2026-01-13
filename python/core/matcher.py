import re
from urllib.parse import urlparse

class UrlMatcher:
    @staticmethod
    def match(pattern: str, url: str) -> bool:
        """
        Chrome Extension 스타일의 매칭 로직을 구현합니다.
        <all_urls>, *://*/*, http://localhost:3000/* 등을 처리합니다.
        """
        if pattern == "<all_urls>":
            return True
            
        try:
            # 1. Scheme, Host(포트 포함), Path 분리
            parts = pattern.split("://")
            if len(parts) != 2:
                # 스킴 와일드카드 처리 (예: *://google.com/*)
                if pattern.startswith("*://"):
                    scheme_pat = "*"
                    rest = pattern[4:]
                else:
                    return False 
            else:
                scheme_pat, rest = parts
            
            if '/' in rest:
                host_port_pat, path_pat = rest.split('/', 1)
                path_pat = '/' + path_pat
            else:
                host_port_pat = rest
                path_pat = '/*'

            # 2. URL 파싱
            parsed = urlparse(url)
            u_scheme = parsed.scheme
            u_hostname = parsed.hostname # 포트 제외된 호스트
            u_port = parsed.port         # 포트 번호 (없으면 None)
            u_path = parsed.path
            
            # 3. Scheme 매칭
            if not UrlMatcher._match_scheme(scheme_pat, u_scheme):
                return False
                
            # 4. Host 및 Port 매칭
            if not UrlMatcher._match_host_and_port(host_port_pat, u_hostname, u_port):
                return False
                
            # 5. Path 매칭
            if not UrlMatcher._match_path(path_pat, u_path):
                return False
                
            return True

        except Exception:
            return False

    @staticmethod
    def _match_scheme(pattern, scheme):
        if pattern == '*': return scheme in ['http', 'https']
        return pattern == scheme

    @staticmethod
    def _match_host_and_port(pattern, hostname, port):
        # 패턴에 포트가 명시되어 있는지 확인 (예: localhost:3000)
        if ':' in pattern:
            pat_host, pat_port = pattern.split(':', 1)
        else:
            pat_host, pat_port = pattern, None

        # 1) 포트 검사
        if pat_port:
            if pat_port == "*":
                pass # 포트 와일드카드
            elif str(port) != pat_port:
                if port is None: 
                    # URL에 포트가 없는데 패턴엔 있는 경우 (http=80 등 정규화 로직이 없다면 불일치 처리)
                    return False
                return False

        # 2) 호스트 검사
        if pat_host == '*': return True
        if pat_host.startswith('*.'):
            suffix = pat_host[2:]
            return hostname == suffix or hostname.endswith('.' + suffix)
        
        return pat_host == hostname

    @staticmethod
    def _match_path(pattern, path):
        # 정규식 변환: 특수문자 이스케이프 후 *만 .*로 변경
        regex = '^' + re.escape(pattern).replace(r'\*', '.*') + '$'
        return re.match(regex, path) is not None