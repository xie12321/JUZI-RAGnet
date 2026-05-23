"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
const child_process_1 = require("child_process");
const path_1 = __importDefault(require("path"));
const fs_1 = __importDefault(require("fs"));
const ipcHandlers_1 = require("./ipcHandlers");
let mainWindow = null;
let backendProcess = null;
function startBackend(wikiRoot) {
    if (process.env.NODE_ENV === 'development') {
        console.log('开发模式：请确保后端已运行在 http://localhost:8000');
        return;
    }
    let backendPath;
    if (electron_1.app.isPackaged) {
        backendPath = path_1.default.join(process.resourcesPath, 'backend', 'cognitive-backend.exe');
    }
    else {
        backendPath = path_1.default.join(__dirname, '../../backend/dist/cognitive-backend.exe');
    }
    if (!fs_1.default.existsSync(backendPath)) {
        console.error('未找到后端可执行文件:', backendPath);
        return;
    }
    // 传递环境变量，让后端知道 wiki 根目录
    backendProcess = (0, child_process_1.spawn)(backendPath, [], {
        cwd: path_1.default.dirname(backendPath),
        stdio: 'pipe',
        env: {
            ...process.env,
            WIKI_ROOT: wikiRoot,
        },
    });
    if (backendProcess.stdout) {
        backendProcess.stdout.on('data', (data) => {
            console.log(`[backend] ${data}`);
        });
    }
    if (backendProcess.stderr) {
        backendProcess.stderr.on('data', (data) => {
            console.error(`[backend error] ${data}`);
        });
    }
    backendProcess.on('close', (code) => {
        console.log(`后端进程退出，代码 ${code}`);
        backendProcess = null;
    });
    backendProcess.on('error', (err) => {
        console.error('后端进程启动失败:', err);
        backendProcess = null;
    });
}
function stopBackend() {
    if (backendProcess) {
        if (process.platform === 'win32') {
            backendProcess.kill('SIGTERM');
            setTimeout(() => {
                if (backendProcess && !backendProcess.killed) {
                    backendProcess.kill('SIGKILL');
                }
            }, 3000);
        }
        else {
            backendProcess.kill('SIGTERM');
        }
        backendProcess = null;
    }
}
function createWindow() {
    try {
        mainWindow = new electron_1.BrowserWindow({
            width: 1400,
            height: 900,
            minWidth: 900,
            minHeight: 600,
            webPreferences: {
                preload: path_1.default.join(__dirname, 'preload.js'),
                contextIsolation: true,
                nodeIntegration: false,
                spellcheck: false,
            },
            icon: path_1.default.join(__dirname, '../public/icon.png'),
            titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
            show: false,
        });
        mainWindow.once('ready-to-show', () => {
            mainWindow?.show();
        });
        if (process.env.NODE_ENV === 'development') {
            mainWindow.loadURL('http://localhost:5173');
            mainWindow.webContents.openDevTools();
        }
        else {
            mainWindow.loadFile(path_1.default.join(__dirname, '../dist/index.html'));
        }
        mainWindow.webContents.setWindowOpenHandler(({ url }) => {
            electron_1.shell.openExternal(url);
            return { action: 'deny' };
        });
        mainWindow.on('closed', () => {
            mainWindow = null;
        });
    }
    catch (err) {
        console.error('创建窗口失败:', err);
    }
}
electron_1.app.whenReady().then(async () => {
    // 确定 wiki 根目录：开发环境用项目下的 wiki，生产环境用系统用户数据目录
    const isDev = process.env.NODE_ENV === 'development';
    const wikiRoot = isDev
        ? path_1.default.join(process.cwd(), 'wiki')
        : path_1.default.join(electron_1.app.getPath('userData'), 'wiki');
    // 初始化 IPC，传入 wiki 目录（内部可能会被用户之前的配置覆盖）
    await (0, ipcHandlers_1.setupIpcHandlers)(wikiRoot);
    // 启动后端子进程时也传入该路径
    startBackend(wikiRoot);
    createWindow();
    electron_1.app.on('activate', () => {
        if (electron_1.BrowserWindow.getAllWindows().length === 0)
            createWindow();
    });
});
electron_1.app.on('window-all-closed', () => {
    if (process.platform !== 'darwin')
        electron_1.app.quit();
});
electron_1.app.on('will-quit', () => {
    stopBackend();
});
