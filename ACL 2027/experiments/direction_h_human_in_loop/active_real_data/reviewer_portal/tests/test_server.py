from __future__ import annotations

import unittest
from pathlib import Path

import server


class CurrentGovernancePortalCase(unittest.TestCase):
    """Verify only the current, text-free governance state."""

    @classmethod
    def setUpClass(cls):
        cls.summary = server.check_readiness()

    def test_current_readiness_is_text_free_and_locked(self):
        self.assertEqual(self.summary["status"], "locked")
        self.assertFalse(self.summary["contains_source_text"])
        self.assertEqual(
            {corpus["id"] for corpus in self.summary["corpora"]}, set(server.TARGETS)
        )
        self.assertTrue(all(not corpus["ready"] for corpus in self.summary["corpora"]))

    def test_current_summary_cannot_satisfy_access_edge(self):
        self.assertFalse(server.public_summary_is_ready(self.summary))

    def test_portal_has_no_item_or_rating_route(self):
        source = Path(server.__file__).read_text(encoding="utf-8")
        self.assertNotIn('"/review', source)
        self.assertNotIn('"/api/items', source)
        self.assertNotIn('"/api/ratings', source)
        self.assertIn("if not public_summary_is_ready(summary):", source)

    def test_page_has_no_personal_or_free_text_input(self):
        html = (server.STATIC_ROOT / "index.html").read_text(encoding="utf-8")
        script = (server.STATIC_ROOT / "app.js").read_text(encoding="utf-8")
        self.assertNotIn('type="text"', html)
        self.assertNotIn("<textarea", html)
        self.assertNotIn("localStorage", script)
        self.assertNotIn("sessionStorage", script)


if __name__ == "__main__":
    unittest.main()
