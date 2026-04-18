# TASK-007_REVIEW_ARCHITECTURE

## 1. 架构定位

V2 智能审查器作为现有执行链路中的附加阶段：

1. `document_loader` 加载文档上下文
2. `block_locator` 输出区块定位
3. 现有规则记录与 TASK-006 逻辑执行
4. **V2 review（本轮新增）**
5. `report_builder` 汇总输出

说明：V2 review 仅产生结构化审查结论，不触发任何写回。

## 2. 组件

- `contracts/review_types.py`
  - 定义 `ReviewDecision / ReviewFinding / ReviewEvidence / ReviewStatus / IntelligentReviewReport`
- `review/model_adapter.py`
  - 本地模型统一接口与降级适配器
- `review/reviewer.py`
  - 审查编排器，负责 mode/target 调度与降级控制
- `review/checkers.py`
  - 三个最小审查器：`heading_structure_review / reference_structure_review / pagination_review`

## 3. 模型接入位置

- 规则审查始终先执行并形成基线 finding。
- `review_mode=llm` 时：
  - 调用本地模型适配层进行辅助 verdict 生成或补充。
  - 模型 verdict 必须通过结构校验后才可并入。
- `review_mode=basic` 时：
  - 仅运行规则审查，不调用模型。

## 4. 降级路径

- `review_mode=off`：不执行 V2 审查。
- `review_mode=llm` 但未配置模型：降级为 `basic`，记录降级原因。
- 模型调用异常 / 非法 JSON / 字段不合法：该模型结果丢弃并降级为规则审查结果，不中断 runner。

## 5. 报告并入

- 在现有报告 `sections` 中新增 `intelligent_review` 区块（仅 review 开启时出现）。
- 区块内包含：
  - 审查状态
  - 审查模式
  - 审查目标
  - 结构化 findings
  - 降级原因
- Markdown 报告新增“智能审查结果”段，标注 `source=rule_engine/local_model`。
