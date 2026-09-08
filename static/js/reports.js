import { $, money, dt, esc } from './utils.js';
import { STATUSES, SOURCE_LABELS } from './constants.js';
import { api } from './api.js';
import { openModal, closeModal } from './ui.js';

export async function openReport() {
  const today = new Date().toISOString().slice(0, 10);
  const start = new Date(); start.setDate(1);
  $('reportDateFrom').value = start.toISOString().slice(0, 10);
  $('reportDateTo').value = today;
  $('reportSummary').innerHTML = '';
  $('reportTable').classList.add('hidden');
  openModal('reportModal');
}

export async function loadReport() {
  const from = $('reportDateFrom').value, to = $('reportDateTo').value;
  if (!from || !to) { alert('Выбери даты периода'); return; }
  try {
    const data = await api(`/api/report?date_from=${from}&date_to=${to}`);
    $('reportSummary').innerHTML = `<div><b>Период:</b> ${from} – ${to}</div><div><b>Всего заявок:</b> ${data.total}</div><div><b>Активные:</b> ${data.active}</div><div><b>Завершённые:</b> ${data.completed}</div><div><b>Отменённые:</b> ${data.cancelled}</div><div><b>Выручка:</b> ${money(data.revenue)}</div>`;
    const tb = $('reportTable').querySelector('tbody');
    tb.innerHTML = Object.entries(data.by_source).map(([k, v]) => `<tr><td>${v.label}</td><td class="num">${v.total}</td><td class="num">${v.completed}</td><td class="num">${money(v.revenue)}</td></tr>`).join('');
    $('reportTable').classList.remove('hidden');
  } catch (e) { alert('Не удалось загрузить отчёт: ' + e.message); }
}

export async function openAnalytics() {
  try {
    const data = await api('/api/analytics/summary');
    let html = `<div style="display:grid;gap:16px"><div><b>Общая статистика</b><div class="meta"><div>Всего заявок: <b>${data.total}</b></div><div>Активные: <b>${data.active}</b></div><div>Завершённые: <b>${data.completed}</b></div><div>Выручка: <b>${money(data.revenue)}</b></div></div></div><div><b>По статусам</b><div class="meta">${Object.entries(data.by_status).map(([k, v]) => `<div>${STATUSES[k] || k}: <b>${v.count}</b> (${money(v.revenue)})</div>`).join('')}</div></div><div><b>По источникам</b><div class="meta">${Object.entries(data.by_source).map(([k, v]) => `<div>${SOURCE_LABELS[k] || k}: <b>${v.count}</b> (${money(v.revenue)})</div>`).join('')}</div></div>`;
    if (data.masters_ranking && data.masters_ranking.length > 0) {
      html += `<div><b>Рейтинг мастеров</b><div class="meta">${data.masters_ranking.map((m, i) => `<div>${i + 1}. ${esc(m.name)}: <b>${m.count}</b> заявок (${money(m.revenue)})</div>`).join('')}</div></div>`;
    }
    html += `<div><b>Топ клиентов</b><div class="meta">${data.top_clients.map((c, i) => `<div>${i + 1}. ${esc(c.client)}: <b>${c.count}</b> заявок (${money(c.revenue)})</div>`).join('')}</div></div></div>`;
    $('analyticsContent').innerHTML = html;
    openModal('analyticsModal');
  } catch (e) { alert('Не удалось загрузить аналитику: ' + e.message); }
}
