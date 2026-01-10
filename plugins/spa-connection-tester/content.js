(function() {
    // 1. 기존 오버레이 제거 (중복 실행 방지)
    const existingPlayer = document.getElementById('aiplugs-lyrics-overlay');
    if (existingPlayer) existingPlayer.remove();

    // ==========================================
    // 2. 설정 (Configuration)
    // ==========================================
    const config = {
        baseFontSize: 34,      // 기본 폰트 크기 (가독성을 위해 키움)
        activeScale: 1.2,      // 활성 라인 확대 배수 (1.2 = 1.2배)
        syncOffset: 0.0,       // 싱크 조절 (초)
        gapThreshold: 2.0,     // 카운트다운 발동 간격
        anticipation: 1.5      // 카운트다운 표시 시간
    };

    // ==========================================
    // 3. 핵심 로직 (Lyrics Engine)
    // ==========================================
    class LyricsEngine {
        constructor() {
            this.lyrics = [];
            this.mergeThreshold = 0.1;
        }

        parseTime(timeStr) {
            try {
                const parts = timeStr.split(':');
                return parseInt(parts[0], 10) * 60 + parseFloat(parts[1]);
            } catch (e) { return 0.0; }
        }

        parseLrc(lrcContent) {
            const lines = lrcContent.split('\n');
            const patternFull = /\[(\d+:\d+(?:\.\d+)?)\]\s*<(\d+:\d+(?:\.\d+)?)>\s*(.*)/;
            const patternStd = /\[(\d+):(\d+)(?:\.(\d+))?\](.*)/;

            let rawLyrics = [];
            lines.forEach(line => {
                line = line.trim();
                if (!line) return;
                
                let startT = 0, endT = null, text = "", matched = false;
                
                // 패턴 1: [시작] <끝> 가사
                let mFull = line.match(patternFull);
                if (mFull) {
                    startT = this.parseTime(mFull[1]);
                    endT = this.parseTime(mFull[2]);
                    text = mFull[3].trim();
                    matched = true;
                } else {
                    // 패턴 2: [시작] 가사
                    let mStd = line.match(patternStd);
                    if (mStd) {
                        const mins = parseInt(mStd[1], 10);
                        const secs = parseInt(mStd[2], 10);
                        let ms = mStd[3] ? parseInt(mStd[3], 10) : 0;
                        if (String(mStd[3]).length === 2) ms *= 10;
                        startT = mins * 60 + secs + (ms / 1000.0);
                        text = mStd[4].trim();
                        matched = true;
                    }
                }

                if (matched && text) rawLyrics.push({ time: startT, endTime: endT, text: text });
            });

            rawLyrics.sort((a, b) => a.time - b.time);

            // 종료 시간 자동 계산
            for (let i = 0; i < rawLyrics.length; i++) {
                if (rawLyrics[i].endTime === null) {
                    if (i < rawLyrics.length - 1) rawLyrics[i].endTime = rawLyrics[i + 1].time;
                    else rawLyrics[i].endTime = rawLyrics[i].time + 3.0;
                }
            }

            this.lyrics = this.mergeShortLines(rawLyrics);
            this.calculateGaps();
        }

        mergeShortLines(lyrics) {
            if (!lyrics.length) return [];
            const merged = [];
            let i = 0;
            while (i < lyrics.length) {
                let current = { ...lyrics[i] };
                let j = 1;
                while ((i + j < lyrics.length) && (j < 3)) {
                    let nextItem = lyrics[i + j];
                    if ((current.endTime - current.time) > this.mergeThreshold) break;
                    if ((nextItem.time - current.endTime) > 0.15) break;

                    current.text += " " + nextItem.text;
                    current.endTime = nextItem.endTime;
                    j++;
                }
                merged.push(current);
                i += j;
            }
            return merged;
        }

        calculateGaps() {
            for (let i = 0; i < this.lyrics.length; i++) {
                this.lyrics[i].needsCountdown = false;
                let gap = (i === 0) ? this.lyrics[i].time : (this.lyrics[i].time - this.lyrics[i-1].endTime);
                if (gap >= config.gapThreshold) this.lyrics[i].needsCountdown = true;
            }
        }

        getCurrentIdx(time) {
            let idx = -1;
            for (let i = 0; i < this.lyrics.length; i++) {
                if (time >= this.lyrics[i].time) idx = i;
                else break;
            }
            return idx;
        }
    }

    // ==========================================
    // 4. 스타일 (CSS) - 선명도 & 확대 로직 강화
    // ==========================================
    const style = document.createElement('style');
    style.innerHTML = `
        :root {
            --ap-font-size: ${config.baseFontSize}px;
            --ap-active-scale: ${config.activeScale};
        }
        #aiplugs-lyrics-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            z-index: 2147483647; pointer-events: none;
            font-family: 'Pretendard', 'Malgun Gothic', sans-serif;
            overflow: hidden; background: transparent;
        }
        /* 컨트롤 패널 */
        .ap-controls {
            position: absolute; top: 20px; left: 20px;
            background: rgba(0, 0, 0, 0.85); padding: 15px; border-radius: 12px;
            pointer-events: auto; color: white; display: flex; flex-direction: column; gap: 8px;
            backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.2);
            width: 240px; font-size: 13px; box-shadow: 0 4px 20px rgba(0,0,0,0.6);
        }
        .ap-row { display: flex; justify-content: space-between; align-items: center; }
        .ap-input { width: 50px; background: #333; border: 1px solid #555; color: white; padding: 3px; border-radius: 4px; text-align: center; }
        
        /* 가사 컨테이너 */
        .ap-lyrics-box {
            position: absolute; top: 50%; left: 0; width: 100%; text-align: center;
            transition: transform 0.1s linear; /* 부드러운 스크롤 */
        }
        .ap-line {
            height: calc(var(--ap-font-size) * 3);
            display: flex; align-items: center; justify-content: center;
            white-space: nowrap; 
            font-size: var(--ap-font-size);
            font-weight: 900; /* 굵게 */
            color: rgba(255,255,255,0.4);
            transition: all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275); /* 쫀득한 모션 */
            -webkit-text-stroke: 1px rgba(0,0,0,0.5); /* 기본 테두리 */
            position: relative;
        }

        /* [핵심] 활성 라인 스타일 (선명도 + 확대) */
        .ap-line.active {
            color: #ffffff !important;
            opacity: 1 !important;
            z-index: 10;
            
            /* 1. 확대: CSS 변수 사용 + !important로 강제 적용 */
            transform: scale(var(--ap-active-scale)) !important;
            
            /* 2. 선명도: 검은 테두리와 딱딱한 그림자 */
            -webkit-text-stroke: 2px black;
            text-shadow: 
                3px 3px 0px #000000, 
                0 0 10px rgba(0, 255, 255, 0.7);
        }

        .ap-line.near { opacity: 0.7; color: #ddd; -webkit-text-stroke: 1px black; }

        /* 카운트다운 점 */
        .ap-dots {
            position: absolute; top: 15%; left: 50%; transform: translateX(-50%);
            display: flex; gap: 6px; opacity: 0; transition: opacity 0.2s;
        }
        .ap-dot { width: 8px; height: 8px; border-radius: 50%; background: #ff3333; box-shadow: 0 0 5px red; }
        .ap-line.show-cnt .ap-dots { opacity: 1; }

        .ap-hidden { display: none; }
        .ap-btn {
            background: linear-gradient(90deg, #00c6ff, #0072ff); border: none; border-radius: 5px;
            color: white; padding: 8px; font-weight: bold; cursor: pointer; width: 100%; margin-top: 5px;
        }
        .ap-btn:hover { filter: brightness(1.1); }
        .ap-btn.red { background: #ff4444; }
        hr { border: 0; border-top: 1px solid #444; width: 100%; margin: 8px 0; }
    `;
    document.head.appendChild(style);

    // ==========================================
    // 5. DOM 생성
    // ==========================================
    const overlay = document.createElement('div');
    overlay.id = 'aiplugs-lyrics-overlay';
    document.body.appendChild(overlay);

    const lyricsBox = document.createElement('div');
    lyricsBox.className = 'ap-lyrics-box';
    overlay.appendChild(lyricsBox);

    const controls = document.createElement('div');
    controls.className = 'ap-controls';
    controls.innerHTML = `
        <div style="font-weight:bold; text-align:center;">AiPlugs Ultimate</div>
        <hr>
        <div class="ap-row"><label>크기 (px)</label><input type="number" id="cfg-size" class="ap-input" value="${config.baseFontSize}"></div>
        <div class="ap-row"><label>확대 (배)</label><input type="number" id="cfg-scale" class="ap-input" value="${config.activeScale}" step="0.1"></div>
        <div class="ap-row"><label>싱크 (초)</label><input type="number" id="cfg-sync" class="ap-input" value="${config.syncOffset}" step="0.1"></div>
        <div style="font-size:11px; color:#aaa; text-align:right; margin-bottom:5px;">(Scale 1.0~2.0 권장)</div>
        <hr>
        <button class="ap-btn" onclick="document.getElementById('inp-audio').click()">🎵 Audio 파일</button>
        <button class="ap-btn" onclick="document.getElementById('inp-lrc').click()">📄 LRC 파일</button>
        <div id="status-msg" style="font-size:11px; color:#ccc; text-align:center; margin-top:5px;">대기중...</div>
        <button class="ap-btn red" id="btn-close">종료</button>
        <input type="file" id="inp-audio" class="ap-hidden" accept="audio/*">
        <input type="file" id="inp-lrc" class="ap-hidden" accept=".lrc,.txt">
    `;
    overlay.appendChild(controls);

    // ==========================================
    // 6. 실행 로직 (Logic Binding)
    // ==========================================
    const engine = new LyricsEngine();
    const audio = new Audio();
    let frameId;
    let domLines = [];
    const statusMsg = document.getElementById('status-msg');

    // 설정 변경 이벤트
    document.getElementById('cfg-size').addEventListener('input', e => {
        document.documentElement.style.setProperty('--ap-font-size', e.target.value + "px");
    });
    document.getElementById('cfg-scale').addEventListener('input', e => {
        let val = parseFloat(e.target.value);
        // 안전 장치: 실수로 100 입력 시 100배가 되지 않도록 경고 및 처리 (보통 2.0 이하 사용)
        if(val > 5) { 
            statusMsg.textContent = "⚠️ 확대 비율이 너무 큽니다!";
            statusMsg.style.color = "orange";
        } else {
            statusMsg.style.color = "#ccc";
        }
        document.documentElement.style.setProperty('--ap-active-scale', val);
    });
    document.getElementById('cfg-sync').addEventListener('input', e => config.syncOffset = parseFloat(e.target.value));

    // 파일 로드
    document.getElementById('inp-audio').addEventListener('change', e => {
        if(e.target.files[0]) {
            audio.src = URL.createObjectURL(e.target.files[0]);
            statusMsg.textContent = "오디오 준비완료";
            if(engine.lyrics.length) audio.play();
        }
    });
    document.getElementById('inp-lrc').addEventListener('change', e => {
        if(e.target.files[0]) {
            const r = new FileReader();
            r.onload = evt => {
                engine.parseLrc(evt.target.result);
                renderDOM();
                statusMsg.textContent = `가사 로드됨 (${engine.lyrics.length}줄)`;
                if(audio.src) audio.play();
                loop();
            };
            r.readAsText(e.target.files[0]);
        }
    });
    document.getElementById('btn-close').addEventListener('click', () => {
        audio.pause();
        cancelAnimationFrame(frameId);
        overlay.remove();
        style.remove();
    });

    function renderDOM() {
        lyricsBox.innerHTML = '';
        domLines = [];
        engine.lyrics.forEach(line => {
            const div = document.createElement('div');
            div.className = 'ap-line';
            div.innerHTML = `<span>${line.text}</span>`;
            
            if(line.needsCountdown) {
                const dots = document.createElement('div');
                dots.className = 'ap-dots';
                dots.innerHTML = '<div class="ap-dot"></div><div class="ap-dot"></div><div class="ap-dot"></div>';
                div.appendChild(dots);
            }
            lyricsBox.appendChild(div);
            domLines.push(div);
        });
    }

    function loop() {
        cancelAnimationFrame(frameId);
        function update() {
            if(!audio.paused) {
                const time = audio.currentTime + config.syncOffset;
                const idx = engine.getCurrentIdx(time);
                
                // 스크롤 (폰트크기 * 3 = 줄높이)
                const lineHeight = parseInt(document.getElementById('cfg-size').value) * 3;
                lyricsBox.style.transform = `translateY(${-idx * lineHeight}px)`;

                domLines.forEach((div, i) => {
                    div.classList.remove('active', 'near', 'show-cnt');
                    
                    // 카운트다운
                    if (i > idx && engine.lyrics[i].needsCountdown) {
                        const remain = engine.lyrics[i].time - time;
                        if (remain > 0 && remain <= config.anticipation) {
                            div.classList.add('show-cnt');
                            const dots = div.querySelectorAll('.ap-dot');
                            dots.forEach((d, di) => {
                                const th = (3 - di) * (config.anticipation / 3.0);
                                d.style.opacity = (remain <= th) ? 1 : 0.2;
                            });
                        }
                    }

                    // 활성 라인 처리
                    if(i === idx) {
                        div.classList.add('active'); // CSS !important로 scale 강제 적용
                    } else if (Math.abs(i - idx) <= 2) {
                        div.classList.add('near');
                        div.style.transform = 'scale(0.9)'; // 주변 가사는 작게
                        div.style.opacity = Math.max(0.2, 1 - Math.abs(i - idx)*0.3);
                    } else {
                        div.style.transform = 'scale(0.8)';
                        div.style.opacity = 0.1;
                    }
                });
            }
            frameId = requestAnimationFrame(update);
        }
        update();
    }

    console.log("%c AiPlugs Ultimate Player Loaded ", "background: black; color: #00c6ff; font-weight: bold; padding: 5px; font-size: 14px;");
})();