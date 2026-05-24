# Claim Policy

This file keeps the paper skeleton conservative while the implementation and experiments continue to mature.

## Claim levels

| Level | Label | Allowed wording | Required support |
| --- | --- | --- | --- |
| L0 | planned | "will test", "target", "placeholder" | Roadmap or design note. |
| L1 | implemented skeleton | "implemented path", "wired scaffold" | Code path plus passing local check. |
| L2 | local guardrail | "local rule-level guardrail", "scaffolding evidence" | Generated eval artifact plus manifest / command. |
| L3 | promoted evidence | "evidence suggests", "in promoted runs" | Promoted eval run, repeated seeds, clean manifest, documented config. |
| L4 | paper claim | "we find", "we show" | Target experiment set, baseline comparison, limitations reviewed. |

## Drafting rules

1. Keep Introduction and Method stable, but phrase results as contribution slots until evidence reaches L3 or L4.
2. Treat `paper/generated/` tables as build guards and claim placeholders by default.
3. Before adding strong comparative language, add or update a row in `paper/claim_evidence_matrix.md`.
4. If a claim depends on human believability, Godot observer UX, LLM-backed behavior, or repeated seeds, keep it at L0-L2 until that evidence exists.
5. Related Work should collect contrast points early, while final novelty language waits for a complete bibliography review.

## Current allowed summary

Safe current wording:

> Loomstead is a research-preview scaffold for studying motivational delegation and process fidelity in persistent multi-agent narratives. Current local rule-level runs validate the table/export pipeline and provide regression guardrails; final empirical claims require additional experiments.

Avoid for now:

- Broad superiority claims over existing multi-agent systems.
- Strong memory-causality claims without runtime-level ablation and more scenarios.
- Human-believability claims without rating protocol and results.
- Claims that the coding adapter proves real software-engineering performance.
