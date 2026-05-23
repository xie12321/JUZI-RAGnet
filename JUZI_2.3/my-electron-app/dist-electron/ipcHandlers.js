"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.setupIpcHandlers = setupIpcHandlers;
const electron_1 = require("electron");
const promises_1 = __importDefault(require("fs/promises"));
const path_1 = __importDefault(require("path"));
const os_1 = __importDefault(require("os"));
const child_process_1 = require("child_process");
const util_1 = __importDefault(require("util"));
const execPromise = util_1.default.promisify(child_process_1.exec);
// 当前 wiki 根目录（动态）
let currentWikiRoot;
async function ensureDir(dir) {
    try {
        await promises_1.default.mkdir(dir, { recursive: true });
    }
    catch {
        // ignore
    }
}
const CONFIG_FILE = path_1.default.join(os_1.default.homedir(), '.cognitive_enhancer_config.json');
async function loadConfig() {
    try {
        const content = await promises_1.default.readFile(CONFIG_FILE, 'utf-8');
        const config = JSON.parse(content);
        if (config.wikiRoot) {
            const stats = await promises_1.default.stat(config.wikiRoot).catch(() => null);
            if (stats?.isDirectory()) {
                currentWikiRoot = config.wikiRoot;
            }
        }
    }
    catch {
        // ignore missing or corrupt config
    }
}
async function saveConfig() {
    try {
        await promises_1.default.writeFile(CONFIG_FILE, JSON.stringify({ wikiRoot: currentWikiRoot }, null, 2), 'utf-8');
    }
    catch (err) {
        console.error('Failed to save config:', err);
    }
}
// 递归获取文件树（保持不变）
async function getFileTree(dir, relativePath = '') {
    const items = await promises_1.default.readdir(dir);
    const result = [];
    for (const item of items) {
        if (item === '.obsidian')
            continue;
        const fullPath = path_1.default.join(dir, item);
        const relPath = path_1.default.join(relativePath, item);
        const stat = await promises_1.default.stat(fullPath);
        if (stat.isDirectory()) {
            const children = await getFileTree(fullPath, relPath);
            result.push({
                name: item,
                path: fullPath,
                relativePath: relPath,
                type: 'directory',
                children,
            });
        }
        else if (item.endsWith('.md')) {
            result.push({
                name: item,
                path: fullPath,
                relativePath: relPath,
                type: 'file',
            });
        }
    }
    return result;
}
// 复制目录（递归）
async function copyDir(src, dest) {
    await ensureDir(dest);
    const entries = await promises_1.default.readdir(src, { withFileTypes: true });
    for (const entry of entries) {
        const srcPath = path_1.default.join(src, entry.name);
        const destPath = path_1.default.join(dest, entry.name);
        if (entry.isDirectory()) {
            await copyDir(srcPath, destPath);
        }
        else if (entry.isFile() && (entry.name.endsWith('.md') || /\.(png|jpg|jpeg|gif|svg|webp)$/i.test(entry.name))) {
            await promises_1.default.copyFile(srcPath, destPath);
        }
    }
}
async function setupIpcHandlers(wikiRoot) {
    // 设置默认 wiki 目录（从主进程传入的系统路径）
    currentWikiRoot = wikiRoot;
    // 加载用户可能保存过的自定义路径（会覆盖上面的默认值）
    await loadConfig();
    // 确保目录存在
    await ensureDir(currentWikiRoot);
    // 以下所有 IPC handler 保持不变
    electron_1.ipcMain.handle('get-wiki-root', async () => {
        return currentWikiRoot;
    });
    electron_1.ipcMain.handle('set-wiki-root', async (_, newPath) => {
        await ensureDir(newPath);
        currentWikiRoot = newPath;
        await saveConfig();
        return true;
    });
    electron_1.ipcMain.handle('select-directory', async () => {
        const result = await electron_1.dialog.showOpenDialog({
            properties: ['openDirectory'],
        });
        if (!result.canceled && result.filePaths.length > 0) {
            return result.filePaths[0];
        }
        return null;
    });
    electron_1.ipcMain.handle('get-wiki-tree', async () => {
        try {
            return await getFileTree(currentWikiRoot);
        }
        catch (err) {
            console.error('get-wiki-tree error:', err);
            return [];
        }
    });
    electron_1.ipcMain.handle('read-file', async (_, filePath) => {
        const content = await promises_1.default.readFile(filePath, 'utf-8');
        return content;
    });
    electron_1.ipcMain.handle('write-file', async (_, filePath, content) => {
        await promises_1.default.writeFile(filePath, content, 'utf-8');
        return true;
    });
    electron_1.ipcMain.handle('create-file', async (_, parentPath, name) => {
        let targetDir = parentPath;
        if (!targetDir || targetDir === '')
            targetDir = currentWikiRoot;
        const fullPath = path_1.default.join(targetDir, name.endsWith('.md') ? name : name + '.md');
        try {
            await promises_1.default.access(fullPath);
            throw new Error('文件已存在');
        }
        catch (err) {
            if (err.code !== 'ENOENT')
                throw err;
        }
        const defaultContent = `---
title: ${path_1.default.basename(name, '.md')}
tags: []
summary: 
---

# ${path_1.default.basename(name, '.md')}

`;
        await promises_1.default.writeFile(fullPath, defaultContent, 'utf-8');
        return fullPath;
    });
    electron_1.ipcMain.handle('rename-node', async (_, oldPath, newName) => {
        const dir = path_1.default.dirname(oldPath);
        const newPath = path_1.default.join(dir, newName);
        await promises_1.default.rename(oldPath, newPath);
        return newPath;
    });
    electron_1.ipcMain.handle('delete-node', async (_, targetPath) => {
        const stat = await promises_1.default.stat(targetPath);
        if (stat.isDirectory()) {
            await promises_1.default.rm(targetPath, { recursive: true, force: true });
        }
        else {
            await promises_1.default.unlink(targetPath);
        }
        return true;
    });
    electron_1.ipcMain.handle('move-node', async (_, srcPath, destDir) => {
        const destPath = path_1.default.join(destDir, path_1.default.basename(srcPath));
        await promises_1.default.rename(srcPath, destPath);
        return destPath;
    });
    electron_1.ipcMain.handle('import-obsidian-vault', async (_, vaultPath, targetCategory) => {
        let targetDir = currentWikiRoot;
        if (targetCategory) {
            targetDir = path_1.default.join(currentWikiRoot, targetCategory);
            await ensureDir(targetDir);
        }
        await copyDir(vaultPath, targetDir);
        return { success: true, targetDir };
    });
    electron_1.ipcMain.handle('open-in-explorer', async (_, folderPath) => {
        electron_1.shell.showItemInFolder(folderPath);
    });
    electron_1.ipcMain.handle('open-with-obsidian', async (_, filePath) => {
        const url = `obsidian://open?path=${encodeURIComponent(filePath)}`;
        await electron_1.shell.openExternal(url);
    });
    electron_1.ipcMain.handle('get-ollama-models', async () => {
        try {
            const { stdout } = await execPromise('ollama list');
            const lines = stdout.trim().split('\n').slice(1);
            const models = lines.filter((l) => l).map((l) => {
                const parts = l.split(/\s+/);
                return { name: parts[0], size: parts[1] };
            });
            const chatModels = models.filter((m) => !m.name.includes('embed') && !m.name.includes('nomic'));
            const embeddingModels = models.filter((m) => m.name.includes('embed') || m.name.includes('nomic'));
            return { chatModels, embeddingModels };
        }
        catch (error) {
            console.error('获取 Ollama 模型列表失败:', error);
            return { chatModels: [], embeddingModels: [] };
        }
    });
}
