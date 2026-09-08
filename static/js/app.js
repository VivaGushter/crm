import { S, setToken, getToken, clearToken } from './state.js';
import { $, esc, money, dateKey, dt, labelDate } from './utils.js';
import { api } from './api.js';
import { openModal, closeModal, toggleDropdown, closeDropdown } from './ui.js';
import { renderCalendar, renderWeek, renderDay, switchView } from './calendar.js';
import { renderRequests, clearRequest, newRequest, editRequest, removeRequest, saveRequest, loadRequests, openRequestView, editViewedRequest, removeViewedRequest } from './requests.js';
import { renderUsersOptions, renderUsers, newUser, editUser, saveUser, removeUser } from './users.js';
import { openReport, loadReport, openAnalytics } from './reports.js';
import { openClients, openAllClients, openClientDetail, exportClients, openAudit } from './clients.js';

const PENDING_CALC_KEY = 'master_crm_pending_calc';

window.editRequest = editRequest;
window.removeRequest = removeRequest;
window.openRequestView = openRequestView;
window.editUser = editUser;
window.openClientDetail = openClientDetail;
window.selectMenuItem = selectMenuItem;
window.renderStats = renderStats;
window.renderCalendar = renderCalendar;
window.renderRequests = renderRequests;

function renderStats() {
  const today = new Date().toISOString().slice(0, 10), done = S.items.filter(x => x.status === 'done');
  $('statTotal').textContent = S.items.length;
  $('statToday').textContent = S.items.filter(x => dateKey(x.visit_date) === today).length;
  $('statScheduled').textContent = S.items.filter(x => x.status === 'scheduled').length;
  $('statDone').textContent = done.length;
  $('statRevenue').textContent = money(done.reduce((a, x) => a + Number(x.price || 0), 0));
}

async function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  $('themeBtn').textContent = theme === 'dark' ? '☀️' : '🌙';
  try { await api('/api/settings', { method: 'PUT', body: JSON.stringify({ theme }) }); } catch (e) {}
}

async function toggleTheme() {
  const now = document.documentElement.dataset.theme || 'light';
  const next = now === 'dark' ? 'light' : 'dark';
  await setTheme(next);
}

function selectMenuItem(item) {
  closeDropdown();
  if (item === 'price') window.location.href = '/price';
  else if (item === 'calculation') window.location.href = '/calculation';
  else if (item === 'admin') window.location.href = '/admin';
  else if (item === 'clients') openClients();
  else if (item === 'analytics') openAnalytics();
  else if (item === 'report') openReport();
  else if (item === 'users') { renderUsers(); openModal('usersModal'); }
  else if (item === 'audit') openAudit();
  else if (item === 'logout') logout();
}

function hasPendingCalculation() {
  try {
    const pending = JSON.parse(sessionStorage.getItem(PENDING_CALC_KEY) || 'null');
    return Boolean(pending && Array.isArray(pending.items) && pending.items.length);
  } catch (e) {
    return false;
  }
}

function openPendingCalculationRequest() {
  if (hasPendingCalculation()) newRequest();
}

async function load() {
  S.users = await api('/api/users');
  renderUsersOptions();
  await loadRequests();
  renderCalendar();
}

async function login() {
  try {
    const username = $('loginUser').value.trim();
    const password = $('loginPass').value;
    const response = await api('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });
    setToken(response.token);
    S.me = response.user;
    if ($('rememberMe').checked) localStorage.setItem('master_crm_remember', '1');
    else localStorage.removeItem('master_crm_remember');
    $('sessionPill').textContent = 'Вошёл: ' + S.me.name;
    $('menuAdmin').classList.toggle('hidden', S.me.role !== 'admin');
    $('menuUsers').classList.toggle('hidden', S.me.role !== 'admin');
    $('menuAudit').classList.toggle('hidden', !['admin', 'manager'].includes(S.me.role));
    if (S.me.theme) setTheme(S.me.theme);
    else setTheme(document.documentElement.dataset.theme || 'light');
    $('loginView').classList.add('hidden');
    $('appView').classList.remove('hidden');
    await load();
    if (hasPendingCalculation()) openPendingCalculationRequest();
    else clearRequest();
  } catch (e) {
    alert(e.message || 'Неверный логин или пароль');
  }
}

async function logout() {
  try {
    await api('/api/auth/logout', { method: 'POST' });
  } catch (e) {}
  clearToken();
  S.auth = null; S.me = null;
  localStorage.removeItem('master_crm_remember');
  $('appView').classList.add('hidden');
  $('loginView').classList.remove('hidden');
  alert('Вы вышли из системы');
}

$('loginBtn').onclick = () => login();
$('loginPass').addEventListener('keydown', e => { if (e.key === 'Enter') login(); });
$('themeBtn').onclick = toggleTheme;
$('menuBtn').onclick = toggleDropdown;
$('prevMonth').onclick = () => { S.month = new Date(S.month.getFullYear(), S.month.getMonth() - 1, 1); renderCalendar(); };
$('nextMonth').onclick = () => { S.month = new Date(S.month.getFullYear(), S.month.getMonth() + 1, 1); renderCalendar(); };
$('prevWeek').onclick = () => { S.selected = new Date(new Date(S.selected).setDate(new Date(S.selected).getDate() - 7)); S.month = new Date(S.selected); renderWeek(); };
$('nextWeek').onclick = () => { S.selected = new Date(new Date(S.selected).setDate(new Date(S.selected).setDate(new Date(S.selected).getDate() + 7)); S.month = new Date(S.selected); renderWeek(); };
$('prevDay').onclick = () => { S.selected = new Date(new Date(S.selected).setDate(new Date(S.selected).getDate() - 1)); S.month = new Date(S.selected); renderDay(); };
$('nextDay').onclick = () => { S.selected = new Date(new Date(S.selected).setDate(new Date(S.selected).getDate() + 1)); S.month = new Date(S.selected); renderDay(); };
$('dateFilter').value = S.selected;
$('dateFilter').onchange = () => { S.selected = $('dateFilter').value; S.month = new Date(S.selected); renderCalendar(); renderRequests(); if (S.view === 'week') renderWeek(); if (S.view === 'day') renderDay(); };
['search', 'statusFilter', 'assigneeFilter', 'sourceFilter', 'contactMethodFilter'].forEach(id => $(id).addEventListener('input', renderRequests));
document.querySelectorAll('.view-switch .btn').forEach(b => b.onclick = () => switchView(b.dataset.view));
$('newRequestFab').onclick = newRequest;
$('newRequestTop').onclick = newRequest;
$('clearRequest').onclick = clearRequest;
$('requestForm').onsubmit = saveRequest;
$('viewEditBtn').onclick = editViewedRequest;
$('viewDeleteBtn').onclick = removeViewedRequest;
$('newUserBtn').onclick = newUser;
$('userForm').onsubmit = saveUser;
$('deleteUserBtn').onclick = removeUser;
$('showAllClientsBtn').onclick = () => {};
$('exportClientsBtn').onclick = exportClients;
$('loadReportBtn').onclick = loadReport;
document.querySelectorAll('[data-close]').forEach(b => b.onclick = () => closeModal(b.dataset.close));
document.querySelectorAll('.modal').forEach(m => m.addEventListener('click', e => { if (e.target === m) closeModal(m.id); }));
document.addEventListener('click', e => { if (!e.target.closest('.dropdown')) closeDropdown(); });
document.documentElement.dataset.theme = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
$('themeBtn').textContent = document.documentElement.dataset.theme === 'dark' ? '☀️' : '🌙';

try {
  const token = getToken();
  if (token) {
    const me = await api('/api/auth/me');
    S.me = me;
    $('sessionPill').textContent = 'Вошёл: ' + S.me.name;
    $('menuAdmin').classList.toggle('hidden', S.me.role !== 'admin');
    $('menuUsers').classList.toggle('hidden', S.me.role !== 'admin');
    $('menuAudit').classList.toggle('hidden', !['admin', 'manager'].includes(S.me.role));
    if (S.me.theme) setTheme(S.me.theme);
    else setTheme(document.documentElement.dataset.theme || 'light');
    $('loginView').classList.add('hidden');
    $('appView').classList.remove('hidden');
    await load();
    openPendingCalculationRequest();
  }
} catch (e) {
  clearToken();
}
