import unittest
from unittest.mock import patch

from backlink_intelligence.analysis import AnalysisConfig, PlacementAnalyzer
from backlink_intelligence.fetcher import FetchConfig
from backlink_intelligence.html_utils import parse_page


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.source = parse_page(
            "<main><p>A custom AI agent connects a website, CRM, email, database, and internal dashboard while supporting reliable business automation workflows.</p></main>",
            requested_url="https://source.example/article/",
            final_url="https://source.example/article/",
            status_code=200,
        )
        self.target = parse_page(
            "<title>AI Agent Cost and ROI</title><h1>AI Agent Cost</h1><p>Implementation pricing, integrations, operating costs, and ROI vary by project.</p>",
            requested_url="https://target.example/guide/",
            final_url="https://target.example/guide/",
            status_code=200,
        )

    @patch("backlink_intelligence.analysis.fetch_page")
    def test_completed_analysis_uses_structured_segments(self, fetch_page):
        fetch_page.side_effect = [self.source, self.target]
        analyzer = PlacementAnalyzer(
            AnalysisConfig(0.0, 0.0, 3, FetchConfig(respect_robots=False))
        )
        result = analyzer.analyze(
            "https://source.example/article/",
            "https://target.example/guide/",
            "AI Agent",
        )
        self.assertEqual(result.status, "completed")
        item = result.opportunities[0]
        self.assertEqual(sum(segment.type == "link" for segment in item.after_segments), 1)
        self.assertEqual("".join(segment.text for segment in item.after_segments), item.after_text)
        self.assertEqual(
            next(segment.url for segment in item.after_segments if segment.type == "link"),
            "https://target.example/guide/",
        )

    @patch("backlink_intelligence.analysis.fetch_page")
    def test_no_suitable_placement_is_successful_outcome(self, fetch_page):
        fetch_page.side_effect = [self.source, self.target]
        analyzer = PlacementAnalyzer(AnalysisConfig(1.0, 1.0, 3))
        result = analyzer.analyze(
            "https://source.example/article/",
            "https://target.example/guide/",
            "AI Agent",
        )
        self.assertEqual(result.status, "no_suitable_placement")
        self.assertEqual(result.opportunities, [])


if __name__ == "__main__":
    unittest.main()
