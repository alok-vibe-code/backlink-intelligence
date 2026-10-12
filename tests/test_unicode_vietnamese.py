import re
import unicodedata
import unittest

from backlink_intelligence.html_utils import parse_page
from backlink_intelligence.placement import (
    _find_complete_phrase,
    _preservation_percent,
    _simple_anchor_variants,
    _stem,
    rank_placements,
)
from backlink_intelligence.relevance import analyze_relevance, similarity, tokens


class VietnameseUnicodeTests(unittest.TestCase):
    def test_vietnamese_words_keep_diacritics_and_short_syllables(self):
        self.assertEqual(
            tokens("KÉT SẮT Việt Tiệp Ổ khóa chống cháy điện tử ý"),
            ["két", "sắt", "việt", "tiệp", "ổ", "khóa", "chống", "cháy", "điện", "tử", "ý"],
        )

    def test_nfc_and_nfd_have_identical_terms_and_relevance(self):
        composed = "Két sắt Việt Tiệp chống cháy có ổ khóa điện tử"
        decomposed = unicodedata.normalize("NFD", composed)
        self.assertNotEqual(composed, decomposed)
        self.assertEqual(tokens(composed), tokens(decomposed))
        self.assertEqual(similarity(composed, decomposed), 1.0)

    def test_combining_marks_with_no_composed_character_are_kept(self):
        text = "a\u0301\u0323"  # NFC still has a combining acute accent.
        canonical = unicodedata.normalize("NFC", text)
        self.assertEqual(tokens(text), [canonical])
        self.assertEqual(tokens(text), tokens("a\u0323\u0301"))

    def test_different_vietnamese_tones_never_merge(self):
        self.assertEqual(tokens("ma má mã mạ"), ["ma", "má", "mã", "mạ"])
        self.assertEqual(similarity("má", "ma"), 0.0)
        self.assertEqual(similarity("mã", "má"), 0.0)
        self.assertNotEqual(tokens("khóa"), tokens("khoa"))

    def test_function_words_removed_but_negation_and_product_words_kept(self):
        text = "và của cho được để những trong với là két sắt không chưa chống cháy"
        self.assertEqual(tokens(text), ["két", "sắt", "không", "chưa", "chống", "cháy"])

    def test_casefold_is_used_for_comparison(self):
        self.assertEqual(tokens("ĐIỆN TỬ Straße"), ["điện", "tử", "strasse"])

    def test_ascii_identifiers_and_english_tokens_match_upstream(self):
        text = ".NET Node.js C++ C# UTF-8 KV-48-NC DH1016 K-123 A B 7 12 3.14 and THE agentic AI"
        upstream_pattern = re.compile(r"[a-z0-9][a-z0-9+#.-]{1,}", re.I)
        upstream_stop = {
            "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have", "how",
            "in", "into", "is", "it", "its", "of", "on", "or", "that", "the", "their", "this", "to",
            "was", "we", "what", "when", "where", "which", "with", "you", "your", "can", "will", "more",
        }
        expected = [term.lower().strip(".-") for term in upstream_pattern.findall(text)
                    if term.lower().strip(".-") not in upstream_stop]
        self.assertEqual(tokens(text), expected)
        self.assertIn("kv-48-nc", tokens(text))
        self.assertIn("c++", tokens(text))

    def test_underscore_punctuation_and_detached_marks_are_boundaries(self):
        self.assertEqual(tokens("\u0301Két_sắt, Việt—Tiệp!"), ["két", "sắt", "việt", "tiệp"])
        self.assertEqual(tokens(""), [])
        self.assertEqual(tokens(None), [])
        self.assertEqual(tokens("+ # -- ..."), [])

    def test_realistic_vietnamese_topic_beats_unrelated_content(self):
        target = "Két sắt Việt Tiệp chống cháy với ổ khóa điện tử bảo vệ tiền tài sản"
        relevant = "Hướng dẫn chọn két sắt chống cháy và kiểm tra ổ khóa điện tử bảo vệ tài sản"
        unrelated = "Máy lọc nước gia đình và hướng dẫn thay lõi vệ sinh bình chứa"
        self.assertGreater(similarity(relevant, target), 0.4)
        self.assertGreater(similarity(relevant, target), similarity(unrelated, target))

    def test_multilevel_evidence_uses_complete_vietnamese_shared_terms(self):
        source = parse_page(
            "<title>Két sắt chống cháy</title><h1>Khóa điện tử</h1>"
            "<p>Két sắt Việt Tiệp chống cháy dùng ổ khóa điện tử bảo vệ tài sản.</p>",
            requested_url="https://source.example", final_url="https://source.example", status_code=200,
        )
        target = parse_page(
            unicodedata.normalize("NFD", "<title>Két sắt Việt Tiệp</title><h1>Khóa điện tử chống cháy</h1>"
                                  "<p>Két sắt chống cháy bảo vệ tiền và tài sản với ổ khóa điện tử.</p>"),
            requested_url="https://target.example", final_url="https://target.example", status_code=200,
        )
        result = analyze_relevance(source, target, "chống cháy khóa điện tử")
        self.assertIn(result.level, {"high", "very_high"})
        self.assertGreater(result.page_similarity, 0.6)
        self.assertTrue({"két", "sắt", "khóa", "cháy", "điện"} <= set(result.shared_terms))

    def test_english_morphology_does_not_modify_vietnamese_or_product_ids(self):
        self.assertEqual(_simple_anchor_variants("két sắt"), [])
        self.assertEqual(_simple_anchor_variants("AI agent"), ["AI agents"])
        self.assertEqual(_stem("đườngs"), "đườngs")
        self.assertEqual(_stem("KV-48-LOCKS"), "kv-48-locks")
        self.assertEqual(_stem("workflows"), "workflow")

    def test_preservation_treats_nfc_and_nfd_as_the_same_copy(self):
        before = "Két sắt chống cháy có khóa điện tử."
        after = unicodedata.normalize("NFD", before)
        self.assertEqual(_preservation_percent(before, after), 100.0)
        self.assertEqual(_preservation_percent(after, before), 100.0)

    def test_nfd_anchor_match_preserves_original_spelling_and_span(self):
        text = unicodedata.normalize("NFD", "Chọn Két Sắt Việt Tiệp để bảo vệ tài sản.")
        match = _find_complete_phrase(text, "két sắt Việt Tiệp")
        self.assertIsNotNone(match)
        self.assertEqual(match.group(), unicodedata.normalize("NFD", "Két Sắt Việt Tiệp"))
        self.assertEqual(text[match.start():match.end()], match.group())
        reverse = _find_complete_phrase("Chọn Két Sắt Việt Tiệp.", unicodedata.normalize("NFD", "két sắt Việt Tiệp"))
        self.assertEqual(reverse.group(), "Két Sắt Việt Tiệp")

    def test_vietnamese_phrase_match_respects_tones_and_word_boundaries(self):
        self.assertIsNone(_find_complete_phrase("khóa", "khoa"))
        self.assertIsNone(_find_complete_phrase("két sắtt", "két sắt"))
        self.assertIsNone(_find_complete_phrase(unicodedata.normalize("NFD", "má"), "ma"))
        self.assertIsNone(_find_complete_phrase("ạ\u0301", "ạ"))

    def test_vietnamese_placement_ranks_real_topic_and_preserves_nfd_copy(self):
        relevant = (
            "Khi chọn Két sắt Việt Tiệp, khách hàng cần kiểm tra khả năng chống cháy, "
            "ổ khóa điện tử và kích thước phù hợp để bảo vệ tiền và tài sản trong gia đình."
        )
        source = parse_page(
            "<main><p>Người dùng máy lọc nước cần thay lõi định kỳ, vệ sinh bình chứa và "
            "kiểm tra chất lượng nguồn nước đầu vào trước khi sử dụng trong gia đình.</p><p>"
            + unicodedata.normalize("NFD", relevant) + "</p></main>",
            requested_url="https://source.example/guide", final_url="https://source.example/guide", status_code=200,
        )
        target = parse_page(
            "<title>Két sắt Việt Tiệp chống cháy</title><h1>Khóa điện tử</h1>"
            "<p>Két sắt chống cháy dùng ổ khóa điện tử bảo vệ tiền và tài sản trong gia đình.</p>",
            requested_url="https://target.example/safe", final_url="https://target.example/safe", status_code=200,
        )
        item = rank_placements(source, target, "két sắt Việt Tiệp", target.final_url, top_n=1)[0]
        self.assertEqual(item.paragraph_index, 2)
        self.assertEqual(item.strategy, "minimal_insertion")
        self.assertEqual(item.after_text, source.paragraphs[1])
        self.assertEqual(item.preservation_percent, 100.0)
        self.assertEqual(unicodedata.normalize("NFC", item.suggested_anchor), "Két sắt Việt Tiệp")


if __name__ == "__main__":
    unittest.main()
