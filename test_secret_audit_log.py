#!/usr/bin/env python3
"""Tests for secret_audit_log."""

import unittest
import json
import tempfile
from pathlib import Path
from io import StringIO
import sys

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

        self.temp_dir = tempfile.mkdtemp()
        self.log_path = Path(self.temp_dir) / "test.log"

        with open(self.log_path, 'w') as f:
            json.dump(self.sample_data, f)

    def test_load_log(self):
        """Test loading a log file."""
        data = secret_audit_log.load_log(self.log_path)
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]['tool'], 'my-app')

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

    def test_limit(self):
        """Test limiting output to last N entries."""
        entries = secret_audit_log.load_log(self.log_path)
        limited = secret_audit_log.format_table(entries, limit=1)

        # Should contain only the last entry
        self.assertIn('reconnect', limited)
        # Count occurrences of the timestamp - last entry should be there
        self.assertIn('10:10:00', limited)


if __name__ == '__main__':
    unittest.main()
