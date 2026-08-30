import gzip
import unittest

from backlink_intelligence.fetcher import FetchError, _decompress_limited
from backlink_intelligence.safety import UnsafeURLError, validate_public_url


class FetcherSecurityTests(unittest.TestCase):
    def test_rejects_nonstandard_public_port(self):
        with self.assertRaises(UnsafeURLError):
            validate_public_url("https://example.com:8443/", resolve_dns=False)

    def test_gzip_expansion_is_bounded(self):
        compressed = gzip.compress(b"A" * 20_000)
        with self.assertRaises(FetchError):
            _decompress_limited(compressed, "gzip", 1_000)

    def test_url_fragment_is_removed_before_fetch(self):
        self.assertEqual(
            validate_public_url("https://example.com/path#private", resolve_dns=False),
            "https://example.com/path",
        )


if __name__ == "__main__":
    unittest.main()
