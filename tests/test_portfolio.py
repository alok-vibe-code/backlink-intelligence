import csv
import tempfile
import unittest
from pathlib import Path

from backlink_intelligence.portfolio import analyze_portfolio, classify_anchor


class PortfolioTests(unittest.TestCase):
    def test_anchor_classification(self):
        self.assertEqual(classify_anchor("https://example.com/page", "https://example.com/page"), "naked_url"); self.assertEqual(classify_anchor("click here", "https://example.com/page"), "generic"); self.assertEqual(classify_anchor("Example guide", "https://example.com/page"), "branded")
    def test_portfolio_distribution(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "links.csv"
            with path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["target_url", "anchor", "placement"]); writer.writeheader(); writer.writerow({"target_url": "https://a.com/x", "anchor": "click here", "placement": "editorial_context"}); writer.writerow({"target_url": "https://a.com/x", "anchor": "https://a.com/x", "placement": "footer"})
            result = analyze_portfolio(path); self.assertEqual(result["total_links"], 2); self.assertEqual(result["destination_distribution"]["https://a.com/x"], 2)


if __name__ == "__main__": unittest.main()
