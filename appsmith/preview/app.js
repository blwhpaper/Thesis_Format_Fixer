const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const TERMINAL_STATUSES = new Set(["completed", "failed"]);

const state = {
  selectedFile: null,
  selectedMode: "check",
  currentJobId: null,
  currentJobStatus: "idle",
  latestResultPayload: null,
  latestArtifacts: {},
  latestError: null,
  apiBaseUrl: DEFAULT_API_BASE_URL,
  lastSubmittedMode: null,
};

function $(id) {
  return document.getElementById(id);
}

function pageIsSingleFile() {
  return document.body && document.body.dataset.page === "single-file";
}

function normalizeApiUrl(path) {
  const base = state.apiBaseUrl.replace(/\/$/, "");
  return `${base}${path}`;
}

function setMode(mode) {
  state.selectedMode = mode === "fix" ? "fix" : "check";
  document.querySelectorAll(".mode-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === state.selectedMode);
  });
  const description = $("modeDescription");
  if (description) {
    description.textContent =
      state.selectedMode === "fix"
        ? "修复模式会在完成后提供修订稿下载。"
        : "检查模式会生成结果摘要和报告。";
  }
}

function updateSelectedFileInfo() {
  const box = $("selectedFileInfo");
  if (!box) return;
  if (!state.selectedFile) {
    box.textContent = "当前未选择文件。";
    return;
  }
  box.textContent = `已选择：${state.selectedFile.name} (${Math.max(1, Math.round(state.selectedFile.size / 1024))} KB)`;
}

function setError(message, tone = "error") {
  state.latestError = message || null;
  const statusCopy = $("jobStatusCopy");
  if (!statusCopy || !message) return;
  statusCopy.textContent = message;
  statusCopy.className = `summary-copy ${tone === "error" ? "text-danger" : ""}`;
}

function setJobStatus(status, headline, copy) {
  state.currentJobStatus = status;
  const statusHeadline = $("jobStatusHeadline");
  const statusCopy = $("jobStatusCopy");
  if (statusHeadline) statusHeadline.textContent = headline;
  if (statusCopy) {
    statusCopy.textContent = copy;
    statusCopy.className = "summary-copy";
  }
}

function resetResultState() {
  state.currentJobId = null;
  state.currentJobStatus = "idle";
  state.latestResultPayload = null;
  state.latestArtifacts = {};
  state.latestError = null;
  setJobStatus("idle", "未开始", "请选择文件并提交。");
  renderPayload(null);
}

function renderList(targetId, items, fallback) {
  const target = $(targetId);
  if (!target) return;
  target.innerHTML = "";
  const values = Array.isArray(items) ? items : [];
  if (!values.length) {
    const li = document.createElement("li");
    li.textContent = fallback;
    target.appendChild(li);
    return;
  }
  values.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = typeof item === "string" ? item : JSON.stringify(item, null, 2);
    target.appendChild(li);
  });
}

function renderCounts(userSummary) {
  const counts = userSummary && userSummary.counts ? userSummary.counts : {};
  $("autoProcessedCount").textContent = counts.auto_processed ?? 0;
  $("detectedCount").textContent = counts.detected_not_auto_fixed ?? 0;
  $("manualReviewCount").textContent = counts.manual_review_required ?? 0;
}

function flattenCategorizedRows(userSummary) {
  const categorized = userSummary && userSummary.categorized ? userSummary.categorized : {};
  const buckets = [
    ["auto_processed", "已自动处理"],
    ["detected_not_auto_fixed", "发现但未自动修改"],
    ["manual_review_required", "需要人工复核"],
  ];
  const rows = [];
  buckets.forEach(([key, label]) => {
    const items = Array.isArray(categorized[key]) ? categorized[key] : [];
    items.forEach((item) => {
      rows.push({
        category: label,
        title: item.issue_title || item.rule_name || "(未命名问题)",
        handlingStatus: item.handling_status || "-",
        nextStep: item.next_step || item.issue_description || "-",
      });
    });
  });
  return rows;
}

function renderDetailTable(payload) {
  const body = $("detailTableBody");
  const empty = $("tableEmptyState");
  const wrap = $("tableWrap");
  if (!body || !empty || !wrap) return;

  body.innerHTML = "";
  if (!payload) {
    wrap.hidden = true;
    empty.hidden = false;
    empty.textContent = "结果返回后，这里会显示需要你关注的问题。";
    return;
  }

  const rows = flattenCategorizedRows(payload.user_summary || {});
  if (!rows.length) {
    wrap.hidden = true;
    empty.hidden = false;
    empty.textContent = "这次没有需要单独展开的问题。";
  } else {
    wrap.hidden = false;
    empty.hidden = true;
    rows.forEach((row) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${row.category}</td>
        <td>${row.title}</td>
        <td>${row.handlingStatus}</td>
        <td>${row.nextStep}</td>
      `;
      body.appendChild(tr);
    });
  }
}

function renderDownloads(artifacts, mode) {
  const list = $("downloadList");
  const hint = $("downloadHint");
  if (!list || !hint) return;
  list.innerHTML = "";

  const downloadItems = [];
  if (artifacts && artifacts.download_report_md_url) {
    downloadItems.push({
      label: "下载处理报告",
      url: normalizeApiUrl(artifacts.download_report_md_url),
      description: "查看本次处理结果",
    });
  }
  if (artifacts && artifacts.download_fixed_docx_url) {
    downloadItems.push({
      label: "下载修订稿",
      url: normalizeApiUrl(artifacts.download_fixed_docx_url),
      description: "查看处理后的文档",
    });
  }

  downloadItems.forEach((item) => {
    const row = document.createElement("div");
    row.className = "download-item";
    row.innerHTML = `
      <div>
        <strong>${item.label}</strong>
        <p>${item.description}</p>
      </div>
      <a class="secondary-button as-link compact-link" href="${item.url}" target="_blank" rel="noreferrer">打开</a>
    `;
    list.appendChild(row);
  });

  if (!artifacts || !artifacts.download_report_md_url) {
    const row = document.createElement("div");
    row.className = "download-item muted-download";
    row.innerHTML = "<div><strong>处理报告</strong><p>当前还没有可下载的报告。</p></div>";
    list.appendChild(row);
  }

  if (mode === "fix" && (!artifacts || !artifacts.download_fixed_docx_url)) {
    const row = document.createElement("div");
    row.className = "download-item muted-download";
    row.innerHTML = "<div><strong>修订稿</strong><p>当前无可下载修订稿。</p></div>";
    list.appendChild(row);
  }

  if (mode === "check") {
    hint.textContent = "检查完成后，可在这里查看报告。";
  } else {
    hint.textContent = "修复完成后，如有修订稿，会在这里显示下载入口。";
  }
}

function renderPayload(payload) {
  const overallStatusBox = $("overallStatusBox");
  if (overallStatusBox) {
    overallStatusBox.textContent = payload?.user_summary?.overall_status || "暂无结果。";
  }
  renderCounts(payload?.user_summary || {});
  renderList("keyIssues", payload?.user_summary?.key_issues || [], "当前没有重点问题。");
  renderList("nextSteps", payload?.user_summary?.next_steps || [], "处理完成后，这里会显示下一步建议。");
  renderDetailTable(payload);
  renderDownloads(payload?.artifacts || {}, payload?.mode || state.selectedMode);
}

function applyJobPayload(payload) {
  state.latestResultPayload = payload;
  state.latestArtifacts = payload && payload.artifacts ? payload.artifacts : {};
  state.currentJobId = payload?.job_id || null;
  setMode(payload?.mode || state.selectedMode);
  renderPayload(payload);

  if (payload?.status === "failed") {
    setJobStatus("failed", "失败", payload.error || "请检查文件后重试。");
    setError(payload.error || "任务失败。");
    return;
  }

  if (payload?.status === "completed") {
    setJobStatus("completed", "已完成", payload.user_summary?.overall_status || "结果已返回。");
    return;
  }

  setJobStatus(payload?.status || "unknown", "处理中", "正在获取结果，请稍候。");
}

async function pollJob(jobId, attempt = 0) {
  const response = await fetch(normalizeApiUrl(`/api/jobs/${jobId}`));
  const payload = await response.json();
  applyJobPayload(payload);
  if (!TERMINAL_STATUSES.has(payload.status) && attempt < 4) {
    window.setTimeout(() => {
      pollJob(jobId, attempt + 1).catch((error) => {
        setError(`轮询失败：${error.message || error}`);
      });
    }, 600);
  }
}

async function submitJob() {
  if (!state.selectedFile) {
    setError("请先选择一个 .docx 文件。");
    return;
  }

  const formData = new FormData();
  formData.append("file", state.selectedFile);
  state.lastSubmittedMode = state.selectedMode;
  setJobStatus("submitting", "处理中", "正在提交，请稍候。");

  try {
    const response = await fetch(normalizeApiUrl(`/api/jobs/${state.selectedMode}`), {
      method: "POST",
      body: formData,
    });
    const payload = await response.json();
    applyJobPayload(payload);
    if (!response.ok || !payload.job_id) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    setJobStatus("submitted", "处理中", "正在获取结果，请稍候。");
    await pollJob(payload.job_id);
  } catch (error) {
    setJobStatus("failed", "失败", "请检查文件内容后重试。");
    setError(`提交失败：${error.message || error}`);
  }
}

function retryLastRequest() {
  if (!state.selectedFile) {
    setError("没有可重试的文件，请重新选择文件后再试。");
    return;
  }
  if (state.lastSubmittedMode) {
    setMode(state.lastSubmittedMode);
  }
  submitJob().catch((error) => {
    setError(`重试失败：${error.message || error}`);
  });
}

function bindSingleFilePage() {
  if (!pageIsSingleFile()) return;

  setMode("check");
  resetResultState();
  updateSelectedFileInfo();
  renderList("keyIssues", [], "当前没有重点问题。");
  renderList("nextSteps", [], "处理完成后，这里会显示下一步建议。");

  document.querySelectorAll(".mode-button").forEach((button) => {
    button.addEventListener("click", () => setMode(button.dataset.mode));
  });

  $("fileInput").addEventListener("change", (event) => {
    const [file] = event.target.files || [];
    state.selectedFile = file || null;
    updateSelectedFileInfo();
  });
  $("submitButton").addEventListener("click", () => {
    submitJob().catch((error) => {
      setError(`提交失败：${error.message || error}`);
    });
  });
  $("retryButton").addEventListener("click", retryLastRequest);
  $("resetButton").addEventListener("click", () => {
    $("fileInput").value = "";
    state.selectedFile = null;
    updateSelectedFileInfo();
    resetResultState();
  });
}

bindSingleFilePage();
