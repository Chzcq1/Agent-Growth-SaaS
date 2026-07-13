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

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("office-form");
  if (!form) return;

  restoreDraft();
  hydrateHistory();

  form.addEventListener("submit", handleSubmit);

  const textarea = document.getElementById("raw-text-input");
  textarea.addEventListener("input", () => {
    localStorage.setItem(DRAFT_KEY, textarea.value);
  });
});

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
    const resp = await fetch("/runs/recent");
    if (!resp.ok) return;
    const runs = await resp.json();
    for (const run of runs) {
      appendRunToThread(run, { live: false });
    }
    scrollThreadToBottom();
  } catch (_) { /* history is a nice-to-have; ignore failures */ }
}

// ─── Form submit ──────────────────────────────────────────────────────────────
async function handleSubmit(e) {
  e.preventDefault();
  const form = e.currentTarget;
  const textarea = form.querySelector("#raw-text-input");
  const rawText = textarea.value.trim();
  if (!rawText) return;

  appendUserBubble(rawText);
  textarea.value = "";
  localStorage.removeItem(DRAFT_KEY);

  setSubmitting(true);
  showProgress();

  const fd = new FormData();
  fd.append("raw_text", rawText);

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
    case "agent_done": markAgentDone(ev.agent); break;
    case "final":      onFinal(ev); break;
    case "error":      appendToThread(errorBanner(ev.message)); break;
  }
}

// ─── Progress area ────────────────────────────────────────────────────────────
function showProgress() { document.getElementById("progress-area").hidden = false; }
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
function appendUserBubble(text) {
  const bubble = el_("div", "chat-bubble chat-bubble--user");
  bubble.innerHTML = `<span class="chat-bubble__icon">${IC.user}</span><span class="chat-bubble__text"></span>`;
  bubble.querySelector(".chat-bubble__text").textContent = text;
  appendToThread(bubble);
}

function onFinal(ev) {
  currentRunId = ev.run_id;
  appendRunToThread(ev, { live: true });
}

function appendRunToThread(run, { live }) {
  // If this is the live in-flight run, the user bubble is already appended
  // by handleSubmit(); for history hydration, show both bubble + card.
  if (!live && run.raw_text) appendUserBubble(run.raw_text);
  const card = buildResultCard(run, { live });
  appendToThread(card);
}

function appendToThread(el) {
  const area = document.getElementById("history-area");
  if (area) {
    area.appendChild(el);
    el.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

function scrollThreadToBottom() {
  window.scrollTo({ top: document.body.scrollHeight, behavior: "auto" });
}

// ─── Result card builder ───────────────────────────────────────────────────────
function buildResultCard(ev, { live } = {}) {
  const {
    key_findings = [], content_ideas = [], founder_actions = [],
    ai_actions = [], missing_info = [], questions = [],
    content_plan = [], target_profile = "", pitch_timing = "", product_pitch = "",
    draft, agents_run = [], run_id, outcome = null, founder_note = null,
  } = ev;

  const card = el_("div", "result-card");

  // Header
  const tags = agents_run.map(l => `<span class="tag">${esc(l)}</span>`).join("");
  card.innerHTML = `
    <div class="result-card__header">
      <span class="result-card__title">${IC.layers} ผลวิเคราะห์<span class="result-card__tags">${tags}</span></span>
    </div>`;

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
        const fd = new FormData();
        fd.append("previous_run_id", String(run_id));
        fd.append("answer", answer);
        try {
          const resp = await fetch("/run/continue", { method: "POST", body: fd });
          if (resp.redirected || resp.ok) location.reload();
        } catch (_) {
          sendBtn.disabled = false;
          sendBtn.textContent = "ส่งคำตอบ";
        }
      });

      qb.appendChild(chips);
      qb.appendChild(textarea);
      qb.appendChild(sendBtn);
      sec.appendChild(qb);
    }
    card.appendChild(sec);
  }

  // ── 2. Key findings (condensed -- founder said 3 pages of bullets is too
  // much most of the time, so show the top few and let them expand) ─────────
  if (key_findings.length) {
    const sec = section(IC.chart, "สิ่งที่วิเคราะห์พบ");
    sec.appendChild(condensedList(key_findings, "result-list", 3));
    card.appendChild(sec);
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

    card.appendChild(sec);
  }

  // ── 4. Content ideas ──────────────────────────────────────────────────────
  if (content_ideas.length) {
    const sec = section(IC.bulb, "ไอเดียคอนเทนต์เพิ่มเติม", "result-section--ideas");
    sec.appendChild(condensedList(content_ideas, "ideas-list", 3, true));
    card.appendChild(sec);
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

    if (draft.approval_id) {
      const actions = el_("div", "draft-approval");
      actions.innerHTML = `
        <form method="post" action="/approvals/${draft.approval_id}/approve">
          <button type="submit" class="btn btn--success btn--sm">อนุมัติ — ใช้ตามนี้</button>
        </form>
        <form method="post" action="/approvals/${draft.approval_id}/reject">
          <button type="submit" class="btn btn--danger btn--sm">ไม่ใช้</button>
        </form>`;
      sec.appendChild(actions);
    }

    if (draft.reasoning) {
      const details = document.createElement("details");
      details.className = "reasoning";
      details.style.marginTop = "10px";
      details.innerHTML = `<summary>เหตุผลที่เลือกมุมนี้</summary><p style="font-size:0.84rem;color:var(--muted)">${esc(draft.reasoning)}</p>`;
      sec.appendChild(details);
    }
    card.appendChild(sec);
  }

  // ── 6. Founder actions (AI thinks → คุณ action) ───────────────────────────
  if (founder_actions.length) {
    const sec = section(IC.check, "สิ่งที่คุณต้องทำ", "result-section--actions");
    const list = el_("ul", "task-list");
    founder_actions.forEach((action, i) => {
      list.appendChild(renderActionItem(action, i));
    });
    sec.appendChild(list);
    card.appendChild(sec);
  }

  // ── 7. AI actions ─────────────────────────────────────────────────────────
  if (ai_actions.length) {
    const sec = section(IC.cpu, "AI จะทำต่อเอง");
    sec.appendChild(condensedList(ai_actions, "result-list result-list--ai", 3));
    card.appendChild(sec);
  }

  // ── 8. Missing info ───────────────────────────────────────────────────────
  const realMissing = missing_info.filter(m => !m.includes("AI ไม่พร้อมใช้งาน"));
  if (realMissing.length) {
    const sec = section(IC.alert, "ข้อมูลที่ยังขาด");
    sec.appendChild(condensedList(realMissing, "result-list result-list--warn", 3));
    card.appendChild(sec);
  }

  // ── 9. Feedback (accept/reject → feeds back into future runs) ─────────────
  if (run_id) {
    card.appendChild(buildFeedbackRow(run_id, outcome, founder_note));
  }

  return card;
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
