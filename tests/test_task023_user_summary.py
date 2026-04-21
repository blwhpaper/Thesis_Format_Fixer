from __future__ import annotations

from thesis_format_fixer.reporters.report_builder import build_user_result_summary, render_user_summary_markdown


def _base_payload() -> dict:
    return {
        "summary": {
            "auto_fix_rule_count": 0,
            "detected_not_auto_modified_count": 0,
            "manual_review_required_count": 0,
        },
        "sections": {
            "auto_fixed": [],
            "detected_not_auto_modified": [],
            "manual_review_required": [],
        },
    }


def test_user_summary_contains_auto_fixed_section_when_auto_fix_exists() -> None:
    payload = _base_payload()
    payload["summary"]["auto_fix_rule_count"] = 1
    payload["sections"]["auto_fixed"] = [
        {"rule_id": "FR-4.2-01", "rule_name": "中文摘要标题文本为摘 要", "status": "fixed"}
    ]
    summary = build_user_result_summary(payload, artifact_paths={"user_summary_md": "/tmp/user_summary.md"})
    md = render_user_summary_markdown(summary, payload=payload)
    assert "## 已自动修改" in md
    assert "FR-4.2-01" in md
    assert "已处理" in md


def test_user_summary_contains_detected_not_fixed_section() -> None:
    payload = _base_payload()
    payload["summary"]["detected_not_auto_modified_count"] = 1
    payload["sections"]["detected_not_auto_modified"] = [
        {
            "rule_id": "FR-4.6-06",
            "rule_name": "目录标题与正文标题一致",
            "decision": "Report Only",
            "status": "detected_not_modified",
        }
    ]
    summary = build_user_result_summary(payload, artifact_paths={"user_summary_md": "/tmp/user_summary.md"})
    md = render_user_summary_markdown(summary, payload=payload)
    assert "## 发现但未自动修改" in md
    assert "未自动修改" in md
    assert "原因：" in md


def test_user_summary_contains_manual_review_section() -> None:
    payload = _base_payload()
    payload["summary"]["manual_review_required_count"] = 1
    payload["sections"]["manual_review_required"] = [
        {
            "item_type": "rule",
            "rule_id": "FR-4.10-05",
            "rule_name": "脚注按页重编编号",
            "reason": "out_of_v1_scope",
        }
    ]
    summary = build_user_result_summary(payload, artifact_paths={"user_summary_md": "/tmp/user_summary.md"})
    md = render_user_summary_markdown(summary, payload=payload)
    assert "## 建议优先人工检查" in md
    assert "脚注按页重编编号" in md
    assert "当前版本出于安全边界不自动修改该类问题" in md


def test_user_summary_is_generated_safely_when_no_issues() -> None:
    payload = _base_payload()
    summary = build_user_result_summary(payload, artifact_paths={"user_summary_md": "/tmp/user_summary.md"})
    md = render_user_summary_markdown(summary, payload=payload)
    assert "用户版结果摘要" in md
    assert "本次未发生可自动修改的问题" in md
    assert "当前没有必须优先人工处理的项" in md
