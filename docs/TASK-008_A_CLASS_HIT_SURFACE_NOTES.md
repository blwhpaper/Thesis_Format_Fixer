# TASK-008 A 类命中面修复说明

## 1. 理论应命中面（按目标区块）

| 目标区块 | 规则 ID |
|---|---|
| 中文摘要标题/正文/关键词 | FR-4.2-01/02/03, FR-4.3-01 |
| 英文摘要标题/正文/关键词 | FR-4.4-01/02/03, FR-4.5-01/02 |
| 目录标题/目录内容基础样式 | FR-4.6-01/02 |
| 正文主标题/副标题 | FR-4.7-01/02 |
| 一级/二级/三级标题基础样式 | FR-4.8-03/04/05 |
| 正文普通段落 | FR-4.9-01 |
| 脚注基础样式 | FR-4.10-02/03/04 |
| 参考文献标题/条目基础样式 | FR-4.11-01/02 |
| 致谢标题/正文 | FR-4.12-01/02 |
| 页边距、页眉、页脚基础格式 | FR-4.13-02, FR-4.14-01/02 |

## 2. 真实样本“只改到脚注”的根因

- `block_locator` 只有少量锚点标题定位，缺少正文/参考文献条目/页面格式块。
- `runner` 仅执行 `task006_specials`，实际写回集中在脚注与参考文献专项。
- `report` 未单独暴露 A 类 `hit/unhit/degraded`，难以快速识别命中面缺口。
- `registry` 将多项 A 类基础样式规则放在 `REPORT_ONLY`，导致运行时白名单不包含这些规则。

## 3. 本轮最小改动链路

1. `detectors/block_locator.py`
- 新增区块：摘要正文、正文区块、正文标题层级、正文普通段落、参考文献条目、致谢正文、页边距/页眉/页脚能力块。
- 兼容保留旧 block id（`contents/references/ack/abstract_*`）避免 TASK-007 受影响。

2. `rules/registry.py` + `rules/whitelist.py`
- 将 A 类基础样式规则恢复到 `AUTO_FIX`（由白名单自动继承）。
- 未变更 B/C 和 Out-of-V1 规则集合。

3. `app/runner.py`
- 新增 TASK-008 A 类执行器接入：`execute_task008_a_surface_docx`。
- 与 TASK-006 合并时保留 `fixed` 优先级，避免后续执行器覆盖已命中结果。

4. `reporters/report_builder.py` + runner payload
- 增加 A 类命中面汇总：`a_class_hit_surface.hit/unhit/degraded`。
- 报告摘要新增 A 类计数：`a_class_hit_count/unhit_count/degraded_count`。

## 4. 边界控制

- 仅处理样式级 A 类修复，不做内容改写。
- 未新增 B 类自动改写器。
- 保持 Out-of-V1 硬拦截能力不变。
