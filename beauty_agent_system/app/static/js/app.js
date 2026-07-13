"use strict";

// ─── Virtual Office — Streaming UI ───────────────────────────────────────────
const LS_KEY = "vo_last_result";

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("office-form");
  if (!form) return;

  // Hide server-rendered static result — JS will manage state
  const staticEl = document.getElementById("static-result");
  if (staticEl) staticEl.classList.add("hidden");

  // Restore last result from localStorage if no server result visible
  const saved = localStorage.getItem(LS_KEY);
  if (saved) {
    try { renderFinal(JSON.parse(saved)); } catch (_) { localStorage.removeItem(LS_KEY); }
  } else if (staticEl && !staticEl.classList.contains("hidden")) {
    // keep server result shown
    staticEl.classList.remove("hidden");
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
    case "planning":    updateProgressAgents(ev.plan_trace?.assignments || []); break;
    case "agent_done":  markAgentDone(ev.agent); break;
    case "final":       onFinal(ev); break;
    case "error":       appendToResult(errorBanner(ev.message)); break;
    case "stream_end":  /* handled in handleSubmit finally */ break;
  }
}

// ─── Progress area ────────────────────────────────────────────────────────────
function showProgress() {
  document.getElementById("progress-area").hidden = false;
}
function hideProgress() {
  document.getElementById("progress-area").hidden = true;
}

function updateProgressAgents(assignments) {
  const container = document.getElementById("progress-agents");
  container.innerHTML = "";
  for (const a of assignments) {
    const el = document.createElement("span");
    el.className = "progress-agent progress-agent--working";
    el.id = `pa-${a.agent}`;
    el.innerHTML = `<span class="agent-dot"></span>${esc(a.emoji || "")} ${esc(a.label)}`;
    container.appendChild(el);
  }
}

function markAgentDone(agent) {
  const el = document.getElementById(`pa-${agent}`);
  if (el) {
    el.classList.remove("progress-agent--working");
    el.classList.add("progress-agent--done");
    el.querySelector(".agent-dot").textContent = "";
    el.innerHTML = `<span class="agent-dot"></span>✓ ${el.textContent.trim()}`;
  }
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
    draft, agents_run = [], run_id,
  } = ev;

  const card = el_("div", "result-card");

  // Header
  const tags = agents_run.map(l => `<span class="tag">${esc(l)}</span>`).join("");
  card.innerHTML = `
    <div class="result-card__header">
      <span class="result-card__title">📋 ผลวิเคราะห์ ${tags}</span>
    </div>`;

  // 1. Questions (if any) — with quick-answer chips
  if (questions.length) {
    const sec = section("💬 ทีม AI มีคำถาม", "result-section--attention");
    for (const q of questions) {
      const qb = el_("div", "question-block");
      qb.innerHTML = `<p><strong>${esc(q.label)}</strong>: ${esc(q.question)}</p>`;

      // Quick-answer chips
      const chips = el_("div", "question-chips");
      const QUICK = [
        "✅ ข้อมูลที่มีอยู่ก็พอแล้ว ทำต่อได้เลย",
        "❓ ยังไม่รู้เหมือนกัน",
        "⏭️ ข้ามคำถามนี้ไปก่อน",
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

  // 2. Key findings
  if (key_findings.length) {
    const sec = section("📊 สิ่งที่วิเคราะห์พบ");
    sec.appendChild(ul_(key_findings, "result-list"));
    card.appendChild(sec);
  }

  // 3. Content ideas
  if (content_ideas.length) {
    const sec = section("📝 ไอเดียโพสต์ / คอนเทนต์", "result-section--ideas");
    const list = el_("ul", "ideas-list");
    for (const idea of content_ideas) {
      const li = document.createElement("li");
      li.appendChild(document.createTextNode(idea));
      list.appendChild(li);
    }
    sec.appendChild(list);
    card.appendChild(sec);
  }

  // 4. Draft message (Sales Assistant)
  if (draft?.message) {
    const sec = section("💬 ข้อความทักลูกค้า (ร่างจาก Sales Assistant)", "result-section--draft");

    const box = el_("div", "draft-box");
    box.textContent = draft.message;
    sec.appendChild(box);

    // Copy button
    const copyBtn = el_("button", "copy-btn");
    copyBtn.type = "button";
    copyBtn.innerHTML = `📋 คัดลอกข้อความ`;
    copyBtn.addEventListener("click", () => {
      navigator.clipboard.writeText(draft.message).then(() => {
        copyBtn.textContent = "✓ คัดลอกแล้ว";
        copyBtn.classList.add("copy-btn--copied");
        setTimeout(() => {
          copyBtn.textContent = "📋 คัดลอกข้อความ";
          copyBtn.classList.remove("copy-btn--copied");
        }, 2000);
      });
    });
    sec.appendChild(copyBtn);

    // Approve / reject buttons
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

  // 5. Founder actions
  if (founder_actions.length) {
    const sec = section("✅ ต้องทำตอนนี้", "result-section--actions");
    const list = el_("ul", "result-list result-list--actions");
    for (const action of founder_actions) {
      const li = document.createElement("li");
      li.textContent = action;
      list.appendChild(li);
    }
    sec.appendChild(list);
    card.appendChild(sec);
  }

  // 6. AI actions (compact, secondary)
  if (ai_actions.length) {
    const sec = section("🤖 AI จะทำต่อเอง");
    sec.appendChild(ul_(ai_actions, "result-list"));
    card.appendChild(sec);
  }

  // 7. Missing info (only if there's real missing data, not just LLM unavailable)
  const realMissing = missing_info.filter(m => !m.includes("AI ไม่พร้อมใช้งาน"));
  if (realMissing.length) {
    const sec = section("⚠️ ข้อมูลที่ยังขาด");
    sec.appendChild(ul_(realMissing, "result-list result-list--warn"));
    card.appendChild(sec);
  }

  clearResult();
  appendToResult(card);
}

// ─── Utilities ────────────────────────────────────────────────────────────────
function section(label, extraClass = "") {
  const sec = el_("div", `result-section ${extraClass}`.trim());
  const lbl = el_("div", "section-label");
  lbl.textContent = label;
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
  el.textContent = `⚠️ ${msg}`;
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
