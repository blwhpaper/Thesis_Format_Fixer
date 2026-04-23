# TASK-APP-02 Appsmith UI 信息架构与页面结构

## 1. 背景与目标

### 1.1 背景

当前仓库已经具备论文格式处理的核心工具链，但入口分散在 CLI、PySide6 GUI 和最小 FastAPI 接口中。已有实现已经证明以下能力是真实存在的：

- 单文件检查：`run_check_with_details()` / `POST /api/jobs/check`
- 单文件修复：`run_fix_with_details()` / `POST /api/jobs/fix`
- 批量修复：`run_batch_fix()`（当前主要由 CLI / GUI 消费）
- 结构化报告：JSON + Markdown 技术报告
- 用户友好摘要：`user_summary` + `*.user_summary.md`

当前问题不是“有没有处理能力”，而是“如何把已有能力以普通用户可理解的页面结构暴露出来”。如果直接在 Appsmith 中堆控件，容易把技术字段、产物路径、人工复核项全部混在一层，导致页面可用性很差。

### 1.2 本文目标

本文只做 UI 信息架构与页面结构收口，不做 Appsmith 页面实现，不改写后端。

本文目标：

- 基于现有 runner / report / API 的真实能力，定义 Appsmith 最小可落地页面地图
- 明确用户任务流、页面拆分、区块结构、状态流转、结果展示层级
- 明确哪些能力已有后端支撑，哪些只能预留
- 为下一轮 Appsmith 实作提供稳定蓝图，避免 UI 设计超出仓内现有能力边界

### 1.3 本轮边界

- 不重写 `runner.py`
- 不新增批量 HTTP API
- 不声称“Appsmith 页面已完成”
- 不把规则引擎包装成新的 SaaS 业务模型
- 所有结论都以仓内已有代码、测试和文档为依据

## 2. 当前工具流程抽象

### 2.1 已核验的主流程

基于 `README.md`、`src/thesis_format_fixer/app/runner.py`、`src/thesis_format_fixer/gui.py`、`src/thesis_format_fixer/api/app.py`、`src/thesis_format_fixer/api/service.py`、相关测试文件，当前真实存在以下主流程。

#### 2.1.1 单文件检查

真实存在。

- 入口：
  - CLI `thesis-format-fixer check`
  - GUI `check`
  - API `POST /api/jobs/check`
- 后端支撑：
  - `run_check_with_details()`
  - 输出 `report.json`、`report.md`、`check.user_summary.md`
  - 返回 `summary`、`sections`、`user_summary`、`artifacts`
- UI 可消费性：
  - 非常适合 Appsmith 直接承接

#### 2.1.2 单文件修复

真实存在，但要明确当前“修复”的能力边界。

- 入口：
  - CLI `thesis-format-fixer fix`
  - GUI `fix`
  - API `POST /api/jobs/fix`
- 后端支撑：
  - `run_fix_with_details()`
  - 输出 `*.fixed.docx`、`report.json`、`report.md`、`fix.user_summary.md`
- 关键边界：
  - `runner.py` 中明确写有 `V1 safety boundary: no content/style write-back, only passthrough copy + report`
  - 因此 UI 上不能把 `fix` 描述为“全自动彻底修复”，只能描述为“生成修复输出与结果报告，仍可能包含未自动修改/需人工复核项”

#### 2.1.3 批量处理

真实存在，但当前更偏向本地工具链能力，不是现成的 Appsmith API 能力。

- 入口：
  - CLI `thesis-format-fixer batch-fix`
  - GUI `batch-fix`
- 后端支撑：
  - `run_batch_fix()`
  - 输出 `batch_summary.json`、`batch_summary.md`
  - 每个文件输出 `*.fixed.docx`、`*.report.json`、`*.report.md`、`*.user_summary.md`
- 关键边界：
  - 当前 API 只暴露了单文件 `check/fix`
  - 没有 `POST /api/jobs/batch-fix`
  - 因此 Appsmith 的批量页本轮只能做“预留页 / 本地部署说明页 / 二期扩展页”，不能伪装成已可用的服务端批量能力

#### 2.1.4 报告生成

真实存在，并且是当前最稳定的 UI 消费基础。

- 技术报告：
  - JSON：结构化字段，适合表格、状态判断、绑定
  - Markdown：适合下载和人工查阅
- 用户摘要：
  - `build_user_result_summary()`
  - `render_user_summary_markdown()`
  - 已有分类结果、关键问题、下一步建议、产物列表、技术字段次级展示
- 结论：
  - Appsmith 不应自行再发明一套结果语义，应该直接复用现有三层结果结构

#### 2.1.5 用户摘要展示

真实存在。

- `report_builder.py` 已定义：
  - `overall_status`
  - `key_issues`
  - `next_steps`
  - `category_summaries`
  - `top_actions`
  - `artifacts`
- `gui.py` 已验证三层展示思路：
  - 概览结果
  - 分类结果
  - 技术字段（次级展示）
- 相关测试：
  - `tests/test_task020_gui.py`
  - `tests/test_task023_user_summary.py`

#### 2.1.6 API 可消费能力

真实存在，但范围明确偏小。

- 已有接口：
  - `GET /api/health`
  - `POST /api/jobs/check`
  - `POST /api/jobs/fix`
  - `GET /api/jobs/{job_id}`
  - `GET /api/jobs/{job_id}/download/fixed-docx`
  - `GET /api/jobs/{job_id}/download/report-md`
- 已有 Appsmith 适配层：
  - `src/thesis_format_fixer/api/models.py`
  - 将内部 `user_summary` 压缩为更适合前端消费的 `categorized` / `counts` / `key_issues` / `next_steps`
- 缺失能力：
  - 无批量 job API
  - 无规则列表 API
  - 无历史 job 列表 API
  - 无任务进度轮询状态机（当前更接近同步执行后直接落结果）

### 2.2 当前最适合被 Appsmith 承接的 UI 消费层

当前最适合由 Appsmith 承接的是：

- 以 `src/thesis_format_fixer/api/app.py` 暴露的 HTTP API 作为执行入口
- 以 `src/thesis_format_fixer/api/models.py` 输出的统一 JSON 作为页面状态源
- 以 `report_builder.py` 已定义的三层结果语义作为结果区结构

不建议 Appsmith 直接消费：

- GUI 专用格式化文本 `format_gui_result()`
- CLI 控制台输出
- 本地文件系统路径拼装逻辑本身

原因：

- Appsmith 更适合绑定 API JSON，而不是桌面 GUI 文本
- API 已经把内部结构压成较稳定的前端消费模型
- 这样可以复用现有 runner，又避免在 Appsmith 里重复写一套结果解释逻辑

### 2.3 已有后端支撑 vs 仅概念能力

#### 已有后端支撑

- 单文件检查
- 单文件修复
- 结果查询
- 技术报告下载
- 修复文档下载
- 用户摘要分类展示
- 批量修复本地执行
- 批量汇总文件生成

#### 仅概念或后续实现

- Appsmith 直接可用的批量处理 API
- 规则列表在线浏览 API
- Job 历史记录中心
- 多任务队列与实时进度百分比
- 用户权限、账户体系
- 云端文件持久化和归档管理

## 3. 目标用户与核心任务

### 3.1 目标用户

本项目 UI 的直接用户不是开发者，而是需要处理论文格式的普通使用者。根据现有 GUI 和用户摘要设计，建议按以下角色抽象：

- 学生用户
  - 上传单篇论文
  - 看懂结果
  - 下载修复文档与报告
- 老师/助理
  - 批量处理多个论文文件
  - 查看每篇处理结果
  - 快速识别失败项和需人工复核项
- 技术支持/项目维护者
  - 查看技术报告
  - 根据技术字段排查问题

### 3.2 核心任务

当前最值得在 Appsmith 中支持的核心任务按优先级排序如下：

1. 上传单个 `.docx` 并执行检查
2. 上传单个 `.docx` 并执行修复
3. 阅读用户友好摘要，理解是否需要继续手工处理
4. 查看问题明细并定位优先处理项
5. 下载技术报告和修复后文档
6. 了解规则边界与“为什么没有自动修改”
7. 预留批量处理入口，但不假装已具备完整线上批量后端

## 4. Appsmith 页面总地图

### 4.1 页面建议

本轮建议 Appsmith 应用至少拆成四页：

1. 工作台首页
2. 单文件处理页
3. 批量处理页
4. 规则/帮助说明页

### 4.2 页面去留结论

#### 工作台首页

保留。

理由：

- 现有能力分为单文件主链路与批量预留链路，首页适合作为入口分流
- 可以先解释当前真实能力边界，避免用户误解“所有页面都已可执行”

#### 单文件处理页

保留，且应作为 MVP 主页面。

理由：

- 当前 API 已完整支撑
- 与现有 Appsmith API Spec 完全一致
- 最容易形成稳定闭环

#### 批量处理页

保留，但页面定位需要调整。

建议定位：

- 当前阶段作为“批量能力说明 + 本地批量能力承接页 + 二期预留页”
- 若后续新增批量 API，再升级为真实执行页

理由：

- `run_batch_fix()` 确实存在，不能假装没有
- 但 API 未开放，不能在 Appsmith 中宣称“在线批量处理已可用”

#### 规则/帮助说明页

保留。

理由：

- 规则边界、自动修改/仅检查/人工复核三层语义是本工具的核心认知门槛
- 可以显著减少结果页中的解释负担

### 4.3 页面关系

建议关系如下：

- 首页负责理解系统和选择入口
- 单文件处理页负责执行主链路
- 批量处理页负责说明现状和二期承接点
- 规则/帮助页负责解释规则边界、结果语义和常见问题

## 5. 各页面信息架构

### 5.1 工作台首页

#### 页面目标

- 让用户快速理解“当前能做什么、不能做什么”
- 给出单文件处理主入口
- 明确批量能力现状

#### 主要区块

- 顶部应用标题区
- 当前能力说明区
- 主入口卡片区
- 结果结构说明区
- 风险与边界提示区

#### 主按钮

- 进入单文件处理

#### 次按钮

- 查看批量处理说明
- 查看规则/帮助

#### 输入数据

- 无强依赖输入
- 可选读取健康检查接口 `GET /api/health` 作为系统可用性提示

#### 输出数据

- 页面导航动作
- 系统可用状态

#### 空状态

- 默认首页即为空状态
- 展示“请选择处理方式”

#### 执行中状态

- 首页无长执行
- 若做健康检查，可展示“正在检查服务状态”

#### 失败状态

- API 不可用时展示“服务未连接，仅可查看说明，暂不可执行单文件处理”

#### 成功状态

- 显示服务在线
- 强调推荐入口为“单文件处理”

#### 页面结构建议

1. 顶部概览卡
   - 应说明本工具处理对象为 `.docx`
   - 应说明主流程是“上传单文件 -> 执行 check/fix -> 查看三层结果”
2. 能力卡片区
   - 单文件检查：已可用
   - 单文件修复：已可用
   - 批量处理：预留 / 后续增强
3. 三层结果说明区
   - 用户友好摘要
   - 问题明细表
   - 技术报告/原始报告
4. 风险提示区
   - 修复不等于全部自动完成
   - 仍可能存在未自动修改项与人工复核项

### 5.2 单文件处理页

#### 页面目标

- 承接现有 API 的最小闭环
- 让普通用户完成一次单文件检查或修复
- 以三层结果结构展示输出

#### 主要区块

- 模式选择区
- 文件上传区
- 执行控制区
- 执行结果总览区
- 问题明细区
- 产物下载区
- 技术报告区

#### 主按钮

- 开始检查
- 开始修复

建议交互：

- 模式选择为 `check` / `fix`
- 主按钮文案随模式变化

#### 次按钮

- 重置
- 刷新结果
- 下载修复文档
- 下载技术报告
- 查看帮助

#### 输入数据

- 上传文件：单个 `.docx`
- 处理模式：`check` 或 `fix`

#### 输出数据

- `job_id`
- `status`
- `summary`
- `user_summary`
- `artifacts`
- `error`

#### 空状态

- 未上传文件时不显示结果区主体
- 展示引导文案：
  - 仅支持单个 `.docx`
  - 先选择模式，再上传文件并执行

#### 执行中状态

- 禁用重复提交
- 禁用模式切换和文件重新上传
- 展示“正在处理，请稍候”
- 保留当前 `job_id` 显示位，便于后续排障

#### 失败状态

- 顶部显示中文错误摘要
- 保留技术错误信息折叠区
- 下载区只保留可用产物
- 问题明细区隐藏或显示空表

#### 成功状态

- 顶部先显示用户友好摘要
- 中部显示问题明细表
- 底部显示技术报告与下载入口

#### 页面结构建议

1. 模式与输入区
   - 模式切换：检查 / 修复
   - 文件上传组件
   - 主执行按钮
   - 重置按钮
2. 结果总览区
   - 总体状态 `overall_status`
   - 三个核心计数
     - 已自动处理
     - 发现但未自动修改
     - 需人工复核
   - 关键问题 `key_issues`
   - 建议下一步 `next_steps`
3. 问题明细区
   - Tab 或分段表格
   - 分为三组：
     - 已自动处理
     - 发现但未自动修改
     - 需人工复核
4. 产物区
   - 用户摘要文件
   - 技术报告 Markdown
   - 修复后文档（仅 fix 成功可见）
5. 技术报告区
   - 展示技术字段摘要
   - 提供原始报告下载入口

### 5.3 批量处理页

#### 页面目标

- 明确说明仓内已有批量本地能力，但当前 Appsmith API 未对外暴露
- 为后续批量 API 与批量 UI 预留结构
- 在不造成功能误导的前提下，先定义未来页面框架

#### 主要区块

- 当前能力说明区
- 批量流程说明区
- 未来页面结构预留区
- 批量结果结构样例区

#### 主按钮

- 查看本地批量流程说明

#### 次按钮

- 返回单文件处理
- 查看规则/帮助

#### 输入数据

- 本轮无真实在线输入
- 后续预留：
  - 目录选择 / 多文件上传
  - 是否递归 `recursive`

#### 输出数据

- 本轮无真实在线执行输出
- 后续预留：
  - `batch_summary.json`
  - 每文件处理结果列表

#### 空状态

- 默认展示“当前线上 Appsmith 未接入批量 API”

#### 执行中状态

- 本轮无
- 后续预留为批量队列状态

#### 失败状态

- 本轮无真实执行失败态
- 后续预留为“部分成功 / 部分失败”

#### 成功状态

- 本轮无真实执行成功态
- 可展示未来结果布局样例

#### 页面结构建议

1. 现状说明卡
   - 本地工具链已有 `run_batch_fix()`
   - 当前 HTTP API 未提供批量接口
2. 后续执行框架示意
   - 批量输入区
   - 批量任务列表区
   - 批量汇总区
   - 单文件结果钻取区
3. 批量结果字段预留
   - `total_files`
   - `succeeded`
   - `failed`
   - `items[]`
4. 风险提示
   - 标注“预留 / 后续实现”

### 5.4 规则/帮助说明页

#### 页面目标

- 解释结果为什么分层
- 解释为什么有些问题不自动修改
- 帮助用户理解 A/B/C 规则边界

#### 主要区块

- 规则边界总览区
- 三类处理结果说明区
- 常见问题区
- 报告阅读说明区

#### 主按钮

- 返回单文件处理

#### 次按钮

- 下载技术报告示例说明
- 返回首页

#### 输入数据

- 静态文档信息
- 可选引用规则文档摘要

#### 输出数据

- 帮助信息展示

#### 空状态

- 页面本身无空状态

#### 执行中状态

- 无

#### 失败状态

- 若未来绑定动态文档接口失败，则回退到内置帮助文本

#### 成功状态

- 成功展示规则边界与阅读指引

#### 页面结构建议

1. 规则边界区
   - A 类：自动修改
   - B 类：自动检查，不直改
   - C 类：人工复核
2. 结果阅读区
   - 用户友好摘要看什么
   - 问题明细表看什么
   - 技术报告什么时候看
3. 常见问题区
   - 为什么 fix 后还有人工复核项
   - 为什么某些条目只提示不修改
4. 规则来源区
   - 标明当前规则来自 `FORMAT_RULEBOOK_v3`

## 6. 各页面关键组件建议

### 6.1 工作台首页

- `Text` / `RichText`
  - 用于系统说明、边界说明
- `Container`
  - 组织能力卡片
- `Button`
  - 页面跳转
- 可选 `Alert`
  - 显示 API 健康状态

### 6.2 单文件处理页

- `Tabs` 或 `Button Group`
  - 切换 `check` / `fix`
- `FilePicker`
  - 上传 `.docx`
- `Button`
  - 执行、重置、刷新、下载
- `Text`
  - 显示总体状态与关键计数
- `List`
  - 展示 `key_issues`、`next_steps`
- `Table`
  - 展示问题明细
- `Collapse` / `Tabs`
  - 分隔三层结果和技术字段
- `Link` / 下载按钮
  - 产物下载

### 6.3 批量处理页

- `Text` / `RichText`
  - 当前能力说明
- `Container`
  - 展示未来批量流程框架
- `Table`
  - 演示批量汇总结构
- `Badge`
  - 标注“预留”“后续实现”

### 6.4 规则/帮助说明页

- `RichText`
  - 承载说明文案
- `Collapse`
  - 常见问题折叠
- `Tabs`
  - A/B/C 规则分类

### 6.5 组件设计建议与理由

- 不建议把所有结果塞进一个 `TextArea`
  - 原因：现有 `user_summary`、`categorized`、`artifacts` 已经是结构化数据
- 不建议首页直接做上传执行
  - 原因：首页职责应是分流与说明，避免首页过重
- 建议单文件页以“执行区 + 总览区 + 明细区 + 下载区”四段式组织
  - 原因：与现有 GUI 和 `report_builder` 三层结果一致

## 7. 关键状态流转设计

### 7.1 单文件主状态机

建议单文件处理页的状态机如下：

1. 初始态
   - 未上传文件
   - 主按钮禁用
2. 可执行态
   - 已选模式
   - 已上传合法 `.docx`
   - 主按钮可用
3. 提交中
   - 调用 `POST /api/jobs/check` 或 `POST /api/jobs/fix`
4. 结果加载中
   - 调用 `GET /api/jobs/{job_id}`
5. 成功态
   - `status=completed`
   - 展示三层结果
6. 失败态
   - `status=failed` 或接口异常
   - 展示用户可理解错误和技术错误

### 7.2 页面级状态字段建议

建议前端至少维护以下状态：

- `pageMode`
  - `check` / `fix`
- `selectedFile`
- `jobId`
- `jobStatus`
  - `idle` / `submitting` / `loading` / `completed` / `failed`
- `jobResult`
- `errorMessage`

### 7.3 关键状态约束

- 未选择文件时，执行按钮禁用
- 执行中时，不允许重复提交
- 成功后先渲染 `user_summary`
- 技术字段默认折叠或降级展示
- 下载按钮仅在对应产物存在时显示

### 7.4 批量页状态约束

本轮只定义，不落地执行状态机。

建议未来状态机：

- `idle`
- `preparing`
- `running`
- `partial_success`
- `completed`
- `failed`

当前页面应明确标注为“预留 / 后续实现”。

## 8. 结果展示分层设计

### 8.1 总原则

结果展示必须明确分三层，不能混为一个文本框：

1. 用户友好摘要
2. 问题明细表
3. 技术报告 / 原始报告

### 8.2 第一层：用户友好摘要

#### 目标

让非技术用户先判断：

- 本次处理是否完成
- 是否还需要自己处理
- 优先处理什么

#### 数据来源

- `user_summary.overall_status`
- `user_summary.counts`
- `user_summary.key_issues`
- `user_summary.next_steps`

#### 展示建议

- 顶部状态卡
- 三个核心统计卡
- 关键问题列表
- 下一步建议列表

#### 理由

- 现有 `report_builder.py` 已经专门为这一层做了抽象
- 应优先复用，而不是让 Appsmith 重新从技术字段拼句子

### 8.3 第二层：问题明细表

#### 目标

让用户看到“具体是什么问题、属于哪一类、建议怎么处理”。

#### 数据来源

- `user_summary.categorized.auto_processed`
- `user_summary.categorized.detected_not_auto_fixed`
- `user_summary.categorized.manual_review_required`

若直接对接 runner 原始 payload，则对应：

- `auto_fixed_items`
- `detected_but_not_fixed_items`
- `manual_review_items`

#### 表格建议字段

- 问题标题
- 问题说明
- 处理状态
- 原因分类
- 建议下一步
- 规则编号

#### 分组建议

- 用 Tab 或分节卡片分开三类问题
- 默认优先打开“发现但未自动修改”或“需人工复核”

#### 理由

- 现有 API 模型已经把三类结果拆开
- 普通用户不需要先看技术字段，而是先知道哪些问题属于自己接下来要处理的事项

### 8.4 第三层：技术报告 / 原始报告

#### 目标

为技术支持、人工排查、精确定位提供次级信息。

#### 数据来源

- `summary`
- `artifacts.report_json`
- `artifacts.report_md`
- `artifacts.download_report_md_url`

#### 展示建议

- 折叠区或“技术详情”二级 Tab
- 显示技术字段摘要：
  - `auto_fix_rule_count`
  - `detected_not_auto_modified_count`
  - `manual_review_required_count`
  - `reference_finding_count`
  - `reference_blocking_count`
  - `block_low_confidence_count`
- 提供原始 Markdown 报告下载按钮

#### 理由

- 与现有 GUI 的“技术字段（次级展示）”保持一致
- 避免技术细节压过普通用户摘要

## 9. MVP 范围

### 9.1 本轮建议纳入 MVP 的页面与能力

- 工作台首页
- 单文件处理页
- 规则/帮助说明页

### 9.2 本轮建议纳入 MVP 的后端绑定

- `GET /api/health`
- `POST /api/jobs/check`
- `POST /api/jobs/fix`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/download/report-md`
- `GET /api/jobs/{job_id}/download/fixed-docx`

### 9.3 本轮不纳入 MVP

- 在线批量执行
- 历史任务中心
- 规则在线检索页
- 高级技术配置（review_mode / model 选择等）

### 9.4 MVP 页面重点

MVP 应聚焦一条主链路：

- 用户上传单个 `.docx`
- 选择检查或修复
- 执行
- 查看三层结果
- 下载产物

## 10. 后续增强范围

以下内容建议放入后续任务，而不是本轮 IA 收口阶段：

- 新增批量 HTTP API，并让批量页转为真实执行页
- 引入 job 历史列表和结果回看
- 支持更细颗粒度的技术报告在线浏览
- 支持规则分组浏览
- 支持服务端持久化和文件保留策略

需要明确标注为“后续实现”的点：

- 批量在线处理
- 实时进度百分比
- 历史任务管理
- 用户账户与权限

## 11. 与现有 runner / report / API 的映射关系

### 11.1 单文件执行映射

| UI 动作 | API | Service / Runner | 产物 |
| --- | --- | --- | --- |
| 开始检查 | `POST /api/jobs/check` | `ApiJobService.create_job(mode="check")` -> `run_check_with_details()` | `report.json` / `report.md` / `check.user_summary.md` |
| 开始修复 | `POST /api/jobs/fix` | `ApiJobService.create_job(mode="fix")` -> `run_fix_with_details()` | `fixed.docx` / `report.json` / `report.md` / `fix.user_summary.md` |
| 读取结果 | `GET /api/jobs/{job_id}` | 读取 `job.json` | 统一 JSON |
| 下载技术报告 | `GET /api/jobs/{job_id}/download/report-md` | `get_download_path()` | Markdown 报告 |
| 下载修复文档 | `GET /api/jobs/{job_id}/download/fixed-docx` | `get_download_path()` | 修复后 docx |

### 11.2 结果层映射

| UI 层级 | 现有数据源 | 说明 |
| --- | --- | --- |
| 用户友好摘要 | `user_summary.overall_status` / `counts` / `key_issues` / `next_steps` | 直接给普通用户阅读 |
| 问题明细表 | `user_summary.categorized.*` | 按三类问题分组展示 |
| 技术报告 / 原始报告 | `summary` + `artifacts.report_md/report_json` | 次级展示，用于排障与精查 |

### 11.3 规则语义映射

| 规则边界 | 规则文档依据 | UI 呈现建议 |
| --- | --- | --- |
| A 类自动修改 | `FORMAT_RULEBOOK_v2/v3` | 展示为“已自动处理” |
| B 类自动检查，不直改 | `FORMAT_RULEBOOK_v2/v3` | 展示为“发现但未自动修改” |
| C 类人工复核 | `FORMAT_RULEBOOK_v2/v3` | 展示为“需人工复核” |

### 11.4 批量能力映射

| UI 规划 | 现有代码 | 当前结论 |
| --- | --- | --- |
| 批量处理页 | `run_batch_fix()` / GUI `batch-fix` | 已有本地能力 |
| Appsmith 在线批量执行 | 无对应 API | 预留 / 后续实现 |

## 12. 风险与边界

### 12.1 不能误导用户的点

- 不能把 `fix` 宣传为“所有问题都被自动修好”
- 不能把批量页写成“当前已可线上执行”
- 不能把技术报告替代用户摘要
- 不能把规则边界隐藏掉，否则用户会误解“为什么系统不改”

### 12.2 IA 设计风险

- 如果首页直接执行上传，会让页面职责混乱
- 如果单文件页不做三层分层，会重复出现 GUI 早期“技术字段堆叠”的问题
- 如果批量页不明确标注预留，会造成验收口径失真

### 12.3 后端边界风险

- API 目前是最小链路，不包含批量与历史记录
- 批量结果虽有本地 JSON/MD 汇总，但未标准化为在线接口
- 用户摘要已较稳定，但 Appsmith 仍应优先消费 API 适配后的字段，而不是自行拼装内部 payload

### 12.4 工程结论

当前 Appsmith 最合理的承接策略不是“把所有已存在功能全部铺成页面”，而是：

1. 先把单文件主链路做扎实
2. 严格复用三层结果结构
3. 把批量页作为明确标注边界的预留页
4. 把规则/帮助页作为解释层，减少结果页负担

这条路径与仓内现有 runner、report、API 的成熟度最匹配，改动最小，风险最低。
