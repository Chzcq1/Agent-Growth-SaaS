"use strict";

// ─── Virtual Office — Streaming UI ───────────────────────────────────────────
// Intercepts the form submit, sends a POST to /run/stream, and renders each
// SSE event progressively so the founder sees agents thinking in real time.

const AGENT_LABEL_SHORT = {
  lead_hunter: "นักล่าลีด",
  sales_assistant: "ผู้ช่วยขาย",
  demo_agent: "Demo Agent",
  onboarding_agent: "Onboarding",
  customer_success_agent: "Customer Success",
  product_analyst_agent: "นักวิเคราะห์ผลิตภัณฑ์",
};

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("office-form");
  if (!form) return;
  form.addEventListener("submit", handleSubmit);
});

// ─── Form submit handler ──────────────────────────────────────────────────────

async function handleSubmit(e) {
  e.preventDefault();
  const form = e.currentTarget;
  const rawText = form.querySelector("#raw-text-input").value.trim();
  if (!rawText) return;

  setSubmitting(true);
  showStreamPanel();
  clearStreamLog();

  const formData = new FormData();
  formData.append("raw_text", rawText);

  try {
    const response = await fetch("/run/stream", { method: "POST", body: formData });
    if (!response.ok) throw new Error(`Server error ${response.status}`);
    await readSSEStream(response);
  } catch (err) {
    appendErrorBanner(err.message || String(err));
  } finally {
    setSubmitting(false);
  }
}

// ─── SSE stream reader ────────────────────────────────────────────────────────
// EventSource only supports GET; we use fetch + ReadableStream for POST.

async function readSSEStream(response) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE events are separated by double newlines
    const parts = buffer.split("\n\n");
    buffer = parts.pop(); // keep incomplete chunk

    for (const part of parts) {
      const dataLine = part.split("\n").find((l) => l.startsWith("data: "));
      if (!dataLine) continue;
      try {
        const event = JSON.parse(dataLine.slice(6));
        handleEvent(event);
      } catch (_) {
        // ignore malformed JSON
      }
    }
  }
}

// ─── Event handlers ───────────────────────────────────────────────────────────

function handleEvent(event) {
  switch (event.type) {
    case "supervisor_thinking": renderSupervisorThinking(event); break;
    case "planning":            renderPlanning(event); break;
    case "agent_start":         renderAgentStart(event); break;
    case "agent_done":          renderAgentDone(event); break;
    case "qa_start":            renderQAStart(); break;
    case "qa_done":             renderQADone(event); break;
    case "rework_start":        renderReworkStart(event); break;
    case "rework_done":         renderReworkDone(event); break;
    case "final":               renderFinal(event); break;
    case "error":               appendErrorBanner(event.message); break;
    case "stream_end":          onStreamEnd(); break;
  }
}

// ─── Render helpers ───────────────────────────────────────────────────────────

function renderSupervisorThinking({ text }) {
  const el = el_("div", "log-step log-step--supervisor");
  el.innerHTML = `<span class="step-spinner"></span><span class="step-text">${esc(text)}</span>`;
  el.id = "supervisor-step";
  appendLog(el);
}

function renderPlanning({ plan_trace }) {
  // Update supervisor step to "done"
  const sup = document.getElementById("supervisor-step");
  if (sup) {
    sup.classList.add("log-step--done");
    sup.querySelector(".step-spinner")?.remove();
    sup.innerHTML = `<span class="step-check">✓</span><span class="step-text">Supervisor เลือก ${plan_trace.assignments.length} Agent</span>`;
  }

  if (!plan_trace.assignments.length) return;

  const el = el_("div", "log-plan");
  el.innerHTML = `
    <div class="plan-goal">${esc(plan_trace.goal)}</div>
    <div class="plan-agents">${plan_trace.assignments.map(a =>
      `<span class="plan-agent">${a.emoji} ${esc(a.label)}</span>`
    ).join("")}</div>`;
  appendLog(el);
}

function renderAgentStart({ agent, label, emoji }) {
  const el = el_("div", "agent-card agent-card--working");
  el.id = `agent-${agent}`;
  el.innerHTML = `
    <div class="agent-card__header">
      <span class="agent-emoji">${emoji}</span>
      <strong class="agent-name">${esc(label)}</strong>
      <span class="agent-status">
        <span class="step-spinner step-spinner--sm"></span>
        <span class="status-text">กำลังวิเคราะห์...</span>
      </span>
    </div>
    <div class="agent-card__body"></div>`;
  appendLog(el);
}

function renderAgentDone({ agent, label, emoji, thinking, findings, question, observations, draft_message }) {
  let card = document.getElementById(`agent-${agent}`);
  if (!card) {
    card = el_("div", "agent-card");
    card.id = `agent-${agent}`;
    appendLog(card);
  }
  card.classList.remove("agent-card--working");
  card.classList.add("agent-card--done");

  let bodyHtml = "";

  if (thinking) {
    bodyHtml += `<div class="agent-thinking">💭 ${esc(thinking)}</div>`;
  }

  if (findings?.length) {
    bodyHtml += `<ul class="agent-findings">${findings.map(f => `<li>${esc(f)}</li>`).join("")}</ul>`;
  } else {
    bodyHtml += `<p class="muted-text" style="margin:6px 0 0">ไม่พบประเด็นที่เกี่ยวข้องโดยตรง</p>`;
  }

  if (draft_message) {
    bodyHtml += `<div class="agent-draft"><span class="draft-label">✏️ ร่างข้อความ</span><p>${esc(draft_message)}</p></div>`;
  }

  if (observations?.length) {
    bodyHtml += `<div class="agent-obs"><span class="obs-label">💡 ไอเดียระหว่างทาง</span><ul>${observations.map(o => `<li>${esc(o)}</li>`).join("")}</ul></div>`;
  }

  if (question) {
    bodyHtml += `
      <div class="agent-question" id="q-${agent}">
        <span class="q-label">❓ ต้องถามคุณก่อน</span>
        <p>${esc(question)}</p>
      </div>`;
  }

  card.innerHTML = `
    <div class="agent-card__header">
      <span class="agent-emoji">${emoji}</span>
      <strong class="agent-name">${esc(label)}</strong>
      <span class="agent-status agent-status--done">
        <span class="step-check">✓</span>
        <span class="status-text">เสร็จแล้ว</span>
      </span>
    </div>
    <div class="agent-card__body">${bodyHtml}</div>`;
}

function renderQAStart() {
  const el = el_("div", "log-step log-step--qa");
  el.id = "qa-step";
  el.innerHTML = `<span class="step-spinner"></span><span class="step-text">🔎 Supervisor กำลังตรวจงาน QA...</span>`;
  appendLog(el);
}

function renderQADone({ note, sufficient, rework }) {
  const el = document.getElementById("qa-step");
  if (!el) return;
  el.classList.add("log-step--done");
  const icon = sufficient ? "✅" : "🔁";
  const msg = sufficient
    ? "QA ผ่าน — ครอบคลุมแล้วในรอบแรก"
    : `QA พบช่องว่าง — ให้ทำเพิ่ม ${rework?.length || 0} Agent`;
  el.innerHTML = `<span class="step-check">✓</span><span class="step-text">${icon} ${msg}${note ? ` (${esc(note)})` : ""}</span>`;
}

function renderReworkStart({ agent, label, emoji, feedback }) {
  let card = document.getElementById(`agent-${agent}`);
  if (card) {
    card.classList.remove("agent-card--done");
    card.classList.add("agent-card--working", "agent-card--rework");
    const header = card.querySelector(".agent-card__header");
    if (header) {
      header.querySelector(".agent-status").innerHTML =
        `<span class="step-spinner step-spinner--sm"></span><span class="status-text">ทำรอบ 2 อยู่...</span>`;
    }
    const body = card.querySelector(".agent-card__body");
    if (body) body.innerHTML += `<div class="rework-note">📝 ${esc(feedback)}</div>`;
  }
}

function renderReworkDone({ agent, label, emoji, findings }) {
  const card = document.getElementById(`agent-${agent}`);
  if (!card) return;
  card.classList.remove("agent-card--working");
  card.classList.add("agent-card--done");
  const header = card.querySelector(".agent-card__header");
  if (header) {
    header.querySelector(".agent-status").innerHTML =
      `<span class="step-check">✓</span><span class="status-text">รอบ 2 เสร็จแล้ว</span>`;
  }
  const body = card.querySelector(".agent-card__body");
  if (body && findings?.length) {
    const ul = document.createElement("ul");
    ul.className = "agent-findings agent-findings--rework";
    ul.innerHTML = findings.map(f => `<li>${esc(f)}</li>`).join("");
    body.appendChild(ul);
  }
}

function renderFinal(event) {
  const {
    key_findings = [], founder_actions = [], ai_actions = [],
    missing_info = [], questions = [], team_notes = [],
    draft, agents_run = [], run_id
  } = event;

  const el = el_("div", "final-card");

  // Questions (answer box)
  let questionsHtml = "";
  if (questions.length) {
    const qItems = questions.map(q =>
      `<li><strong>${esc(q.label)}</strong> — ${esc(q.question)}</li>`
    ).join("");
    questionsHtml = `
      <div class="final-section final-section--attention">
        <div class="section-label">💬 ทีม AI อยากถามคุณ</div>
        <ul class="result-list">${qItems}</ul>
        ${run_id ? `
        <form method="post" action="/run/continue" class="stacked-form" style="margin-top:12px">
          <input type="hidden" name="previous_run_id" value="${run_id}" />
          <textarea name="answer" rows="3" placeholder="ตอบคำถามด้านบน แล้วทีมจะทำงานต่อทันที..." required></textarea>
          <button type="submit" class="btn btn--primary">ส่งคำตอบ ให้ทีมทำงานต่อ</button>
        </form>` : ""}
      </div>`;
  }

  // Team notes
  let notesHtml = "";
  if (team_notes.length) {
    notesHtml = `
      <div class="final-section">
        <div class="section-label">💡 ข้อสังเกตจากทีม AI</div>
        <ul class="result-list">${team_notes.map(n => `<li><strong>${esc(n.label)}</strong>: ${esc(n.note)}</li>`).join("")}</ul>
      </div>`;
  }

  // Key findings
  const findingsHtml = key_findings.length
    ? `<ul class="result-list">${key_findings.map(f => `<li>${esc(f)}</li>`).join("")}</ul>`
    : `<p class="muted-text">ไม่พบประเด็นที่ชัดเจนจากข้อมูลนี้</p>`;

  // Action plan
  const founderHtml = founder_actions.length
    ? `<ul class="result-list">${founder_actions.map(a => `<li>${esc(a)}</li>`).join("")}</ul>`
    : `<span class="muted-text">ไม่มี</span>`;
  const aiHtml = ai_actions.length
    ? `<ul class="result-list">${ai_actions.map(a => `<li>${esc(a)}</li>`).join("")}</ul>`
    : `<span class="muted-text">ไม่มี</span>`;

  // Missing info
  const missingHtml = missing_info.length
    ? `<ul class="result-list result-list--warn">${missing_info.map(m => `<li>${esc(m)}</li>`).join("")}</ul>`
    : "";

  // Draft message (Sales Assistant)
  let draftHtml = "";
  if (draft) {
    draftHtml = `
      <div class="final-section">
        <div class="section-label">✏️ ข้อความร่างจาก Sales Assistant (รอตรวจก่อนส่ง)</div>
        <div class="draft-box">${esc(draft.message)}</div>
        ${draft.reasoning ? `<details class="reasoning"><summary>เหตุผลที่เลือกมุมนี้</summary><p>${esc(draft.reasoning)}</p></details>` : ""}
        ${draft.approval_id ? `
        <div class="approval-card__actions" style="margin-top:10px">
          <form method="post" action="/approvals/${draft.approval_id}/approve">
            <button type="submit" class="btn btn--success">อนุมัติ</button>
          </form>
          <form method="post" action="/approvals/${draft.approval_id}/reject">
            <button type="submit" class="btn btn--danger">ไม่ใช้</button>
          </form>
        </div>
        <div class="approval-card__actions approval-card__actions--secondary" style="margin-top:8px">
          <form method="post" action="/approvals/${draft.approval_id}/edit">
            <input type="text" name="edited_message" value="${esc(draft.message)}" required />
            <button type="submit" class="btn btn--primary btn--small">แก้แล้วใช้</button>
          </form>
        </div>` : ""}
      </div>`;
  }

  const tagHtml = agents_run.map(l => `<span class="tag">${esc(l)}</span>`).join("");

  el.innerHTML = `
    <div class="final-card__header">
      <span class="final-card__title">📋 ผลสรุป Virtual Office ${tagHtml}</span>
    </div>
    ${questionsHtml}
    ${notesHtml}
    <div class="final-section">
      <div class="section-label">สิ่งที่พบ (Key Findings)</div>
      ${findingsHtml}
    </div>
    <div class="final-section">
      <div class="section-label">แผนงาน (Action Plan)</div>
      <div class="action-grid">
        <div class="action-col action-col--founder"><div class="action-col__label">👤 Founder ต้องทำเอง</div>${founderHtml}</div>
        <div class="action-col action-col--ai"><div class="action-col__label">🤖 AI จะทำต่อเอง</div>${aiHtml}</div>
      </div>
    </div>
    ${missingHtml ? `<div class="final-section"><div class="section-label">ข้อมูลที่ยังขาด</div>${missingHtml}</div>` : ""}
    ${draftHtml}`;

  appendLog(el);

  // Hide the old static result — this streaming one replaces it
  const staticResult = document.getElementById("static-result");
  if (staticResult) staticResult.hidden = true;
}

function onStreamEnd() {
  setSubmitting(false);
}

// ─── Utilities ─────────────────────────────────────────────────────────────

function showStreamPanel() {
  const panel = document.getElementById("stream-panel");
  if (panel) panel.hidden = false;
  // Hide static result during streaming
  const staticResult = document.getElementById("static-result");
  if (staticResult) staticResult.hidden = true;
}

function clearStreamLog() {
  const log = document.getElementById("stream-log");
  if (log) log.innerHTML = "";
}

function appendLog(el) {
  const log = document.getElementById("stream-log");
  if (log) {
    log.appendChild(el);
    el.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

function appendErrorBanner(msg) {
  const el = el_("div", "error-banner");
  el.innerHTML = `⚠️ ข้อผิดพลาด: ${esc(msg)}`;
  appendLog(el);
}

function setSubmitting(submitting) {
  const btn = document.getElementById("submit-btn");
  if (!btn) return;
  btn.disabled = submitting;
  btn.querySelector(".btn-text").hidden = submitting;
  btn.querySelector(".btn-spinner").hidden = !submitting;
}

function el_(tag, className) {
  const e = document.createElement(tag);
  e.className = className;
  return e;
}

function esc(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
