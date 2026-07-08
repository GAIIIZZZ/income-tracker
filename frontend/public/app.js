const ALLOWED_EXT = new Set(["jpg", "jpeg", "png", "webp", "bmp"]);

function isAllowed(filename) {
  const ext = (filename.split(".").pop() || "").toLowerCase();
  return ALLOWED_EXT.has(ext);
}

function formatAmount(n) {
  return (Number(n) || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Dates are stored/sorted internally as ISO "YYYY-MM-DD" (so string sort == chronological
// sort); these helpers only affect what's shown to and typed by the user (day/month/year).
function formatDateDisplay(iso) {
  if (!iso) return "";
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!m) return iso;
  return `${m[3]}-${m[2]}-${m[1]}`;
}

function parseDateDisplay(display) {
  if (!display) return display;
  const m = /^(\d{1,2})-(\d{1,2})-(\d{4})$/.exec(display.trim());
  if (!m) return display.trim();
  return `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}`;
}

function formatDateTimeDisplay(sqlDatetime) {
  if (!sqlDatetime) return "";
  const [datePart, timePart] = sqlDatetime.split(" ");
  const displayDate = formatDateDisplay(datePart);
  return timePart ? `${displayDate} ${timePart.slice(0, 5)}` : displayDate;
}

function formatPeriodLabel(period) {
  if (/^\d{4}-\d{2}-\d{2}$/.test(period)) return formatDateDisplay(period);
  if (/^\d{4}-\d{2}$/.test(period)) {
    const [y, m] = period.split("-");
    return `${m}-${y}`;
  }
  return period;
}

function imageUrl(row) {
  if (!row.processed_image_path) return null;
  const normalized = row.processed_image_path.replace(/\\/g, "/");
  const reviewIdx = normalized.indexOf("/needs_review/");
  if (reviewIdx >= 0) return "/images/needs_review/" + normalized.slice(reviewIdx + "/needs_review/".length);
  const processedIdx = normalized.indexOf("/processed/");
  if (processedIdx >= 0) return "/images/processed/" + normalized.slice(processedIdx + "/processed/".length);
  return null;
}

// ---------- Toast notifications ----------
const toastContainer = document.getElementById("toastContainer");

function showToast(message, { loading = false } = {}) {
  const id = "toast-" + Date.now() + "-" + Math.random().toString(36).slice(2, 7);
  const el = document.createElement("div");
  el.className = "toast" + (loading ? " loading" : "");
  el.id = id;
  el.innerHTML = loading
    ? `<span class="toast-spinner"></span><span class="toast-message">${message}</span>`
    : `<span class="toast-icon">&#10003;</span><span class="toast-message">${message}</span>`;
  toastContainer.appendChild(el);
  if (!loading) dismissToast(id);
  return id;
}

function updateToast(id, message, { success = true, autoDismiss = true } = {}) {
  const el = document.getElementById(id);
  if (!el) return showToast(message, { loading: false });
  el.classList.remove("loading");
  el.classList.add(success ? "success" : "error");
  el.innerHTML = `<span class="toast-icon">${success ? "&#10003;" : "&#10007;"}</span><span class="toast-message">${message}</span>`;
  if (autoDismiss) dismissToast(id);
  return id;
}

function dismissToast(id, delay = 4500) {
  setTimeout(() => {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.add("toast-out");
    setTimeout(() => el.remove(), 250);
  }, delay);
}

// ---------- Type (Income / Expense) + per-type state ----------
let currentType = "income";

function makeTypeState(type) {
  return {
    currentView: "unsaved",
    currentDraftSlot: 1,
    batchSort: "favorite",
    savedBatchesCache: [],
    sortState: { field: null, dir: "asc" },
    visibleSlots: JSON.parse(localStorage.getItem(`visible-draft-slots-${type}`) || "[1]"),
  };
}

const perType = { income: makeTypeState("income"), expense: makeTypeState("expense") };

function ts() {
  return perType[currentType];
}

function typeLabel(type = currentType) {
  return type === "expense" ? "Expense" : "Income";
}

function saveVisibleSlots() {
  localStorage.setItem(`visible-draft-slots-${currentType}`, JSON.stringify(ts().visibleSlots));
}

function updateTypeLabels() {
  document.getElementById("saveBtn").textContent = `Save ${typeLabel()}`;
  document.getElementById("graphTitle").textContent = `${typeLabel()} over time`;
  document.querySelector(".sidebar-header").textContent = `${typeLabel()} Working`;
}

// ---------- Tabs ----------
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
    if (btn.dataset.tab === "transactions" && btn.dataset.type) {
      currentType = btn.dataset.type;
      updateTypeLabels();
      updateToolbarForView();
      loadSidebar();
      loadTransactions();
      loadGraph();
    }
    if (btn.dataset.tab === "gallery") loadGallery();
    if (btn.dataset.tab === "zones") loadZoneProfiles();
  });
});

const sidebarList = document.getElementById("sidebarList");
const workingList = document.getElementById("workingList");

async function loadSidebar() {
  await renderWorkingSlots();
  await renderSavedBatches();
}

async function renderWorkingSlots() {
  const allUnsaved = await (await fetch(`/api/transactions?batch_id=unsaved&type=${currentType}`)).json();
  const usedSlots = new Set(allUnsaved.map((t) => t.draft_slot || 1));
  usedSlots.forEach((s) => { if (!ts().visibleSlots.includes(s)) ts().visibleSlots.push(s); });
  if (ts().visibleSlots.length === 0) ts().visibleSlots = [1];
  ts().visibleSlots.sort((a, b) => a - b);
  saveVisibleSlots();

  if (!ts().visibleSlots.includes(ts().currentDraftSlot)) ts().currentDraftSlot = ts().visibleSlots[0];

  workingList.innerHTML = ts().visibleSlots.map((slot) => {
    const isActive = ts().currentView === "unsaved" && ts().currentDraftSlot === slot;
    const label = ts().visibleSlots.length > 1 ? `Working Set ${slot}` : "Current (unsaved)";
    return `
      <li class="sidebar-item${isActive ? " active" : ""}" data-slot="${slot}">
        <span class="sidebar-item-text"><span class="sidebar-item-name">${label}</span></span>
        <span class="sidebar-item-actions">
          <button class="working-delete-btn" title="Cancel this set" data-slot="${slot}">&times;</button>
        </span>
      </li>
    `;
  }).join("");
}

workingList.addEventListener("click", async (e) => {
  const li = e.target.closest(".sidebar-item");
  if (!li) return;

  const deleteBtn = e.target.closest(".working-delete-btn");
  if (deleteBtn) {
    const slot = Number(deleteBtn.dataset.slot);
    const label = ts().visibleSlots.length > 1 ? `Working Set ${slot}` : "the current working set";
    if (!confirm(`Cancel ${label}? This deletes all its unsaved transactions.`)) return;

    const resp = await fetch(`/api/clear?draft_slot=${slot}&type=${currentType}`, { method: "POST" });
    const result = await resp.json();

    ts().visibleSlots = ts().visibleSlots.filter((s) => s !== slot);
    if (ts().visibleSlots.length === 0) ts().visibleSlots = [1];
    saveVisibleSlots();
    if (ts().currentDraftSlot === slot) ts().currentDraftSlot = ts().visibleSlots[0];

    await renderWorkingSlots();
    updateToolbarForView();
    updateBatchInfoBar();
    loadTransactions();
    loadGraph();
    showToast(`Cancelled ${label} (${result.deleted} transaction(s) removed).`);
    return;
  }

  ts().currentView = "unsaved";
  ts().currentDraftSlot = Number(li.dataset.slot);
  document.querySelectorAll(".sidebar-item").forEach((el) => el.classList.remove("active"));
  li.classList.add("active");
  updateToolbarForView();
  updateBatchInfoBar();
  loadTransactions();
  loadGraph();
});

document.getElementById("addSecondSlotBtn").addEventListener("click", async () => {
  const nextSlot = ts().visibleSlots.length ? Math.max(...ts().visibleSlots) + 1 : 1;
  ts().visibleSlots.push(nextSlot);
  saveVisibleSlots();
  ts().currentView = "unsaved";
  ts().currentDraftSlot = nextSlot;
  await renderWorkingSlots();
  updateToolbarForView();
  updateBatchInfoBar();
  loadTransactions();
  loadGraph();
  showToast(`Added Working Set ${nextSlot}.`);
});

document.getElementById("batchSortSelect").addEventListener("change", (e) => {
  ts().batchSort = e.target.value;
  renderSavedBatches();
});

async function renderSavedBatches() {
  const resp = await fetch(`/api/batches?sort=${ts().batchSort}&type=${currentType}`);
  ts().savedBatchesCache = await resp.json();

  sidebarList.innerHTML = ts().savedBatchesCache.map((b) => `
    <li class="sidebar-item${ts().currentView === String(b.id) ? " active" : ""}" data-batch="${b.id}">
      <button class="sidebar-star${b.is_favorite ? " active" : ""}" title="${b.is_favorite ? "Unfavorite" : "Favorite"}">${b.is_favorite ? "&#9733;" : "&#9734;"}</button>
      <span class="sidebar-item-text">
        <span class="sidebar-item-name">${b.name}</span>
        <span class="sidebar-item-meta">
          <span class="badge-type badge-${b.batch_type}">${typeLabel(b.batch_type)}</span>
          ${b.count} tx &middot; ${formatAmount(b.total)}
        </span>
      </span>
      <span class="sidebar-item-actions">
        <button class="sidebar-rename-btn" title="Rename">&#9998;</button>
        <button class="sidebar-delete-btn" title="Delete">&times;</button>
      </span>
    </li>
  `).join("");

  updateBatchInfoBar();
}

sidebarList.addEventListener("click", async (e) => {
  const li = e.target.closest(".sidebar-item");
  if (!li) return;

  const starBtn = e.target.closest(".sidebar-star");
  const renameBtn = e.target.closest(".sidebar-rename-btn");
  const deleteBtn = e.target.closest(".sidebar-delete-btn");

  if (starBtn) {
    const batch = ts().savedBatchesCache.find((b) => String(b.id) === li.dataset.batch);
    await fetch(`/api/batches/${li.dataset.batch}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_favorite: !batch.is_favorite }),
    });
    showToast(batch.is_favorite ? "Removed from favorites." : "Added to favorites.");
    renderSavedBatches();
    return;
  }

  if (renameBtn) {
    const currentName = li.querySelector(".sidebar-item-name").textContent;
    const newName = prompt("Rename this saved batch:", currentName);
    if (!newName || !newName.trim() || newName.trim() === currentName) return;
    await fetch(`/api/batches/${li.dataset.batch}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: newName.trim() }),
    });
    showToast("Batch renamed.");
    renderSavedBatches();
    return;
  }

  if (deleteBtn) {
    const currentName = li.querySelector(".sidebar-item-name").textContent;
    if (!confirm(`Delete "${currentName}" and all its transactions? This cannot be undone.`)) return;
    await fetch(`/api/batches/${li.dataset.batch}`, { method: "DELETE" });
    if (ts().currentView === li.dataset.batch) ts().currentView = "unsaved";
    showToast(`Deleted "${currentName}".`);
    updateToolbarForView();
    loadSidebar();
    loadTransactions();
    loadGraph();
    return;
  }

  ts().currentView = li.dataset.batch;
  document.querySelectorAll(".sidebar-item").forEach((el) => el.classList.remove("active"));
  li.classList.add("active");
  updateToolbarForView();
  updateBatchInfoBar();
  loadTransactions();
});

function updateBatchInfoBar() {
  const bar = document.getElementById("batchInfoBar");
  const batch = ts().savedBatchesCache.find((b) => String(b.id) === ts().currentView);
  if (!batch) {
    bar.hidden = true;
    return;
  }
  bar.hidden = false;
  bar.textContent = `Saved ${formatDateTimeDisplay(batch.created_at)}` +
    (batch.last_edited ? ` · Last edited ${formatDateTimeDisplay(batch.last_edited)}` : "");
}

function updateToolbarForView() {
  const showWorkingControls = ts().currentView === "unsaved";
  document.getElementById("saveBtn").hidden = !showWorkingControls;
  document.getElementById("clearBtn").hidden = !showWorkingControls;
  document.getElementById("addManualBtn").hidden = !showWorkingControls;
}

// ---------- Sidebar collapse ----------
const SIDEBAR_COLLAPSED_KEY = "sidebar-collapsed";

function applySidebarCollapsed(collapsed) {
  document.getElementById("sidebar").classList.toggle("collapsed", collapsed);
  document.getElementById("sidebarToggle").innerHTML = collapsed ? "&#187;" : "&#171;";
}

document.getElementById("sidebarToggle").addEventListener("click", () => {
  const collapsed = !document.getElementById("sidebar").classList.contains("collapsed");
  localStorage.setItem(SIDEBAR_COLLAPSED_KEY, collapsed ? "1" : "0");
  applySidebarCollapsed(collapsed);
});

applySidebarCollapsed(localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "1");

// ---------- Folder / multi-file collection (drag & drop) ----------
async function readAllEntries(reader) {
  let all = [];
  let batch;
  do {
    batch = await new Promise((resolve, reject) => reader.readEntries(resolve, reject));
    all = all.concat(batch);
  } while (batch.length > 0);
  return all;
}

async function walkEntry(entry, files) {
  if (entry.isFile) {
    const file = await new Promise((resolve, reject) => entry.file(resolve, reject));
    if (isAllowed(file.name)) files.push(file);
  } else if (entry.isDirectory) {
    const entries = await readAllEntries(entry.createReader());
    for (const child of entries) await walkEntry(child, files);
  }
}

async function collectFilesFromDrop(dataTransfer) {
  const items = dataTransfer.items;
  if (items && items.length && items[0].webkitGetAsEntry) {
    const entries = [];
    for (const item of items) {
      const entry = item.webkitGetAsEntry && item.webkitGetAsEntry();
      if (entry) entries.push(entry);
    }
    const files = [];
    for (const entry of entries) await walkEntry(entry, files);
    if (files.length) return files;
  }
  return Array.from(dataTransfer.files || []).filter((f) => isAllowed(f.name));
}

// ---------- Upload area ----------
const uploadArea = document.getElementById("uploadArea");
const fileInput = document.getElementById("fileInput");
const folderInput = document.getElementById("folderInput");

document.getElementById("browseFilesLink").addEventListener("click", (e) => {
  e.stopPropagation();
  fileInput.click();
});
document.getElementById("browseFolderLink").addEventListener("click", (e) => {
  e.stopPropagation();
  folderInput.click();
});

uploadArea.addEventListener("click", () => fileInput.click());
uploadArea.addEventListener("dragover", (e) => { e.preventDefault(); uploadArea.classList.add("dragover"); });
uploadArea.addEventListener("dragleave", () => uploadArea.classList.remove("dragover"));
uploadArea.addEventListener("drop", async (e) => {
  e.preventDefault();
  uploadArea.classList.remove("dragover");
  const files = await collectFilesFromDrop(e.dataTransfer);
  if (files.length) runBatchUpload(files);
});
fileInput.addEventListener("change", () => {
  const files = Array.from(fileInput.files || []).filter((f) => isAllowed(f.name));
  fileInput.value = "";
  if (files.length) runBatchUpload(files);
});
folderInput.addEventListener("change", () => {
  const files = Array.from(folderInput.files || []).filter((f) => isAllowed(f.name));
  folderInput.value = "";
  if (files.length) runBatchUpload(files);
});

// ---------- Upload progress (per drag-drop session, unrelated to saved batches) ----------
async function uploadSingle(file) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("draft_slot", String(ts().currentDraftSlot));
  formData.append("transaction_type", currentType);
  const resp = await fetch("/api/upload", { method: "POST", body: formData });
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

async function runBatchUpload(files) {
  const batchProgress = document.getElementById("batchProgress");
  const batchTitle = document.getElementById("batchTitle");
  const batchList = document.getElementById("batchList");
  const batchSummary = document.getElementById("batchSummary");
  const batchDismiss = document.getElementById("batchDismiss");

  ts().currentView = "unsaved";
  document.querySelectorAll(".sidebar-item").forEach((el) => el.classList.toggle("active", el.dataset.slot === String(ts().currentDraftSlot)));
  updateToolbarForView();
  updateBatchInfoBar();

  batchProgress.hidden = false;
  batchSummary.hidden = true;
  batchDismiss.hidden = true;
  batchList.innerHTML = "";
  batchTitle.textContent = `Processing 0 / ${files.length}...`;

  const uploadToastId = showToast(`Processing 0 / ${files.length} slip(s)...`, { loading: true });

  const statusEls = files.map((file) => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="batch-item-name">${file.name}</span><span class="batch-item-status queued">queued</span>`;
    batchList.appendChild(li);
    return li.querySelector(".batch-item-status");
  });

  let succeeded = 0, needsReview = 0, failed = 0, total = 0;

  for (let i = 0; i < files.length; i++) {
    const statusEl = statusEls[i];
    statusEl.textContent = "processing";
    statusEl.className = "batch-item-status processing";
    batchTitle.textContent = `Processing ${i + 1} / ${files.length}...`;
    const toastMsgEl = document.querySelector(`#${uploadToastId} .toast-message`);
    if (toastMsgEl) toastMsgEl.textContent = `Processing ${i + 1} / ${files.length} slip(s)...`;
    try {
      const record = await uploadSingle(files[i]);
      if (record.status === "needs_review") {
        needsReview++;
        statusEl.textContent = "needs review";
        statusEl.className = "batch-item-status error";
      } else {
        succeeded++;
        statusEl.textContent = "done";
        statusEl.className = "batch-item-status done";
      }
      total += Number(record.amount) || 0;
    } catch (err) {
      failed++;
      statusEl.textContent = "failed";
      statusEl.className = "batch-item-status error";
    }
  }

  batchTitle.textContent = `Finished ${files.length} file${files.length === 1 ? "" : "s"}`;
  batchSummary.hidden = false;
  batchSummary.textContent =
    `${succeeded} processed, ${needsReview} need review, ${failed} failed — total ${formatAmount(total)}`;
  batchDismiss.hidden = false;

  updateToast(
    uploadToastId,
    `Finished ${files.length} file${files.length === 1 ? "" : "s"} — ${succeeded} processed, ${needsReview} need review, ${failed} failed.`,
    { success: failed === 0 }
  );

  loadTransactions();
  loadGraph();
}

document.getElementById("batchDismiss").addEventListener("click", () => {
  document.getElementById("batchProgress").hidden = true;
});

// ---------- Transactions ----------
const txBody = document.getElementById("txBody");
let currentRows = [];
let editingRowId = null;

function escapeAttr(v) {
  return String(v ?? "").replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
}

function statusPill(row) {
  const label = row.status === "needs_review" ? "needs review" : row.status;
  const title = row.recheck_note ? ` title="${row.recheck_note.replace(/"/g, "&quot;")}"` : "";
  return `<span class="status-pill status-${row.status}"${title}>${label}</span>`;
}

function imageLink(row) {
  const url = imageUrl(row);
  if (!url) return "-";
  return `<a class="thumb-link" href="${url}" target="_blank" rel="noopener">view</a>`;
}

async function loadTransactions() {
  const params = new URLSearchParams();
  params.set("batch_id", ts().currentView);
  params.set("type", currentType);
  if (ts().currentView === "unsaved") params.set("draft_slot", String(ts().currentDraftSlot));
  const search = document.getElementById("searchInput").value.trim();
  const status = document.getElementById("statusFilter").value;
  if (search) params.set("search", search);
  if (status) params.set("status", status);

  const resp = await fetch(`/api/transactions?${params.toString()}`);
  currentRows = await resp.json();
  renderTransactions();
}

function sortedRows() {
  if (!ts().sortState.field) return currentRows;
  const { field, dir } = ts().sortState;
  const mult = dir === "asc" ? 1 : -1;
  return [...currentRows].sort((a, b) => {
    if (field === "amount") {
      const av = a.amount === null || a.amount === undefined ? -Infinity : Number(a.amount);
      const bv = b.amount === null || b.amount === undefined ? -Infinity : Number(b.amount);
      return (av - bv) * mult;
    }
    const av = (a[field] ?? "").toString().toLowerCase();
    const bv = (b[field] ?? "").toString().toLowerCase();
    if (av < bv) return -1 * mult;
    if (av > bv) return 1 * mult;
    return 0;
  });
}

function updateSortIndicators() {
  document.querySelectorAll(".sort-btn").forEach((btn) => {
    const indicator = btn.querySelector(".sort-indicator");
    indicator.textContent = btn.dataset.sort === ts().sortState.field ? (ts().sortState.dir === "asc" ? "▲" : "▼") : "";
  });
}

function viewRowHtml(row) {
  return `
    <td data-field="transaction_date">${formatDateDisplay(row.transaction_date)}</td>
    <td data-field="transaction_time">${row.transaction_time ?? ""}</td>
    <td data-field="sender_name">${row.sender_name ?? ""}</td>
    <td data-field="amount">${row.amount ?? ""}</td>
    <td data-field="notes">${row.notes ?? ""}</td>
    <td>${statusPill(row)}</td>
    <td>${imageLink(row)}</td>
    <td class="row-actions">
      <button class="row-edit" title="Edit">&#9998;</button>
      <button class="row-delete" title="Delete">&times;</button>
    </td>
  `;
}

const STATUS_OPTIONS = [
  { value: "pending", label: "pending" },
  { value: "corrected", label: "corrected" },
  { value: "needs_review", label: "needs review" },
];

function statusSelect(row) {
  const options = STATUS_OPTIONS.map(
    ({ value, label }) => `<option value="${value}" ${value === row.status ? "selected" : ""}>${label}</option>`
  ).join("");
  return `<select class="edit-input" data-field="status">${options}</select>`;
}

function editRowHtml(row) {
  return `
    <td><input type="text" class="edit-input" data-field="transaction_date" value="${escapeAttr(formatDateDisplay(row.transaction_date))}" placeholder="DD-MM-YYYY" /></td>
    <td><input type="text" class="edit-input" data-field="transaction_time" value="${escapeAttr(row.transaction_time)}" placeholder="HH:MM" /></td>
    <td><input type="text" class="edit-input" data-field="sender_name" value="${escapeAttr(row.sender_name)}" /></td>
    <td><input type="number" step="0.01" class="edit-input" data-field="amount" value="${escapeAttr(row.amount)}" /></td>
    <td><input type="text" class="edit-input" data-field="notes" value="${escapeAttr(row.notes)}" /></td>
    <td>${statusSelect(row)}</td>
    <td>${imageLink(row)}</td>
    <td class="row-actions">
      <button class="row-confirm" title="Confirm">&#10003;</button>
      <button class="row-cancel" title="Cancel">&#10005;</button>
    </td>
  `;
}

function renderTransactions() {
  const rows = sortedRows();
  txBody.innerHTML = "";
  let total = 0;
  let reviewCount = 0;
  let pendingCount = 0;

  for (const row of rows) {
    total += Number(row.amount) || 0;
    if (row.status === "needs_review") reviewCount++;
    if (row.status === "pending") pendingCount++;

    const tr = document.createElement("tr");
    tr.dataset.id = row.id;
    tr.innerHTML = row.id === editingRowId ? editRowHtml(row) : viewRowHtml(row);
    txBody.appendChild(tr);
  }

  document.getElementById("statCount").textContent = rows.length;
  document.getElementById("statTotal").textContent = formatAmount(total);
  document.getElementById("statPending").textContent = pendingCount;
  document.getElementById("statReview").textContent = reviewCount;
  document.getElementById("footerTotal").textContent = formatAmount(total);

  updateSortIndicators();
}

document.querySelectorAll(".sort-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const field = btn.dataset.sort;
    if (ts().sortState.field === field) {
      ts().sortState.dir = ts().sortState.dir === "asc" ? "desc" : "asc";
    } else {
      ts().sortState = { field, dir: "asc" };
    }
    editingRowId = null;
    renderTransactions();
  });
});

txBody.addEventListener("click", async (e) => {
  const editBtn = e.target.closest(".row-edit");
  const cancelBtn = e.target.closest(".row-cancel");
  const confirmBtn = e.target.closest(".row-confirm");
  const deleteBtn = e.target.closest(".row-delete");

  if (editBtn) {
    editingRowId = Number(editBtn.closest("tr").dataset.id);
    renderTransactions();
    return;
  }

  if (cancelBtn) {
    editingRowId = null;
    renderTransactions();
    return;
  }

  if (confirmBtn) {
    const tr = confirmBtn.closest("tr");
    const id = Number(tr.dataset.id);
    const row = currentRows.find((r) => r.id === id);
    const updates = {};
    tr.querySelectorAll(".edit-input").forEach((input) => {
      const field = input.dataset.field;
      let value = input.value.trim();
      if (field === "amount") value = value === "" ? null : parseFloat(value);
      if (field === "transaction_date") value = parseDateDisplay(value);
      if (value === "") value = null;
      const oldStr = row[field] === null || row[field] === undefined ? "" : String(row[field]);
      const newStr = value === null || value === undefined ? "" : String(value);
      if (oldStr !== newStr) updates[field] = value;
    });
    editingRowId = null;
    if (Object.keys(updates).length > 0) {
      await patchTransaction(id, updates);
      await loadTransactions();
      loadSidebar();
      loadGraph();
      showToast("Edit saved.");
    } else {
      renderTransactions();
    }
    return;
  }

  if (deleteBtn) {
    const tr = deleteBtn.closest("tr");
    if (!confirm("Delete this transaction?")) return;
    await fetch(`/api/transactions/${tr.dataset.id}`, { method: "DELETE" });
    loadTransactions();
    loadSidebar();
    loadGraph();
    showToast("Transaction deleted.");
  }
});

async function patchTransaction(id, fields) {
  await fetch(`/api/transactions/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(fields),
  });
}

document.getElementById("refreshBtn").addEventListener("click", () => { loadTransactions(); loadSidebar(); loadGraph(); });

document.getElementById("exportExcelBtn").addEventListener("click", () => {
  const params = new URLSearchParams();
  params.set("batch_id", ts().currentView);
  params.set("type", currentType);
  if (ts().currentView === "unsaved") params.set("draft_slot", String(ts().currentDraftSlot));
  const search = document.getElementById("searchInput").value.trim();
  const status = document.getElementById("statusFilter").value;
  if (search) params.set("search", search);
  if (status) params.set("status", status);
  window.location.href = `/api/export?${params.toString()}`;
});

document.getElementById("importExcelBtn").addEventListener("click", () => {
  document.getElementById("excelImportInput").click();
});

document.getElementById("excelImportInput").addEventListener("change", async () => {
  const input = document.getElementById("excelImportInput");
  const file = input.files[0];
  input.value = "";
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);
  formData.append("draft_slot", String(ts().currentDraftSlot));
  formData.append("type", currentType);

  const toastId = showToast("Importing from Excel...", { loading: true });
  const resp = await fetch("/api/import", { method: "POST", body: formData });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    updateToast(toastId, err.detail || "Import failed.", { success: false });
    return;
  }
  const result = await resp.json();

  ts().currentView = "unsaved";
  updateToolbarForView();
  await loadSidebar();
  document.querySelectorAll(".sidebar-item").forEach((el) => el.classList.toggle("active", el.dataset.slot === String(ts().currentDraftSlot)));
  updateBatchInfoBar();
  loadTransactions();
  loadGraph();

  updateToast(
    toastId,
    `Imported ${result.imported} transaction(s)` + (result.skipped ? `, skipped ${result.skipped} row(s) with no valid amount.` : "."),
    { success: true }
  );
});
document.getElementById("searchInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter") loadTransactions();
});
document.getElementById("statusFilter").addEventListener("change", loadTransactions);

document.getElementById("addManualBtn").addEventListener("click", async () => {
  await fetch("/api/transactions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ draft_slot: ts().currentDraftSlot, transaction_type: currentType }),
  });
  loadTransactions();
  loadGraph();
  showToast("Transaction added.");
});

document.getElementById("clearBtn").addEventListener("click", async () => {
  if (!confirm("Delete all currently shown (unsaved) transactions? This cannot be undone.")) return;
  const toastId = showToast("Clearing...", { loading: true });
  const resp = await fetch(`/api/clear?draft_slot=${ts().currentDraftSlot}&type=${currentType}`, { method: "POST" });
  const result = await resp.json();
  loadTransactions();
  loadGraph();
  updateToast(toastId, `Cleared ${result.deleted} transaction(s).`);
});

document.getElementById("saveBtn").addEventListener("click", async () => {
  const toastId = showToast("Saving and running AI double-check...", { loading: true });

  const resp = await fetch("/api/batches", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ draft_slot: ts().currentDraftSlot, type: currentType }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    updateToast(toastId, err.detail || "Nothing to save.", { success: false });
    return;
  }
  const batch = await resp.json();

  const flaggedResp = await fetch(`/api/transactions?batch_id=${batch.id}&status=needs_review`);
  const flagged = await flaggedResp.json();
  const flaggedCount = flagged.filter((r) => r.recheck_status === "mismatch").length;

  await loadSidebar();
  ts().currentView = "unsaved";
  document.querySelectorAll(".sidebar-item").forEach((el) => el.classList.toggle("active", el.dataset.slot === String(ts().currentDraftSlot)));
  updateBatchInfoBar();
  loadTransactions();
  loadGraph();

  updateToast(
    toastId,
    `Saved as "${batch.name}" — ${batch.count} transaction(s), total ${formatAmount(batch.total)}.` +
    (flaggedCount ? `\n${flaggedCount} flagged for review by the AI double-check.` : "\nAI double-check found no disagreements.")
  );
});

// ---------- Graph ----------
const LINE_DEFS = [
  { key: "correct", label: "Correct", color: "var(--ok)" },
  { key: "pending", label: "Pending", color: "var(--warn)" },
  { key: "needs_review", label: "Needs review", color: "var(--danger)" },
  { key: "all_total", label: "All", color: "var(--accent)" },
];
let lineVisibility = { correct: true, pending: true, needs_review: true, all_total: true };
let lastGraphData = [];

function toBuddhistEra(isoDateStr) {
  if (!isoDateStr) return null;
  const [y, m, d] = isoDateStr.split("-");
  return `${Number(y) + 543}-${m}-${d}`;
}

async function loadGraph() {
  const period = document.getElementById("graphPeriod").value;
  const dateFrom = toBuddhistEra(document.getElementById("graphDateFrom").value);
  const dateTo = toBuddhistEra(document.getElementById("graphDateTo").value);

  const params = new URLSearchParams({ period, type: currentType });
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);

  const resp = await fetch(`/api/income-summary?${params.toString()}`);
  lastGraphData = await resp.json();
  renderLegend();
  renderLineChart();
}

function renderLegend() {
  const totals = { correct: 0, pending: 0, needs_review: 0, all_total: 0 };
  lastGraphData.forEach((d) => {
    LINE_DEFS.forEach(({ key }) => { totals[key] += Number(d[key]) || 0; });
  });

  const legend = document.getElementById("graphLegend");
  legend.innerHTML = LINE_DEFS.map(({ key, label, color }) => `
    <label class="legend-item">
      <input type="checkbox" data-line="${key}" ${lineVisibility[key] ? "checked" : ""} />
      <span class="legend-swatch" style="background:${color}"></span>
      <span>${label}</span>
      <span class="legend-total">${formatAmount(totals[key])}</span>
    </label>
  `).join("");
}

document.getElementById("graphLegend").addEventListener("change", (e) => {
  const key = e.target.dataset.line;
  if (!key) return;
  lineVisibility[key] = e.target.checked;
  renderLineChart();
});

function renderLineChart() {
  const container = document.getElementById("graphContainer");
  const data = lastGraphData;
  if (!data.length) {
    container.innerHTML = '<div class="graph-empty">No data for this range yet.</div>';
    return;
  }

  const width = Math.max(480, data.length * 70);
  const height = 240;
  const padding = { top: 16, right: 16, bottom: 30, left: 70 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const visibleKeys = LINE_DEFS.filter((l) => lineVisibility[l.key]).map((l) => l.key);
  const maxVal = Math.max(1, ...data.flatMap((d) => visibleKeys.map((k) => Number(d[k]) || 0)));
  const stepX = data.length > 1 ? chartW / (data.length - 1) : 0;

  function pointFor(i, val) {
    const x = padding.left + (data.length > 1 ? i * stepX : chartW / 2);
    const y = padding.top + chartH - (val / maxVal) * chartH;
    return [x, y];
  }

  let svgParts = "";
  LINE_DEFS.forEach(({ key, color }) => {
    if (!lineVisibility[key]) return;
    const points = data.map((d, i) => pointFor(i, Number(d[key]) || 0));
    const pathD = points.map((p, i) => `${i === 0 ? "M" : "L"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
    svgParts += `<path d="${pathD}" fill="none" style="stroke:${color}" stroke-width="2" />`;
    points.forEach((p, i) => {
      const val = Number(data[i][key]) || 0;
      svgParts += `<circle cx="${p[0].toFixed(1)}" cy="${p[1].toFixed(1)}" r="3.5" style="fill:${color}"><title>${formatPeriodLabel(data[i].period)} — ${LINE_DEFS.find(l => l.key === key).label}: ${formatAmount(val)}</title></circle>`;
    });
  });

  let labels = "";
  data.forEach((d, i) => {
    const [x] = pointFor(i, 0);
    labels += `<text class="graph-label" x="${x.toFixed(1)}" y="${height - 10}" text-anchor="middle">${formatPeriodLabel(d.period)}</text>`;
  });
  const axisLabel = `<text class="graph-label" x="${padding.left - 8}" y="${padding.top + 4}" text-anchor="end">${formatAmount(maxVal)}</text>`;

  container.innerHTML = `<svg viewBox="0 0 ${width} ${height}" width="${width}" height="${height}">${axisLabel}${labels}${svgParts}</svg>`;
}

document.getElementById("graphPeriod").addEventListener("change", loadGraph);
document.getElementById("graphDateFrom").addEventListener("change", loadGraph);
document.getElementById("graphDateTo").addEventListener("change", loadGraph);

// ---------- Gallery ----------
const galleryGrid = document.getElementById("galleryGrid");

async function loadGallery() {
  const typeFilter = document.getElementById("galleryTypeFilter").value;
  const params = new URLSearchParams({ batch_id: "all", limit: "500" });
  if (typeFilter) params.set("type", typeFilter);
  const resp = await fetch(`/api/transactions?${params.toString()}`);
  const rows = await resp.json();
  galleryGrid.innerHTML = rows.map((row) => {
    const url = imageUrl(row);
    const thumb = url
      ? `<img class="gallery-thumb" src="${url}" alt="${row.sender_name ?? ''}" loading="lazy" />`
      : `<div class="gallery-thumb-placeholder">no image</div>`;
    return `
      <div class="gallery-card">
        ${url ? `<a href="${url}" target="_blank" rel="noopener">${thumb}</a>` : thumb}
        <div class="gallery-body">
          <div class="gallery-name">
            <span class="badge-type badge-${row.transaction_type}">${typeLabel(row.transaction_type)}</span>
            ${row.sender_name ?? "(unknown sender)"}
          </div>
          <div class="gallery-amount">${formatAmount(row.amount)}</div>
          <div class="gallery-meta">${formatDateDisplay(row.transaction_date)} ${row.transaction_time ?? ""}</div>
        </div>
      </div>
    `;
  }).join("");
}

document.getElementById("refreshGalleryBtn").addEventListener("click", loadGallery);
document.getElementById("galleryTypeFilter").addEventListener("change", loadGallery);

// ---------- Zone profiles ----------
const ZONE_FIELD_LABELS = {
  sender_name: "Sender Name",
  transaction_date: "Date",
  transaction_time: "Time",
  amount: "Amount",
};

let zoneProfilesCache = [];
let currentZones = {}; // field -> {x, y, width, height} fractions
let zoneSampleFile = null;
let zoneDrawing = null;

function zoneSampleUrl(profile) {
  if (!profile.sample_image_path) return null;
  const normalized = profile.sample_image_path.replace(/\\/g, "/");
  return `/images/zone_samples/${normalized.split("/").pop()}`;
}

async function loadZoneProfiles() {
  const resp = await fetch("/api/zone-profiles");
  zoneProfilesCache = await resp.json();
  renderZoneProfileList();
}

function renderZoneProfileList() {
  const grid = document.getElementById("zoneProfileList");
  if (!zoneProfilesCache.length) {
    grid.innerHTML = '<div class="zone-empty">No zone profiles yet. Create one to help the AI read a specific bank\'s slips more accurately.</div>';
    return;
  }
  grid.innerHTML = zoneProfilesCache.map((p) => {
    const url = zoneSampleUrl(p);
    const fields = JSON.parse(p.zones_json).map((z) => ZONE_FIELD_LABELS[z.field] || z.field).join(", ");
    return `
      <div class="zone-profile-card">
        ${url ? `<img class="zone-profile-thumb" src="${url}" alt="${p.name}" />` : '<div class="zone-profile-thumb-placeholder">no sample</div>'}
        <div class="zone-profile-body">
          <div class="zone-profile-name">${p.name}</div>
          <div class="zone-profile-meta">Keywords: ${p.identifier_keywords}</div>
          <div class="zone-profile-meta">Zones: ${fields}</div>
        </div>
        <button class="zone-profile-delete" data-id="${p.id}" title="Delete">&times;</button>
      </div>
    `;
  }).join("");
}

document.getElementById("zoneProfileList").addEventListener("click", async (e) => {
  const delBtn = e.target.closest(".zone-profile-delete");
  if (!delBtn) return;
  if (!confirm("Delete this zone profile? Future uploads from this bank will fall back to whole-text extraction.")) return;
  await fetch(`/api/zone-profiles/${delBtn.dataset.id}`, { method: "DELETE" });
  showToast("Zone profile deleted.");
  loadZoneProfiles();
});

document.getElementById("newZoneProfileBtn").addEventListener("click", () => {
  currentZones = {};
  zoneSampleFile = null;
  const nameInput = document.getElementById("zoneProfileName");
  nameInput.value = `${typeLabel()} - `;
  nameInput.setSelectionRange(nameInput.value.length, nameInput.value.length);
  document.getElementById("zoneProfileKeywords").value = "";
  document.getElementById("zoneSampleFileName").textContent = "";
  document.getElementById("zoneSampleImg").removeAttribute("src");
  document.getElementById("zoneBoxLayer").innerHTML = "";
  document.getElementById("zoneCalibrator").hidden = false;
});

document.getElementById("zoneCancelBtn").addEventListener("click", () => {
  document.getElementById("zoneCalibrator").hidden = true;
});

document.getElementById("zoneSampleBtn").addEventListener("click", () => {
  document.getElementById("zoneSampleInput").click();
});

document.getElementById("zoneSampleInput").addEventListener("change", () => {
  const file = document.getElementById("zoneSampleInput").files[0];
  if (!file) return;
  zoneSampleFile = file;
  document.getElementById("zoneSampleFileName").textContent = file.name;
  document.getElementById("zoneSampleImg").src = URL.createObjectURL(file);
  currentZones = {};
  renderZoneBoxes();
});

function renderZoneBoxes() {
  const layer = document.getElementById("zoneBoxLayer");
  layer.innerHTML = "";
  for (const [field, box] of Object.entries(currentZones)) {
    const div = document.createElement("div");
    div.className = "zone-box";
    div.style.left = `${box.x * 100}%`;
    div.style.top = `${box.y * 100}%`;
    div.style.width = `${box.width * 100}%`;
    div.style.height = `${box.height * 100}%`;
    div.innerHTML = `<span class="zone-box-label">${ZONE_FIELD_LABELS[field]} <button class="zone-box-remove" data-field="${field}">&times;</button></span>`;
    layer.appendChild(div);
  }
}

const zoneBoxLayer = document.getElementById("zoneBoxLayer");

zoneBoxLayer.addEventListener("click", (e) => {
  const removeBtn = e.target.closest(".zone-box-remove");
  if (!removeBtn) return;
  e.stopPropagation();
  delete currentZones[removeBtn.dataset.field];
  renderZoneBoxes();
});

zoneBoxLayer.addEventListener("mousedown", (e) => {
  if (e.target.closest(".zone-box-remove")) return;
  const rect = zoneBoxLayer.getBoundingClientRect();
  zoneDrawing = { startX: e.clientX - rect.left, startY: e.clientY - rect.top };
  const tempDiv = document.createElement("div");
  tempDiv.id = "zoneBoxTemp";
  tempDiv.className = "zone-box zone-box-drawing";
  zoneBoxLayer.appendChild(tempDiv);
});

zoneBoxLayer.addEventListener("mousemove", (e) => {
  if (!zoneDrawing) return;
  const rect = zoneBoxLayer.getBoundingClientRect();
  const curX = e.clientX - rect.left;
  const curY = e.clientY - rect.top;
  const tempDiv = document.getElementById("zoneBoxTemp");
  if (!tempDiv) return;
  tempDiv.style.left = `${Math.min(zoneDrawing.startX, curX)}px`;
  tempDiv.style.top = `${Math.min(zoneDrawing.startY, curY)}px`;
  tempDiv.style.width = `${Math.abs(curX - zoneDrawing.startX)}px`;
  tempDiv.style.height = `${Math.abs(curY - zoneDrawing.startY)}px`;
});

window.addEventListener("mouseup", (e) => {
  if (!zoneDrawing) return;
  const rect = zoneBoxLayer.getBoundingClientRect();
  const curX = Math.min(Math.max(e.clientX - rect.left, 0), rect.width);
  const curY = Math.min(Math.max(e.clientY - rect.top, 0), rect.height);
  const left = Math.min(zoneDrawing.startX, curX);
  const top = Math.min(zoneDrawing.startY, curY);
  const width = Math.abs(curX - zoneDrawing.startX);
  const height = Math.abs(curY - zoneDrawing.startY);
  const tempDiv = document.getElementById("zoneBoxTemp");
  if (tempDiv) tempDiv.remove();
  zoneDrawing = null;

  if (width < 8 || height < 8 || rect.width === 0 || rect.height === 0) return;

  const field = document.getElementById("zoneFieldSelect").value;
  currentZones[field] = {
    x: left / rect.width,
    y: top / rect.height,
    width: width / rect.width,
    height: height / rect.height,
  };
  renderZoneBoxes();
});

document.getElementById("zoneSaveBtn").addEventListener("click", async () => {
  const name = document.getElementById("zoneProfileName").value.trim();
  const keywords = document.getElementById("zoneProfileKeywords").value.trim();
  if (!name) { alert("Enter a profile name."); return; }
  if (!zoneSampleFile) { alert("Choose a sample slip image."); return; }
  if (Object.keys(currentZones).length === 0) { alert("Draw at least one zone box."); return; }

  const zonesArray = Object.entries(currentZones).map(([field, box]) => ({ field, ...box }));

  const formData = new FormData();
  formData.append("name", name);
  formData.append("identifier_keywords", keywords);
  formData.append("zones_json", JSON.stringify(zonesArray));
  formData.append("sample_image", zoneSampleFile);

  const toastId = showToast("Saving zone profile...", { loading: true });
  const resp = await fetch("/api/zone-profiles", { method: "POST", body: formData });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    updateToast(toastId, err.detail || "Failed to save profile.", { success: false });
    return;
  }
  updateToast(toastId, `Zone profile "${name}" saved.`);
  document.getElementById("zoneCalibrator").hidden = true;
  loadZoneProfiles();
});

document.getElementById("exportZoneProfilesBtn").addEventListener("click", () => {
  window.location.href = "/api/zone-profiles/export";
});

document.getElementById("importZoneProfilesBtn").addEventListener("click", () => {
  document.getElementById("zoneImportInput").click();
});

document.getElementById("zoneImportInput").addEventListener("change", async () => {
  const input = document.getElementById("zoneImportInput");
  const file = input.files[0];
  input.value = "";
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  const toastId = showToast("Importing zone profiles...", { loading: true });
  const resp = await fetch("/api/zone-profiles/import", { method: "POST", body: formData });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    updateToast(toastId, err.detail || "Import failed.", { success: false });
    return;
  }
  const result = await resp.json();
  updateToast(toastId, `Imported ${result.imported} zone profile(s).`);
  loadZoneProfiles();
});

document.getElementById("saveAsSeedBtn").addEventListener("click", async () => {
  const toastId = showToast("Saving as default seed...", { loading: true });
  const resp = await fetch("/api/zone-profiles/save-as-seed", { method: "POST" });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    updateToast(toastId, err.detail || "Failed to save seed.", { success: false });
    return;
  }
  const result = await resp.json();
  updateToast(toastId, `Saved ${result.saved} profile(s) as the default seed for fresh installs.`);
});

// ---------- Theme ----------
const THEME_KEY = "theme-preference";

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  document.querySelectorAll(".theme-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.theme === theme);
  });
}

document.querySelectorAll(".theme-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const theme = btn.dataset.theme;
    localStorage.setItem(THEME_KEY, theme);
    applyTheme(theme);
  });
});

applyTheme(localStorage.getItem(THEME_KEY) === "light" ? "light" : "dark");

// ---------- Init ----------
updateTypeLabels();
updateToolbarForView();
loadSidebar();
loadTransactions();
loadGraph();
