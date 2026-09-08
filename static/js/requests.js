import { S } from './state.js';
import { $, esc, dateKey, dt, money, labelDate } from './utils.js';
import { STATUSES, SOURCE_LABELS, CONTACT_METHOD_LABELS } from './constants.js';
import { api } from './api.js';
import { openModal, closeModal } from './ui.js';
import { renderCalendar, renderWeek, renderDay } from './calendar.js';

const PENDING_CALC_KEY = 'master_crm_pending_calc';
let calculationItems = null;
let viewingRequestId = null;

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
  $('requests').innerHTML = rows.length ? rows.map(x => `<article class="request request-clickable" role="button" tabindex="0" onclick="window.openRequestView(${x.id})" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();window.openRequestView(${x.id})}"><div class="row"><div><div class="name">${esc(x.client)}</div><div class="muted">${dt(x.visit_date)}</div></div><span class="badge s-${x.status}">${STATUSES[x.status]}</span></div><div class="meta"><div>📍 ${esc(x.address)}</div><div>📞 <a href="tel:${esc(x.phone)}" onclick="event.stopPropagation()">${esc(x.phone)}</a></div><div>👤 ${esc(x.assignee_name || x.assignee)}</div><div>💰 ${money(x.price)}</div>${x.source && x.source !== 'unknown' ? `<div>📥 ${SOURCE_LABELS[x.source] || x.source}</div>` : ''}${x.contact_method ? `<div>📞 ${CONTACT_METHOD_LABELS[x.contact_method] || x.contact_method}</div>` : ''}${x.comment ? `<div>📝 ${esc(x.comment)}</div>` : ''}</div><div class="two"><button class="btn btn-secondary" onclick="event.stopPropagation();window.editRequest(${x.id})">Изменить</button><button class="btn btn-danger" onclick="event.stopPropagation();window.removeRequest(${x.id})">Удалить</button></div></article>`).join('') : '<div class="empty">На выбранный день заявок нет.</div>';
}

function normalizeCalculationItem(item) {
  return { price_item_id: item.price_item_id ?? null, category_name: item.category_name ?? item.category_name_snapshot ?? '', name: item.name ?? item.name_snapshot ?? '', unit: item.unit ?? item.unit_snapshot ?? 'шт', unit_price: Number(item.unit_price) || 0, quantity: Number(item.quantity) || 1 };
}
function calculationTotal() { return (calculationItems || []).reduce((total, item) => total + Number(item.unit_price || 0) * Number(item.quantity || 0), 0); }
function setCalculationItems(items) { calculationItems = Array.isArray(items) ? items.map(normalizeCalculationItem) : null; renderCalculationItems(); }
function clearCalculationItems() { calculationItems = null; renderCalculationItems(); }
function renderCalculationItems() {
  const block = $('calculationItemsBlock'), list = $('calculationItemsList'), total = $('calculationItemsTotal');
  if (!calculationItems) { block.classList.add('hidden'); list.innerHTML = ''; total.textContent = ''; return; }
  block.classList.remove('hidden');
  if (!calculationItems.length) { list.innerHTML = '<div class="calculation-empty">Состав работ пуст. Добавьте позиции через страницу «Калькуляция».</div>'; total.textContent = ''; return; }
  list.innerHTML = calculationItems.map((item, index) => { const lineTotal = Number(item.unit_price || 0) * Number(item.quantity || 0); return `<div class="calculation-item"><div class="calculation-item-info"><div class="calculation-item-name">${esc(item.name)}</div><div class="calculation-item-meta">${item.category_name ? esc(item.category_name) + ' · ' : ''}${esc(item.unit)}</div></div><input type="number" min="0.01" step="0.01" value="${item.quantity}" aria-label="Количество ${esc(item.name)}" onchange="window.updateCalculationQuantity(${index}, this.value)"><input type="number" min="0" step="1" value="${item.unit_price}" aria-label="Цена ${esc(item.name)}" onchange="window.updateCalculationPrice(${index}, this.value)"><button type="button" class="btn btn-danger calculation-item-remove" onclick="window.removeCalculationItem(${index})">Удалить</button><div class="calculation-item-meta">${money(lineTotal)}</div></div>`; }).join('');
  total.textContent = 'Итого по составу: ' + money(calculationTotal());
}
function renderViewCalculationItems(items) {
  const list = $('viewCalculationList'), total = $('viewCalculationTotal');
  const normalized = Array.isArray(items) ? items.map(normalizeCalculationItem) : [];
  if (!normalized.length) { list.innerHTML = '<div class="calculation-empty">Состав работ не указан.</div>'; total.textContent = ''; return; }
  list.innerHTML = normalized.map(item => { const lineTotal = Number(item.unit_price || 0) * Number(item.quantity || 0); return `<div class="calculation-item calculation-item-readonly"><div class="calculation-item-info"><div class="calculation-item-name">${esc(item.name)}</div><div class="calculation-item-meta">${item.category_name ? esc(item.category_name) + ' · ' : ''}${esc(item.unit)}</div></div><div class="calculation-item-meta">${item.quantity} × ${money(item.unit_price)}</div><div class="calculation-item-meta">${money(lineTotal)}</div></div>`; }).join('');
  total.textContent = 'Итого по составу: ' + money(normalized.reduce((sum, item) => sum + Number(item.unit_price || 0) * Number(item.quantity || 0), 0));
}
function updateCalculationQuantity(index, value) { if (!calculationItems || !calculationItems[index]) return; const quantity = Number(String(value).replace(',', '.')); if (Number.isFinite(quantity) && quantity > 0) calculationItems[index].quantity = quantity; renderCalculationItems(); $('price').value = Math.round(calculationTotal()); }
function updateCalculationPrice(index, value) { if (!calculationItems || !calculationItems[index]) return; const unitPrice = Number(String(value).replace(',', '.')); calculationItems[index].unit_price = Number.isFinite(unitPrice) && unitPrice >= 0 ? unitPrice : 0; renderCalculationItems(); $('price').value = Math.round(calculationTotal()); }
function removeCalculationItem(index) { if (!calculationItems) return; calculationItems.splice(index, 1); renderCalculationItems(); $('price').value = Math.round(calculationTotal()); }
function applyPendingCalculation() {
  try { const raw = sessionStorage.getItem(PENDING_CALC_KEY); if (!raw) return false; const pending = JSON.parse(raw); if (!Array.isArray(pending.items) || !pending.items.length) return false; setCalculationItems(pending.items); $('price').value = Math.round(Number(pending.total) || calculationTotal()); sessionStorage.removeItem(PENDING_CALC_KEY); return true; } catch (e) { sessionStorage.removeItem(PENDING_CALC_KEY); return false; }
}

export function clearRequest() {
  $('requestForm').reset(); $('requestId').value = ''; $('requestFormTitle').textContent = 'Новая заявка';
  $('requestStatus').value = 'new'; $('price').value = '0'; $('source').value = 'avito'; $('contactMethod').value = '';
  const d = new Date(S.selected + 'T10:00:00'); $('visitDate').value = d.toISOString().slice(0, 16);
  if (S.auth) $('assignee').value = S.auth.user;
  clearCalculationItems(); applyPendingCalculation();
}
export function newRequest() { clearRequest(); openModal('requestModal'); }
export async function openRequestView(id) {
  const x = S.items.find(i => i.id === id); if (!x) return;
  viewingRequestId = id;
  $('viewClient').textContent = x.client || 'Заявка';
  $('viewStatus').textContent = STATUSES[x.status] || x.status || '—';
  $('viewStatus').className = 'badge s-' + (x.status || 'new');
  $('viewVisitDate').textContent = dt(x.visit_date);
  $('viewAddress').textContent = x.address || '—';
  $('viewPhone').textContent = x.phone || '—'; $('viewPhone').href = x.phone ? 'tel:' + x.phone : 'tel:';
  $('viewAssignee').textContent = x.assignee_name || x.assignee || '—';
  $('viewPrice').textContent = money(x.price);
  $('viewSource').textContent = SOURCE_LABELS[x.source] || (x.source === 'unknown' ? 'Не указан' : x.source || 'Не указан');
  $('viewContactMethod').textContent = CONTACT_METHOD_LABELS[x.contact_method] || (x.contact_method || 'Не указан');
  $('viewComment').textContent = x.comment || '—';
  renderViewCalculationItems([]);
  openModal('requestViewModal');
  try { const request = await api('/api/requests/' + id); renderViewCalculationItems(request.items || []); } catch (e) { $('viewCalculationList').innerHTML = '<div class="calculation-empty">Не удалось загрузить состав работ.</div>'; $('viewCalculationTotal').textContent = ''; }
}
export function editViewedRequest() { if (viewingRequestId !== null) { closeModal('requestViewModal'); editRequest(viewingRequestId); } }
export function removeViewedRequest() { if (viewingRequestId !== null) { const id = viewingRequestId; closeModal('requestViewModal'); removeRequest(id); } }
export async function editRequest(id) {
  const x = S.items.find(i => i.id === id); if (!x) return;
  $('requestFormTitle').textContent = 'Редактирование заявки'; $('requestId').value = x.id;
  $('client').value = x.client; $('visitDate').value = x.visit_date.slice(0, 16); $('address').value = x.address; $('phone').value = x.phone; $('requestStatus').value = x.status;
  $('price').value = x.price; $('assignee').value = x.assignee; $('comment').value = x.comment || ''; $('source').value = x.source || 'unknown'; $('contactMethod').value = x.contact_method || '';
  clearCalculationItems(); openModal('requestModal');
  try { const request = await api('/api/requests/' + id); setCalculationItems(request.items || []); } catch (e) { alert('Не удалось загрузить состав работ: ' + e.message); }
}
export async function removeRequest(id) {
  if (!confirm('Удалить заявку?')) return;
  try { await api('/api/requests/' + id, { method: 'DELETE' }); await loadRequests(); if (S.view === 'week') renderWeek(); if (S.view === 'day') renderDay(); } catch (e) { alert(e.message); }
}
export async function saveRequest(e) {
  e.preventDefault();
  const p = { client: $('client').value.trim(), visit_date: $('visitDate').value, address: $('address').value.trim(), phone: $('phone').value.trim(), status: $('requestStatus').value, price: Number($('price').value || 0), comment: $('comment').value.trim(), assignee: $('assignee').value, source: $('source').value, contact_method: $('contactMethod').value };
  if (calculationItems !== null) { p.items = calculationItems.map(normalizeCalculationItem); const total = calculationTotal(); if (Math.abs(total - p.price) > 1) { p.price = Math.round(total * 100) / 100; $('price').value = p.price; } }
  try {
    const id = $('requestId').value;
    await api(id ? '/api/requests/' + id : '/api/requests', { method: id ? 'PUT' : 'POST', body: JSON.stringify(p) });
    S.selected = p.visit_date.slice(0, 10); $('dateFilter').value = S.selected; closeModal('requestModal'); clearCalculationItems(); await loadRequests(); if (S.view === 'week') renderWeek(); if (S.view === 'day') renderDay();
  } catch (e) { alert('Не удалось сохранить: ' + e.message); }
}
export async function loadRequests() {
  S.items = await api('/api/requests'); if (typeof window.renderStats === 'function') window.renderStats(); if (typeof window.renderCalendar === 'function') window.renderCalendar(); renderRequests();
}
window.updateCalculationQuantity = updateCalculationQuantity;
window.updateCalculationPrice = updateCalculationPrice;
window.removeCalculationItem = removeCalculationItem;
window.openRequestView = openRequestView;
