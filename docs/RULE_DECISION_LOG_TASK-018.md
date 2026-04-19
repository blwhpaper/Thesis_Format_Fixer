# RULE_DECISION_LOG_TASK-018

## 目标

- 将参考文献相关问题从粗粒度 report 暴露继续下沉为细粒度 checker + finding。
- 仅做审查增强，不做高风险自动改写。

## 冻结口径落地

- 类型标识检查：`M/C/N/J/D/R/S/P/DB/CP/EB`，并支持如 `[J/OL]`、`[EB/OL]` 的组合审查。
- J 类结构：`作者. 题目[J]. 期刊名, 年份(期数): 页码.`
- M/D/R 类结构：`作者. 书名或题名[类型]. 版次. 出版地: 出版单位, 年份, 页码.`（D 类按本任务冻结规则禁止页码）
- 分组与数量：英文在前、中文在后；英文文献不少于 5 篇。
- 新增冻结规则：
  - 英文条目禁止 `《》`
  - D 类条目禁止页码

## TASK-018 Finding Code 清单

- `reference_type_marker_missing`
- `reference_type_marker_invalid`
- `reference_type_carrier_invalid`
- `reference_journal_structure_invalid`
- `reference_book_structure_invalid`
- `reference_thesis_structure_invalid`
- `reference_eb_ol_structure_invalid`
- `reference_language_order_invalid`
- `reference_english_count_insufficient`
- `reference_punctuation_invalid`
- `reference_field_order_invalid`
- `reference_english_contains_cn_book_title_marks`
- `reference_d_thesis_has_page_range`

## 结构化字段约束

每条参考文献 finding 至少包含：

- `rule_code`
- `finding_code`
- `severity`
- `block_id`
- `reference_index`
- `reference_text`
- `reason` 或 `expected_pattern`
- `is_auto_fixable=false`

## 范围声明

- 不扩展到正文其它区块。
- 不实现“近三年为主”“与开题报告差异 3-5 篇”等外部依赖规则。
- 不做引文-脚注-参考文献交叉核验。
