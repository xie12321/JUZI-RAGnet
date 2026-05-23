import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('electronAPI', {
  // Wiki 管理
  getWikiRoot: () => ipcRenderer.invoke('get-wiki-root'),
  setWikiRoot: (path: string) => ipcRenderer.invoke('set-wiki-root', path),
  selectDirectory: () => ipcRenderer.invoke('select-directory'),
  getWikiTree: () => ipcRenderer.invoke('get-wiki-tree'),
  readFile: (path: string) => ipcRenderer.invoke('read-file', path),
  writeFile: (path: string, content: string) => ipcRenderer.invoke('write-file', path, content),
  createFile: (parentPath: string, name: string) => ipcRenderer.invoke('create-file', parentPath, name),
  renameNode: (oldPath: string, newName: string) => ipcRenderer.invoke('rename-node', oldPath, newName),
  deleteNode: (path: string) => ipcRenderer.invoke('delete-node', path),
  moveNode: (srcPath: string, destDir: string) => ipcRenderer.invoke('move-node', srcPath, destDir),
  importObsidianVault: (vaultPath: string, targetCategory?: string) =>
    ipcRenderer.invoke('import-obsidian-vault', vaultPath, targetCategory),
  openInExplorer: (path: string) => ipcRenderer.invoke('open-in-explorer', path),
  openWithObsidian: (path: string) => ipcRenderer.invoke('open-with-obsidian', path),
  getOllamaModels: () => ipcRenderer.invoke('get-ollama-models'),
  platform: process.platform,
});
