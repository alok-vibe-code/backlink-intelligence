import unittest

from backlink_intelligence.models import MonitorSnapshot
from backlink_intelligence.monitor import compare_snapshots


class MonitorTests(unittest.TestCase):
    def new_snapshot(self, **overrides):
        data = dict(source_url="https://s.com", target_url="https://t.com", source_status=200, target_status=200, link_found=True, anchor="AI guide", rel=(), placement="editorial_context", source_canonical="https://s.com", source_robots=("index", "follow"), checked_at="now"); data.update(overrides); return MonitorSnapshot(**data)
    def test_baseline(self): self.assertEqual(compare_snapshots(None, self.new_snapshot()), ["baseline_created"])
    def test_removed_link_detected(self):
        old = self.new_snapshot().to_dict(); changes = compare_snapshots(old, self.new_snapshot(link_found=False, anchor="", placement="unknown")); self.assertIn("link_removed", changes); self.assertIn("anchor_changed", changes)
    def test_rel_change_detected(self):
        old = self.new_snapshot().to_dict(); changes = compare_snapshots(old, self.new_snapshot(rel=("nofollow",))); self.assertIn("rel_attributes_changed", changes)
    def test_unchanged(self): self.assertEqual(compare_snapshots(self.new_snapshot().to_dict(), self.new_snapshot()), ["unchanged"])


if __name__ == "__main__": unittest.main()
