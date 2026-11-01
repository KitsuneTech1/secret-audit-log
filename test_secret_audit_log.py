#!/usr/bin/env python3
"""Tests for secret_audit_log."""

import unittest
import json
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO

# Import the module
import secret_audit_log


class TestSecretAuditLog(unittest.TestCase):
    """Test secret_audit_log functionality."""

    def setUp(self):
        """Create a sample log file."""
        self.sample_data = [
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
            },
            {
                "timestamp": "2026-10-31T10:10:00",
                "tool": "my-app",
                "secret": "db_password",
                "reason": "reconnect after timeout"
            }
        ]

        self.log_path = Path(__file__).with_name('.secret-audit-log-test.json')

        with self.log_path.open('w', encoding='utf-8') as f:
            json.dump(self.sample_data, f)

    def tearDown(self):
        self.log_path.unlink(missing_ok=True)

    def write_log(self, data):
        with self.log_path.open('w', encoding='utf-8') as f:
            json.dump(data, f)

    def test_load_log(self):
        """Test loading a log file."""
        data = secret_audit_log.load_log(self.log_path)
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]['tool'], 'my-app')

    def test_load_enveloped_log(self):
        """Test loading the supported entries object envelope."""
        self.write_log({'entries': self.sample_data})

        self.assertEqual(secret_audit_log.load_log(self.log_path), self.sample_data)

    def test_load_json_lines_log(self):
        """Test loading one JSON object per line."""
        with self.log_path.open('w', encoding='utf-8') as f:
            f.write('\n'.join(json.dumps(entry) for entry in self.sample_data))
            f.write('\n\n')

        self.assertEqual(secret_audit_log.load_log(self.log_path), self.sample_data)

    def test_load_accepts_utf8_bom(self):
        """Accept JSON files written with a UTF-8 byte-order mark."""
        self.log_path.write_text(
            json.dumps(self.sample_data), encoding='utf-8-sig'
        )

        self.assertEqual(secret_audit_log.load_log(self.log_path), self.sample_data)

    def test_load_rejects_invalid_shape(self):
        """Reject a JSON value that cannot contain audit entries."""
        self.write_log({'unexpected': []})

        with self.assertRaises(secret_audit_log.AuditLogError):
            secret_audit_log.load_log(self.log_path)

    def test_load_rejects_missing_metadata(self):
        """Reject entries without all required metadata fields."""
        invalid_entry = dict(self.sample_data[0])
        del invalid_entry['reason']
        self.write_log([invalid_entry])

        with self.assertRaises(secret_audit_log.AuditLogError):
            secret_audit_log.load_log(self.log_path)

    def test_load_rejects_invalid_timestamp(self):
        """Reject entries whose timestamp is not ISO 8601."""
        invalid_entry = dict(self.sample_data[0])
        invalid_entry['timestamp'] = 'not-a-timestamp'
        self.write_log([invalid_entry])

        with self.assertRaises(secret_audit_log.AuditLogError):
            secret_audit_log.load_log(self.log_path)

    def test_filter_by_tool(self):
        """Test filtering by tool name."""
        entries = secret_audit_log.load_log(self.log_path)
        filtered = secret_audit_log.filter_entries(entries, 'my-app')
        self.assertEqual(len(filtered), 2)
        self.assertTrue(all(e['tool'] == 'my-app' for e in filtered))

    def test_filter_by_secret(self):
        """Test filtering by secret name."""
        entries = secret_audit_log.load_log(self.log_path)
        filtered = secret_audit_log.filter_entries(entries, 'api_key')
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['secret'], 'api_key')

    def test_filter_by_reason(self):
        """Test filtering by reason substring."""
        entries = secret_audit_log.load_log(self.log_path)
        filtered = secret_audit_log.filter_entries(entries, 'timeout')
        self.assertEqual(len(filtered), 1)
        self.assertIn('timeout', filtered[0]['reason'])

    def test_no_filter(self):
        """Test without filter returns all entries."""
        entries = secret_audit_log.load_log(self.log_path)
        filtered = secret_audit_log.filter_entries(entries, None)
        self.assertEqual(len(filtered), 3)

    def test_format_table(self):
        """Test table formatting."""
        entries = secret_audit_log.load_log(self.log_path)
        table = secret_audit_log.format_table(entries)

        # Check that required fields appear in output
        self.assertIn('Timestamp', table)
        self.assertIn('Tool', table)
        self.assertIn('Secret', table)
        self.assertIn('Reason', table)
        self.assertIn('my-app', table)
        self.assertIn('db_password', table)

    def test_format_json(self):
        """Test JSON formatting."""
        entries = secret_audit_log.load_log(self.log_path)
        json_str = secret_audit_log.format_json(entries)

        # Parse to verify it's valid JSON
        parsed = json.loads(json_str)
        self.assertEqual(len(parsed), 3)
        self.assertEqual(parsed[0]['tool'], 'my-app')

    def test_format_json_omits_untrusted_extra_fields(self):
        """JSON output contains metadata only, never arbitrary input fields."""
        entry = dict(self.sample_data[0])
        entry['value'] = 'must-not-be-printed'
        entry['internal'] = {'anything': 'else'}

        parsed = json.loads(secret_audit_log.format_json([entry]))

        self.assertEqual(parsed, [{
            'timestamp': entry['timestamp'],
            'tool': entry['tool'],
            'secret': entry['secret'],
            'reason': entry['reason'],
        }])
        self.assertNotIn('must-not-be-printed', secret_audit_log.format_json([entry]))

    def test_limit(self):
        """Test limiting output to last N entries."""
        entries = secret_audit_log.load_log(self.log_path)
        limited = secret_audit_log.format_table(entries, limit=1)

        # Should contain only the last entry
        self.assertIn('reconnect', limited)
        # Count occurrences of the timestamp - last entry should be there
        self.assertIn('10:10:00', limited)

    def test_zero_limit_returns_no_entries(self):
        """A zero limit should select zero entries."""
        entries = secret_audit_log.load_log(self.log_path)

        self.assertEqual(secret_audit_log.format_json(entries, limit=0), '[]')
        self.assertEqual(secret_audit_log.format_table(entries, limit=0), 'No entries found.')

    def test_negative_limit_is_rejected(self):
        """Negative limits are invalid instead of slicing from the wrong side."""
        with self.assertRaises(ValueError):
            secret_audit_log.format_json(self.sample_data, limit=-1)

    def test_table_keeps_full_timestamp(self):
        """Table output must not silently discard timezone information."""
        entry = dict(self.sample_data[0])
        entry['timestamp'] = '2026-10-31T10:00:00+00:00'

        self.assertIn(entry['timestamp'], secret_audit_log.format_table([entry]))

    def test_table_handles_direct_non_string_metadata(self):
        """Table formatting does not crash when called with non-string metadata."""
        entry = dict(self.sample_data[0])
        entry['tool'] = 42

        self.assertIn('42', secret_audit_log.format_table([entry]))

    def test_table_escapes_multiline_metadata(self):
        """Multiline fields stay on one table row."""
        entry = dict(self.sample_data[0])
        entry['reason'] = 'first line\nsecond line'

        table = secret_audit_log.format_table([entry])

        self.assertIn('first line\\nsecond line', table)
        self.assertEqual(table.count('\n'), 2)

    def test_table_escapes_terminal_control_characters(self):
        """Table output cannot emit terminal control sequences from metadata."""
        entry = dict(self.sample_data[0])
        entry['tool'] = 'app\x1b[31m\x00'

        table = secret_audit_log.format_table([entry])

        self.assertIn(r'app\x1b[31m\x00', table)
        self.assertNotIn('\x1b', table)
        self.assertNotIn('\x00', table)

    def test_main_reports_missing_file_without_traceback(self):
        """CLI errors are concise and returned as a nonzero status."""
        stdout = StringIO()
        stderr = StringIO()
        missing_path = self.log_path.with_name('missing.log')

        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = secret_audit_log.main([str(missing_path)])

        self.assertEqual(result, 1)
        self.assertEqual(stdout.getvalue(), '')
        self.assertIn('Log file not found', stderr.getvalue())
        self.assertNotIn('Traceback', stderr.getvalue())

    def test_main_prints_filtered_json(self):
        """CLI success combines filtering, JSON output, and limiting."""
        stdout = StringIO()

        with redirect_stdout(stdout):
            result = secret_audit_log.main([
                str(self.log_path), '--format', 'json', '--filter', 'timeout', '--limit', '1'
            ])

        self.assertEqual(result, 0)
        self.assertEqual(json.loads(stdout.getvalue()), [self.sample_data[2]])

    def test_main_rejects_negative_limit(self):
        """CLI rejects negative limits with argparse status 2."""
        stderr = StringIO()

        with redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
            secret_audit_log.main([str(self.log_path), '--limit', '-1'])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn('non-negative integer', stderr.getvalue())


if __name__ == '__main__':
    unittest.main()
