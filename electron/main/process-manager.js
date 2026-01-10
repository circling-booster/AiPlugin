const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const treeKill = require('tree-kill');
const os = require('os'); // [수정] OS 감지를 위해 모듈 추가

class ProcessManager {
  constructor() {
    this.pythonProcess = null;
    this.cloudProcess = null;
  }

  getPythonPath() {
    // [수정] OS에 따른 가상환경 경로 분기 처리
    const isWin = os.platform() === 'win32';
    
    // Windows는 'Scripts', 맥/리눅스는 'bin'
    const binDir = isWin ? 'Scripts' : 'bin';
    // Windows는 'python.exe', 맥/리눅스는 'python'
    const exeFile = isWin ? 'python.exe' : 'python';

    const venvPath = path.join(__dirname, '..', '..', '.venv', binDir, exeFile);
    
    // 가상환경이 없으면 시스템 전역 python 사용 (맥은 보통 python3)
    const systemPython = isWin ? 'python' : 'python3';

    return fs.existsSync(venvPath) ? venvPath : systemPython;
  }

  startCore(apiPort, proxyPort, mainWindow) {
    const scriptPath = path.join(__dirname, '..', '..', 'python', 'main.py');
    const pythonExe = this.getPythonPath();

    console.log(`[Electron] Starting Core: API=${apiPort}, PROXY=${proxyPort} using ${pythonExe}`);
    
    this.pythonProcess = spawn(pythonExe, [
      scriptPath,
      '--api-port', apiPort.toString(),
      '--proxy-port', proxyPort.toString()
    ], {
      cwd: path.dirname(scriptPath),
      env: { ...process.env, PYTHONUNBUFFERED: '1' }, // 로그 실시간 출력 보장
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

  startCloudServer() {
    const scriptPath = path.join(__dirname, '..', '..', 'cloud_server', 'main.py');
    const pythonExe = this.getPythonPath();
    console.log(`[Electron] Starting Cloud Simulation...`);
    
    this.cloudProcess = spawn(pythonExe, [scriptPath], {
      cwd: path.join(__dirname, '..', '..'),
      env: { ...process.env, PYTHONUNBUFFERED: '1' }
    });
    
    this.cloudProcess.stdout.on('data', d => console.log(`[Cloud] ${d.toString().trim()}`));
  }

  killAll() {
    if (this.pythonProcess) {
      console.log('Killing Python Core...');
      treeKill(this.pythonProcess.pid);
      this.pythonProcess = null;
    }
    if (this.cloudProcess) {
      console.log('Killing Cloud Server...');
      treeKill(this.cloudProcess.pid);
      this.cloudProcess = null;
    }
  }
}

module.exports = new ProcessManager();