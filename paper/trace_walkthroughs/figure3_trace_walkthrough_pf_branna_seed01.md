# Figure 3 Trace Walkthrough Draft (research-preview)

## Scope and evidence level

- Intended figure: Figure 3 (`intervention -> event -> subjective memory -> relationship/heuristic -> later decision -> outcome`)
- Claim level target: L2 local guardrail evidence (per `paper/claim_policy.md`)
- This draft uses one clean exported artifact and stays in interface/research-preview wording.

## Source artifact

- Run: `.run/eval-runs/run_2026-05-27T13-37-33Z`
- Manifest: `.run/eval-runs/run_2026-05-27T13-37-33Z/manifest.json`
  - `ok=true`
  - `git.shortCommit=71e9f07`
  - `git.dirty=false`
  - `seedCount=5`
- Per-scenario file:
  - `.run/eval-runs/run_2026-05-27T13-37-33Z/per_scenario/pf.branna_forgiveness_requires_memory_full_motivational_delegation_seed01.json`

## Candidate trace chain for Figure 3

1. **Intervention/setup anchor**
   - `scenarioId=pf.branna_forgiveness_requires_memory`
   - `setupKind=forgiveness_memory`
   - Seeded harm memory:
     - `harmEventId=evt_485d0da457cd4ad1b4a992914c672653`
     - `recordId=evt_485d0da457cd4ad1b4a992914c672653:bram:harm`

2. **Tool event (goal-relevant action)**
   - `eventType=tool.execution_completed`
   - `eventId=evt_aa11706eb4b4408b9f92df85fd7546a4`
   - `toolId=social.chat_with`
   - `targetNpcId=player`
   - Trace refs include:
     - subjective memory refs (`count=1`)
     - heuristic refs (`count=1`)
     - motivation decision trace (`eventId=evt_f3aae51dfcdc4ba5a4f09580ea98f4fe`)

3. **Observed memory result (trace-link bridge)**
   - `eventType=memory.result_observed`
   - `eventId=evt_6223740588d04bb5a242b7063554154e`
   - `sourceEventId=evt_aa11706eb4b4408b9f92df85fd7546a4`
   - `observerVisibility=participants_only`
   - `memoryCount=2`
   - `relationshipEdgeCount=3`

4. **Subjective memory + relationship + heuristic evidence**
   - Subjective memory records include:
     - `evt_485d0da457cd4ad1b4a992914c672653:bram:harm` (negative valence)
     - `evt_aa11706eb4b4408b9f92df85fd7546a4:bram` (current interaction)
   - Relationship edges include:
     - `bram::player::trust` (`strength=0.52`)
     - `bram::player::affection` (`strength=0.53`)
   - Heuristic refs include designer seed and preference heuristics.

5. **Later decision and counterfactual replay**
   - With relationship memory: `social.chat_with`
   - Without relationship memory: `social.give_gift`
   - `toolSelectionChanged=true`
   - `counterfactualToolSelectionChangeRate=0.5`
   - Replay stats:
     - `cycleCount=24`
     - `comparisonCount=48`
     - `changedDecisionCount=24`

6. **Outcome snapshot (for this seed)**
   - `goal_success_rate=1.0`
   - `required_process_coverage=1.0`
   - `causal_trace_coverage=1.0`
   - `relationship_memory_causal_use_rate=1.0`
   - `process_believability_score=1.0`
   - Process checks listed in the artifact are all `true`.

## Figure drafting notes (manual follow-up required)

- The event summaries in the artifact include mojibake-like strings; figure labels should use curated wording instead of raw summary text.
- This walkthrough uses one seed from one scenario and is suitable for an illustrative trace panel.
- Publication-ready Figure 3 should add either:
  - a second trace from a different scenario, or
  - a compact aggregate annotation from `counterfactual_replay.jsonl`.
