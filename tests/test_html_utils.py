import unittest

from backlink_intelligence.html_utils import parse_page

HTML = """
<html><head><title>Agentic AI Guide</title><link rel="canonical" href="https://example.com/guide" /><meta name="robots" content="index, follow" /></head><body>
<header><a href="/">Home</a></header><main><article><h1>Agentic AI Guide</h1><h2>Tool Calling</h2>
<p>AI agents can use tools to retrieve data and perform structured actions.</p>
<p>See the <a href="https://target.com/course" rel="nofollow">agentic AI course</a> for a structured learning path.</p>
</article></main><footer><a href="https://social.example/profile">Social</a></footer></body></html>
"""


class HTMLTests(unittest.TestCase):
    def setUp(self):
        self.page = parse_page(HTML, requested_url="https://example.com/guide", final_url="https://example.com/guide", status_code=200)
    def test_metadata_extraction(self):
        self.assertEqual(self.page.title, "Agentic AI Guide"); self.assertEqual(self.page.h1, "Agentic AI Guide"); self.assertEqual(self.page.canonical, "https://example.com/guide"); self.assertIn("index", self.page.robots); self.assertTrue(self.page.is_indexable)
    def test_paragraph_and_heading_extraction(self):
        self.assertGreaterEqual(len(self.page.paragraphs), 2); self.assertIn("Tool Calling", self.page.headings); self.assertGreater(self.page.word_count, 10)
    def test_link_context_and_placement(self):
        target = next(l for l in self.page.links if "target.com" in l.href); self.assertEqual(target.text, "agentic AI course"); self.assertEqual(target.placement, "editorial_context"); self.assertIn("nofollow", target.rel)
        footer = next(l for l in self.page.links if "social.example" in l.href); self.assertEqual(footer.placement, "footer")

    def test_navigation_sidebar_footer_and_duplicates_do_not_pollute_page_copy(self):
        page = parse_page(
            """<html><body>
            <nav><h1>Navigation Heading</h1><h2>Repeated Course Menu</h2><p>Repeated promotional navigation copy.</p></nav>
            <aside><h2>Related Programs</h2><p>Sidebar promotion for another course.</p></aside>
            <main><h2>Agentic AI Curriculum</h2>
            <p>Build autonomous AI agents with tools, retrieval, memory, and orchestration.</p>
            <h2>Agentic AI Curriculum</h2>
            <p>Build autonomous AI agents with tools, retrieval, memory, and orchestration.</p></main>
            <footer><p>Footer promotional links and legal navigation.</p></footer>
            </body></html>""",
            requested_url="https://example.com/course",
            final_url="https://example.com/course",
            status_code=200,
        )
        self.assertEqual(page.headings, ["Agentic AI Curriculum"])
        self.assertEqual(page.h1, "")
        self.assertEqual(
            page.paragraphs,
            ["Build autonomous AI agents with tools, retrieval, memory, and orchestration."],
        )


if __name__ == "__main__": unittest.main()
