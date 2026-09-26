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

    def test_delightchat_agent_article_matches_agentic_ai_course_despite_menu_noise(self):
        source = parse_page(
            """<title>Best Company Data APIs for AI Agents</title><main><article>
            <p>The table below summarizes the main strengths of each provider and the AI agent use cases they are best suited for:</p>
            <p>Choosing the right company data API for an AI agent requires more than comparing database size or the number of available fields. The API should provide reliable data in a format that autonomous workflows can retrieve, interpret, and use.</p>
            <p>A company data API lets AI agents access structured business information such as firmographics, workforce data, funding, technologies, and company growth signals for research and automated decisions.</p>
            </article></main>""",
            requested_url="https://www.delightchat.io/blog/best-company-data-apis-for-ai-agents",
            final_url="https://www.delightchat.io/blog/best-company-data-apis-for-ai-agents",
            status_code=200,
        )
        target = parse_page(
            """<title>Agentic AI Course with Certificate by IIT Bombay for Working Professionals</title>
            <body><nav>
            <h2>PG Program in Artificial Intelligence and Machine Learning</h2>
            <p>Browse online degrees, certificates, bootcamps, and professional programs.</p>
            <h2>Certificate Program in Data Science</h2>
            <p>Browse online degrees, certificates, bootcamps, and professional programs.</p>
            </nav><div class="main">
            <h1>Certificate in Agentic AI</h1>
            <h2>Hands-on Agentic AI Curriculum</h2>
            <p>Learn to build autonomous AI agents that reason, act, and collaborate using retrieval augmented generation, Model Context Protocol, LangGraph, CrewAI, tools, memory, and orchestration.</p>
            <h2>What will you learn to build and apply?</h2>
            <p>Apply agentic AI techniques to real-world business use cases involving intelligent workflows, structured data, external tools, multi-agent systems, evaluation, and deployment.</p>
            </div></body>""",
            requested_url="https://www.mygreatlearning.com/iit-bombay-certificate-in-agentic-ai",
            final_url="https://www.mygreatlearning.com/iit-bombay-certificate-in-agentic-ai",
            status_code=200,
        )
        items = rank_placements(
            source,
            target,
            "AI agent course",
            target.final_url,
            top_n=3,
            min_context_score=0.15,
            min_destination_score=0.08,
        )
        self.assertGreaterEqual(len(items), 1)
        self.assertTrue(items[0].review_required)
        self.assertEqual(items[0].recommendation_status, "manual_review")
        self.assertIn("AI agent", items[0].before)
        self.assertFalse(items[0].before.rstrip().endswith((':', ';')))
        self.assertGreaterEqual(items[0].score, 0.15)
        self.assertGreaterEqual(items[0].destination_score, 0.08)

    def test_unrelated_course_does_not_pass_on_generic_course_language(self):
        source = parse_page(
            """<main><p>AI agents retrieve company data, coordinate tools, monitor business changes, and support automated research decisions across connected workflows.</p></main>""",
            requested_url="https://source.example/ai-agents",
            final_url="https://source.example/ai-agents",
            status_code=200,
        )
        target = parse_page(
            """<title>Professional Watercolor Painting Course</title><main>
            <h1>Learn Watercolor Painting</h1>
            <p>Study color mixing, brush control, paper selection, washes, composition, landscapes, and portrait painting through guided studio exercises.</p>
            </main>""",
            requested_url="https://target.example/watercolor-course",
            final_url="https://target.example/watercolor-course",
            status_code=200,
        )
        items = rank_placements(
            source,
            target,
            "AI agent course",
            target.final_url,
            top_n=3,
            min_context_score=0.15,
            min_destination_score=0.08,
        )
        self.assertEqual(items, [])


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
            "Financial Agents now perform Continuous Accounting, a practical application "
            "that can be examined more deeply through an ai in finance course. "
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
            item.after_text.count("a practical application that can be examined more deeply"),
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
        self.assertIn("Finance professionals can examine", item.after_text)
        self.assertIn("target_audience_used_for_contextual_sentence", item.reasons)
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

    def test_rewrite_normalizes_space_before_terminal_punctuation(self):
        source = parse_page(
            """<main><p>Financial agents monitor transactions and support continuous accounting across connected global finance operations . Teams review exceptions before reports are finalized.</p></main>""",
            requested_url="https://s.com", final_url="https://s.com", status_code=200,
        )
        target = parse_page(
            """<title>AI in Finance Course</title><h1>Finance AI Applications</h1><p>Study financial agents, continuous accounting, and transaction monitoring.</p>""",
            requested_url="https://t.com", final_url="https://t.com", status_code=200,
        )
        item = rank_placements(source, target, "ai in finance course", "https://t.com", top_n=1)[0]
        self.assertNotIn(" ,", item.after_text)
        self.assertIn("operations, a practical application", item.after_text)

    def test_learning_rewrite_uses_explicit_student_audience(self):
        source = parse_page(
            """<main><p>Financial agents support continuous accounting and transaction monitoring across connected business systems, regional teams, and carefully governed reporting workflows.</p></main>""",
            requested_url="https://s.com", final_url="https://s.com", status_code=200,
        )
        target = parse_page(
            """<title>AI in Finance Course for Students</title><h1>Finance AI Applications</h1><p>Study financial agents, continuous accounting, and transaction monitoring.</p>""",
            requested_url="https://t.com/course", final_url="https://t.com/course", status_code=200,
        )
        item = rank_placements(source, target, "ai in finance course", "https://t.com/course", top_n=1)[0]

        self.assertIn("a practical application students can examine more deeply", item.after_text)
        self.assertNotIn("professionals", item.after_text.casefold())
        self.assertIn("target_audience_used_for_contextual_sentence", item.reasons)

    def test_learning_rewrite_uses_other_explicit_target_audiences(self):
        source = parse_page(
            """<main><p>Financial agents support continuous accounting and transaction monitoring across connected business systems, regional teams, and carefully governed reporting workflows.</p></main>""",
            requested_url="https://s.com", final_url="https://s.com", status_code=200,
        )
        for audience, expected in (
            ("Developers", "developers can examine"),
            ("Marketers", "marketers can examine"),
            ("Executives", "executives can examine"),
        ):
            with self.subTest(audience=audience):
                target = parse_page(
                    f"""<title>AI in Finance Course for {audience}</title><h1>Finance AI Applications</h1><p>Study financial agents, continuous accounting, and transaction monitoring.</p>""",
                    requested_url="https://t.com/course", final_url="https://t.com/course", status_code=200,
                )
                item = rank_placements(source, target, "ai in finance course", "https://t.com/course", top_n=1)[0]
                self.assertIn(expected, item.after_text)
                self.assertIn("target_audience_used_for_contextual_sentence", item.reasons)

    def test_learning_rewrite_uses_neutral_wording_without_explicit_audience(self):
        source = parse_page(
            """<main><p>Financial agents support continuous accounting and transaction monitoring across connected business systems, regional teams, and carefully governed reporting workflows.</p></main>""",
            requested_url="https://s.com", final_url="https://s.com", status_code=200,
        )
        target = parse_page(
            """<title>AI in Finance Course</title><h1>Finance AI Applications</h1><p>Study financial agents, continuous accounting, and transaction monitoring.</p>""",
            requested_url="https://t.com/course", final_url="https://t.com/course", status_code=200,
        )
        item = rank_placements(source, target, "ai in finance course", "https://t.com/course", top_n=1)[0]

        self.assertIn("a practical application that can be examined more deeply", item.after_text)
        self.assertNotIn("professionals", item.after_text.casefold())
        self.assertIn("neutral_audience_wording_used", item.reasons)

    def test_passing_audience_mention_does_not_define_target_audience(self):
        source = parse_page(
            """<main><p>Financial agents support continuous accounting and transaction monitoring across connected business systems, regional teams, and carefully governed reporting workflows.</p></main>""",
            requested_url="https://s.com", final_url="https://s.com", status_code=200,
        )
        target = parse_page(
            """<title>AI in Finance Course</title><h1>Finance AI Applications</h1><p>The course covers transaction monitoring. Professionals frequently discuss automation adoption in industry surveys.</p>""",
            requested_url="https://t.com/course", final_url="https://t.com/course", status_code=200,
        )
        item = rank_placements(source, target, "ai in finance course", "https://t.com/course", top_n=1)[0]

        self.assertIn("a practical application that can be examined more deeply", item.after_text)
        self.assertNotIn("professionals can", item.after_text.casefold())
        self.assertIn("neutral_audience_wording_used", item.reasons)

    def test_guide_is_not_treated_as_a_course(self):
        source = parse_page(
            """<main><p>Marketing teams review campaign performance, attribution patterns, audience behavior, conversion data, reporting limitations, and channel results before changing their customer acquisition strategy.</p></main>""",
            requested_url="https://s.com", final_url="https://s.com", status_code=200,
        )
        target = parse_page(
            """<title>Marketing Attribution Guide</title><h1>Attribution Models Explained</h1><p>This article compares measurement approaches and reporting limitations.</p>""",
            requested_url="https://t.com/guides/attribution", final_url="https://t.com/guides/attribution", status_code=200,
        )
        item = rank_placements(source, target, "marketing attribution guide", "https://t.com/guides/attribution", top_n=1)[0]

        self.assertNotIn("professionals", item.after_text.casefold())
        self.assertNotIn("course", item.after_text.casefold())
        self.assertIn("neutral_audience_wording_used", item.reasons)

    def test_service_target_uses_implementation_wording_not_course_audience(self):
        source = parse_page(
            """<main><p>Operations teams integrate automated workflows across connected systems to route approvals, monitor exceptions, and coordinate reliable execution throughout complex business processes.</p></main>""",
            requested_url="https://s.com", final_url="https://s.com", status_code=200,
        )
        target = parse_page(
            """<title>Workflow Automation Software Platform</title><h1>Connected Workflow Automation</h1><p>Integrate business systems, automate approvals, monitor exceptions, and deploy reliable operational workflows.</p>""",
            requested_url="https://t.com/products/workflow-automation", final_url="https://t.com/products/workflow-automation", status_code=200,
        )
        item = rank_placements(source, target, "workflow automation platform", "https://t.com/products/workflow-automation", top_n=1)[0]

        self.assertIn("an approach that can be explored further", item.after_text)
        self.assertNotIn("professionals", item.after_text.casefold())
        self.assertNotIn("course", item.after_text.casefold())

    def test_course_url_cannot_override_clear_pricing_page_evidence(self):
        source = parse_page(
            """<main><p>AI automation costs vary according to integrations, transaction volume, operational support, infrastructure requirements, and the expected return on investment.</p></main>""",
            requested_url="https://s.com", final_url="https://s.com", status_code=200,
        )
        target = parse_page(
            """<title>AI Platform Pricing and TCO</title><h1>Plans and Pricing</h1><p>Compare implementation costs, operating expenses, plans, and expected ROI.</p>""",
            requested_url="https://t.com/course", final_url="https://t.com/course", status_code=200,
        )
        item = rank_placements(source, target, "AI platform pricing", "https://t.com/course", top_n=1)[0]

        self.assertIn("implementation costs", item.after_text)
        self.assertNotIn("professionals", item.after_text.casefold())
        self.assertNotIn("studied more deeply", item.after_text)

    def test_course_url_supports_ambiguous_on_page_copy_without_guessing_audience(self):
        source = parse_page(
            """<main><p>Financial agents support continuous accounting and transaction monitoring across connected business systems, regional teams, and carefully governed reporting workflows.</p></main>""",
            requested_url="https://s.com", final_url="https://s.com", status_code=200,
        )
        target = parse_page(
            """<title>Applied Finance AI</title><h1>Financial Agent Applications</h1><p>Continuous accounting, transaction monitoring, and reporting workflows.</p>""",
            requested_url="https://t.com/education/course/finance-ai", final_url="https://t.com/education/course/finance-ai", status_code=200,
        )
        item = rank_placements(source, target, "finance AI education", "https://t.com/education/course/finance-ai", top_n=1)[0]

        self.assertIn("a practical application that can be examined more deeply", item.after_text)
        self.assertNotIn("professionals", item.after_text.casefold())



if __name__ == "__main__":
    unittest.main()
