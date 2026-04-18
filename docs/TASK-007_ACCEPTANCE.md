# TASK-007_ACCEPTANCE

## 1. 功能验收

- 已新增 V2 审查能力，且默认关闭。
- CLI 支持：
  - `--review-mode off|basic|llm`
  - `--review-target headings,references,pagination`
  - `--review-local-model <name>`
- 三个最小审查器可输出结构化 verdict：
  - 标题层级
  - 参考文献结构
  - 页码/正文起始

## 2. 安全验收

- 审查结果 `auto_fix_allowed=false`。
- V2 审查不触发任何 docx 回写。
- 本地模型异常不阻断主链路。
- 不扩展到 V1/V2 范围外能力。

## 3. 报告验收

- 现有报告体系保留。
- 开启 review 时新增“智能审查结果”区块。
- 明确区分 `source=rule_engine` 与 `source=local_model`。
- 不出现模型自由文本长评裸贴。

## 4. 测试验收

最小测试集覆盖：

- 审查契约结构
- review 关闭不影响原链路
- review 开启且无模型时可降级
- mock 模型合法返回并入报告
- mock 模型非法返回触发降级
- 三个审查器最小样例
- 审查器不触发格式回写
