import { FormEvent, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { loginLocal } from '../api/client';
import { setTokens } from '../auth';

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');

  // OIDC 回调落地：IdP 登录后回跳 /login?access_token=...&refresh_token=...，读取并跳转
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const at = params.get('access_token');
    const rt = params.get('refresh_token');
    if (at) {
      setTokens(at, rt || undefined);
      window.history.replaceState({}, '', window.location.pathname);
      navigate('/chat', { replace: true });
    }
  }, [navigate]);
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const tokens = await loginLocal(username, password);
      setTokens(tokens.access_token, tokens.refresh_token);
      navigate('/chat', { replace: true });
    } catch (err: any) {
      const msg = err?.response?.data?.error?.message || err?.message || '登录失败';
      setError(msg);
    } finally {
      setBusy(false);
    }
  }

  function onOidc() {
    // TODO: SSO/OIDC 跳转。契约 §6.1：前端 → gateway(/api/auth/login?redirect_uri) → IdP 授权码流。
    // 待后端提供 redirect_uri 与回调落地页后补全；当前直接跳网关授权起点。
    const base =
      (import.meta.env.REACT_APP_API_BASE as string | undefined) ||
      (import.meta.env.VITE_API_BASE as string | undefined) ||
      '/api';
    window.location.href = `${base}/auth/login?redirect_uri=${encodeURIComponent(window.location.origin + '/chat')}`;
  }

  return (
    <div className="login-wrap">
      <form className="login-card" onSubmit={onSubmit}>
        <h1>WorkBuddy Enterprise</h1>
        <p className="sub">企业级 AI 智能体工作台 · 登录</p>

        <label>用户名</label>
        <input
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="username"
          autoFocus
        />

        <label>密码</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="password"
        />

        {error && <div className="alert">{error}</div>}

        <button className="btn-primary" type="submit" disabled={busy}>
          {busy ? '登录中…' : '本地登录'}
        </button>

        <div className="divider"><span>或</span></div>

        <button className="btn-oidc" type="button" onClick={onOidc}>
          使用企业账号登录 (OIDC)
        </button>
      </form>
    </div>
  );
}
