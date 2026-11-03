"""CSV data quality analysis."""

import csv
from io import StringIO


def analyze_csv(content: bytes, delimiter: str = ",") -> dict:
    """Analyze a UTF-8 CSV with a header row."""
    if delimiter not in (",", ";"):
        raise ValueError("Use a comma or semicolon delimiter.")

    text = content.decode("utf-8-sig")
    reader = csv.reader(
        StringIO(text, newline=""),
        delimiter=delimiter,
        strict=True,
    )

    headers = [value.strip() for value in next(reader, [])]

    if not headers or any(not header for header in headers):
        raise ValueError("A header is required for every column.")

    if len(set(headers)) != len(headers):
        raise ValueError("Column headers must be unique.")

    report = {
        "row_count": 0,
        "duplicate_count": 0,
        "empty_cell_count": 0,
        "anomalies": [],
    }

    seen_rows = set()
    next_line = reader.line_num + 1

    for row in reader:
        row_number = next_line
        next_line = reader.line_num + 1

        if not row:
            continue

        if len(row) != len(headers):
            raise ValueError(
                f"Row {row_number} has an unexpected number of columns."
            )

        report["row_count"] += 1

        row_key = tuple(row)

        if row_key in seen_rows:
            report["duplicate_count"] += 1
            report["anomalies"].append({
                "type": "duplicate_row",
                "row": row_number,
            })

        seen_rows.add(row_key)

        for column, value in zip(headers, row):
            if not value.strip():
                report["empty_cell_count"] += 1
                report["anomalies"].append({
                    "type": "empty_cell",
                    "row": row_number,
                    "column": column,
                })

    return report