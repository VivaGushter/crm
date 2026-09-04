const API_BASE = "";
let currentUser = null;
let allRequests = [];
let users = [];
let calendarState = {
  mode: "month",
  cursor: new Date()
};

const $ = (id) => document.getElementById(id);

// ---------- AUTH ----------

async function tryAutoLogin() {
  const saved = localStorage.getItem("crm_user");
  const token = localStorage.getItem("crm_token");
  if (!saved || !token) return false;
  try {
    const res = await fetch(`${API_BASE}/api/me`, {
      headers: { "Authorization": `Bearer ${token}` }
    });
    if (!res.ok) throw new Error();
    const data = await res.json();
    currentUser = data;
    localStorage.setItem("crm_user", JSON.stringify(data));
    return true;
  } catch {
    localStorage.removeItem("crm_user");
    localStorage.removeItem("crm_token");
    return false;
  }
}

async function login(username, password, remember) {
  const res = await fetch(`${API_BASE}/api/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Неверный логин или пароль");
  }
  const data = await res.json();
  currentUser = data.user;
  const token = data.token;
  if (remember) {
    localStorage.setItem("crm_user", JSON.stringify(currentUser));
    localStorage.setItem("crm_token", token);
  } else {
    sessionStorage.setItem("crm_user", JSON.stringify(currentUser));
    sessionStorage.setItem("crm_token", token);
  }
}

function logout() {
  localStorage.removeItem("crm_user");
  localStorage.removeItem("crm_token");
  sessionStorage.removeItem("crm_user");
  sessionStorage.removeItem("crm_token");
  currentUser = null;
  showLogin();
}

function getAuthHeaders() {
  const token = localStorage.getItem("crm_token") || sessionStorage.getItem("crm_token");
  return { "Authorization": `Bearer ${token}` };
}

// ---------- VIEW SWITCH ----------

function showLogin() {
  $("login-view").classList.remove("hidden");
  $("main-view").classList.add("hidden");
}

function showMain() {
  $("login-view").classList.add("hidden");
  $("main-view").classList.remove("hidden");
  $("user-display").textContent = currentUser?.name || "";
  loadUsers();
  switchTab("calendar");
}

// ---------- TABS ----------

function switchTab(tab) {
  document.querySelectorAll(".tab").forEach(t => {
    t.classList.toggle("active", t.dataset.tab === tab);
  });
  document.querySelectorAll(".tab-content").forEach(c => {
    c.classList.toggle("active", c.id === `${tab}-tab`);
  });
  if (tab === "calendar") renderCalendar();
  if (tab === "list") renderList();
  if (tab === "report") {}
}

// ---------- USERS ----------

async function loadUsers() {
  const res = await fetch(`${API_BASE}/api/users`, { headers: getAuthHeaders() });
  if (!res.ok) return;
  users = await res.json();
  const sel = $("req-assignee");
  sel.innerHTML = "";
  users.forEach(u => {
    const opt = document.createElement("option");
    opt.value = u.id;
    opt.textContent = u.name;
    sel.appendChild(opt);
  });
}

// ---------- REQUESTS ----------

async function loadRequests() {
  const res = await fetch(`${API_BASE}/api/requests`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error("Не удалось загрузить заявки");
  allRequests = await res.json();
}

function parseDate(str) {
  // str: "YYYY-MM-DDTHH:MM" or "YYYY-MM-DD HH:MM"
  return new Date(str.replace(" ", "T"));
}

function fmtDate(d) {
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const yyyy = d.getFullYear();
  return `${dd}.${mm}.${yyyy}`;
}

function fmtTime(d) {
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  return `${hh}:${mi}`;
}

function statusLabel(s) {
  return {
    new: "Новая",
    in_progress: "В работе",
    done: "Готово",
    cancelled: "Отмена"
  }[s] || s;
}

function sourceLabel(s) {
  return {
    avito: "Авито",
    domovoy: "Домовые чаты",
    unknown: "Не указан"
  }[s] || s;
}

function contactLabel(c) {
  return {
    call: "Звонок",
    whatsapp: "WhatsApp",
    telegram: "Telegram",
    sms: "SMS",
    "": "Не указан"
  }[c] || c || "Не указан";
}

// ---------- CALENDAR ----------

function startOfMonth(d) {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}

function addMonths(d, n) {
  return new Date(d.getFullYear(), d.getMonth() + n, 1);
}

function startOfWeek(d) {
  const day = d.getDay(); // 0 Sun
  const diff = (day + 6) % 7; // make Monday 0
  const res = new Date(d);
  res.setDate(d.getDate() - diff);
  res.setHours(0, 0, 0, 0);
  return res;
}

function addDays(d, n) {
  const res = new Date(d);
  res.setDate(d.getDate() + n);
  return res;
}

function renderCalendar() {
  const mode = calendarState.mode;
  const cursor = calendarState.cursor;
  $("cal-title").textContent = cursor.toLocaleString("ru", { month: "long", year: "numeric" });
  $("cal-mode").value = mode;

  if (mode === "month") renderMonthGrid(cursor);
  else if (mode === "week") renderWeekView(cursor);
  else if (mode === "day") renderDayView(cursor);
}

function renderMonthGrid(cursor) {
  const grid = $("calendar-grid");
  grid.classList.remove("hidden");
  $("calendar-day-view").classList.add("hidden");
  grid.innerHTML = "";

  const first = startOfMonth(cursor);
  const start = startOfWeek(first);
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  for (let i = 0; i < 42; i++) {
    const cellDate = addDays(start, i);
    const cell = document.createElement("div");
    cell.className = "cal-cell";
    if (cellDate.getMonth() !== cursor.getMonth()) cell.classList.add("other-month");
    if (cellDate.getTime() === today.getTime()) cell.classList.add("today");

    const dateLabel = document.createElement("div");
    dateLabel.className = "cal-date";
    dateLabel.textContent = cellDate.getDate();
    cell.appendChild(dateLabel);

    const dayReqs = allRequests.filter(r => {
      const d = parseDate(r.visit_date);
      return d.toDateString() === cellDate.toDateString();
    });

    dayReqs.slice(0, 6).forEach(r => {
      const chip = document.createElement("div");
      chip.className = "cal-chip";
      chip.textContent = `${fmtTime(parseDate(r.visit_date))} ${r.client}`;
      chip.title = `${r.client}, ${r.address}`;
      chip.addEventListener("click", () => openRequestModal(r.id));
      cell.appendChild(chip);
    });

    if (dayReqs.length > 6) {
      const more = document.createElement("div");
      more.className = "cal-chip";
      more.textContent = `+${dayReqs.length - 6} ещё`;
      cell.appendChild(more);
    }

    grid.appendChild(cell);
  }
}

function renderWeekView(cursor) {
  const grid = $("calendar-grid");
  grid.classList.remove("hidden");
  $("calendar-day-view").classList.add("hidden");
  grid.innerHTML = "";

  const start = startOfWeek(cursor);
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  for (let i = 0; i < 7; i++) {
    const cellDate = addDays(start, i);
    const cell = document.createElement("div");
    cell.className = "cal-cell";
    if (cellDate.getTime() === today.getTime()) cell.classList.add("today");

    const dateLabel = document.createElement("div");
    dateLabel.className = "cal-date";
    dateLabel.textContent = `${cellDate.getDate()} ${cellDate.toLocaleString("ru", { weekday: "short" })}`;
    cell.appendChild(dateLabel);

    const dayReqs = allRequests.filter(r => {
      const d = parseDate(r.visit_date);
      return d.toDateString() === cellDate.toDateString();
    });

    dayReqs.slice(0, 8).forEach(r => {
      const chip = document.createElement("div");
      chip.className = "cal-chip";
      chip.textContent = `${fmtTime(parseDate(r.visit_date))} ${r.client}`;
      chip.title = `${r.client}, ${r.address}`;
      chip.addEventListener("click", () => openRequestModal(r.id));
      cell.appendChild(chip);
    });

    grid.appendChild(cell);
  }
}

function renderDayView(cursor) {
  $("calendar-grid").classList.add("hidden");
  const dayView = $("calendar-day-view");
  dayView.classList.remove("hidden");
  dayView.innerHTML = "";

  const dayReqs = allRequests.filter(r => {
    const d = parseDate(r.visit_date);
    return d.toDateString() === cursor.toDateString();
  });

  dayReqs.sort((a, b) => parseDate(a.visit_date) - parseDate(b.visit_date));

  dayReqs.forEach(r => {
    const row = document.createElement("div");
    row.className = "day-chip";
    const left = document.createElement("div");
    left.textContent = `${fmtTime(parseDate(r.visit_date))} — ${r.client}, ${r.address}`;
    const right = document.createElement("div");
    right.textContent = statusLabel(r.status);
    row.appendChild(left);
    row.appendChild(right);
    row.addEventListener("click", () => openRequestModal(r.id));
    dayView.appendChild(row);
  });
}

// ---------- LIST ----------

function renderList() {
  const scope = $("list-scope").value;
  const search = $("list-search").value.trim().toLowerCase();
  const status = $("list-status").value;
  const source = $("list-source").value;
  const contact = $("list-contact-method").value;

  let from = null, to = null;
  if (scope === "selected") {
    const d = calendarState.cursor;
    from = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    to = new Date(d);
    to.setDate(d.getDate() + 1);
  } else if (scope === "range") {
    const f = $("list-from").value;
    const t = $("list-to").value;
    if (f && t) {
      from = new Date(f);
      to = new Date(t);
      to.setDate(to.getDate() + 1);
    }
  }

  let list = allRequests.slice();

  if (from && to) {
    list = list.filter(r => {
      const d = parseDate(r.visit_date);
      return d >= from && d < to;
    });
  }

  if (search) {
    list = list.filter(r =>
      r.client.toLowerCase().includes(search) ||
      r.address.toLowerCase().includes(search) ||
      r.phone.toLowerCase().includes(search)
    );
  }

  if (status) list = list.filter(r => r.status === status);
  if (source) list = list.filter(r => r.source === source);
  if (contact !== null && contact !== undefined && contact !== "") {
    list = list.filter(r => (r.contact_method || "") === contact);
  }

  const tbody = $("requests-tbody");
  tbody.innerHTML = "";

  list.sort((a, b) => parseDate(a.visit_date) - parseDate(b.visit_date));

  list.forEach(r => {
    const tr = document.createElement("tr");
    const d = parseDate(r.visit_date);
    const assigneeName = users.find(u => u.id === r.assignee)?.name || r.assignee;

    tr.innerHTML = `
      <td>${fmtDate(d)} ${fmtTime(d)}</td>
      <td>${escapeHtml(r.client)}</td>
      <td>${escapeHtml(r.address)}</td>
      <td>${escapeHtml(r.phone)}</td>
      <td>${statusLabel(r.status)}</td>
      <td>${sourceLabel(r.source)}</td>
      <td>${contactLabel(r.contact_method)}</td>
      <td>${escapeHtml(assigneeName)}</td>
      <td>${r.price ? r.price.toFixed(2) : "0.00"}</td>
      <td><button class="btn-ghost edit-btn">✏️</button></td>
    `;

    tr.querySelector(".edit-btn").addEventListener("click", () => openRequestModal(r.id));
    tbody.appendChild(tr);
  });
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ---------- REPORT ----------

async function runReport() {
  const from = $("report-from").value;
  const to = $("report-to").value;
  const groupBy = $("report-group-by").value;

  if (!from || !to) {
    alert("Укажите период");
    return;
  }

  const params = new URLSearchParams({ from, to, group_by: groupBy });
  const res = await fetch(`${API_BASE}/api/report?${params}`, { headers: getAuthHeaders() });
  if (!res.ok) {
    alert("Ошибка при формировании отчёта");
    return;
  }
  const data = await res.json();

  const sum = $("report-summary");
  sum.textContent = `Заявок: ${data.total_requests}, Сумма: ${data.total_price.toFixed(2)}`;

  const tableDiv = $("report-table");
  tableDiv.innerHTML = "";

  const table = document.createElement("table");
  table.innerHTML = `
    <thead>
      <tr>
        <th>${groupBy === "date" ? "Дата" : groupBy === "source" ? "Источник" : "Способ связи"}</th>
        <th>Заявок</th>
        <th>Сумма</th>
      </tr>
    </thead>
    <tbody></tbody>
  `;
  const tbody = table.querySelector("tbody");

  data.rows.forEach(row => {
    const tr = document.createElement("tr");
    let label = row.key;
    if (groupBy === "source") label = sourceLabel(row.key);
    if (groupBy === "contact_method") label = contactLabel(row.key);
    tr.innerHTML = `
      <td>${escapeHtml(label)}</td>
      <td>${row.count}</td>
      <td>${row.sum.toFixed(2)}</td>
    `;
    tbody.appendChild(tr);
  });

  tableDiv.appendChild(table);
}

// ---------- MODAL: REQUEST ----------

function openRequestModal(id = null) {
  const modal = $("request-modal");
  modal.classList.remove("hidden");
  $("req-id").value = id || "";
  $("req-delete-btn").classList.toggle("hidden", !id);

  if (id) {
    const r = allRequests.find(x => x.id === id);
    $("request-modal-title").textContent = "Редактирование заявки";
    $("req-client").value = r.client;
    $("req-address").value = r.address;
    $("req-phone").value = r.phone;
    $("req-status").value = r.status;
    $("req-assignee").value = r.assignee;
    $("req-source").value = r.source || "unknown";
    $("req-contact-method").value = r.contact_method || "";
    $("req-price").value = r.price || 0;
    $("req-comment").value = r.comment || "";
    const d = parseDate(r.visit_date);
    $("req-date").value = toLocalDateTimeValue(d);
  } else {
    $("request-modal-title").textContent = "Новая заявка";
    $("req-client").value = "";
    $("req-address").value = "";
    $("req-phone").value = "";
    $("req-status").value = "new";
    $("req-assignee").value = currentUser?.id || (users[0]?.id || "");
    $("req-source").value = "unknown";
    $("req-contact-method").value = "";
    $("req-price").value = 0;
    $("req-comment").value = "";
    const now = new Date();
    $("req-date").value = toLocalDateTimeValue(now);
  }
}

function closeRequestModal() {
  $("request-modal").classList.add("hidden");
}

function toLocalDateTimeValue(d) {
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}T${hh}:${mi}`;
}

async function saveRequest(e) {
  e.preventDefault();
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
    price: parseFloat($("req-price").value) || 0,
    comment: $("req-comment").value.trim()
  };

  try {
    if (id) {
      const res = await fetch(`${API_BASE}/api/requests/${id}`, {
        method: "PUT",
        headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("Не удалось сохранить");
    } else {
      const res = await fetch(`${API_BASE}/api/requests`, {
        method: "POST",
        headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("Не удалось создать");
    }
    await loadRequests();
    closeRequestModal();
    renderCalendar();
    if (!$("list-tab").classList.contains("hidden")) renderList();
  } catch (err) {
    alert(err.message);
  }
}

async function deleteRequest() {
  const id = $("req-id").value;
  if (!id) return;
  const ok = await confirmModal("Удалить заявку?", "Это действие нельзя отменить.");
  if (!ok) return;
  try {
    const res = await fetch(`${API_BASE}/api/requests/${id}`, {
      method: "DELETE",
      headers: getAuthHeaders()
    });
    if (!res.ok) throw new Error("Не удалось удалить");
    await loadRequests();
    closeRequestModal();
    renderCalendar();
    if (!$("list-tab").classList.contains("hidden")) renderList();
  } catch (err) {
    alert(err.message);
  }
}

// ---------- MODAL: CONFIRM ----------

function confirmModal(title, message) {
  return new Promise(resolve => {
    $("confirm-title").textContent = title;
    $("confirm-message").textContent = message;
    const modal = $("confirm-modal");
    modal.classList.remove("hidden");

    const cleanup = () => {
      $("confirm-ok").onclick = null;
      $("confirm-cancel").onclick = null;
      $("confirm-close").onclick = null;
      modal.querySelector(".modal-backdrop").onclick = null;
    };

    $("confirm-ok").onclick = () => {
      cleanup();
      modal.classList.add("hidden");
      resolve(true);
    };
    $("confirm-cancel").onclick =
      $("confirm-close").onclick =
      modal.querySelector(".modal-backdrop").onclick =
      () => {
        cleanup();
        modal.classList.add("hidden");
        resolve(false);
      };
  });
}

// ---------- INIT ----------

async function init() {
  // Theme
  const savedTheme = localStorage.getItem("crm_theme");
  if (savedTheme === "light") {
    document.body.classList.add("light");
    $("theme-toggle").textContent = "☀️";
  }

  $("theme-toggle").addEventListener("click", () => {
    document.body.classList.toggle("light");
    const isLight = document.body.classList.contains("light");
    localStorage.setItem("crm_theme", isLight ? "light" : "dark");
    $("theme-toggle").textContent = isLight ? "☀️" : "🌙";
  });

  // Login form
  $("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = $("login-username").value.trim();
    const password = $("login-password").value;
    const remember = $("login-remember").checked;
    try {
      await login(username, password, remember);
      showMain();
    } catch (err) {
      alert(err.message);
    }
  });

  $("logout-btn").addEventListener("click", logout);

  // Tabs
  document.querySelectorAll(".tab").forEach(t => {
    t.addEventListener("click", () => switchTab(t.dataset.tab));
  });

  // Calendar controls
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

  $("cal-mode").addEventListener("change", (e) => {
    calendarState.mode = e.target.value;
    renderCalendar();
  });

  $("add-request-btn").addEventListener("click", () => openRequestModal());

  // List controls
  $("list-scope").addEventListener("change", () => {
    const isRange = $("list-scope").value === "range";
    $("list-range-inputs").classList.toggle("hidden", !isRange);
    renderList();
  });
  $("list-from").addEventListener("change", renderList);
  $("list-to").addEventListener("change", renderList);
  $("list-search").addEventListener("input", renderList);
  $("list-status").addEventListener("change", renderList);
  $("list-source").addEventListener("change", renderList);
  $("list-contact-method").addEventListener("change", renderList);
  $("list-refresh").addEventListener("click", async () => {
    await loadRequests();
    renderList();
  });

  // Report
  $("report-run").addEventListener("click", runReport);

  // Modal: request
  $("request-modal-close").addEventListener("click", closeRequestModal);
  $("req-cancel-btn").addEventListener("click", closeRequestModal);
  $("request-modal").querySelector(".modal-backdrop").addEventListener("click", closeRequestModal);
  $("request-form").addEventListener("submit", saveRequest);
  $("req-delete-btn").addEventListener("click", deleteRequest);

  // Modal: confirm
  $("confirm-close").addEventListener("click", () => $("confirm-modal").classList.add("hidden"));
  $("confirm-cancel").addEventListener("click", () => $("confirm-modal").classList.add("hidden"));
  $("confirm-modal").querySelector(".modal-backdrop").addEventListener("click", () => $("confirm-modal").classList.add("hidden"));

  // Auto-login
  const ok = await tryAutoLogin();
  if (ok) {
    await loadRequests();
    showMain();
  } else {
    showLogin();
  }
}

init();