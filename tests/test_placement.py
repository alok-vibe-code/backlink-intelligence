import unittest
from unittest.mock import patch

from backlink_intelligence.html_utils import parse_page
from backlink_intelligence.placement import _anchor_with_article, rank_placements, suggest_placements


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

    def test_finance_course_anchor_is_integrated_into_one_supported_sentence(self):
        source = parse_page(
            """<main><p>Financial Agents now perform Continuous Accounting. Instead of waiting for month-end, agents monitor every transaction in real time across global entities.</p></main>""",
            requested_url="https://s.com/finance", final_url="https://s.com/finance", status_code=200,
        )
        target = parse_page(
            """<title>AI and Agentic AI in Finance Course</title><h1>AI in Finance Course</h1>
            <p>Learn how financial agents support continuous accounting, transaction monitoring, and practical AI applications in global finance operations.</p>""",
            requested_url="https://t.com/course", final_url="https://t.com/course", status_code=200,
        )
        item = rank_placements(source, target, "ai in finance course", "https://t.com/course", top_n=1)[0]

        expected = (
            "Financial Agents now perform Continuous Accounting, one of the practical "
            "applications professionals can examine more deeply through an ai in finance course. "
            "Instead of waiting for month-end, agents monitor every transaction in real time across global entities."
        )
        self.assertEqual(item.after_text, expected)
        self.assertEqual(item.strategy, "contextual_sentence")
        self.assertEqual(item.intervention, "medium")
        self.assertTrue(item.review_required)
        self.assertEqual(item.recommendation_status, "manual_review")
        self.assertIn("source_sentence_lightly_rewritten", item.reasons)
        self.assertIn("publisher_meaning_preserved", item.reasons)
        self.assertNotIn("Readers who want additional context", item.after_text)

    def test_rewrite_changes_only_one_sentence_and_preserves_protected_facts(self):
        source = parse_page(
            """<main><p>In 2026, FinanceCo described the process as &quot;continuous accounting&quot; across 14 entities. Instead of waiting for month-end, agents monitor every transaction in real time across global entities.</p></main>""",
            requested_url="https://s.com/facts", final_url="https://s.com/facts", status_code=200,
        )
        target = parse_page(
            """<title>AI in Finance Course</title><h1>Practical AI Applications in Finance</h1>
            <p>The course examines continuous accounting, financial agents, transaction monitoring, and finance operations.</p>""",
            requested_url="https://t.com/course", final_url="https://t.com/course", status_code=200,
        )
        item = rank_placements(source, target, "ai in finance course", "https://t.com/course", top_n=1)[0]

        self.assertIn("2026", item.after_text)
        self.assertIn("FinanceCo", item.after_text)
        self.assertIn('"continuous accounting"', item.after_text)
        self.assertIn("14 entities", item.after_text)
        self.assertEqual(
            item.after_text.count("one of the practical applications professionals can examine more deeply"),
            1,
        )
        self.assertGreaterEqual(item.preservation_percent, 99.0)

    def test_unsupported_learning_relationship_uses_context_specific_append(self):
        source = parse_page(
            """<main><p>Teams coordinate regional logistics schedules, warehouse capacity, delivery windows, supplier communications, and inventory reviews across several operational systems.</p></main>""",
            requested_url="https://s.com/logistics", final_url="https://s.com/logistics", status_code=200,
        )
        target = parse_page(
            """<title>AI in Finance Course</title><h1>AI Education for Finance Professionals</h1>
            <p>Learn financial modeling, risk analysis, accounting automation, and investment applications.</p>""",
            requested_url="https://t.com/course", final_url="https://t.com/course", status_code=200,
        )
        item = rank_placements(source, target, "ai in finance course", "https://t.com/course", top_n=1)[0]

        self.assertTrue(item.after_text.startswith(source.paragraphs[0]))
        self.assertNotIn("source_sentence_lightly_rewritten", item.reasons)
        self.assertNotIn("Readers who want additional context", item.after_text)
        self.assertEqual(item.preservation_percent, 100.0)

    def test_segments_reconstruct_rewrite_and_contain_one_safe_link(self):
        source = parse_page(
            """<main><p>Financial agents automate accounting workflows and monitor transactions across connected business systems while helping finance teams review exceptions and maintain reliable operations.</p></main>""",
            requested_url="https://s.com", final_url="https://s.com", status_code=200,
        )
        target = parse_page(
            """<title>AI in Finance Course</title><h1>Finance AI Applications</h1><p>Study financial agents, accounting workflows, and transaction monitoring.</p>""",
            requested_url="https://t.com/course", final_url="https://t.com/course", status_code=200,
        )
        item = rank_placements(source, target, "AI in Finance Course", "https://t.com/course", top_n=1)[0]

        self.assertEqual("".join(segment.text for segment in item.after_segments), item.after_text)
        links = [segment for segment in item.after_segments if segment.type == "link"]
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].url, "https://t.com/course")
        self.assertEqual(links[0].text, "AI in finance course")

    def test_generated_anchor_articles_are_grammatical(self):
        self.assertEqual(_anchor_with_article("ai in finance course"), "an ai in finance course")
        self.assertEqual(_anchor_with_article("SEO guide"), "an SEO guide")
        self.assertEqual(_anchor_with_article("finance course"), "a finance course")
        self.assertEqual(_anchor_with_article("university course"), "a university course")

    def test_generated_rewrite_is_deterministic(self):
        source = parse_page(
            """<main><p>Financial agents support continuous accounting and transaction monitoring across complex global finance operations, connected business systems, regional teams, and carefully governed reporting workflows.</p></main>""",
            requested_url="https://s.com", final_url="https://s.com", status_code=200,
        )
        target = parse_page(
            """<title>AI in Finance Course</title><h1>AI Applications in Finance</h1><p>Study financial agents, continuous accounting, and transaction monitoring.</p>""",
            requested_url="https://t.com", final_url="https://t.com", status_code=200,
        )
        first = rank_placements(source, target, "ai in finance course", "https://t.com", top_n=1)[0]
        second = rank_placements(source, target, "ai in finance course", "https://t.com", top_n=1)[0]
        self.assertEqual(first.to_dict(), second.to_dict())



if __name__ == "__main__":
    unittest.main()
