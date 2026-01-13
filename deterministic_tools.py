import csv
import json
from dataclasses import dataclass
from io import StringIO
from typing import Any, Dict, List, Optional


@dataclass
class StructuredParseResponse:
    parsed: List[Any]
    warnings: List[str]


def parse_structured_data(
    raw_text: str,
    fmt: str = "json",
    delimiter: Optional[str] = None,
    column_names: Optional[List[str]] = None,
    schema: Optional[List[str]] = None,
) -> StructuredParseResponse:
    text = raw_text or ""
    warnings: List[str] = []
    if not text.strip():
        warnings.append("Input text is empty")
        return StructuredParseResponse(parsed=[], warnings=warnings)

    if fmt == "json":
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError as exc:
            return StructuredParseResponse(parsed=[], warnings=[f"JSON decode error: {exc}"])
        if isinstance(decoded, list):
            parsed = decoded
        else:
            parsed = [decoded]
        parsed = _ensure_schema(parsed, schema, warnings)
        return StructuredParseResponse(parsed=parsed, warnings=warnings)

    if fmt == "csv":
        delim = delimiter or ","
        reader = csv.reader(StringIO(text), delimiter=delim)
        rows = [row for row in reader if row]
        if not rows:
            warnings.append("CSV input contains no rows")
            return StructuredParseResponse(parsed=[], warnings=warnings)
        header: List[str]
        data_rows: List[List[str]]
        if column_names:
            header = column_names
            data_rows = rows
        else:
            header = rows[0]
            data_rows = rows[1:]
        parsed = []
        for idx, row in enumerate(data_rows, start=1):
            entry = {}

            for col_index, column in enumerate(header):
                if col_index < len(row):
                    entry[column] = row[col_index]
                else:
                    entry[column] = ""
            parsed.append(entry)
        parsed = _ensure_schema(parsed, schema, warnings)
        return StructuredParseResponse(parsed=parsed, warnings=warnings)

    if fmt == "lines":
        delim = delimiter or "\n"
        lines = [line for line in text.split(delim) if line.strip()]
        if not lines:
            warnings.append("No line entries found")
            return StructuredParseResponse(parsed=[], warnings=warnings)
        parsed = []
        for idx, line in enumerate(lines, start=1):
            if column_names and len(column_names) == 1:
                parsed.append({column_names[0]: line})
            elif column_names:
                entry: Dict[str, Any] = {}
                entry[column_names[0]] = line
                for extra in column_names[1:]:
                    entry[extra] = ""
                parsed.append(entry)
            else:
                parsed.append({"line": line})
        parsed = _ensure_schema(parsed, schema, warnings)
        return StructuredParseResponse(parsed=parsed, warnings=warnings)

    warnings.append(f"Unsupported format '{fmt}'")
    return StructuredParseResponse(parsed=[], warnings=warnings)


def _ensure_schema(
    parsed: List[Any],
    schema: Optional[List[str]],
    warnings: List[str],
) -> List[Any]:
    if not schema:
        return parsed
    enhanced = []
    for idx, entry in enumerate(parsed, start=1):
        if not isinstance(entry, dict):
            warnings.append(f"Entry {idx} is not an object; skipping schema validation")
            enhanced.append(entry)
            continue
        missing = [field for field in schema if field not in entry or entry[field] == ""]
        if missing:
            warnings.append(f"Entry {idx} missing fields: {missing}")
        enhanced.append(entry)
    return enhanced
