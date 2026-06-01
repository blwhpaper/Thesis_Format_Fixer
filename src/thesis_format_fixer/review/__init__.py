"""Review package for TASK-007 intelligent checks."""

from thesis_format_fixer.review.adapter import (
    TFF_AUTHOR,
    TFF_INITIALS,
    ReviewApplyResult,
    ReviewFinding as WordReviewFinding,
    WordReviewAdapter,
)
from thesis_format_fixer.review.model_adapter import (
    DisabledModelAdapter,
    LocalModelAdapter,
    ModelAdapterError,
    PlaceholderLocalModelAdapter,
    StubModelAdapter,
)
from thesis_format_fixer.review.reviewer import REVIEW_TARGETS, ReviewConfig, Reviewer

__all__ = [
    "TFF_AUTHOR",
    "TFF_INITIALS",
    "DisabledModelAdapter",
    "LocalModelAdapter",
    "ModelAdapterError",
    "PlaceholderLocalModelAdapter",
    "REVIEW_TARGETS",
    "ReviewApplyResult",
    "ReviewConfig",
    "Reviewer",
    "StubModelAdapter",
    "WordReviewAdapter",
    "WordReviewFinding",
]
