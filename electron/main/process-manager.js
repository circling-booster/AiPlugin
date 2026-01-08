const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const treeKill = require('tree-kill');

class ProcessManager {
  constructor() {
    this.pythonProcess = null;
    this.cloudProcess = null;
  }

  getPythonPath() {
    // Windows: 가상환경(venv) 우선, 없으면 시스템 python 사용
    const venvPath = path.join(__dirname, '..', '..', 'venv', 'Scripts', 'python.exe');
    return fs.existsSync(venvPath) ? venvPath : 'python';
  }

  startCore(apiPort, proxyPort, mainWindow) {
    const scriptPath = path.join(__dirname, '..', '..', 'python', 'main.py');
    const pythonExe = this.getPythonPath();

    console.log(`[Electron] Starting Core: API=${apiPort}, PROXY=${proxyPort}`);
    
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