const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const treeKill = require('tree-kill');
const os = require('os');

class ProcessManager {
  constructor() {
    this.pythonProcess = null;
    this.cloudProcess = null;
    // this.cloudPort 제거: startCore 인자로 직접 전달받으므로 상태 저장이 불필요함
  }

  getPythonPath() {
    const isWin = os.platform() === 'win32';
    const binDir = isWin ? 'Scripts' : 'bin';
    const exeFile = isWin ? 'python.exe' : 'python';
    const venvPath = path.join(__dirname, '..', '..', '.venv', binDir, exeFile);
    const systemPython = isWin ? 'python' : 'python3';
    return fs.existsSync(venvPath) ? venvPath : systemPython;
  }

  // [Fixed] cloudPort added to arguments
  startCore(apiPort, proxyPort, cloudPort, mainWindow) {
    const scriptPath = path.join(__dirname, '..', '..', 'python', 'main.py');
    const pythonExe = this.getPythonPath();

    console.log(`[Electron] Starting Core: API=${apiPort}, PROXY=${proxyPort}, CLOUD_LINK=${cloudPort} using ${pythonExe}`);
    
    // [Fixed] Pass Cloud URL as Env var for Core to sync
    const env = { 
        ...process.env, 
        PYTHONUNBUFFERED: '1',
        CLOUD_BASE_URL: `http://localhost:${cloudPort}` // Sync Cloud Port to Core
    };
    
    this.pythonProcess = spawn(pythonExe, [
      scriptPath,
      '--api-port', apiPort.toString(),
      '--proxy-port', proxyPort.toString()
    ], {
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

  // [Fixed] Accept dynamic port
  startCloudServer(port) {
    const scriptPath = path.join(__dirname, '..', '..', 'cloud_server', 'main.py');
    const pythonExe = this.getPythonPath();
    console.log(`[Electron] Starting Cloud Simulation on port ${port}...`);
    
    this.cloudProcess = spawn(pythonExe, [
        scriptPath, 
        '--port', port.toString() // Pass port arg
    ], {
      cwd: path.join(__dirname, '..', '..'),
      env: { ...process.env, PYTHONUNBUFFERED: '1' }
    });
    
    this.cloudProcess.stdout.on('data', d => console.log(`[Cloud] ${d.toString().trim()}`));
    this.cloudProcess.stderr.on('data', d => console.error(`[Cloud-Err] ${d.toString().trim()}`));
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