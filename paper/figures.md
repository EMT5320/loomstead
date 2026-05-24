# Figure and Table Plan

## Figure 1: System overview

- Goal: show Godot Client, Python Agent Server, Director, Event Skill, NPC loop, ToolExecutor, memory stores, Debug / Eval export.
- Source files: `docs/agent_loop_architecture.md`, `README.md`, `backend/app/runtime/`, `backend/app/memory/`.
- Status: planned.

## Figure 2: Motivational Delegation loop

- Goal: show user goal -> GoalSpec -> indirect intervention -> NPC arbitration -> tool execution -> observation -> eval checkpoint.
- Source files: `docs/research_framing_motivational_delegation.md`, `docs/cross_domain_adapter.md`.
- Status: planned.

## Figure 3: Trace evidence chain

- Goal: visualize `intervention -> event -> subjective memory -> relationship edge / heuristic -> later decision -> outcome`.
- Source files: `GET /api/debug.phase2`, `paper/generated/manifest_inventory.md`, process trace artifacts.
- Status: needs concrete exported trace snippet.

## Table 1: Metric families

- Goal: summarize goal achievement, process fidelity, autonomy, memory causality, traceability, side effects.
- Source files: `docs/process_fidelity_eval_spec.md`.
- Status: draftable now.

## Table 2: Process Fidelity ablation summary

- Goal: compare Full, Hard Delegation, No Subjective Memory, No Relationship Edge, Shuffled Memory Owner, Evidence-Link Removal.
- Source files: `paper/generated/ablation_table.csv`, `paper/generated/eval_summary_tables.md`.
- Status: generated from current run.

## Table 3: Memory causality and trace coverage

- Goal: show relationship memory causal use, causal trace coverage, relationship consistency.
- Source files: process suite summary and counterfactual replay artifacts.
- Status: generated baseline table exists; detailed replay rows pending.

## Table 4: Stability

- Goal: 24h / 72h ticks, failures, interruptions, memory observations, heuristic references.
- Source files: latest stability summaries.
- Status: generated from current run.

## Table 5: Cross-domain adapter

- Goal: town vs coding scenarios and shared metrics.
- Source files: latest domain summary and manifest.
- Status: generated from current run.

## Table 6: Related-work positioning

- Goal: compare Loomstead with Generative Agents, Concordia, drama management, AutoGen, MetaGPT, ChatDev, and AgentBench.
- Source files: `paper/lit_review/source_index.md`, `paper/lit_review/*.md`, `paper/references.bib`.
- Status: first seed pass complete; trace-debugging and human believability sources still pending.
