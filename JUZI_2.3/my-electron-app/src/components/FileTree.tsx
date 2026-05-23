import React, { useState, useEffect, useRef, useCallback } from 'react';

interface WikiNode {
  name: string;
  path: string;
  relativePath: string;
  type: 'file' | 'directory';
  children?: WikiNode[];
}

interface FileTreeProps {
  onSelectFile: (path: string) => void;
  onRefresh?: () => void;
  selectedFile?: string | null;
}

interface ContextMenuState {
  visible: boolean;
  x: number;
  y: number;
  node: WikiNode | null;
}

function getFileIcon(name: string, isExpanded: boolean): string {
  if (name.endsWith('.md')) return '📄';
  return isExpanded ? '📂' : '📁';
}

const FileTree: React.FC<FileTreeProps> = ({ onSelectFile, onRefresh, selectedFile }) => {
  const [tree, setTree] = useState<WikiNode[]>([]);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [contextMenu, setContextMenu] = useState<ContextMenuState>({ visible: false, x: 0, y: 0, node: null });
  const [loading, setLoading] = useState(false);
  const [renameNode, setRenameNode] = useState<WikiNode | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);
  const contextMenuRef = useRef<HTMLDivElement>(null);

  const loadTree = useCallback(async () => {
    setLoading(true);
    try {
      const data = await window.electronAPI.getWikiTree();
      setTree(data);
      // Default expand root directories only on first load
      setExpanded((prev) => {
        if (prev.size > 0) return prev;
        const rootDirs = new Set<string>();
        data.forEach((node) => {
          if (node.type === 'directory') rootDirs.add(node.path);
        });
        return rootDirs;
      });
    } catch (err) {
      console.error('Failed to load file tree:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTree();
  }, [loadTree]);

  // Close context menu on outside click or scroll
  useEffect(() => {
    if (!contextMenu.visible) return;
    const handleClose = () => setContextMenu((prev) => ({ ...prev, visible: false }));
    const handleScroll = () => handleClose();
    window.addEventListener('click', handleClose);
    window.addEventListener('scroll', handleScroll, true);
    return () => {
      window.removeEventListener('click', handleClose);
      window.removeEventListener('scroll', handleScroll, true);
    };
  }, [contextMenu.visible]);

  const toggleExpand = useCallback((path: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }, []);

  const handleContextMenu = useCallback((e: React.MouseEvent, node: WikiNode) => {
    e.preventDefault();
    e.stopPropagation();
    // Calculate position within viewport bounds
    const menuWidth = 140;
    const menuHeight = 80;
    const x = Math.min(e.clientX, window.innerWidth - menuWidth - 8);
    const y = Math.min(e.clientY, window.innerHeight - menuHeight - 8);
    setContextMenu({ visible: true, x, y, node });
  }, []);

  const handleRenameStart = useCallback((node: WikiNode) => {
    setRenameNode(node);
    setRenameValue(node.name);
    setContextMenu((prev) => ({ ...prev, visible: false }));
  }, []);

  const handleRenameConfirm = useCallback(async () => {
    if (!renameNode || !renameValue.trim() || renameValue.trim() === renameNode.name) {
      setRenameNode(null);
      return;
    }
    try {
      await window.electronAPI.renameNode(renameNode.path, renameValue.trim());
      await loadTree();
      onRefresh?.();
    } catch (err: any) {
      alert(err.message || '重命名失败');
    }
    setRenameNode(null);
  }, [renameNode, renameValue, loadTree, onRefresh]);

  const handleDelete = useCallback(async () => {
    if (!contextMenu.node) return;
    const node = contextMenu.node;
    if (window.confirm(`确定删除 "${node.name}" 吗？${node.type === 'directory' ? '目录及其所有内容将被永久删除。' : ''}`)) {
      try {
        await window.electronAPI.deleteNode(node.path);
        await loadTree();
        onRefresh?.();
      } catch (err: any) {
        alert(err.message || '删除失败');
      }
    }
    setContextMenu((prev) => ({ ...prev, visible: false }));
  }, [contextMenu.node, loadTree, onRefresh]);

  const handleNodeClick = useCallback(
    (node: WikiNode) => {
      if (node.type === 'directory') {
        toggleExpand(node.path);
      } else {
        onSelectFile(node.path);
      }
    },
    [toggleExpand, onSelectFile]
  );

  const renderNode = useCallback(
    (node: WikiNode, depth: number = 0): React.ReactNode => {
      const isExpanded = expanded.has(node.path);
      const isSelected = selectedFile === node.path;
      const isRenaming = renameNode?.path === node.path;

      return (
        <div key={node.path} style={{ marginLeft: depth * 16 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '5px 8px',
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer',
              userSelect: 'none',
              transition: 'background var(--transition-fast)',
              background: isSelected ? 'var(--bg-primary-light)' : 'transparent',
              color: isSelected ? 'var(--bg-primary)' : 'var(--text-primary)',
            }}
            onClick={() => handleNodeClick(node)}
            onContextMenu={(e) => handleContextMenu(e, node)}
            onMouseEnter={(e) => {
              if (!isSelected) e.currentTarget.style.background = 'var(--bg-surface-hover)';
            }}
            onMouseLeave={(e) => {
              if (!isSelected) e.currentTarget.style.background = 'transparent';
            }}
          >
            {/* Expand/Collapse indicator for directories */}
            {node.type === 'directory' && (
              <span
                style={{
                  width: 16,
                  height: 16,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'transform var(--transition-fast)',
                  transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                  color: 'var(--text-muted)',
                  fontSize: '11px',
                }}
              >
                ▶
              </span>
            )}
            {node.type === 'file' && <span style={{ width: 16 }} />}

            {/* Icon */}
            <span style={{ fontSize: '14px', lineHeight: 1 }}>
              {getFileIcon(node.name, isExpanded)}
            </span>

            {/* Name */}
            {isRenaming ? (
              <input
                className="input"
                type="text"
                value={renameValue}
                onChange={(e) => setRenameValue(e.target.value)}
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleRenameConfirm();
                  if (e.key === 'Escape') setRenameNode(null);
                }}
                onBlur={handleRenameConfirm}
                onClick={(e) => e.stopPropagation()}
                style={{
                  padding: '2px 6px',
                  fontSize: '13px',
                  minHeight: 'auto',
                  flex: 1,
                }}
              />
            ) : (
              <span
                style={{
                  fontSize: '13px',
                  fontWeight: node.type === 'directory' ? 500 : 400,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  flex: 1,
                }}
                title={node.name}
              >
                {node.name}
              </span>
            )}
          </div>

          {/* Children */}
          {node.type === 'directory' && isExpanded && node.children && (
            <div style={{ animation: 'fadeIn 150ms ease' }}>
              {node.children.map((child) => renderNode(child, depth + 1))}
            </div>
          )}
        </div>
      );
    },
    [expanded, selectedFile, renameNode, renameValue, handleNodeClick, handleContextMenu, handleRenameConfirm]
  );

  return (
    <div ref={containerRef} style={{ height: '100%', overflow: 'auto' }}>
      {loading && tree.length === 0 && (
        <div style={{ padding: 16, textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
          加载中...
        </div>
      )}

      {!loading && tree.length === 0 && (
        <div style={{ padding: 16, textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
          暂无文件，点击「新建」创建
        </div>
      )}

      {tree.map((node) => renderNode(node))}

      {/* Context Menu */}
      {contextMenu.visible && contextMenu.node && (
        <div
          ref={contextMenuRef}
          style={{
            position: 'fixed',
            top: contextMenu.y,
            left: contextMenu.x,
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-md)',
            boxShadow: 'var(--shadow-lg)',
            zIndex: 1000,
            minWidth: 120,
            overflow: 'hidden',
            animation: 'fadeIn 100ms ease',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <div
            style={{
              padding: '8px 14px',
              cursor: 'pointer',
              fontSize: '13px',
              color: 'var(--text-primary)',
              transition: 'background var(--transition-fast)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--bg-surface-hover)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
            }}
            onClick={() => handleRenameStart(contextMenu.node!)}
          >
            重命名
          </div>
          <div
            style={{
              padding: '8px 14px',
              cursor: 'pointer',
              fontSize: '13px',
              color: 'var(--text-danger)',
              transition: 'background var(--transition-fast)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#fef2f2';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
            }}
            onClick={handleDelete}
          >
            删除
          </div>
        </div>
      )}
    </div>
  );
};

export default FileTree;
