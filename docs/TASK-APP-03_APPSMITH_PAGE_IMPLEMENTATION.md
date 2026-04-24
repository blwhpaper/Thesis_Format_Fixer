# TASK-APP-03 Appsmith 首页与单文件处理页实现说明

## 1. 实际读取并核验文件清单

本轮已实际读取并核验以下文件：

- `README.md`
- `pyproject.toml`
- `docs/TASK-APP-01_APPSMITH_API_SPEC.md`
- `docs/TASK-APP-02_APPSMITH_UI_IA.md`
- `docs/APPsmith_UI_SKELETON.md`
- `src/thesis_format_fixer/api/app.py`
- `src/thesis_format_fixer/api/service.py`
- `src/thesis_format_fixer/api/models.py`
- `src/thesis_format_fixer/app/runner.py`
- `src/thesis_format_fixer/reporters/report_builder.py`
- `src/thesis_format_fixer/contracts/report_types.py`
- `src/thesis_format_fixer/contracts/review_types.py`
- `src/thesis_format_fixer/gui.py`
- `tests/test_smoke.py`
- `tests/test_task020_gui.py`
- `tests/test_task023_user_summary.py`
- 补充核验：`tests/test_api_smoke.py`
- 补充核验：`appsmith/preview/index.html`
- 补充核验：`appsmith/preview/app.js`
- 补充核验：`appsmith/preview/styles.css`
- 补充核验：`appsmith/skeleton/page_blueprint.json`
- 补充核验：`appsmith/docker-compose.yml`
- 补充核验：`appsmith/mock/*.json`

## 2. 已核验的真实前提

### 2.1 单文件 API 真实请求结构

- `POST /api/jobs/check`
  - `multipart/form-data`
  - 上传字段只有 `file`
- `POST /api/jobs/fix`
  - `multipart/form-data`
  - 上传字段只有 `file`

不支持额外业务参数，也没有单独的 mode 字段；模式由 endpoint 本身决定。

### 2.2 job status 查询接口真实返回字段

`GET /api/jobs/{job_id}` 返回 `job.json`，真实字段为：

- `job_id`
- `status`
- `mode`
- `input_filename`
- `output_filename`
- `summary`
- `user_summary`
- `artifacts`
- `error`

当前 `ApiJobService.create_job()` 是同步执行后直接落盘并返回结果，因此真实状态主要是：

- `completed`
- `failed`

前端可以保留“提交中 / 已提交”作为本地页面状态，但不能伪造后端存在 `queued/running/progress` 语义。

### 2.3 `artifacts / user_summary / categorized / summary` 真实口径

`artifacts` 真实字段：

- `input_file`
- `report_json`
- `report_md`
- `user_summary_md`
- `fixed_docx`
- `download_fixed_docx_url`
- `download_report_md_url`

其中真正可供浏览器下载的只有当前 API 明确暴露的：

- `download_report_md_url`
- `download_fixed_docx_url`

`user_summary` 供 Appsmith 消费时，由 `src/thesis_format_fixer/api/models.py` 压缩为：

- `overall_status`
- `processing_label`
- `categorized`
- `counts`
- `key_issues`
- `next_steps`
- `artifacts`

`categorized` 真实包含三类：

- `auto_processed`
- `detected_not_auto_fixed`
- `manual_review_required`

三类列表里的元素不是字符串，而是由 `report_builder.build_user_result_summary()` 生成的结构化条目，常见字段包括：

- `issue_title`
- `issue_description`
- `handling_status`
- `why_not_auto_fixed`
- `next_step`
- `rule_id`
- `reason_category`

`summary` 真实来自 `runner.py` 现有 payload，页面当前重点消费的技术字段包括：

- `auto_fix_rule_count`
- `detected_not_auto_modified_count`
- `manual_review_required_count`
- `reference_finding_count`
- `reference_blocking_count`
- `block_low_confidence_count`

### 2.4 当前仓内 Appsmith 目录、预览方式、mock / 骨架现状

已核验：

- `appsmith/docker-compose.yml`
  - 仅提供 Appsmith CE 容器启动位
- `appsmith/skeleton/page_blueprint.json`
  - 之前只有单页骨架定义
- `appsmith/preview/`
  - 是当前仓内唯一现成的页面预览机制
  - 通过静态 HTML/CSS/JS 本地预览
- `appsmith/mock/*.json`
  - 之前用于静态 mock 联动

结论：

- 仓内当前并没有真正的 Appsmith 导出工程或页面 JSON。
- 本轮最小落地策略是优先复用 `appsmith/preview` 和 `appsmith/skeleton/page_blueprint.json`。

## 3. 实际新增 / 修改文件清单

### 新增文件

- `appsmith/preview/single-file.html`
- `appsmith/preview/batch-placeholder.html`
- `appsmith/preview/help.html`
- `docs/TASK-APP-03_APPSMITH_PAGE_IMPLEMENTATION.md`

### 修改文件

- `appsmith/preview/index.html`
- `appsmith/preview/app.js`
- `appsmith/preview/styles.css`
- `appsmith/skeleton/page_blueprint.json`
- `src/thesis_format_fixer/api/app.py`

## 4. 页面结构摘要

### 4.1 工作台首页

已真实落地以下区块：

- 工具简介
- 单文件处理入口
- 批量处理预留入口
- 规则与帮助入口
- 简短操作步骤
- 本轮范围说明
- 本地预览提示

### 4.2 单文件处理页

已真实落地以下区块：

- 文件上传区
- 检查 / 修复模式切换
- 提交按钮 / 重试按钮 / 重置按钮
- 任务状态区
- 用户摘要区
- 问题明细区
- 技术报告区
- 下载区
- 错误信息区

### 4.3 额外补充页

为满足首页入口闭环，同时保持真实边界，本轮补充：

- `batch-placeholder.html`
- `help.html`

其中批量页明确标注为预留，不提供伪执行。

## 5. 页面组件清单

### 工作台首页

- 顶部 Hero
- 导航入口条
- 工具简介卡
- 快速开始卡
- 单文件处理入口卡
- 批量处理预留卡
- 规则与帮助入口卡
- 本轮落地范围卡
- 本地预览提示卡

### 单文件处理页

- API Base URL 输入框
- API 健康检查按钮
- 文件选择器
- 检查 / 修复模式按钮组
- 提交按钮
- 重试按钮
- 重置按钮
- `job_id / status / mode` 展示
- 3 个结果统计卡
- 总体状态卡
- 重点问题列表
- 建议下一步列表
- 结构化问题表格
- summary 技术统计 chips
- JSON viewer
- 报告下载入口
- 修订稿下载入口
- 错误信息提示区

## 6. Queries / Actions / States 设计

### 6.1 页面状态

本轮实际落地的最小状态流：

- `selectedFile`
- `selectedMode`
- `currentJobId`
- `currentJobStatus`
- `latestResultPayload`
- `latestArtifacts`
- `latestError`

### 6.2 实际动作设计

- `checkHealth()`
  - 请求 `GET /api/health`
- `submitJob()`
  - 根据 `selectedMode` 调用：
    - `POST /api/jobs/check`
    - `POST /api/jobs/fix`
- `pollJob(jobId)`
  - 请求 `GET /api/jobs/{job_id}`
- `retryLastRequest()`
  - 复用当前已选文件和最近一次 mode 再提交
- `resetResultState()`
  - 只清空前端状态，不改后端

### 6.3 结果展示绑定

第一层，用户友好摘要：

- `user_summary.overall_status`
- `user_summary.counts.*`
- `user_summary.key_issues`
- `user_summary.next_steps`

第二层，问题明细表：

- `user_summary.categorized.auto_processed`
- `user_summary.categorized.detected_not_auto_fixed`
- `user_summary.categorized.manual_review_required`
- `summary.*` 技术统计

第三层，技术报告：

- `latestResultPayload` 原始 JSON

### 6.4 下载区绑定

只展示真实下载项：

- `artifacts.download_report_md_url`
- `artifacts.download_fixed_docx_url`

不会把仅本地路径字段伪装成浏览器下载项：

- `report_json`
- `report_md`
- `user_summary_md`
- `fixed_docx`

这些路径仍保留在技术 payload 里，但不在下载区伪装成真实下载按钮。

## 7. 已跑通链路说明

### 7.1 真实跑通的后端链路

已通过现有测试真实验证：

- 上传 `.docx` 到 `POST /api/jobs/check`
- 返回 `job_id`
- 查询 `GET /api/jobs/{job_id}`
- 下载 `GET /api/jobs/{job_id}/download/report-md`

也已真实验证：

- 上传 `.docx` 到 `POST /api/jobs/fix`
- 返回 `job_id`
- 查询 fix 结果
- 下载 `GET /api/jobs/{job_id}/download/fixed-docx`

对应测试：

- `tests/test_api_smoke.py`

### 7.2 本轮页面接通的链路

`appsmith/preview/single-file.html` 已真实接到上述 API 字段与 endpoint：

- 选择文件
- 选择 `check/fix`
- 提交任务
- 读取返回 `job_id`
- 轮询 `GET /api/jobs/{job_id}`
- 成功后分三层展示结果
- 失败后展示错误并允许重试
- 下载区只显示 API 真正返回的下载项

### 7.3 关于轮询的真实说明

当前后端是同步执行并立即落盘，因此轮询行为的真实意义是：

- 读取同一个 `job_id` 的落盘结果
- 为后续可能扩展为异步执行预留前端状态流

不能宣称已实现真实异步队列或百分比进度。

## 8. 当前限制与遗留问题

- 当前仓内没有真正的 Appsmith 页面导出工程，本轮落地基于 `appsmith/preview` 静态预览机制。
- 批量处理页仍是预留态，因为当前没有批量 HTTP API。
- API 目前只提供 `report-md` 和 `fixed-docx` 下载 endpoint，没有 `user_summary_md` 单独下载 endpoint。
- 前端问题明细当前以 `categorized` 三类结构为主，没有新增第二套表结构。
- 后端 job status 当前真实只有同步完成后的 `completed/failed`，没有 `queued/running`。

## 9. 本轮最小后端补丁说明

本轮仅对 `src/thesis_format_fixer/api/app.py` 增加了 CORS 中间件：

- 原因：浏览器态 preview 页面需要直接请求本地 API
- 目的：不改动核心 runner / report 语义，只解除消费层联调阻塞

未修改：

- `runner.py` 核心执行逻辑
- 报告构建语义
- 下载 endpoint 语义

## 10. 下一步建议

最合理的下一步任务是：

1. 决定是否要把当前 `appsmith/preview` 页面真正迁移为 Appsmith 内部页面配置。
2. 若继续推进在线批量能力，优先新增批量 HTTP API，而不是先做前端假页面。
3. 若需要更完整下载体验，再补 `user_summary_md` 的显式下载 endpoint。
4. 若未来要做真实异步任务，再补 `queued/running` 状态与更稳定的轮询协议。

## 11. 收尾说明

TASK-APPsmith-03 收尾阶段，单文件预览页已进一步去技术化：

- 页面不再展示 `selectedFile`、`selectedMode`、`API Base URL`、健康检查入口。
- 页面不再直出接口名、字段来源、路径名、payload key。
- `job_id` 与内部状态明细不再作为用户可见信息展示。
- 统计卡片仅保留用户可理解标题、数字和简短文案。
- 问题明细表去掉 `rule_id`、原因分类等开发态字段展示。
- 原始 JSON viewer 与 summary 技术 chips 已从用户页面移除。
