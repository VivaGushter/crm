import { S } from './state.js';
import { $, esc, money, dateKey, dt, labelDate } from './utils.js';
import { api } from './api.js';
import { openModal, closeModal, toggleDropdown, closeDropdown } from './ui.js';
import { renderCalendar, renderWeek, renderDay, switchView } from './calendar.js';
import { renderRequests, clearRequest, newRequest, editRequest, removeRequest, saveRequest, loadRequests } from './requests.js';
import { renderUsersOptions, renderUsers, newUser, editUser, saveUser, removeUser } from './users.js';
import { openReport, loadReport, openAnalytics } from './reports.js';
import { openClients, openAllClients, openClientDetail, exportClients, openAudit } from './clients.js';

// Глобальные функции для HTML-обработчиков
window.editRequest = editRequest;
window.removeRequest = removeRequest;
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
  try { await api('/api/me/settings', { method: 'PUT', body: JSON.stringify({ theme }) }); } catch (e) {}
}

async function toggleTheme() {
  const now = document.documentElement.dataset.theme || 'light';
  const next = now === 'dark' ? 'light' : 'dark';
  await setTheme(next);
}

function selectMenuItem(item) {
  closeDropdown();
  if (item === 'price') window.location.href = '/price';
  else if (item === 'admin') window.location.href = '/admin';
  else if (item === 'clients') openClients();
  else if (item === 'analytics') openAnalytics();
  else if (item === 'report') openReport();
  else if (item === 'users') { renderUsers(); openModal('usersModal'); }
  else if (item === 'audit') openAudit();
  else if (item === 'logout') logout();
}

async function load() {
  S.users = await api('/api/users');
  renderUsersOptions();
  await loadRequests();
  renderCalendar();
}

async function login() {
  try {
    S.auth = { user: $('loginUser').value.trim(), pass: $('loginPass').value };
    const me = await api('/api/me');
    S.me = me;
    if ($('rememberMe').checked) localStorage.setItem('master_crm_auth', JSON.stringify(S.auth));
    else localStorage.removeItem('master_crm_auth');
    $('sessionPill').textContent = 'Вошёл: ' + S.me.name;
    $('menuAdmin').classList.toggle('hidden', S.me.role !== 'admin');
    $('menuUsers').classList.toggle('hidden', S.me.role !== 'admin');
    $('menuAudit').classList.toggle('hidden', !['admin', 'manager'].includes(S.me.role));
    if (me.theme) setTheme(me.theme);
    else setTheme(document.documentElement.dataset.theme || 'light');
    $('loginView').classList.add('hidden');
    $('appView').classList.remove('hidden');
    await load();
    clearRequest();
  } catch (e) {
    alert(e.message || 'Неверный логин или пароль');
  }
}

function logout(show = true) {
  S.auth = null; S.me = null;
  localStorage.removeItem('master_crm_auth');
  $('appView').classList.add('hidden');
  $('loginView').classList.remove('hidden');
  if (show) alert('Вы вышли из системы');
}

// Обработчики событий — вешаем после определения всех функций
$('loginBtn').onclick = () => login();
$('loginPass').addEventListener('keydown', e => { if (e.key === 'Enter') login(); });
$('themeBtn').onclick = toggleTheme;
$('menuBtn').onclick = toggleDropdown;
$('prevMonth').onclick = () => { S.month = new Date(S.month.getFullYear(), S.month.getMonth() - 1, 1); renderCalendar(); };
$('nextMonth').onclick = () => { S.month = new Date(S.month.getFullYear(), S.month.getMonth() + 1, 1); renderCalendar(); };
$('prevWeek').onclick = () => { S.selected = new Date(new Date(S.selected).setDate(new Date(S.selected).getDate() - 7)); S.month = new Date(S.selected); renderWeek(); };
$('nextWeek').onclick = () => { S.selected = new Date(new Date(S.selected).setDate(new Date(S.selected).getDate() + 7)); S.month = new Date(S.selected); renderWeek(); };
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

// Авто-вход из localStorage
try {
  const saved = JSON.parse(localStorage.getItem('master_crm_auth'));
  if (saved?.user && saved?.pass) {
    $('loginUser').value = saved.user;
    $('loginPass').value = saved.pass;
    $('rememberMe').checked = true;
    setTimeout(() => login(), 100);
  }
} catch (e) {}
