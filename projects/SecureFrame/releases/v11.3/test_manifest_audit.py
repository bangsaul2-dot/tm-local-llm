"""Synthetic metadata audit tests."""
import unittest
from manifest_audit import audit

class ManifestAuditTests(unittest.TestCase):
    def test_duplicate_metadata(self):
        item = {"topic":"Public example","source":{"name":"sample","page":1}}
        result = audit({"records":[item, item]})
        self.assertEqual(result["record_count"], 2)
        self.assertEqual(result["duplicate_source_reference_count"], 1)
        self.assertEqual(result["unverified_records"], 2)

if __name__ == "__main__":
    unittest.main()
