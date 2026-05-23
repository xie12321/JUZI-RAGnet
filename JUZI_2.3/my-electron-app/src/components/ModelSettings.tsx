import React, { useState, useEffect, useCallback, useMemo } from 'react';

interface CloudModel {
  id: string;
  name: string;
  type: 'openai';
  purpose: 'chat' | 'embedding';
  modelName: string;
  apiBase: string;
  apiKey: string;
  temperature?: number;
}

interface StoredConfig {
  cloudModels?: CloudModel[];
  currentChatModelId?: string;
  currentEmbeddingModelId?: string;
  ollamaBaseUrl?: string;
}

const STORAGE_KEY = 'cognitive_enhancer_models';

const DEFAULT_CLOUD_MODELS: CloudModel[] = [
  {
    id: 'openai-gpt35',
    name: 'OpenAI GPT-3.5 Turbo',
    type: 'openai',
    purpose: 'chat',
    modelName: 'gpt-3.5-turbo',
    apiBase: 'https://api.openai.com/v1',
    apiKey: '',
    temperature: 0.7,
  },
  {
    id: 'openai-embedding',
    name: 'OpenAI Embedding',
    type: 'openai',
    purpose: 'embedding',
    modelName: 'text-embedding-ada-002',
    apiBase: 'https://api.openai.com/v1',
    apiKey: '',
  },
];

function loadStoredConfig(): StoredConfig | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    // ignore
  }
  return null;
}

function saveStoredConfig(config: StoredConfig) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
}

const ModelSettings: React.FC = () => {
  const initialConfig = useMemo(() => loadStoredConfig(), []);

  const [cloudModels, setCloudModels] = useState<CloudModel[]>(
    initialConfig?.cloudModels || DEFAULT_CLOUD_MODELS
  );
  const [currentChatModelId, setCurrentChatModelId] = useState<string>(
    initialConfig?.currentChatModelId || ''
  );
  const [currentEmbeddingModelId, setCurrentEmbeddingModelId] = useState<string>(
    initialConfig?.currentEmbeddingModelId || ''
  );
  const [ollamaBaseUrl, setOllamaBaseUrl] = useState<string>(
    initialConfig?.ollamaBaseUrl || 'http://localhost:11434'
  );

  const [ollamaChatModels, setOllamaChatModels] = useState<{ name: string; size: string }[]>([]);
  const [ollamaEmbeddingModels, setOllamaEmbeddingModels] = useState<{ name: string; size: string }[]>([]);
  const [loadingOllama, setLoadingOllama] = useState(false);
  const [showCloudForm, setShowCloudForm] = useState(false);
  const [editingCloudModel, setEditingCloudModel] = useState<CloudModel | null>(null);
  const [showChatModels, setShowChatModels] = useState(true);
  const [showEmbeddingModels, setShowEmbeddingModels] = useState(true);
  const [formError, setFormError] = useState<string | null>(null);

  // Load Ollama models
  useEffect(() => {
    let cancelled = false;
    setLoadingOllama(true);
    window.electronAPI
      .getOllamaModels()
      .then((res) => {
        if (cancelled) return;
        setOllamaChatModels(res.chatModels);
        setOllamaEmbeddingModels(res.embeddingModels);
        setCurrentChatModelId((prev) => {
          if (!prev && res.chatModels.length > 0) return res.chatModels[0].name;
          return prev;
        });
        setCurrentEmbeddingModelId((prev) => {
          if (!prev && res.embeddingModels.length > 0) return res.embeddingModels[0].name;
          return prev;
        });
      })
      .catch(() => {
        if (!cancelled) {
          setOllamaChatModels([]);
          setOllamaEmbeddingModels([]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingOllama(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Persist config
  useEffect(() => {
    saveStoredConfig({
      cloudModels,
      currentChatModelId,
      currentEmbeddingModelId,
      ollamaBaseUrl,
    });
  }, [cloudModels, currentChatModelId, currentEmbeddingModelId, ollamaBaseUrl]);

  // 辅助函数：解析当前嵌入模型的实际名称（用于同步到后端）
  const resolveEmbedModelName = useCallback((embedId: string) => {
    const cloudEmbed = cloudModels.find(m => m.id === embedId && m.purpose === 'embedding');
    if (cloudEmbed) return cloudEmbed.modelName;
    return embedId; // 本地 Ollama 模型 ID 即为模型名
  }, [cloudModels]);

  // 同步对话模型 + 嵌入模型到增强层
  const syncModelToBackend = useCallback((chatModelId: string, embedModelId: string) => {
    let modelConfig: any = null;

    const cloudModel = cloudModels.find(m => m.id === chatModelId && m.purpose === 'chat');
    if (cloudModel) {
      modelConfig = {
        type: 'openai',
        model: cloudModel.modelName,
        api_base: cloudModel.apiBase,
        api_key: cloudModel.apiKey,
        temperature: cloudModel.temperature ?? 0.7,
      };
    } else {
      const localModel = ollamaChatModels.find(m => m.name === chatModelId);
      if (localModel) {
        const baseUrl = ollamaBaseUrl || 'http://localhost:11434';
        const apiBase = baseUrl.endsWith('/v1') ? baseUrl : baseUrl + '/v1';
        modelConfig = {
          type: 'ollama',
          model: chatModelId,
          api_base: apiBase,
          api_key: 'ollama',
          temperature: 0.7,
        };
      }
    }

    if (modelConfig) {
      modelConfig.embed_model = resolveEmbedModelName(embedModelId);
      fetch('http://localhost:8000/v1/cognitive/set_model', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(modelConfig),
      }).catch(err => console.error('同步模型配置失败', err));
    }
  }, [cloudModels, ollamaChatModels, ollamaBaseUrl, resolveEmbedModelName]);

  // 切换对话模型
  const handleSelectChatModel = useCallback((id: string) => {
    setCurrentChatModelId(id);
    syncModelToBackend(id, currentEmbeddingModelId);
  }, [syncModelToBackend, currentEmbeddingModelId]);

  // 切换嵌入模型
  const handleSelectEmbeddingModel = useCallback((id: string) => {
    setCurrentEmbeddingModelId(id);
    syncModelToBackend(currentChatModelId, id);
  }, [syncModelToBackend, currentChatModelId]);

  // 云端模型的添加、编辑、删除、保存函数保持不变
  const handleAddCloudModel = useCallback(() => {
    setFormError(null);
    setEditingCloudModel({
      id: `cloud-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      name: '',
      type: 'openai',
      purpose: 'chat',
      modelName: '',
      apiBase: 'https://api.openai.com/v1',
      apiKey: '',
      temperature: 0.7,
    });
    setShowCloudForm(true);
  }, []);

  const handleEditCloudModel = useCallback((model: CloudModel) => {
    setFormError(null);
    setEditingCloudModel({ ...model });
    setShowCloudForm(true);
  }, []);

  const handleDeleteCloudModel = useCallback(
    (id: string) => {
      if (!window.confirm('确定删除此云端模型配置吗？')) return;
      setCloudModels((prev) => prev.filter((m) => m.id !== id));
      if (currentChatModelId === id) setCurrentChatModelId('');
      if (currentEmbeddingModelId === id) setCurrentEmbeddingModelId('');
    },
    [currentChatModelId, currentEmbeddingModelId]
  );

  const handleSaveCloudModel = useCallback(
    (model: CloudModel) => {
      if (!model.name.trim() || !model.modelName.trim() || !model.apiBase.trim() || !model.apiKey.trim()) {
        setFormError('请填写所有必填字段');
        return;
      }
      const existingIds = cloudModels.filter((m) => m.id !== model.id).map((m) => m.id);
      if (existingIds.includes(model.id)) {
        setFormError('模型 ID 冲突，请重试');
        return;
      }
      setFormError(null);
      setCloudModels((prev) => {
        const exists = prev.find((m) => m.id === model.id);
        if (exists) return prev.map((m) => (m.id === model.id ? model : m));
        return [...prev, model];
      });
      setShowCloudForm(false);
      setEditingCloudModel(null);
    },
    [cloudModels]
  );

  const currentChatLabel = useMemo(() => {
    const cloud = cloudModels.find((m) => m.id === currentChatModelId && m.purpose === 'chat');
    if (cloud) return cloud.name;
    const local = ollamaChatModels.find((m) => m.name === currentChatModelId);
    if (local) return local.name;
    return '未选择';
  }, [cloudModels, currentChatModelId, ollamaChatModels]);

  const currentEmbeddingLabel = useMemo(() => {
    const cloud = cloudModels.find((m) => m.id === currentEmbeddingModelId && m.purpose === 'embedding');
    if (cloud) return cloud.name;
    const local = ollamaEmbeddingModels.find((m) => m.name === currentEmbeddingModelId);
    if (local) return local.name;
    return '未选择';
  }, [cloudModels, currentEmbeddingModelId, ollamaEmbeddingModels]);

  // UI 部分完全保留原样，只修改了事件处理函数
  return (
    <div
      style={{
        height: '100%',
        overflowY: 'auto',
        padding: 'var(--space-6)',
      }}
    >
      <div style={{ maxWidth: 800, margin: '0 auto' }}>
        <h2 style={{ fontSize: '20px', fontWeight: 700, marginBottom: 'var(--space-6)' }}>模型设置</h2>

        {/* Status Card */}
        <div
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-lg)',
            padding: 'var(--space-5)',
            marginBottom: 'var(--space-5)',
          }}
        >
          <div className="flex-col" style={{ gap: 'var(--space-3)' }}>
            <div className="flex items-center justify-between">
              <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>当前对话模型</span>
              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                {currentChatLabel}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>当前嵌入模型</span>
              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                {currentEmbeddingLabel}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Ollama 服务地址</span>
              <span
                style={{
                  fontSize: '13px',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--text-primary)',
                }}
              >
                {ollamaBaseUrl}
              </span>
            </div>
          </div>
        </div>

        {/* Local Chat Models */}
        <section style={{ marginBottom: 'var(--space-6)' }}>
          <button
            onClick={() => setShowChatModels((v) => !v)}
            className="flex items-center justify-between"
            style={{
              width: '100%',
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              padding: 'var(--space-3) 0',
              fontSize: '15px',
              fontWeight: 600,
              color: 'var(--text-primary)',
              fontFamily: 'inherit',
            }}
          >
            <span className="flex items-center" style={{ gap: 'var(--space-2)' }}>
              <span style={{ fontSize: '18px' }}>📦</span>
              本地语言模型 (Ollama)
              {loadingOllama && <span className="badge" style={{ animation: 'pulse 2s ease infinite' }}>检测中</span>}
            </span>
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{
                transform: showChatModels ? 'rotate(180deg)' : 'rotate(0deg)',
                transition: 'transform var(--transition-fast)',
                color: 'var(--text-muted)',
              }}
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>

          {showChatModels && (
            <div
              style={{
                background: 'var(--bg-surface)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-lg)',
                padding: 'var(--space-4)',
              }}
            >
              {ollamaChatModels.length === 0 ? (
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', textAlign: 'center', padding: 'var(--space-4)' }}>
                  未检测到 Ollama 模型，请确保 Ollama 已安装并运行。
                </p>
              ) : (
                <div className="flex-col" style={{ gap: 'var(--space-2)', maxHeight: 300, overflowY: 'auto' }}>
                  {ollamaChatModels.map((model) => (
                    <label
                      key={model.name}
                      className="flex items-center"
                      style={{
                        gap: 'var(--space-3)',
                        padding: 'var(--space-3)',
                        borderRadius: 'var(--radius-md)',
                        cursor: 'pointer',
                        transition: 'background var(--transition-fast)',
                        background:
                          currentChatModelId === model.name ? 'var(--bg-primary-light)' : 'transparent',
                      }}
                      onMouseEnter={(e) => {
                        if (currentChatModelId !== model.name) {
                          e.currentTarget.style.background = 'var(--bg-surface-hover)';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (currentChatModelId !== model.name) {
                          e.currentTarget.style.background = 'transparent';
                        }
                      }}
                    >
                      <input
                        type="radio"
                        name="chatModel"
                        checked={currentChatModelId === model.name}
                        onChange={() => handleSelectChatModel(model.name)}
                      />
                      <span style={{ fontSize: '13px', fontWeight: 500, flex: 1 }}>{model.name}</span>
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{model.size}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>

        {/* Local Embedding Models */}
        <section style={{ marginBottom: 'var(--space-6)' }}>
          <button
            onClick={() => setShowEmbeddingModels((v) => !v)}
            className="flex items-center justify-between"
            style={{
              width: '100%',
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              padding: 'var(--space-3) 0',
              fontSize: '15px',
              fontWeight: 600,
              color: 'var(--text-primary)',
              fontFamily: 'inherit',
            }}
          >
            <span className="flex items-center" style={{ gap: 'var(--space-2)' }}>
              <span style={{ fontSize: '18px' }}>🔍</span>
              本地嵌入模型 (Ollama)
            </span>
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{
                transform: showEmbeddingModels ? 'rotate(180deg)' : 'rotate(0deg)',
                transition: 'transform var(--transition-fast)',
                color: 'var(--text-muted)',
              }}
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>

          {showEmbeddingModels && (
            <div
              style={{
                background: 'var(--bg-surface)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-lg)',
                padding: 'var(--space-4)',
              }}
            >
              {ollamaEmbeddingModels.length === 0 ? (
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', textAlign: 'center', padding: 'var(--space-4)' }}>
                  未检测到嵌入模型，建议安装 nomic-embed-text 等。
                </p>
              ) : (
                <div className="flex-col" style={{ gap: 'var(--space-2)', maxHeight: 300, overflowY: 'auto' }}>
                  {ollamaEmbeddingModels.map((model) => (
                    <label
                      key={model.name}
                      className="flex items-center"
                      style={{
                        gap: 'var(--space-3)',
                        padding: 'var(--space-3)',
                        borderRadius: 'var(--radius-md)',
                        cursor: 'pointer',
                        transition: 'background var(--transition-fast)',
                        background:
                          currentEmbeddingModelId === model.name
                            ? 'var(--bg-primary-light)'
                            : 'transparent',
                      }}
                      onMouseEnter={(e) => {
                        if (currentEmbeddingModelId !== model.name) {
                          e.currentTarget.style.background = 'var(--bg-surface-hover)';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (currentEmbeddingModelId !== model.name) {
                          e.currentTarget.style.background = 'transparent';
                        }
                      }}
                    >
                      <input
                        type="radio"
                        name="embeddingModel"
                        checked={currentEmbeddingModelId === model.name}
                        onChange={() => handleSelectEmbeddingModel(model.name)}
                      />
                      <span style={{ fontSize: '13px', fontWeight: 500, flex: 1 }}>{model.name}</span>
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{model.size}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>

        {/* Ollama Base URL */}
        <section style={{ marginBottom: 'var(--space-6)' }}>
          <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: 'var(--space-3)' }}>⚙️ 本地 Ollama 服务地址</h3>
          <div
            style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-lg)',
              padding: 'var(--space-4)',
            }}
          >
            <input
              className="input"
              type="text"
              value={ollamaBaseUrl}
              onChange={(e) => setOllamaBaseUrl(e.target.value)}
              placeholder="http://localhost:11434"
            />
            <p className="form-hint">修改后需重新加载模型列表</p>
          </div>
        </section>

        {/* Cloud Models */}
        <section>
          <div className="flex items-center justify-between" style={{ marginBottom: 'var(--space-4)' }}>
            <h3 style={{ fontSize: '15px', fontWeight: 600 }}>☁️ 云端模型 (OpenAI 兼容)</h3>
            <button className="btn btn-sm btn-primary" onClick={handleAddCloudModel}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              添加
            </button>
          </div>

          <div
            style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-lg)',
              overflow: 'hidden',
            }}
          >
            <table className="data-table">
              <thead>
                <tr>
                  <th>名称</th>
                  <th>模型名</th>
                  <th>用途</th>
                  <th style={{ width: 160 }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {cloudModels.map((model) => (
                  <tr key={model.id}>
                    <td style={{ fontWeight: 500 }}>{model.name}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>{model.modelName}</td>
                    <td>
                      <span
                        className="badge"
                        style={{
                          background: model.purpose === 'chat' ? 'var(--bg-primary-light)' : '#f3e8ff',
                          color: model.purpose === 'chat' ? 'var(--bg-primary)' : '#7c3aed',
                        }}
                      >
                        {model.purpose === 'chat' ? '对话' : '嵌入'}
                      </span>
                    </td>
                    <td>
                      <div className="flex" style={{ gap: 'var(--space-2)' }}>
                        <button
                          className="btn btn-sm"
                          onClick={() => {
                            if (model.purpose === 'chat') handleSelectChatModel(model.id);
                            else handleSelectEmbeddingModel(model.id);
                          }}
                        >
                          使用
                        </button>
                        <button className="btn btn-sm btn-ghost" onClick={() => handleEditCloudModel(model)}>
                          编辑
                        </button>
                        <button
                          className="btn btn-sm btn-ghost"
                          style={{ color: 'var(--text-danger)' }}
                          onClick={() => handleDeleteCloudModel(model.id)}
                        >
                          删除
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {cloudModels.length === 0 && (
                  <tr>
                    <td colSpan={4} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 'var(--space-6)' }}>
                      暂无云端模型配置
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* Cloud Model Form Modal */}
        {showCloudForm && editingCloudModel && (
          <CloudModelForm
            model={editingCloudModel}
            error={formError}
            onSave={handleSaveCloudModel}
            onCancel={() => {
              setShowCloudForm(false);
              setEditingCloudModel(null);
              setFormError(null);
            }}
          />
        )}
      </div>
    </div>
  );
};

const CloudModelForm: React.FC<{
  model: CloudModel;
  error: string | null;
  onSave: (model: CloudModel) => void;
  onCancel: () => void;
}> = ({ model, error, onSave, onCancel }) => {
  const [form, setForm] = useState<CloudModel>(model);

  const update = useCallback(<K extends keyof CloudModel>(key: K, value: CloudModel[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  }, []);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      onSave(form);
    },
    [form, onSave]
  );

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 520 }}>
        <div className="modal-header">
          <h3 style={{ fontSize: '16px', fontWeight: 600 }}>
            {model.name ? '编辑云端模型' : '添加云端模型'}
          </h3>
          <button className="btn btn-ghost btn-sm" onClick={onCancel}>
            ✕
          </button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && (
              <div
                style={{
                  background: '#fef2f2',
                  border: '1px solid #fecaca',
                  borderRadius: 'var(--radius-md)',
                  padding: 'var(--space-3)',
                  marginBottom: 'var(--space-4)',
                  color: 'var(--text-danger)',
                  fontSize: '13px',
                }}
              >
                {error}
              </div>
            )}
            <div className="form-group">
              <label className="form-label">显示名称 *</label>
              <input
                className="input"
                type="text"
                value={form.name}
                onChange={(e) => update('name', e.target.value)}
                required
                placeholder="例如：GPT-4"
              />
            </div>
            <div className="form-group">
              <label className="form-label">用途</label>
              <select
                className="input"
                value={form.purpose}
                onChange={(e) => update('purpose', e.target.value as 'chat' | 'embedding')}
              >
                <option value="chat">对话模型</option>
                <option value="embedding">嵌入模型</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">模型名称 *</label>
              <input
                className="input"
                type="text"
                value={form.modelName}
                onChange={(e) => update('modelName', e.target.value)}
                required
                placeholder="例如 gpt-4 或 text-embedding-ada-002"
              />
              <p className="form-hint">API 调用时使用的模型标识符</p>
            </div>
            <div className="form-group">
              <label className="form-label">API Base URL *</label>
              <input
                className="input"
                type="text"
                value={form.apiBase}
                onChange={(e) => update('apiBase', e.target.value)}
                required
                placeholder="https://api.openai.com/v1"
              />
            </div>
            <div className="form-group">
              <label className="form-label">API Key *</label>
              <input
                className="input"
                type="password"
                value={form.apiKey}
                onChange={(e) => update('apiKey', e.target.value)}
                required
                placeholder="sk-..."
              />
              <p className="form-hint" style={{ color: 'var(--text-danger)' }}>
                ⚠️ 敏感信息，请确保环境安全
              </p>
            </div>
            {form.purpose === 'chat' && (
              <div className="form-group">
                <label className="form-label">Temperature</label>
                <input
                  className="input"
                  type="number"
                  step="0.1"
                  min="0"
                  max="2"
                  value={form.temperature ?? 0.7}
                  onChange={(e) => update('temperature', parseFloat(e.target.value))}
                />
                <p className="form-hint">取值范围 0-2，数值越高输出越随机</p>
              </div>
            )}
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-ghost" onClick={onCancel}>
              取消
            </button>
            <button type="submit" className="btn btn-primary">
              保存
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ModelSettings;