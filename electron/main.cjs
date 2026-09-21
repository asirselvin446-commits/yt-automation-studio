const { app, BrowserWindow, dialog, ipcMain, shell } = require('electron');
const path = require('path');
const http = require('http');
const { spawn, execSync } = require('child_process');

let mainWindow = null;
let backendProcess = null;
let isQuitting = false;
let backendRestarts = 0;
let lastRestartAt = 0;

// If the backend dies while the app is open, bring it back and reload the UI so
// the user never lands on a dead "Failed to fetch" state.
function handleBackendExit(code, signal) {
  console.log(`[Electron] Backend exited code=${code} signal=${signal}`);
  if (isQuitting) return;
  const now = Date.now();
  // Reset the burst counter if it's been calm for a while.
  if (now - lastRestartAt > 30000) backendRestarts = 0;
  lastRestartAt = now;
  if (backendRestarts >= 5) {
    console.error('[Electron] Backend keeps exiting; stopping auto-restart.');
    return;
  }
  backendRestarts++;
  setTimeout(() => {
    if (isQuitting) return;
    spawnBackendProcess();
    waitForBackend((ready) => {
      if (ready && mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.loadURL(BACKEND_URL);
      }
    });
  }, 1000);
}
// Dedicated port so this app never piggybacks on another backend (e.g. a dev
// server or another studio build) that happens to be on the common 8000.
const BACKEND_PORT = 8473;
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;

// Determine project root directory
const isPackaged = app.isPackaged;
const ROOT_DIR = isPackaged
  ? path.dirname(app.getPath('exe'))
  : path.resolve(__dirname, '..');

function getPythonPath() {
  const fs = require('fs');
  if (process.platform === 'win32') {
    const candidates = [
      path.join(ROOT_DIR, '.venv', 'Scripts', 'pythonw.exe'),
      path.join(__dirname, '..', '.venv', 'Scripts', 'pythonw.exe'),
      path.join(ROOT_DIR, '.venv', 'Scripts', 'python.exe'),
      path.join(__dirname, '..', '.venv', 'Scripts', 'python.exe'),
    ];
    for (const cand of candidates) {
      if (fs.existsSync(cand)) return cand;
    }
  } else {
    const candidates = [
      path.join(ROOT_DIR, '.venv', 'bin', 'python'),
      path.join(__dirname, '..', '.venv', 'bin', 'python'),
    ];
    for (const cand of candidates) {
      if (fs.existsSync(cand)) return cand;
    }
  }
  return 'python';
}

function spawnBackendProcess() {
  const fs = require('fs');
  // 1. Check for standalone packaged backend executable first
  const binaryCandidates = [
    path.join(ROOT_DIR, 'backend_engine.exe'),
    path.join(ROOT_DIR, 'backend_engine', 'backend_engine.exe'),
    path.join(ROOT_DIR, 'backend_runner.exe'),
  ];
  const spawnEnv = { ...process.env, BACKEND_PORT: String(BACKEND_PORT) };
  for (const bin of binaryCandidates) {
    if (fs.existsSync(bin)) {
      try {
        backendProcess = spawn(bin, [], {
          cwd: ROOT_DIR,
          windowsHide: true,
          stdio: 'ignore',
          detached: false,
          env: spawnEnv,
        });
        backendProcess.on('exit', handleBackendExit);
        backendProcess.on('error', (err) => console.error('[Electron] Backend error:', err));
        return;
      } catch (err) {
        console.error('[Electron] Failed to launch binary backend:', err);
      }
    }
  }

  // 2. Launch via Python script runner
  const pythonExe = getPythonPath();
  const runnerScript = path.join(__dirname, '..', 'backend_runner.py');

  try {
    backendProcess = spawn(pythonExe, [runnerScript], {
      cwd: ROOT_DIR,
      windowsHide: true,
      stdio: 'ignore',
      detached: false,
      env: spawnEnv,
    });

    backendProcess.on('error', (err) => {
      console.error('[Electron] Backend launch error:', err);
    });

    backendProcess.on('exit', handleBackendExit);
  } catch (err) {
    console.error('[Electron] Failed to start backend:', err);
  }
}

function startBackend() {
  const healthUrl = `${BACKEND_URL}/api/v1/system/health`;
  const req = http.get(healthUrl, (res) => {
    if (res.statusCode === 200) {
      console.log('[Electron] Healthy backend already active on port', BACKEND_PORT);
      return;
    }
    spawnBackendProcess();
  });

  req.on('error', () => {
    spawnBackendProcess();
  });
}

function killBackend() {
  if (backendProcess && backendProcess.pid) {
    try {
      if (process.platform === 'win32') {
        execSync(`taskkill /F /T /PID ${backendProcess.pid}`, { stdio: 'ignore' });
      } else {
        backendProcess.kill();
      }
    } catch (e) {
      // Process may already have terminated
    }
    backendProcess = null;
  }
}

function waitForBackend(callback, maxAttempts = 150, intervalMs = 200) {
  let attempts = 0;
  const healthUrl = `${BACKEND_URL}/api/v1/system/health`;

  const check = () => {
    attempts++;
    http.get(healthUrl, (res) => {
      if (res.statusCode === 200 || res.statusCode === 404) {
        callback(true);
      } else if (attempts < maxAttempts) {
        setTimeout(check, intervalMs);
      } else {
        callback(false);
      }
    }).on('error', () => {
      if (attempts < maxAttempts) {
        setTimeout(check, intervalMs);
      } else {
        callback(false);
      }
    });
  };

  check();
}

function createWindow() {
  const iconPath = path.join(ROOT_DIR, 'assets', 'icon.png');

  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    backgroundColor: '#090a0f',
    title: 'YT Automation Studio',
    icon: iconPath,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      devTools: false,
    },
  });

  // Sleek dark splash while backend boots
  const splashHtml = `
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8">
        <title>YT Automation Studio</title>
        <style>
          body {
            margin: 0;
            background: #090a0f;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #ffffff;
            user-select: none;
          }
          .container {
            text-align: center;
          }
          .spinner {
            width: 42px;
            height: 42px;
            border: 3px solid rgba(99, 102, 241, 0.15);
            border-top: 3px solid #6366f1;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 0 auto 20px auto;
          }
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
          h2 {
            font-size: 16px;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin: 0 0 6px 0;
            color: #f1f5f9;
          }
          p {
            font-size: 12px;
            color: #64748b;
            margin: 0;
          }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="spinner"></div>
          <h2>YT Automation Studio</h2>
          <p>Initializing desktop engine...</p>
        </div>
      </body>
    </html>
  `;

  mainWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(splashHtml));

  // Wait for FastAPI backend to be online, then load the real app.
  waitForBackend((ready) => {
    if (!mainWindow || mainWindow.isDestroyed()) return;
    if (ready) {
      mainWindow.loadURL(BACKEND_URL);
    } else {
      // Don't dump the user onto a browser "refused to connect" page — show our
      // own error with a retry, and try to (re)start the backend.
      const errHtml = `
        <!DOCTYPE html><html><head><meta charset="utf-8">
        <style>body{margin:0;background:#090a0f;color:#e2e8f0;height:100vh;display:flex;
        align-items:center;justify-content:center;font-family:'Segoe UI',system-ui,sans-serif}
        .c{text-align:center;max-width:420px;padding:32px}h2{margin:0 0 10px}
        p{color:#94a3b8;font-size:13px;line-height:1.5}
        button{margin-top:18px;padding:10px 20px;border:0;border-radius:8px;background:#6366f1;
        color:#fff;font-weight:600;cursor:pointer}</style></head>
        <body><div class="c"><h2>Starting engine…</h2>
        <p>The desktop engine is taking longer than usual to start. This can happen on
        first launch. Click retry in a moment.</p>
        <button onclick="location.reload()">Retry</button></div></body></html>`;
      mainWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(errHtml));
      startBackend();
      setTimeout(() => {
        waitForBackend((r2) => {
          if (r2 && mainWindow && !mainWindow.isDestroyed()) mainWindow.loadURL(BACKEND_URL);
        });
      }, 2000);
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// IPC Handlers
ipcMain.handle('select-folder', async () => {
  if (!mainWindow) return null;
  const res = await dialog.showOpenDialog(mainWindow, {
    title: 'Select YouTube Automation Folder',
    properties: ['openDirectory', 'createDirectory'],
  });
  if (res.canceled || !res.filePaths.length) {
    return null;
  }
  return res.filePaths[0];
});

ipcMain.handle('open-external', async (event, url) => {
  if (url && (url.startsWith('https://') || url.startsWith('http://'))) {
    await shell.openExternal(url);
  }
});

ipcMain.handle('get-version', () => {
  return app.getVersion();
});

// App Lifecycle
app.whenReady().then(() => {
  startBackend();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('before-quit', () => {
  isQuitting = true;
  killBackend();
});

app.on('window-all-closed', () => {
  isQuitting = true;
  killBackend();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
