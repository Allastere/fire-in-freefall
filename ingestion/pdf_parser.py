"""Lightweight pypdf parser for NASA technical reports and BASS-II Appendix A test matrices."""

import re
from pathlib import Path
from typing import Any
from pypdf import PdfReader

_CAMERA_METADATA_MARKERS: tuple[str, ...] = (
    "Exposure Mode",
    "Exposure compensation",
    "Bracket frames",
    "Shutter speed",
    "Shutter hold",
    "F stop",
    "ISO",
    "SD card",
    "Secure digital",
    "Release mode",
    "Filter (Y/N)",
)

_SKIP_SECTION_MARKERS: tuple[str, ...] = (
    "References",
    "Presentations and Publications",
    "Publications",
)


def _clean_pdf_text(text: str) -> str:
    """Normalize PDF line breaks and filter camera header noise."""
    cleaned_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(marker.lower() in stripped.lower() for marker in _CAMERA_METADATA_MARKERS):
            continue
        cleaned_lines.append(stripped)
    return "\n".join(cleaned_lines)


def _extract_observation_tail(row_block: str) -> str:
    """Extract the descriptive Test observations and anomalies text after sensor columns."""
    # Sensor columns at the end of Appendix A rows are 9 numeric/---/OR/NA fields followed by English text.
    # Match after the last CO / O2 / frames block before the next test/footnote.
    tail_match = re.search(
        r"(?:\bNA\b|---|\+?OR|over|[-+]?\d+(?:\.\d+)?)\s+"
        r"(?:\bNA\b|---|\+?OR|over|[-+]?\d+(?:\.\d+)?)\s+"
        r"([A-Z][A-Za-z0-9,.;:()'\"/\-\s%°µ]+)$",
        row_block.strip(),
    )
    if tail_match:
        obs = re.sub(r"\s+", " ", tail_match.group(1)).strip()
        # Trim trailing footnote lines (e.g., "aGreenwich Mean Time.")
        obs = re.split(r"\b[a-h](?:Greenwich|Manual|Continuous|Exposure|Number|Bracket)\b", obs)[0].strip()
        return obs[:400]
    return ""


def parse_bass2_appendix_a(pdf_path: Path | str) -> dict[str, dict[str, Any]]:
    """Extract per-test flow_direction, observations, and report source_page from Appendix A (Tables A.1–A.6)."""
    path = Path(pdf_path)
    if not path.exists():
        return {}

    reader = PdfReader(str(path))
    test_metadata: dict[str, dict[str, Any]] = {}

    row_pattern = re.compile(
        r"(?:^|\s)(?:[-0-9]+|---+|NA)\s+"
        r"([BFMOP]\d+[ab]?|T\d+[ab]?)\s+"
        r"(?:\d+[mML]?|---)\s+"
        r".{1,220}?"
        r"(?<!\w)(Opposed|Concurrent|Stagnation|\?)(?!\w)",
        flags=re.DOTALL,
    )

    for page_idx, page in enumerate(reader.pages):
        raw_text = page.extract_text() or ""
        if "Appendix A" not in raw_text and "TABLE A." not in raw_text:
            continue

        # Stop processing if References/Publications section appears on page
        header_line = raw_text.splitlines()[0] if raw_text else ""
        if any(sec.lower() in header_line.lower() for sec in _SKIP_SECTION_MARKERS):
            continue

        # Parse NASA report page number (e.g. "NASA/TM-20210011385 103")
        tm_match = re.search(r"NASA/TM-\S+\s+(\d+)", raw_text)
        report_page = int(tm_match.group(1)) if tm_match else (page_idx + 1)

        cleaned = _clean_pdf_text(raw_text)
        matches = list(row_pattern.finditer(cleaned))

        for i, match in enumerate(matches):
            test_id = match.group(1).strip()
            raw_dir = match.group(2).strip()
            flow_direction = "Unknown" if raw_dir == "?" else raw_dir

            start_pos = match.end()
            end_pos = matches[i + 1].start() if (i + 1) < len(matches) else min(len(cleaned), start_pos + 700)
            row_tail = cleaned[start_pos:end_pos]
            observations = _extract_observation_tail(row_tail)

            test_metadata[test_id] = {
                "flow_direction": flow_direction,
                "observations": observations,
                "source_page": report_page,
                "source_doc": path.name,
            }

    return test_metadata
