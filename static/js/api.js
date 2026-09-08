import { getToken } from './state.js';

export function authHeaders() {
  const token = getToken();
  return token ? { Authorization: 'Bearer ' + token } : {};
}

export async function api(url, opt = {}) {
  const r = await fetch(url, { ...opt, headers: { 'Content-Type': 'application/json', ...authHeaders(), ...(opt.headers || {}) } });
  if (r.status === 401) {
    localStorage.removeItem('master_crm_token');
    window.location.reload();
    throw new Error('Нужно войти заново');
  }
  const body = await r.text();
  let data = {};
  try { data = body ? JSON.parse(body) : {}; } catch { data = { detail: body }; }
  if (!r.ok) throw new Error(data.detail || 'Ошибка запроса');
  return data;
}
