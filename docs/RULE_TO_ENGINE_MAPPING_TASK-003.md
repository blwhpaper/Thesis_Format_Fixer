# RULE_TO_ENGINE_MAPPING_TASK-003

## 1. 说明

- 基线文件：`rules/FORMAT_RULEBOOK_v2.md`（唯一实现基线）。
- 目标：把冻结规则逐条映射到 V1 可执行决策。
- `v1_decision` 四类：`Auto Fix` / `Auto Check` / `Report Only` / `Out of V1`。
- 约束：B/C 类不进入自动修复；高风险项保持保守边界。

## 2. 规则映射总表

| rule_id | rule_name | source_section | target_block | detection_method | fixability | risk_level | required_docx_capability | v1_decision |
|---|---|---|---|---|---|---|---|---|
| FR-4.1-01 | 中文封皮使用专用封皮 | 4.1 | cover.cn | 封皮关键字段存在性匹配（标题/院系/专业等） | no-fix | high | 首页段落提取、关键词匹配 | Auto Check |
| FR-4.1-02 | 英文封皮存在且为A4打印范围 | 4.1 | cover.en | 英文封皮页块存在性与页设置读取 | no-fix | high | 页面尺寸读取、页面块定位 | Report Only |
| FR-4.1-03 | 封皮字段存在性可检查 | 4.1 | cover.cn+cover.en | 固定字段词典匹配 | no-fix | medium | 段落文本提取 | Auto Check |
| FR-4.1-04 | 封皮模板重建不自动修改 | 4.1/5.3 | cover.layout | 仅输出禁止自动修复标记 | unfixable | high | 无（策略规则） | Out of V1 |
| FR-4.1-05 | PDF细粒度版式需人工核对 | 4.1 | cover.layout | 不做机器判定，仅给人工复核提示 | unfixable | high | 无（策略规则） | Out of V1 |
| FR-4.2-01 | 中文摘要标题文本为“摘 要” | 4.2 | abstract.cn.title | 标题锚点精确匹配 | fixable | low | 段落文本读写 | Auto Fix |
| FR-4.2-02 | 中文摘要标题样式规范 | 4.2 | abstract.cn.title | 标题样式属性比对 | fixable | low | 段落样式读写（字体/字号/加粗/对齐/段前后/行距） | Auto Fix |
| FR-4.2-03 | 中文摘要正文样式规范 | 4.2 | abstract.cn.body | 摘要块内段落样式比对 | fixable | low | 运行字体与段落格式读写 | Auto Fix |
| FR-4.3-01 | 中文关键词样式规范 | 4.3 | abstract.cn.keywords | 关键词行识别+样式比对 | fixable | low | 段落文本与样式读写 | Auto Fix |
| FR-4.3-02 | 中文关键词分号分隔 | 4.3 | abstract.cn.keywords | 分隔符规则校验 | no-fix | low | 文本解析 | Auto Check |
| FR-4.3-03 | 中文关键词数量不少于5 | 4.3 | abstract.cn.keywords | 分号切分后计数 | no-fix | low | 文本解析 | Auto Check |
| FR-4.4-01 | 英文摘要标题文本为Abstract | 4.4 | abstract.en.title | 标题锚点精确匹配 | fixable | low | 段落文本读写 | Auto Fix |
| FR-4.4-02 | 英文摘要标题样式规范 | 4.4 | abstract.en.title | 样式属性比对 | fixable | low | 段落样式读写 | Auto Fix |
| FR-4.4-03 | 英文摘要正文样式规范 | 4.4 | abstract.en.body | 摘要块内段落样式比对 | fixable | low | 运行字体与段落格式读写 | Auto Fix |
| FR-4.5-01 | 英文关键词标题样式规范 | 4.5 | abstract.en.keywords_label | 关键词标签行样式比对 | fixable | low | 段落样式读写 | Auto Fix |
| FR-4.5-02 | 英文关键词内容样式规范 | 4.5 | abstract.en.keywords | 内容样式比对 | fixable | low | 段落样式读写 | Auto Fix |
| FR-4.5-03 | 英文关键词首字母大写 | 4.5 | abstract.en.keywords | 词级大小写规则校验 | no-fix | medium | 文本分词与大小写检测 | Auto Check |
| FR-4.5-04 | 英文关键词半角分号分隔 | 4.5 | abstract.en.keywords | 分隔符规则校验 | no-fix | low | 文本解析 | Auto Check |
| FR-4.5-05 | 英文关键词词内空格规范 | 4.5 | abstract.en.keywords | 多空格/首尾空格检测 | no-fix | low | 文本解析 | Auto Check |
| FR-4.6-01 | 目录标题CONTENTS样式 | 4.6 | toc.title | 标题锚点与样式比对 | fixable | low | 段落文本与样式读写 | Auto Fix |
| FR-4.6-02 | 目录内容样式（TNR小四25磅） | 4.6 | toc.entries | 目录区域样式比对 | conditional-fix | medium | TOC区域识别、段落样式写入 | Report Only |
| FR-4.6-03 | 目录为自动目录 | 4.6 | toc.field | 目录域代码存在性检测 | no-fix | high | 字段代码读取（TOC field） | Auto Check |
| FR-4.6-04 | 目录页码不带“-” | 4.6 | toc.entries | 目录行尾页码模式检测 | no-fix | medium | 目录文本解析 | Auto Check |
| FR-4.6-05 | 点线为居中引导线 | 4.6 | toc.tab_leader | 制表位引导符检测 | no-fix | medium | 段落制表位属性读取 | Report Only |
| FR-4.6-06 | 目录标题与正文标题一致 | 4.6 | toc.entries vs body.headings | 目录条目与标题集合比对 | no-fix | high | TOC提取+标题提取+归一化匹配 | Report Only |
| FR-4.6-07 | 目录至少到二级层次 | 4.6 | toc.entries | TOC层级深度检测 | no-fix | medium | TOC层级读取 | Auto Check |
| FR-4.7-01 | 正文主标题样式规范 | 4.7 | body.main_title | 候选主标题定位+样式比对 | conditional-fix | medium | 主标题定位、段落样式读写 | Report Only |
| FR-4.7-02 | 正文副标题样式规范 | 4.7 | body.sub_title | 候选副标题定位+样式比对 | conditional-fix | medium | 副标题定位、段落样式读写 | Report Only |
| FR-4.8-01 | 标题序号层级1/1.1/1.1.1 | 4.8 | body.headings | 正则+上下文层级一致性检查 | no-fix | high | 标题检测、层级解析 | Auto Check |
| FR-4.8-02 | 序号前四英文字符缩进 | 4.8 | body.headings | 前导空白/缩进量检测 | no-fix | medium | 段落缩进读取、文本前缀解析 | Auto Check |
| FR-4.8-03 | 一级标题样式规范 | 4.8 | body.h1 | 已识别h1样式比对 | conditional-fix | medium | 标题层级定位+样式读写 | Report Only |
| FR-4.8-04 | 二三级标题样式规范 | 4.8 | body.h2_h3 | 已识别h2/h3样式比对 | conditional-fix | medium | 标题层级定位+样式读写 | Report Only |
| FR-4.8-05 | 各级标题行距25磅 | 4.8 | body.headings | 标题段落行距检测 | conditional-fix | medium | 标题定位+段落格式读写 | Report Only |
| FR-4.9-01 | 正文普通段落样式规范 | 4.9 | body.paragraphs | 正文段落范围识别+样式比对 | conditional-fix | medium | 正文块定位、段落样式读写 | Report Only |
| FR-4.10-01 | 采用页脚脚注（非尾注） | 4.10 | footnotes.type | 脚注/尾注对象类型检查 | no-fix | medium | 注释对象读取 | Auto Check |
| FR-4.10-02 | 中文脚注字体字号规范 | 4.10 | footnotes.cn | 脚注run样式检测 | conditional-fix | medium | 脚注对象读写、语言判别 | Report Only |
| FR-4.10-03 | 英文脚注字体字号规范 | 4.10 | footnotes.en | 脚注run样式检测 | conditional-fix | medium | 脚注对象读写、语言判别 | Report Only |
| FR-4.10-04 | 脚注单倍行距 | 4.10 | footnotes.all | 段落行距检测 | conditional-fix | medium | 脚注段落格式读写 | Report Only |
| FR-4.10-05 | 脚注按页重编编号 | 4.10/5.3 | footnotes.numbering | 分页+编号重置策略检测/修复均高风险 | unfixable | high | 分页感知、锚点重排 | Out of V1 |
| FR-4.11-01 | 参考文献标题REFERENCES样式 | 4.11 | bibliography.title | 标题锚点与样式比对 | fixable | low | 段落文本与样式读写 | Auto Fix |
| FR-4.11-02 | 参考文献条目基础字体字号行距 | 4.11 | bibliography.entries | 参考文献块内样式比对 | conditional-fix | medium | 参考文献块定位、段落样式读写 | Report Only |
| FR-4.11-03 | 条目基础结构遵循原始示例 | 4.11 | bibliography.entries | 模板模式匹配（期刊/专著/论文/报告） | no-fix | high | 文本结构解析 | Auto Check |
| FR-4.11-04 | 参考文献语言分组符合性 | 5.2 | bibliography.entries | 语言识别+分组次序检查 | no-fix | high | 语言识别、条目分组 | Report Only |
| FR-4.11-05 | 参考文献近三年符合性 | 5.2 | bibliography.entries | 年份提取与阈值检查 | no-fix | high | 年份抽取 | Report Only |
| FR-4.11-06 | 参考文献发表顺序符合性 | 5.2 | bibliography.entries | 条目顺序与年份/编号一致性检查 | no-fix | high | 条目排序规则解析 | Report Only |
| FR-4.12-01 | 致谢标题“致谢”样式规范 | 4.12 | ack.title | 标题锚点+样式比对 | fixable | low | 段落文本与样式读写 | Auto Fix |
| FR-4.12-02 | 致谢正文样式规范 | 4.12 | ack.body | 致谢块内样式比对 | fixable | low | 段落样式读写 | Auto Fix |
| FR-4.12-03 | 仅要求中文致谢 | 4.12 | ack.section | 中文致谢区块存在性检查 | no-fix | low | 段落标题定位 | Auto Check |
| FR-4.13-01 | A4双面打印 | 4.13 | page.setup | 页面尺寸+双面相关设置读取 | no-fix | medium | section page setup读取 | Auto Check |
| FR-4.13-02 | 页边距上/下/左/右固定值 | 4.13 | page.margins | section margins 比对 | conditional-fix | medium | section属性读写 | Report Only |
| FR-4.13-03 | 不对称页边距检查保留 | 4.13 | page.mirror_margins | mirror margins相关属性检查 | no-fix | high | section镜像边距属性读取 | Auto Check |
| FR-4.14-01 | 页眉距顶2cm+五号TNR居中 | 4.14 | header.style | header段落样式+距离检测 | conditional-fix | high | header/footer对象读写、分节遍历 | Report Only |
| FR-4.14-02 | 页脚距底1.75cm+五号TNR居中 | 4.14 | footer.style | footer段落样式+距离检测 | conditional-fix | high | header/footer对象读写、分节遍历 | Report Only |
| FR-4.14-03 | 奇偶页不同 | 4.14/5.2 | section.odd_even | odd/even header-footer flag检测 | no-fix | high | 文档设置读取 | Auto Check |
| FR-4.15-01 | 页码从正文开始 | 4.15/5.2 | page.numbering.start | 正文起始分节与页码起点检查 | no-fix | high | section链接+页码域分析 | Report Only |
| FR-4.15-02 | 页码字体五号TNR居中 | 4.15 | footer.page_num_style | 页码run样式检测 | no-fix | high | 页码域run定位 | Report Only |
| FR-4.15-03 | 页码格式为-1- | 4.15/5.2 | footer.page_num_format | 页码显示格式检测 | no-fix | high | 页码域格式解析 | Auto Check |
| FR-4.15-04 | 起始分节与页码联动高风险 | 4.15/5.3 | section.numbering_linkage | 仅输出禁止自动修复标记 | unfixable | high | 分节与域重构能力 | Out of V1 |
| FR-4.16-01 | 装订顺序符合要求 | 4.16/5.2 | global.order | 章节标题序列比对 | no-fix | high | 全文块序列定位 | Report Only |
| FR-4.16-02 | 装订线在左侧 | 4.16 | binding.gutter | 装订线/装订边属性检查 | no-fix | high | section gutter属性读取 | Report Only |
| FR-4.16-03 | 装订线处理仅检查不重排 | 4.16/5.3 | binding.layout | 仅输出禁止自动修复标记 | unfixable | high | 无（策略规则） | Out of V1 |

## 3. 统计汇总（按 v1_decision）

- Auto Fix：13 条
- Auto Check：19 条
- Report Only：24 条
- Out of V1：5 条
- 合计：61 条

## 4. A 类但 V1 暂不自动修复的条目

以下条目在 `FORMAT_RULEBOOK_v2` 中属于 A（自动修改）口径，但出于 V1 最小可控范围收紧，降为 `Report Only`：

- FR-4.6-02（目录内容样式）
- FR-4.7-01、FR-4.7-02（主标题/副标题样式）
- FR-4.8-03、FR-4.8-04、FR-4.8-05（各级标题样式与行距）
- FR-4.9-01（正文普通段落样式）
- FR-4.10-02、FR-4.10-03、FR-4.10-04（脚注基础样式）
- FR-4.11-02（参考文献条目基础样式）
- FR-4.13-02（常规页边距写回）
- FR-4.14-01、FR-4.14-02（页眉页脚基础样式）

统一原因：需要先具备高置信度块定位、分节稳定遍历与复杂对象写回保护；在 V1 先做检测与报告，避免误改全篇结构。

## 5. TASK-017 最小补丁映射（基于 v3 增补）

| rule_id | rule_name | source_section | target_block | detection_method | fixability | risk_level | required_docx_capability | v1_decision |
|---|---|---|---|---|---|---|---|---|
| FR-4.5-06 | 英文内容禁用中文书名号《》 | 4.5 | english.text | 英文段落中扫描《》并过滤中文上下文 | no-fix | medium | 段落文本提取与字符集判断 | Auto Check |
| FR-4.11-07 | D类参考文献不得包含页码 | 4.11 | bibliography.entries | 识别 `[D]` 条目后校验页码字段 | fixable | low | 参考文献条目识别与文本回写 | Auto Fix |

补丁说明：
- FR-4.5-06 属于项目补充决议，默认仅审查不自动改写。
- FR-4.11-07 为项目决议覆盖口径，不宣称学校原文逐字条款；在 `fix` 链路按安全条件执行页码移除。
