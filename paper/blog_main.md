# Loomstead: Motivational Delegation for Process-Constrained Narrative Agents

`Loomstead` is a research-preview multi-agent narrative runtime built around a playable Godot town slice. The project asks a focused question: can a Director steer long-running narrative goals by shaping context while NPCs still choose their own actions through motivation, memory, relationships, tools, and heuristics?

The current portfolio story has three layers:

1. **Playable surface**: a Godot town with NPCs, events, observer mode, and trace inspection.
2. **Runtime mechanism**: a Python Agent Server where `MotivationEngine -> ToolExecutor -> ResultObserver` is the active decision path.
3. **Evaluation layer**: Process Fidelity checks whether a goal was achieved through a credible path.

Recommended figures:

- System overview: [`paper/generated/figures/system_overview.png`](generated/figures/system_overview.png)
- Motivational Delegation loop: [`paper/generated/figures/motivational_delegation_loop.png`](generated/figures/motivational_delegation_loop.png)
- Trace evidence chain: [`paper/generated/figures/trace_evidence_chain_figure3.png`](generated/figures/trace_evidence_chain_figure3.png)

## 1. The problem: final state is too weak for narrative agents

Persistent narrative goals are often easy to encode as final states:

- Branna forgives the player.
- Kai and Mira become close.
- A festival succeeds.

Those final states lose the part players care about: the earned path. Loomstead treats these as **process-constrained goals**. A successful run should show intervening events, subjective memory formation, relationship movement, later decisions that reference those memories, and an auditable trace chain.

The town slice exists because these failures are readable. When an NPC instantly forgives someone after a hidden flag flips, the result feels brittle. When the NPC recalls an event, chooses a social tool, updates trust, and later acts differently, the system exposes the causal path that made the outcome credible.

## 2. The method: Motivational Delegation

Motivational Delegation is the project’s name for indirect Director control. The Director shapes:

- motivation,
- opportunity,
- information,
- event pressure,
- resource constraints,
- available tools.

NPCs then arbitrate among legal tools using their own state. The Director can create a reason to act, expose an opportunity, or add pressure, while the runtime keeps action selection inside the NPC loop.

The current implementation routes Phase 2 tick decisions through:

```text
MotivationEngine -> ToolExecutor -> ResultObserver
```

The supporting stores include subjective memory, relationship edges, heuristic seeds, capability preferences, and trace references. Godot remains the presentation layer; the Python server owns the authoritative world state and legal tool execution.

## 3. The evaluation layer: Process Fidelity

Process Fidelity Eval measures path quality in addition to goal completion. The current promoted process run is:

```text
.run/eval-promoted/run_2026-05-29T13-57-50Z
```

It covers:

- 4 Process Fidelity GoalSpecs,
- 5 seeds,
- 5 baselines,
- 20/20 full-baseline process checks,
- 100 cloud-provider arbitration records,
- 0 fallback calls.

Current `C2`/`C3`/`C4` claim status is **promoted with caveat** after owner review:

- **C2**: Motivational Delegation satisfies current process constraints while preserving agent-initiated action.
- **C3**: Hard Delegation reaches final goals while producing shortcut and autonomy violations.
- **C4**: relationship edges and evidence links act as causal evidence in current ablation and replay scaffolds.

The key contrast is visible in the Hard Delegation baseline. It reaches `goal_success_rate=1.0`, then collapses path-quality metrics: `required_process_coverage=0.185714`, `forced_action_rate=1.0`, `agent_initiated_action_ratio=0.0`, `causal_trace_coverage=0.0`, and `shortcut_violation_rate=1.0`.

That result supports the evaluation story: goal completion alone can hide forced or shortcut paths.

## 4. Trace walkthrough: one concrete evidence chain

The Figure 3 walkthrough uses:

```text
paper/trace_walkthroughs/figure3_trace_walkthrough_pf_branna_seed01.md
```

The Branna forgiveness trace shows:

1. a seeded harm memory,
2. a later `social.chat_with` tool event,
3. a `memory.result_observed` bridge event,
4. updated subjective memory and relationship edges,
5. counterfactual replay where the selected tool changes when relationship memory is removed,
6. full process metrics for the seed.

The same figure also references a Tomas repair trace to show the pattern across another scenario. The diagram source is [`paper/diagrams/trace_evidence_chain_figure3.mmd`](diagrams/trace_evidence_chain_figure3.mmd), and the rendered PNG is available in [`paper/generated/figures/trace_evidence_chain_figure3.png`](generated/figures/trace_evidence_chain_figure3.png).

## 5. Current caveats

This is research-preview evidence. External wording should keep these boundaries:

- `C2`/`C3`/`C4` can be described as **promoted with caveat**.
- Final empirical wording still needs human process ratings, broader scenario coverage, and stronger dynamic baselines; the current blind pilot gate is tracked in `docs/human_rating_pilot_gate.md`.
- The promoted process run still carries a machine-level `needs_manual_review` status because it was exported during a dirty closure pass and drift policy asks for human explanation.
- Godot observer-mode visuals are implemented, while the newest real-window capture remains a manual verification task.

## 6. Portfolio demo path

For a short showcase, record the Godot town and observer dock with the backend running:

```powershell
npm.cmd run client:env
npm.cmd run start
npm.cmd run client:run
```

Use the capture script in [`docs/demo_capture_plan.md`](../docs/demo_capture_plan.md). The strongest 60-second arc is:

1. living town,
2. player/NPC interaction,
3. event result,
4. observer dock,
5. trace filtering and copyable evidence,
6. closing frame with `/api/debug.phase2`.

The intended takeaway is simple: Loomstead is a playable town slice, an explainable agent runtime, and an evaluation harness for whether narrative outcomes were earned through a credible process.
