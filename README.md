# secret-audit-log

Read a secret access trail without handling secret values.

## What it does

The command reads access metadata and prints a table or JSON. Each event records
when access was requested, which tool requested it, which secret name was used,
and why.

The output contains only these four metadata fields. The `secret` field must be
the name of the secret, not its value. This program does not fetch, resolve, or
redact values that were written into a log by mistake.

## Requirements

Python 3 and the standard library. There is no package metadata in this small
repository, so run the script directly.

```bash
python secret_audit_log.py <log_file> [options]
```

## Log format

The reader accepts a JSON array:

```json
[
  {
    "timestamp": "2026-10-31T10:00:00Z",
    "tool": "my-app",
    "secret": "db_password",
    "reason": "initialize connection"
  }
]
```

It also accepts an object containing an `entries` array, or JSON Lines with one
event object per line. Blank JSON Lines are ignored.

Every event must contain non-empty string values for `timestamp`, `tool`,
`secret`, and `reason`. Timestamps must be ISO 8601 values. Invalid files are
reported on stderr and do not produce partial output. Files larger than 16 MiB
are rejected before parsing.

## Usage

Show all events as a table:

```bash
python secret_audit_log.py audit.log
```

Select JSON output:

```bash
python secret_audit_log.py audit.log --format json
```

Filter with a case-insensitive substring. The filter searches the tool, secret
name, and reason fields:

```bash
python secret_audit_log.py audit.log --filter timeout
```

Show only the last 10 events:

```bash
python secret_audit_log.py audit.log --limit 10
```

`--limit 0` shows no events. Negative limits are rejected.

The command exits with status 0 on success and status 1 when the file cannot be
read or does not match the log format. Argument errors use the normal argparse
status 2.

## Testing

```bash
python -m unittest -v
```

The tests use local temporary files only. They do not make network requests.

## License

MIT License

Copyright (c) 2026 KitsuneTech1
