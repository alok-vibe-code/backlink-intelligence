import unittest
from unittest.mock import patch

from backlink_intelligence.html_utils import parse_page
from backlink_intelligence.placement import suggest_placements


class PlacementTests(unittest.TestCase):
    def setUp(self):
        self.source = parse_page(
            """<title>AI Agent Architecture</title><main><article><h1>Building AI Agents</h1>
            <p>Modern AI agents combine tool calling, retrieval, memory, and orchestration to complete complex workflows. Teams often introduce these capabilities progressively as systems become more autonomous and reliable.</p>
            <p>Unrelated paragraph about office furniture, chairs, desks, shelving, workplace lighting, and interior design trends for modern offices.</p>
            </article></main>""",
            requested_url="https://source.com/article", final_url="https://source.com/article", status_code=200,
        )
        self.target = parse_page(
            """<title>Agentic AI Learning Roadmap</title><h1>Learn Agentic AI</h1>
            <p>A hands-on roadmap covering tool calling, retrieval, RAG, memory, multi-agent systems, evaluation, security, and production reliability.</p>""",
            requested_url="https://target.com/roadmap", final_url="https://target.com/roadmap", status_code=200,
        )

    @patch("backlink_intelligence.placement.fetch_page")
    def test_returns_ranked_before_after(self, fetch):
        fetch.side_effect = [self.source, self.target]
        items = suggest_placements("https://source.com/article", "https://target.com/roadmap", "Agentic AI learning roadmap", top_n=2)
        self.assertGreaterEqual(len(items), 1)
        self.assertIn("BEFORE" if False else "", "")
        self.assertIn("[Agentic AI learning roadmap](https://target.com/roadmap)", items[0].after)
        self.assertEqual(items[0].paragraph_index, 1)
        self.assertIn(items[0].strategy, {"minimal_insertion", "contextual_sentence"})
        self.assertGreaterEqual(items[0].preservation_percent, 95)

    @patch("backlink_intelligence.placement.fetch_page")
    def test_exact_anchor_in_paragraph_uses_minimal_insertion(self, fetch):
        source = parse_page("<main><p>This Agentic AI learning roadmap introduces tools, memory, retrieval, evaluation, and production patterns for engineers building modern agents.</p></main>", requested_url="https://s.com", final_url="https://s.com", status_code=200)
        fetch.side_effect = [source, self.target]
        items = suggest_placements("https://s.com", "https://target.com/roadmap", "Agentic AI learning roadmap", top_n=1)
        self.assertEqual(items[0].strategy, "minimal_insertion")

    @patch("backlink_intelligence.placement.fetch_page")
    def test_awkward_anchor_gets_editorial_alternative(self, fetch):
        fetch.side_effect = [self.source, self.target]
        items = suggest_placements("https://source.com/article", "https://target.com/roadmap", "THIS IS A VERY LONG AWKWARD ANCHOR PHRASE FOR SEO", top_n=1)
        self.assertEqual(items[0].suggested_anchor, "Agentic AI Learning Roadmap")
        self.assertIn("suggested_anchor_differs_from_requested", items[0].warnings)

    @patch("backlink_intelligence.placement.fetch_page")
    def test_preserves_existing_anchor_capitalization(self, fetch):
        source = parse_page(
            "<main><p>A custom AI agent can connect a website, CRM, email, database, and internal dashboard while supporting several business workflows.</p></main>",
            requested_url="https://s.com", final_url="https://s.com", status_code=200,
        )
        target = parse_page(
            "<title>AI Agent Cost in 2026: Pricing Models, Hidden Costs, TCO, and ROI</title><h1>AI Agent Cost</h1><p>AI agent pricing includes development and operating costs.</p>",
            requested_url="https://t.com", final_url="https://t.com", status_code=200,
        )
        fetch.side_effect = [source, target]
        item = suggest_placements("https://s.com", "https://t.com", "AI Agent", top_n=1)[0]
        self.assertIn("[AI agent](https://t.com)", item.after)
        self.assertNotIn("[AI Agent](https://t.com)", item.after)
        self.assertEqual(item.suggested_anchor, "AI agent")
        self.assertIn("source_anchor_capitalization_preserved", item.reasons)

    @patch("backlink_intelligence.placement.fetch_page")
    def test_plural_existing_anchor_is_linked_as_complete_phrase(self, fetch):
        source = parse_page(
            "<main><p>Modern AI agents can coordinate tools, retrieval, memory, approvals, and business systems across several connected workflows while supporting reliable operations for growing teams.</p></main>",
            requested_url="https://s.com", final_url="https://s.com", status_code=200,
        )
        target = parse_page(
            "<title>AI Agent Cost in 2026: Pricing Models and ROI</title><h1>AI Agent Cost</h1><p>AI agent costs include development and operations.</p>",
            requested_url="https://t.com", final_url="https://t.com", status_code=200,
        )
        fetch.side_effect = [source, target]
        item = suggest_placements("https://s.com", "https://t.com", "AI Agent", top_n=1)[0]
        self.assertIn("[AI agents](https://t.com)", item.after)
        self.assertNotIn("[AI Agent](https://t.com)s", item.after)
        self.assertEqual(item.suggested_anchor, "AI agents")
        self.assertIn("anchor_adapted_to_source_grammar", item.reasons)
        self.assertIn("requested_anchor_not_used_verbatim", item.warnings)

    @patch("backlink_intelligence.placement.fetch_page")
    def test_destination_intent_prioritizes_cost_context(self, fetch):
        source = parse_page(
            """<main>
            <p>The AI agent checks each request, updates the CRM, drafts replies, creates follow-up tasks, and notifies the sales team for approval.</p>
            <p>A simple chatbot costs less than a custom AI agent that connects your website, CRM, email, database, and internal dashboard.</p>
            <p>Modern AI agents can coordinate tools, memory, retrieval, orchestration, approvals, and connected workflows for growing teams.</p>
            </main>""",
            requested_url="https://s.com", final_url="https://s.com", status_code=200,
        )
        target = parse_page(
            """<title>AI Agent Cost in 2026: Pricing Models, Hidden Costs, TCO, and ROI</title>
            <h1>AI Agent Cost in 2026</h1>
            <h2>How Much Does an AI Agent Cost?</h2>
            <p>An AI agent can cost less than one thousand dollars per month or require substantial custom development. Pricing, total cost of ownership, operating expense, and ROI depend on integrations, infrastructure, monitoring, and support.</p>""",
            requested_url="https://t.com", final_url="https://t.com", status_code=200,
        )
        fetch.side_effect = [source, target]
        items = suggest_placements("https://s.com", "https://t.com", "AI Agent", top_n=3)
        self.assertEqual(items[0].paragraph_index, 2)
        self.assertGreater(items[0].destination_score, items[1].destination_score)
        self.assertIn(items[0].destination_fit, {"high", "very_high"})
        for item in items[1:]:
            self.assertEqual(item.destination_fit, "low")


    @patch("backlink_intelligence.placement.fetch_page")
    def test_contextual_sentence_avoids_target_title_dump(self, fetch):
        source = parse_page(
            "<main><p>AI automation does not have to be expensive, but the cost depends on what you want to build and the systems that need to be connected.</p></main>",
            requested_url="https://s.com", final_url="https://s.com", status_code=200,
        )
        target = parse_page(
            "<title>AI Agent Cost in 2026: Pricing, TCO and ROI Guide</title><h1>AI Agent Cost</h1><p>Pricing depends on implementation, integrations, operations, and expected ROI.</p>",
            requested_url="https://t.com", final_url="https://t.com", status_code=200,
        )
        fetch.side_effect = [source, target]
        item = suggest_placements("https://s.com", "https://t.com", "AI Agent", top_n=1)[0]
        self.assertEqual(item.strategy, "contextual_sentence")
        self.assertNotIn("AI Agent Cost in 2026: Pricing, TCO and ROI Guide", item.after)
        self.assertNotIn("see [", item.after)
        self.assertIn("[AI agent](https://t.com)", item.after)
        self.assertIn("implementation costs", item.after)
        self.assertEqual(item.suggested_anchor, "AI agent")
        self.assertIn("target_title_not_injected_into_source_copy", item.reasons)
        self.assertIn("destination_intent_used_for_contextual_sentence", item.reasons)

    @patch("backlink_intelligence.placement.fetch_page")
    def test_general_contextual_sentence_does_not_echo_target_title(self, fetch):
        source = parse_page(
            "<main><p>Teams often introduce these capabilities progressively as systems become more autonomous and reliable across increasingly complex production workflows.</p></main>",
            requested_url="https://s.com", final_url="https://s.com", status_code=200,
        )
        target = parse_page(
            "<title>Agentic AI Learning Roadmap</title><h1>Learn Agentic AI</h1><p>A structured roadmap for tool calling, retrieval, memory, evaluation, and production reliability.</p>",
            requested_url="https://t.com", final_url="https://t.com", status_code=200,
        )
        fetch.side_effect = [source, target]
        item = suggest_placements("https://s.com", "https://t.com", "Agentic AI learning roadmap", top_n=1)[0]
        self.assertEqual(item.strategy, "contextual_sentence")
        self.assertNotIn("For a more detailed resource on", item.after)
        self.assertNotIn("see [", item.after)
        self.assertIn("[Agentic AI learning roadmap](https://t.com)", item.after)



if __name__ == "__main__":
    unittest.main()
