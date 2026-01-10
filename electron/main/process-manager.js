const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const treeKill = require('tree-kill');
const os = require('os');

class ProcessManager {
  constructor() {
    this.pythonProcess = null;
    // [Cleanup] Removed unused cloudProcess
  }

  getPythonPath() {
    const isWin = os.platform() === 'win32';
    const binDir = isWin ? 'Scripts' : 'bin';
    const exeFile = isWin ? 'python.exe' : 'python';
    const venvPath = path.join(__dirname, '..', '..', '.venv', binDir, exeFile);
    const systemPython = isWin ? 'python' : 'python3';
    return fs.existsSync(venvPath) ? venvPath : systemPython;
  }

  // [Modified] Cleaned up legacy cloud parameters (cloudPort removed)
  startCore(apiPort, proxyPort, mainWindow) {
    const scriptPath = path.join(__dirname, '..', '..', 'python', 'main.py');
    const pythonExe = this.getPythonPath();

    console.log(`[Electron] Starting Core: API=${apiPort}, PROXY=${proxyPort} (External Cloud) using ${pythonExe}`);
    
    // [Cleanup] Removed commented-out CLOUD_BASE_URL injection
    const env = { 
        ...process.env, 
        PYTHONUNBUFFERED: '1'
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

  killAll() {
    if (this.pythonProcess) {
      console.log('Killing Python Core...');
      treeKill(this.pythonProcess.pid);
      this.pythonProcess = null;
    }
    // [Cleanup] Removed cloudProcess cleanup logic
  }
}

module.exports = new ProcessManager();