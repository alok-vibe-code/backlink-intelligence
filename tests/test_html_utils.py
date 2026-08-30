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


if __name__ == "__main__": unittest.main()
