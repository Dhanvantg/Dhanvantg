import unittest
import xml.etree.ElementTree as ET
from scripts.update_profile import summarize, replace_context, overview_svg, context_markdown, START, END


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.user = {"created_at": "2021-10-10T00:00:00Z", "followers": 6}
        self.repos = [{"language": "Python", "fork": False, "stargazers_count": 2}, {"language": "Go", "fork": True, "stargazers_count": 50}, {"language": None, "fork": False}]

    def test_forks_and_undetected_languages_do_not_skew_breakdown(self):
        _, languages = summarize(self.repos)
        self.assertEqual(dict(languages), {"Python": 1})
        body = context_markdown(self.user, self.repos, "2026-09-30")
        self.assertIn("100.0%", body)
        self.assertNotIn("Go ", body)
        self.assertIn("organization work is not included", body)

    def test_updater_preserves_biography_and_manual_sections(self):
        original = "Intro\n" + START + "old" + END + "\nProjects"
        changed = replace_context(original, "fresh")
        self.assertEqual(changed, "Intro\n" + START + "\nfresh\n" + END + "\nProjects")
        with self.assertRaises(ValueError):
            replace_context("No markers", "fresh")

    def test_svg_is_valid_and_stars_exclude_forks(self):
        result = overview_svg(self.user, self.repos, "2026-09-30")
        ET.fromstring(result)
        self.assertIn("2 stars on original", result)
        self.assertNotIn("52 stars", result)

    def test_empty_sample_has_no_fabricated_language(self):
        self.assertIn("No detected primary languages", context_markdown(self.user, [], "2026-09-30"))


if __name__ == "__main__":
    unittest.main()
