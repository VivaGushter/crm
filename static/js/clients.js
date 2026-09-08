import { $, esc, dt, money } from './utils.js';
import { STATUSES } from './constants.js';
import { api } from './api.js';
import { openModal, closeModal } from './ui.js';

export async function openClients() {
  try {
    const clients = await api('/api/clients');
    const recent = clients.slice(0, 3);
    $('clientsList').innerHTML = recent.length ? recent.map(c => `<div class="client-item" onclick="window.openClientDetail('${esc(c.client).replace(/'/g, "\\'")}')"><b>${esc(c.client)}</b><small>${c.count} заявок · ${money(c.revenue)} · Последняя: ${dt(c.last_visit)}</small></div>`).join('') : '<div class="empty">Клиентов пока нет</div>';
    $('showAllClientsBtn').onclick = () => { openAllClients(clients); };
    openModal('clientsModal');
  } catch (e) { alert('Не удалось загрузить клиентов: ' + e.message); }
}

export function openAllClients(clients) {
  const html = clients.map(c => `<div class="client-item" onclick="window.openClientDetail('${esc(c.client).replace(/'/g, "\\'")}')"><b>${esc(c.client)}</b><small>${c.count} заявок · ${money(c.revenue)} · Последняя: ${dt(c.last_visit)}</small></div>`).join('');
  $('clientsList').innerHTML = html;
}

export async function openClientDetail(name) {
  try {
    const data = await api('/api/clients/' + encodeURIComponent(name));
    $('clientDetailName').textContent = data.client;
    $('clientDetailStats').innerHTML = `<div><b>Всего заявок:</b> ${data.total}</div><div><b>Выручка:</b> ${money(data.revenue)}</div>`;
    $('clientDetailRequests').innerHTML = data.requests.length ? data.requests.map(r => `<article class="request"><div class="row"><div><div class="name">${esc(r.client)}</div><div class="muted">${dt(r.visit_date)}</div></div><span class="badge s-${r.status}">${STATUSES[r.status]}</span></div><div class="meta"><div>📍 ${esc(r.address)}</div><div>📞 <a href="tel:${esc(r.phone)}">${esc(r.phone)}</a></div><div>👤 ${esc(r.assignee_name || r.assignee)}</div><div>💰 ${money(r.price)}</div></div></article>`).join('') : '<div class="empty">Заявок нет</div>';
    openModal('clientDetailModal');
  } catch (e) { alert('Не удалось загрузить клиента: ' + e.message); }
}

export async function exportClients() {
  try {
    const data = await api('/api/clients/export');
    const blob = new Blob([data.csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'clients.csv'; a.click();
    URL.revokeObjectURL(url);
  } catch (e) { alert('Не удалось экспортировать: ' + e.message); }
}

export async function openAudit() {
  if (!['admin', 'manager'].includes(S.me.role)) { alert('Доступ только для администратора и менеджера'); return; }
  try {
    const logs = await api('/api/audit');
    $('auditList').innerHTML = logs.length ? logs.map(l => `<article class="request"><div class="row"><div><div class="name">${esc(l.user_name || l.user_id)}</div><div class="muted">${dt(l.created_at)}</div></div><span class="badge" style="background:var(--primary-soft)">${esc(l.action)}</span></div><div class="meta"><div><b>Сущность:</b> ${esc(l.entity_type)} ${l.entity_id ? `#${l.entity_id}` : ''}</div>${l.old_values ? `<div><b>Было:</b> <code style="font-size:12px">${esc(JSON.stringify(JSON.parse(l.old_values)).slice(0, 200))}</code></div>` : ''}${l.new_values ? `<div><b>Стало:</b> <code style="font-size:12px">${esc(JSON.stringify(JSON.parse(l.new_values)).slice(0, 200))}</code></div>` : ''}</div></article>`).join('') : '<div class="empty">Записей нет</div>';
    openModal('auditModal');
  } catch (e) { alert('Не удалось загрузить аудит: ' + e.message); }
}

import { S } from './state.js';
