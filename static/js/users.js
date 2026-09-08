import { S } from './state.js';
import { $, esc } from './utils.js';
import { ROLE_LABELS } from './constants.js';
import { api } from './api.js';
import { openModal, closeModal } from './ui.js';

export function renderUsersOptions() {
  const opts = S.users.map(u => `<option value="${esc(u.id)}">${esc(u.name)}</option>`).join('');
  $('assignee').innerHTML = opts;
  $('assigneeFilter').innerHTML = '<option value="all">Все мастера</option>' + opts;
}

export function renderUsers() {
  $('usersList').innerHTML = S.users.map(u => `<div class="user"><div><b>${esc(u.name)}</b><br><small>${esc(u.id)} · ${ROLE_LABELS[u.role] || u.role}</small></div><button class="btn btn-secondary" onclick="window.editUser('${esc(u.id)}')">Изменить</button></div>`).join('');
}

export function newUser() {
  $('userForm').reset(); $('editUserId').value = ''; $('newUserId').disabled = false;
  $('newUserPassword').required = true; $('passwordLabel').textContent = 'Пароль';
  $('userFormTitle').textContent = 'Новый пользователь'; $('deleteUserBtn').classList.add('hidden');
  openModal('userModal');
}

export function editUser(id) {
  const u = S.users.find(x => x.id === id);
  if (!u) return;
  $('editUserId').value = u.id; $('newUserId').value = u.id; $('newUserId').disabled = true;
  $('newUserName').value = u.name; $('newUserPassword').value = '';
  $('newUserPassword').required = false;
  $('passwordLabel').textContent = 'Новый пароль (оставь пустым, чтобы не менять)';
  $('newUserRole').value = u.role; $('userFormTitle').textContent = 'Редактирование пользователя';
  $('deleteUserBtn').classList.toggle('hidden', u.id === S.me.id);
  openModal('userModal');
}

export async function saveUser(e) {
  e.preventDefault();
  const old = $('editUserId').value, p = { id: $('newUserId').value.trim(), name: $('newUserName').value.trim(), password: $('newUserPassword').value, role: $('newUserRole').value };
  if (old && !p.password) delete p.password;
  try {
    await api(old ? '/api/users/' + old : '/api/users', { method: old ? 'PUT' : 'POST', body: JSON.stringify(p) });
    S.users = await api('/api/users');
    renderUsers();
    closeModal('userModal');
  } catch (e) { alert('Не удалось сохранить: ' + e.message); }
}

export async function removeUser() {
  const id = $('editUserId').value;
  if (!id || !confirm('Удалить пользователя ' + id + '?')) return;
  try {
    await api('/api/users/' + id, { method: 'DELETE' });
    S.users = await api('/api/users');
    renderUsers();
    closeModal('userModal');
  } catch (e) { alert('Не удалось удалить: ' + e.message); }
}
