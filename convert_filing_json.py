#!/usr/bin/env python3
import sys
import json
from pathlib import Path
from typing import Any, Dict, List, Union

Json = Dict[str, Any]

def is_probably_ndjson(text: str) -> bool:
    # Heuristic: multiple lines that each appear to be JSON objects/arrays
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) <= 1:
        return False
    try:
        # Try parsing first few lines independently
        for ln in lines[:10]:
            json.loads(ln)
        return True
    except Exception:
        return False

def load_input(path: Path) -> Union[Json, List[Json]]:
    data = path.read_text(encoding="utf-8")
    # NDJSON?
    if is_probably_ndjson(data):
        docs: List[Json] = []
        for ln in data.splitlines():
            ln = ln.strip()
            if not ln:
                continue
            docs.append(json.loads(ln))
        return docs
    # Regular JSON (object or array)
    return json.loads(data)

def transform_sections(sections_obj: Any) -> List[Json]:
    """
    Convert a 'sections' mapping to a list of objects.
    Keeps original values and adds 'section_id' from the original key.
    If sections_obj is already a list, return as-is.
    If it's missing or not a mapping/list, return empty list.
    """
    if isinstance(sections_obj, list):
        # Trust user-provided list form
        # Ensure section_id exists; if not, derive a stable id
        out = []
        for idx, sec in enumerate(sections_obj):
            if isinstance(sec, dict):
                if "section_id" not in sec:
                    sec = {**sec, "section_id": f"section_{idx}"}
                out.append(sec)
        return out
    if isinstance(sections_obj, dict):
        result: List[Json] = []
        for key, value in sections_obj.items():
            if isinstance(value, dict):
                result.append({**value, "section_id": key})
            else:
                # Non-dict section value; wrap it
                result.append({"section_id": key, "value": value})
        return result
    return []

def transform_parts(parts_obj: Any) -> List[Json]:
    """
    Convert 'parts' mapping to a list of part objects.
    Each part keeps/sets 'part_name' and converts its 'sections' similarly.
    If 'parts' is already a list, normalize each element's sections.
    """
    out: List[Json] = []
    if isinstance(parts_obj, list):
        for part in parts_obj:
            if not isinstance(part, dict):
                continue
            part_name = part.get("part_name")
            sections = transform_sections(part.get("sections"))
            # Preserve all other part fields
            base = {k: v for k, v in part.items() if k not in ("sections",)}
            base["sections"] = sections
            # Ensure part_name present
            if not base.get("part_name"):
                base["part_name"] = part_name or "Part"
            out.append(base)
        return out

    if isinstance(parts_obj, dict):
        for key, value in parts_obj.items():
            if isinstance(value, dict):
                part_name = value.get("part_name") or key
                sections = transform_sections(value.get("sections"))
                # Preserve all other fields inside the part value
                base = {k: v for k, v in value.items() if k not in ("sections",)}
                base["part_name"] = part_name
                base["sections"] = sections
                out.append(base)
            else:
                # Non-dict part; wrap it
                out.append({"part_name": key, "value": value, "sections": []})
        return out

    # If parts missing or unexpected, return empty list
    return []

def transform_document(doc: Json) -> Json:
    """
    Transform a single filing document:
    - Replace 'parts' with array-of-parts
    - Each part's 'sections' -> array-of-sections with 'section_id'
    Preserve all other top-level fields.
    """
    top = {k: v for k, v in doc.items() if k != "parts"}
    parts = transform_parts(doc.get("parts"))
    top["parts"] = parts
    return top

def main(argv: List[str]) -> int:
    if len(argv) < 3:
        print("Usage: python convert_filing_json.py <input.json> <output.json>")
        return 2

    in_path = Path(argv[1])
    out_path = Path(argv[2])

    if not in_path.exists():
        print(f"Input file not found: {in_path}")
        return 1

    data = load_input(in_path)

    if isinstance(data, list):
        transformed = [transform_document(d) for d in data if isinstance(d, dict)]
    else:
        transformed = transform_document(data)

    # Write output: if multiple docs, write as JSON array
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(transformed, f, ensure_ascii=False, indent=2)

    print(f"Wrote transformed JSON to {out_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
