import json
import tempfile
import unittest
from pathlib import Path
from agentflow.core import DemoModel, Pipeline, SearchTool, save_run


class PipelineTests(unittest.TestCase):
    def test_demo_pipeline_and_artifacts(self):
        state = Pipeline(DemoModel(), SearchTool(offline=True)).run("What are multi-agent systems?")
        self.assertEqual([x["agent"] for x in state.trace], ["planner", "researcher", "analyst", "critic", "quality_gate", "writer"])
        self.assertEqual(len(state.evidence), 2)
        self.assertIn("## Sources", state.report)
        with tempfile.TemporaryDirectory() as folder:
            report, trace = save_run(state, folder)
            self.assertTrue(report.is_file())
            self.assertEqual(len(json.loads(trace.read_text())["trace"]), 6)

    def test_empty_question_rejected(self):
        with self.assertRaises(ValueError):
            Pipeline(DemoModel(), SearchTool(offline=True)).run("  ")


if __name__ == "__main__":
    unittest.main()
