import unittest

from backlink_intelligence.html_utils import parse_page
from backlink_intelligence.link_analysis import find_backlink, normalize_url, outbound_evidence, same_destination


class LinkAnalysisTests(unittest.TestCase):
    def test_normalize_url(self):
        self.assertEqual(normalize_url("https://Example.com/page/"), "https://example.com/page"); self.assertTrue(same_destination("https://example.com/page/", "https://example.com/page"))
    def test_find_backlink(self):
        page = parse_page("<main><p>Read <a href='https://target.com/a/'>this guide</a> now.</p></main>", requested_url="https://source.com", final_url="https://source.com", status_code=200); result = find_backlink(page, "https://target.com/a"); self.assertTrue(result.found); self.assertEqual(result.anchor, "this guide"); self.assertEqual(result.placement, "editorial_context")
    def test_outbound_evidence(self):
        html = "<main><p>Text " + " ".join(f"<a href='https://d{i}.example/page'>x{i}</a>" for i in range(8)) + " words enough for context and testing external links.</p></main>"; page = parse_page(html, requested_url="https://source.com", final_url="https://source.com", status_code=200); evidence = outbound_evidence(page); self.assertEqual(evidence.external_links, 8); self.assertEqual(evidence.unique_external_domains, 8)


if __name__ == "__main__": unittest.main()
