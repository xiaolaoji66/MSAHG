from __future__ import print_function

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "reproduction"
    / "audit_sthgcn_sample_materializer_v1r3_provenance.py"
)
SPEC = importlib.util.spec_from_file_location(
    "audit_sthgcn_sample_materializer_v1r3_provenance", str(MODULE_PATH)
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class V1R3GateSemanticsTest(unittest.TestCase):
    def setUp(self):
        self.forward = {name: True for name in MODULE.EXPECTED_GATES}
        self.reverse = {name: True for name in reversed(MODULE.EXPECTED_GATES)}

    def test_exact_gate_set_is_order_independent(self):
        self.assertTrue(MODULE.exact_gate_map(self.forward))
        self.assertTrue(MODULE.exact_gate_map(self.reverse))
        self.assertTrue(MODULE.old_order_sensitive_gate_predicate(self.forward))
        self.assertFalse(MODULE.old_order_sensitive_gate_predicate(self.reverse))

    def test_missing_and_extra_names_fail(self):
        missing = dict(self.forward)
        missing.pop(MODULE.EXPECTED_GATES[0])
        extra = dict(self.forward)
        extra["R17_UNREGISTERED"] = True
        self.assertFalse(MODULE.exact_gate_map(missing))
        self.assertFalse(MODULE.exact_gate_map(extra))

    def test_false_and_nonboolean_values_fail(self):
        false_value = dict(self.forward)
        false_value[MODULE.EXPECTED_GATES[0]] = False
        integer_value = dict(self.forward)
        integer_value[MODULE.EXPECTED_GATES[0]] = 1
        self.assertFalse(MODULE.exact_gate_map(false_value))
        self.assertFalse(MODULE.exact_gate_map(integer_value))

    def test_duplicate_json_object_key_fails(self):
        with self.assertRaises(MODULE.DuplicateKeyError):
            MODULE.loads_json_exact('{"a":1,"a":1}')

    def test_fresh_audit_output_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            audit_output = Path(temporary) / "audit.json"
            audit_output.write_text("preserve", encoding="utf-8")
            result = MODULE.main(
                [
                    "--registry",
                    "missing",
                    "--output-root",
                    "missing",
                    "--v1-output-root",
                    "missing",
                    "--audit-output",
                    str(audit_output),
                ]
            )
            self.assertEqual(result, 2)
            self.assertEqual(audit_output.read_text(encoding="utf-8"), "preserve")

    def test_exception_emits_one_failure_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            audit_output = Path(temporary) / "audit.json"
            result = MODULE.main(
                [
                    "--registry",
                    "missing",
                    "--output-root",
                    "missing",
                    "--v1-output-root",
                    "missing",
                    "--audit-output",
                    str(audit_output),
                ]
            )
            self.assertEqual(result, 2)
            receipt = json.loads(audit_output.read_text(encoding="utf-8"))
            self.assertEqual(receipt["decision"], "FAIL")
            self.assertFalse(receipt["automatic_retry_performed"])


if __name__ == "__main__":
    unittest.main()
