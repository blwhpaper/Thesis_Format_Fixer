"""Conservative bibliography entry parser for TASK-011."""

from __future__ import annotations

from dataclasses import dataclass
import re


TYPE_CODE_RE = re.compile(r"\[(?P<type>[A-Z]{1,3}(?:/[A-Z]{1,3})?)\]")
INDEX_RE = re.compile(r"^\s*\[(?P<index>\d+)\]\s*")
YEAR_RE = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
URL_RE = re.compile(r"(https?://\S+|doi:\s*\S+)", re.IGNORECASE)
ISSUE_RE = re.compile(r"(?:\(|（)\s*([^)）]+)\s*(?:\)|）)")
PAGES_RE = re.compile(r"(\d+\s*[-–—]\s*\d+)")
PLACE_PUBLISHER_YEAR_RE = re.compile(
    r"(?P<place>[^,:，：]{1,40})\s*[:：]\s*(?P<publisher>[^,，]{1,80})\s*[,，]\s*(?P<year>(?:19|20)\d{2})"
)
EDITION_RE = re.compile(r"(\d+(?:st|nd|rd|th)\s+ed\.?|第[一二三四五六七八九十0-9]+版)", re.IGNORECASE)
TYPE_BY_CODE: dict[str, str] = {
    "J": "journal",
    "M": "book",
    "D": "thesis",
    "R": "report",
    "C": "conference",
    "N": "newspaper",
    "S": "standard",
    "P": "patent",
    "DB": "electronic",
    "EB": "electronic",
    "CP": "electronic",
}


@dataclass(frozen=True, slots=True)
class ReferenceEntryParse:
    raw_text: str
    normalized_text: str
    index_number: int | None
    authors: tuple[str, ...]
    title: str | None
    entry_type: str
    type_code: str | None
    container_or_source: str | None
    year: str | None
    issue: str | None
    pages: str | None
    publisher: str | None
    publication_place: str | None
    edition: str | None
    degree_grantor: str | None
    medium_code: str | None
    url_or_locator: str | None
    language_hint: str
    parse_confidence: str
    parse_notes: tuple[str, ...]


def _normalize_text(text: str) -> str:
    cleaned = text.replace("\u3000", " ").replace("\n", " ").replace("\t", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _detect_language_hint(text: str) -> str:
    has_zh = any("\u4e00" <= ch <= "\u9fff" for ch in text)
    has_en = any(("a" <= ch.lower() <= "z") for ch in text)
    if has_zh and has_en:
        return "mixed"
    if has_zh:
        return "zh"
    if has_en:
        return "en"
    return "unknown"


def _split_type_code(raw_type_code: str | None) -> tuple[str | None, str | None]:
    if not raw_type_code:
        return None, None
    parts = raw_type_code.split("/", maxsplit=1)
    if len(parts) == 1:
        return parts[0], None
    return parts[0], parts[1]


def _infer_entry_type(
    normalized: str,
    explicit_code: str | None,
    notes: list[str],
) -> tuple[str, bool]:
    if explicit_code:
        entry_type = TYPE_BY_CODE.get(explicit_code, "unknown")
        if entry_type == "unknown":
            notes.append(f"unknown_explicit_type_code:{explicit_code}")
        return entry_type, True

    lowered = normalized.casefold()
    if URL_RE.search(normalized):
        notes.append("type_inferred_from_url")
        return "electronic", False
    if any(token in lowered for token in ("thesis", "dissertation", "学位论文", "硕士论文", "博士论文")):
        notes.append("type_inferred_from_thesis_keyword")
        return "thesis", False
    if any(token in lowered for token in ("journal", "vol.", "no.", "期刊", "学报", "卷", "期")):
        notes.append("type_inferred_from_journal_keyword")
        return "journal", False
    if any(token in lowered for token in ("press", "publisher", "出版社", "出版")):
        notes.append("type_inferred_from_book_or_report_keyword")
        return "book_or_report", False
    notes.append("type_not_resolved")
    return "unknown", False


def _split_authors_and_title(prefix: str, notes: list[str]) -> tuple[tuple[str, ...], str | None]:
    trimmed = prefix.strip().strip("，,;；")
    if not trimmed:
        notes.append("authors_title_prefix_empty")
        return (), None

    segments = [part.strip(" ;；，,") for part in re.split(r"[。.]", trimmed) if part.strip()]
    if len(segments) >= 2:
        authors_blob = segments[0]
        title = ".".join(segments[1:]).strip() or None
        authors = tuple(item.strip() for item in re.split(r"\s*(?:,|，|、|;|；| and | & )\s*", authors_blob) if item.strip())
        return authors, title

    notes.append("authors_title_split_fallback")
    return (trimmed,), None


def _parse_journal_suffix(suffix: str) -> dict[str, str | None]:
    payload: dict[str, str | None] = {
        "container_or_source": None,
        "year": None,
        "issue": None,
        "pages": None,
    }
    year_match = YEAR_RE.search(suffix)
    if year_match:
        payload["year"] = year_match.group(0)
        container = suffix[: year_match.start()].strip(" .，,;；:")
        payload["container_or_source"] = container or None
    else:
        payload["container_or_source"] = suffix.strip(" .，,;；:") or None

    issue_match = ISSUE_RE.search(suffix)
    if issue_match:
        payload["issue"] = issue_match.group(1).strip()
    pages_match = PAGES_RE.search(suffix)
    if pages_match:
        payload["pages"] = pages_match.group(1).replace(" ", "")
    return payload


def _parse_bookish_suffix(suffix: str) -> dict[str, str | None]:
    payload: dict[str, str | None] = {
        "container_or_source": None,
        "year": None,
        "publisher": None,
        "publication_place": None,
        "edition": None,
        "degree_grantor": None,
        "pages": None,
    }
    suffix_wo_edition = suffix
    edition_match = EDITION_RE.search(suffix)
    if edition_match:
        payload["edition"] = edition_match.group(1).strip()
        suffix_wo_edition = (suffix[: edition_match.start()] + " " + suffix[edition_match.end() :]).strip()

    match = PLACE_PUBLISHER_YEAR_RE.search(suffix_wo_edition)
    if match:
        payload["publication_place"] = match.group("place").strip()
        payload["publisher"] = match.group("publisher").strip()
        payload["year"] = match.group("year")
    else:
        year_match = YEAR_RE.search(suffix)
        if year_match:
            payload["year"] = year_match.group(0)

    pages_match = PAGES_RE.search(suffix_wo_edition)
    if pages_match:
        payload["pages"] = pages_match.group(1).replace(" ", "")

    degree_match = re.search(
        r"(?:at|in|授予单位|授予机构)[:：\s]*([^,，.;；。]{2,80})",
        suffix,
        re.IGNORECASE,
    )
    if degree_match:
        payload["degree_grantor"] = degree_match.group(1).strip()
    elif any(token in suffix for token in ("学位论文", "thesis", "dissertation")):
        payload["degree_grantor"] = (payload["publisher"] or payload["publication_place"] or "").strip() or None

    if payload["publication_place"] is None and payload["publisher"] is None:
        payload["container_or_source"] = suffix.strip(" .，,;；:") or None

    return payload


def _parse_electronic_suffix(suffix: str) -> dict[str, str | None]:
    payload: dict[str, str | None] = {
        "container_or_source": None,
        "year": None,
        "url_or_locator": None,
    }
    locator_match = URL_RE.search(suffix)
    if locator_match:
        payload["url_or_locator"] = locator_match.group(1).strip().rstrip(".,;；。")
        prefix = suffix[: locator_match.start()].strip(" .，,;；:")
        payload["container_or_source"] = prefix or None
    else:
        payload["container_or_source"] = suffix.strip(" .，,;；:") or None

    year_match = YEAR_RE.search(suffix)
    if year_match:
        payload["year"] = year_match.group(0)
    return payload


def parse_reference_entry(raw_text: str) -> ReferenceEntryParse:
    normalized = _normalize_text(raw_text)
    notes: list[str] = []

    index_number = None
    index_match = INDEX_RE.match(normalized)
    working = normalized
    if index_match:
        index_number = int(index_match.group("index"))
        working = normalized[index_match.end() :].strip()
    else:
        notes.append("index_number_missing")

    type_match = TYPE_CODE_RE.search(working)
    raw_type_code = type_match.group("type") if type_match else None
    explicit_code, medium_code = _split_type_code(raw_type_code)
    entry_type, from_explicit_code = _infer_entry_type(working, explicit_code, notes)

    authors: tuple[str, ...] = ()
    title: str | None = None
    container_or_source: str | None = None
    year: str | None = None
    issue: str | None = None
    pages: str | None = None
    publisher: str | None = None
    publication_place: str | None = None
    edition: str | None = None
    degree_grantor: str | None = None
    url_or_locator: str | None = None

    if type_match:
        prefix = working[: type_match.start()].strip()
        suffix = working[type_match.end() :].strip(" .，,;；")
    else:
        split = re.split(r"[。.]", working, maxsplit=2)
        if len(split) >= 2:
            prefix = f"{split[0]}.{split[1]}"
            suffix = split[2].strip() if len(split) >= 3 else ""
        else:
            prefix = working
            suffix = ""
            notes.append("type_marker_missing_and_split_failed")

    authors, title = _split_authors_and_title(prefix, notes)

    if entry_type == "journal":
        journal_data = _parse_journal_suffix(suffix)
        container_or_source = journal_data["container_or_source"]
        year = journal_data["year"]
        issue = journal_data["issue"]
        pages = journal_data["pages"]
    elif entry_type in {"book", "thesis", "report", "book_or_report"}:
        bookish = _parse_bookish_suffix(suffix)
        container_or_source = bookish["container_or_source"]
        year = bookish["year"]
        pages = bookish["pages"]
        publisher = bookish["publisher"]
        publication_place = bookish["publication_place"]
        edition = bookish["edition"]
        degree_grantor = bookish["degree_grantor"]
    elif entry_type == "electronic":
        electronic = _parse_electronic_suffix(suffix or working)
        container_or_source = electronic["container_or_source"]
        year = electronic["year"]
        url_or_locator = electronic["url_or_locator"]
    else:
        # Keep resilient fallback extraction for unknown forms.
        year_match = YEAR_RE.search(working)
        if year_match:
            year = year_match.group(0)
        locator_match = URL_RE.search(working)
        if locator_match:
            url_or_locator = locator_match.group(1).strip().rstrip(".,;；。")

    if url_or_locator is None:
        locator_match = URL_RE.search(working)
        if locator_match:
            url_or_locator = locator_match.group(1).strip().rstrip(".,;；。")

    language_hint = _detect_language_hint(normalized)

    parse_confidence = "low"
    if from_explicit_code and entry_type != "unknown":
        if (authors or title) and (year or container_or_source or publisher or url_or_locator):
            parse_confidence = "high"
        else:
            notes.append("explicit_type_but_fields_sparse")
    elif entry_type != "unknown":
        notes.append("heuristic_type_confidence_downgraded")
    else:
        notes.append("entry_type_unknown")

    if entry_type == "unknown":
        notes.append("fallback_raw_only")

    return ReferenceEntryParse(
        raw_text=raw_text,
        normalized_text=normalized,
        index_number=index_number,
        authors=authors,
        title=title,
        entry_type=entry_type,
        type_code=explicit_code,
        container_or_source=container_or_source,
        year=year,
        issue=issue,
        pages=pages,
        publisher=publisher,
        publication_place=publication_place,
        edition=edition,
        degree_grantor=degree_grantor,
        medium_code=medium_code,
        url_or_locator=url_or_locator,
        language_hint=language_hint,
        parse_confidence=parse_confidence,
        parse_notes=tuple(notes),
    )
