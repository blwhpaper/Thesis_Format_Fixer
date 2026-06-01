# TASK-008 真实样本回灌校准

## 1. 回灌样本

- 样本文件：`runs/sample_run_001/example_thesis_fixed.docx`
- 校准日期：2026-04-18
- 输出目录：`runs/task008_calibration/`

## 2. 执行命令

```bash
PYTHONPATH=src python3 -m thesis_format_fixer.cli check \
  runs/sample_run_001/example_thesis_fixed.docx \
  --report-json runs/task008_calibration/check.report.json \
  --report-md runs/task008_calibration/check.report.md

PYTHONPATH=src python3 -m thesis_format_fixer.cli fix \
  runs/sample_run_001/example_thesis_fixed.docx \
  --out runs/task008_calibration/example_thesis_fixed.task008.fixed.docx \
  --report-json runs/task008_calibration/fix.report.json \
  --report-md runs/task008_calibration/fix.report.md
```

## 3. 命中前后差异

- `check` 阶段：`auto_fix_rule_count=0`，A 类以 `detected_not_modified` 暴露，体现“应命中未写回”。
- `fix` 阶段：`auto_fix_rule_count=19`，`a_class_hit_count=26`，命中已不再局限于脚注。
- `fix` 阶段 `a_class_unhit_count=1`：仅 `FR-4.11-02`（参考文献条目）未稳定命中。

## 4. 本轮已稳定命中的 A 类

- 摘要/关键词：`FR-4.2-01/02/03`, `FR-4.3-01`, `FR-4.4-01/02/03`, `FR-4.5-01/02`
- 目录与正文：`FR-4.6-01/02`, `FR-4.7-01/02`, `FR-4.8-03/04/05`, `FR-4.9-01`
- 参考文献标题与致谢：`FR-4.11-01`, `FR-4.12-01/02`
- 页面基础格式：`FR-4.13-02`, `FR-4.14-01/02`
- 脚注样式：`FR-4.10-02/03/04`

## 5. 当前仍未稳定命中的 A 类

- `FR-4.11-02`（参考文献条目基础字体字号行距）
- 当前样本中未检出稳定“参考文献条目模式”，`references_entries` block 置信度为 0.0，已在报告中显式标记为未命中。

## 6. 为什么暂不扩到 B/C

- 本轮只修 A 类命中面与链路打通，不新增内容改写逻辑。
- 未实现目录域重建、页码分节重构、脚注按页重编、参考文献内容级改写等 B/C 或 Out-of-V1 能力。
- 报告中仍保留 `detected_not_auto_modified` 与 `manual_review_required` 暴露机制，避免越界自动修改。
