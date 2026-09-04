const API_BASE = "";

let currentUser = null;
let authHeader = "";
let allRequests = [];
let users = [];
let calendarState = {
  mode: "month",
  cursor: new Date()
};

const $ = (id) => document.getElementById(id);

function basicHeader(username, password) {
  return "Basic " + btoa(unescape(encodeURIComponent(`${username}:${password}`)));
}

function getAuthHeaders() {
  return authHeader ? { Authorization: authHeader } : {};
}

async function apiFetch(path, options = {}) {
  const headers = {
    ...getAuthHeaders(),
    ...(options.headers || {})
  };
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (response.status === 401) {
    clearSession();
    showLogin();
    throw new Error("Сессия завершена. Войдите снова.");
  }
  return response;
}

function clearSession() {
  currentUser = null;
  authHeader = "";
  sessionStorage.removeItem("crm_basic_auth");
  sessionStorage.removeItem("crm_user");
}

async function login(username, password, remember) {
  const header = basicHeader(username, password);
  const response = await fetch(`${API_BASE}/api/users`, {
    headers: { Authorization: header }
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error("Неверный логин или пароль");
    }
    throw new Error("Не удалось проверить вход: HTTP " + response.status);
  }

  const userList = await response.json();
  const matched = userList.find((user) => user.id === username);
  if (!matched) {
    throw new Error("Пользователь не найден");
  }

  currentUser = matched;
  authHeader = header;

  // Basic Auth credentials persist only for this browser session.
  if (remember) {
    sessionStorage.setItem("crm_basic_auth", authHeader);
    sessionStorage.setItem("crm_user", JSON.stringify(currentUser));
  }
}

async function tryAutoLogin() {
  const savedHeader = sessionStorage.getItem("crm_basic_auth");
  const savedUser = sessionStorage.getItem("crm_user");
  if (!savedHeader || !savedUser) return false;

  authHeader = savedHeader;
  try {
    const response = await apiFetch("/api/users");
    if (!response.ok) throw new Error();
    const userList = await response.json();
    const saved = JSON.parse(savedUser);
    currentUser = userList.find((user) => user.id === saved.id) || saved;
    return true;
  } catch {
    clearSession();
    return false;
  }
}

function logout() {
  clearSession();
  showLogin();
}

function showLogin() {
  $("login-view").classList.remove("hidden");
  $("main-view").classList.add("hidden");
  $("login-password").value = "";
}

async function showMain() {
  $("login-view").classList.add("hidden");
  $("main-view").classList.remove("hidden");
  $("user-display").textContent = currentUser?.name || currentUser?.id || "";
  await loadUsers();
  await loadRequests();
  switchTab("calendar");
}

function switchTab(tab) {
  document.querySelectorAll(".tab").forEach((item) => {
    item.classList.toggle("active", item.dataset.tab === tab);
  });
  document.querySelectorAll(".tab-content").forEach((item) => {
    item.classList.toggle("active", item.id === `${tab}-tab`);
  });
  if (tab === "calendar") renderCalendar();
  if (tab === "list") renderList();
}

async function loadUsers() {
  const response = await apiFetch("/api/users");
  if (!response.ok) throw new Error("Не удалось загрузить пользователей");
  users = await response.json();

  const select = $("req-assignee");
  select.innerHTML = "";
  users.forEach((user) => {
    const option = document.createElement("option");
    option.value = user.id;
    option.textContent = user.name || user.id;
    select.appendChild(option);
  });
}

async function loadRequests() {
  const response = await apiFetch("/api/requests");
  if (!response.ok) throw new Error("Не удалось загрузить заявки");
  allRequests = await response.json();
}

function parseDate(value) {
  if (!value) return new Date();
  return new Date(String(value).replace(" ", "T"));
}

function dateKey(value) {
  const date = parseDate(value);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function localDateKey(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function fmtDate(date) {
  return date.toLocaleDateString("ru-RU");
}

function fmtTime(date) {
  return date.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
}

function toLocalDateTimeValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hour = String(date.getHours()).padStart(2, "0");
  const minute = String(date.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day}T${hour}:${minute}`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function statusLabel(value) {
  return {
    new: "Новая",
    in_progress: "В работе",
    done: "Готово",
    cancelled: "Отмена"
  }[value] || value || "—";
}

function sourceLabel(value) {
  return {
    avito: "Авито",
    domovoy: "Домовые чаты",
    unknown: "Не указан"
  }[value] || value || "Не указан";
}

function contactLabel(value) {
  return {
    call: "Звонок",
    whatsapp: "WhatsApp",
    telegram: "Telegram",
    sms: "SMS"
  }[value] || "Не указан";
}

function userLabel(userId) {
  const user = users.find((item) => item.id === userId);
  return user?.name || userId || "—";
}

function startOfWeek(date) {
  const copy = new Date(date);
  const day = copy.getDay();
  copy.setDate(copy.getDate() - ((day + 6) % 7));
  copy.setHours(0, 0, 0, 0);
  return copy;
}

function addDays(date, amount) {
  const copy = new Date(date);
  copy.setDate(copy.getDate() + amount);
  return copy;
}

function addMonths(date, amount) {
  const copy = new Date(date);
  copy.setMonth(copy.getMonth() + amount);
  return copy;
}

function requestsForDay(date) {
  const key = localDateKey(date);
  return allRequests
    .filter((request) => dateKey(request.visit_date) === key)
    .sort((a, b) => parseDate(a.visit_date) - parseDate(b.visit_date));
}

function renderCalendar() {
  const { mode, cursor } = calendarState;
  $("cal-mode").value = mode;

  if (mode === "month") {
    $("cal-title").textContent = cursor.toLocaleDateString("ru-RU", {
      month: "long",
      year: "numeric"
    });
    renderMonth(cursor);
  } else if (mode === "week") {
    const start = startOfWeek(cursor);
    const finish = addDays(start, 6);
    $("cal-title").textContent = `${fmtDate(start)} — ${fmtDate(finish)}`;
    renderWeek(cursor);
  } else {
    $("cal-title").textContent = cursor.toLocaleDateString("ru-RU", {
      weekday: "long",
      day: "numeric",
      month: "long",
      year: "numeric"
    });
    renderDay(cursor);
  }
}

function renderMonth(cursor) {
  const grid = $("calendar-grid");
  grid.classList.remove("hidden");
  $("calendar-day-view").classList.add("hidden");
  grid.innerHTML = "";

  const weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];
  weekdays.forEach((day) => {
    const header = document.createElement("div");
    header.className = "cal-cell cal-weekday";
    header.textContent = day;
    grid.appendChild(header);
  });

  const first = new Date(cursor.getFullYear(), cursor.getMonth(), 1);
  const start = startOfWeek(first);
  const today = localDateKey(new Date());

  for (let index = 0; index < 42; index += 1) {
    const day = addDays(start, index);
    const cell = document.createElement("div");
    cell.className = "cal-cell";
    if (day.getMonth() !== cursor.getMonth()) cell.classList.add("other-month");
    if (localDateKey(day) === today) cell.classList.add("today");

    const label = document.createElement("div");
    label.className = "cal-date";
    label.textContent = day.getDate();
    cell.appendChild(label);

    requestsForDay(day).slice(0, 5).forEach((request) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "cal-chip";
      chip.textContent = `${fmtTime(parseDate(request.visit_date))} ${request.client}`;
      chip.title = `${request.client}: ${request.address}`;
      chip.addEventListener("click", (event) => {
        event.stopPropagation();
        openRequestModal(request.id);
      });
      cell.appendChild(chip);
    });

    const count = requestsForDay(day).length;
    if (count > 5) {
      const more = document.createElement("button");
      more.type = "button";
      more.className = "cal-chip";
      more.textContent = `Ещё: ${count - 5}`;
      more.addEventListener("click", () => {
        calendarState.cursor = day;
        calendarState.mode = "day";
        renderCalendar();
      });
      cell.appendChild(more);
    }

    cell.addEventListener("dblclick", () => {
      calendarState.cursor = day;
      openRequestModal();
    });
    grid.appendChild(cell);
  }
}

function renderWeek(cursor) {
  const grid = $("calendar-grid");
  grid.classList.remove("hidden");
  $("calendar-day-view").classList.add("hidden");
  grid.innerHTML = "";

  const start = startOfWeek(cursor);
  const today = localDateKey(new Date());
  for (let index = 0; index < 7; index += 1) {
    const day = addDays(start, index);
    const cell = document.createElement("div");
    cell.className = "cal-cell";
    if (localDateKey(day) === today) cell.classList.add("today");

    const label = document.createElement("div");
    label.className = "cal-date";
    label.textContent = day.toLocaleDateString("ru-RU", {
      weekday: "short",
      day: "numeric",
      month: "short"
    });
    cell.appendChild(label);

    requestsForDay(day).forEach((request) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "cal-chip";
      chip.textContent = `${fmtTime(parseDate(request.visit_date))} ${request.client}`;
      chip.addEventListener("click", () => openRequestModal(request.id));
      cell.appendChild(chip);
    });
    grid.appendChild(cell);
  }
}

function renderDay(cursor) {
  $("calendar-grid").classList.add("hidden");
  const container = $("calendar-day-view");
  container.classList.remove("hidden");
  container.innerHTML = "";

  const list = requestsForDay(cursor);
  if (list.length === 0) {
    container.textContent = "На этот день заявок нет.";
    return;
  }

  list.forEach((request) => {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "day-chip";
    row.innerHTML = `<span>${fmtTime(parseDate(request.visit_date))} — ${escapeHtml(request.client)}, ${escapeHtml(request.address)}</span><span>${escapeHtml(statusLabel(request.status))}</span>`;
    row.addEventListener("click", () => openRequestModal(request.id));
    container.appendChild(row);
  });
}

function renderList() {
  const scope = $("list-scope").value;
  const search = $("list-search").value.trim().toLowerCase();
  const status = $("list-status").value;
  const source = $("list-source").value;
  const contact = $("list-contact-method").value;

  $("list-range-inputs").classList.toggle("hidden", scope !== "range");

  let list = [...allRequests];
  if (scope === "selected") {
    const selected = localDateKey(calendarState.cursor);
    list = list.filter((request) => dateKey(request.visit_date) === selected);
  }
  if (scope === "range") {
    const from = $("list-from").value;
    const to = $("list-to").value;
    if (from) list = list.filter((request) => dateKey(request.visit_date) >= from);
    if (to) list = list.filter((request) => dateKey(request.visit_date) <= to);
  }
  if (search) {
    list = list.filter((request) => [request.client, request.address, request.phone]
      .some((value) => String(value || "").toLowerCase().includes(search)));
  }
  if (status) list = list.filter((request) => request.status === status);
  if (source) list = list.filter((request) => (request.source || "unknown") === source);
  if (contact) list = list.filter((request) => (request.contact_method || "") === contact);

  list.sort((a, b) => parseDate(a.visit_date) - parseDate(b.visit_date));
  const tbody = $("requests-tbody");
  tbody.innerHTML = "";

  list.forEach((request) => {
    const date = parseDate(request.visit_date);
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${fmtDate(date)} ${fmtTime(date)}</td>
      <td>${escapeHtml(request.client)}</td>
      <td>${escapeHtml(request.address)}</td>
      <td>${escapeHtml(request.phone)}</td>
      <td>${escapeHtml(statusLabel(request.status))}</td>
      <td>${escapeHtml(sourceLabel(request.source))}</td>
      <td>${escapeHtml(contactLabel(request.contact_method))}</td>
      <td>${escapeHtml(userLabel(request.assignee))}</td>
      <td>${Number(request.price || 0).toFixed(2)}</td>
      <td><button class="btn-ghost edit-btn" type="button">Изменить</button></td>
    `;
    row.querySelector(".edit-btn").addEventListener("click", () => openRequestModal(request.id));
    tbody.appendChild(row);
  });
}

async function runReport() {
  const dateFrom = $("report-from").value;
  const dateTo = $("report-to").value;
  const groupBy = $("report-group-by").value;

  if (!dateFrom || !dateTo) {
    alert("Укажите дату начала и дату окончания.");
    return;
  }

  const params = new URLSearchParams({ date_from: dateFrom, date_to: dateTo });
  const response = await apiFetch(`/api/report?${params.toString()}`);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Не удалось сформировать отчёт");
  }
  const report = await response.json();
  renderReport(report, groupBy);
}

function renderReport(report, groupBy) {
  const summary = $("report-summary");
  const totalRequests = Number(report.total_requests ?? report.total ?? 0);
  const totalPrice = Number(report.total_price ?? report.total_amount ?? report.amount ?? 0);
  summary.textContent = `Заявок: ${totalRequests}. Сумма: ${totalPrice.toFixed(2)}.`;

  const output = $("report-table");
  output.innerHTML = "";

  const rows = Array.isArray(report.rows) ? report.rows : [];
  if (rows.length === 0) {
    output.textContent = "За выбранный период данных нет.";
    return;
  }

  const table = document.createElement("table");
  table.innerHTML = `<thead><tr><th>${groupBy === "source" ? "Источник" : groupBy === "contact_method" ? "Способ связи" : "Дата"}</th><th>Заявок</th><th>Сумма</th></tr></thead><tbody></tbody>`;
  const body = table.querySelector("tbody");

  rows.forEach((row) => {
    const key = row.key ?? row.date ?? row.source ?? row.contact_method ?? "—";
    let label = key;
    if (groupBy === "source") label = sourceLabel(key);
    if (groupBy === "contact_method") label = contactLabel(key);
    const count = Number(row.count ?? row.requests ?? 0);
    const sum = Number(row.sum ?? row.total_price ?? row.amount ?? 0);
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${escapeHtml(label)}</td><td>${count}</td><td>${sum.toFixed(2)}</td>`;
    body.appendChild(tr);
  });
  output.appendChild(table);
}

function openRequestModal(id = null) {
  const modal = $("request-modal");
  const request = id ? allRequests.find((item) => String(item.id) === String(id)) : null;

  $("req-id").value = request?.id || "";
  $("request-modal-title").textContent = request ? "Редактирование заявки" : "Новая заявка";
  $("req-delete-btn").classList.toggle("hidden", !request);

  if (request) {
    $("req-client").value = request.client || "";
    $("req-address").value = request.address || "";
    $("req-phone").value = request.phone || "";
    $("req-date").value = toLocalDateTimeValue(parseDate(request.visit_date));
    $("req-status").value = request.status || "new";
    $("req-assignee").value = request.assignee || currentUser?.id || "";
    $("req-source").value = request.source || "unknown";
    $("req-contact-method").value = request.contact_method || "";
    $("req-price").value = Number(request.price || 0);
    $("req-comment").value = request.comment || "";
  } else {
    const defaultDate = new Date(calendarState.cursor);
    defaultDate.setHours(new Date().getHours(), new Date().getMinutes(), 0, 0);
    $("req-client").value = "";
    $("req-address").value = "";
    $("req-phone").value = "";
    $("req-date").value = toLocalDateTimeValue(defaultDate);
    $("req-status").value = "new";
    $("req-assignee").value = currentUser?.id || users[0]?.id || "";
    $("req-source").value = "avito";
    $("req-contact-method").value = "";
    $("req-price").value = "0";
    $("req-comment").value = "";
  }
  modal.classList.remove("hidden");
}

function closeRequestModal() {
  $("request-modal").classList.add("hidden");
}

async function saveRequest(event) {
  event.preventDefault();
  const id = $("req-id").value;
  const payload = {
    client: $("req-client").value.trim(),
    visit_date: $("req-date").value,
    address: $("req-address").value.trim(),
    phone: $("req-phone").value.trim(),
    status: $("req-status").value,
    assignee: $("req-assignee").value,
    source: $("req-source").value,
    contact_method: $("req-contact-method").value,
    price: Number($("req-price").value || 0),
    comment: $("req-comment").value.trim()
  };

  if (!payload.client || !payload.visit_date || !payload.address || !payload.phone || !payload.assignee) {
    alert("Заполните обязательные поля.");
    return;
  }

  const path = id ? `/api/requests/${encodeURIComponent(id)}` : "/api/requests";
  const method = id ? "PUT" : "POST";
  const response = await apiFetch(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Не удалось сохранить заявку");
  }

  await loadRequests();
  closeRequestModal();
  renderCalendar();
  renderList();
}

function confirmModal(title, message) {
  return new Promise((resolve) => {
    const modal = $("confirm-modal");
    $("confirm-title").textContent = title;
    $("confirm-message").textContent = message;
    modal.classList.remove("hidden");

    const finish = (result) => {
      modal.classList.add("hidden");
      $("confirm-ok").onclick = null;
      $("confirm-cancel").onclick = null;
      $("confirm-close").onclick = null;
      modal.querySelector(".modal-backdrop").onclick = null;
      resolve(result);
    };
    $("confirm-ok").onclick = () => finish(true);
    $("confirm-cancel").onclick = () => finish(false);
    $("confirm-close").onclick = () => finish(false);
    modal.querySelector(".modal-backdrop").onclick = () => finish(false);
  });
}

async function deleteRequest() {
  const id = $("req-id").value;
  if (!id) return;
  const approved = await confirmModal("Удалить заявку?", "Это действие нельзя отменить.");
  if (!approved) return;

  const response = await apiFetch(`/api/requests/${encodeURIComponent(id)}`, { method: "DELETE" });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Не удалось удалить заявку");
  }
  await loadRequests();
  closeRequestModal();
  renderCalendar();
  renderList();
}

async function refreshRequests() {
  await loadRequests();
  renderCalendar();
  renderList();
}

function configureTheme() {
  const saved = localStorage.getItem("crm_theme") || "dark";
  document.body.classList.toggle("light", saved === "light");
  $("theme-toggle").textContent = saved === "light" ? "☀️" : "🌙";
  $("theme-toggle").addEventListener("click", () => {
    const light = document.body.classList.toggle("light");
    localStorage.setItem("crm_theme", light ? "light" : "dark");
    $("theme-toggle").textContent = light ? "☀️" : "🌙";
  });
}

async function init() {
  configureTheme();

  $("login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const username = $("login-username").value.trim();
    const password = $("login-password").value;
    const remember = $("login-remember").checked;
    try {
      await login(username, password, remember);
      await showMain();
    } catch (error) {
      alert(error.message || "Не удалось выполнить вход");
    }
  });

  $("logout-btn").addEventListener("click", logout);
  document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => switchTab(tab.dataset.tab)));

  $("cal-prev").addEventListener("click", () => {
    if (calendarState.mode === "month") calendarState.cursor = addMonths(calendarState.cursor, -1);
    else if (calendarState.mode === "week") calendarState.cursor = addDays(calendarState.cursor, -7);
    else calendarState.cursor = addDays(calendarState.cursor, -1);
    renderCalendar();
  });
  $("cal-next").addEventListener("click", () => {
    if (calendarState.mode === "month") calendarState.cursor = addMonths(calendarState.cursor, 1);
    else if (calendarState.mode === "week") calendarState.cursor = addDays(calendarState.cursor, 7);
    else calendarState.cursor = addDays(calendarState.cursor, 1);
    renderCalendar();
  });
  $("cal-today").addEventListener("click", () => {
    calendarState.cursor = new Date();
    renderCalendar();
  });
  $("cal-mode").addEventListener("change", (event) => {
    calendarState.mode = event.target.value;
    renderCalendar();
  });
  $("add-request-btn").addEventListener("click", () => openRequestModal());

  ["list-scope", "list-from", "list-to", "list-search", "list-status", "list-source", "list-contact-method"].forEach((id) => {
    $(id).addEventListener(id === "list-search" ? "input" : "change", renderList);
  });
  $("list-refresh").addEventListener("click", () => refreshRequests().catch((error) => alert(error.message)));

  $("report-run").addEventListener("click", () => runReport().catch((error) => alert(error.message)));

  $("request-modal-close").addEventListener("click", closeRequestModal);
  $("req-cancel-btn").addEventListener("click", closeRequestModal);
  $("request-modal").querySelector(".modal-backdrop").addEventListener("click", closeRequestModal);
  $("request-form").addEventListener("submit", (event) => saveRequest(event).catch((error) => alert(error.message)));
  $("req-delete-btn").addEventListener("click", () => deleteRequest().catch((error) => alert(error.message)));

  const date = new Date();
  $("report-from").value = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-01`;
  $("report-to").value = localDateKey(date);

  if (await tryAutoLogin()) {
    try {
      await showMain();
    } catch (error) {
      clearSession();
      showLogin();
    }
  } else {
    showLogin();
  }
}

init();
