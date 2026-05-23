"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
electron_1.contextBridge.exposeInMainWorld('electronAPI', {
    // Wiki 管理
    getWikiRoot: () => electron_1.ipcRenderer.invoke('get-wiki-root'),
    setWikiRoot: (path) => electron_1.ipcRenderer.invoke('set-wiki-root', path),
    selectDirectory: () => electron_1.ipcRenderer.invoke('select-directory'),
    getWikiTree: () => electron_1.ipcRenderer.invoke('get-wiki-tree'),
    readFile: (path) => electron_1.ipcRenderer.invoke('read-file', path),
    writeFile: (path, content) => electron_1.ipcRenderer.invoke('write-file', path, content),
    createFile: (parentPath, name) => electron_1.ipcRenderer.invoke('create-file', parentPath, name),
    renameNode: (oldPath, newName) => electron_1.ipcRenderer.invoke('rename-node', oldPath, newName),
    deleteNode: (path) => electron_1.ipcRenderer.invoke('delete-node', path),
    moveNode: (srcPath, destDir) => electron_1.ipcRenderer.invoke('move-node', srcPath, destDir),
    importObsidianVault: (vaultPath, targetCategory) => electron_1.ipcRenderer.invoke('import-obsidian-vault', vaultPath, targetCategory),
    openInExplorer: (path) => electron_1.ipcRenderer.invoke('open-in-explorer', path),
    openWithObsidian: (path) => electron_1.ipcRenderer.invoke('open-with-obsidian', path),
    getOllamaModels: () => electron_1.ipcRenderer.invoke('get-ollama-models'),
    platform: process.platform,
});
