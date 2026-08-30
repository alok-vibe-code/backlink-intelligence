import io
import unittest
from contextlib import redirect_stdout

from backlink_intelligence import __version__
from backlink_intelligence.cli import main


class CLITests(unittest.TestCase):
    def test_version_is_stable(self):
        self.assertEqual(__version__, "1.1.0")

    def test_status_command(self):
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["status"])
        self.assertEqual(exit_code, 0)
        self.assertIn("audit, qualify, place, monitor, portfolio", output.getvalue())

    def test_root_help_returns_success(self):
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main([])
        self.assertEqual(exit_code, 0)
        self.assertIn("Evidence-first backlink intelligence", output.getvalue())


if __name__ == "__main__":
    unittest.main()
