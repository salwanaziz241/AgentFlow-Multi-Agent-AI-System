"""Deterministic evidence checks. These are guardrails, not factual verification."""
import re
from dataclasses import dataclass, asdict

@dataclass
class Audit:
    passed: bool
    citation_count: int
    valid_citations: int
    unknown_citations: list[str]
    uncited_paragraphs: int
    coverage: float
    notes: list[str]

    def to_dict(self):
        return asdict(self)

def audit_report(report: str, source_ids: set[str]) -> Audit:
    citations = re.findall(r'\[(S\d+)\]', report)
    unknown = sorted(set(citations) - source_ids)
    valid = sum(c in source_ids for c in citations)
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', report) if p.strip()]
    substantive = [p for p in paragraphs if len(p) > 100 and not p.startswith('#')]
    uncited = sum(not any(f'[{sid}]' in p for sid in source_ids) for p in substantive)
    coverage = round((len(substantive)-uncited)/len(substantive), 2) if substantive else 0.0
    notes = []
    if unknown: notes.append('Unknown source IDs: ' + ', '.join(unknown))
    if uncited: notes.append(f'{uncited} substantial paragraph(s) lack a source reference')
    if not citations: notes.append('No inline source references found')
    if not source_ids: notes.append('No evidence retrieved')
    return Audit(bool(source_ids) and bool(valid) and not unknown and uncited == 0, len(citations), valid, unknown, uncited, coverage, notes)
