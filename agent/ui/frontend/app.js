// Barebones client for the user-testing page: pick a task, chat as the customer, end the session.
const $ = (id) => document.getElementById(id);
let session = null;

async function api(path, body) {
  const res = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json();
}

function bubble(role, text) {
  const wrap = document.createElement("div");
  wrap.className = `d-flex mb-2 ${role === "customer" ? "justify-content-end" : ""}`;
  const div = document.createElement("div");
  div.className = `msg rounded px-3 py-2 ${role === "customer" ? "bg-primary text-white" : "bg-white border"}`;
  div.textContent = text;
  wrap.appendChild(div);
  $("chat").appendChild(wrap);
  $("chat").scrollTop = $("chat").scrollHeight;
}

function toolLine(call) {
  const div = document.createElement("div");
  div.className = `tool text-muted font-monospace mb-1 ${$("showTools").checked ? "" : "d-none"}`;
  div.dataset.tool = "1";
  const status = call.error ? "REFUSED" : call.write ? "WRITE" : "read";
  div.textContent = `[${status}] ${call.name}(${JSON.stringify(call.arguments)}) → ${call.result.slice(0, 160)}`;
  $("chat").appendChild(div);
}

function setOpen(open) {
  $("input").disabled = !open;
  $("send").disabled = !open;
  $("end").disabled = !open;
  $("start").disabled = open;
  $("task").disabled = open;
}

$("showTools").addEventListener("change", () => {
  document.querySelectorAll("[data-tool]").forEach((el) => el.classList.toggle("d-none", !$("showTools").checked));
});

$("start").addEventListener("click", async () => {
  $("chat").innerHTML = "";
  $("result").className = "alert d-none";
  const s = await api("/api/sessions", { task_id: $("task").value });
  session = s.session_id;
  const sc = s.scenario;
  $("known").textContent = sc.known_info || "—";
  $("reason").textContent = sc.reason_for_call || "—";
  $("unknown").textContent = sc.unknown_info || "—";
  $("persona").textContent = sc.task_instructions || "—";
  $("scenario").classList.remove("d-none");
  bubble("agent", s.greeting);
  setOpen(true);
  $("input").focus();
});

$("form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = $("input").value.trim();
  if (!text || !session) return;
  $("input").value = "";
  bubble("customer", text);
  setOpen(false);
  $("end").disabled = true;
  $("send").textContent = "…";
  try {
    const r = await api(`/api/sessions/${session}/messages`, { text });
    r.tools.forEach(toolLine);
    if (r.error) bubble("agent", `⚠️ ${r.error}`);
    else bubble("agent", r.reply);
  } catch (err) {
    bubble("agent", `⚠️ ${err.message}`);
  }
  $("send").textContent = "Send";
  setOpen(true);
  $("input").focus();
});

$("end").addEventListener("click", async () => {
  const r = await api(`/api/sessions/${session}/end`, {});
  setOpen(false);
  session = null;
  $("result").className = `alert ${r.verdict === "correct" ? "alert-success" : "alert-warning"}`;
  $("result").innerHTML = "";
  [
    `Verdict: ${r.verdict}`,
    `End state matches τ²-bench: ${r.end_state_match}`,
    r.notes ? `Notes: ${r.notes}` : "",
    `Log: ${r.log}`,
  ].filter(Boolean).forEach((line) => {
    const p = document.createElement("div");
    p.className = "small";
    p.textContent = line;
    $("result").appendChild(p);
  });
});

(async () => {
  const tasks = await api("/api/tasks");
  for (const t of tasks) {
    const o = document.createElement("option");
    o.value = t.id;
    o.textContent = `${t.id}: ${t.reason}`;
    $("task").appendChild(o);
  }
  $("task").value = "99";
})();
