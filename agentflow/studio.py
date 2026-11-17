"""Produce a self-contained, local HTML run viewer without a web server."""
import html
import json
from pathlib import Path

STYLE = '''
:root{font-family:Inter,ui-sans-serif,system-ui,sans-serif;color:#e8ecf5;background:#090e1a}
*{box-sizing:border-box}body{margin:0}.shell{max-width:1180px;margin:auto;padding:36px 24px}
.eyebrow{color:#8ca8f9;letter-spacing:.15em;text-transform:uppercase;font-size:11px;font-weight:700}
h1{font-size:clamp(30px,5vw,52px);letter-spacing:-.05em;margin:10px 0}h2{font-size:18px;margin:0 0 15px}
p{color:#aebad0;line-height:1.65}.muted{color:#8494ad}.top{display:flex;justify-content:space-between;gap:20px;align-items:center}
.pill{border:1px solid #344263;padding:8px 12px;border-radius:100px;font-size:12px;color:#b9c9e8}
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:26px 0}.metric,.panel{border:1px solid #25314a;background:#111a2c;border-radius:16px;padding:22px}
.metric strong{display:block;font-size:30px;margin-top:8px}.metric span{color:#9baac5;font-size:12px}
.layout{display:grid;grid-template-columns:1fr 1fr;gap:16px}.wide{grid-column:1/-1}
.steps{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0}.step{background:#192743;border:1px solid #32476c;padding:9px 13px;border-radius:9px;color:#bcd1fb;font-size:13px}
pre{white-space:pre-wrap;word-break:break-word;background:#0b1220;border:1px solid #263550;padding:16px;border-radius:10px;max-height:380px;overflow:auto;color:#d2ddef;font-size:12px;line-height:1.65}
.source{padding:12px 0;border-bottom:1px solid #263550}.source a{color:#9abaff;overflow-wrap:anywhere}
details{border-bottom:1px solid #29364e;padding:12px 0}summary{cursor:pointer;font-weight:600}summary span{color:#8494ad;font-size:12px;margin-left:10px}
.good{color:#72d5b0}.warn{color:#ffce82}footer{padding:24px 0;color:#71809b;font-size:12px}
@media(max-width:700px){.metrics{grid-template-columns:repeat(2,1fr)}.layout{grid-template-columns:1fr}.wide{grid-column:auto}.top{display:block}}
'''

def render_dashboard(state, output: str | Path) -> Path:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    esc = lambda v: html.escape(str(v), quote=True)
    audit = state.audit or {}
    status = 'Passed automated citation checks' if audit.get('passed') else 'Review required'
    evidence_html = ''.join(f'<div class="source"><b>[{esc(e.id)}] {esc(e.title)}</b><p>{esc(e.excerpt[:240])}</p><a href="{esc(e.url)}" target="_blank" rel="noopener noreferrer">Open source</a></div>' for e in state.evidence)
    trace_html = ''.join(f'<details><summary>{esc(t["agent"].title())}<span>{esc(t.get("duration_ms", "—"))} ms</span></summary><pre>{esc(t["output"])}</pre></details>' for t in state.trace)
    metrics = [('Agent steps',len(state.trace)),('Sources',len(state.evidence)),('Citation coverage',f'{int(audit.get("coverage",0)*100)}%'),('Revisions',state.revisions)]
    metrics_html = ''.join(f'<div class="metric"><span>{esc(label)}</span><strong>{esc(value)}</strong></div>' for label,value in metrics)
    report = esc(state.report)
    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>AgentFlow | Run Studio</title><style>{STYLE}</style></head><body><main class="shell"><div class="top"><div><div class="eyebrow">AgentFlow / Run Studio</div><h1>Research, with receipts.</h1><p>Explore how specialized agents turned a question into a source-backed report.</p></div><span class="pill">{esc(state.mode.upper())} RUN</span></div><section class="panel"><div class="eyebrow">Research question</div><h2 style="margin-top:12px">{esc(state.question)}</h2><div class="steps">{''.join(f'<span class="step">{esc(x)}</span>' for x in ['Plan','Retrieve','Analyze','Critique','Draft','Audit','Revise'])}</div><span class="{'good' if audit.get('passed') else 'warn'}">● {esc(status)}</span><p class="muted" style="font-size:12px">Citation coverage is a formatting/evidence-reference check, not proof that claims are true.</p></section><section class="metrics">{metrics_html}</section><div class="layout"><section class="panel"><h2>Evidence library</h2>{evidence_html or '<p>No evidence retrieved.</p>'}</section><section class="panel"><h2>Quality gate</h2><p><b>{esc(status)}</b></p><p>{esc('; '.join(audit.get('notes',[])) or 'No structural citation issues detected.')}</p><pre>{esc(json.dumps(audit,indent=2))}</pre></section><section class="panel wide"><h2>Agent activity</h2><p>Open any step to inspect its output.</p>{trace_html}</section><section class="panel wide"><h2>Generated report</h2><pre>{report}</pre></section></div><footer>AgentFlow · Offline demo uses fixtures; live mode uses an LLM and Wikipedia. Always review sources before relying on a report.</footer></main></body></html>'''
    target = output / 'dashboard.html'
    target.write_text(page, encoding='utf-8')
    return target
