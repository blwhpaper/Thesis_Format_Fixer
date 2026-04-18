"""Rule registry built from RULE_TO_ENGINE_MAPPING_TASK-003.md."""

from __future__ import annotations

from collections.abc import Iterable

from thesis_format_fixer.contracts.rule_types import RuleBinding, RuleDecision, RuleMetadata

SOURCE_OF_TRUTH = "docs/RULE_TO_ENGINE_MAPPING_TASK-003.md"

RULE_NAME_BY_ID: dict[str, str] = {
    "FR-4.1-01": "中文封皮使用专用封皮",
    "FR-4.1-02": "英文封皮存在且为A4打印范围",
    "FR-4.1-03": "封皮字段存在性可检查",
    "FR-4.1-04": "封皮模板重建不自动修改",
    "FR-4.1-05": "PDF细粒度版式需人工核对",
    "FR-4.2-01": "中文摘要标题文本为摘 要",
    "FR-4.2-02": "中文摘要标题样式规范",
    "FR-4.2-03": "中文摘要正文样式规范",
    "FR-4.3-01": "中文关键词样式规范",
    "FR-4.3-02": "中文关键词分号分隔",
    "FR-4.3-03": "中文关键词数量不少于5",
    "FR-4.4-01": "英文摘要标题文本为Abstract",
    "FR-4.4-02": "英文摘要标题样式规范",
    "FR-4.4-03": "英文摘要正文样式规范",
    "FR-4.5-01": "英文关键词标题样式规范",
    "FR-4.5-02": "英文关键词内容样式规范",
    "FR-4.5-03": "英文关键词首字母大写",
    "FR-4.5-04": "英文关键词半角分号分隔",
    "FR-4.5-05": "英文关键词词内空格规范",
    "FR-4.6-01": "目录标题CONTENTS样式",
    "FR-4.6-02": "目录内容样式",
    "FR-4.6-03": "目录为自动目录",
    "FR-4.6-04": "目录页码不带-",
    "FR-4.6-05": "点线为居中引导线",
    "FR-4.6-06": "目录标题与正文标题一致",
    "FR-4.6-07": "目录至少到二级层次",
    "FR-4.7-01": "正文主标题样式规范",
    "FR-4.7-02": "正文副标题样式规范",
    "FR-4.8-01": "标题序号层级1/1.1/1.1.1",
    "FR-4.8-02": "序号前四英文字符缩进",
    "FR-4.8-03": "一级标题样式规范",
    "FR-4.8-04": "二三级标题样式规范",
    "FR-4.8-05": "各级标题行距25磅",
    "FR-4.9-01": "正文普通段落样式规范",
    "FR-4.10-01": "采用页脚脚注",
    "FR-4.10-02": "中文脚注字体字号规范",
    "FR-4.10-03": "英文脚注字体字号规范",
    "FR-4.10-04": "脚注单倍行距",
    "FR-4.10-05": "脚注按页重编编号",
    "FR-4.11-01": "参考文献标题REFERENCES样式",
    "FR-4.11-02": "参考文献条目基础字体字号行距",
    "FR-4.11-03": "条目基础结构遵循原始示例",
    "FR-4.11-04": "参考文献语言分组符合性",
    "FR-4.11-05": "参考文献近三年符合性",
    "FR-4.11-06": "参考文献发表顺序符合性",
    "FR-4.12-01": "致谢标题样式规范",
    "FR-4.12-02": "致谢正文样式规范",
    "FR-4.12-03": "仅要求中文致谢",
    "FR-4.13-01": "A4双面打印",
    "FR-4.13-02": "页边距上/下/左/右固定值",
    "FR-4.13-03": "不对称页边距检查保留",
    "FR-4.14-01": "页眉距顶2cm样式",
    "FR-4.14-02": "页脚距底1.75cm样式",
    "FR-4.14-03": "奇偶页不同",
    "FR-4.15-01": "页码从正文开始",
    "FR-4.15-02": "页码字体五号TNR居中",
    "FR-4.15-03": "页码格式为-1-",
    "FR-4.15-04": "起始分节与页码联动高风险",
    "FR-4.16-01": "装订顺序符合要求",
    "FR-4.16-02": "装订线在左侧",
    "FR-4.16-03": "装订线处理仅检查不重排",
}

RULE_IDS_BY_DECISION: dict[RuleDecision, tuple[str, ...]] = {
    RuleDecision.AUTO_FIX: (
        "FR-4.2-01",
        "FR-4.2-02",
        "FR-4.2-03",
        "FR-4.3-01",
        "FR-4.4-01",
        "FR-4.4-02",
        "FR-4.4-03",
        "FR-4.5-01",
        "FR-4.5-02",
        "FR-4.6-01",
        "FR-4.6-02",
        "FR-4.7-01",
        "FR-4.7-02",
        "FR-4.8-03",
        "FR-4.8-04",
        "FR-4.8-05",
        "FR-4.9-01",
        "FR-4.10-02",
        "FR-4.10-03",
        "FR-4.10-04",
        "FR-4.11-01",
        "FR-4.11-02",
        "FR-4.12-01",
        "FR-4.12-02",
        "FR-4.13-02",
        "FR-4.14-01",
        "FR-4.14-02",
    ),
    RuleDecision.AUTO_CHECK: (
        "FR-4.1-01",
        "FR-4.1-03",
        "FR-4.3-02",
        "FR-4.3-03",
        "FR-4.5-03",
        "FR-4.5-04",
        "FR-4.5-05",
        "FR-4.6-03",
        "FR-4.6-04",
        "FR-4.6-07",
        "FR-4.8-01",
        "FR-4.8-02",
        "FR-4.10-01",
        "FR-4.11-03",
        "FR-4.12-03",
        "FR-4.13-01",
        "FR-4.13-03",
        "FR-4.14-03",
        "FR-4.15-03",
    ),
    RuleDecision.REPORT_ONLY: (
        "FR-4.1-02",
        "FR-4.6-05",
        "FR-4.6-06",
        "FR-4.11-04",
        "FR-4.11-05",
        "FR-4.11-06",
        "FR-4.15-01",
        "FR-4.15-02",
        "FR-4.16-01",
        "FR-4.16-02",
    ),
    RuleDecision.OUT_OF_V1: (
        "FR-4.1-04",
        "FR-4.1-05",
        "FR-4.10-05",
        "FR-4.15-04",
        "FR-4.16-03",
    ),
}


class RuleRegistry:
    """Central registry: rule_id -> metadata/detector/fixer/reporter."""

    def __init__(self) -> None:
        self._bindings: dict[str, RuleBinding] = {}
        self._build_default_bindings()

    def _build_default_bindings(self) -> None:
        for decision, rule_ids in RULE_IDS_BY_DECISION.items():
            for rule_id in rule_ids:
                metadata = RuleMetadata(
                    rule_id=rule_id,
                    rule_name=RULE_NAME_BY_ID[rule_id],
                    v1_decision=decision,
                    checked_only=decision is not RuleDecision.AUTO_FIX,
                    allow_write_back=decision is RuleDecision.AUTO_FIX,
                    source_of_truth=SOURCE_OF_TRUTH,
                )
                self._bindings[rule_id] = RuleBinding(metadata=metadata)

    def get_binding(self, rule_id: str) -> RuleBinding:
        return self._bindings[rule_id]

    def get_metadata(self, rule_id: str) -> RuleMetadata:
        return self.get_binding(rule_id).metadata

    def register_handlers(
        self,
        rule_id: str,
        *,
        detector: object | None = None,
        fixer: object | None = None,
        reporter: object | None = None,
    ) -> None:
        binding = self.get_binding(rule_id)
        if detector is not None:
            binding.detector = detector
        if fixer is not None:
            binding.fixer = fixer
        if reporter is not None:
            binding.reporter = reporter

    def all_metadata(self) -> tuple[RuleMetadata, ...]:
        ordered: list[RuleMetadata] = []
        for decision in RuleDecision:
            for rule_id in RULE_IDS_BY_DECISION[decision]:
                ordered.append(self._bindings[rule_id].metadata)
        return tuple(ordered)

    def rule_ids(self) -> tuple[str, ...]:
        return tuple(self._bindings.keys())

    def by_decision(self, decision: RuleDecision) -> tuple[RuleMetadata, ...]:
        return tuple(self._bindings[rule_id].metadata for rule_id in RULE_IDS_BY_DECISION[decision])


def iter_all_rule_ids() -> Iterable[str]:
    for decision in RuleDecision:
        yield from RULE_IDS_BY_DECISION[decision]
