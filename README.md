# secret-audit-log

Read and display a secret audit trail without printing secret values.

## What it does

When tools request secrets during execution, they should log access metadata: timestamp, tool name, secret name, and reason for access. This tool reads that log and displays the audit trail as a table or JSON, filtering by tool, secret, or reason substring.

The secret values themselves are never printed, only access metadata.

## Installation

```bash
pip install -e .
```

Or run directly:

```bash
python secret_audit_log.py <log_file> [options]
```

## Usage

### Basic usage

Display all audit entries as a table:

```bash
python secret_audit_log.py audit.log
```

### Output formats

Table (default):

```bash
python secret_audit_log.py audit.log --format table
```

JSON:

```bash
python secret_audit_log.py audit.log --format json
```

### Filtering

Filter by tool name:

```bash
python secret_audit_log.py audit.log --filter my-app
```

Filter by secret name:

```bash
python secret_audit_log.py audit.log --filter db_password
```

Filter by reason (substring):

```bash
python secret_audit_log.py audit.log --filter timeout
```

### Limiting output

Show only the last 10 entries:

```bash
python secret_audit_log.py audit.log --limit 10
```

Combine filters and limits:

```bash
python secret_audit_log.py audit.log --filter my-app --limit 5 --format json
```

## Log format

The audit log is a JSON file containing an array of entries:

```json
[
  {
    "timestamp": "2026-10-31T10:00:00",
    "tool": "my-app",
    "secret": "db_password",
    "reason": "initialize connection"
  },
  {
    "timestamp": "2026-10-31T10:05:00",
    "tool": "another-tool",
    "secret": "api_key",
    "reason": "external service call"
  }
]
```

Each entry must have:
- timestamp: ISO 8601 format
- tool: name of the tool requesting the secret
- secret: name of the secret (not its value)
- reason: human-readable reason for the request

## Testing

```bash
python -m unittest test_secret_audit_log
```

## License

MIT License

Copyright (c) 2026 KitsuneTech1
