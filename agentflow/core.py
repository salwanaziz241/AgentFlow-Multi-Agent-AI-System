from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol


@dataclass
class Evidence:
    id: str
    title: str
    url: str
    excerpt: str


@dataclass
class RunState:
    question: str
    plan: str = ""
    evidence: list[Evidence] = field(default_factory=list)
    analysis: str = ""
    critique: str = ""
    report: str = ""
    audit: dict = field(default_factory=dict)
    revisions: int = 0
    mode: str = "live"
    trace: list[dict] = field(default_factory=list)

    def record(self, agent: str, result: str, duration_ms: int = 0) -> None:
        self.trace.append({"agent": agent, "timestamp": datetime.now(timezone.utc).isoformat(), "duration_ms": duration_ms, "output": result})


class Model(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class OpenAIModel:
    def __init__(self, model: str = "gpt-4.1-mini"):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install the LLM extra: pip install -e '.[llm]'") from exc
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("Set OPENAI_API_KEY before running --mode live")
        self.client = OpenAI(timeout=40.0, max_retries=2)
        self.model = model

    def complete(self, system: str, user: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.2,
        )
        return response.choices[0].message.content or ""


class OllamaModel:
    """Local model via Ollama's OpenAI-compatible chat endpoint."""
    def __init__(self, model: str = "llama3.2:3b"):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install dependencies: python -m pip install -e '.[studio,llm]'") from exc
        self.client = OpenAI(base_url="http://127.0.0.1:11434/v1", api_key="ollama", timeout=180.0, max_retries=0)
        self.model = model

    def complete(self, system: str, user: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.2,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Local Ollama request failed. Check that Ollama is running and that "
                f"you downloaded '{self.model}' using 'ollama pull {self.model}'. Details: {exc}"
            ) from exc
        return response.choices[0].message.content or ""


class DemoModel:
    """Deterministic sample outputs; does not claim to be real AI inference."""
    def complete(self, system: str, user: str) -> str:
        role = system.splitlines()[0].lower()
        if "planner" in role:
            return "1. Retrieve up to three sources. 2. Summarize supported observations. 3. Check claims. 4. Write a cited report."
        if "analyst" in role:
            return "The available sources provide introductory context. Findings must be limited to what the excerpts actually say; missing details require further verification."
        if role.startswith("critic agent"):
            return "Evidence check: Do not assert unsupported numerical results, causality, or source agreement. Clearly label the offline demonstration and any evidence gaps."
        if "revise" in role:
            return "## Findings\n\nA multi-agent system consists of interacting agents [S1]. Natural language processing studies interactions between computers and human language [S2].\n\n## Limitations\n\nThese short introductory excerpts do not establish performance gains or real-world effectiveness [S1] [S2]."
        return "## Findings\n\nA multi-agent system consists of interacting agents [S1]. Natural language processing studies interactions between computers and human language [S2].\n\n## Limitations\n\nThese short introductory excerpts do not establish performance gains or real-world effectiveness [S1] [S2]."


class SearchTool:
    """Wikipedia search and extracts, using the public MediaWiki API."""
    ENDPOINT = "https://en.wikipedia.org/w/api.php"

    def __init__(self, offline: bool = False):
        self.offline = offline

    def search(self, query: str, limit: int = 3) -> list[Evidence]:
        if self.offline:
            return [
                Evidence("S1", "Demo: multi-agent systems", "https://en.wikipedia.org/wiki/Multi-agent_system", "A multi-agent system consists of multiple interacting intelligent agents."),
                Evidence("S2", "Demo: natural language processing", "https://en.wikipedia.org/wiki/Natural_language_processing", "Natural language processing concerns interactions between computers and human language."),
            ]
        params = urllib.parse.urlencode({"action": "query", "generator": "search", "gsrsearch": query,
                                         "gsrlimit": min(limit, 5), "prop": "extracts|info", "exintro": 1,
                                         "explaintext": 1, "inprop": "url", "format": "json"})
        request = urllib.request.Request(f"{self.ENDPOINT}?{params}", headers={"User-Agent": "AgentFlowPortfolio/0.1 (educational research demo)"})
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                payload = json.load(response)
        except Exception as exc:
            raise RuntimeError(f"Wikipedia retrieval failed: {exc}") from exc
        pages = payload.get("query", {}).get("pages", {})
        items = sorted(pages.values(), key=lambda p: p.get("index", 999))
        return [Evidence(f"S{i}", p.get("title", "Untitled"), p.get("fullurl", ""),
                         re.sub(r"\s+", " ", p.get("extract", "")).strip()[:1600])
                for i, p in enumerate(items, 1) if p.get("extract")]


class Pipeline:
    def __init__(self, model: Model, search: SearchTool, max_revisions: int = 1):
        self.model = model
        self.search = search
        self.max_revisions = max(0, max_revisions)

    def run(self, question: str) -> RunState:
        if not question.strip():
            raise ValueError("Question cannot be empty")
        from .audit import audit_report
        state = RunState(question=question, mode="demo" if isinstance(self.model, DemoModel) else ("ollama" if isinstance(self.model, OllamaModel) else "live"))
        state.plan = self.model.complete("Planner agent: propose a concise research plan.", question)
        state.record("planner", state.plan)
        state.evidence = self.search.search(question)
        state.record("researcher", json.dumps([asdict(e) for e in state.evidence], ensure_ascii=False))
        source_text = "\n".join(f"[{e.id}] {e.title}: {e.excerpt} ({e.url})" for e in state.evidence)
        state.analysis = self.model.complete(
            "Analyst agent: synthesize only the provided evidence. Cite evidence IDs. Do not invent facts.",
            f"Question: {question}\nSources:\n{source_text or 'No sources retrieved.'}")
        state.record("analyst", state.analysis)
        state.critique = self.model.complete(
            "Critic agent: audit claims for support; identify unsupported claims, uncertainty, and missing evidence.",
            f"Question: {question}\nSources:\n{source_text}\nAnalysis:\n{state.analysis}")
        state.record("critic", state.critique)
        draft = self.model.complete(
            "Writer agent: write a short Markdown report. Use only supplied evidence; cite [S1] etc. Include limitations. Follow the critic's cautions.",
            f"Question: {question}\nSources:\n{source_text}\nAnalysis:\n{state.analysis}\nCritique:\n{state.critique}")
        check = audit_report(draft, {e.id for e in state.evidence})
        state.record("quality_gate", json.dumps(check.to_dict()))
        for _ in range(self.max_revisions):
            if check.passed or not state.evidence:
                break
            draft = self.model.complete(
                "Revise agent: repair unsupported or missing source references. Every substantial factual paragraph needs a valid [S1] style citation. Never invent evidence. Return only Markdown.",
                f"Question: {question}\nEvidence: {source_text}\nDraft: {draft}\nAudit: {json.dumps(check.to_dict())}")
            state.revisions += 1
            state.record("reviser", draft)
            check = audit_report(draft, {e.id for e in state.evidence})
            state.record("quality_gate", json.dumps(check.to_dict()))
        state.audit = check.to_dict()
        state.report = (f"# Research report: {question}\n\n{draft}\n\n"
                        "## Sources\n" + ("\n".join(f"- [{e.id}] {e.title}: {e.url}" for e in state.evidence) or "- No sources retrieved")
                        + "\n\n## Review notes\n" + state.critique + "\n")
        state.record("writer", state.report)
        return state


def save_run(state: RunState, output: str | Path) -> tuple[Path, Path]:
    folder = Path(output)
    folder.mkdir(parents=True, exist_ok=True)
    report = folder / "report.md"
    trace = folder / "trace.json"
    report.write_text(state.report, encoding="utf-8")
    trace.write_text(json.dumps(asdict(state), indent=2, ensure_ascii=False), encoding="utf-8")
    from .studio import render_dashboard
    render_dashboard(state, folder)
    return report, trace
