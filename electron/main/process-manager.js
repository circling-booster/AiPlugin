const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const treeKill = require('tree-kill'); // [Checklist] 올바른 Import 확인
const os = require('os');

class ProcessManager {
  constructor() {
    this.pythonProcess = null;
  }

  getPythonPath() {
    const isWin = os.platform() === 'win32';
    const binDir = isWin ? 'Scripts' : 'bin';
    const exeFile = isWin ? 'python.exe' : 'python';
    
    // [Checklist] 경로 무결성: .venv 우선 탐색
    const venvPath = path.join(__dirname, '..', '..', '.venv', binDir, exeFile);
    if (fs.existsSync(venvPath)) return venvPath;
    
    return isWin ? 'python' : 'python3';
  }

  loadSettings() {
    try {
      const settingsPath = path.join(__dirname, '../../config/settings.json');
      if (fs.existsSync(settingsPath)) {
        return JSON.parse(fs.readFileSync(settingsPath, 'utf-8'));
      }
    } catch (e) {
      console.error("[ProcessManager] Settings load failed:", e);
    }
    return { system_mode: 'dual' };
  }

  startCore(apiPort, proxyPort, mainWindow) {
    const pythonExe = this.getPythonPath();
    const scriptPath = path.join(__dirname, '..', '..', 'python', 'main.py');
    const settings = this.loadSettings();
    const isNativeOnly = settings.system_mode === 'native-only';
    
    const args = [scriptPath, '--api-port', apiPort.toString()];

    // [Checklist] 실행 환경: 모드에 따른 인자 분기
    if (isNativeOnly) {
        console.log(`[ProcessManager] Mode: Native-Only (Proxy Disabled)`);
        args.push('--no-proxy');
        args.push('--proxy-port', '0'); // 명시적 0 전달
    } else {
        console.log(`[ProcessManager] Mode: Dual-Pipeline (Proxy: ${proxyPort})`);
        args.push('--proxy-port', proxyPort.toString());
    }

    const env = { ...process.env, PYTHONUNBUFFERED: '1' };
    
    console.log(`[Electron] Spawning Core: ${pythonExe} ${args.join(' ')}`);

    this.pythonProcess = spawn(pythonExe, args, {
      cwd: path.dirname(scriptPath),
      env: env,
      stdio: ['ignore', 'pipe', 'pipe']
    });

    this.pythonProcess.stdout.on('data', (data) => {
      const msg = data.toString().trim();
      console.log(`[Core] ${msg}`);
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('log', msg);
      }
    });

    this.pythonProcess.stderr.on('data', (data) => {
      const msg = data.toString().trim();
      console.error(`[Core-Err] ${msg}`);
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('log', `ERR: ${msg}`);
      }
    });
  }

  killAll() {
    if (this.pythonProcess) {
      console.log('Killing Python Core...');
      treeKill(this.pythonProcess.pid);
      this.pythonProcess = null;
    }
  }
}

module.exports = new ProcessManager();