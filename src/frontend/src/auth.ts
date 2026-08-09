// 本地 JWT 存取：前端只持有 access_token 与 refresh_token（localStorage 兜底）。
// 生产建议配合 httpOnly cookie，但 MVP 用 localStorage 简化闭环。

const ACCESS_KEY = 'wb_access_token';
const REFRESH_KEY = 'wb_refresh_token';

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh?: string): void {
  localStorage.setItem(ACCESS_KEY, access);
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}
