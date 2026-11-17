import tempfile
import unittest
from pathlib import Path
from agentflow.audit import audit_report
from agentflow.core import DemoModel, Pipeline, SearchTool, save_run

class AuditTests(unittest.TestCase):
    def test_unknown_citation_detected(self):
        result = audit_report('A source says this [S9].', {'S1'})
        self.assertFalse(result.passed)
        self.assertEqual(result.unknown_citations, ['S9'])

    def test_uncited_long_paragraph_detected(self):
        result = audit_report('This is a factual paragraph. ' * 9, {'S1'})
        self.assertEqual(result.uncited_paragraphs, 1)

    def test_dashboard_created_and_escaped(self):
        state = Pipeline(DemoModel(), SearchTool(offline=True)).run('<script>alert(1)</script>')
        with tempfile.TemporaryDirectory() as tmp:
            save_run(state,tmp)
            page = (Path(tmp)/'dashboard.html').read_text()
            self.assertIn('&lt;script&gt;',page)
            self.assertNotIn('<script>alert(1)</script>',page)
            self.assertIn('Evidence library',page)
            self.assertTrue(state.audit['passed'])

if __name__ == '__main__': unittest.main()
