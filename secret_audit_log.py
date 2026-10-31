#!/usr/bin/env python3
"""Read and display a secret audit trail without printing secrets."""

import json
import sys
from datetime import datetime
from argparse import ArgumentParser
from pathlib import Path


def load_log(log_path):
    """Load JSON log file. Return list of entries."""
    try:
        with open(log_path, 'r') as f:
            data = json.load(f)
        # Support both direct list and {entries: []} format
        if isinstance(data, dict):
            return data.get('entries', [])
        return data if isinstance(data, list) else []
    except FileNotFoundError:
        print(f"Error: Log file not found: {log_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {log_path}: {e}", file=sys.stderr)
        sys.exit(1)


def filter_entries(entries, filter_str):
    """Filter entries by substring match in tool, secret, or reason."""
    if not filter_str:
        return entries
    filter_lower = filter_str.lower()
    return [
        e for e in entries
        if (filter_lower in str(e.get('tool', '')).lower() or
            filter_lower in str(e.get('secret', '')).lower() or
            filter_lower in str(e.get('reason', '')).lower())
    ]


def format_table(entries, limit=None):
    """Format entries as aligned table."""
    if limit:
        entries = entries[-limit:]

    if not entries:
        return "No entries found."

    # Calculate column widths
    max_time = max(len(e.get('timestamp', '')[:19]) for e in entries) if entries else 19
    max_tool = max(len(e.get('tool', '')) for e in entries) if entries else 10
    max_secret = max(len(e.get('secret', '')) for e in entries) if entries else 10
    max_reason = max(len(e.get('reason', '')) for e in entries) if entries else 15

    max_time = max(max_time, 19)
    max_tool = max(max_tool, 10)
    max_secret = max(max_secret, 10)
    max_reason = max(max_reason, 15)

    # Header
    header = f"{'Timestamp':<{max_time}} {'Tool':<{max_tool}} {'Secret':<{max_secret}} {'Reason':<{max_reason}}"
    lines = [header, '-' * (max_time + max_tool + max_secret + max_reason + 3)]

    # Rows
    for entry in entries:
        ts = str(entry.get('timestamp', ''))[:19]
        tool = str(entry.get('tool', ''))[:max_tool]
        secret = str(entry.get('secret', ''))[:max_secret]
        reason = str(entry.get('reason', ''))[:max_reason]
        lines.append(f"{ts:<{max_time}} {tool:<{max_tool}} {secret:<{max_secret}} {reason:<{max_reason}}")

    return '\n'.join(lines)


def format_json(entries, limit=None):
    """Format entries as JSON."""
    if limit:
        entries = entries[-limit:]
    return json.dumps(entries, indent=2)


def main():
    parser = ArgumentParser(description='Read and display a secret audit trail.')
    parser.add_argument('log_path', help='Path to the audit log JSON file')
    parser.add_argument('--format', choices=['table', 'json'], default='table',
                        help='Output format (default: table)')
    parser.add_argument('--filter', help='Filter by substring in tool, secret, or reason')
    parser.add_argument('--limit', type=int, help='Show only last N entries')

    args = parser.parse_args()

    entries = load_log(args.log_path)
    entries = filter_entries(entries, args.filter)

    if args.format == 'json':
        output = format_json(entries, args.limit)
    else:
        output = format_table(entries, args.limit)

    print(output)


if __name__ == '__main__':
    main()
