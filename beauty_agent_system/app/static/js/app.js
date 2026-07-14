"use strict";

// ─── Virtual Office — Streaming UI ───────────────────────────────────────────
const DRAFT_KEY = "vo_draft_input";

// ── SVG icon library (Lucide-style, no emoji) ─────────────────────────────────
const IC = {
  chart:   `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>`,
  bulb:    `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="9" y1="18" x2="15" y2="18"/><line x1="10" y1="22" x2="14" y2="22"/><path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14"/></svg>`,
  layers:  `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>`,
  target:  `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>`,
  msg:     `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`,
  check:   `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>`,
  cpu:     `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/></svg>`,
  alert:   `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
  help:    `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
  copy:    `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`,
  done:    `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`,
  user:    `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`,
  clock:   `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`,
  img:     `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>`,
  arrow:   `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>`,
  chevron: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>`,
  thumbUp: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 10v12"/><path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z"/></svg>`,
  thumbDown: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 14V2"/><path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22a3.13 3.13 0 0 1-3-3.88Z"/></svg>`,
  paper:   `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`,
};

// Agent icon keys → SVG (for progress dots)
const AGENT_ICONS = {
  lead_hunter:            `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`,
  sales_assistant:        IC.msg,
  demo_agent:             IC.chart,
  onboarding_agent:       `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/></svg>`,
  customer_success_agent: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
  product_analyst_agent:  `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>`,
  content_strategist:     IC.layers,
};

let currentRunId = null; // run_id of the in-flight SSE run, once known
let pendingImages = []; // [{ url, file }] attached to the message about to be sent
let _liveCard = null;  // the streaming-token card shown while GA is typing
let _liveTextEl = null; // <p> inside _liveCard that receives tokens

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("office-form");
  if (!form) return;

  restoreDraft();
  hydrateHistory();
  initSidebar();
  initAttachments();

  form.addEventListener("submit", handleSubmit);

  const textarea = document.getElementById("raw-text-input");
  autoGrowTextarea(textarea);
  textarea.addEventListener("input", () => {
    localStorage.setItem(DRAFT_KEY, textarea.value);
    autoGrowTextarea(textarea);
  });
  // Enter sends, Shift+Enter adds a newline -- standard chat-app behavior.
  textarea.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit();
    }
  });
});

// ─── Custom confirm modal (replaces browser's ugly confirm()) ─────────────────
function showConfirmModal(title, body, confirmLabel = "ยืนยัน") {
  return new Promise((resolve) => {
    let overlay = document.getElementById("vo-confirm-overlay");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "vo-confirm-overlay";
      overlay.className = "vo-modal-overlay";
      overlay.innerHTML = `
        <div class="vo-modal" role="dialog" aria-modal="true">
          <p class="vo-modal__title"></p>
          <p class="vo-modal__body"></p>
          <div class="vo-modal__actions">
            <button class="btn btn--sm vo-modal__cancel">ยกเลิก</button>
            <button class="btn btn--danger btn--sm vo-modal__ok"></button>
          </div>
        </div>`;
      document.body.appendChild(overlay);
    }
    overlay.querySelector(".vo-modal__title").textContent = title;
    overlay.querySelector(".vo-modal__body").textContent = body || "";
    overlay.querySelector(".vo-modal__ok").textContent = confirmLabel;
    overlay.classList.add("vo-modal-overlay--open");

    const finish = (result) => {
      overlay.classList.remove("vo-modal-overlay--open");
      overlay.querySelector(".vo-modal__cancel").onclick = null;
      overlay.querySelector(".vo-modal__ok").onclick = null;
      overlay.onclick = null;
      resolve(result);
    };
    overlay.querySelector(".vo-modal__cancel").onclick = () => finish(false);
    overlay.querySelector(".vo-modal__ok").onclick    = () => finish(true);
    overlay.onclick = (e) => { if (e.target === overlay) finish(false); };
  });
}

// ─── Sidebar: collapse toggle + new chat + delete ─────────────────────────────
const SIDEBAR_COLLAPSED_KEY = "vo_sidebar_collapsed";

function initSidebar() {
  initSidebarTabs();
  const sidebar = document.getElementById("sidebar");
  if (!sidebar) return; // pages without the sidebar context (none currently)

  if (localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "1") {
    sidebar.classList.add("sidebar--collapsed");
  }
  const toggle = (e) => {
    e?.preventDefault();
    const collapsed = sidebar.classList.toggle("sidebar--collapsed");
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, collapsed ? "1" : "0");
  };
  document.getElementById("sidebar-toggle")?.addEventListener("click", toggle);
  document.getElementById("sidebar-toggle-mobile")?.addEventListener("click", toggle);

  document.getElementById("new-chat-btn")?.addEventListener("click", async () => {
    try {
      const resp = await fetch("/conversations", { method: "POST" });
      const data = await resp.json();
      if (data.id) window.location.href = `/?conversation_id=${data.id}`;
    } catch (_) { /* ignore -- founder can just retry the click */ }
  });

  document.querySelectorAll(".conversation-item__delete").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      e.stopPropagation();
      const id = btn.dataset.id;
      const confirmed = await showConfirmModal("ลบแชทนี้เลยไหม?", "ข้อมูลในแชทนี้จะหายไปหมด", "ลบแชท");
      if (!confirmed) return;
      try {
        await fetch(`/conversations/${id}`, { method: "DELETE" });
        const activeId = document.getElementById("conversation-list")?.dataset.active;
        if (String(activeId) === String(id)) {
          window.location.href = "/";
        } else {
          btn.closest(".conversation-item")?.remove();
        }
      } catch (_) { /* ignore */ }
    });
  });
}

// ─── Sidebar tabs + Leads panel ───────────────────────────────────────────────
const STAGE_OPTIONS = [
  { value: "cold",        label: "ยังไม่เคยคุย" },
  { value: "interested",  label: "สนใจ/กำลังพิจารณา" },
  { value: "negotiating", label: "กำลังต่อรอง" },
  { value: "closed",      label: "ปิดการขายแล้ว" },
  { value: "post_sale",   label: "ดูแลหลังขาย" },
  { value: "churned",     label: "เลิกใช้/หายไป" },
];

const PANEL_MAP = {
  chats:    "conversation-list",
  leads:    "leads-panel",
  inbox:    "inbox-panel",
  facebook: "facebook-panel",
  tiktok:   "tiktok-panel",
};

let _inboxPollTimer = null;

function initSidebarTabs() {
  const tabs = document.querySelectorAll(".sidebar__tab");
  if (!tabs.length) return;

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.tab;
      tabs.forEach((t) => {
        t.classList.toggle("sidebar__tab--active", t === tab);
        t.setAttribute("aria-selected", t === tab ? "true" : "false");
      });
      Object.entries(PANEL_MAP).forEach(([key, panelId]) => {
        const panel = document.getElementById(panelId);
        if (panel) panel.classList.toggle("sidebar__panel--active", key === target);
      });
      if (target === "leads") loadLeads();
      if (target === "facebook") loadFacebookLeads();
      if (target === "tiktok") loadTikTokLeads();
      if (target === "inbox") {
        loadInbox();
        startInboxPolling();
      } else {
        stopInboxPolling();
      }
    });
  });
}

// ─── Chatwoot inbox live feed ──────────────────────────────────────────────────
async function loadInbox() {
  const list = document.getElementById("inbox-list");
  const status = document.getElementById("inbox-status");
  if (!list) return;
  try {
    const resp = await fetch("/chatwoot/conversations/active");
    if (!resp.ok) throw new Error(resp.statusText);
    const convs = await resp.json();
    if (status) status.textContent = `${convs.length} รายการ`;
    if (!convs.length) {
      list.innerHTML = '<p class="leads-empty">ยังไม่มีบทสนทนาที่ AI ดูแล</p>';
      return;
    }
    list.innerHTML = "";
    convs.forEach((c) => list.appendChild(buildInboxItem(c)));
  } catch (e) {
    if (list) list.innerHTML = `<p class="leads-empty">โหลดไม่ได้: ${e.message}</p>`;
  }
}

function startInboxPolling() {
  if (_inboxPollTimer) return;
  _inboxPollTimer = setInterval(loadInbox, 10_000);
}

function stopInboxPolling() {
  if (_inboxPollTimer) { clearInterval(_inboxPollTimer); _inboxPollTimer = null; }
}

function buildInboxItem(conv) {
  const item = el_("div", "inbox-item");

  const nameRow = el_("div", "inbox-item__name");
  nameRow.textContent = conv.shop_name;
  const badge = el_("span", "stage-badge");
  badge.textContent = conv.stage_label || conv.stage;
  // Use the same color map as the leads panel
  const STAGE_COLORS = {
    cold: "#78716c", interested: "#3b82f6", negotiating: "#f59e0b",
    closed: "#10b981", post_sale: "#8b5cf6", churned: "#ef4444",
  };
  badge.style.background = STAGE_COLORS[conv.stage] || "#78716c";
  nameRow.appendChild(badge);

  const preview = el_("div", "inbox-item__preview");
  preview.textContent = conv.last_message || "(ไม่มีข้อความ)";

  const meta = el_("div", "inbox-item__meta");
  const dot = el_("span", `inbox-item__role-dot inbox-item__role-dot--${conv.last_role || "user"}`);
  const time = el_("span", "inbox-item__time");
  if (conv.last_contacted_at) {
    const d = new Date(conv.last_contacted_at);
    time.textContent = d.toLocaleTimeString("th-TH", { hour: "2-digit", minute: "2-digit" });
  }
  const takeoverBtn = el_("button", "takeover-btn");
  takeoverBtn.textContent = "รับช่วงต่อ";
  takeoverBtn.addEventListener("click", async (e) => {
    e.stopPropagation();
    takeoverBtn.disabled = true;
    takeoverBtn.textContent = "...";
    try {
      await fetch(`/chatwoot/conversations/${conv.chatwoot_conversation_id}/takeover`, { method: "POST" });
      takeoverBtn.textContent = "✓ รับแล้ว";
    } catch (_) {
      takeoverBtn.textContent = "รับช่วงต่อ";
      takeoverBtn.disabled = false;
    }
  });
  meta.appendChild(dot);
  meta.appendChild(time);
  meta.appendChild(takeoverBtn);

  item.appendChild(nameRow);
  item.appendChild(preview);
  item.appendChild(meta);
  return item;
}

async function loadLeads() {
  const list = document.getElementById("leads-list");
  if (!list) return;
  try {
    const resp = await fetch("/leads");
    if (!resp.ok) throw new Error(resp.statusText);
    const leads = await resp.json();
    if (!leads.length) {
      list.innerHTML = '<p class="leads-empty">ยังไม่มีลีดในระบบ</p>';
      return;
    }
    list.innerHTML = "";
    leads.forEach((lead) => list.appendChild(buildLeadItem(lead)));
  } catch (e) {
    list.innerHTML = `<p class="leads-empty">โหลดไม่ได้: ${e.message}</p>`;
  }
}

function buildLeadItem(lead) {
  const item = el_("div", "lead-item");
  const name = el_("div", "lead-item__name");
  name.textContent = lead.shop_name;

  const footer = el_("div", "lead-item__footer");

  // Stage badge (color-coded pill)
  const badge = el_("span", "stage-badge");
  badge.textContent = lead.stage_label;
  badge.style.background = lead.stage_color || "#78716c";

  // Stage dropdown for quick editing
  const sel = document.createElement("select");
  sel.className = "stage-select";
  STAGE_OPTIONS.forEach(({ value, label }) => {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = label;
    if (value === lead.stage) opt.selected = true;
    sel.appendChild(opt);
  });
  sel.addEventListener("change", async () => {
    try {
      const fd = new FormData();
      fd.append("stage", sel.value);
      const resp = await fetch(`/leads/${lead.id}/stage`, { method: "PATCH", body: fd });
      const data = await resp.json();
      if (data.ok) {
        badge.textContent = data.stage_label;
        // Update color by looking up from STAGE_OPTIONS mapping (color comes from server)
        loadLeads(); // simple reload to sync colors
      }
    } catch (_) { /* ignore */ }
  });

  // Last contact date
  const lastContact = el_("span", "lead-item__last-contact");
  if (lead.last_contacted_at) {
    const d = new Date(lead.last_contacted_at);
    lastContact.textContent = d.toLocaleDateString("th-TH", { day: "numeric", month: "short" });
  }

  footer.appendChild(badge);
  footer.appendChild(sel);
  footer.appendChild(lastContact);
  item.appendChild(name);
  item.appendChild(footer);
  return item;
}

// ─── Facebook prospecting log ──────────────────────────────────────────────────
async function loadFacebookLeads() {
  const list = document.getElementById("facebook-list");
  const status = document.getElementById("facebook-status");
  if (!list) return;
  try {
    const resp = await fetch("/facebook/leads");
    if (!resp.ok) throw new Error(resp.statusText);
    const leads = await resp.json();
    if (!leads.length) {
      list.innerHTML = '<p class="leads-empty">ยังไม่มีลีดจาก Facebook\n(เปิดใช้งาน FACEBOOK_ENABLED=true)</p>';
      if (status) status.textContent = "ว่าง";
      return;
    }
    if (status) status.textContent = `${leads.length} คน`;
    list.innerHTML = "";
    leads.forEach((lead) => list.appendChild(buildFacebookLeadItem(lead)));
  } catch (e) {
    list.innerHTML = `<p class="leads-empty">โหลดไม่ได้: ${e.message}</p>`;
  }
}

function buildFacebookLeadItem(lead) {
  const item = el_("div", "lead-item fb-lead-item");

  // Name + stage badge
  const name = el_("div", "lead-item__name");
  name.textContent = lead.shop_name;
  const badge = el_("span", "stage-badge");
  badge.textContent = lead.stage_label;
  badge.style.background = lead.stage_color || "#1877F2";
  name.appendChild(badge);

  // Comment snippet
  if (lead.comment_snippet) {
    const snippet = el_("div", "fb-lead__snippet");
    snippet.textContent = `💬 "${lead.comment_snippet}"`;
    item.appendChild(name);
    item.appendChild(snippet);
  } else {
    item.appendChild(name);
  }

  // Footer: Facebook link + time
  const footer = el_("div", "lead-item__footer");
  if (lead.facebook_url) {
    const link = document.createElement("a");
    link.href = lead.facebook_url;
    link.target = "_blank";
    link.rel = "noopener";
    link.className = "fb-lead__link";
    link.textContent = "ดูโปรไฟล์";
    footer.appendChild(link);
  }
  const timeEl = el_("span", "lead-item__last-contact");
  if (lead.created_at) {
    const d = new Date(lead.created_at);
    timeEl.textContent = d.toLocaleDateString("th-TH", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  }
  footer.appendChild(timeEl);
  item.appendChild(footer);
  return item;
}

// ─── TikTok prospecting log ────────────────────────────────────────────────────
async function loadTikTokLeads() {
  const list = document.getElementById("tiktok-list");
  const status = document.getElementById("tiktok-status");
  if (!list) return;
  try {
    const resp = await fetch("/tiktok/leads");
    if (!resp.ok) throw new Error(resp.statusText);
    const leads = await resp.json();
    if (!leads.length) {
      list.innerHTML = '<p class="leads-empty">ยังไม่มีลีดจาก TikTok\n(เปิดใช้งาน TIKTOK_ENABLED=true)</p>';
      if (status) status.textContent = "ว่าง";
      return;
    }
    if (status) status.textContent = `${leads.length} คน`;
    list.innerHTML = "";
    leads.forEach((lead) => list.appendChild(buildTikTokLeadItem(lead)));
  } catch (e) {
    list.innerHTML = `<p class="leads-empty">โหลดไม่ได้: ${e.message}</p>`;
  }
}

function buildTikTokLeadItem(lead) {
  const item = el_("div", "lead-item tt-lead-item");

  // Name + stage badge + merged indicator
  const name = el_("div", "lead-item__name");
  name.textContent = lead.shop_name;
  const badge = el_("span", "stage-badge");
  badge.textContent = lead.stage_label;
  badge.style.background = lead.stage_color || "#010101";
  name.appendChild(badge);
  if (lead.merged) {
    const mergedTag = el_("span", "tt-merged-tag");
    mergedTag.textContent = "merged";
    name.appendChild(mergedTag);
  }

  // Comment snippet
  if (lead.comment_snippet) {
    const snippet = el_("div", "fb-lead__snippet");
    snippet.textContent = `💬 "${lead.comment_snippet}"`;
    item.appendChild(name);
    item.appendChild(snippet);
  } else {
    item.appendChild(name);
  }

  // Footer: video link + time
  const footer = el_("div", "lead-item__footer");
  if (lead.tiktok_video_url) {
    const link = document.createElement("a");
    link.href = lead.tiktok_video_url;
    link.target = "_blank";
    link.rel = "noopener";
    link.className = "tt-lead__link";
    link.textContent = "ดูวิดีโอ";
    footer.appendChild(link);
  }
  const timeEl = el_("span", "lead-item__last-contact");
  if (lead.created_at) {
    const d = new Date(lead.created_at);
    timeEl.textContent = d.toLocaleDateString("th-TH", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  }
  footer.appendChild(timeEl);
  item.appendChild(footer);
  return item;
}

// ─── Image attachments ─────────────────────────────────────────────────────────
function initAttachments() {
  const attachBtn = document.getElementById("attach-btn");
  const imageInput = document.getElementById("image-input");
  if (!attachBtn || !imageInput) return;

  attachBtn.addEventListener("click", () => imageInput.click());
  imageInput.addEventListener("change", async () => {
    const files = Array.from(imageInput.files || []);
    imageInput.value = ""; // allow re-selecting the same file later
    for (const file of files) {
      await uploadAndPreviewImage(file);
    }
  });
}

async function uploadAndPreviewImage(file) {
  const previews = document.getElementById("attachment-previews");
  const chip = el_("div", "attachment-chip attachment-chip--uploading");
  const localUrl = URL.createObjectURL(file);
  chip.innerHTML = `<img src="${localUrl}" alt="" /><span class="attachment-chip__spinner"></span>`;
  previews.hidden = false;
  previews.appendChild(chip);

  try {
    const fd = new FormData();
    fd.append("file", file);
    const resp = await fetch("/images/upload", { method: "POST", body: fd });
    if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).detail || "อัปโหลดไม่สำเร็จ");
    const data = await resp.json();
    pendingImages.push({ url: data.url });
    chip.classList.remove("attachment-chip--uploading");
    const removeBtn = el_("button", "attachment-chip__remove");
    removeBtn.type = "button";
    removeBtn.innerHTML = "&times;";
    removeBtn.addEventListener("click", () => {
      pendingImages = pendingImages.filter(p => p.url !== data.url);
      chip.remove();
      if (!pendingImages.length) previews.hidden = true;
    });
    chip.appendChild(removeBtn);
  } catch (err) {
    chip.remove();
    if (!previews.children.length) previews.hidden = true;
    appendToThread(errorBanner(err.message || "อัปโหลดรูปไม่สำเร็จ"));
  }
}

function clearAttachments() {
  pendingImages = [];
  const previews = document.getElementById("attachment-previews");
  if (previews) { previews.innerHTML = ""; previews.hidden = true; }
}

// ─── Draft persistence (typed input must survive a refresh) ──────────────────
function restoreDraft() {
  const textarea = document.getElementById("raw-text-input");
  const saved = localStorage.getItem(DRAFT_KEY);
  if (saved && !textarea.value.trim()) textarea.value = saved;
}

// ─── History hydration (DB is the source of truth -- a refresh never loses
// the thread; every run the founder has ever submitted stays visible) ─────────
async function hydrateHistory() {
  try {
    const resp = await fetch(`/runs/recent?conversation_id=${getConversationId()}`);
    if (!resp.ok) return;
    const runs = await resp.json();
    for (const run of runs) {
      appendRunToThread(run, { live: false });
    }
    scrollThreadToBottom();
  } catch (_) { /* history is a nice-to-have; ignore failures */ }
}

function getConversationId() {
  return document.getElementById("conversation-id-input")?.value || "";
}

// ─── Chat scroll container (the only thing that scrolls -- the composer
// stays pinned to the bottom of the viewport like a normal AI chat app) ────
function scrollChatToBottom(behavior = "smooth") {
  const area = document.getElementById("chat-scroll");
  if (!area) return;
  area.scrollTo({ top: area.scrollHeight, behavior });
}

// Textarea auto-grows a little as the founder types a longer message,
// instead of staying a fixed single line.
function autoGrowTextarea(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
}

// ─── Form submit ──────────────────────────────────────────────────────────────
async function handleSubmit(e) {
  e.preventDefault();
  const form = e.currentTarget;
  const textarea = form.querySelector("#raw-text-input");
  const rawText = textarea.value.trim();
  const imageUrls = pendingImages.map(p => p.url);
  if (!rawText && !imageUrls.length) return;

  appendUserBubble(rawText, imageUrls);
  textarea.value = "";
  autoGrowTextarea(textarea);
  localStorage.removeItem(DRAFT_KEY);
  clearAttachments();

  setSubmitting(true);
  showProgress();

  const fd = new FormData();
  fd.append("raw_text", rawText);
  fd.append("conversation_id", getConversationId());
  fd.append("image_urls", JSON.stringify(imageUrls));

  try {
    const resp = await fetch("/run/stream", { method: "POST", body: fd });
    if (!resp.ok) throw new Error(`Server error ${resp.status}`);
    await readSSE(resp);
  } catch (err) {
    appendToThread(errorBanner(err.message || String(err)));
  } finally {
    hideProgress();
    setSubmitting(false);
  }
}

// ─── SSE reader ───────────────────────────────────────────────────────────────
async function readSSE(resp) {
  const reader = resp.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop();
    for (const part of parts) {
      const line = part.split("\n").find(l => l.startsWith("data: "));
      if (!line) continue;
      try { handleEvent(JSON.parse(line.slice(6))); } catch (_) {}
    }
  }
}

// ─── Event dispatch ───────────────────────────────────────────────────────────
function handleEvent(ev) {
  switch (ev.type) {
    case "supervisor_thinking": showThinkingCloud(ev.text || "กำลังคิด..."); break;
    case "planning":   hideThinkingCloud(); updateProgressAgents(ev.plan_trace?.assignments || []); break;
    case "agent_start": markAgentTyping(ev.agent); break;
    case "agent_done": markAgentDone(ev.agent); renderInterimAgentCard(ev); break;
    case "reviewing":  showThinkingCloud(ev.text || "กำลังตรวจสอบและสรุปผล..."); break;
    case "token":      appendToken(ev.text || ""); break;
    case "final":      onFinal(ev); break;
    case "error":      appendToThread(errorBanner(ev.message)); break;
  }
  scrollChatToBottom();
}

// ─── Progress area ────────────────────────────────────────────────────────────
function showProgress() {
  document.getElementById("progress-area").hidden = false;
  scrollChatToBottom();
}
function hideProgress() {
  document.getElementById("progress-area").hidden = true;
  hideThinkingCloud();
}

function showThinkingCloud(text) {
  const cloud = document.getElementById("thinking-cloud");
  document.getElementById("thinking-cloud__text").textContent = text;
  cloud.hidden = false;
}
function hideThinkingCloud() {
  document.getElementById("thinking-cloud").hidden = true;
}

function updateProgressAgents(assignments) {
  const container = document.getElementById("progress-agents");
  container.innerHTML = "";
  for (const a of assignments) {
    const el = document.createElement("span");
    el.className = "progress-agent progress-agent--queued";
    el.id = `pa-${a.agent}`;
    const icon = AGENT_ICONS[a.agent] || IC.cpu;
    el.innerHTML = `
      <span class="agent-dot"></span>
      <span class="agent-icon">${icon}</span>
      <span class="agent-label">${esc(a.label)}</span>
      <span class="agent-typing"><i></i><i></i><i></i></span>`;
    container.appendChild(el);
  }
}

function markAgentTyping(agent) {
  const el = document.getElementById(`pa-${agent}`);
  if (!el) return;
  el.classList.remove("progress-agent--queued");
  el.classList.add("progress-agent--working");
}

function markAgentDone(agent) {
  const el = document.getElementById(`pa-${agent}`);
  if (!el) return;
  el.classList.remove("progress-agent--working");
  el.classList.add("progress-agent--done");
  el.querySelector(".agent-dot").innerHTML = IC.done;
  el.querySelector(".agent-dot").classList.add("agent-dot--done");
  flyHandoffPaper(el);
}

// ─── "Handoff" animation: a little paper flies from the agent chip that just
// finished up toward the thinking-cloud/Supervisor spot, so work visibly
// passes hand-to-hand instead of just silently ticking a checkbox ──────────────
function flyHandoffPaper(sourceEl) {
  const target = document.getElementById("thinking-cloud") || document.getElementById("progress-bar-wrap");
  if (!sourceEl || !target) return;
  const srcRect = sourceEl.getBoundingClientRect();
  const tgtRect = target.getBoundingClientRect();

  const paper = document.createElement("div");
  paper.className = "handoff-paper";
  paper.innerHTML = IC.paper;
  paper.style.left = `${srcRect.left + srcRect.width / 2}px`;
  paper.style.top = `${srcRect.top + srcRect.height / 2}px`;
  document.body.appendChild(paper);

  const dx = (tgtRect.left + tgtRect.width / 2) - (srcRect.left + srcRect.width / 2);
  const dy = (tgtRect.top + tgtRect.height / 2) - (srcRect.top + srcRect.height / 2);

  requestAnimationFrame(() => {
    paper.style.transform = `translate(${dx}px, ${dy}px) rotate(340deg) scale(0.4)`;
    paper.style.opacity = "0";
  });
  setTimeout(() => paper.remove(), 750);
}

// ─── Chat thread (history) ─────────────────────────────────────────────────────
function appendUserBubble(text, imageUrls = []) {
  const bubble = el_("div", "chat-bubble chat-bubble--user");
  bubble.innerHTML = `<span class="chat-bubble__icon">${IC.user}</span><span class="chat-bubble__text"></span>`;
  bubble.querySelector(".chat-bubble__text").textContent = text;
  if (imageUrls.length) {
    const imgs = el_("div", "chat-bubble__images");
    for (const url of imageUrls) {
      const img = document.createElement("img");
      img.src = url;
      img.alt = "รูปที่แนบมา";
      imgs.appendChild(img);
    }
    bubble.appendChild(imgs);
  }
  appendToThread(bubble);
}

// ─── Token streaming (general_assistant streams plain text live) ──────────────
function appendToken(text) {
  if (!_liveCard) {
    _liveCard = el_("div", "result-card result-card--live");
    _liveTextEl = el_("p", "live-answer-text");
    _liveCard.appendChild(_liveTextEl);
    appendToThread(_liveCard);
  }
  _liveTextEl.textContent += text;
  scrollChatToBottom();
}

function clearLiveCard() {
  if (_liveCard) {
    _liveCard.remove();
    _liveCard = null;
    _liveTextEl = null;
  }
}

function onFinal(ev) {
  currentRunId = ev.run_id;
  clearLiveCard();
  clearInterimAgentCards();
  appendRunToThread(ev, { live: true });
}

function appendRunToThread(run, { live }) {
  // If this is the live in-flight run, the user bubble is already appended
  // by handleSubmit(); for history hydration, show both bubble + card.
  if (!live && run.raw_text) appendUserBubble(run.raw_text, run.image_urls || []);
  const { card, sections } = buildResultCard(run, { live });
  appendToThread(card);
  revealSectionsSequentially(card, sections, { live });
}

// ─── Progressive per-agent reveal: as soon as one agent finishes, show its
// own findings/answer right away instead of making the founder wait for the
// single merged "final" card at the end -- these interim cards are removed
// once the final synthesized card lands. ────────────────────────────────────
function clearInterimAgentCards() {
  document.querySelectorAll(".interim-agent-card").forEach(el => el.remove());
}

function renderInterimAgentCard(ev) {
  const hasContent = (ev.findings && ev.findings.length) || ev.answer_text || ev.draft_message;
  if (!hasContent) return;

  const card = el_("div", "result-card interim-agent-card");
  const icon = AGENT_ICONS[ev.agent] || IC.cpu;
  card.innerHTML = `
    <div class="result-card__header">
      <span class="result-card__title">${icon} ${esc(ev.label)}</span>
    </div>`;

  if (ev.answer_text) {
    const sec = section(IC.msg, "คำตอบ");
    const p = el_("p", "interim-answer-text");
    p.textContent = ev.answer_text;
    sec.appendChild(p);
    card.appendChild(sec);
  } else if (ev.findings && ev.findings.length) {
    const sec = section(IC.chart, "สิ่งที่พบ");
    sec.appendChild(condensedList(ev.findings, "result-list", 3));
    card.appendChild(sec);
  }

  card.classList.add("result-section--incoming");
  appendToThread(card);
  requestAnimationFrame(() => card.classList.remove("result-section--incoming"));
}

function appendToThread(el) {
  const area = document.getElementById("history-area");
  if (area) {
    area.appendChild(el);
    el.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

function scrollThreadToBottom() {
  scrollChatToBottom("auto");
}

// ─── Result card builder ───────────────────────────────────────────────────────
function buildResultCard(ev, { live } = {}) {
  const {
    key_findings = [], content_ideas = [], founder_actions = [],
    ai_actions = [], missing_info = [], questions = [],
    content_plan = [], target_profile = "", pitch_timing = "", product_pitch = "",
    draft, agents_run = [], run_id, outcome = null, founder_note = null,
    general_answer = null,
  } = ev;

  const card = el_("div", "result-card");
  // Sections are collected here instead of appended directly so the caller
  // can reveal them one-by-one (progressive "streaming" feel) instead of
  // dumping the whole analysis on screen in one frame.
  const sections = [];

  // Header
  const tags = agents_run.map(l => `<span class="tag">${esc(l)}</span>`).join("");
  card.innerHTML = `
    <div class="result-card__header">
      <span class="result-card__title">${IC.layers} ผลวิเคราะห์<span class="result-card__tags">${tags}</span></span>
    </div>`;

  // ── 0. General answer (freeform reply from the General Assistant, when
  // the message was a general/non-CSC question or had an image attached) ────
  if (general_answer) {
    const sec = section(IC.msg, "คำตอบ", "result-section--general-answer");
    const p = el_("p", "general-answer-text");
    p.textContent = general_answer;
    sec.appendChild(p);
    sections.push(sec);
  }

  // ── 1. Questions ──────────────────────────────────────────────────────────
  if (questions.length) {
    const sec = section(IC.help, "ทีม AI มีคำถาม", "result-section--attention");
    for (const q of questions) {
      const qb = el_("div", "question-block");
      qb.innerHTML = `<p><strong>${esc(q.label)}</strong>: ${esc(q.question)}</p>`;

      const chips = el_("div", "question-chips");
      const QUICK = [
        "ข้อมูลที่มีอยู่ก็พอแล้ว ทำต่อได้เลย",
        "ยังไม่รู้เหมือนกัน",
        "ข้ามคำถามนี้ไปก่อน",
      ];
      let selectedAnswer = "";
      const textarea = el_("textarea", "question-custom");
      textarea.rows = 2;
      textarea.placeholder = "หรือพิมพ์คำตอบเอง...";
      textarea.addEventListener("input", () => { selectedAnswer = textarea.value; });

      for (const label of QUICK) {
        const btn = el_("button", "chip-btn");
        btn.type = "button";
        btn.textContent = label;
        btn.addEventListener("click", () => {
          selectedAnswer = label;
          textarea.value = "";
          chips.querySelectorAll(".chip-btn").forEach(b => b.classList.remove("chip-btn--selected"));
          btn.classList.add("chip-btn--selected");
        });
        chips.appendChild(btn);
      }

      const sendBtn = el_("button", "btn btn--primary btn--sm");
      sendBtn.type = "button";
      sendBtn.style.marginTop = "8px";
      sendBtn.textContent = "ส่งคำตอบ";
      sendBtn.addEventListener("click", async () => {
        const answer = selectedAnswer || textarea.value.trim();
        if (!answer || !run_id) return;
        sendBtn.disabled = true;
        sendBtn.textContent = "กำลังส่ง...";

        // Step 1: ask the backend to build the combined text (original raw_text +
        // answer annotation) and return the conversation to stream into.
        const continueFd = new FormData();
        continueFd.append("previous_run_id", String(run_id));
        continueFd.append("answer", answer);
        let combinedText, conversationId;
        try {
          const continueResp = await fetch("/run/continue", { method: "POST", body: continueFd });
          if (!continueResp.ok) throw new Error(`continue error ${continueResp.status}`);
          const data = await continueResp.json();
          combinedText = data.combined_text;
          conversationId = data.conversation_id;
        } catch (err) {
          sendBtn.disabled = false;
          sendBtn.textContent = "ส่งคำตอบ";
          appendToThread(errorBanner(err.message || "ส่งคำตอบไม่สำเร็จ"));
          return;
        }

        // Step 2: stream the re-run through the normal SSE pipeline so the
        // founder gets real-time progress instead of a full-page reload.
        appendUserBubble(`[ตอบคำถาม] ${answer}`);
        setSubmitting(true);
        showProgress();
        const streamFd = new FormData();
        streamFd.append("raw_text", combinedText);
        streamFd.append("conversation_id", String(conversationId || ""));
        streamFd.append("image_urls", "[]");
        try {
          const streamResp = await fetch("/run/stream", { method: "POST", body: streamFd });
          if (!streamResp.ok) throw new Error(`Server error ${streamResp.status}`);
          await readSSE(streamResp);
        } catch (err) {
          appendToThread(errorBanner(err.message || String(err)));
        } finally {
          hideProgress();
          setSubmitting(false);
        }
      });

      qb.appendChild(chips);
      qb.appendChild(textarea);
      qb.appendChild(sendBtn);
      sec.appendChild(qb);
    }
    sections.push(sec);
  }

  // ── 2. Key findings (condensed -- founder said 3 pages of bullets is too
  // much most of the time, so show the top few and let them expand) ─────────
  if (key_findings.length) {
    const sec = section(IC.chart, "สิ่งที่วิเคราะห์พบ");
    sec.appendChild(condensedList(key_findings, "result-list", 3));
    sections.push(sec);
  }

  // ── 3. Content plan (step-by-step, Notion-style) ──────────────────────────
  if (content_plan.length || target_profile || pitch_timing || product_pitch) {
    const sec = section(IC.layers, "แผนโพสต์ Facebook — ขั้นตอน", "result-section--plan");

    if (target_profile) {
      const chip = el_("div", "profile-chip");
      chip.innerHTML = `<span class="chip-icon">${IC.target}</span><strong>กลุ่มเป้าหมาย:</strong> ${esc(target_profile)}`;
      sec.appendChild(chip);
    }

    for (const step of content_plan) {
      const stepEl = el_("div", "plan-step");

      const header = el_("div", "plan-step__header");
      header.innerHTML = `
        <span class="step-badge">Step ${esc(String(step.step || ""))}</span>
        <span class="step-phase">${esc(step.phase || "")}</span>`;
      stepEl.appendChild(header);

      if (step.group) {
        const row = el_("div", "plan-row");
        row.innerHTML = `<span class="plan-row__label">${IC.target} กลุ่ม</span><span class="plan-row__val">${esc(step.group)}</span>`;
        stepEl.appendChild(row);
      }

      if (step.target_audience) {
        const row = el_("div", "plan-row");
        row.innerHTML = `<span class="plan-row__label">${IC.user} เป้าหมาย</span><span class="plan-row__val">${esc(step.target_audience)}</span>`;
        stepEl.appendChild(row);
      }

      if (step.copy) {
        const copyWrap = el_("div", "plan-copy-wrap");
        const copyBox = el_("div", "plan-copy-box");
        copyBox.textContent = step.copy;
        const copyBtn = el_("button", "mini-copy-btn");
        copyBtn.type = "button";
        copyBtn.innerHTML = IC.copy + " คัดลอก";
        copyBtn.addEventListener("click", () => {
          navigator.clipboard.writeText(step.copy).then(() => {
            copyBtn.innerHTML = IC.done + " คัดลอกแล้ว";
            copyBtn.classList.add("mini-copy-btn--done");
            setTimeout(() => {
              copyBtn.innerHTML = IC.copy + " คัดลอก";
              copyBtn.classList.remove("mini-copy-btn--done");
            }, 2000);
          });
        });
        copyWrap.appendChild(copyBox);
        copyWrap.appendChild(copyBtn);
        stepEl.appendChild(copyWrap);
      }

      if (step.image) {
        const row = el_("div", "plan-row");
        row.innerHTML = `<span class="plan-row__label">${IC.img} ภาพ</span><span class="plan-row__val plan-row__val--muted">${esc(step.image)}</span>`;
        stepEl.appendChild(row);
      }

      if (step.goal_metric || step.goal) {
        const row = el_("div", "plan-row");
        row.innerHTML = `<span class="plan-row__label">${IC.arrow} เป้า</span><span class="plan-row__val">${esc(step.goal_metric || step.goal)}</span>`;
        stepEl.appendChild(row);
      }

      if (step.engagement_tactic) {
        const row = el_("div", "plan-row");
        row.innerHTML = `<span class="plan-row__label">${IC.bulb} กระตุ้นปฏิสัมพันธ์</span><span class="plan-row__val">${esc(step.engagement_tactic)}</span>`;
        stepEl.appendChild(row);
      }

      if (step.cta) {
        const ctaEl = el_("div", "plan-cta");
        ctaEl.innerHTML = `<span class="plan-cta__label">หลังโพสต์:</span> ${esc(step.cta)}`;
        stepEl.appendChild(ctaEl);
      }

      sec.appendChild(stepEl);
    }

    if (pitch_timing || product_pitch) {
      const pitchWrap = el_("div", "pitch-wrap");
      if (pitch_timing) {
        const row = el_("div", "pitch-row");
        row.innerHTML = `<div class="pitch-row__label">${IC.clock} เสนอขายเมื่อไหร่</div><div class="pitch-row__val">${esc(pitch_timing)}</div>`;
        pitchWrap.appendChild(row);
      }
      if (product_pitch) {
        const row = el_("div", "pitch-row");
        row.innerHTML = `<div class="pitch-row__label">${IC.msg} อธิบายระบบ</div><div class="pitch-row__val">${esc(product_pitch)}</div>`;
        pitchWrap.appendChild(row);
      }
      sec.appendChild(pitchWrap);
    }

    sections.push(sec);
  }

  // ── 4. Content ideas ──────────────────────────────────────────────────────
  if (content_ideas.length) {
    const sec = section(IC.bulb, "ไอเดียคอนเทนต์เพิ่มเติม", "result-section--ideas");
    sec.appendChild(condensedList(content_ideas, "ideas-list", 3, true));
    sections.push(sec);
  }

  // ── 5. Draft message ──────────────────────────────────────────────────────
  if (draft?.message) {
    const sec = section(IC.msg, "ข้อความทักลูกค้า (ร่างจาก Sales Assistant)", "result-section--draft");

    const box = el_("div", "draft-box");
    box.textContent = draft.message;
    sec.appendChild(box);

    const copyBtn = el_("button", "copy-btn");
    copyBtn.type = "button";
    copyBtn.innerHTML = `${IC.copy} คัดลอกข้อความ`;
    copyBtn.addEventListener("click", () => {
      navigator.clipboard.writeText(draft.message).then(() => {
        copyBtn.innerHTML = `${IC.done} คัดลอกแล้ว`;
        copyBtn.classList.add("copy-btn--copied");
        setTimeout(() => {
          copyBtn.innerHTML = `${IC.copy} คัดลอกข้อความ`;
          copyBtn.classList.remove("copy-btn--copied");
        }, 2000);
      });
    });
    sec.appendChild(copyBtn);

    if (draft.reasoning) {
      const details = document.createElement("details");
      details.className = "reasoning";
      details.style.marginTop = "10px";
      details.innerHTML = `<summary>เหตุผลที่เลือกมุมนี้</summary><p style="font-size:0.84rem;color:var(--muted)">${esc(draft.reasoning)}</p>`;
      sec.appendChild(details);
    }
    sections.push(sec);
  }

  // ── 6. Founder actions (AI thinks → คุณ action) ───────────────────────────
  if (founder_actions.length) {
    const sec = section(IC.check, "สิ่งที่คุณต้องทำ", "result-section--actions");
    const list = el_("ul", "task-list");
    founder_actions.forEach((action, i) => {
      list.appendChild(renderActionItem(action, i));
    });
    sec.appendChild(list);
    sections.push(sec);
  }

  // ── 7. AI actions ─────────────────────────────────────────────────────────
  if (ai_actions.length) {
    const sec = section(IC.cpu, "AI จะทำต่อเอง");
    sec.appendChild(condensedList(ai_actions, "result-list result-list--ai", 3));
    sections.push(sec);
  }

  // ── 8. Missing info ───────────────────────────────────────────────────────
  const realMissing = missing_info.filter(m => !m.includes("AI ไม่พร้อมใช้งาน"));
  if (realMissing.length) {
    const sec = section(IC.alert, "ข้อมูลที่ยังขาด");
    sec.appendChild(condensedList(realMissing, "result-list result-list--warn", 3));
    sections.push(sec);
  }

  // ── 9. Feedback (accept/reject → feeds back into future runs) ─────────────
  if (run_id) {
    sections.push(buildFeedbackRow(run_id, outcome, founder_note));
  }

  return { card, sections };
}

// ─── Reveal a result card's sections one at a time, each with a small
// stagger + fade/slide-in, so a founder can read a section that's already
// done while later ones are still "arriving" -- instead of the whole
// analysis appearing in one frame. History hydration (live=false) reveals
// everything instantly so reloading the page doesn't feel slow. ──────────
function revealSectionsSequentially(card, sections, { live } = {}) {
  if (!live) {
    sections.forEach(sec => card.appendChild(sec));
    return;
  }
  let i = 0;
  const revealNext = () => {
    if (i >= sections.length) return;
    const sec = sections[i++];
    sec.classList.add("result-section--incoming");
    card.appendChild(sec);
    scrollChatToBottom();
    requestAnimationFrame(() => sec.classList.remove("result-section--incoming"));
    setTimeout(revealNext, 260);
  };
  revealNext();
}

// ─── Condensed list: show first N items, "ดูเพิ่มเติม" toggles the rest ────────
function condensedList(items, className, visibleCount, asIdeas = false) {
  const wrap = el_("div", "condensed-list-wrap");
  const list = el_("ul", className);

  const renderItem = (item) => {
    const li = document.createElement("li");
    if (asIdeas) {
      li.innerHTML = `<span class="idea-dot"></span><span></span>`;
      li.querySelector("span:last-child").textContent = item;
    } else {
      li.textContent = item;
    }
    return li;
  };

  items.slice(0, visibleCount).forEach(item => list.appendChild(renderItem(item)));
  wrap.appendChild(list);

  if (items.length > visibleCount) {
    const rest = el_("ul", `${className} condensed-list__rest`);
    rest.hidden = true;
    items.slice(visibleCount).forEach(item => rest.appendChild(renderItem(item)));
    wrap.appendChild(rest);

    const toggle = el_("button", "condensed-list__toggle");
    toggle.type = "button";
    const remaining = items.length - visibleCount;
    toggle.innerHTML = `${IC.chevron} ดูเพิ่มเติมอีก ${remaining} ข้อ`;
    toggle.addEventListener("click", () => {
      const expanded = !rest.hidden;
      rest.hidden = expanded;
      toggle.classList.toggle("condensed-list__toggle--open", !expanded);
      toggle.innerHTML = expanded
        ? `${IC.chevron} ดูเพิ่มเติมอีก ${remaining} ข้อ`
        : `${IC.chevron} ย่อกลับ`;
    });
    wrap.appendChild(toggle);
  }

  return wrap;
}

// ─── Feedback row: this run's output — accepted / rejected + optional note ────
function buildFeedbackRow(runId, outcome, founderNote) {
  const wrap = el_("div", "feedback-row");
  if (outcome) {
    wrap.classList.add("feedback-row--done");
    const label = outcome === "accepted" ? "คุณบอกว่าใช้ได้" : "คุณบอกว่าไม่เวิร์ก";
    const icon = outcome === "accepted" ? IC.thumbUp : IC.thumbDown;
    wrap.innerHTML = `<span class="feedback-row__done">${icon} ${label}</span>`;
    if (founderNote) {
      wrap.innerHTML += `<span class="feedback-row__note">"${esc(founderNote)}"</span>`;
    }
    return wrap;
  }

  wrap.innerHTML = `<span class="feedback-row__label">ผลลัพธ์นี้เป็นยังไงบ้าง? (ช่วยให้ทีม AI เรียนรู้ต่อไป)</span>`;
  const btnRow = el_("div", "feedback-row__btns");
  const noteInput = el_("input", "feedback-row__note-input");
  noteInput.type = "text";
  noteInput.placeholder = "โน้ตสั้นๆ (ไม่บังคับ) เช่น ลูกค้าตอบรับ/เงียบ/ปฏิเสธเพราะอะไร";
  noteInput.hidden = true;

  const submitFeedback = async (outcomeVal, btn) => {
    btn.disabled = true;
    const fd = new FormData();
    fd.append("outcome", outcomeVal);
    fd.append("founder_note", noteInput.value.trim());
    try {
      await fetch(`/runs/${runId}/feedback`, { method: "POST", body: fd });
      wrap.classList.add("feedback-row--done");
      const label = outcomeVal === "accepted" ? "บันทึกแล้ว — ใช้ได้" : "บันทึกแล้ว — ไม่เวิร์ก";
      const icon = outcomeVal === "accepted" ? IC.thumbUp : IC.thumbDown;
      wrap.innerHTML = `<span class="feedback-row__done">${icon} ${label}</span>`;
    } catch (_) {
      btn.disabled = false;
    }
  };

  const upBtn = el_("button", "feedback-btn feedback-btn--up");
  upBtn.type = "button";
  upBtn.innerHTML = `${IC.thumbUp} ใช้ได้`;
  upBtn.addEventListener("click", () => submitFeedback("accepted", upBtn));

  const downBtn = el_("button", "feedback-btn feedback-btn--down");
  downBtn.type = "button";
  downBtn.innerHTML = `${IC.thumbDown} ไม่เวิร์ก`;
  downBtn.addEventListener("click", () => { noteInput.hidden = false; noteInput.focus(); });
  downBtn.addEventListener("dblclick", () => submitFeedback("rejected", downBtn));

  const sendNoteBtn = el_("button", "feedback-btn feedback-btn--sm");
  sendNoteBtn.type = "button";
  sendNoteBtn.textContent = "ส่ง";
  sendNoteBtn.hidden = true;
  noteInput.addEventListener("input", () => { sendNoteBtn.hidden = false; });
  sendNoteBtn.addEventListener("click", () => submitFeedback("rejected", downBtn));

  btnRow.appendChild(upBtn);
  btnRow.appendChild(downBtn);
  btnRow.appendChild(noteInput);
  btnRow.appendChild(sendNoteBtn);
  wrap.appendChild(btnRow);
  return wrap;
}

// ─── Action item card (expandable — 6-field strategic breakdown) ──────────────
function renderActionItem(action, i) {
  const li = document.createElement("li");
  li.className = "task-item";

  // Backward-compat: older runs stored founder_actions as plain strings.
  if (typeof action === "string" || action == null) {
    li.innerHTML = `
      <span class="task-num">${i + 1}</span>
      <span class="task-body">${esc(action)}</span>`;
    return li;
  }

  const {
    action: actionText = "", goal_metric = "", target_audience = "",
    where_and_how_many = "", reasoning = "", engagement_tactic = "",
  } = action;

  const details = document.createElement("details");
  details.className = "task-details";

  const summary = document.createElement("summary");
  summary.className = "task-summary";
  summary.innerHTML = `
    <span class="task-num">${i + 1}</span>
    <span class="task-body">${esc(actionText)}</span>
    <span class="task-expand-icon">${IC.arrow}</span>`;
  details.appendChild(summary);

  const body = el_("div", "task-detail-body");
  const rows = [
    [IC.target, "เป้าหมาย", goal_metric],
    [IC.user, "กลุ่มเป้าหมาย", target_audience],
    [IC.layers, "ที่ไหน/กี่จุด", where_and_how_many],
    [IC.bulb, "ทำไมถึงจะได้ผล", reasoning],
    [IC.chart, "วิธีกระตุ้นปฏิสัมพันธ์", engagement_tactic],
  ];
  for (const [icon, label, val] of rows) {
    if (!val) continue;
    const row = el_("div", "task-detail-row");
    row.innerHTML = `<span class="task-detail-row__label">${icon} ${label}</span><span class="task-detail-row__val">${esc(val)}</span>`;
    body.appendChild(row);
  }
  details.appendChild(body);
  li.appendChild(details);
  return li;
}

// ─── Utilities ────────────────────────────────────────────────────────────────
function section(iconHtml, label, extraClass = "") {
  const sec = el_("div", `result-section ${extraClass}`.trim());
  const lbl = el_("div", "section-label");
  lbl.innerHTML = `<span class="section-icon">${iconHtml}</span>${label}`;
  sec.appendChild(lbl);
  return sec;
}

function errorBanner(msg) {
  const el = el_("div", "error-banner");
  el.innerHTML = `${IC.alert} ${esc(msg)}`;
  return el;
}

function setSubmitting(on) {
  const btn = document.getElementById("submit-btn");
  if (!btn) return;
  btn.disabled = on;
  btn.querySelector(".btn-text").hidden = on;
  btn.querySelector(".btn-spinner").hidden = !on;
}

function el_(tag, className) {
  const e = document.createElement(tag);
  if (className) e.className = className;
  return e;
}

function esc(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
