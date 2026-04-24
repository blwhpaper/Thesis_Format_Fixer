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

function getApiBaseUrl() {
  const input = $("apiBaseUrlInput");
  const value = input ? input.value.trim() : "";
  return value || DEFAULT_API_BASE_URL;
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
        ? "修复模式会调用 POST /api/jobs/fix，并在成功时尝试展示修订稿下载。"
        : "检查模式会调用 POST /api/jobs/check，只生成报告与摘要。";
  }
  const modeValue = $("jobModeValue");
  if (modeValue) {
    modeValue.textContent = state.selectedMode;
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
  const errorBox = $("errorBox");
  if (!errorBox) return;
  errorBox.className = `status-box ${tone === "error" ? "danger" : "subtle"}`;
  errorBox.textContent = message || "当前没有错误。";
}

function setJobStatus(status, headline, copy) {
  state.currentJobStatus = status;
  const statusHeadline = $("jobStatusHeadline");
  const statusCopy = $("jobStatusCopy");
  const statusValue = $("jobStatusValue");
  if (statusHeadline) statusHeadline.textContent = headline;
  if (statusCopy) statusCopy.textContent = copy;
  if (statusValue) statusValue.textContent = status;
}

function resetResultState() {
  state.currentJobId = null;
  state.currentJobStatus = "idle";
  state.latestResultPayload = null;
  state.latestArtifacts = {};
  state.latestError = null;
  const jobIdValue = $("jobIdValue");
  if (jobIdValue) jobIdValue.textContent = "-";
  setJobStatus("idle", "尚未提交任务", "请选择文件并提交。");
  renderPayload(null);
  setError("", "subtle");
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
        ruleId: item.rule_id || "-",
        reasonCategory: item.reason_category || "-",
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
  const summaryCounts = $("summaryCounts");
  if (!body || !empty || !wrap || !summaryCounts) return;

  body.innerHTML = "";
  if (!payload) {
    wrap.hidden = true;
    empty.hidden = false;
    empty.textContent = "结果返回后，这里会按三类问题展开结构化明细。";
    summaryCounts.innerHTML = "";
    return;
  }

  const rows = flattenCategorizedRows(payload.user_summary || {});
  if (!rows.length) {
    wrap.hidden = true;
    empty.hidden = false;
    empty.textContent = "本次返回中没有可展开的问题明细，当前仅保留统计与技术 payload。";
  } else {
    wrap.hidden = false;
    empty.hidden = true;
    rows.forEach((row) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${row.category}</td>
        <td>${row.title}</td>
        <td>${row.handlingStatus}</td>
        <td>${row.ruleId}</td>
        <td>${row.reasonCategory}</td>
        <td>${row.nextStep}</td>
      `;
      body.appendChild(tr);
    });
  }

  const summary = payload.summary || {};
  summaryCounts.innerHTML = `
    <div class="summary-chip">auto_fix_rule_count: ${summary.auto_fix_rule_count ?? 0}</div>
    <div class="summary-chip">detected_not_auto_modified_count: ${summary.detected_not_auto_modified_count ?? 0}</div>
    <div class="summary-chip">manual_review_required_count: ${summary.manual_review_required_count ?? 0}</div>
    <div class="summary-chip">reference_finding_count: ${summary.reference_finding_count ?? 0}</div>
    <div class="summary-chip">reference_blocking_count: ${summary.reference_blocking_count ?? 0}</div>
  `;
}

function renderDownloads(artifacts, mode) {
  const list = $("downloadList");
  const hint = $("downloadHint");
  if (!list || !hint) return;
  list.innerHTML = "";

  const downloadItems = [];
  if (artifacts && artifacts.download_report_md_url) {
    downloadItems.push({
      label: "下载技术报告（Markdown）",
      url: normalizeApiUrl(artifacts.download_report_md_url),
      description: "真实 API 下载地址",
    });
  }
  if (artifacts && artifacts.download_fixed_docx_url) {
    downloadItems.push({
      label: "下载修订稿 DOCX",
      url: normalizeApiUrl(artifacts.download_fixed_docx_url),
      description: "仅 fix 成功时返回",
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
    row.innerHTML = "<div><strong>技术报告下载</strong><p>当前结果没有可下载的 Markdown 报告。</p></div>";
    list.appendChild(row);
  }

  if (mode === "fix" && (!artifacts || !artifacts.download_fixed_docx_url)) {
    const row = document.createElement("div");
    row.className = "download-item muted-download";
    row.innerHTML = "<div><strong>修订稿下载</strong><p>当前无可下载修订稿。</p></div>";
    list.appendChild(row);
  }

  if (mode === "check") {
    hint.textContent = "检查模式下不会生成修订稿下载；若存在技术报告下载，会在上方单独展示。";
  } else {
    hint.textContent = "修复模式下若 API 返回 `download_fixed_docx_url`，这里会显示修订稿下载。";
  }
}

function renderPayload(payload) {
  const overallStatusBox = $("overallStatusBox");
  const technicalViewer = $("technicalReportViewer");
  if (overallStatusBox) {
    overallStatusBox.textContent = payload?.user_summary?.overall_status || "暂无结果。";
  }
  renderCounts(payload?.user_summary || {});
  renderList("keyIssues", payload?.user_summary?.key_issues || [], "当前没有重点问题。");
  renderList("nextSteps", payload?.user_summary?.next_steps || [], "处理完成后，这里会显示下一步建议。");
  renderDetailTable(payload);
  renderDownloads(payload?.artifacts || {}, payload?.mode || state.selectedMode);
  if (technicalViewer) {
    technicalViewer.textContent = JSON.stringify(payload || {}, null, 2);
  }
}

function applyJobPayload(payload) {
  state.latestResultPayload = payload;
  state.latestArtifacts = payload && payload.artifacts ? payload.artifacts : {};
  state.currentJobId = payload?.job_id || null;
  if ($("jobIdValue")) {
    $("jobIdValue").textContent = state.currentJobId || "-";
  }
  setMode(payload?.mode || state.selectedMode);
  renderPayload(payload);

  if (payload?.status === "failed") {
    setJobStatus("failed", "任务执行失败", payload.error || "请检查上传文件和 API 状态后重试。");
    setError(payload.error || "任务失败。");
    return;
  }

  if (payload?.status === "completed") {
    setJobStatus("completed", "任务已完成", payload.user_summary?.overall_status || "结果已返回。");
    setError("", "subtle");
    return;
  }

  setJobStatus(payload?.status || "unknown", "任务处理中", "已拿到 job_id，正在读取最新结果。");
}

async function checkHealth() {
  state.apiBaseUrl = getApiBaseUrl();
  try {
    const response = await fetch(normalizeApiUrl("/api/health"));
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    setError(`API 连通正常：${payload.status}`, "subtle");
  } catch (error) {
    setError(`API 连通失败：${error.message || error}`);
  }
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
  state.apiBaseUrl = getApiBaseUrl();
  if (!state.selectedFile) {
    setError("请先选择一个 .docx 文件。");
    return;
  }

  const formData = new FormData();
  formData.append("file", state.selectedFile);
  state.lastSubmittedMode = state.selectedMode;
  setJobStatus("submitting", "任务提交中", "正在上传文件并创建任务。");
  setError("", "subtle");

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
    setJobStatus("submitted", "任务已提交", "已获取 job_id，开始查询任务结果。");
    await pollJob(payload.job_id);
  } catch (error) {
    setJobStatus("failed", "提交失败", "请检查 API 地址、文件内容或稍后重试。");
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

  $("apiBaseUrlInput").addEventListener("change", () => {
    state.apiBaseUrl = getApiBaseUrl();
  });
  $("healthCheckButton").addEventListener("click", () => {
    checkHealth().catch((error) => {
      setError(`API 检查失败：${error.message || error}`);
    });
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
