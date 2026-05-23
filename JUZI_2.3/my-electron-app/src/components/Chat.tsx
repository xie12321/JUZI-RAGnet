import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: number;
}

interface ThinkingStage {
  stage: 'think' | 'connect' | 'reflect';
  label: string;
  content: string;
}

const STORAGE_KEY = 'chat_history';

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function loadMessages(): Message[] {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed)) {
        return parsed.map((m: any) => ({
          id: m.id || generateId(),
          role: m.role,
          content: m.content,
          createdAt: m.createdAt || Date.now(),
        }));
      }
    }
  } catch {
    // ignore corrupt storage
  }
  return [];
}

function saveMessages(messages: Message[]) {
  try {
    const storable = messages.map(({ id, role, content, createdAt }) => ({ id, role, content, createdAt }));
    localStorage.setItem(STORAGE_KEY, JSON.stringify(storable));
  } catch {
    // storage might be full
  }
}

interface ChatModelConfig {
  type: 'openai' | 'ollama';
  modelName: string;
  apiBase?: string;
  apiKey?: string;
  temperature?: number;
  baseUrl?: string;
}

function getCurrentChatModel(): ChatModelConfig | null {
  try {
    const stored = localStorage.getItem('cognitive_enhancer_models');
    if (!stored) return null;
    const data = JSON.parse(stored);
    const cloud = data.cloudModels?.find((m: any) => m.id === data.currentChatModelId && m.purpose === 'chat');
    if (cloud) return { type: 'openai', ...cloud };
    if (data.currentChatModelId && !data.currentChatModelId.startsWith('openai-')) {
      return { type: 'ollama', modelName: data.currentChatModelId, baseUrl: data.ollamaBaseUrl || 'http://localhost:11434' };
    }
  } catch {
    // ignore
  }
  return null;
}

function getCurrentEmbedModel(): string {
  try {
    const stored = localStorage.getItem('cognitive_enhancer_models');
    if (!stored) return 'nomic-embed-text';
    const data = JSON.parse(stored);
    const cloudEmbed = data.cloudModels?.find((m: any) => m.id === data.currentEmbeddingModelId && m.purpose === 'embedding');
    if (cloudEmbed) return cloudEmbed.modelName;
    return data.currentEmbeddingModelId || 'nomic-embed-text';
  } catch {
    return 'nomic-embed-text';
  }
}

function formatTime(ts: number): string {
  const d = new Date(ts);
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}

const Chat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>(loadMessages);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [thinkingStages, setThinkingStages] = useState<ThinkingStage[]>([]);
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(true);
  const [isThinkingStreaming, setIsThinkingStreaming] = useState(false);

  // 思考池相关状态
  const [thoughtPoolContent, setThoughtPoolContent] = useState('');
  const [showThoughtPool, setShowThoughtPool] = useState(true);

  // 维护相关状态
  const [maintenanceRunning, setMaintenanceRunning] = useState(false);
  const [maintenanceProgress, setMaintenanceProgress] = useState<{
    stage: string;
    current: number;
    total: number;
    message: string;
  } | null>(null);
  const [maintenanceMode, setMaintenanceMode] = useState<'incremental' | 'full'>('incremental');
  const [executionMode, setExecutionMode] = useState<'enhanced' | 'direct'>('direct');
  const [importText, setImportText] = useState('');
  const [showImportModal, setShowImportModal] = useState(false);
  const [indexRebuilding, setIndexRebuilding] = useState(false);

  const maintenanceWsRef = useRef<WebSocket | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const currentAssistantIdRef = useRef<string | null>(null);
  const thinkingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pendingThinkingRef = useRef<{ stage: 'think' | 'connect' | 'reflect'; text: string } | null>(null);
  const thinkingStageIndexRef = useRef(0);

  // Persist messages
  useEffect(() => {
    saveMessages(messages);
  }, [messages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length]);

  // Cleanup
  useEffect(() => {
    return () => {
      stopThinkingStream();
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
      if (maintenanceWsRef.current && maintenanceWsRef.current.readyState === WebSocket.OPEN) {
        maintenanceWsRef.current.close();
      }
    };
  }, []);

  // 启动时自动同步模型配置到增强层
  useEffect(() => {
   const sync = async () => {
      const modelConfig = getCurrentChatModel();
      if (!modelConfig) return;

    let wikiRoot = '';
    try {
      wikiRoot = await window.electronAPI.getWikiRoot();
    } catch (e) {
      console.error('获取 Wiki 根路径失败', e);
    }
    
    let payload: any;
    if (modelConfig.type === 'openai') {
      payload = {
        type: 'openai',
        model: modelConfig.modelName,
        api_base: modelConfig.apiBase,
        api_key: modelConfig.apiKey,
        temperature: modelConfig.temperature ?? 0.7,
        embed_model: getCurrentEmbedModel(),
        wiki_root: wikiRoot,
      };
    } else {
      const baseUrl = modelConfig.baseUrl || 'http://localhost:11434';
      const apiBase = baseUrl.endsWith('/v1') ? baseUrl : baseUrl + '/v1';
      payload = {
        type: 'ollama',
        model: modelConfig.modelName,
        api_base: apiBase,
        api_key: 'ollama',
        temperature: 0.7,
        embed_model: getCurrentEmbedModel(),
         wiki_root: wikiRoot, 
      };
    }
    fetch('http://localhost:8000/v1/cognitive/set_model', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).catch(() => {});
  };
    sync();
  }, []);

  const stopThinkingStream = useCallback(() => {
    if (thinkingTimerRef.current) {
      clearInterval(thinkingTimerRef.current);
      thinkingTimerRef.current = null;
    }
  }, []);

  const resetThinking = useCallback(() => {
    stopThinkingStream();
    setThinkingStages([]);
    setIsThinkingStreaming(false);
    setIsThinkingExpanded(true);
    thinkingStageIndexRef.current = 0;
    pendingThinkingRef.current = null;
  }, [stopThinkingStream]);

  const startThinkingStreamRef = useRef<(stage: 'think' | 'connect' | 'reflect', fullText: string) => void>(undefined);
  startThinkingStreamRef.current = (stage, fullText) => {
    stopThinkingStream();
    setIsThinkingStreaming(true);

    const labelMap: Record<string, string> = {
      think: '初步思考',
      connect: '连接思考',
      reflect: '反思',
    };

    let index = 0;
    const stageOrder: ('think' | 'connect' | 'reflect')[] = ['think', 'connect', 'reflect'];

    thinkingTimerRef.current = setInterval(() => {
      if (index < fullText.length) {
        setThinkingStages((prev) => {
          const existing = prev.find((s) => s.stage === stage);
          if (existing) {
            return prev.map((s) => (s.stage === stage ? { ...s, content: fullText.slice(0, index + 1) } : s));
          }
          return [...prev, { stage, label: labelMap[stage], content: fullText.slice(0, index + 1) }];
        });
        index++;
      } else {
        stopThinkingStream();
        setIsThinkingStreaming(false);
        thinkingStageIndexRef.current++;
        if (pendingThinkingRef.current) {
          const next = pendingThinkingRef.current;
          pendingThinkingRef.current = null;
          const nextStage = stageOrder[thinkingStageIndexRef.current];
          if (nextStage && next.stage === nextStage) {
            startThinkingStreamRef.current?.(nextStage, next.text);
          }
        }
      }
    }, 15);
  };

  const startThinkingStream = useCallback((stage: 'think' | 'connect' | 'reflect', fullText: string) => {
    startThinkingStreamRef.current?.(stage, fullText);
  }, []);

  const sendMessage = useCallback(async () => {
    if (!input.trim() || loading) return;
    const userMsg: Message = { id: generateId(), role: 'user', content: input.trim(), createdAt: Date.now() };
    const assistantId = generateId();
    const assistantMsg: Message = { id: assistantId, role: 'assistant', content: '', createdAt: Date.now() };
    const newMessages = [...messages, userMsg, assistantMsg];
    setMessages(newMessages);
    currentAssistantIdRef.current = assistantId;
    setInput('');
    setLoading(true);
    resetThinking();
    setThoughtPoolContent('');

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    const modelConfig = getCurrentChatModel();
    const wsRequest: Record<string, any> = {
      messages: newMessages.map(({ role, content }) => ({ role, content })),
    };
    if (modelConfig?.type === 'openai') {
      wsRequest.model = modelConfig.modelName;
      wsRequest.api_base = modelConfig.apiBase;
      wsRequest.api_key = modelConfig.apiKey;
      wsRequest.temperature = modelConfig.temperature ?? 0.7;
    } else if (modelConfig?.type === 'ollama') {
      wsRequest.model = modelConfig.modelName;
      wsRequest.ollama_base_url = modelConfig.baseUrl;
    } else {
      wsRequest.model = 'qwen2.5:7b';
    }

    const ws = new WebSocket('ws://localhost:8000/ws/chat');
    wsRef.current = ws;
    ws.onopen = () => ws.send(JSON.stringify(wsRequest));
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const { type, content } = data;
        const stageOrder: ('think' | 'connect' | 'reflect')[] = ['think', 'connect', 'reflect'];
        if (type === 'think' || type === 'connect' || type === 'reflect') {
          const currentStage = stageOrder[thinkingStageIndexRef.current];
          if (currentStage && currentStage === type) {
            if (thinkingTimerRef.current === null) startThinkingStream(currentStage, content);
            else pendingThinkingRef.current = { stage: type, text: content };
          }
        } else if (type === 'reset_thinking') {
          // 重新规划时，清空上一轮思考过程的展示
          resetThinking();
        } else if (type === 'thought_pool') {
          setThoughtPoolContent(content);
        } else if (type === 'output') {
          setMessages((prev) => {
            const idx = prev.findIndex((m) => m.id === assistantId);
            if (idx === -1) return prev;
            const next = [...prev];
            next[idx] = { ...next[idx], content };
            return next;
          });
        } else if (type === 'done') {
          ws.close();
          setLoading(false);
          currentAssistantIdRef.current = null;
          stopThinkingStream();
          setIsThinkingStreaming(false);
          pendingThinkingRef.current = null;
        }
      } catch {
        // ignore
      }
    };
    ws.onerror = () => {
      setMessages((prev) => {
        const idx = prev.findIndex((m) => m.id === assistantId);
        if (idx === -1) return prev;
        const next = [...prev];
        next[idx] = { ...next[idx], content: '连接失败，请检查后端服务是否运行在 localhost:8000。' };
        return next;
      });
      setLoading(false);
      currentAssistantIdRef.current = null;
      ws.close();
    };
    ws.onclose = () => {
      setLoading(false);
      currentAssistantIdRef.current = null;
      wsRef.current = null;
    };
  }, [input, loading, messages, resetThinking, startThinkingStream, stopThinkingStream]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      sendMessage();
    }
  }, [sendMessage]);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 200) + 'px';
  }, []);

  const clearHistory = useCallback(() => {
    if (window.confirm('确定清空所有对话历史吗？此操作不可恢复。')) {
      setMessages([]);
      localStorage.removeItem(STORAGE_KEY);
    }
  }, []);

  // ---------- 维护任务通信 ----------
  const sendMaintenanceRequest = useCallback(async (action: string, extraPayload: any = {}) => {
    if (maintenanceWsRef.current && maintenanceWsRef.current.readyState === WebSocket.OPEN) {
      maintenanceWsRef.current.close();
    }
    const modelConfig = getCurrentChatModel();
    const embedModel = getCurrentEmbedModel();

    let wikiRoot = '';
    try {
      wikiRoot = await window.electronAPI.getWikiRoot();
    } catch (e) {
      console.error('获取 Wiki 根路径失败', e);
    }

    const payload: any = {
      mode: maintenanceMode,
      execution_mode: executionMode,
      model_config: modelConfig ? {
        type: modelConfig.type,
        model: modelConfig.modelName,
        api_base: modelConfig.apiBase,
        api_key: modelConfig.apiKey,
        temperature: modelConfig.temperature ?? 0.7,
      } : null,
      embed_model: embedModel,
      wiki_root: wikiRoot,
      ...extraPayload,
    };

    const ws = new WebSocket('ws://localhost:8001/ws/maintenance');
    maintenanceWsRef.current = ws;
    setMaintenanceRunning(true);
    setMaintenanceProgress(null);

    ws.onopen = () => {
      ws.send(JSON.stringify({ action, payload }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'progress') {
        setMaintenanceProgress({ stage: data.stage, current: data.current, total: data.total, message: data.message });
      } else if (data.type === 'done') {
        setMaintenanceRunning(false);
        setMaintenanceProgress(null);
        alert('任务完成！');
        ws.close();
      } else if (data.type === 'error') {
        setMaintenanceRunning(false);
        setMaintenanceProgress(null);
        alert('任务失败: ' + data.message);
        ws.close();
      }
    };

    ws.onerror = () => {
      setMaintenanceRunning(false);
      setMaintenanceProgress(null);
      alert('无法连接到维护系统');
    };
  }, [maintenanceMode, executionMode]);

  const runHealthCheck = useCallback(() => {
    sendMaintenanceRequest('run_health_check');
  }, [sendMaintenanceRequest]);

  const runPoolPrecipitation = useCallback(() => {
    sendMaintenanceRequest('precipitate_pools');
}, [sendMaintenanceRequest]);

  const runImport = useCallback(() => {
    if (!importText.trim()) {
      alert('请输入或粘贴要导入的文本');
      return;
    }
    sendMaintenanceRequest('run_import', { import_text: importText });
    setShowImportModal(false);
    setImportText('');
  }, [importText, sendMaintenanceRequest]);

  const rebuildIndex = useCallback(async () => {
  setIndexRebuilding(true);
  try {
    const res = await fetch('http://localhost:8000/v1/cognitive/rebuild_index', {
      method: 'POST',
    });
    if (res.ok) {
      alert('索引重建成功！');
    } else {
      const err = await res.json();
      alert('索引重建失败：' + (err.detail || '未知错误'));
    }
  } catch (e) {
    alert('无法连接到增强层');
  } finally {
    setIndexRebuilding(false);
  }
}, []);

  const renderThinking = useMemo(() => {
    if (thinkingStages.length === 0 && !isThinkingStreaming) return null;
    return (
      <div style={{ marginBottom: 12, animation: 'fadeIn 200ms ease' }}>
        <button onClick={() => setIsThinkingExpanded((v) => !v)} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '12px', color: 'var(--text-muted)', background: 'transparent', border: 'none', cursor: 'pointer', padding: '4px 0', fontFamily: 'inherit' }}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ transform: isThinkingExpanded ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 200ms ease' }}>
            <polyline points="9 18 15 12 9 6" />
          </svg>
          <span>思考过程</span>
          {isThinkingStreaming && <span className="badge" style={{ animation: 'pulse 2s ease infinite' }}>思考中</span>}
        </button>
        {isThinkingExpanded && (
          <div style={{ marginTop: 8, padding: '10px 14px', background: 'var(--bg-inset)', borderRadius: 'var(--radius-md)', borderLeft: '3px solid var(--border-color-strong)', fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            {thinkingStages.map((stage) => (
              <div key={stage.stage} style={{ marginBottom: 8 }}>
                <strong style={{ color: 'var(--text-primary)', fontSize: '12px' }}>{stage.label}：</strong>
                <div style={{ marginTop: 2, whiteSpace: 'pre-wrap' }}>{stage.content}</div>
              </div>
            ))}
            {isThinkingStreaming && thinkingStages.length === 0 && (
              <div style={{ color: 'var(--text-muted)' }}>正在思考<span className="dot-blink">.</span><span className="dot-blink">.</span><span className="dot-blink">.</span></div>
            )}
          </div>
        )}
      </div>
    );
  }, [thinkingStages, isThinkingStreaming, isThinkingExpanded]);

  return (
    <div style={{ height: '100%', display: 'flex', overflow: 'hidden' }}>
      {/* 左侧对话区域 */}
      <div className="flex-col" style={{ flex: 1, minWidth: 0, height: '100%', background: 'var(--bg-base)' }}>
        <style>{`
          @keyframes progressIndeterminate {
            0% { transform: translateX(-100%); }
            50% { transform: translateX(200%); }
            100% { transform: translateX(-100%); }
          }
        `}</style>

        {/* Messages Area */}
        <div className="flex-1" style={{ overflowY: 'auto', padding: 'var(--space-4)' }}>
          <div style={{ maxWidth: 800, margin: '0 auto' }}>
            {messages.length === 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', minHeight: 300, color: 'var(--text-muted)', textAlign: 'center' }}>
                <div style={{ width: 56, height: 56, borderRadius: 'var(--radius-lg)', background: 'var(--bg-primary-light)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 'var(--space-4)', color: 'var(--bg-primary)' }}>
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
                </div>
                <p style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>开始新的对话</p>
                <p style={{ fontSize: '13px' }}>输入消息与 AI 助手交流</p>
              </div>
            )}

            {messages.map((msg) => (
              <div key={msg.id} style={{ display: 'flex', flexDirection: msg.role === 'user' ? 'row-reverse' : 'row', gap: 'var(--space-3)', marginBottom: 'var(--space-4)', animation: 'fadeIn 300ms ease' }}>
                <div style={{ width: 32, height: 32, borderRadius: 'var(--radius-full)', background: msg.role === 'user' ? 'var(--bg-primary)' : 'var(--bg-surface-active)', color: msg.role === 'user' ? 'var(--text-on-primary)' : 'var(--text-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '13px', fontWeight: 600, flexShrink: 0, marginTop: 2 }}>{msg.role === 'user' ? '我' : 'AI'}</div>
                <div style={{ maxWidth: '80%', minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 4, flexDirection: msg.role === 'user' ? 'row-reverse' : 'row' }}>
                    <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>{msg.role === 'user' ? '我' : '助手'}</span>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{formatTime(msg.createdAt)}</span>
                  </div>
                  {msg.role === 'assistant' && msg.id === currentAssistantIdRef.current && loading && !msg.content && renderThinking}
                  <div style={{ background: msg.role === 'user' ? 'var(--bg-primary)' : 'var(--bg-surface)', color: msg.role === 'user' ? 'var(--text-on-primary)' : 'var(--text-primary)', padding: 'var(--space-3) var(--space-4)', borderRadius: msg.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px', border: msg.role === 'user' ? 'none' : '1px solid var(--border-color)', boxShadow: msg.role === 'user' ? 'none' : 'var(--shadow-sm)', fontSize: '14px', lineHeight: 1.6, wordBreak: 'break-word' }}>
                    {msg.role === 'assistant' ? (
                      <div className="markdown-body"><ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content || (loading && msg.id === currentAssistantIdRef.current ? '...' : '')}</ReactMarkdown></div>
                    ) : (
                      <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                    )}
                  </div>
                </div>
              </div>
            ))}

            {loading && !messages.some((m) => m.role === 'assistant' && m.id === currentAssistantIdRef.current) && (
              <div className="flex" style={{ gap: 'var(--space-3)', marginBottom: 'var(--space-4)' }}>
                <div style={{ width: 32, height: 32, borderRadius: 'var(--radius-full)', background: 'var(--bg-surface-active)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}><span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)' }}>AI</span></div>
                <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-color)', padding: 'var(--space-3) var(--space-4)', borderRadius: '16px 16px 16px 4px', fontSize: '14px', color: 'var(--text-muted)' }}>思考中<span className="dot-blink">.</span><span className="dot-blink">.</span><span className="dot-blink">.</span></div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Area */}
        <div style={{ borderTop: '1px solid var(--border-color)', padding: 'var(--space-3) var(--space-4)', background: 'var(--bg-surface)' }}>
          <div style={{ maxWidth: 800, margin: '0 auto' }}>
            {/* 维护进度条 */}
            {maintenanceRunning && maintenanceProgress && (
              <div style={{ marginBottom: 8 }}>
                <div style={{ height: 4, width: '100%', backgroundColor: 'var(--bg-inset)', borderRadius: 2, overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${(maintenanceProgress.current / maintenanceProgress.total) * 100}%`, backgroundColor: 'var(--bg-primary)', borderRadius: 2, transition: 'width 0.3s' }} />
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{maintenanceProgress.message}</div>
              </div>
            )}

            {/* 维护控制栏 */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'center' }}>
              <select value={maintenanceMode} onChange={(e) => setMaintenanceMode(e.target.value as any)} style={{ padding: '4px 8px', fontSize: 12, borderRadius: 6, border: '1px solid var(--border-color)', background: 'var(--bg-surface)' }}>
                <option value="incremental">增量维护</option>
                <option value="full">全库维护</option>
              </select>
              <select value={executionMode} onChange={(e) => setExecutionMode(e.target.value as any)} style={{ padding: '4px 8px', fontSize: 12, borderRadius: 6, border: '1px solid var(--border-color)', background: 'var(--bg-surface)' }}>
                <option value="direct">直连模式</option>
                <option value="enhanced">增强模式</option>
              </select>
            </div>

            <div className="flex" style={{ gap: 'var(--space-3)', alignItems: 'flex-end' }}>
              <div style={{ flex: 1, position: 'relative' }}>
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={handleInputChange}
                  onKeyDown={handleKeyDown}
                  placeholder="输入消息... (Enter 发送，Shift+Enter 换行)"
                  disabled={loading}
                  rows={1}
                  style={{
                    width: '100%', padding: '10px 14px', paddingRight: 80, borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)', background: 'var(--bg-base)', color: 'var(--text-primary)', fontSize: '14px', lineHeight: 1.5, resize: 'none', outline: 'none', minHeight: 44, maxHeight: 200, fontFamily: 'inherit', transition: 'border-color var(--transition-fast), box-shadow var(--transition-fast)',
                  }}
                  onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--bg-primary)'; e.currentTarget.style.boxShadow = '0 0 0 3px var(--bg-primary-light)'; }}
                  onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--border-color)'; e.currentTarget.style.boxShadow = 'none'; }}
                />
                <span style={{ position: 'absolute', right: 10, bottom: 10, fontSize: '11px', color: 'var(--text-muted)', pointerEvents: 'none' }}>{input.length > 0 && `${input.length} 字`}</span>
              </div>

              <button onClick={sendMessage} disabled={loading || !input.trim()} className="btn btn-primary" style={{ height: 44, width: 44, padding: 0, borderRadius: 'var(--radius-lg)', flexShrink: 0 }} title="发送">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
              </button>

              <button onClick={clearHistory} className="btn btn-ghost" style={{ height: 44, width: 44, padding: 0, borderRadius: 'var(--radius-lg)', flexShrink: 0, color: 'var(--text-muted)' }} title="清空对话">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>
              </button>

              {/* 维护按钮组 */}
              <button onClick={runHealthCheck} disabled={maintenanceRunning} className="btn btn-ghost" style={{ height: 44, width: 44, padding: 0, borderRadius: 'var(--radius-lg)', flexShrink: 0, color: 'var(--text-muted)' }} title="健康检查">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" /></svg>
              </button>
              <button onClick={runPoolPrecipitation} disabled={maintenanceRunning} className="btn btn-ghost" style={{ height: 44, width: 44, padding: 0, borderRadius: 'var(--radius-lg)', flexShrink: 0, color: 'var(--text-muted)' }} title="沉淀暂存区思考池">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" /></svg>
              </button>
              <button onClick={() => setShowImportModal(true)} className="btn btn-ghost" style={{ height: 44, width: 44, padding: 0, borderRadius: 'var(--radius-lg)', flexShrink: 0, color: 'var(--text-muted)' }} title="导入知识">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" /></svg>
              </button>
              <button
              onClick={rebuildIndex}
              disabled={indexRebuilding}
              className="btn btn-ghost"
              style={{
              height: 44,
              width: 44,
              padding: 0,
              borderRadius: 'var(--radius-lg)',
              flexShrink: 0,
              color: 'var(--text-muted)',
              }}
              title="重建知识库索引"
            > 
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="23 4 23 10 17 10" />
              <polyline points="1 20 1 14 7 14" />
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
              </svg>
              </button>
            </div>
          </div>
        </div>

        {/* 导入知识模态框 */}
        {showImportModal && (
          <div className="modal-overlay" onClick={() => setShowImportModal(false)}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 500 }}>
              <div className="modal-header">
                <h3>导入知识</h3>
                <button onClick={() => setShowImportModal(false)} className="btn btn-ghost btn-sm">✕</button>
              </div>
              <div className="modal-body">
                <textarea
                  className="input"
                  rows={8}
                  value={importText}
                  onChange={(e) => setImportText(e.target.value)}
                  placeholder="粘贴书籍内容或长文本..."
                />
              </div>
              <div className="modal-footer">
                <button className="btn" onClick={() => setShowImportModal(false)}>取消</button>
                <button className="btn btn-primary" onClick={runImport} disabled={!importText.trim()}>导入</button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 右侧思考池面板 */}
      <div style={{
        width: showThoughtPool ? 300 : 40,
        minWidth: showThoughtPool ? 300 : 40,
        borderLeft: '1px solid var(--border-color)',
        background: 'var(--bg-surface)',
        display: 'flex',
        flexDirection: 'column',
        transition: 'width 0.2s ease, min-width 0.2s ease',
        overflow: 'hidden'
      }}>
        {/* 折叠按钮 */}
        <button
          onClick={() => setShowThoughtPool(!showThoughtPool)}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 4,
            padding: '8px',
            background: 'transparent',
            border: 'none',
            borderBottom: '1px solid var(--border-color)',
            cursor: 'pointer',
            color: 'var(--text-muted)',
            fontSize: 12,
            fontFamily: 'inherit',
            whiteSpace: 'nowrap'
          }}
          title={showThoughtPool ? '折叠思考池' : '展开思考池'}
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ transition: 'transform 0.2s ease' }}>
            <polyline points={showThoughtPool ? "15 6 9 12 15 18" : "9 6 15 12 9 18"} />
          </svg>
          {showThoughtPool && <span>思考池</span>}
        </button>

        {/* 思考池内容 */}
        {showThoughtPool && (
          <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: 'var(--space-3)',
            fontSize: '13px',
            color: 'var(--text-secondary)',
            lineHeight: 1.6,
            whiteSpace: 'pre-wrap'
          }}>
            {thoughtPoolContent || (
              <div style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
                思考池为空。发送消息后，这里将显示思考池的实时演化过程。
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Chat;