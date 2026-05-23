import React, { useState, useCallback } from 'react';
import FileTree from './FileTree';
import MarkdownEditor from './MarkdownEditor';

const WikiManager: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [newFileModal, setNewFileModal] = useState(false);
  const [newFileName, setNewFileName] = useState('');
  const [importModal, setImportModal] = useState(false);
  const [importPath, setImportPath] = useState('');
  const [importTarget, setImportTarget] = useState('');
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const showToast = useCallback((message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  }, []);

  const handleFileSelect = useCallback((path: string) => {
    setSelectedFile(path);
  }, []);

  const handleSave = useCallback(() => {
    setRefreshKey((prev) => prev + 1);
  }, []);

  const handleNewFile = useCallback(async () => {
    if (!newFileName.trim()) return;
    try {
      await window.electronAPI.createFile('', newFileName.trim());
      setRefreshKey((prev) => prev + 1);
      setNewFileModal(false);
      setNewFileName('');
      showToast('文件创建成功');
    } catch (err: any) {
      showToast(err.message || '创建失败', 'error');
    }
  }, [newFileName, showToast]);

  const handleImportObsidian = useCallback(async () => {
    if (!importPath) return;
    try {
      await window.electronAPI.importObsidianVault(importPath, importTarget || undefined);
      setRefreshKey((prev) => prev + 1);
      setImportModal(false);
      setImportPath('');
      setImportTarget('');
      showToast('导入完成');
    } catch (err: any) {
      showToast(err.message || '导入失败', 'error');
    }
  }, [importPath, importTarget, showToast]);

  const handleSelectImportDir = useCallback(async () => {
    const path = await window.electronAPI.selectDirectory();
    if (path) setImportPath(path);
  }, []);

  const handleOpenInExplorer = useCallback(async () => {
    try {
      const root = await window.electronAPI.getWikiRoot();
      await window.electronAPI.openInExplorer(root);
    } catch {
      showToast('打开失败', 'error');
    }
  }, [showToast]);

  const handleSetWikiRoot = useCallback(async () => {
    const newRoot = await window.electronAPI.selectDirectory();
    if (newRoot) {
      try {
        await window.electronAPI.setWikiRoot(newRoot);
        setRefreshKey((prev) => prev + 1);
        setSelectedFile(null);
        showToast('Wiki 根目录已更新');
      } catch {
        showToast('设置失败', 'error');
      }
    }
  }, [showToast]);

  return (
    <div className="flex" style={{ height: '100%' }}>
      {/* Sidebar */}
      <div
        style={{
          width: 280,
          minWidth: 280,
          borderRight: '1px solid var(--border-color)',
          background: 'var(--bg-surface)',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Toolbar */}
        <div
          style={{
            padding: 'var(--space-3)',
            borderBottom: '1px solid var(--border-color)',
            display: 'flex',
            flexWrap: 'wrap',
            gap: 'var(--space-2)',
          }}
        >
          <button
            className="btn btn-sm"
            onClick={() => setNewFileModal(true)}
            title="新建文件"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            新建
          </button>
          <button
            className="btn btn-sm"
            onClick={() => setImportModal(true)}
            title="导入 Obsidian"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            导入
          </button>
          <button
            className="btn btn-sm btn-ghost"
            onClick={handleOpenInExplorer}
            title="在资源管理器中打开"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
              <polyline points="15 3 21 3 21 9" />
              <line x1="10" y1="14" x2="21" y2="3" />
            </svg>
          </button>
          <button
            className="btn btn-sm btn-ghost"
            onClick={handleSetWikiRoot}
            title="设置 Wiki 目录"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
          </button>
        </div>

        {/* File Tree */}
        <div className="flex-1" style={{ overflow: 'auto', padding: 'var(--space-2)' }}>
          <FileTree
            key={refreshKey}
            onSelectFile={handleFileSelect}
            selectedFile={selectedFile}
            onRefresh={() => setRefreshKey((prev) => prev + 1)}
          />
        </div>
      </div>

      {/* Editor */}
      <div className="flex-1" style={{ background: 'var(--bg-base)' }}>
        <MarkdownEditor filePath={selectedFile} onSave={handleSave} />
      </div>

      {/* New File Modal */}
      {newFileModal && (
        <div className="modal-overlay" onClick={() => setNewFileModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 style={{ fontSize: '16px', fontWeight: 600 }}>新建文件</h3>
              <button className="btn btn-ghost btn-sm" onClick={() => setNewFileModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label className="form-label">文件名（不需要 .md 后缀）</label>
                <input
                  className="input"
                  type="text"
                  value={newFileName}
                  onChange={(e) => setNewFileName(e.target.value)}
                  placeholder="例如：读书笔记"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleNewFile();
                  }}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-ghost" onClick={() => setNewFileModal(false)}>取消</button>
              <button className="btn btn-primary" onClick={handleNewFile} disabled={!newFileName.trim()}>
                创建
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Import Modal */}
      {importModal && (
        <div className="modal-overlay" onClick={() => setImportModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 style={{ fontSize: '16px', fontWeight: 600 }}>导入 Obsidian 仓库</h3>
              <button className="btn btn-ghost btn-sm" onClick={() => setImportModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label className="form-label">Obsidian 仓库路径</label>
                <div className="flex" style={{ gap: 'var(--space-2)' }}>
                  <input
                    className="input"
                    type="text"
                    value={importPath}
                    onChange={(e) => setImportPath(e.target.value)}
                    placeholder="点击右侧按钮选择文件夹..."
                    readOnly
                    style={{ flex: 1 }}
                  />
                  <button className="btn" onClick={handleSelectImportDir}>选择</button>
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">目标子目录（可选）</label>
                <input
                  className="input"
                  type="text"
                  value={importTarget}
                  onChange={(e) => setImportTarget(e.target.value)}
                  placeholder="如 Reasoning / Experience / Memory，留空则导入根目录"
                />
                <p className="form-hint">导入的文件会复制到 Wiki 根目录下的指定子目录中</p>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-ghost" onClick={() => setImportModal(false)}>取消</button>
              <button className="btn btn-primary" onClick={handleImportObsidian} disabled={!importPath}>
                导入
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className="toast-container">
          <div className={`toast toast-${toast.type}`}>
            <span>{toast.message}</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default WikiManager;
