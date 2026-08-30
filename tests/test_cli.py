import io
import unittest
from contextlib import redirect_stdout

from backlink_intelligence import __version__
from backlink_intelligence.cli import main


class FoundationTests(unittest.TestCase):
    def test_version_is_pre_alpha_foundation(self):
        self.assertEqual(__version__, "0.0.1")

    def test_status_command(self):
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["status"])
        self.assertEqual(exit_code, 0)
        self.assertIn("v0.1.0 Backlink Evidence Auditor", output.getvalue())
        self.assertIn("Discover -> Qualify -> Place -> Monitor", output.getvalue())

    def test_root_help_returns_success(self):
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main([])
        self.assertEqual(exit_code, 0)
        self.assertIn("Evidence-first backlink intelligence", output.getvalue())


if __name__ == "__main__":
    unittest.main()
