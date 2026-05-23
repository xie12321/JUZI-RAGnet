import { ipcMain, dialog, shell } from 'electron';
import fs from 'fs/promises';
import path from 'path';
import os from 'os';
import { exec } from 'child_process';
import util from 'util';

const execPromise = util.promisify(exec);

// 当前 wiki 根目录（动态）
let currentWikiRoot: string;

async function ensureDir(dir: string) {
  try {
    await fs.mkdir(dir, { recursive: true });
  } catch {
    // ignore
  }
}

const CONFIG_FILE = path.join(os.homedir(), '.cognitive_enhancer_config.json');

async function loadConfig() {
  try {
    const content = await fs.readFile(CONFIG_FILE, 'utf-8');
    const config = JSON.parse(content);
    if (config.wikiRoot) {
      const stats = await fs.stat(config.wikiRoot).catch(() => null);
      if (stats?.isDirectory()) {
        currentWikiRoot = config.wikiRoot;
      }
    }
  } catch {
    // ignore missing or corrupt config
  }
}

async function saveConfig() {
  try {
    await fs.writeFile(CONFIG_FILE, JSON.stringify({ wikiRoot: currentWikiRoot }, null, 2), 'utf-8');
  } catch (err) {
    console.error('Failed to save config:', err);
  }
}

// 递归获取文件树（保持不变）
async function getFileTree(dir: string, relativePath: string = ''): Promise<any[]> {
  const items = await fs.readdir(dir);
  const result: any[] = [];

  for (const item of items) {
    if (item === '.obsidian') continue;
    const fullPath = path.join(dir, item);
    const relPath = path.join(relativePath, item);
    const stat = await fs.stat(fullPath);

    if (stat.isDirectory()) {
      const children = await getFileTree(fullPath, relPath);
      result.push({
        name: item,
        path: fullPath,
        relativePath: relPath,
        type: 'directory',
        children,
      });
    } else if (item.endsWith('.md')) {
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
async function copyDir(src: string, dest: string) {
  await ensureDir(dest);
  const entries = await fs.readdir(src, { withFileTypes: true });
  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);
    if (entry.isDirectory()) {
      await copyDir(srcPath, destPath);
    } else if (entry.isFile() && (entry.name.endsWith('.md') || /\.(png|jpg|jpeg|gif|svg|webp)$/i.test(entry.name))) {
      await fs.copyFile(srcPath, destPath);
    }
  }
}

export async function setupIpcHandlers(wikiRoot: string) {
  // 设置默认 wiki 目录（从主进程传入的系统路径）
  currentWikiRoot = wikiRoot;
  // 加载用户可能保存过的自定义路径（会覆盖上面的默认值）
  await loadConfig();
  // 确保目录存在
  await ensureDir(currentWikiRoot);

  // 以下所有 IPC handler 保持不变
  ipcMain.handle('get-wiki-root', async () => {
    return currentWikiRoot;
  });

  ipcMain.handle('set-wiki-root', async (_, newPath: string) => {
    await ensureDir(newPath);
    currentWikiRoot = newPath;
    await saveConfig();
    return true;
  });

  ipcMain.handle('select-directory', async () => {
    const result = await dialog.showOpenDialog({
      properties: ['openDirectory'],
    });
    if (!result.canceled && result.filePaths.length > 0) {
      return result.filePaths[0];
    }
    return null;
  });

  ipcMain.handle('get-wiki-tree', async () => {
    try {
      return await getFileTree(currentWikiRoot);
    } catch (err) {
      console.error('get-wiki-tree error:', err);
      return [];
    }
  });

  ipcMain.handle('read-file', async (_, filePath: string) => {
    const content = await fs.readFile(filePath, 'utf-8');
    return content;
  });

  ipcMain.handle('write-file', async (_, filePath: string, content: string) => {
    await fs.writeFile(filePath, content, 'utf-8');
    return true;
  });

  ipcMain.handle('create-file', async (_, parentPath: string, name: string) => {
    let targetDir = parentPath;
    if (!targetDir || targetDir === '') targetDir = currentWikiRoot;
    const fullPath = path.join(targetDir, name.endsWith('.md') ? name : name + '.md');
    try {
      await fs.access(fullPath);
      throw new Error('文件已存在');
    } catch (err: any) {
      if (err.code !== 'ENOENT') throw err;
    }
    const defaultContent = `---
title: ${path.basename(name, '.md')}
tags: []
summary: 
---

# ${path.basename(name, '.md')}

`;
    await fs.writeFile(fullPath, defaultContent, 'utf-8');
    return fullPath;
  });

  ipcMain.handle('rename-node', async (_, oldPath: string, newName: string) => {
    const dir = path.dirname(oldPath);
    const newPath = path.join(dir, newName);
    await fs.rename(oldPath, newPath);
    return newPath;
  });

  ipcMain.handle('delete-node', async (_, targetPath: string) => {
    const stat = await fs.stat(targetPath);
    if (stat.isDirectory()) {
      await fs.rm(targetPath, { recursive: true, force: true });
    } else {
      await fs.unlink(targetPath);
    }
    return true;
  });

  ipcMain.handle('move-node', async (_, srcPath: string, destDir: string) => {
    const destPath = path.join(destDir, path.basename(srcPath));
    await fs.rename(srcPath, destPath);
    return destPath;
  });

  ipcMain.handle('import-obsidian-vault', async (_, vaultPath: string, targetCategory?: string) => {
    let targetDir = currentWikiRoot;
    if (targetCategory) {
      targetDir = path.join(currentWikiRoot, targetCategory);
      await ensureDir(targetDir);
    }
    await copyDir(vaultPath, targetDir);
    return { success: true, targetDir };
  });

  ipcMain.handle('open-in-explorer', async (_, folderPath: string) => {
    shell.showItemInFolder(folderPath);
  });

  ipcMain.handle('open-with-obsidian', async (_, filePath: string) => {
    const url = `obsidian://open?path=${encodeURIComponent(filePath)}`;
    await shell.openExternal(url);
  });

  ipcMain.handle('get-ollama-models', async () => {
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
    } catch (error) {
      console.error('获取 Ollama 模型列表失败:', error);
      return { chatModels: [], embeddingModels: [] };
    }
  });
}