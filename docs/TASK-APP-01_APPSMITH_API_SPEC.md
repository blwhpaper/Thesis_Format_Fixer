# TASK-APP-01 Appsmith API Spec

## 1. 目标

提供最小可用 HTTP 服务，供 Appsmith 调用现有论文格式整理引擎的单文件主链路：

- 单文件 `check`
- 单文件 `fix`
- 结果读取
- 产物下载

本接口层不重写规则引擎，只负责：

- 参数校验
- 上传文件保存
- 建立 `job_id` 和工作目录
- 调用现有 `runner`
- 返回统一 JSON
- 暴露下载地址

## 2. 服务启动

```bash
thesis-format-fixer-api
```

默认地址：

- `http://127.0.0.1:8000`

可通过环境变量调整 job 根目录：

- `THESIS_FORMAT_FIXER_API_ROOT`

未设置时默认使用系统临时目录下的：

- `thesis-format-fixer-api/<job_id>/`

## 3. 接口列表

### `GET /api/health`

健康检查。

响应示例：

```json
{
  "status": "ok"
}
```

### `POST /api/jobs/check`

表单上传字段：

- `file`: 单个 `.docx`

行为：

- 生成 `job_id`
- 保存原始文件到独立工作目录
- 调用 `run_check_with_details()`
- 返回统一结果 JSON

### `POST /api/jobs/fix`

表单上传字段：

- `file`: 单个 `.docx`

行为：

- 生成 `job_id`
- 保存原始文件到独立工作目录
- 调用 `run_fix_with_details()`
- 输出修复后的 `.fixed.docx`
- 返回统一结果 JSON

### `GET /api/jobs/{job_id}`

读取该 job 最近一次落盘结果。

### `GET /api/jobs/{job_id}/download/fixed-docx`

下载修复后的 `.docx`。

说明：

- 仅 `fix` 成功时可用
- `check` 模式或失败 job 会返回 404

### `GET /api/jobs/{job_id}/download/report-md`

下载 Markdown 技术报告。

## 4. 统一响应结构

所有主接口返回统一 JSON 结构，至少包含：

```json
{
  "job_id": "string",
  "status": "completed",
  "mode": "check",
  "input_filename": "demo.docx",
  "output_filename": null,
  "summary": {},
  "user_summary": {
    "overall_status": "string",
    "processing_label": "检查",
    "categorized": {
      "auto_processed": [],
      "detected_not_auto_fixed": [],
      "manual_review_required": []
    },
    "counts": {
      "auto_processed": 0,
      "detected_not_auto_fixed": 0,
      "manual_review_required": 0
    },
    "key_issues": [],
    "next_steps": [],
    "artifacts": []
  },
  "artifacts": {
    "input_file": "/abs/path/input/demo.docx",
    "report_json": "/abs/path/output/demo.report.json",
    "report_md": "/abs/path/output/demo.report.md",
    "user_summary_md": "/abs/path/output/check.user_summary.md",
    "fixed_docx": null,
    "download_fixed_docx_url": null,
    "download_report_md_url": "/api/jobs/<job_id>/download/report-md"
  },
  "error": null
}
```

字段说明：

- `summary`: 复用现有技术摘要字段
- `user_summary`: 面向 Appsmith 的轻量用户摘要
- `categorized.auto_processed`: 已自动处理
- `categorized.detected_not_auto_fixed`: 发现问题但未自动改
- `categorized.manual_review_required`: 需要手动检查
- `error`: 统一错误消息；成功时为 `null`

## 5. 错误处理

错误返回仍保持同一 JSON 外形，`status=failed`，并在 `error` 中给出说明。

当前最小校验包含：

- 未上传文件
- 非 `.docx`
- 空文件
- 不存在的 `job_id`
- 不存在的下载产物

## 6. 工作目录约定

每次请求一个独立目录：

```text
<jobs_root>/<job_id>/
  input/
    original.docx
  output/
    *.report.json
    *.report.md
    check.user_summary.md | fix.user_summary.md
    *.fixed.docx
  job.json
```

其中：

- `job.json` 是 `GET /api/jobs/{job_id}` 的读取来源
- 下载接口直接暴露 `output/` 中的已有产物

## 7. 与现有 CLI / GUI 的边界

- API 不进入 `gui.py`
- API 复用 `runner.py` 现有单文件入口
- CLI / GUI 原有行为保持不变
- 规则引擎、报告构建、用户摘要生成逻辑不在本任务内重写
