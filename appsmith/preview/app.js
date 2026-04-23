const datasets = {
  empty: "/appsmith/mock/empty-result.json",
  check: "/appsmith/mock/check-result.json",
  fix: "/appsmith/mock/fix-result.json",
  failure: "/appsmith/mock/failure-result.json",
};

const stateSelect = document.getElementById("stateSelect");
const modeButtons = Array.from(document.querySelectorAll(".mode-button"));
const overallStatus = document.getElementById("overallStatus");
const processingLabel = document.getElementById("processingLabel");
const autoProcessedCount = document.getElementById("autoProcessedCount");
const detectedCount = document.getElementById("detectedCount");
const manualReviewCount = document.getElementById("manualReviewCount");
const issueTableBody = document.getElementById("issueTableBody");
const downloadList = document.getElementById("downloadList");
const keyIssues = document.getElementById("keyIssues");
const nextSteps = document.getElementById("nextSteps");
const emptyState = document.getElementById("emptyState");
const tableWrap = document.getElementById("tableWrap");
const modeDescription = document.getElementById("modeDescription");

function setMode(mode) {
  modeButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === mode);
  });
  modeDescription.value =
    mode === "fix"
      ? "自动修复可处理的问题，并保留人工复核清单"
      : "仅检测格式问题，不改原文件";
}

function severityClass(level) {
  if (level === "高") return "status-high";
  if (level === "中") return "status-medium";
  return "status-low";
}

function renderList(target, items, fallback) {
  target.innerHTML = "";
  if (!items.length) {
    const li = document.createElement("li");
    li.textContent = fallback;
    target.appendChild(li);
    return;
  }
  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    target.appendChild(li);
  });
}

function renderDownloads(artifacts) {
  downloadList.innerHTML = "";
  const candidates = [
    { label: "修复后文档", path: artifacts.fixed_docx },
    { label: "检查报告", path: artifacts.report_md },
    { label: "用户摘要", path: artifacts.user_summary_md },
  ].filter((item) => item.path);

  if (!candidates.length) {
    downloadList.innerHTML = "<div class='empty-state'>当前状态下还没有可下载产物。</div>";
    return;
  }

  candidates.forEach((item) => {
    const row = document.createElement("div");
    row.className = "download-item";
    row.innerHTML = `<div><strong>${item.label}</strong><p>${item.path}</p></div><button>下载</button>`;
    downloadList.appendChild(row);
  });
}

function renderTable(rows) {
  issueTableBody.innerHTML = "";
  if (!rows.length) {
    tableWrap.hidden = true;
    emptyState.hidden = false;
    return;
  }
  tableWrap.hidden = false;
  emptyState.hidden = true;
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.rule_code}</td>
      <td>${row.title}</td>
      <td>${row.section}</td>
      <td class="${severityClass(row.severity)}">${row.severity}</td>
      <td>${row.auto_fixed}</td>
      <td>${row.suggestion}</td>
    `;
    issueTableBody.appendChild(tr);
  });
}

async function loadState(stateKey) {
  const response = await fetch(datasets[stateKey]);
  const payload = await response.json();
  const mode = payload.mode === "fix" ? "fix" : "check";
  setMode(mode);

  overallStatus.textContent = payload.user_summary.overall_status;
  processingLabel.textContent = payload.user_summary.processing_label;
  autoProcessedCount.textContent = payload.user_summary.counts.auto_processed;
  detectedCount.textContent = payload.user_summary.counts.detected_not_auto_fixed;
  manualReviewCount.textContent = payload.user_summary.counts.manual_review_required;

  renderTable(payload.issue_rows || []);
  renderDownloads(payload.artifacts || {});
  renderList(keyIssues, payload.user_summary.key_issues || [], "当前没有重点问题。");
  renderList(nextSteps, payload.user_summary.next_steps || [], "处理完成后，这里会给出下一步建议。");
}

modeButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const nextState = button.dataset.mode === "fix" ? "fix" : "check";
    stateSelect.value = nextState;
    loadState(nextState);
  });
});

stateSelect.addEventListener("change", (event) => {
  loadState(event.target.value);
});

loadState("empty");
