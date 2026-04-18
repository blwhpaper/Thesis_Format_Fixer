# TASK-007_MODEL_IO_SPEC

## 1. 输入协议（给本地模型）

输入为 JSON 对象，不传自由长文本。

必填字段：

- `task`: `heading_structure_review | reference_structure_review | pagination_review`
- `rule_ids`: 本次审查关联规则 ID 列表
- `context`: 与目标相关的最小片段（标题行、参考文献条目、分页相关信号）
- `constraints`:
  - `auto_fix_allowed=false`
  - `decision_enum=["pass","warn","fail","unable_to_judge"]`

## 2. 输出协议（模型返回）

模型必须返回 JSON 数组，每项映射一个 `ReviewFinding`：

- `rule_id`
- `block_id`
- `block_type`
- `target`
- `decision` (`pass|warn|fail|unable_to_judge`)
- `confidence` (0~1)
- `evidence` (数组，每项含 `reason`，可含 `paragraph_index/snippet`)
- `suggestion`
- `auto_fix_allowed` (必须为 `false`)
- `source` (必须为 `local_model`)

## 3. 校验与拒收策略

以下任一情况视为非法模型输出并触发降级：

- 非 JSON
- 非数组
- 缺少必填字段
- `decision/source/auto_fix_allowed` 不在允许值
- `confidence` 非数字或超范围

降级动作：

- 丢弃该次模型返回
- 保留规则审查结果
- 记录 `degraded_reasons`

## 4. 安全约束

- 模型不直接接触 docx 写回接口。
- 模型输出不直接裸贴进最终报告。
- 最终报告仅接收结构化字段。
