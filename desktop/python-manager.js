const { spawn } = require('child_process');
const path = require('path');

let engineProcess = null;

function findUv() {
  const homePath = process.env.USERPROFILE || process.env.HOME || '~';
  const localAppData = process.env.LOCALAPPDATA || '';
  const appData = process.env.APPDATA || '';
  const candidates = [
    path.join(homePath, '.local', 'bin', 'uv.exe'),
    path.join(homePath, '.cargo', 'bin', 'uv.exe'),
    path.join(localAppData, 'Programs', 'uv', 'uv.exe'),
    path.join(appData, 'uv', 'uv.exe'),
    'uv',
    'uv.exe',
    'uv.bat',
  ];
  for (const c of candidates) {
    try {
      const result = require('child_process').execSync(`"${c}" --version`, { stdio: 'pipe', timeout: 5000 });
      if (result.toString().includes('uv')) return c;
    } catch {}
  }
  return 'uv';
}

function getEngineDir() {
  // In development, engine is one level up
  return path.join(__dirname, '..');
}

function killPort(port) {
  try {
    const { execSync } = require('child_process');
    const result = execSync(`netstat -ano | findstr :${port}`, { encoding: 'utf8', timeout: 5000 });
    const pidSet = new Set();
    for (const line of result.split('\n')) {
      if (!line.includes('LISTENING')) continue;
      const parts = line.trim().split(/\s+/);
      const pid = parts[parts.length - 1];
      if (pid && pid !== '0' && !pidSet.has(pid)) {
        pidSet.add(pid);
        execSync(`taskkill /f /pid ${pid}`, { timeout: 5000 });
        console.log(`[Python Manager] Killed PID ${pid} holding port ${port}`);
      }
    }
  } catch {
    // Port is free or netstat failed — either is fine
  }
}

function startEngine() {
  return new Promise((resolve) => {
    const engineDir = getEngineDir();
    const uvPath = findUv();

    console.log(`[Python Manager] Engine dir: ${engineDir}`);
    console.log(`[Python Manager] Using uv: ${uvPath}`);

    // Pre-cleanup: kill any process still holding port 9876
    if (process.platform === 'win32') {
      killPort(9876);
    }

    try {
      engineProcess = spawn(uvPath, ['run', 'python', '-m', 'engine.main'], {
        cwd: engineDir,
        stdio: ['pipe', 'pipe', 'pipe'],
        env: { ...process.env, PYTHONUNBUFFERED: '1' },
        shell: true,
      });

      engineProcess.stdout.on('data', (data) => {
        process.stdout.write(`[Engine] ${data}`);
      });

      engineProcess.stderr.on('data', (data) => {
        process.stderr.write(`[Engine] ${data}`);
      });

      engineProcess.on('error', (err) => {
        console.error(`[Python Manager] Spawn error: ${err.message}`);
        resolve(false);
      });

      engineProcess.on('close', (code) => {
        console.log(`[Python Manager] Engine exited (code ${code})`);
        engineProcess = null;
      });

      // Give engine 3s to start
      setTimeout(() => {
        if (engineProcess && !engineProcess.killed) {
          console.log('[Python Manager] Engine started OK');
          resolve(true);
        } else {
          resolve(false);
        }
      }, 3000);
    } catch (err) {
      console.error(`[Python Manager] Error: ${err.message}`);
      resolve(false);
    }
  });
}

function stopEngine() {
  if (engineProcess && !engineProcess.killed) {
    console.log('[Python Manager] Stopping engine...');
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', String(engineProcess.pid), '/f', '/t']);
      // Wait briefly then ensure port is freed
      setTimeout(() => { killPort(9876); }, 2000);
    } else {
      engineProcess.kill('SIGTERM');
      setTimeout(() => {
        if (engineProcess && !engineProcess.killed) {
          engineProcess.kill('SIGKILL');
        }
      }, 3000);
    }
    engineProcess = null;
  }
}

module.exports = { startEngine, stopEngine };
