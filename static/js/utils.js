export function $(id) { return document.getElementById(id); }
export function esc(v) { return String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
export function dateKey(v) { return String(v).slice(0, 10); }
export function localDateKey(date) { return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`; }
export function money(v) { return new Intl.NumberFormat('ru-RU').format(Number(v || 0)) + ' ₽'; }
export function dt(v) { return new Intl.DateTimeFormat('ru-RU', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(v)); }
export function labelDate(v) { return new Intl.DateTimeFormat('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date(v + 'T00:00:00')); }
export function getWeekStart(d) { const date = new Date(d), day = (date.getDay() + 6) % 7; date.setDate(date.getDate() - day); return date; }
