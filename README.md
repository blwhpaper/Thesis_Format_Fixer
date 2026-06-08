# thesis-format-fixer

可配置的 DOCX thesis formatting checker and safe fixer。

本项目定位为通用工程框架：通过 profile 配置约束检查与安全修复边界，不绑定任何具体高校，不声称适用于所有大学。

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## CLI

```bash
thesis-format-fixer --help

# Check
thesis-format-fixer check samples/input/demo.docx \
  --report-json samples/output/demo.check.report.json \
  --report-md samples/output/demo.check.report.md

# Check with explicit profile (for profile_drift audit)
thesis-format-fixer check samples/input/demo.docx \
  --profile rules/profiles/generic_university_zh.yaml \
  --report-json samples/output/demo.check.report.json

# Safe fix to a new file (never overwrite input)
thesis-format-fixer fix samples/input/demo.docx \
  --out samples/output/demo.fixed.docx

# Batch fix (recursive by default)
thesis-format-fixer batch-fix samples/input \
  --out-dir samples/output/batch
```

## GUI

```bash
python -m thesis_format_fixer.gui
```

## Sample Profiles

- Default profile: `rules/profiles/generic_university_zh.yaml`
- Sample institution profile: `rules/profiles/sample_institution_zh.yaml`

说明：以上 profile 仅为示例模板。请在私有环境按本机构规范定制，不要将真实政策文件、真实学生论文或个人信息直接公开到仓库。

## Profile Customization

可按需调整：

- 标题/章节命名与词典
- 参考文献格式约束
- A/B/C 分级执行策略
- 报告提示文案与人工复核口径

建议流程：复制 sample profile，重命名后逐项替换规则字段并配套回归测试。

当前已提供最小 `Generic Format Profile Engine` 骨架（profile 加载、`generic < institution < overrides` 合成、rule key 校验、rulebook/runtime 漂移检查）。

## Safe Fix Boundary

- A 类：低风险自动修复
- B 类：检测并报告，不自动改写关键结构
- C 类：人工复核，不自动改写
- `fix` 输出到新文件，不覆盖输入 `.docx`
- 保留 manual/fallback/error boundary

## Out of Scope

当前不包含：

- 封皮模板精细重建
- 自动目录域重建
- 正文分节页码系统重构
- 脚注按页重编
- 复杂语义级参考文献重排/纠错
- Word 批注/Review 模式的完整 CLI 集成（当前仅作为底层引擎就绪）

## Contributor / Agent Protocol

Read governance in this order before modifying the repository:

1. [`AGENTS.md`](AGENTS.md)
2. [`CLAUDE.md`](CLAUDE.md)
3. [`docs/roadmap.md`](docs/roadmap.md)
4. `docs/governance/TASK_STATE.md`
5. `docs/governance/TASK_INDEX.md`

Historical governance audits remain for provenance, but the files above are the runtime truth for task startup and handoff.

## License

MIT，见 `LICENSE`。

## Maintainer Status

- 当前状态：维护中（best-effort）
- 不承诺对所有学校规范开箱即用
- 欢迎通过 issue/PR 提供可复现样例与最小测试
