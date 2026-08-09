import { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { getAccessToken } from '../auth';

// 路由守卫：无 JWT 一律跳 /login。
export default function RequireAuth({ children }: { children: ReactNode }) {
  const location = useLocation();
  const token = getAccessToken();
  if (!token) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return <>{children}</>;
}
