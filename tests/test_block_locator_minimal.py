from pathlib import Path

from thesis_format_fixer.detectors.block_locator import locate_blocks, scan_reference_entries
from thesis_format_fixer.io.document_loader import CapabilityFlags, DocumentContext


def _context(paragraphs: list[str]) -> DocumentContext:
    return DocumentContext(
        source_path=Path("dummy.txt"),
        paragraphs=tuple(paragraphs),
        capabilities=CapabilityFlags(
            can_read_docx=False,
            can_write_docx=False,
            can_rebuild_toc=False,
            can_reconstruct_sections=False,
            can_renumber_footnotes_per_page=False,
            can_reconstruct_odd_even_layout=False,
            can_rebuild_cover=False,
            can_reorder_bibliography_content=False,
        ),
    )


def test_block_locator_outputs_confidence_and_evidence() -> None:
    context = _context(
        [
            "摘 要",
            "关键词：方法；实验；模型；评估；系统",
            "Abstract",
            "Keywords: Method; Experiment; Model",
            "CONTENTS",
            "REFERENCES",
            "致谢",
        ]
    )

    block_map = locate_blocks(context)

    expected_blocks = {
        "abstract_cn",
        "keywords_cn",
        "abstract_en",
        "keywords_en",
        "contents",
        "references",
        "ack",
        "abstract_cn_title",
        "abstract_en_title",
        "contents_title",
        "references_title",
        "ack_title",
        "body",
        "body_main_title",
        "body_paragraphs",
        "references_entries",
        "page_margins",
        "header",
        "footer",
    }
    assert expected_blocks.issubset(set(block_map.blocks))

    for block in block_map.blocks.values():
        assert isinstance(block.confidence, float)
        assert block.evidence
        assert block.evidence[0].reason


def test_references_entries_detect_continuous_numbered_items() -> None:
    context = _context(
        [
            "CONTENTS",
            "1 Intro",
            "REFERENCES",
            "[1] Smith J. Journal of Testing, 2026.",
            "[2] Brown A. Testing Press, 2025.",
            "[3] Lee C. Test Report, 2024.",
            "致谢",
        ]
    )

    block_map = locate_blocks(context)
    heading = block_map.blocks["references_heading"]
    entries = block_map.blocks["references_entries"]

    assert heading.start_paragraph == 2
    assert entries.start_paragraph == 3
    assert entries.end_paragraph == 5
    assert entries.confidence >= 0.9


def test_references_entries_support_continuations_and_blank_noise() -> None:
    context = _context(
        [
            "REFERENCES",
            "[1] Smith J. Journal of Testing,",
            "Vol.12(3):10-20.",
            "",
            "[2] Brown A. Testing Press, 2025.",
            "Master Thesis, TY University.",
            "APPENDIX",
            "Appendix content should not be included.",
        ]
    )

    block_map = locate_blocks(context)
    entries = block_map.blocks["references_entries"]

    assert entries.start_paragraph == 1
    assert entries.end_paragraph == 5
    assert "groups=2" in entries.evidence[0].reason


def test_references_entries_detect_english_author_leading_fallback() -> None:
    paragraphs = (
        "REFERENCES",
        "Smith, J. Testing Methodology. Journal of Tests, 2026.",
        "Brown A. Experimental Results. Testing Press, 2025.",
        "致谢",
    )
    scan = scan_reference_entries(paragraphs, heading_index=0, hard_stop_index=3)

    assert len(scan.entry_groups) == 2
    assert scan.entry_group_sources == ("author_leading_fallback", "author_leading_fallback")


def test_references_entries_detect_chinese_author_leading_fallback() -> None:
    paragraphs = (
        "REFERENCES",
        "王强，李明. 测试方法研究. 测试学报, 2024.",
        "张三. 模型验证报告. 2023.",
        "附录",
    )
    scan = scan_reference_entries(paragraphs, heading_index=0, hard_stop_index=3)

    assert len(scan.entry_groups) == 2
    assert scan.entry_group_sources == ("author_leading_fallback", "author_leading_fallback")


def test_references_entries_numbered_and_author_leading_can_coexist() -> None:
    paragraphs = (
        "REFERENCES",
        "[1] Smith J. Journal of Testing, 2026.",
        "Wang, Q.; Li, M. Bilingual Research Report, 2025.",
        "[2] Brown A. Testing Press, 2024.",
        "ACKNOWLEDGEMENTS",
    )
    scan = scan_reference_entries(paragraphs, heading_index=0, hard_stop_index=4)

    assert len(scan.entry_groups) == 3
    assert scan.entry_group_sources == (
        "numbered_entry",
        "author_leading_fallback",
        "numbered_entry",
    )


def test_references_entries_author_leading_multiline_is_grouped_stably() -> None:
    paragraphs = (
        "REFERENCES",
        "Smith, J., Brown, A., and Lee, C. Collaborative Testing Framework.",
        "Journal of Complex Validation, 2026, 12(3):10-20.",
        "Wang, Q. Another Study. 2025.",
        "APPENDIX",
    )
    scan = scan_reference_entries(paragraphs, heading_index=0, hard_stop_index=4)

    assert len(scan.entry_groups) == 2
    assert scan.entry_groups[0] == (1, 2)
    assert scan.entry_group_sources[0] == "author_leading_fallback"


def test_references_heading_does_not_match_plain_body_mentions() -> None:
    context = _context(
        [
            "In this section we mention REFERENCES as a concept.",
            "Another normal body paragraph.",
            "[1] citation-like token in plain body should not trigger references block.",
        ]
    )

    block_map = locate_blocks(context)
    assert block_map.blocks["references_title"].start_paragraph is None
    assert block_map.blocks["references_entries"].start_paragraph is None
