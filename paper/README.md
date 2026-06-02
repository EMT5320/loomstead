# Loomstead Paper Workspace

This directory keeps the Loomstead paper workflow tied to concrete repository evidence: research claims, exported eval tables, figure plans, literature notes, BibTeX sources, and the LaTeX draft.

## Current writing target

- Working title: **Loomstead: An Explainable Multi-Agent Narrative Runtime**
- Target shape: portfolio engineering write-up / research-preview notes, not the current thesis or paper mainline.
- Core claim: the system demonstrates agent orchestration, structured trace observability, legal tool execution, memory / relationship evidence capture, and eval-infra engineering for process auditing.
- Evidence boundary: `C2`/`C3`/`C4` are owner-approved only at the metric / explainability level, backed by the 2026-05-29 cloud Process Fidelity bundle. Human-believability scoring is closed as infeasible on current data until behavior-divergent baselines exist.
- Current drafting policy: keep the paper workspace as supporting material for the portfolio story; do not invest in new empirical framing or presentation polish unless Loomstead is re-promoted to a research mainline.

## Directory layout

```text
paper/
|-- README.md
|-- WORKFLOW.md
|-- outline.md
|-- blog_main.md
|-- claim_evidence_matrix.md
|-- figures.md
|-- claim_policy.md
|-- references.bib
|-- diagrams/
|-- generated/
|   |-- figures/
|   |-- eval_tables.tex
|-- lit_review/
|   |-- prior_related_work_inventory.md
|   |-- trace_provenance_attribution.md
`-- latex/
```

## Per-session loop

1. Run new evals or identify the latest promoted run.
2. Refresh `paper/generated/` with `python scripts/paper_extract_eval_tables.py`; this updates Markdown, CSV, JSON, and LaTeX table artifacts.
3. Update `claim_evidence_matrix.md` so each claim has evidence and a missing-evidence note.
4. Update `figures.md` so each planned figure has a source and status.
5. Compile `paper/latex/main.tex` to keep the draft buildable.

## Key commands

```powershell
python scripts/check_paper_tooling.py --json
python scripts/paper_extract_eval_tables.py
npm.cmd run paper:figures
python -m compileall scripts
latexmk -pdf -cd -interaction=nonstopmode -halt-on-error -outdir=build paper/latex/main.tex
npm.cmd run paper:check
git diff --check
```

## Writing rules

- Keep claims evidence-linked.
- Prefer skeleton placeholders over early overclaiming.
- Label rule-level results as scaffolding evidence.
- Keep the town slice as the primary validation domain.
- Use the coding adapter as secondary portability evidence.
- Keep `paper/references.bib` and `paper/latex/references.bib` synchronized until the Zotero export path is automated.
- Mermaid figure sources live in `paper/diagrams/`; render them with `npm.cmd run paper:figures` into `paper/generated/figures/`.
