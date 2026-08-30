import unittest
from unittest.mock import patch

from backlink_intelligence.html_utils import parse_page
from backlink_intelligence.placement import suggest_placements


class PlacementTests(unittest.TestCase):
    def setUp(self):
        self.source = parse_page("""<title>AI Agent Architecture</title><main><article><h1>Building AI Agents</h1><p>Modern AI agents combine tool calling, retrieval, memory, and orchestration to complete complex workflows. Teams often introduce these capabilities progressively as systems become more autonomous and reliable.</p><p>Unrelated paragraph about office furniture, chairs, desks, shelving, workplace lighting, and interior design trends for modern offices.</p></article></main>""", requested_url="https://source.com/article", final_url="https://source.com/article", status_code=200)
        self.target = parse_page("""<title>Agentic AI Learning Roadmap</title><h1>Learn Agentic AI</h1><p>A hands-on roadmap covering tool calling, retrieval, RAG, memory, multi-agent systems, evaluation, security, and production reliability.</p>""", requested_url="https://target.com/roadmap", final_url="https://target.com/roadmap", status_code=200)
    @patch("backlink_intelligence.placement.fetch_page")
    def test_returns_ranked_before_after(self, fetch):
        fetch.side_effect = [self.source, self.target]; items = suggest_placements("https://source.com/article", "https://target.com/roadmap", "Agentic AI learning roadmap", top_n=2); self.assertGreaterEqual(len(items), 1); self.assertIn("[Agentic AI learning roadmap](https://target.com/roadmap)", items[0].after); self.assertEqual(items[0].paragraph_index, 1); self.assertIn(items[0].strategy, {"minimal_insertion", "contextual_sentence"}); self.assertGreaterEqual(items[0].preservation_percent, 95)
    @patch("backlink_intelligence.placement.fetch_page")
    def test_exact_anchor_in_paragraph_uses_minimal_insertion(self, fetch):
        source = parse_page("<main><p>This Agentic AI learning roadmap introduces tools, memory, retrieval, evaluation, and production patterns for engineers building modern agents.</p></main>", requested_url="https://s.com", final_url="https://s.com", status_code=200); fetch.side_effect = [source, self.target]; items = suggest_placements("https://s.com", "https://target.com/roadmap", "Agentic AI learning roadmap", top_n=1); self.assertEqual(items[0].strategy, "minimal_insertion")
    @patch("backlink_intelligence.placement.fetch_page")
    def test_awkward_anchor_gets_editorial_alternative(self, fetch):
        fetch.side_effect = [self.source, self.target]; items = suggest_placements("https://source.com/article", "https://target.com/roadmap", "THIS IS A VERY LONG AWKWARD ANCHOR PHRASE FOR SEO", top_n=1); self.assertEqual(items[0].suggested_anchor, "Agentic AI Learning Roadmap"); self.assertIn("suggested_anchor_differs_from_requested", items[0].warnings)


if __name__ == "__main__": unittest.main()
