import { FormEvent, useEffect, useRef, useState } from 'react';
import {
  listProjects,
  Project,
  listKbs,
  listDocuments,
  createKb,
  KnowledgeBase,
  ingestDocument,
  getDocument,
  DocumentMeta,
  searchKb,
  SearchResult,
} from '../api/client';

export default function Knowledge() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState<string>('');
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [kbId, setKbId] = useState<string>('');
  const [newName, setNewName] = useState('');

  const [docs, setDocs] = useState<DocumentMeta[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [loadingDocs, setLoadingDocs] = useState(false);

  // 已发起轮询的 document_id 集合
  const pollingRef = useRef<Set<string>>(new Set());

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
      .then((ks) => {
        setKbs(ks);
        setKbId(ks[0]?.id ?? '');
      })
      .catch(() => setKbs([]));
  }, [projectId]);

  useEffect(() => {
    if (!kbId) {
      setDocs([]);
      setLoadingDocs(false);
      return;
    }
    let cancelled = false;
    setLoadingDocs(true);
    setError(null);
    listDocuments(kbId)
      .then((ds) => {
        if (cancelled) return;
        setDocs(ds);
        // 切换知识库后，继续轮询此前尚未终态（pending/parsing）的文档，保证状态最终收敛
        ds.filter((d) => d.status === 'pending' || d.status === 'parsing').forEach((d) => {
          if (!pollingRef.current.has(d.id)) {
            pollingRef.current.add(d.id);
            pollStatus(kbId, d);
          }
        });
      })
      .catch(() => {
        if (!cancelled) setDocs([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingDocs(false);
      });
    return () => {
      cancelled = true;
    };
  }, [kbId]);

  async function onAddKb(e: FormEvent) {
    e.preventDefault();
    const name = newName.trim();
    if (!name || !projectId) return;
    setError(null);
    try {
      const kb = await createKb(name, projectId);
      setKbs((prev) => [...prev, kb]);
      setKbId(kb.id);
      setNewName('');
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || err?.message || '创建知识库失败');
    }
  }

  async function onUpload(file: File) {
    if (!kbId) {
      setError('请先选择或创建一个知识库');
      return;
    }
    setError(null);
    setUploading(true);
    try {
      const { document_id, status } = await ingestDocument(kbId, file);
      const doc: DocumentMeta = {
        id: document_id,
        kb_id: kbId,
        title: file.name,
        status,
        chunk_count: 0,
      };
      setDocs((prev) => [...prev, doc]);
      pollingRef.current.add(document_id);
      pollStatus(kbId, doc);
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || err?.message || '上传失败');
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  }

  // 轮询文档状态直到 indexed / failed
  function pollStatus(kb: string, doc: DocumentMeta) {
    const timer = setInterval(async () => {
      try {
        const meta = await getDocument(kb, doc.id);
        setDocs((prev) => prev.map((d) => (d.id === doc.id ? { ...d, ...meta } : d)));
        if (meta.status === 'indexed' || meta.status === 'failed') {
          clearInterval(timer);
          pollingRef.current.delete(doc.id);
        }
      } catch {
        clearInterval(timer);
        pollingRef.current.delete(doc.id);
      }
    }, 2000);
  }

  async function onSearch(e: FormEvent) {
    e.preventDefault();
    if (!kbId || !query.trim()) return;
    setError(null);
    setSearching(true);
    try {
      const r = await searchKb(kbId, query.trim());
      setResults(r);
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || err?.message || '检索失败');
    } finally {
      setSearching(false);
    }
  }

  return (
    <div className="page">
      <header className="page-head">
        <h2>知识库管理</h2>
        <label>
          项目
          <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </label>
      </header>

      {error && <div className="alert">{error}</div>}

      <section className="kb-grid">
        <div className="card">
          <h3>知识库</h3>
          <form className="inline-form" onSubmit={onAddKb}>
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="新知识库名称"
            />
            <button className="btn-primary" type="submit">创建</button>
          </form>
          <ul className="kb-list">
            {kbs.length === 0 && <li className="muted">暂无知识库</li>}
            {kbs.map((k) => (
              <li
                key={k.id}
                className={k.id === kbId ? 'active' : ''}
                onClick={() => setKbId(k.id)}
              >
                <span>{k.name}</span>
                <small>{k.collection || k.id}</small>
              </li>
            ))}
          </ul>
        </div>

        <div className="card">
          <h3>文档入库</h3>
          <input
            ref={fileRef}
            type="file"
            disabled={!kbId || uploading}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onUpload(f);
            }}
          />
          <p className="hint">支持 PDF / Word / 图片 / 表格，上传后自动解析切片并轮询状态。</p>
          <table className="doc-table">
            <thead>
              <tr><th>标题</th><th>状态</th><th>切片数</th></tr>
            </thead>
            <tbody>
              {docs.length === 0 && loadingDocs && (
                <tr><td colSpan={3} className="muted">加载中…</td></tr>
              )}
              {docs.length === 0 && !loadingDocs && (
                <tr><td colSpan={3} className="muted">尚未上传文档</td></tr>
              )}
              {docs.map((d) => (
                <tr key={d.id}>
                  <td>{d.title || d.id}</td>
                  <td><span className={`tag ${d.status}`}>{d.status}</span></td>
                  <td>{d.chunk_count ?? '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card">
          <h3>检索测试</h3>
          <form className="inline-form" onSubmit={onSearch}>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="输入检索问题"
              disabled={!kbId || searching}
            />
            <button className="btn-primary" type="submit" disabled={!kbId || searching}>
              {searching ? '检索中…' : '检索'}
            </button>
          </form>
          <div className="search-results">
            {results.length === 0 && <p className="muted">暂无结果</p>}
            {results.map((r) => (
              <div key={r.chunk_id} className="result">
                <div className="result-meta">
                  <span>score {r.score.toFixed(3)}</span>
                  <span>doc {r.document_id.slice(0, 8)}</span>
                </div>
                <p>{r.content}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
