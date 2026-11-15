"""Presentation regressions: readable prose, deduplicated references and readable source rows."""
import unittest
from streamlit.testing.v1 import AppTest


class NarrativeTests(unittest.TestCase):
    def test_prose_deduplicates_references_and_formats_json_as_a_table(self):
        app = AppTest.from_string('''
from ui.scientific_narrative import render_narrative
citation = {"source_id": "internal-source-id", "quote": '{"Test": "B1", "Final carbon dioxide": "0.44"}'}
render_narrative({"behaviour": [{"text": "Recorded gas concentrations describe this specimen.", "citations": [citation]}],
    "concerns": [{"text": "Measurement uncertainty is unavailable.", "citations": [citation]}]},
    [{"source_id": "internal-source-id", "psi_id": "PSI-25", "source_doc": "Original.csv", "locator": "CSV record 1"}])
''').run()
        self.assertFalse(app.exception)
        self.assertEqual(sum(x.value == "Sources [1]" for x in app.caption), 2)
        self.assertFalse(any("internal-source-id" in x.value for x in app.caption))
        self.assertEqual(len(app.dataframe), 1)
        self.assertEqual(app.dataframe[0].value.iloc[1]["Source value"], "0.44")
        self.assertFalse(app.text)
        self.assertTrue(any(x.label == "References for this interpretation" for x in app.expander))

    def test_empty_sections_are_not_rendered_and_limits_remain_visible(self):
        app = AppTest.from_string('''
from ui.scientific_narrative import render_narrative
render_narrative({"behaviour": [], "limitations": ["Interpretation requires review."]}, [])
''').run()
        self.assertFalse(app.exception)
        self.assertEqual([x.value for x in app.subheader], ["Interpretation limits"])
        self.assertFalse(app.expander)


if __name__ == "__main__":
    unittest.main()
