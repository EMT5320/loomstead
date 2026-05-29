---
status: active
owner_lane: project-status
last_verified: 2026-05-29
startup_load: after-agent-context
source_of_truth: true
scope: 当前实现事实、验证状态、人工验收边界
---

# Loomstead 当前项目状态

> 自管理层文档，软上限 250 行。只记当前事实、当前命令、当前缺口；历史变化由 git history 承载。

## 1. 当前阶段

- 项目名：`Loomstead`，narrative-primary 的可解释多 Agent 叙事运行时与研究环境。
- 技术骨架：Godot 4.x 客户端 + Python Agent Server + Web Debug / 研究控制台。
- Phase 1（活着的世界）已收口（2026-05-21 主人确认），`world_main.tscn` 为默认完成基线。
- Phase 2（骨架建立期）rule-level scaffold 已超额完成，正在 `P2.skeleton` checkpoint，等待主人选定下一阶段方向（候选见 `docs/phase_checkpoints.md`）。

## 2. 当前已验证事实

| 开发线 | 当前事实 |
|---|---|
| 后端 Runtime | Python Agent Server 是权威世界状态入口；`/api/world/state`、`/api/player/action`、`/api/world/tick`、`/api/debug.phase2` 已开放；规则版 Director v0 与 `event.starlight_festival_shortage` 已运行；tick 主路径走 `MotivationEngine -> ToolExecutor -> ResultObserver`；`schema_registry.v1` 已集中治理主要 schema。`ToolDefinition.served_needs` 与 CapabilityRegistry 显式需求匹配已落地，legacy prefix 仅作未标注 fallback。Arbitration `candidateScores` 输出 `scoreComponentSourceRefs` / `scoreExplanationRefs`。 |
| Phase 2 trace | `motivation.decision_made`、工具完成 / 失败 / 中断、`memory.result_observed`、`budget.decision_consumed` / `budget.decision_fallback` 全部带 `phase2.trace.v1`，含 `sourceEventIds` 与 `traceRefs`。 |
| Eval / Research | `scripts/run_agent_eval.py` 覆盖 rule process suite、stability、stability determinism、domain adapter suite、evidence robustness suite。Process Fidelity Eval 已含 Hard Delegation、No Subjective Memory、No Relationship Edge、Shuffled Owner、Evidence-Link Removal、Branna Forgiveness fixture、Counterfactual Replay、budget decision trace checks。Stability suite 把 `budget_trace_links_decision` 纳入硬门禁。Coding domain 含 8 fixture + derived dependency graph + `dependency_evidence_chain.v2` + reviewer arbitration + `coding.domain_counterfactual_replay.v1`；narrative domain 已接入 `narrative.domain_counterfactual_replay.v1`；domain suite 支持 `--seeds`。Evidence robustness 升级为 `phase2.evidence_robustness.strict_gate.v1`，输出 `phase2.evidence_robustness.domain_signature.v2` 的 coding / narrative 分域签名。`scripts/check_research_evidence.py` 校验 latest promoted robustness。 |
| 最新 clean evidence | Process suite five-repeat 20/20（`run_2026-05-27T13-37-33Z`）；domain suite five-repeat 55/55（`domain_2026-05-27T13-29-21Z`），aggregate counterfactual mean `0.645238`、town mean `0.333333`、coding mean `0.762203`；robustness five-seed 300/300（`robustness_2026-05-28T03-08-43Z`，已 promote），promotion 为 `needs_manual_review`（drift policy 对 scenarioIds 索引补齐要求人工说明）。 |
| Godot 客户端 | `clients/godot/` 是 Godot 4.x 项目，默认主场景 `res://scenes/world_main.tscn`；Phase 1 玩家移动、`E` talk、tick NPC 行动、远处事件提示和三场景拼图收口；Research Dock 三 Tab 读取 `/api/debug.phase2` 展示 motivation / 主观记忆 / 关系边 / heuristics / trace timeline；`memory.result_observed` 行、来源跳转按钮、Copy trace JSON、Prev/Next 循环导航、单条 trace 提示、Trace Copy 空态 / 成功 tooltip、Phase 2 Debug 错误提示、`[C]` / `[,]` / `[.]` / 左右方括号热键、NPC 高亮代码已落地。 |
| Web Debug / LLM | `RuleBasedProvider` 与 OpenAI-compatible `CloudApiProvider` 已接入；`config/models.example.json` 默认 rule fallback；Web Debug 已展示 provider / fallback / cost 总览、Heuristic Library、Arbitration Trace、Rashomon Memory。 |
| Content / NPC | 6 名首发 NPC 深度卡入库；`voiceStyle`、`speechQuirks`、`monologueSeeds`、`giftReactions`、`gossipHooks` 已被 runtime / smoke 覆盖；4 核心（kai / mira / bram / lena）已有 motivation profile / capability preferences / heuristic seed；tomas / orren 仍是 stub。Gossip 仍只记录 `gossip.propagation_validated`，未真正写入记忆 / 关系扩散。 |
| 资产 | `assets/manifests/asset_manifest.json` 登记 55 条资产；3 张地点背景、星灯祭 CG、玩家 + 6 NPC 立绘、7 张地图小人、3 类交互 marker 已进入 Godot；`AssetRegistry` 支持 happy / troubled fallback；表情差分、行动反馈图标和生活行动 UI 小组件仍是 `prompt_ready` backlog。 |
| 上下文治理 | `docs/context_governance.md` 是治理协议；`AGENTS.md` / `CLAUDE.md` / `docs/agent_context.md` / 本文 / `docs/phase_checkpoints.md` 是当前事实入口；`scripts/build_agent_context.py` 提供 `context:check` / `context:brief` / `context:resume`；旧设计文档（agentic_game_design / gameplay_system_architecture / game_content_storyline / npc_deep_card_spec）已归档至 `docs/archive/`。 |
| 跨环境 artifact | 双环境只同步已整理证据子树：`.run/eval-promoted/`、`.run/eval-reviewer-packets/`、`.run/process-llm-evidence/`。`.run/eval-runs/` 已回归本地滚动区（`.gitignore` 忽略），跨机复盘靠 `eval:archive:promote` 把被 claim 引用的 run 复制到 `eval-promoted`。`git rm --cached` 不删本机工作区文件，产出机器的 archive / drift / promote 命令照常；另一台机器只消费 promoted 子树。Godot 缓存、截图、Mermaid 临时配置、一次性脚本和日志继续按本地临时产物处理。 |

## 3. 当前缺口

- **真实 LLM evidence**：cloud provider 已跑通 Branna Forgiveness（`pf.branna_forgiveness_requires_memory`）1 GoalSpec × 5 seed × 5 baseline，0 fallback，token / cost / latency 记录在 `.run/process-llm-evidence/latest.json`（另有 `latest.local-office-2026-05-29.json` 单 seed 跨机记录）。仍缺：cloud run 的 process fidelity / ablation 结论尚未 promote 进 claim matrix；3 process-constrained GoalSpec 仅覆盖 1 个（Close Friend / Festival 未跑 cloud）；C2/C3/C4 claim level 升级待主人显式确认。
- **证据指针**：`paper/claim_evidence_matrix.md` 引用的 4 个 run（`run_2026-05-28T07-43-32Z`、`stability_2026-05-25T07-34-55Z`、`domain_2026-05-28T07-49-46Z`、`domain_2026-05-27T13-29-21Z`）已 promote 到 `.run/eval-promoted/` 并完成 matrix 路径迁移，跨机证据链固定。§2 “最新 clean evidence” 的 05-27 组是 rule suite five-repeat 快照，与 matrix 引用的 export run 属不同口径，保留并存。
- **人工 reviewer 抽样**：packet 已生成，停在 `manual_review_required` gate，等待人工填表。
- **真实 Godot 窗口复验**：最新 Trace 导航 / 中断布局补修代码已落地，真实窗口复验**暂缓**到后端 / Eval 主线稳定后集中处理（治理协议 §3.1：避免每次新增字段后反复进入中间态窗口验收和小修循环）。
- **Phase 4 候选**：gossip 真扩散、玩家行为传播、emergence scenario 仍未启动。
- **30 秒可分享 demo 物料**：愿景 §"作品集传播优先"原则要求每条核心能力都有可分享 demo，当前为零。

## 4. 开发前硬约束

- 后端 Runtime 是权威世界状态修改点；Godot 本地坐标只做表现，不写回权威世界。
- LLM 输出只生成文本、结构化建议或工具意图；世界状态变更必须经过 Runtime 规则、schema 校验和 fallback。
- 密钥、私有模型配置、本机绝对路径和临时 overlay 不写入仓库。
- 已整理的 eval 证据 artifact 可进入提交态；未整理 `.run/` 临时产物按本地处理（除 2026-05-28 一次性 .run 全量入库的临时操作）。
- 新增 API、事件类型、schema、eval artifact、Debug 字段或 Godot 消费字段前，先写清数据契约。
- 未由代码、命令或人工窗口验证的能力必须标注 `manual unverified` 或同等说明。
- Phase 2 直接使用 MotivationEngine；不并行扩写旧 `LifeActionExecutor`。
- 治理协议 §3 风格条款优先级高于"最小修改"等保守倾向。

## 5. 人工验收

- `manual verified`：2026-05-21 Phase 1 收口；2026-05-25 UI 重设计观感与可读性；2026-05-26 Trace `memory.result_observed` 可发现性 + 来源跳转。
- `manual unverified`：最新 Trace 导航 / 中断布局补修真实窗口复验；真实 LLM cloud 证据的 process fidelity / ablation 指标结论人工未核对（provider usage artifact 已落地，见 §3）；`.run/eval-promoted/stability_2026-05-25T07-34-55Z` promotion 的 drift 人工说明（`needs_manual_review`）；`prompt_ready` 资产生成与登记。

## 6. 当前可运行命令

```powershell
npm.cmd run context:resume
npm.cmd run context:check
npm.cmd run context:brief
npm.cmd run check
npm.cmd run smoke
npm.cmd run schema:check
npm.cmd run eval:process
npm.cmd run eval:stability
npm.cmd run eval:stability:long
npm.cmd run eval:stability:determinism
npm.cmd run eval:domain
npm.cmd run eval:robustness
npm.cmd run eval:archive:check
npm.cmd run eval:archive:drift
npm.cmd run eval:reviewer:packet
npm.cmd run research:evidence:check
npm.cmd run content:check
npm.cmd run asset:check
npm.cmd run model:check
npm.cmd run client:env
npm.cmd run client:run:check
npm.cmd run llm:smoke
git diff --check
```

按任务线选最小必要命令。真实 LLM、真实 Godot 窗口和玩家手感不属于默认离线门禁。

## 7. 下一步

`P2.skeleton` checkpoint 待主人选定方向。详见 `docs/phase_checkpoints.md` 候选 A/B/C/D。浮浮酱推荐 `B → A`。
