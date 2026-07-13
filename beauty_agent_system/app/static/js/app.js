"use strict";

// ─── Virtual Office — Streaming UI ───────────────────────────────────────────
const LS_KEY = "vo_last_result";

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

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("office-form");
  if (!form) return;

  const staticEl = document.getElementById("static-result");
  if (staticEl) staticEl.classList.add("hidden");

  const saved = localStorage.getItem(LS_KEY);
  if (saved) {
    try { renderFinal(JSON.parse(saved)); } catch (_) { localStorage.removeItem(LS_KEY); }
  }

  form.addEventListener("submit", handleSubmit);
});

// ─── Form submit ──────────────────────────────────────────────────────────────
async function handleSubmit(e) {
  e.preventDefault();
  const form = e.currentTarget;
  const rawText = form.querySelector("#raw-text-input").value.trim();
  if (!rawText) return;

  setSubmitting(true);
  clearResult();
  showProgress();
  document.getElementById("static-result")?.classList.add("hidden");

  const fd = new FormData();
  fd.append("raw_text", rawText);

  try {
    const resp = await fetch("/run/stream", { method: "POST", body: fd });
    if (!resp.ok) throw new Error(`Server error ${resp.status}`);
    await readSSE(resp);
  } catch (err) {
    appendToResult(errorBanner(err.message || String(err)));
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
    case "planning":   updateProgressAgents(ev.plan_trace?.assignments || []); break;
    case "agent_done": markAgentDone(ev.agent); break;
    case "final":      onFinal(ev); break;
    case "error":      appendToResult(errorBanner(ev.message)); break;
  }
}

// ─── Progress area ────────────────────────────────────────────────────────────
function showProgress() { document.getElementById("progress-area").hidden = false; }
function hideProgress() { document.getElementById("progress-area").hidden = true; }

function updateProgressAgents(assignments) {
  const container = document.getElementById("progress-agents");
  container.innerHTML = "";
  for (const a of assignments) {
    const el = document.createElement("span");
    el.className = "progress-agent progress-agent--working";
    el.id = `pa-${a.agent}`;
    const icon = AGENT_ICONS[a.agent] || IC.cpu;
    el.innerHTML = `<span class="agent-dot"></span><span class="agent-icon">${icon}</span>${esc(a.label)}`;
    container.appendChild(el);
  }
}

function markAgentDone(agent) {
  const el = document.getElementById(`pa-${agent}`);
  if (!el) return;
  el.classList.remove("progress-agent--working");
  el.classList.add("progress-agent--done");
  el.querySelector(".agent-dot").innerHTML = IC.done;
  el.querySelector(".agent-dot").classList.add("agent-dot--done");
}

// ─── Result rendering ─────────────────────────────────────────────────────────
function onFinal(ev) {
  localStorage.setItem(LS_KEY, JSON.stringify(ev));
  renderFinal(ev);
}

function renderFinal(ev) {
  const {
    key_findings = [], content_ideas = [], founder_actions = [],
    ai_actions = [], missing_info = [], questions = [],
    content_plan = [], target_profile = "", pitch_timing = "", product_pitch = "",
    draft, agents_run = [], run_id,
  } = ev;

  const card = el_("div", "result-card");

  // Header
  const tags = agents_run.map(l => `<span class="tag">${esc(l)}</span>`).join("");
  card.innerHTML = `
    <div class="result-card__header">
      <span class="result-card__title">${IC.layers} ผลวิเคราะห์ ${tags}</span>
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

  // ── 2. Key findings ───────────────────────────────────────────────────────
  if (key_findings.length) {
    const sec = section(IC.chart, "สิ่งที่วิเคราะห์พบ");
    sec.appendChild(ul_(key_findings, "result-list"));
    card.appendChild(sec);
  }

  // ── 3. Content plan (step-by-step, Notion-style) ──────────────────────────
  if (content_plan.length || target_profile || pitch_timing || product_pitch) {
    const sec = section(IC.layers, "แผนโพสต์ Facebook — ขั้นตอน", "result-section--plan");

    // Target profile chip
    if (target_profile) {
      const chip = el_("div", "profile-chip");
      chip.innerHTML = `<span class="chip-icon">${IC.target}</span><strong>กลุ่มเป้าหมาย:</strong> ${esc(target_profile)}`;
      sec.appendChild(chip);
    }

    // Steps
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

      if (step.goal) {
        const row = el_("div", "plan-row");
        row.innerHTML = `<span class="plan-row__label">${IC.arrow} เป้า</span><span class="plan-row__val">${esc(step.goal)}</span>`;
        stepEl.appendChild(row);
      }

      if (step.cta) {
        const ctaEl = el_("div", "plan-cta");
        ctaEl.innerHTML = `<span class="plan-cta__label">หลังโพสต์:</span> ${esc(step.cta)}`;
        stepEl.appendChild(ctaEl);
      }

      sec.appendChild(stepEl);
    }

    // Pitch timing & product pitch
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
    const list = el_("ul", "ideas-list");
    for (const idea of content_ideas) {
      const li = document.createElement("li");
      li.innerHTML = `<span class="idea-dot"></span><span>${esc(idea)}</span>`;
      list.appendChild(li);
    }
    sec.appendChild(list);
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
      const li = document.createElement("li");
      li.className = "task-item";
      li.innerHTML = `
        <span class="task-num">${i + 1}</span>
        <span class="task-body">${esc(action)}</span>`;
      list.appendChild(li);
    });
    sec.appendChild(list);
    card.appendChild(sec);
  }

  // ── 7. AI actions ─────────────────────────────────────────────────────────
  if (ai_actions.length) {
    const sec = section(IC.cpu, "AI จะทำต่อเอง");
    sec.appendChild(ul_(ai_actions, "result-list result-list--ai"));
    card.appendChild(sec);
  }

  // ── 8. Missing info ───────────────────────────────────────────────────────
  const realMissing = missing_info.filter(m => !m.includes("AI ไม่พร้อมใช้งาน"));
  if (realMissing.length) {
    const sec = section(IC.alert, "ข้อมูลที่ยังขาด");
    sec.appendChild(ul_(realMissing, "result-list result-list--warn"));
    card.appendChild(sec);
  }

  clearResult();
  appendToResult(card);
}

// ─── Utilities ────────────────────────────────────────────────────────────────
function section(iconHtml, label, extraClass = "") {
  const sec = el_("div", `result-section ${extraClass}`.trim());
  const lbl = el_("div", "section-label");
  lbl.innerHTML = `<span class="section-icon">${iconHtml}</span>${label}`;
  sec.appendChild(lbl);
  return sec;
}

function ul_(items, className) {
  const list = el_("ul", className);
  for (const item of items) {
    const li = document.createElement("li");
    li.textContent = item;
    list.appendChild(li);
  }
  return list;
}

function clearResult() {
  const area = document.getElementById("result-area");
  if (area) area.innerHTML = "";
}

function appendToResult(el) {
  const area = document.getElementById("result-area");
  if (area) {
    area.appendChild(el);
    el.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
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
