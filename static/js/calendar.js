import { S } from './state.js';
import { $, localDateKey, labelDate, dt, getWeekStart, dateKey, esc, money } from './utils.js';
import { STATUSES, SOURCE_LABELS, CONTACT_METHOD_LABELS } from './constants.js';
import { renderRequests } from './requests.js';
import { switchView } from './calendar.js';

export function renderCalendar() {
  const m = S.month, start = new Date(m.getFullYear(), m.getMonth(), 1), weekday = (start.getDay() + 6) % 7;
  const gridStart = new Date(start); gridStart.setDate(start.getDate() - weekday);
  const by = {};
  S.items.forEach(x => { const k = dateKey(x.visit_date); (by[k] ??= []).push(x); });
  $('monthLabel').textContent = new Intl.DateTimeFormat('ru-RU', { month: 'long', year: 'numeric' }).format(m);
  $('calendar').innerHTML = '';
  for (let i = 0; i < 42; i++) {
    const d = new Date(gridStart); d.setDate(gridStart.getDate() + i);
    const k = localDateKey(d), list = (by[k] || []).sort((a, b) => a.visit_date.localeCompare(b.visit_date));
    const statusCounts = { new: 0, scheduled: 0, work: 0, done: 0, cancel: 0 };
    list.forEach(x => { if (STATUSES[x.status]) statusCounts[x.status]++; });
    const b = document.createElement('button'); b.type = 'button';
    b.className = 'day' + (d.getMonth() !== m.getMonth() ? ' other' : '') + (list.length ? ' has' : '') + (k === S.selected ? ' active' : '');
    let dotsHtml = '';
    if (statusCounts.new > 0) dotsHtml += `<span class="status-dot status-new" title="Новая: ${statusCounts.new}"></span>`;
    if (statusCounts.scheduled > 0) dotsHtml += `<span class="status-dot status-scheduled" title="Назначена: ${statusCounts.scheduled}"></span>`;
    if (statusCounts.work > 0) dotsHtml += `<span class="status-dot status-work" title="В работе: ${statusCounts.work}"></span>`;
    if (statusCounts.done > 0) dotsHtml += `<span class="status-dot status-done" title="Завершена: ${statusCounts.done}"></span>`;
    if (statusCounts.cancel > 0) dotsHtml += `<span class="status-dot status-cancel" title="Отменена: ${statusCounts.cancel}"></span>`;
    b.innerHTML = `<div class="dhead"><span>${d.getDate()}</span><span>${list.length || ''}</span></div><div style="margin-top:6px">${dotsHtml}${list.slice(0, 1).map(x => `<div class="dot">${esc(x.client)}</div>`).join('')}</div>`;
    b.onclick = () => { S.selected = k; $('dateFilter').value = k; renderCalendar(); if (typeof window.renderRequests === 'function') window.renderRequests(); if (S.view !== 'month') switchView('month'); };
    $('calendar').appendChild(b);
  }
}

export function renderWeek() {
  const start = getWeekStart(S.selected);
  $('weekLabel').textContent = new Intl.DateTimeFormat('ru-RU', { month: 'long', year: 'numeric' }).format(start);
  $('weekGrid').innerHTML = '';
  const by = {};
  S.items.forEach(x => { (by[dateKey(x.visit_date)] ??= []).push(x); });
  const weekDays = [];
  for (let i = 0; i < 7; i++) { const d = new Date(start); d.setDate(start.getDate() + i); weekDays.push(d); }
  const dayNames = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'];
  weekDays.forEach((d, i) => {
    const k = localDateKey(d), list = (by[k] || []).sort((a, b) => a.visit_date.localeCompare(b.visit_date)), today = dateKey(new Date()) === k;
    const col = document.createElement('div'); col.className = 'week-col';
    col.innerHTML = `<div class="week-head${today ? ' today' : ''}">${dayNames[i]}, ${d.getDate()}</div><div class="week-body">${list.map(x => `<div class="week-card" onclick="window.editRequest(${x.id})"><b>${esc(x.client)}</b><small>${dt(x.visit_date)}</small><small>${esc(x.address)}</small><span class="badge s-${x.status}" style="margin-top:6px;display:inline-block">${STATUSES[x.status]}</span></div>`).join('')}</div>`;
    $('weekGrid').appendChild(col);
  });
}

export function renderDay() {
  const d = new Date(S.selected);
  $('dayLabel').textContent = labelDate(S.selected);
  const list = S.items.filter(x => dateKey(x.visit_date) === S.selected).sort((a, b) => a.visit_date.localeCompare(b.visit_date));
  $('dayList').innerHTML = list.length ? list.map(x => `<div class="day-card"><div class="top"><div><div class="time">${dt(x.visit_date)}</div><div class="client">${esc(x.client)}</div></div><span class="badge s-${x.status}">${STATUSES[x.status]}</span></div><div class="meta"><div>📍 ${esc(x.address)}</div><div>📞 <a href="tel:${esc(x.phone)}">${esc(x.phone)}</a></div><div>👤 ${esc(x.assignee_name || x.assignee)}</div><div>💰 ${money(x.price)}</div>${x.source && x.source !== 'unknown' ? `<div>📥 ${SOURCE_LABELS[x.source] || x.source}</div>` : ''}${x.contact_method ? `<div>📞 ${CONTACT_METHOD_LABELS[x.contact_method] || x.contact_method}</div>` : ''}</div><div class="two" style="margin-top:10px"><button class="btn btn-secondary" onclick="window.editRequest(${x.id})">Изменить</button><button class="btn btn-danger" onclick="window.removeRequest(${x.id})">Удалить</button></div></div>`).join('') : '<div class="empty">На этот день заявок нет.</div>';
}

export function switchView(v) {
  S.view = v;
  document.querySelectorAll('.view-switch .btn').forEach(b => b.classList.toggle('active', b.dataset.view === v));
  $('monthView').classList.toggle('hidden', v !== 'month');
  $('weekView').classList.toggle('hidden', v !== 'week');
  $('dayView').classList.toggle('hidden', v !== 'day');
  if (v === 'week') renderWeek();
  if (v === 'day') renderDay();
}
