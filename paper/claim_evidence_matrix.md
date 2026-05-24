# Claim Evidence Matrix

| ID | Claim | Current support | Evidence source | Figure / table target | Missing evidence | Section |
| --- | --- | --- | --- | --- | --- | --- |
| C1 | Loomstead frames persistent narrative goals as process-constrained goals whose success requires trace evidence beyond final state. | verified design + partial runtime | `docs/research_framing_motivational_delegation.md`, `docs/process_fidelity_eval_spec.md`, README research section | Figure 1, Table 1 | More human-readable trace walkthroughs from real play windows | Introduction / Motivation |
| C2 | Motivational Delegation can satisfy process constraints while preserving agent-initiated action in current rule-level scenarios. | partial empirical | `.run/eval-runs/run_2026-05-23T12-25-11Z/summary.json`, `paper/generated/eval_summary_tables.md` | Table 2 | At least 5-10 seeds per scenario and non-rule provider runs | Experiments |
| C3 | Hard Delegation reaches final goals in the current process suite while producing shortcut and autonomy violations. | partial empirical | process fidelity ablation comparison | Table 2 | Stronger dynamic Hard Delegation baseline with recovery and replanning | Eval / Experiments |
| C4 | Relationship edges and evidence links are used as causal evidence in current ablation and replay scaffolds. | partial empirical | process fidelity summary, counterfactual replay artifacts, `docs/current_status.md` | Figure 4, Table 3 | Runtime-level memory-disable runs and more relationship-specific scenarios | Eval / Discussion |
| C5 | The trace schema covers decision, tool, interruption, and memory-observation events in the Phase 2 runtime. | verified by gate | `npm.cmd run smoke`, `npm.cmd run schema:check`, `GET /api/debug.phase2` implementation | Figure 3 | Trace replay UI validation in Godot ObserverPanel | System |
| C6 | The rule runtime remains stable over 24h and 72h simulated windows in the current exported runs. | verified by latest export | `.run/eval-runs/stability_2026-05-23T12-25-24Z/summary.json`, `.run/eval-runs/stability_2026-05-23T12-25-50Z/summary.json` | Table 4 | Repeated seeds and LLM-backed stability windows | Experiments |
| C7 | The DomainAdapter abstraction can export comparable summary schema across town and coding fixtures. | partial empirical | `.run/eval-runs/domain_2026-05-23T12-25-59Z/summary.json`, `docs/cross_domain_adapter.md` | Table 5 | More realistic dependency graphs, cross-file regressions, reviewer disagreement | Cross-domain Adapter |
| C8 | Current results should be presented as research-preview scaffolding evidence. | verified limitation | `README.md`, `docs/current_status.md`, eval summaries | Limitations box | More final empirical evidence before strong claims | Limitations |
| C9 | The first related-work framing can separate believable simulation, drama management, task-oriented multi-agent orchestration, and interactive agent evaluation. | verified literature seed | `paper/lit_review/source_index.md`, `paper/references.bib`, primary source pages | Table 6 | Add trace-debugging papers, human believability protocols, and exact Zotero keys | Related Work |

## Support labels

- `verified design`: grounded in active design docs.
- `verified by gate`: grounded in a current passing command.
- `partial empirical`: grounded in rule-level or small-sample exported runs.
- `planned`: proposed, still missing evidence.
