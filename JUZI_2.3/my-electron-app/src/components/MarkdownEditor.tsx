import React, { useState, useEffect, useCallback } from 'react';
import MDEditor from '@uiw/react-md-editor';

interface MarkdownEditorProps {
  filePath: string | null;
  onSave?: () => void;
}

const MarkdownEditor: React.FC<MarkdownEditorProps> = ({ filePath, onSave }) => {
  const [content, setContent] = useState('');
  const [saving, setSaving] = useState(false);
  const [originalContent, setOriginalContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isDirty = content !== originalContent;

  useEffect(() => {
    if (!filePath) {
      setContent('');
      setOriginalContent('');
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    const load = async () => {
      try {
        const text = await window.electronAPI.readFile(filePath);
        setContent(text);
        setOriginalContent(text);
      } catch (err: any) {
        setError(err.message || '无法读取文件');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [filePath]);

  const handleSave = useCallback(async () => {
    if (!filePath || !isDirty) return;
    setSaving(true);
    try {
      await window.electronAPI.writeFile(filePath, content);
      setOriginalContent(content);
      onSave?.();
    } catch (err: any) {
      setError(err.message || '保存失败');
    } finally {
      setSaving(false);
    }
  }, [filePath, content, isDirty, onSave]);

  // Keyboard shortcut: Ctrl+S
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        handleSave();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [handleSave]);

  if (!filePath) {
    return (
      <div
        style={{
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-muted)',
          fontSize: '14px',
        }}
      >
        <div style={{ textAlign: 'center' }}>
          <div
            style={{
              width: 48,
              height: 48,
              borderRadius: 'var(--radius-lg)',
              background: 'var(--bg-inset)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto var(--space-4)',
            }}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
          </div>
          <p>从左侧选择文件开始编辑</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div
        style={{
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-muted)',
          fontSize: '14px',
        }}
      >
        加载中...
      </div>
    );
  }

  return (
    <div className="flex-col" style={{ height: '100%' }}>
      {/* Header */}
      <div
        className="flex items-center justify-between"
        style={{
          padding: 'var(--space-3) var(--space-4)',
          borderBottom: '1px solid var(--border-color)',
          background: 'var(--bg-surface)',
          flexShrink: 0,
        }}
      >
        <div className="flex items-center" style={{ gap: 'var(--space-3)', minWidth: 0 }}>
          <span
            style={{
              fontSize: '12px',
              color: 'var(--text-muted)',
              fontFamily: 'var(--font-mono)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
            title={filePath}
          >
            {filePath}
          </span>
          {isDirty && (
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: 'var(--bg-warning)',
                flexShrink: 0,
              }}
              title="有未保存的更改"
            />
          )}
        </div>

        <div className="flex items-center" style={{ gap: 'var(--space-3)' }}>
          {error && (
            <span style={{ fontSize: '12px', color: 'var(--text-danger)' }}>{error}</span>
          )}
          <button
            className="btn btn-sm btn-primary"
            onClick={handleSave}
            disabled={saving || !isDirty}
          >
            {saving ? (
              <span className="flex items-center" style={{ gap: 6 }}>
                <span style={{ width: 12, height: 12, border: '2px solid currentColor', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
                保存中
              </span>
            ) : (
              <span className="flex items-center" style={{ gap: 6 }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
                  <polyline points="17 21 17 13 7 13 7 21" />
                  <polyline points="7 3 7 8 15 8" />
                </svg>
                保存
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Editor */}
      <div className="flex-1" style={{ overflow: 'hidden' }}>
        <MDEditor
          value={content}
          onChange={(val) => {
            setContent(val || '');
            setError(null);
          }}
          height="100%"
          visibleDragbar={false}
          hideToolbar={false}
          textareaProps={{
            placeholder: '在此输入 Markdown 内容...',
            style: { fontFamily: 'var(--font-mono)' },
          }}
        />
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default MarkdownEditor;
