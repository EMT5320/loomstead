# Loomstead Paper Workspace

This directory keeps the Loomstead paper workflow tied to concrete repository evidence: research claims, exported eval tables, figure plans, literature notes, BibTeX sources, and the LaTeX draft.

## Current writing target

- Working title: **Loomstead: Motivational Delegation for Process-Constrained Goals in Persistent Multi-Agent Narratives**
- Target shape: research preview / workshop / arXiv technical report draft.
- Core claim: a Director can shape motivation, opportunity, information, event pressure, resources, and constraints while autonomous NPCs choose actions through their own memory, relationships, heuristics, and tool capabilities.
- Evidence boundary: current results are rule-level scaffolding evidence from Process Fidelity, baseline / ablation, 24h / 72h stability, cross-domain adapter exports, and manifest checks. More seeds, LLM-backed runs, human believability scoring, and real Godot observer-mode validation remain open.

## Directory layout

```text
paper/
|-- README.md
|-- WORKFLOW.md
|-- outline.md
|-- claim_evidence_matrix.md
|-- figures.md
|-- references.bib
|-- generated/
|   |-- eval_tables.tex
|-- lit_review/
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
python -m compileall scripts
latexmk -pdf -cd -interaction=nonstopmode -halt-on-error -outdir=build paper/latex/main.tex
npm.cmd run paper:check
git diff --check
```

## Writing rules

- Keep claims evidence-linked.
- Label rule-level results as scaffolding evidence.
- Keep the town slice as the primary validation domain.
- Use the coding adapter as secondary portability evidence.
- Keep `paper/references.bib` and `paper/latex/references.bib` synchronized until the Zotero export path is automated.
