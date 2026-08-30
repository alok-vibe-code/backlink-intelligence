import unittest
from unittest.mock import patch

from backlink_intelligence.audit import audit_backlink
from backlink_intelligence.html_utils import parse_page


class AuditTests(unittest.TestCase):
    @patch("backlink_intelligence.audit.fetch_page")
    def test_strong_editorial_candidate(self, fetch):
        source = parse_page("<title>AI agents</title><main><article><h1>AI Agent Guide</h1><p>Agentic AI systems use tool calling, memory, retrieval and evaluation. Read the <a href='https://target.com/roadmap'>Agentic AI roadmap</a> for hands-on examples and implementation patterns.</p></article></main>", requested_url="https://source.com/a", final_url="https://source.com/a", status_code=200)
        target = parse_page("<title>Agentic AI roadmap</title><h1>Build AI agents</h1><p>Learn tool calling, memory, RAG, evaluation and production agent patterns.</p>", requested_url="https://target.com/roadmap", final_url="https://target.com/roadmap", status_code=200)
        fetch.side_effect = [source, target]; result = audit_backlink("https://source.com/a", "https://target.com/roadmap")
        self.assertTrue(result.backlink.found); self.assertEqual(result.backlink.placement, "editorial_context"); self.assertIn(result.recommendation, {"strong_candidate", "manual_review"}); self.assertIn("target_link_found", result.reasons)
    @patch("backlink_intelligence.audit.fetch_page")
    def test_not_found(self, fetch):
        source = parse_page("<main><p>No target link exists on this relevant article about AI agents and tool calling.</p></main>", requested_url="https://source.com", final_url="https://source.com", status_code=200)
        target = parse_page("<p>AI agent target page with tools and memory.</p>", requested_url="https://target.com", final_url="https://target.com", status_code=200)
        fetch.side_effect = [source, target]; result = audit_backlink("https://source.com", "https://target.com"); self.assertFalse(result.backlink.found); self.assertEqual(result.recommendation, "not_found")


if __name__ == "__main__": unittest.main()
