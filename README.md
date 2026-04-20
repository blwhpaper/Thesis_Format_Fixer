# thesis-format-fixer

`thesis-format-fixer` 是一个针对英文毕业论文 `.docx` 的格式检查/修复工具。

当前阶段：**TASK-022 可交付版收口与验收**。

## 1. 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## 2. CLI 用法

```bash
# 查看帮助
thesis-format-fixer --help

# 单文件检查（建议显式输出报告路径）
thesis-format-fixer check samples/input/demo.docx \
  --report-json samples/output/demo.check.report.json \
  --report-md samples/output/demo.check.report.md

# 单文件修复（安全输出到新文件，不覆盖原文件）
thesis-format-fixer fix samples/input/demo.docx \
  --out samples/output/demo.fixed.docx

# 批量修复（默认递归）
thesis-format-fixer batch-fix samples/input \
  --out-dir samples/output/batch

# 批量修复（仅当前目录）
thesis-format-fixer batch-fix samples/input \
  --out-dir samples/output/batch \
  --no-recursive
```

## 3. GUI 启动方式

```bash
python -m thesis_format_fixer.gui
```

GUI 模式支持：`check` / `fix` / `batch-fix`。

## 4. 单文件处理流程（GUI/CLI 一致走 runner/report）

1. 选择输入 `.docx`。
2. 选择输出目录（GUI）或 `--out`（CLI fix）。
3. 运行 `check` 或 `fix`。
4. 在输出目录查看生成产物（报告或修复文件+报告）。

## 5. 批量处理流程

1. 指定输入目录（默认递归扫描 `.docx`）。
2. 指定输出目录。
3. 执行 `batch-fix`。
4. 查看批处理汇总：`batch_summary.json`、`batch_summary.md`。
5. 查看每个文件的 `exit_code` 与产物路径。

## 6. 输出文件说明

### 单文件 `check`

- `*.check.report.json`
- `*.check.report.md`

### 单文件 `fix`

- `*.fixed.docx`
- `*.report.json`
- `*.report.md`

### 批量 `batch-fix`

- 每个输入文件对应：`*.fixed.docx` + `*.report.json` + `*.report.md`
- 保持输入目录的相对结构
- 汇总文件：
  - `batch_summary.json`
  - `batch_summary.md`

## 7. 当前支持范围（A/B/C 边界内）

- A 类低风险自动修复（已冻结白名单）
- B 类自动检查、报告提示
- C 类保持人工复核，不自动改写
- GUI 与 CLI 共用 `runner` 与 `report_builder` 主链路

规则基线与映射参考：

- `rules/FORMAT_RULEBOOK_v3.md`
- `docs/RULE_TO_ENGINE_MAPPING_TASK-003.md`
- `docs/V1_OUT_OF_SCOPE_TASK-003.md`

## 8. 当前未支持范围

以下仍为 out-of-scope，不应宣称已支持：

- 封皮模板重建与精细布局重建
- 自动目录域重建
- 正文起始分节与页码系统重构
- 脚注按页重编
- 装订线版面重排
- 参考文献内容级语义纠错/复杂重排

## 9. 常见问题与失败提示

- 输入文件不存在：会明确提示 `输入文件不存在`。
- 输入不是 `.docx`：会明确提示 `输入文件必须是 .docx`。
- 批量目录为空：会产出 `batch_summary`，并提示未找到 `.docx`。
- 输出目录不可写：会明确提示 `输出目录不可写/不可创建`。
- 批量中单个文件失败：不会中断全部任务，会在汇总中显示该文件 `exit_code` 与错误信息。
- GUI 运行失败：显示可理解错误信息，不向普通用户直出 Python traceback。

## 10. 规则来源

- `rules/FORMAT_RULEBOOK_v3.md`
- `rules/FORMAT_RULEBOOK_v2.md`
- `rules/sources/FORMAT_RULEBOOK_v1.md`
- `rules/sources/8. 毕业论文正文写作格式要求.docx`
- `rules/sources/10.1论文封皮.pdf`
- `rules/sources/太院教字[2021]03号太原学院毕业论文（设计）管理办法（终稿）.pdf`
