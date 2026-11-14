"""Parser for DOCX/TXT methodology and FAQ documents (e.g. BASS-II data FAQ.docx)."""

from pathlib import Path
from typing import Any
from docx import Document

# PI-to-flow-direction defaults extracted from BASS-II data FAQ.docx
FAQ_PI_FLOW_DEFAULTS: dict[str, str] = {
    "Bhattacharjee": "Opposed",
    "Fernandez-Pello": "Opposed",
    "Miller": "Opposed",
    "Olson": "Stagnation",
    "T'ien": "Concurrent",
    "Ferkul": "Concurrent",
}


def parse_bass2_faq(docx_path: Path | str) -> dict[str, Any]:
    """Extract FAQ rules, sensor caveats, and PI flow-direction defaults from BASS-II data FAQ.docx."""
    path = Path(docx_path)
    if not path.exists():
        return {"paragraphs": [], "pi_flow_defaults": FAQ_PI_FLOW_DEFAULTS, "sensor_notes": []}

    doc = Document(str(path))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]

    sensor_notes: list[str] = []
    for text in paragraphs:
        lower = text.lower()
        if any(k in lower for k in ("calibrated", "mca", "anemometer", "response time", "over range", "or =")):
            sensor_notes.append(text)

    return {
        "paragraphs": paragraphs,
        "pi_flow_defaults": dict(FAQ_PI_FLOW_DEFAULTS),
        "sensor_notes": sensor_notes,
    }
