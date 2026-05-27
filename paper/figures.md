# Figure and Table Plan

## Figure 1: System overview

- Goal: show Godot Client, Python Agent Server, Director, Event Skill, NPC loop, ToolExecutor, memory stores, Debug / Eval export.
- Source files: `docs/agent_loop_architecture.md`, `README.md`, `backend/app/runtime/`, `backend/app/memory/`.
- Draft source: `paper/diagrams/system_overview.mmd`.
- LaTeX status: boxed placeholder included in `paper/latex/sections/03_system.tex`.
- Status: draft source ready; rendered PDF/SVG asset pending.

## Figure 2: Motivational Delegation loop

- Goal: show user goal -> GoalSpec -> indirect intervention -> NPC arbitration -> tool execution -> observation -> eval checkpoint.
- Source files: `docs/research_framing_motivational_delegation.md`, `docs/cross_domain_adapter.md`.
- Draft source: `paper/diagrams/motivational_delegation_loop.mmd`.
- LaTeX status: boxed placeholder included in `paper/latex/sections/04_motivational_delegation.tex`.
- Status: draft source ready; rendered PDF/SVG asset pending.

## Figure 3: Trace evidence chain

- Goal: visualize `intervention -> event -> subjective memory -> relationship edge / heuristic -> later decision -> outcome`.
- Source files: `GET /api/debug.phase2`, `paper/generated/manifest_inventory.md`, process trace artifacts.
- Status: needs concrete exported trace snippet.

## Table 1: Metric families

- Goal: summarize goal achievement, process fidelity, autonomy, memory causality, traceability, side effects.
- Source files: `docs/process_fidelity_eval_spec.md`.
- Status: drafted in `paper/latex/sections/04_process_fidelity_eval.tex`.

## Table 2: Process Fidelity ablation summary

- Goal: compare Full, Hard Delegation, No Subjective Memory, No Relationship Edge, Shuffled Memory Owner, Evidence-Link Removal.
- Source files: `paper/generated/ablation_table.csv`, `paper/generated/eval_summary_tables.md`, `paper/generated/eval_tables.tex`.
- Status: generated from current run and included by `paper/latex/sections/05_experiments.tex`.

## Table 3: Memory causality and trace coverage

- Goal: show relationship memory causal use, causal trace coverage, relationship consistency.
- Source files: process suite summary and counterfactual replay artifacts.
- Status: generated baseline table exists; detailed replay rows pending.

## Table 4: Stability

- Goal: 24h ticks, failures, interruptions, memory observations, heuristic references.
- Source files: latest stability summaries, `paper/generated/eval_tables.tex`.
- Status: generated from current run and included by `paper/latex/sections/05_experiments.tex`.

## Table 5: Cross-domain adapter

- Goal: town vs coding scenarios, deterministic repeat count, shared metrics, counterfactual route change rate, and fixture-level coding evidence pipeline.
- Source files: `.run/eval-runs/domain_2026-05-27T13-29-21Z/summary.json`, manifest, `docs/cross_domain_adapter.md`, `paper/generated/eval_tables.tex`.
- Status: generated from current clean deterministic five-repeat domain run and included by `paper/latex/sections/05_experiments.tex`; wording should stay at interface / portability evidence.

## Table 6: Related-work positioning

- Goal: compare Loomstead with Generative Agents, Concordia, drama management, AutoGen, MetaGPT, ChatDev, and AgentBench.
- Source files: `paper/lit_review/source_index.md`, `paper/lit_review/*.md`, `paper/references.bib`.
- Status: related-work prose drafted; trace-debugging and human believability sources still pending.
