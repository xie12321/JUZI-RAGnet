import React, { useState } from 'react';
import Chat from './components/Chat';
import WikiManager from './components/WikiManager';
import ModelSettings from './components/ModelSettings';
import Settings from './components/Settings';

type TabId = 'chat' | 'wiki' | 'settings' | 'model';

interface NavItem {
  id: TabId;
  label: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  {
    id: 'chat',
    label: '对话',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    ),
  },
  {
    id: 'wiki',
    label: 'Wiki 管理',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <polyline points="10 9 9 9 8 9" />
      </svg>
    ),
  },
  {
    id: 'model',
    label: '模型设置',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
        <line x1="8" y1="21" x2="16" y2="21" />
        <line x1="12" y1="17" x2="12" y2="21" />
      </svg>
    ),
  },
  {
    id: 'settings',
    label: '设置',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
      </svg>
    ),
  },
];

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('chat');

  return (
    <div className="flex" style={{ height: '100vh', width: '100vw', overflow: 'hidden' }}>
      {/* Sidebar */}
      <aside
        style={{
          width: 'var(--sidebar-width)',
          minWidth: 'var(--sidebar-width)',
          background: 'var(--bg-surface)',
          borderRight: '1px solid var(--border-color)',
          display: 'flex',
          flexDirection: 'column',
          padding: 'var(--space-4)',
        }}
      >
        {/* App Title */}
        <div style={{ marginBottom: 'var(--space-6)', paddingLeft: 'var(--space-2)' }}>
          <h1
            style={{
              fontSize: '20px',
              fontWeight: 700,
              color: 'var(--text-primary)',
              letterSpacing: '-0.02em',
            }}
          >
            JUZI
          </h1>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: 2 }}>
            模型增强助手
          </p>
        </div>

        {/* Navigation */}
        <nav className="flex-col" style={{ gap: 'var(--space-1)', flex: 1 }}>
          {NAV_ITEMS.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-3)',
                  width: '100%',
                  padding: '10px var(--space-3)',
                  borderRadius: 'var(--radius-md)',
                  border: 'none',
                  background: isActive ? 'var(--bg-primary-light)' : 'transparent',
                  color: isActive ? 'var(--bg-primary)' : 'var(--text-secondary)',
                  fontSize: '14px',
                  fontWeight: isActive ? 600 : 500,
                  cursor: 'pointer',
                  transition: 'all var(--transition-fast)',
                  textAlign: 'left',
                  fontFamily: 'inherit',
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = 'var(--bg-surface-hover)';
                    e.currentTarget.style.color = 'var(--text-primary)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.color = 'var(--text-secondary)';
                  }
                }}
              >
                {item.icon}
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* Footer */}
        <div style={{ marginTop: 'auto', paddingTop: 'var(--space-4)', borderTop: '1px solid var(--border-color)' }}>
          <p style={{ fontSize: '11px', color: 'var(--text-muted)', paddingLeft: 'var(--space-2)' }}>
            v1.0.0
          </p>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1" style={{ background: 'var(--bg-base)', overflow: 'hidden' }}>
        {activeTab === 'chat' && <Chat />}
        {activeTab === 'wiki' && <WikiManager />}
        {activeTab === 'settings' && <Settings />}
        {activeTab === 'model' && <ModelSettings />}
      </main>
    </div>
  );
};

export default App;