---
status: archive
owner_lane: research-quality
last_verified: 2026-06-02
startup_load: on-demand
source_of_truth: false
scope: Human Rating Pilot 的预注册 gate（2026-06-02 评估为前提不成立、已关闭，保留为方法论记录）
---

# Human Rating Pilot Gate

> 自管理层归档记录。2026-06-02 已关闭；不再作为当前 gate、命令入口或展示材料依据。

## 1. 关闭结论

- `hard_delegation` 是 metric stub：`backend/app/eval/runner.py` 的 `_run_hard_delegation_process_scenario` 不跑 `AgentRuntime.tick`，没有可供 reviewer 比较的真实 runtime 过程。
- Memory / relationship ablation 输入会进入决策路径，但在 promoted scenarios 中没有产生行为分化：同场景 `goalToolEvents` 一致，差异主要体现在 evidence / integrity 指标。
- 因此，当前 promoted run 不能支撑 human-believability blind pilot，也不能支撑 “Full 生成更可信行为” 结论。
- `Process Fidelity` 当前可辩护贡献收缩为 explainability / 证据完整性度量 / debug guardrail。

## 2. 保留价值

- 原 `human_rating_pilot_2026-06-01_zh_v0` packet 只作为方法论记录保留，不发放 reviewer，不回收评分。
- 未来如果重新实现 behavior-divergent baseline（例如 runtime-backed Hard Delegation 或真正 memory-critical 场景），可参考旧 protocol 的盲评结构，但必须重新预注册、重新生成 packet。

## 3. 当前口径

- `C2` / `C3` / `C4` 只保留 metric / explainability level 的 `promoted with caveat`。
- `Loomstead` 作为二线 portfolio 工程项目，展示 agent orchestration / observability / eval infra，不再追 human-believability 论文化。
