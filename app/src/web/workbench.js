async function api(path, init) {
  const res = await fetch(path, init);
  const text = await res.text();
  let json;
  try { json = JSON.parse(text); } catch { json = { raw: text }; }
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return json;
}

let currentTaskId = null;

async function refresh() {
  if (!currentTaskId) return;
  const detail = await api(`/api/video-tasks/${currentTaskId}`);
  const arts = await api(`/api/video-tasks/${currentTaskId}/artifacts`);
  document.getElementById("detailOut").textContent = JSON.stringify(detail, null, 2);
  document.getElementById("artOut").textContent = JSON.stringify(arts, null, 2);
}

document.getElementById("createBtn").addEventListener("click", async () => {
  const input_kind = document.getElementById("inputKind").value;
  const input_text = document.getElementById("inputText").value || "";
  const source_links = (document.getElementById("sourceLinks").value || "")
    .split("\n").map(s => s.trim()).filter(Boolean);

  const created = await api("/api/video-tasks", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ input_kind, input_text, source_links }),
  });
  currentTaskId = created.task_id;
  document.getElementById("taskId").textContent = `task_id=${currentTaskId}`;
  await refresh();
});

document.getElementById("refreshBtn").addEventListener("click", refresh);

document.getElementById("retryBtn").addEventListener("click", async () => {
  if (!currentTaskId) return;
  const resp = await api(`/api/video-tasks/${currentTaskId}/retry`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ step_key: "script_generation" }),
  });
  console.log(resp);
  await refresh();
});

