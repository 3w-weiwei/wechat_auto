const { spawn } = require('child_process');
const path = require('path');

let engineProcess = null;

function findUv() {
  const homePath = process.env.USERPROFILE || process.env.HOME || '~';
  const candidates = [
    path.join(homePath, '.local', 'bin', 'uv.exe'),
    path.join(homePath, '.cargo', 'bin', 'uv.exe'),
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

function startEngine() {
  return new Promise((resolve) => {
    const engineDir = getEngineDir();
    const uvPath = findUv();

    console.log(`[Python Manager] Engine dir: ${engineDir}`);
    console.log(`[Python Manager] Using uv: ${uvPath}`);

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
