"""Interactive Streamlit front end for AgentFlow."""
from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import streamlit as st

from agentflow.core import DemoModel, OpenAIModel, OllamaModel, Pipeline, SearchTool, save_run

st.set_page_config(page_title="AgentFlow Studio", page_icon="🧭", layout="wide")
st.markdown("""<style>
.block-container {max-width: 1180px; padding-top: 2rem}
[data-testid="stMetricValue"] {font-size: 1.5rem}
</style>""", unsafe_allow_html=True)

STAGES = ["planner", "researcher", "analyst", "critic", "quality_gate", "reviser", "writer"]


def run_agentflow(question: str, mode: str, model_name: str, revisions: int, progress):
    model = DemoModel() if mode == "demo" else (OllamaModel(model_name) if mode == "ollama" else OpenAIModel(model_name))
    pipeline = Pipeline(model, SearchTool(offline=mode == "demo"), max_revisions=revisions)
    # The pipeline runs synchronously. The progress indicator is intentionally not
    # presented as per-agent live progress, which the backend does not expose yet.
    with st.spinner("Agents are researching, reviewing and writing…"):
        state = pipeline.run(question)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    save_run(state, Path("outputs") / "runs" / stamp)
    save_run(state, Path("outputs") / "latest")
    progress.success("Run completed. Reports and execution traces saved.")
    return state


st.title("🧭 AgentFlow Studio")
st.caption("Multi-agent research · evidence audit · reproducible execution traces")
with st.sidebar:
    st.header("Run settings")
    mode_label = st.radio("Execution mode", ["Offline demo", "Local Ollama", "Live AI"], help="Demo uses fixed samples; Local Ollama runs a model on your Mac; Live AI uses OpenAI.")
    mode = "demo" if mode_label == "Offline demo" else ("ollama" if mode_label == "Local Ollama" else "live")
    model_name = st.text_input("Model name", value="llama3.2:3b" if mode == "ollama" else "gpt-4.1-mini", disabled=mode == "demo", key=f"model_{mode}")
    revisions = st.slider("Maximum revision attempts", 0, 3, 1)
    st.divider()
    st.caption("Local Ollama requires Ollama running and a downloaded model (ollama pull llama3.2:3b). Live AI requires OPENAI_API_KEY and may incur API charges. Both research modes retrieve Wikipedia sources over the internet.")
    st.caption("The citation gate checks citation structure, not factual truth.")

question = st.text_area("Research question", value="How can AI agents improve customer support?", height=110)
run = st.button("▶ Run agents", type="primary", use_container_width=True)
status = st.empty()
if run:
    if not question.strip():
        st.warning("Enter a research question first.")
    else:
        try:
            st.session_state["last_state"] = run_agentflow(question.strip(), mode, model_name, revisions, status)
        except Exception as exc:
            st.error(f"Run failed: {exc}")

state = st.session_state.get("last_state")
if state is None:
    latest = Path("outputs/latest/trace.json")
    if latest.exists():
        try:
            st.info("A previous run is available below. Click Run agents to start a new one.")
            saved = json.loads(latest.read_text(encoding="utf-8"))
            from agentflow.core import Evidence, RunState
            saved["evidence"] = [Evidence(**e) for e in saved.get("evidence", [])]
            state = RunState(**saved)
        except (ValueError, TypeError, KeyError):
            st.warning("Could not load the previous run.")
if state is None:
    st.info("Choose a mode and click Run agents. Offline demo needs no API key.")
    st.stop()

st.divider()
a, b, c, d = st.columns(4)
a.metric("Mode", state.mode.upper())
b.metric("Sources", len(state.evidence))
c.metric("Citation audit", "PASS" if state.audit.get("passed") else "FLAGGED")
d.metric("Revisions", state.revisions)
report_tab, agents_tab, evidence_tab, audit_tab, export_tab = st.tabs(["📄 Report", "🧠 Agent activity", "🔎 Evidence", "🛡️ Quality checks", "⬇️ Export"])
with report_tab:
    if state.mode == "demo":
        st.warning("Offline demonstration: this report uses fixed sample responses, not live research. The output is not tailored to your question.")
    st.markdown(state.report)
with agents_tab:
    st.caption("Recorded stages in execution order. Durations are not currently measured.")
    for idx, event in enumerate(state.trace, 1):
        with st.expander(f"{idx:02d} · {event['agent'].replace('_', ' ').title()}", expanded=idx == 1):
            st.caption(event.get("timestamp", ""))
            output = event.get("output", "")
            if event["agent"] in {"researcher", "quality_gate"}:
                try:
                    st.json(json.loads(output))
                except ValueError:
                    st.code(output)
            else:
                st.markdown(output)
with evidence_tab:
    if not state.evidence:
        st.warning("No evidence was retrieved. Do not treat this run as verified research.")
    for item in state.evidence:
        with st.container(border=True):
            st.markdown(f"**[{item.id}] {item.title}**")
            st.write(item.excerpt)
            if item.url.startswith("https://"):
                st.link_button("Open source", item.url)
with audit_tab:
    st.json(state.audit)
    st.caption("A passing citation audit means source identifiers were formatted and present. It does not establish that sources support every claim.")
    st.markdown("**Critic's notes**")
    st.write(state.critique)
with export_tab:
    st.download_button("Download Markdown report", state.report, "agentflow-report.md", mime="text/markdown")
    st.download_button("Download JSON trace", json.dumps(asdict(state), indent=2, ensure_ascii=False), "agentflow-trace.json", mime="application/json")
    st.caption("Runs are also saved under outputs/runs/ and outputs/latest/.")
