import unittest
from unittest.mock import patch

from backlink_intelligence.safety import UnsafeURLError, validate_public_url


class SafetyTests(unittest.TestCase):
    def test_rejects_unsupported_scheme(self):
        with self.assertRaises(UnsafeURLError): validate_public_url("file:///etc/passwd", resolve_dns=False)
    def test_rejects_localhost(self):
        with self.assertRaises(UnsafeURLError): validate_public_url("http://localhost/admin", resolve_dns=False)
    def test_rejects_private_literal_ip(self):
        with self.assertRaises(UnsafeURLError): validate_public_url("http://127.0.0.1/", resolve_dns=False)
        with self.assertRaises(UnsafeURLError): validate_public_url("http://169.254.169.254/latest/meta-data", resolve_dns=False)
    def test_accepts_public_literal_ip(self):
        self.assertEqual(validate_public_url("https://8.8.8.8/", resolve_dns=False), "https://8.8.8.8/")
    @patch("backlink_intelligence.safety.socket.getaddrinfo")
    def test_rejects_dns_rebinding_to_private_ip(self, getaddrinfo):
        getaddrinfo.return_value = [(2, 1, 6, "", ("10.0.0.4", 443))]
        with self.assertRaises(UnsafeURLError): validate_public_url("https://example.com")


if __name__ == "__main__": unittest.main()
