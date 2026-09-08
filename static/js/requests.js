import { S } from './state.js';
import { $, esc, dateKey, dt, money, labelDate } from './utils.js';
import { STATUSES, SOURCE_LABELS, CONTACT_METHOD_LABELS } from './constants.js';
import { api } from './api.js';
import { openModal, closeModal } from './ui.js';
import { switchView } from './calendar.js';

export function filtered() {
  const q = $('search').value.trim().toLowerCase(), st = $('statusFilter').value, as = $('assigneeFilter').value,
    day = $('dateFilter').value || S.selected, src = $('sourceFilter').value, cm = $('contactMethodFilter').value;
  return S.items.filter(x => {
    const text = [x.client, x.address, x.phone, x.comment, x.assignee_name].join(' ').toLowerCase();
    return (!q || text.includes(q)) && (st === 'all' || x.status === st) && (as === 'all' || x.assignee === as)
      && (!day || dateKey(x.visit_date) === day) && (src === 'all' || x.source === src) && (cm === 'all' || x.contact_method === cm);
  }).sort((a, b) => a.visit_date.localeCompare(b.visit_date));
}

export function renderRequests() {
  $('dateTitle').textContent = 'Заявки на ' + labelDate($('dateFilter').value || S.selected);
  const rows = filtered();
  $('requests').innerHTML = rows.length ? rows.map(x => `<article class="request"><div class="row"><div><div class="name">${esc(x.client)}</div><div class="muted">${dt(x.visit_date)}</div></div><span class="badge s-${x.status}">${STATUSES[x.status]}</span></div><div class="meta"><div>📍 ${esc(x.address)}</div><div>📞 <a href="tel:${esc(x.phone)}">${esc(x.phone)}</a></div><div>👤 ${esc(x.assignee_name || x.assignee)}</div><div>💰 ${money(x.price)}</div>${x.source && x.source !== 'unknown' ? `<div>📥 ${SOURCE_LABELS[x.source] || x.source}</div>` : ''}${x.contact_method ? `<div>📞 ${CONTACT_METHOD_LABELS[x.contact_method] || x.contact_method}</div>` : ''}${x.comment ? `<div>📝 ${esc(x.comment)}</div>` : ''}</div><div class="two"><button class="btn btn-secondary" onclick="window.editRequest(${x.id})">Изменить</button><button class="btn btn-danger" onclick="window.removeRequest(${x.id})">Удалить</button></div></article>`).join('') : '<div class="empty">На выбранный день заявок нет.</div>';
}

export function clearRequest() {
  $('requestForm').reset(); $('requestId').value = ''; $('requestFormTitle').textContent = 'Новая заявка';
  $('requestStatus').value = 'new'; $('price').value = '0'; $('source').value = 'avito'; $('contactMethod').value = '';
  const d = new Date(S.selected + 'T10:00:00'); $('visitDate').value = d.toISOString().slice(0, 16);
  if (S.auth) $('assignee').value = S.auth.user;
}

export function newRequest() { clearRequest(); openModal('requestModal'); }

export function editRequest(id) {
  const x = S.items.find(i => i.id === id);
  if (!x) return;
  $('requestFormTitle').textContent = 'Редактирование заявки'; $('requestId').value = x.id;
  $('client').value = x.client; $('visitDate').value = x.visit_date.slice(0, 16);
  $('address').value = x.address; $('phone').value = x.phone; $('requestStatus').value = x.status;
  $('price').value = x.price; $('assignee').value = x.assignee; $('comment').value = x.comment || '';
  $('source').value = x.source || 'unknown'; $('contactMethod').value = x.contact_method || '';
  openModal('requestModal');
}

export async function removeRequest(id) {
  if (!confirm('Удалить заявку?')) return;
  try {
    await api('/api/requests/' + id, { method: 'DELETE' });
    await loadRequests();
    if (S.view === 'week') renderWeek();
    if (S.view === 'day') renderDay();
  } catch (e) { alert(e.message); }
}

export async function saveRequest(e) {
  e.preventDefault();
  const p = {
    client: $('client').value.trim(), visit_date: $('visitDate').value, address: $('address').value.trim(),
    phone: $('phone').value.trim(), status: $('requestStatus').value, price: Number($('price').value || 0),
    comment: $('comment').value.trim(), assignee: $('assignee').value, source: $('source').value, contact_method: $('contactMethod').value
  };
  try {
    const id = $('requestId').value;
    await api(id ? '/api/requests/' + id : '/api/requests', { method: id ? 'PUT' : 'POST', body: JSON.stringify(p) });
    S.selected = p.visit_date.slice(0, 10); $('dateFilter').value = S.selected;
    closeModal('requestModal');
    await loadRequests();
    if (S.view === 'week') renderWeek();
    if (S.view === 'day') renderDay();
  } catch (e) { alert('Не удалось сохранить: ' + e.message); }
}

export async function loadRequests() {
  S.items = await api('/api/requests');
  if (typeof window.renderStats === 'function') window.renderStats();
  if (typeof window.renderCalendar === 'function') window.renderCalendar();
  renderRequests();
}

import { renderCalendar, renderWeek, renderDay } from './calendar.js';
