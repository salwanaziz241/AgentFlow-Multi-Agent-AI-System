import argparse
from .core import DemoModel, OpenAIModel, Pipeline, SearchTool, save_run


def main() -> None:
    parser = argparse.ArgumentParser(description="AgentFlow: multi-agent research system")
    parser.add_argument("question", help="Research question")
    parser.add_argument("--mode", choices=["demo", "live"], default="demo")
    parser.add_argument("--model", default="gpt-4.1-mini", help="OpenAI model for live mode")
    parser.add_argument("--output", default="outputs/latest")
    parser.add_argument("--revisions", type=int, default=1, help="Maximum citation-repair attempts")
    args = parser.parse_args()
    pipeline = Pipeline(DemoModel() if args.mode == "demo" else OpenAIModel(args.model),
                        SearchTool(offline=args.mode == "demo"), max_revisions=args.revisions)
    state = pipeline.run(args.question)
    report, trace = save_run(state, args.output)
    print(state.report)
    print(f"\nSaved report: {report}\nSaved trace: {trace}\nOpen dashboard: {report.parent / 'dashboard.html'}")


if __name__ == "__main__":
    main()
