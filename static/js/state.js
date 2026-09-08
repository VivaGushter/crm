export const S = {
  auth: null,
  me: null,
  users: [],
  items: [],
  month: new Date(new Date().getFullYear(), new Date().getMonth(), 1),
  selected: new Date().toISOString().slice(0, 10),
  weekStart: null,
  view: 'month'
};

export function setToken(token) {
  localStorage.setItem('master_crm_token', token);
}

export function getToken() {
  return localStorage.getItem('master_crm_token');
}

export function clearToken() {
  localStorage.removeItem('master_crm_token');
}
