import { FormEvent, useEffect, useRef, useState } from 'react';
import { getAccessToken } from '../auth';
import {
  apiBase,
  listProjects,
  Project,
  listKbs,
  KnowledgeBase,
} from '../api/client';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface ChatChunk {
  id?: string;
  choices?: { delta?: { content?: string } }[];
  usage?: { prompt_tokens?: number; completion_tokens?: number };
}

// 用 fetch + ReadableStream 解析 text/event-stream，逐字累加显示。
async function streamChat(
  payload: Record<string, unknown>,
  token: string,
  onDelta: (text: string) => void
): Promise<void> {
  const resp = await fetch(`${apiBase}/v1/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  if (!resp.ok || !resp.body) {
    let msg = `请求失败 (${resp.status})`;
    try {
      const j = await resp.json();
      msg = j?.error?.message || msg;
    } catch {
      /* ignore */
    }
    throw new Error(msg);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE: 以空行分隔事件
    const events = buffer.split('\n\n');
    buffer = events.pop() ?? '';

    for (const evt of events) {
      for (const line of evt.split('\n')) {
        const trimmed = line.trim();
        if (!trimmed.startsWith('data:')) continue;
        const data = trimmed.slice('data:'.length).trim();
        if (data === '[DONE]') return;
        try {
          const chunk: ChatChunk = JSON.parse(data);
          const content = chunk.choices?.[0]?.delta?.content;
          if (content) onDelta(content);
        } catch {
          /* 跳过无法解析的片段 */
        }
      }
    }
  }
}

export default function Chat() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [projectId, setProjectId] = useState<string>('');
  const [kbId, setKbId] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listProjects()
      .then((ps) => {
        setProjects(ps);
        if (ps.length) setProjectId(ps[0].id);
      })
      .catch(() => setError('无法加载项目列表'));
  }, []);

  useEffect(() => {
    if (!projectId) {
      setKbs([]);
      setKbId('');
      return;
    }
    listKbs(projectId)
      .then(setKbs)
      .catch(() => setKbs([]));
  }, [projectId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages]);

  async function send(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || busy) return;
    setError(null);
    const token = getAccessToken();
    if (!token) {
      setError('登录已失效，请重新登录');
      return;
    }

    const next = [...messages, { role: 'user' as const, content: text }];
    setMessages(next);
    setInput('');
    setBusy(true);

    // 先放一条空的 assistant 消息用于流式追加
    setMessages([...next, { role: 'assistant', content: '' }]);

    try {
      const payload: Record<string, unknown> = {
        model: 'qwen3-235b',
        messages: next.map((m) => ({ role: m.role, content: m.content })),
        stream: true,
        project_id: projectId || null,
        tools: 'auto',
        temperature: 0.7,
      };
      if (kbId) (payload as any).kb_id = kbId;

      await streamChat(payload, token, (delta) => {
        setMessages((prev) => {
          const copy = [...prev];
          const last = copy[copy.length - 1];
          if (last?.role === 'assistant') {
            copy[copy.length - 1] = { role: 'assistant', content: last.content + delta };
          } else {
            copy.push({ role: 'assistant', content: delta });
          }
          return copy;
        });
      });
    } catch (err: any) {
      setError(err?.message || '对话请求失败');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page chat-page">
      <header className="page-head">
        <h2>对话工作台</h2>
        <div className="selectors">
          <label>
            项目
            <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
              {projects.length === 0 && <option value="">（无项目）</option>}
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </label>
          <label>
            知识库
            <select value={kbId} onChange={(e) => setKbId(e.target.value)}>
              <option value="">（不使用）</option>
              {kbs.map((k) => (
                <option key={k.id} value={k.id}>{k.name}</option>
              ))}
            </select>
          </label>
        </div>
      </header>

      {error && <div className="alert">{error}</div>}

      <div className="chat-log" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="empty">在下方输入问题，开始一次带企业知识的对话。</div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role}`}>
            <div className="role">{m.role === 'user' ? '我' : 'WorkBuddy'}</div>
            <div className="text">{m.content || (busy && i === messages.length - 1 ? '▍' : '')}</div>
          </div>
        ))}
      </div>

      <form className="chat-input" onSubmit={send}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={busy ? '回答生成中…' : '输入消息，Enter 发送'}
          disabled={busy}
        />
        <button className="btn-primary" type="submit" disabled={busy || !input.trim()}>
          发送
        </button>
      </form>
    </div>
  );
}
