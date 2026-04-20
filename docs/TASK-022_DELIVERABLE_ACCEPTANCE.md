# TASK-022 DELIVERABLE ACCEPTANCE

## 1. 本轮目标

在不新增规则大类、不改 A/B/C 边界、不做大重构前提下，完成 GUI/CLI/runner/report 链路的易用性收口与可交付验收。

## 2. 实际验收范围

- 入口：CLI、GUI（核心执行函数）、batch-fix。
- 收口点：
  - 交互与提示文案收紧
  - 输出路径与产物可预期
  - 常见异常显式提示
  - 文档可直接交付试用
- 非目标：不扩展新规则，不修改主线规划，不引入云模型。

## 3. 实测入口

### 3.1 CLI

实测命令（2026-04-20）：

- `python3 -m thesis_format_fixer.cli check <docx> --report-json ... --report-md ...`
- `python3 -m thesis_format_fixer.cli fix <docx> --out <*.fixed.docx>`
- `python3 -m thesis_format_fixer.cli batch-fix <input_dir> --out-dir <output_dir> --no-recursive`
- `python3 -m thesis_format_fixer.cli check <not_docx.txt>`（异常场景）
- `python3 -m thesis_format_fixer.cli batch-fix <empty_dir> --out-dir <output_dir>`（空目录场景）
- `python3 -m thesis_format_fixer.cli batch-fix <input_dir> --out-dir <file_path>`（输出不可写场景）

结果：

- 正常场景可生成预期产物。
- `.txt` 输入被拒绝并返回码 `2`。
- 空目录返回码 `2`，并产出 `batch_summary`，`warning=输入目录中未找到 .docx 文件`。
- 输出目录不可创建时返回码 `2`，提示 `输出目录不可创建`。

### 3.2 GUI

实测方式（2026-04-20）：调用 GUI 核心执行函数：

- `execute_gui_task(input_file=..., mode='check')`
- `execute_gui_batch_task(input_dir=..., recursive=False)`

结果：

- 单文件 check 成功，生成 `*.check.report.json/md`。
- batch-fix 成功，生成每文件产物与 `batch_summary`。
- 失败时返回可理解错误字符串，不直出 traceback。

说明：当前环境为自动化/无交互窗口验收，未做人工点击式 UI 走查。

### 3.3 Batch

- 批量任务对单文件失败按“继续处理其余文件”策略执行。
- `batch_summary.items` 中记录每文件 `exit_code` 与 `error`（若有）。
- 汇总退出码：
  - 全成功 `0`
  - 部分失败 `1`
  - 输入目录非法/空目录/输出目录不可写 `2`

## 4. 关键通过项

- 输入不存在、输入非 `.docx`、输出目录不可写、空批量目录均有明确提示。
- GUI 与 CLI 共用 runner/report 主链路，未形成双轨实现。
- 单文件与批量输出命名保持一致约定（`*.fixed.docx` + 报告；batch 含汇总）。
- GUI 失败信息不再向普通用户暴露 traceback。
- README 已补齐安装、CLI/GUI、流程、产物、支持范围、未支持范围、常见失败说明。
- 全量测试通过：`81 passed`。

## 5. 已知限制

- GUI 自动化验收覆盖核心执行函数与结果格式；未在本轮做 headful 人工点击回归。
- 当前 fix 仍遵循既有安全边界，非白名单高风险规则保持不自动改写。
- 本轮未新增规则能力，仅做交付收口。

## 6. 结论

在 TASK-022 约束下，当前版本已达到“可直接交付试用”的收口标准。
