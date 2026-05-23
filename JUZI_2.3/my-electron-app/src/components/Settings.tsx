import React, { useState, useEffect } from 'react';

interface AppSettings {
  autoLaunch: boolean;
  minimizeToTray: boolean;
  showThinkingProcess: boolean;
  autoSaveWiki: boolean;
  chatFontSize: 'small' | 'medium' | 'large';
}

const STORAGE_KEY = 'app_general_settings';

const DEFAULT_SETTINGS: AppSettings = {
  autoLaunch: false,
  minimizeToTray: true,
  showThinkingProcess: true,
  autoSaveWiki: false,
  chatFontSize: 'medium',
};

const loadSettings = (): AppSettings => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) };
    }
  } catch {
    // ignore parse errors
  }
  return DEFAULT_SETTINGS;
};

const saveSettings = (settings: AppSettings) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
};

const Settings: React.FC = () => {
  const [settings, setSettings] = useState<AppSettings>(loadSettings);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saved'>('idle');

  useEffect(() => {
    saveSettings(settings);
    setSaveStatus('saved');
    const timer = setTimeout(() => setSaveStatus('idle'), 1500);
    return () => clearTimeout(timer);
  }, [settings]);

  const update = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  const handleClearCache = () => {
    if (window.confirm('确定清空所有本地数据吗？包括对话历史、模型配置和应用设置。此操作不可恢复。')) {
      localStorage.clear();
      window.location.reload();
    }
  };

  return (
    <div
      style={{
        height: '100%',
        overflowY: 'auto',
        padding: 'var(--space-6)',
      }}
    >
      <div style={{ maxWidth: 640, margin: '0 auto' }}>
        <div className="flex items-center justify-between" style={{ marginBottom: 'var(--space-6)' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 700 }}>通用设置</h2>
          {saveStatus === 'saved' && (
            <span className="badge badge-primary">已自动保存</span>
          )}
        </div>

        <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
          <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: 'var(--space-4)', color: 'var(--text-secondary)' }}>
            应用行为
          </h3>

          <div className="flex-col" style={{ gap: 'var(--space-4)' }}>
            <label className="flex items-center justify-between" style={{ cursor: 'pointer' }}>
              <div>
                <div style={{ fontSize: '14px', fontWeight: 500 }}>开机自动启动</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: 2 }}>
                  登录系统时自动启动应用
                </div>
              </div>
              <Toggle checked={settings.autoLaunch} onChange={(v) => update('autoLaunch', v)} />
            </label>

            <label className="flex items-center justify-between" style={{ cursor: 'pointer' }}>
              <div>
                <div style={{ fontSize: '14px', fontWeight: 500 }}>最小化到托盘</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: 2 }}>
                  关闭窗口时最小化到系统托盘而不是退出
                </div>
              </div>
              <Toggle checked={settings.minimizeToTray} onChange={(v) => update('minimizeToTray', v)} />
            </label>
          </div>
        </div>

        <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
          <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: 'var(--space-4)', color: 'var(--text-secondary)' }}>
            对话与 Wiki
          </h3>

          <div className="flex-col" style={{ gap: 'var(--space-4)' }}>
            <label className="flex items-center justify-between" style={{ cursor: 'pointer' }}>
              <div>
                <div style={{ fontSize: '14px', fontWeight: 500 }}>显示思考过程</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: 2 }}>
                  在 AI 回复前展示推理步骤
                </div>
              </div>
              <Toggle checked={settings.showThinkingProcess} onChange={(v) => update('showThinkingProcess', v)} />
            </label>

            <label className="flex items-center justify-between" style={{ cursor: 'pointer' }}>
              <div>
                <div style={{ fontSize: '14px', fontWeight: 500 }}>自动保存 Wiki 编辑</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: 2 }}>
                  离开编辑器时自动保存更改
                </div>
              </div>
              <Toggle checked={settings.autoSaveWiki} onChange={(v) => update('autoSaveWiki', v)} />
            </label>

            <div>
              <div style={{ fontSize: '14px', fontWeight: 500, marginBottom: 'var(--space-2)' }}>对话字体大小</div>
              <div className="flex" style={{ gap: 'var(--space-2)' }}>
                {(['small', 'medium', 'large'] as const).map((size) => (
                  <button
                    key={size}
                    onClick={() => update('chatFontSize', size)}
                    className="btn"
                    style={{
                      flex: 1,
                      background: settings.chatFontSize === size ? 'var(--bg-primary-light)' : undefined,
                      color: settings.chatFontSize === size ? 'var(--bg-primary)' : undefined,
                      borderColor: settings.chatFontSize === size ? 'var(--bg-primary)' : undefined,
                    }}
                  >
                    {size === 'small' ? '小' : size === 'medium' ? '中' : '大'}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="card" style={{ borderColor: 'var(--bg-danger)', background: '#fef2f2' }}>
          <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: 'var(--space-4)', color: 'var(--text-danger)' }}>
            危险操作
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: 'var(--space-4)' }}>
            清空所有本地缓存数据，包括对话历史、模型配置和通用设置。此操作不可撤销。
          </p>
          <button className="btn btn-danger" onClick={handleClearCache}>
            清空所有数据
          </button>
        </div>
      </div>
    </div>
  );
};

const Toggle: React.FC<{ checked: boolean; onChange: (v: boolean) => void }> = ({ checked, onChange }) => {
  return (
    <button
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      style={{
        width: 40,
        height: 22,
        borderRadius: 11,
        border: 'none',
        background: checked ? 'var(--bg-primary)' : 'var(--border-color-strong)',
        cursor: 'pointer',
        position: 'relative',
        transition: 'background var(--transition-fast)',
        padding: 0,
      }}
    >
      <span
        style={{
          display: 'block',
          width: 18,
          height: 18,
          borderRadius: '50%',
          background: '#fff',
          position: 'absolute',
          top: 2,
          left: checked ? 20 : 2,
          transition: 'left var(--transition-fast)',
          boxShadow: '0 1px 3px rgba(0,0,0,0.15)',
        }}
      />
    </button>
  );
};

export default Settings;
