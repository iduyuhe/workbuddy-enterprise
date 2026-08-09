import { useEffect, useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { getCurrentUser, CurrentUser } from '../api/client';
import { clearTokens } from '../auth';

export default function Layout() {
  const navigate = useNavigate();
  const [me, setMe] = useState<CurrentUser | null>(null);

  useEffect(() => {
    getCurrentUser()
      .then(setMe)
      .catch(() => {
        // 拿不到用户信息（token 失效）则回登录
        clearTokens();
        navigate('/login', { replace: true });
      });
  }, [navigate]);

  const canAudit = me?.roles.some((r) => r === 'admin' || r === 'auditor') ?? false;

  function logout() {
    clearTokens();
    navigate('/login', { replace: true });
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">WorkBuddy<span>Enterprise</span></div>
        <nav>
          <NavLink to="/chat" className={navClass}>对话工作台</NavLink>
          <NavLink to="/kb" className={navClass}>知识库</NavLink>
          {canAudit && <NavLink to="/audit" className={navClass}>审计日志</NavLink>}
        </nav>
        <div className="sidebar-foot">
          {me && (
            <div className="who">
              <strong>{me.display_name || me.username}</strong>
              <small>{me.roles.join(', ')}</small>
            </div>
          )}
          <button className="btn-ghost" onClick={logout}>退出登录</button>
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}

function navClass({ isActive }: { isActive: boolean }): string {
  return isActive ? 'nav-item active' : 'nav-item';
}
