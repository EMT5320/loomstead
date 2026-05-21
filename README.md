# Loomstead

![Status: research preview](https://img.shields.io/badge/status-research_preview-6f42c1)
![Phase: 1 to 2](https://img.shields.io/badge/phase-1_%E2%86%92_2-0366d6)
![Primary domain: narrative town slice](https://img.shields.io/badge/primary_domain-narrative_town_slice-22863a)

> An explainable multi-agent narrative runtime for motivational delegation and process fidelity evaluation.

`Loomstead` uses a playable Godot town slice as the primary validation domain for studying process-constrained goals in persistent multi-agent narratives. The project focuses on how a Director can shape motivation, opportunity, information, resources, event pressure, and constraints so autonomous NPC agents weave believable social processes instead of receiving hard task assignments or direct state edits.

Short research tagline:

```text
Motivational Delegation for process-constrained goals in persistent multi-agent narratives.
```

For orientation, agent assistants can start with [AGENTS.md](AGENTS.md) and [docs/agent_context.md](docs/agent_context.md). Current implementation facts live in [docs/current_status.md](docs/current_status.md), long-term direction in [docs/project_vision.md](docs/project_vision.md), and research framing in [docs/research_framing_motivational_delegation.md](docs/research_framing_motivational_delegation.md).

## Why Loomstead

`Loom` points to the project’s core mechanic: relationships, memories, interventions, and consequences are woven into traceable processes. `Stead` keeps the homestead / town-slice grounding that makes those processes visible to players and evaluators.

The town is not a generic demo wrapper. It is the primary validation domain because Process Fidelity needs scenes where humans can intuitively judge whether a process feels earned:

- “Kai and Mira become close friends” cannot be reduced to a relationship score.
- “Branna forgives the player” cannot be reduced to `forgiven=true`.
- “The Starlight Festival succeeds” cannot be reduced to `festival_success=true`.

The value is in the path: motivation shifts, shared events, misunderstanding repair, witness reactions, subjective memory formation, and later behavior that references those memories.

## Project identity

- **Research status**: research preview.
- **Current phase**: Phase 1 is closed; Phase 2 skeleton work is starting.
- **Primary domain**: narrative town slice.
- **Secondary domain**: task / coding adapters for portability checks, not the main product direction.
- **Differentiation**: few-but-deep NPCs, explainable traces, process fidelity evaluation.

Core axes:

- **Few but deep**: 4 core NPCs + 2 stub NPCs in Phase 2, emphasizing subjective memory, relationship evolution, heuristics, and explainable decisions over scale.
- **Explainable**: Director interventions, Event Skill activation, NPC decisions, tool calls, world changes, subjective memories, and relationship deltas are traceable.
- **Evaluable**: Process Fidelity Eval checks shortcut violations, forced actions, required process coverage, relationship-memory causal use, and Director overreach.
- **Player-visible**: research claims surface as on-screen NPC behavior, event reactions, relationship changes, memory differences, observer views, or Debug traces.

## Entry points

### For research readers

Start here if you care about the research claim, evaluation setup, baselines, or future dataset:

1. [Research framing](docs/research_framing_motivational_delegation.md): narrative-primary / task-secondary, Motivational Delegation, Process Fidelity, rebuttal map.
2. [Process Fidelity Eval spec](docs/process_fidelity_eval_spec.md): metrics, Hard Delegation baseline, ablation protocol, GoalSpec schema, dataset outputs.
3. [Project vision](docs/project_vision.md): long-term differentiation, success criteria, player-visible experience, research/product boundary.
4. [Agent loop architecture](docs/agent_loop_architecture.md): NPC motivation loop, tools, subjective memory, heuristic learning, arbitration, eval skeleton.
5. [Cross-domain adapter](docs/cross_domain_adapter.md): how the same research abstractions may later leave the town domain.

### For developers

Start here if you want to run, modify, or validate the project locally:

1. [Current status](docs/current_status.md): implemented facts, verification state, gaps, and manual validation notes.
2. [Goal board](docs/goal_board.md): active lanes, collaboration notes, validation commands, recommended schedule.
3. [Documentation index](docs/README.md): source-of-truth map and task-line reading routes.
4. [Godot client README](clients/godot/README.md): client entry point and Godot environment notes.
5. [Model profile guide](docs/model_profile_template_guide.md): local model config, provider routing, and real LLM smoke workflow.

## Current stage

### Phase 1: living world slice

Closed as the current playable baseline on 2026-05-21:

- Python Agent Server as authoritative world state.
- `GET /api/world/state`, `POST /api/player/action`, `POST /api/world/tick`, Debug / Memory / model config APIs.
- Rule-based Director v0 and one Event Skill: Starlight Festival shortage.
- Godot `world_main.tscn` with player movement, NPC map sprites, tick-driven NPC movement/action states, world pulse panel, remote event compass, `E` talk, and VN feedback panel.
- Six first-launch NPC deep cards with voice anchors, relationship stages, gift reactions, monologue seeds, gossip hooks, and life-action seeds.

Phase 1 is now frozen for regression fixes only. New agent-system work moves to Phase 2.

### Phase 2: runtime skeleton

Starting now. Planned skeleton work includes:

- ToolDefinition registry and three-layer tool model.
- MotivationEngine replacing the old `LifeActionExecutor`.
- CapabilityRegistry for dynamic tool filtering.
- SubjectiveMemoryStore and RelationshipEdgeStore.
- HeuristicLibrary and failure-driven learning.
- ArbitrationLayer with `contributing_sources` trace.
- World entity schemas for farm plots, items, inventory, shops, buildings, time, and weather.
- EvalFramework with baselines, memory ablations, Counterfactual Replay, and dataset exports.
- Observer mode in Godot.

Phase 2 is planned to retire the old `LifeActionExecutor` directly rather than running it in parallel with MotivationEngine.

## Runtime shape

```text
Godot Client
  ├─ Player movement / VN presentation / NPC and event visualization
  └─ Observer mode and Debug UI (Phase 2+)

Python Agent Server
  ├─ World / Simulation: authoritative world state and legal tool execution
  ├─ Director: low-frequency narrative pacing and indirect interventions
  ├─ Event Skill: localized pressure, constraints, outcomes, fallback text, asset hints
  ├─ NPC Agent Loop: motivation, capability filtering, subjective memory, heuristics, arbitration
  ├─ Provider: RuleBasedProvider + OpenAI-compatible CloudApiProvider
  └─ Eval / Debug: traces, ablations, Process Fidelity metrics, dataset export
```

Research chain:

```text
Process-constrained Goal
  -> Director Interventions
  -> NPC Motivation / Opportunity / Information / Constraint Changes
  -> Autonomous Tool Actions
  -> Objective Event Log
  -> Subjective Memory Views + Relationship Edges
  -> Process Fidelity Eval + Debug Trace
```

## Local run

Use Windows PowerShell and `npm.cmd` for the least surprising local behavior.

### Start the Python server

```powershell
npm.cmd run start
```

### Open the Godot client

```powershell
npm.cmd run client:run
```

The default scene is `clients/godot/scenes/world_main.tscn`. The legacy P0 UI remains available:

```powershell
npm.cmd run client:run:legacy
```

### Common checks

```powershell
npm.cmd run context:check
npm.cmd run check
npm.cmd run smoke
npm.cmd run asset:check
npm.cmd run client:env
npm.cmd run client:run:check
git diff --check
```

Choose the smallest relevant command for the task. For context-governance changes, run at least `npm.cmd run context:check` and `git diff --check`.

## Model configuration

Committed config defaults to rule fallback so the project can run without secrets.

- Template: `config/models.example.json`
- Local ignored config: `config/models.json`, `config/models.local.json`
- Recommended check:

```powershell
npm.cmd run model:check
```

The current environment-variable prefix remains `AGENT_TOWN_*` for compatibility with existing scripts, local configs, and smoke tests. Do not treat that prefix as the long-term brand. Phase 2 skeleton work may migrate these to `LOOMSTEAD_*` with a compatibility shim.

Examples that intentionally remain valid today:

```powershell
$env:AGENT_TOWN_REQUIRE_REAL_LLM_SMOKE = "1"
$env:AGENT_TOWN_MODEL_CONFIG = "config/models.local.json"
```

API keys stay in local ignored config or environment variables, outside committed files.

## Repository metadata checklist

Remote GitHub metadata is managed outside this commit because it affects shared repository state.

Recommended remote updates:

- Rename the repository to `loomstead`; keep GitHub’s automatic redirect from the old URL.
- Set About / description to:

```text
A narrative-primary multi-agent runtime for motivational delegation and process fidelity evaluation.
```

- Set topics:

```text
multi-agent
llm-agent
process-fidelity
narrative-simulation
agent-evaluation
motivational-delegation
```

## Citation

Citation information will be added when the research preprint or technical report is available.

## Development Notes

- Backend Runtime owns authoritative world state.
- Godot reads state, submits legal player actions, and presents results.
- LLM output enters visible state through parsing, validation, fallback, and event recording.
- New NPCs, locations, events, tools, save fields, or Debug fields usually start with a data contract.
- Unverified behavior is tracked as pending or manually unverified rather than completed.
- Secrets, local absolute paths, unregistered assets, and temporary runtime files stay outside committed files.
