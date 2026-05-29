# Figure and Table Plan

## Figure 1: System overview

- Goal: show Godot Client, Python Agent Server, Director, Event Skill, NPC loop, ToolExecutor, memory stores, Debug / Eval export.
- Source files: `docs/agent_loop_architecture.md`, `README.md`, `backend/app/runtime/`, `backend/app/memory/`.
- Draft source: `paper/diagrams/system_overview.mmd`.
- Rendered assets: `paper/generated/figures/system_overview.svg`, `paper/generated/figures/system_overview.png`.
- LaTeX status: rendered PNG included in `paper/latex/sections/03_system.tex`.
- Status: draft source and rendered assets ready; publication-quality visual polish pending.

## Figure 2: Motivational Delegation loop

- Goal: show user goal -> GoalSpec -> indirect intervention -> NPC arbitration -> tool execution -> observation -> eval checkpoint.
- Source files: `docs/research_framing_motivational_delegation.md`, `docs/cross_domain_adapter.md`.
- Draft source: `paper/diagrams/motivational_delegation_loop.mmd`.
- Rendered assets: `paper/generated/figures/motivational_delegation_loop.svg`, `paper/generated/figures/motivational_delegation_loop.png`.
- LaTeX status: rendered PNG included in `paper/latex/sections/04_motivational_delegation.tex`.
- Status: draft source and rendered assets ready; publication-quality visual polish pending.

## Figure 3: Trace evidence chain

- Goal: visualize `intervention -> event -> subjective memory -> relationship edge / heuristic -> later decision -> outcome`.
- Source files: `GET /api/debug.phase2`, `paper/generated/manifest_inventory.md`, process trace artifacts.
- Draft source: `paper/diagrams/trace_evidence_chain_figure3.mmd`.
- Draft walkthrough: `paper/trace_walkthroughs/figure3_trace_walkthrough_pf_branna_seed01.md`.
- Draft artifact source: `.run/eval-promoted/run_2026-05-29T13-57-50Z/per_scenario/pf.branna_forgiveness_requires_memory_full_motivational_delegation_seed01.json`.
- Second trace source: `.run/eval-promoted/run_2026-05-29T13-57-50Z/per_scenario/pf.repair_talk_requires_memory_trace_full_motivational_delegation_seed01.json`.
- Rendered assets: `paper/generated/figures/trace_evidence_chain_figure3.svg`, `paper/generated/figures/trace_evidence_chain_figure3.png`, `paper/generated/figures/trace_evidence_chain_figure3.pdf`.
- LaTeX status: rendered PNG included in `paper/latex/sections/04_process_fidelity_eval.tex`.
- Status: editable Mermaid source and rendered assets ready with two current clean-run trace examples plus aggregate guardrail annotation; publication-quality visual polish remains pending.

## Table 1: Metric families

- Goal: summarize goal achievement, process fidelity, autonomy, memory causality, traceability, side effects.
- Source files: `docs/process_fidelity_eval_spec.md`.
- Status: drafted in `paper/latex/sections/04_process_fidelity_eval.tex`.

## Table 2: Process Fidelity ablation summary

- Goal: compare Full, Hard Delegation, No Subjective Memory, No Relationship Edge, Shuffled Memory Owner, Evidence-Link Removal.
- Source files: `.run/eval-promoted/run_2026-05-29T13-57-50Z/summary.json`, `.run/eval-promoted/run_2026-05-29T13-57-50Z/ablation_comparison.json`, `paper/generated/ablation_table.csv`, `paper/generated/eval_summary_tables.md`, `paper/generated/eval_tables.tex`.
- Status: generated from current clean five-repeat process run and included by `paper/latex/sections/05_experiments.tex`.

## Table 3: Memory causality and trace coverage

- Goal: show relationship memory causal use, causal trace coverage, relationship consistency.
- Source files: `.run/eval-promoted/run_2026-05-29T13-57-50Z/summary.json`, process suite counterfactual replay artifacts.
- Status: generated baseline table exists; detailed replay rows pending.

## Table 4: Stability

- Goal: 24h ticks, failures, interruptions, memory observations, heuristic references.
- Source files: latest stability summaries, `paper/generated/eval_tables.tex`.
- Status: generated from current run and included by `paper/latex/sections/05_experiments.tex`.

## Table 5: Cross-domain adapter

- Goal: town vs coding scenarios, deterministic repeat count, shared metrics, counterfactual route change rate, and fixture-level coding evidence pipeline.
- Source files: `.run/eval-promoted/domain_2026-05-28T07-49-46Z/summary.json`, manifest, `docs/cross_domain_adapter.md`, `paper/generated/eval_tables.tex`.
- Status: generated from current clean deterministic five-repeat domain run and included by `paper/latex/sections/05_experiments.tex`; wording should stay at interface / portability evidence.

## Table 6: Related-work positioning

- Goal: compare Loomstead with Generative Agents, Concordia, drama management, AutoGen, MetaGPT, ChatDev, and AgentBench.
- Source files: `paper/lit_review/source_index.md`, `paper/lit_review/*.md`, `paper/references.bib`.
- Status: related-work prose drafted; trace-debugging and human believability sources still pending.
