import axios, { AxiosInstance } from 'axios';
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from '../auth';

// API base 默认 /api：开发期经 vite 代理转发到 gateway(:8000)，生产经 nginx 反代。
// 任务约定环境变量 REACT_APP_API_BASE；Vite 下同时支持 VITE_API_BASE（见 vite.config envPrefix）。
const API_BASE: string =
  (import.meta.env.REACT_APP_API_BASE as string | undefined) ||
  (import.meta.env.VITE_API_BASE as string | undefined) ||
  '/api';

export const apiBase = API_BASE;

export interface TokenResponse {
  access_token: string;
  refresh_token?: string;
  expires_in?: number;
  token_type?: string;
}

export interface CurrentUser {
  id: string;
  username: string;
  display_name?: string;
  roles: string[];
  projects: string[];
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  owner_id?: string;
}

export interface KnowledgeBase {
  id: string;
  name: string;
  project_id?: string;
  embedding?: string;
  collection?: string;
  created_at?: string;
}

export interface DocumentMeta {
  id: string;
  kb_id?: string;
  title?: string;
  source_path?: string;
  status: string; // pending / parsing / indexed / failed
  chunk_count?: number;
  created_at?: string;
}

export interface SearchResult {
  chunk_id: string;
  document_id: string;
  score: number;
  content: string;
  meta?: Record<string, unknown>;
}

export interface AuditEvent {
  id: number;
  ts?: string;
  actor_id?: string;
  actor_name?: string;
  project_id?: string;
  action?: string;
  resource?: string;
  req_id?: string;
  model?: string;
  tokens_in?: number;
  tokens_out?: number;
  ip?: string;
  detail_json?: Record<string, unknown>;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export interface ApiError {
  error?: { code: string; message: string; req_id?: string };
}

const client: AxiosInstance = axios.create({ baseURL: API_BASE });

// 请求拦截器：附加 Bearer
client.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器：401 时尝试用 refresh_token 换发，失败则清除（由路由守卫跳登录）
let refreshing: Promise<string | null> | null = null;

client.interceptors.response.use(
  (resp) => resp,
  async (error) => {
    const original = error.config as any;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const rt = getRefreshToken();
      if (rt) {
        try {
          if (!refreshing) {
            refreshing = refreshToken(rt);
          }
          const newAccess = await refreshing;
          refreshing = null;
          if (newAccess) {
            setTokens(newAccess);
            original.headers.Authorization = `Bearer ${newAccess}`;
            return client(original);
          }
        } catch {
          refreshing = null;
        }
      }
      clearTokens();
      if (window.location.pathname !== '/login') {
        window.location.assign('/login');
      }
    }
    return Promise.reject(error);
  }
);

async function refreshToken(refresh: string): Promise<string | null> {
  try {
    const resp = await axios.post<TokenResponse>(`${API_BASE}/auth/token/refresh`, {
      refresh_token: refresh,
    });
    return resp.data.access_token ?? null;
  } catch {
    return null;
  }
}

// ============ 认证 ============
export async function loginLocal(username: string, password: string): Promise<TokenResponse> {
  const resp = await axios.post<TokenResponse>(`${API_BASE}/auth/login/local`, {
    username,
    password,
  });
  return resp.data;
}

export async function getCurrentUser(): Promise<CurrentUser> {
  const resp = await client.get<CurrentUser>('/auth/me');
  return resp.data;
}

export async function listProjects(): Promise<Project[]> {
  // auth-service 暴露 GET /projects，经网关映射 /api/auth/projects
  const resp = await client.get<Project[]>('/auth/projects');
  return resp.data;
}

// ============ 知识库 ============
export async function listKbs(projectId?: string): Promise<KnowledgeBase[]> {
  const resp = await client.get<KnowledgeBase[]>('/kb', {
    params: projectId ? { project_id: projectId } : undefined,
  });
  return resp.data;
}

export async function createKb(name: string, projectId?: string, embedding = 'bge-m3') {
  const resp = await client.post<KnowledgeBase>('/kb', { name, project_id: projectId, embedding });
  return resp.data;
}

export async function ingestDocument(kbId: string, file: File): Promise<{ document_id: string; status: string }> {
  const form = new FormData();
  form.append('file', file);
  const resp = await client.post(`/kb/${kbId}/ingest`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return resp.data;
}

export async function getDocument(kbId: string, docId: string): Promise<DocumentMeta> {
  const resp = await client.get<DocumentMeta>(`/kb/${kbId}/documents/${docId}`);
  return resp.data;
}

export async function listDocuments(kbId: string): Promise<DocumentMeta[]> {
  // 契约未单列文档列表接口，复用 knowledge-service 列表约定；若后端未提供则回退空数组
  try {
    const resp = await client.get<DocumentMeta[]>(`/kb/${kbId}/documents`);
    return resp.data;
  } catch {
    return [];
  }
}

export async function searchKb(
  kbId: string,
  query: string,
  topK = 5,
  rerank = true,
  scoreThreshold = 0.3
): Promise<SearchResult[]> {
  const resp = await client.post<{ results: SearchResult[] }>(`/kb/${kbId}/search`, {
    query,
    top_k: topK,
    rerank,
    score_threshold: scoreThreshold,
  });
  return resp.data.results ?? [];
}

// ============ 审计 ============
export async function listAuditEvents(params: {
  project_id?: string;
  action?: string;
  page?: number;
  size?: number;
}): Promise<Page<AuditEvent>> {
  const resp = await client.get<Page<AuditEvent>>('/audit/events', { params });
  return resp.data;
}

export default client;
