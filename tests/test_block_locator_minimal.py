from pathlib import Path

from thesis_format_fixer.detectors.block_locator import locate_blocks
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
    }
    assert set(block_map.blocks) == expected_blocks

    for block in block_map.blocks.values():
        assert isinstance(block.confidence, float)
        assert block.evidence
        assert block.evidence[0].reason
