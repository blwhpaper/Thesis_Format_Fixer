"""Local model adapter interfaces for TASK-007 review."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol


class ModelAdapterError(RuntimeError):
    """Raised when local model adapter fails."""


class LocalModelAdapter(Protocol):
    """Pluggable local model adapter interface."""

    def generate(self, *, task: str, payload: dict[str, object]) -> list[dict[str, object]]:
        """Generate structured verdicts for a review task."""


@dataclass(slots=True)
class DisabledModelAdapter:
    """No-op adapter used when model usage is disabled."""

    def generate(self, *, task: str, payload: dict[str, object]) -> list[dict[str, object]]:
        return []


@dataclass(slots=True)
class StubModelAdapter:
    """Deterministic adapter for tests."""

    responses: dict[str, object]

    def generate(self, *, task: str, payload: dict[str, object]) -> list[dict[str, object]]:
        raw = self.responses.get(task, [])
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ModelAdapterError(f"invalid_json:{task}") from exc
        if not isinstance(raw, list):
            raise ModelAdapterError(f"invalid_shape:{task}")
        output: list[dict[str, object]] = []
        for item in raw:
            if not isinstance(item, dict):
                raise ModelAdapterError(f"invalid_item:{task}")
            output.append(item)
        return output


@dataclass(slots=True)
class PlaceholderLocalModelAdapter:
    """Placeholder for future concrete local model integrations."""

    model_name: str

    def generate(self, *, task: str, payload: dict[str, object]) -> list[dict[str, object]]:
        raise ModelAdapterError(f"local_model_not_implemented:{self.model_name}:{task}")
