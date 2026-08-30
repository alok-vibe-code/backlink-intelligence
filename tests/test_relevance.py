import unittest

from backlink_intelligence.html_utils import parse_page
from backlink_intelligence.relevance import analyze_relevance, similarity, tokens


class RelevanceTests(unittest.TestCase):
    def test_tokenization_removes_common_stopwords(self):
        result = tokens("The agentic AI course is for developers"); self.assertIn("agentic", result); self.assertNotIn("the", result)
    def test_similar_text_scores_higher(self):
        high = similarity("agentic ai agents tool calling memory rag", "ai agents use tool calling and memory rag"); low = similarity("agentic ai agents tool calling memory rag", "gardening soil flowers watering plants"); self.assertGreater(high, low)
    def test_multilevel_relevance(self):
        source = parse_page("<title>AI Agents</title><h1>Agent systems</h1><p>Agentic AI uses tools, memory and retrieval for autonomous workflows.</p>", requested_url="https://a.com", final_url="https://a.com", status_code=200)
        target = parse_page("<title>Agentic AI Course</title><h1>Learn AI agents</h1><p>Build AI agents with tool calling, RAG, memory and multi-agent systems.</p>", requested_url="https://b.com", final_url="https://b.com", status_code=200)
        result = analyze_relevance(source, target, "tools memory retrieval"); self.assertIn(result.level, {"medium", "high", "very_high"}); self.assertGreater(result.page_similarity, 0); self.assertIn("memory", result.shared_terms)


if __name__ == "__main__": unittest.main()
