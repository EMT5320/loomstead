---
status: active
owner_lane: context-governance
last_verified: 2026-06-03
startup_load: first-read
source_of_truth: true
scope: 新对话入口、当前边界、最近下一步
---

# Loomstead 新对话入口

> 自管理层文档，软上限 250 行，只记当前事实，不写历史流水。

## 1. 启动顺序

1. `npm.cmd run context:resume`：分支、脏区、manual gate、最近下一步。
2. 读 `docs/context_governance.md`：三层文档边界、改动权限、推进感约束。
3. 读 `AGENTS.md`：跨助手指令与开发风格硬约束。
4. 读本入口（你正在读）。
5. 读 `docs/phase_checkpoints.md`：当前阶段位置与下一阶段候选。
6. 涉及实现 / 状态时核对 `docs/current_status.md`。
7. 跨环境 / 多助手 / 子代理接续时参考 `docs/assistant_continuity.md`。

## 2. 一句话定位

`Loomstead` 是 narrative-primary 的可解释多 Agent 叙事运行时与二线工程展示项目：Director / Event Skill / NPC runtime / trace / eval 共同展示 **agent orchestration + observability + eval infra** 能力。2026-06-02 后，Process Fidelity 只作为证据完整性 / debug guardrail，不再主张 human-validated believability。

## 3. 当前阶段

- **2026-06-02 战略收缩**：经两项目对比，主人确认 `AlgoCoach-Flywheel`（另一仓库）为求职 + 论文主力；`Loomstead` 收缩为**可解释多 agent 系统工程展示项目**，停止追 human believability / 论文化 / cloud 重跑。可辩护贡献定位为 agent orchestration / observability / eval infra。
- **Auditable Agents spike 当前状态**：求职展示录屏 / GIF manual gate 已由主人暂缓；最小 deterministic audit suite 与 reviewer-readable packet 生成器已落地，先验证 trace-grounded action provenance / policy bypass / counterfactual audit report 是否有清晰证据分化。若报告价值不足，则彻底停止研究投入。
- Phase 1（活着的世界）已收口；`world_main.tscn` 是默认完成基线。
- Phase 2（骨架建立期）rule-level scaffold 已超额完成；B 真实 LLM 证据线已完成本轮 artifact 收口。
- `P2.exit` 已通过 promoted-with-caveat 口径；`P_demo.exit` 求职展示线降为可选低优先（仅录制 explainability demo 素材）。
- 不再扩 Phase 1 旧玩法线；不在已稳定基础设施层（manifest / archive / promote / drift / strict gate）继续无 trigger 加固。

## 4. 当前边界

- 后端持有权威世界状态；Godot 只做表现 + 合法工具调用。
- LLM 输出进入可见结果前必须经过解析、规则校验、fallback 和事件记录。
- 密钥只放 `config/models.local.json`、`config/models.json` 或环境变量。
- 常规 `check` / `smoke` 不访问真实 LLM；真实 provider 证据由 `npm.cmd run llm:smoke` 单独刷新。
- Godot headless / dry-run 不等同真实窗口验收；真实窗口体验需要人工记录。
- 新增 schema、事件字段、Debug 字段、eval artifact、Godot 消费字段前先明确数据契约。
- claim level 升级只能由主人显式确认；AI 助手只能维持或降级。

## 5. 最近下一步（2026-06-02 战略收缩后）

- **Human Rating pilot 已评估为前提不成立、不执行**：`hard_delegation` 是 metric stub 不跑 runtime；memory / relationship ablation 输入虽进入决策路径，但 promoted scenarios 中未改变 `goalToolEvents`，因此现有 believability 梯度只支持 evidence/integrity 层，不支持人类盲评系统能力结论。详见 `docs/human_rating_pilot_gate.md`。
- **可辩护贡献收缩为工程展示**：Process Fidelity 定位为证据完整性度量 / debug guardrail（指标对证据缺失 / 归属错乱 / 链接剥离敏感，promoted run 已支持），不再主张 "Full 生成更可信行为"。`paper/claim_evidence_matrix.md` 的 C2/C3/C4 已降级为 metric / explainability 级。
- **求职展示入口**：`docs/portfolio_capability_map.md` 已把现有资产串联为 capability map（工程能力栈 / 对应岗位 / 面试讲法 / 诚实边界 / 与 AlgoCoach 分工）。
- **兜底工程项目收尾优先**：README / blog / capability map / ShowcasePanel 继续作为 portfolio 入口；只在现有 Godot / Observer 资源足够清楚时录低成本素材，不追加展示层大改。
- **短挽救实验已最小实现**：`backend/app/eval/audit.py` + `eval:audit` / `eval:audit:export` 覆盖 3 个高风险非叙事场景、5 个 baseline、`audit.report.v1`、`audit.counterfactual_replay.v1` 与 `audit.go_no_go.v1`；`scripts/build_audit_reviewer_packet.py` + `eval:audit:packet` 生成 README / summary / case studies / raw 附录。当前只支持 toy deterministic 审计 harness claim，避免升级 believability 或 AI Safety 强 claim。
- **Go / No-Go 当前机器结果**：`npm.cmd run eval:audit` 通过；Full provenance=1.0、Shortcut/Direct bypass=1.0、3 个场景 counterfactual sensitive、15 份 audit report 字段完整。`manual_reviewer_readability` 是人工 gate，最新 packet：`.run/eval-reviewer-packets/audit_reviewer_packet_2026-06-05T08-28-28Z`。
- **主力已转移**：求职 + 论文主力为 `AlgoCoach-Flywheel`（另一仓库）；Loomstead 不再启动 Phase 3 内容深度线、Phase 4 玩家变量线等新开发线。

## 6. 按开发线读取

- 后端 / Agent Loop：`docs/agent_loop_architecture.md`、`docs/world_entity_model.md`、`backend/app/runtime/`、`backend/app/tools/`、`backend/app/memory/`
- Eval / Research：`docs/process_fidelity_eval_spec.md`、`docs/cross_domain_adapter.md`、`docs/eval_dataset_archive.md`、`backend/app/eval/`、`backend/app/domain/`、`scripts/run_agent_eval.py`
- Godot 客户端：`docs/game_client_environment.md`、`docs/production_roadmap.md`、`clients/godot/`
- LLM / Debug：`docs/model_profile_template_guide.md`、`config/`、`backend/app/providers/`、`frontend/`、`GET /api/debug.phase2`
- Content / NPC：`backend/app/content/`（旧设计文档已归档至 `docs/archive/`）
- 资产：`docs/art_direction.md`、`docs/asset_generation_prompts.md`、`docs/map_sprite_style_guide.md`、`assets/manifests/asset_manifest.json`
- 上下文治理：`docs/context_governance.md`、`AGENTS.md`、`CLAUDE.md`、`docs/assistant_continuity.md`、`docs/workflows.md`、`scripts/build_agent_context.py`

## 7. 验证命令

```powershell
npm.cmd run context:resume
npm.cmd run context:check
npm.cmd run context:handoff
npm.cmd run check
npm.cmd run smoke
npm.cmd run schema:check
npm.cmd run eval:process
npm.cmd run eval:stability
npm.cmd run eval:domain
npm.cmd run eval:robustness
npm.cmd run eval:audit
npm.cmd run eval:audit:export
npm.cmd run eval:audit:packet
npm.cmd run eval:archive:check
npm.cmd run eval:archive:drift
npm.cmd run research:evidence:check
npm.cmd run client:env
npm.cmd run client:run:check
npm.cmd run llm:smoke
git diff --check
```

按任务线选最小必要命令。`llm:smoke` 只在切换 model / key / profile / prompt 或刷新真实证据时运行。

## 8. 协作约束

- 状态文档区分 `code integrated` / `command checked` / `artifact backed` / `manual verified` / `manual unverified`。
- 自管理层文档不复制源设计长文，不堆历史流水；超过软上限触发"是否拆分"检讨。
- 多子代理并行时治理入口（本文、`current_status.md`、`AGENTS.md`、`context_governance.md`）由主会话串行修改。
- 跨家里 / 公司同步时 `.run/eval-promoted/` / `.run/eval-reviewer-packets/` / `.run/process-llm-evidence/` 的命名证据文件可随 Git 同步；`.run/eval-runs/` 与 `.run/process-llm-evidence/latest*.json` 是本地滚动/缓存区，只在产出机器本地保留，跨机复盘靠 `eval:archive:promote` 与命名 cloud artifact。
