import unittest
from unittest.mock import patch

from backlink_intelligence.html_utils import parse_page
from backlink_intelligence.qualify import qualify_prospect


class QualifyTests(unittest.TestCase):
    @patch("backlink_intelligence.qualify.fetch_page")
    def test_qualification_returns_explainable_fields(self, fetch):
        source = parse_page("<title>Data science guide</title><main><h1>Learning data science</h1><p>Data science programs combine statistics, Python, machine learning, applied AI, analytics, projects, and practical modeling skills for working professionals.</p></main>", requested_url="https://publisher.com/data", final_url="https://publisher.com/data", status_code=200)
        target = parse_page("<title>Data Science Program</title><h1>Applied data science and AI</h1><p>Learn statistics, Python, machine learning, applied AI and analytics through practical projects.</p>", requested_url="https://brand.com/program", final_url="https://brand.com/program", status_code=200)
        fetch.side_effect = [source, target]; result = qualify_prospect("https://publisher.com/data", "https://brand.com/program", "data science program"); self.assertEqual(result["source_status"], 200); self.assertIn(result["recommendation"], {"prioritize", "manual_review", "low_priority"}); self.assertIn("page_relevance", result); self.assertIn("placement_potential", result)


if __name__ == "__main__": unittest.main()
