# Loomstead Paper Workflow

## 1. Repository orientation

Read these sources first:

- `paper/claim_policy.md`
- `docs/research_framing_motivational_delegation.md`
- `docs/process_fidelity_eval_spec.md`
- `docs/cross_domain_adapter.md`
- `docs/agent_loop_architecture.md`
- `docs/current_status.md`

Goal: confirm the paper claim slots, evidence sources, unfinished experiments, current limitations, and allowed claim strength.

## 2. Evidence refresh

Routine refresh:

```powershell
npm.cmd run eval:archive:check
npm.cmd run eval:archive:drift
python scripts/paper_extract_eval_tables.py
```

This refreshes `paper/generated/eval_summary_tables.md`, `paper/generated/ablation_table.csv`, `paper/generated/latest_runs.json`, `paper/generated/manifest_inventory.md`, and `paper/generated/eval_tables.tex`.

When new evidence is needed:

```powershell
npm.cmd run eval:process:export
npm.cmd run eval:stability:export
npm.cmd run eval:stability:long:export
npm.cmd run eval:domain:export
npm.cmd run eval:archive:check
npm.cmd run eval:archive:drift
python scripts/paper_extract_eval_tables.py
```

## 3. Claim-first drafting

Before writing prose, update `paper/claim_evidence_matrix.md`:

1. Write the claim.
2. Bind it to a concrete evidence source.
3. Mark support as verified / partial / planned.
4. Add the missing evidence.
5. Assign the target figure or table.

Keep claim strength aligned with `paper/claim_policy.md`. Early sections should reserve stable skeleton slots and avoid final empirical phrasing until evidence is promoted.

## 4. Literature workflow

- Use Zotero as the formal citation library.
- Use `paper/lit_review/zotero_intake_workflow.md` as the browser + Zotero intake checklist.
- Keep `paper/references.bib` and `paper/latex/references.bib` limited to cited or actively planned references; keep them in sync until a Zotero export helper is added.
- Use `scripts/paper_search.py` for metadata discovery and reading-queue updates.
- Use `paper/lit_review/*.md` for short notes, contrast points, and citation placement.

## 5. LaTeX build

Minimal build command:

```powershell
latexmk -pdf -cd -interaction=nonstopmode -halt-on-error -outdir=build paper/latex/main.tex
```

Build outputs live under `paper/latex/build/`; source files stay under `paper/latex/`. The draft currently inputs generated tables from `paper/generated/eval_tables.tex`.

## 6. Closeout checks

```powershell
python scripts/check_paper_tooling.py --json
python -m compileall scripts
python scripts/paper_extract_eval_tables.py
latexmk -pdf -cd -interaction=nonstopmode -halt-on-error -outdir=build paper/latex/main.tex
npm.cmd run paper:check
git diff --check
```

If a session only changes paper text, the full project gate can be skipped. Changes to eval, schema, runtime, or factual docs should still run the relevant project gate.
