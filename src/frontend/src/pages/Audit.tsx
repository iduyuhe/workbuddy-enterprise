import { useEffect, useState } from 'react';
import {
  getCurrentUser,
  listAuditEvents,
  listProjects,
  Project,
  AuditEvent,
  Page,
} from '../api/client';

const ACTION_OPTIONS = ['', 'chat', 'kb.ingest', 'skill.invoke', 'mcp.call', 'login'];

export default function Audit() {
  const [allowed, setAllowed] = useState<boolean | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState<string>('');
  const [action, setAction] = useState<string>('');

  const [data, setData] = useState<Page<AuditEvent> | null>(null);
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getCurrentUser()
      .then((u) => setAllowed(u.roles.some((r) => r === 'admin' || r === 'auditor')))
      .catch(() => setAllowed(false));
    listProjects().then(setProjects).catch(() => setProjects([]));
  }, []);

  useEffect(() => {
    if (allowed === false) return;
    fetchEvents();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, action, page, allowed]);

  async function fetchEvents() {
    setLoading(true);
    setError(null);
    try {
      const res = await listAuditEvents({
        project_id: projectId || undefined,
        action: action || undefined,
        page,
        size: 20,
      });
      setData(res);
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || err?.message || '加载审计事件失败');
    } finally {
      setLoading(false);
    }
  }

  if (allowed === false) {
    return (
      <div className="page">
        <div className="alert">无权访问审计日志（仅 admin / auditor 可见）。</div>
      </div>
    );
  }

  if (allowed === null) {
    return <div className="page"><p className="muted">加载中…</p></div>;
  }

  return (
    <div className="page">
      <header className="page-head">
        <h2>审计日志</h2>
        <div className="selectors">
          <label>
            项目
            <select value={projectId} onChange={(e) => { setPage(1); setProjectId(e.target.value); }}>
              <option value="">全部项目</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </label>
          <label>
            动作
            <select value={action} onChange={(e) => { setPage(1); setAction(e.target.value); }}>
              {ACTION_OPTIONS.map((a) => (
                <option key={a} value={a}>{a || '全部动作'}</option>
              ))}
            </select>
          </label>
        </div>
      </header>

      {error && <div className="alert">{error}</div>}
      {loading && <p className="muted">加载中…</p>}

      <table className="audit-table">
        <thead>
          <tr>
            <th>时间</th><th>操作者</th><th>项目</th><th>动作</th>
            <th>资源</th><th>模型</th><th>token(in/out)</th><th>IP</th>
          </tr>
        </thead>
        <tbody>
          {data && data.items.length === 0 && (
            <tr><td colSpan={8} className="muted">暂无审计事件</td></tr>
          )}
          {data?.items.map((ev) => (
            <tr key={ev.id}>
              <td>{ev.ts ? new Date(ev.ts).toLocaleString() : '-'}</td>
              <td>{ev.actor_name || ev.actor_id || '-'}</td>
              <td>{ev.project_id ? ev.project_id.slice(0, 8) : '-'}</td>
              <td><span className="tag action">{ev.action || '-'}</span></td>
              <td>{ev.resource || '-'}</td>
              <td>{ev.model || '-'}</td>
              <td>{(ev.tokens_in ?? '-')} / {(ev.tokens_out ?? '-')}</td>
              <td>{ev.ip || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="pager">
        <button className="btn-ghost" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
          上一页
        </button>
        <span>第 {page} 页 / 共 {data ? Math.max(1, Math.ceil(data.total / 20)) : 1} 页</span>
        <button
          className="btn-ghost"
          disabled={!data || page >= Math.ceil(data.total / 20)}
          onClick={() => setPage((p) => p + 1)}
        >
          下一页
        </button>
      </div>
    </div>
  );
}
