"""Regression checks for the public Flash Info quality gates."""

import unittest

from app.routes.news import (
    NewsSummaryBody,
    NewsSummaryItem,
    _is_commercial_content,
    _is_database_ready_news,
    _is_google_news_relay,
    _is_untranslated_english,
    _local_summary,
    _normalize_summary_bullets,
    _summary_is_usable,
)


class NewsQualityTests(unittest.TestCase):
    def test_retail_discount_is_never_public_content(self) -> None:
        self.assertTrue(_is_commercial_content({
            "source": "Futura Sciences",
            "title": "Caméra 2K+ : ce pack Blink à -71 % fait un carton sur Amazon",
            "snippet": "Amazon propose le pack à 49,99 euros au lieu de 169,98 euros.",
            "link": "https://example.invalid/blink",
        }))

    def test_fallback_drops_incomplete_sentence(self) -> None:
        body = NewsSummaryBody(
            scopeLabel="Test",
            items=[
                NewsSummaryItem(source="Numerama", title="A", snippet="Une campagne cible les autoradios Android connectés. Ces appareils deviennent des relais pour botnet."),
                NewsSummaryItem(source="Source B", title="B", snippet="Une phrase suffisamment longue mais volontairement tronquée à la fin du tex"),
            ],
        )
        result = _local_summary(body)
        self.assertIn("## Ce qui compte", result)
        self.assertIn("## Ce que cela implique", result)
        self.assertNotIn("fin du tex", result)

    def test_markdown_structure_is_preserved(self) -> None:
        result = _normalize_summary_bullets("## Ce qui compte\n- Un fait vérifiable (Source)\n## Ce que cela implique\n- Une conséquence prudente")
        self.assertEqual(result.splitlines()[0], "## Ce qui compte")
        self.assertEqual(result.splitlines()[2], "## Ce que cela implique")

    def test_raw_teaser_cannot_become_a_flash_info_item(self) -> None:
        row = {
            "title": "A breaking but empty headline",
            "snippet": "This long RSS teaser looks informative but was never validated or summarized by the enrichment worker.",
            "enriched": False,
        }
        self.assertFalse(_is_database_ready_news(row))

    def test_google_news_relay_cannot_become_a_flash_info_item(self) -> None:
        self.assertTrue(_is_google_news_relay({
            "link": "https://news.google.com/rss/articles/CBMiExample?oc=5",
        }))
        self.assertFalse(_is_google_news_relay({
            "link": "https://www.numerama.com/tech/article.html",
        }))

    def test_untranslated_english_fallback_is_not_public_value(self) -> None:
        self.assertTrue(_is_untranslated_english(
            "AI is being integrated into classrooms, but teachers face challenges in using it effectively."
        ))
        self.assertFalse(_is_untranslated_english(
            "Selon les chercheurs, cette mesure est suivie par les équipes avec des données vérifiables."
        ))

    def test_truncated_or_unattributed_model_summary_falls_back(self) -> None:
        items = [
            NewsSummaryItem(source="Numerama", title="A", snippet="Un fait long et vérifiable provenant de la première source et contenant des éléments précis."),
            NewsSummaryItem(source="Le Grand Continent", title="B", snippet="Un autre fait long et vérifiable provenant de la seconde source et contenant des éléments précis."),
        ]
        malformed = "## Ce qui compte\n## Faits distincts\n- Une affirmation sans source et coupée à la fin"
        self.assertFalse(_summary_is_usable(malformed, items))


if __name__ == "__main__":
    unittest.main()
