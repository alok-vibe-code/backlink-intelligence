import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backlink_intelligence.analysis import PlacementAnalysis
from backlink_intelligence.api import (
    OpportunityResponse,
    SETTINGS,
    SegmentResponse,
    app,
    challenge_verifier,
)
from backlink_intelligence.html_utils import parse_page
from backlink_intelligence.models import PlacementSuggestion, TextSegment


class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[challenge_verifier] = lambda: (lambda token: True)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

    def pages(self):
        source = parse_page(
            "<main><p>Unicode testing includes an emoji 😀 and an AI agent in a complete editorial sentence for review.</p></main>",
            requested_url="https://source.example/",
            final_url="https://source.example/",
            status_code=200,
        )
        target = parse_page(
            "<title>AI Agent Guide</title><p>AI agent implementation guide.</p>",
            requested_url="https://target.example/",
            final_url="https://target.example/",
            status_code=200,
        )
        return source, target

    def payload(self):
        return {
            "source_url": "https://source.example/",
            "target_url": "https://target.example/",
            "anchor": "AI agent",
            "challenge_token": "test-token",
        }

    @patch("backlink_intelligence.api.PlacementAnalyzer.analyze")
    def test_v1_completed_contract_uses_segments_not_offsets(self, analyze):
        source, target = self.pages()
        after_text = "Unicode testing includes an emoji 😀 and an AI agent in a complete sentence."
        analyze.return_value = PlacementAnalysis(
            status="completed",
            source=source,
            target=target,
            opportunities=[
                PlacementSuggestion(
                    rank=1,
                    paragraph_index=1,
                    score=0.4,
                    context_level="high",
                    destination_score=0.2,
                    destination_fit="high",
                    requested_anchor="AI agent",
                    suggested_anchor="AI agent",
                    strategy="minimal_insertion",
                    before=after_text,
                    after="Unicode testing includes an emoji 😀 and an [AI agent](https://target.example/) in a complete sentence.",
                    after_text=after_text,
                    after_segments=[
                        TextSegment("text", "Unicode testing includes an emoji 😀 and an "),
                        TextSegment("link", "AI agent", "https://target.example/"),
                        TextSegment("text", " in a complete sentence."),
                    ],
                    added_words=0,
                    preservation_percent=100.0,
                    intervention="low",
                    recommendation_status="recommended",
                    review_required=False,
                    reasons=["anchor_already_present_in_original_copy"],
                )
            ],
        )
        response = self.client.post("/v1/place", json=self.payload())
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertNotIn("link_start", body["opportunities"][0])
        segments = body["opportunities"][0]["after_segments"]
        self.assertEqual("".join(segment["text"] for segment in segments), after_text)
        self.assertEqual(sum(segment["type"] == "link" for segment in segments), 1)

    @patch("backlink_intelligence.api.PlacementAnalyzer.analyze")
    def test_no_suitable_placement_returns_http_200(self, analyze):
        source, target = self.pages()
        analyze.return_value = PlacementAnalysis(
            status="no_suitable_placement",
            source=source,
            target=target,
            opportunities=[],
        )
        response = self.client.post("/v1/place", json=self.payload())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "no_suitable_placement")
        self.assertEqual(response.json()["opportunities"], [])

    def test_unknown_request_field_is_rejected(self):
        payload = self.payload()
        payload["unexpected"] = True
        response = self.client.post("/v1/place", json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "invalid_request")

    def test_health_contract(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["api_version"], "1")
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_unapproved_origin_is_rejected(self):
        response = self.client.post(
            "/v1/place",
            json=self.payload(),
            headers={"Origin": "https://attacker.example"},
        )
        self.assertEqual(response.status_code, 403)

    def test_unapproved_host_is_rejected_in_production(self):
        with patch.object(SETTINGS, "environment", "production"):
            response = self.client.post(
                "/v1/place",
                json=self.payload(),
                headers={
                    "Host": "attacker.example",
                    "Origin": "https://alokblog.com",
                },
            )
        self.assertEqual(response.status_code, 400)

    def test_unicode_segments_reconstruct_combining_and_non_bmp_text(self):
        after_text = "Cafe\u0301 😀 links to an AI agent guide."
        opportunity = OpportunityResponse(
            rank=1,
            paragraph_index=1,
            score=0.2,
            context_level="medium",
            destination_score=0.1,
            destination_fit="medium",
            requested_anchor="AI agent",
            suggested_anchor="AI agent",
            strategy="minimal_insertion",
            recommendation_status="recommended",
            review_required=False,
            intervention="low",
            preservation_percent=100.0,
            before_text=after_text,
            after_text=after_text,
            after_segments=[
                SegmentResponse(type="text", text="Cafe\u0301 😀 links to an "),
                SegmentResponse(
                    type="link", text="AI agent", url="https://target.example/"
                ),
                SegmentResponse(type="text", text=" guide."),
            ],
            reasons=[],
            warnings=[],
        )
        self.assertEqual(
            "".join(segment.text for segment in opportunity.after_segments), after_text
        )

    def test_structured_segments_reject_mismatched_text(self):
        with self.assertRaises(ValueError):
            OpportunityResponse(
                rank=1,
                paragraph_index=1,
                score=0.2,
                context_level="medium",
                destination_score=0.1,
                destination_fit="medium",
                requested_anchor="AI agent",
                suggested_anchor="AI agent",
                strategy="minimal_insertion",
                recommendation_status="recommended",
                review_required=False,
                intervention="low",
                preservation_percent=100.0,
                before_text="Before",
                after_text="Expected",
                after_segments=[
                    SegmentResponse(
                        type="link", text="Different", url="https://target.example/"
                    )
                ],
                reasons=[],
                warnings=[],
            )


if __name__ == "__main__":
    unittest.main()
