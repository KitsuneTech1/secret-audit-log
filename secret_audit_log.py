#!/usr/bin/env python3
"""Read and display a secret audit trail without printing secret values."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


PUBLIC_FIELDS = ("timestamp", "tool", "secret", "reason")


class AuditLogError(ValueError):
    """Raised when an audit log cannot be read or does not match its format."""


def _validate_entry(entry, index):
    if not isinstance(entry, dict):
        raise AuditLogError(f"Entry {index} is not an object")

    missing = [field for field in PUBLIC_FIELDS if field not in entry]
    if missing:
        raise AuditLogError(
            f"Entry {index} is missing metadata: {', '.join(missing)}"
        )

    for field in PUBLIC_FIELDS:
        value = entry[field]
        if not isinstance(value, str) or not value.strip():
            raise AuditLogError(f"Entry {index} has invalid {field} metadata")

    try:
        datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise AuditLogError(f"Entry {index} has an invalid timestamp") from exc

    return entry


def _validate_entries(data):
    if isinstance(data, dict):
        if "entries" not in data:
            raise AuditLogError("Log object must contain an 'entries' list")
        data = data["entries"]

    if not isinstance(data, list):
        raise AuditLogError("Log must be a JSON list or an object with an 'entries' list")

    return [_validate_entry(entry, index) for index, entry in enumerate(data)]


def _parse_json_lines(text):
    entries = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise AuditLogError(f"Invalid JSON on line {line_number}: {exc.msg}") from exc
    return _validate_entries(entries)


def load_log(log_path):
    """Load a JSON array, entries envelope, or JSON Lines audit log."""
    path = Path(log_path)
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as exc:
        raise AuditLogError(f"Log file not found: {log_path}") from exc
    except UnicodeError as exc:
        raise AuditLogError(f"Log file is not valid UTF-8: {log_path}") from exc
    except OSError as exc:
        detail = exc.strerror or "could not read file"
        raise AuditLogError(f"Could not read log file {log_path}: {detail}") from exc

    if not text.strip():
        return []

    try:
        return _validate_entries(json.loads(text))
    except json.JSONDecodeError as exc:
        try:
            return _parse_json_lines(text)
        except AuditLogError as line_error:
            raise AuditLogError(f"Invalid JSON in {log_path}: {exc.msg}") from line_error


def filter_entries(entries, filter_str):
    """Filter entries by substring match in tool, secret, or reason."""
    if filter_str is None or filter_str == "":
        return entries

    filter_lower = str(filter_str).casefold()
    return [
        entry for entry in entries
        if isinstance(entry, dict)
        and any(filter_lower in str(entry.get(field, "")).casefold()
                for field in ("tool", "secret", "reason"))
    ]


def _select_entries(entries, limit):
    if limit is None:
        return list(entries)
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
        raise ValueError("limit must be a non-negative integer")
    if limit == 0:
        return []
    return list(entries[-limit:])


def _public_entry(entry):
    return {field: entry[field] for field in PUBLIC_FIELDS}


def _table_value(value):
    escaped = []
    for character in str(value):
        if character == "\r":
            escaped.append("\\r")
        elif character == "\n":
            escaped.append("\\n")
        elif character == "\t":
            escaped.append("\\t")
        elif not character.isprintable():
            codepoint = ord(character)
            if codepoint <= 0xFF:
                escaped.append(f"\\x{codepoint:02x}")
            else:
                escaped.append(f"\\u{codepoint:04x}")
        else:
            escaped.append(character)
    return "".join(escaped)


def format_table(entries, limit=None):
    """Format entries as an aligned table containing metadata only."""
    entries = _select_entries(entries, limit)
    if not entries:
        return "No entries found."

    headers = ("Timestamp", "Tool", "Secret", "Reason")
    rows = [
        [_table_value(_public_entry(entry)[field]) for field in PUBLIC_FIELDS]
        for entry in entries
    ]
    widths = [
        max(len(header), *(len(row[index]) for row in rows))
        for index, header in enumerate(headers)
    ]

    header = " ".join(f"{label:<{width}}" for label, width in zip(headers, widths))
    separator = "-" * (sum(widths) + len(widths) - 1)
    lines = [header, separator]
    lines.extend(
        " ".join(f"{value:<{width}}" for value, width in zip(row, widths))
        for row in rows
    )
    return "\n".join(lines)


def format_json(entries, limit=None):
    """Format selected entries as JSON containing metadata only."""
    selected = _select_entries(entries, limit)
    return json.dumps([_public_entry(entry) for entry in selected], indent=2)


def _non_negative_int(value):
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("limit must be a non-negative integer") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("limit must be a non-negative integer")
    return number


def build_parser():
    parser = argparse.ArgumentParser(description="Read and display a secret audit trail.")
    parser.add_argument("log_path", help="Path to the audit log file")
    parser.add_argument(
        "--format", choices=["table", "json"], default="table",
        help="Output format (default: table)",
    )
    parser.add_argument(
        "--filter", help="Case-insensitive substring in tool, secret, or reason"
    )
    parser.add_argument(
        "--limit", type=_non_negative_int,
        help="Show only the last N entries (zero shows none)",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    try:
        entries = filter_entries(load_log(args.log_path), args.filter)
        if args.format == "json":
            output = format_json(entries, args.limit)
        else:
            output = format_table(entries, args.limit)
    except AuditLogError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
