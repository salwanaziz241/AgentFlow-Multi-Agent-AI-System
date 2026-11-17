# AgentFlow — Research, with receipts

An inspectable multi-agent research workflow. Instead of hiding everything behind a single prompt, AgentFlow separates planning, retrieval, synthesis, critique, writing, and a deterministic citation quality gate. A local HTML **Run Studio** shows what each stage produced.

> **Scope:** A portfolio prototype, not a production research engine. Live execution uses OpenAI plus Wikipedia introductory excerpts. The demo is deterministic and does not make live LLM calls. Citation coverage checks references, **not whether claims are actually true**.

## Quick start (Python 3.10+)

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
python -m agentflow "How can AI agents improve customer support?" --mode demo
```

Open **`outputs/latest/dashboard.html`** in your browser. No server needed. Read the report in `outputs/latest/report.md`, and inspect the raw record in `outputs/latest/trace.json`.

For live execution:

```bash
pip install -e '.[llm]'
export OPENAI_API_KEY='your-key'  # Windows PowerShell: $env:OPENAI_API_KEY='your-key'
python -m agentflow "What are the limitations of multi-agent AI systems?" --mode live --model gpt-4.1-mini
```

Live mode requires internet access and a paid API key; it has not been verified end-to-end in this environment. The Wikipedia API may rate-limit or fail. **Never commit API keys.**

## How it works

```text
Question
  ↓
Planner → Researcher (Wikipedia tool) → Analyst → Critic → Writer
                                                       ↓
                                               Citation quality gate
                                                       ↓
                                      [if needed] Reviser → Recheck
                                                       ↓
                                      Report + JSON trace + Run Studio
```

Each agent has a specific instruction and shares a structured `RunState`. The critic is an LLM review; the quality gate is deterministic Python. The gate detects nonexistent citation IDs and substantial paragraphs with no inline citation. If it fails, the reviser gets one chance by default (`--revisions 2` to allow two). This is a **bounded correction loop**, not a guarantee of factual accuracy.

## Why this project is more than a chatbot

- **Separation of concerns:** replace the model, retriever, or evaluator independently.
- **Inspectable evidence:** every source has an ID, title, URL, and excerpt.
- **Explicit quality gate:** auditable rules rather than relying entirely on the model's confidence.
- **Bounded self-correction:** the writer can revise based on feedback, without an endless loop.
- **Run Studio:** a responsive standalone HTML view of source cards, quality checks, agent activity, and the final report.
- **Offline-first demonstration:** no API costs to show a recruiter the full pipeline.

## Repository map

```text
agentflow/
├── agentflow/
│   ├── core.py         # models, retrieval, orchestration, state, report
│   ├── audit.py        # deterministic citation checks
│   ├── studio.py       # local HTML dashboard generator
│   ├── cli.py          # command-line interface
│   └── __main__.py
├── examples/demo-output/
│   ├── dashboard.html  # open this first
│   ├── report.md
│   └── trace.json
├── tests/
│   ├── test_pipeline.py
│   └── test_audit.py
├── pyproject.toml
└── README.md
```

## Tests

```bash
python -m unittest discover -s tests -v
```

Five automated tests cover demo artifacts, empty inputs, invalid citations, missing citations, and HTML escaping. All five passed in the packaged environment.

## A realistic next sprint

1. Replace Wikipedia-only retrieval with multi-source retrieval and metadata (publication dates, domain quality).
2. Evaluate claim-level factual support, not just citation formatting, using labeled examples.
3. Add structured JSON outputs and retry/error handling for invalid model responses.
4. Add run-level cost, token usage, and latency monitoring.
5. Deploy a small hosted interface with an evaluation dataset and reproducible benchmark.


## Responsible use

Wikipedia extracts are introductory, not comprehensive evidence. LLM outputs may hallucinate. A passing audit is **not** a factuality certification. Review reports and original sources before use. Demo output is fixture-based and must not be presented as real retrieval or model inference.

## Interactive AgentFlow Studio (Streamlit)

The Streamlit app lets you enter a research question, run the agents, inspect each stage,
review retrieved sources and citation checks, and download Markdown/JSON results.

From the extracted project folder (the one containing `pyproject.toml`):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[studio]'
python -m streamlit run agentflow/webapp.py
```

 browser should open at `http://localhost:8501`. Choose **Offline demo** and
click **Run agents**. Demo mode uses fixed example text regardless of your question.
It demonstrates the workflow but does **not** research your topic.

For genuine research, install the optional LLM dependency:

```bash
python -m pip install -e '.[all]'
export OPENAI_API_KEY='your_api_key_here'
python -m streamlit run agentflow/webapp.py
```

Select **Live AI** in the sidebar. The application uses OpenAI for agent reasoning
and Wikipedia for introductory source retrieval. API calls may cost money. The
quality gate checks citation structure, **not** whether the cited text proves
individual claims. Research results must still be independently verified.

To stop the server, press `Control+C` in the terminal.
