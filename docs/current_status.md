---
status: active
owner_lane: project-status
last_verified: 2026-05-28
startup_load: after-agent-context
source_of_truth: true
scope: current implementation facts, verification state, and work constraints
---

# 当前项目状态与开发前约束

> 状态更新时间：2026-05-28（Eval evidence robustness strict gate / 分域签名已落地；budget trace quality 已进入 process / stability eval 证据面；Godot 最新窗口复验暂停到后端/eval 主线稳定后再集中处理）
> 本文记录当前仓库中已核对、命令已检或明确标注人工未验收的事实。长期方向见 `docs/project_vision.md`，研究 framing 见 `docs/research_framing_motivational_delegation.md`，Agent loop 设计见 `docs/agent_loop_architecture.md`。

## 1. 当前阶段判断

- 项目名：`Loomstead`。
- 当前定位：narrative-primary 的可解释多 Agent 叙事运行时与研究环境。
- 技术骨架：Godot 4.x 客户端 + Python Agent Server + Web Debug / 研究控制台。
- Phase 1（活着的世界）：done；2026-05-21 主人确认可以收口，默认 `world_main.tscn` 是完成基线。
- Phase 2（骨架建立期）：首轮骨架已落地，当前进入 trace / eval 收紧期。
- 当前差异化主轴：少而深 + 可解释 + 可评估。

## 2. 当前已验证事实

| 开发线 | 当前事实 | 仍需关注 |
| --- | --- | --- |
| 后端 Runtime / Director | Python Agent Server 是权威世界状态入口；已有 `GET /api/world/state`、`POST /api/player/action`、`POST /api/world/tick`、`GET /api/debug.phase2`；规则版 Director v0 与单个 Event Skill `event.starlight_festival_shortage` 已运行；Phase 2 tick 主路径已切到 `MotivationEngine -> ToolExecutor -> ResultObserver`；`motivation.decision_made`、工具完成 / 失败 / 中断、`memory.result_observed` 均带 trace 证据；`schema_registry.v1` 已集中治理主要 schema；`ToolDefinition.served_needs` 与 CapabilityRegistry 显式需求匹配已落地，legacy prefix 仅作未标注工具 fallback；`candidateScores` 已输出 `scoreComponentSourceRefs` / `scoreExplanationRefs` 用于解释裁决分数组件来源。 | 继续扩展 schema 迁移覆盖、失败模式、真实预算策略和更完整竞争上下文裁决；旧 `LifeActionExecutor` 只做回归修复。 |
| Eval / Research | `scripts/run_agent_eval.py` 已覆盖 rule process suite、stability、stability determinism、domain adapter suite 和 evidence robustness suite；Process Fidelity Eval 包含 Hard Delegation、No Subjective Memory、No Relationship Edge、Shuffled Owner、Evidence-Link Removal、Branna Forgiveness fixture、Counterfactual Replay、budget decision trace checks 和本地 export / archive manifest；stability suite 已把 `budget_trace_links_decision` 纳入硬门禁，并输出 budget source / trace ref rate；process suite 最新 clean five-repeat rule export 为 20/20；coding domain adapter 已覆盖 8 类 repo fixture、源码派生依赖图、`dependency_evidence_chain.v2`、跨文件回归 fixture、reviewer judgment arbitration 和 `coding.domain_counterfactual_replay.v1` 证据移除 replay；narrative domain adapter 已接入 `narrative.domain_counterfactual_replay.v1`；domain suite 已支持 `--seeds`；evidence robustness 已升级为 `phase2.evidence_robustness.strict_gate.v1` 严格门禁，并输出 `phase2.evidence_robustness.domain_signature.v2` 的 coding / narrative 分域签名摘要；robustness manifest `scenarioIds` 已覆盖 process / coding / narrative 场景；`scripts/check_research_evidence.py` 可检查 latest promoted robustness strict gate 证据；`paper/research_claim_review_2026-05-28.md` 已记录 C2 / C3 / C4 / C7 / C15 / C16 claim review 和 robustness drift 说明；`scripts/build_eval_reviewer_packet.py` 可从 clean process/domain manifests 生成 manual reviewer 抽样包。 | Eval 是 Phase 2 硬验收线；domain adapter clean deterministic five-repeat export 为 55/55，process suite clean five-repeat export 为 20/20；最新 clean robustness five-seed export `.run/eval-runs/robustness_2026-05-28T03-08-43Z` 为 300/300 source perturbation checks、strict gate pass、`git.dirty=false`，并已 promote 到 `.run/eval-promoted/robustness_2026-05-28T03-08-43Z`，状态 `needs_manual_review` 已解释为 scenarioIds 索引补齐触发零容忍 drift policy，而非 strict gate / metric / baseline 回退；人工 reviewer packet 已到 `manual_review_required` gate，后续需要人工填表或继续补 provider-backed eval。 |
| Godot 客户端 | `clients/godot/` 是 Godot 4.x 项目；默认主场景为 `res://scenes/world_main.tscn`；Phase 1 玩家移动、`E` talk、tick NPC 行动、远处事件提示和三场景拼图已收口；Research Dock 三 Tab 已读取 `/api/debug.phase2` 并展示 motivation、subjective memory、relationship edges、heuristics 与 trace timeline；`memory.result_observed` 行、来源跳转按钮、Copy trace JSON、Prev/Next 循环导航、单条 trace 导航提示、Trace Copy 空态 / 成功 tooltip、Phase 2 Debug 错误提示、`[C]` / `[,]` / `[.]` / 左右方括号热键和 NPC 高亮代码已落地。 | 主人已确认 UI 重设计后的整体观感、非全屏滚动、6 NPC 密度、遮挡风险修复，以及 `memory.result_observed` 可发现性和来源跳转按钮；最新 Prev/Next、热键和 `4 中断` 布局补修仍需真实窗口复验。 |
| Web Debug / LLM | `RuleBasedProvider` 与 OpenAI-compatible `CloudApiProvider` 已接入；`config/models.example.json` 默认 rule fallback；Web Debug 已展示 provider / fallback / cost 总览、Heuristic Library、Arbitration Trace 和 Rashomon Memory。 | 最新成功真实 LLM smoke 是 2026-05-23；2026-05-24 曾触达 CloudApiProvider 但供应商返回 `HTTP 402 Insufficient Balance`，未刷新通过证据；切换 key / profile / prompt 后需单独跑 `npm.cmd run llm:smoke`。 |
| Content / NPC | 6 名首发 NPC 深度卡已入库；`voiceStyle`、`speechQuirks`、`monologueSeeds`、`giftReactions`、`gossipHooks` 已被 runtime / smoke 覆盖；4 核心 NPC（kai / mira / bram / lena）已有实际 motivation / capability / heuristic seed；tomas / orren 保持 stub。 | 谣言传播仍只记录校验结果，不写入世界状态、关系或记忆扩散；2 名 stub NPC 后续按剧情需要升级。 |
| 资产管线 | `assets/manifests/asset_manifest.json` 登记 55 条资产；3 张地点背景、星灯祭 CG、玩家 + 6 NPC 立绘、7 张地图小人和 3 类交互 marker 已进入 Godot；`AssetRegistry` 支持 happy / troubled 回退。 | 表情差分、行动反馈图标和生活行动 UI 小组件仍是 `prompt_ready` backlog；地图小人是否晋级 `source_selected` 仍需主人确认。 |
| 上下文治理 | `AGENTS.md`、`CLAUDE.md`、`docs/agent_context.md`、`docs/current_status.md`、`docs/README.md` 是基础入口；`docs/assistant_continuity.md` 和 `docs/workflows.md` 负责跨助手接续与 workflow 索引；`scripts/build_agent_context.py` 提供 `context:check` / `context:brief` / `context:resume`。 | 状态文档只记录当前事实和验证边界；长历史、过时 handoff 和旧看板留在 `docs/archive/`。 |

跨环境 artifact 策略（2026-05-28 晚间补充）：家里 / 公司交替开发时，已整理的 eval 证据子树可随 Git 同步，包括 `.run/eval-runs/`、`.run/eval-promoted/`、`.run/eval-reviewer-packets/` 和 `.run/process-llm-evidence/`；Godot 缓存、截图、Mermaid 临时配置、一次性脚本和日志继续作为本地临时产物处理。如果当前机器缺少文档记录的 promoted manifest，优先按 artifact 同步缺口处理，不默认重复运行白天已经完成的 eval。

## 3. 最近核对结果

- 2026-05-28 夜间 Eval budget trace 收口：`run_stability_scenarios` 已把 `budget.decision_consumed` / `budget.decision_fallback` 纳入 trace coverage，新增 `budget_trace_links_decision` 硬门禁和 `budget_decision_source_link_rate` / `budget_decision_trace_ref_rate` 指标；Process Fidelity per-scenario artifact 新增 `decisionBudgetTrace` 摘要与 `decision_budget_trace` / `decision_budget_source_link` checks。`docs/eval_reviewer_sampling_packet.md` 补充 Paper 使用边界，明确抽样包只证明 manual reviewer packet generated，人工填表前不能写成 human-reviewed evidence。`npm.cmd run eval:stability` 与 `npm.cmd run eval:process` 均通过。
- 2026-05-28 晚间后端 trace / budget 收口：`budget.decision_consumed` / `budget.decision_fallback` 事件已接入统一 Phase 2 trace envelope，并保留 `sourceEventIds` / `traceRefs`，可从预算事件回跳到 `motivation.decision_made` 来源；`trace_schema` 已把预算事件的版本、来源和 trace refs 纳入 debug details；`scripts/smoke_test.py` 新增预算事件 trace / source 回跳断言。Paper 侧同步收紧 C16 / reviewer-packet 口径，保持 `promoted evidence with caveat`、`needs_manual_review`、manual sampling gate pending 和 human-believability pending。`npm.cmd run smoke`、`npm.cmd run schema:check`、`npm.cmd run paper:tooling`、`npm.cmd run check`、`npm.cmd run context:check` 和 `git diff --check` 均通过。
- 2026-05-28 Research claim review / robustness drift 说明：新增 `paper/research_claim_review_2026-05-28.md`，审查 C2 / C3 / C4 / C7 / C15 / C16 的证据等级、反论点、缺口和安全措辞；`paper/claim_evidence_matrix.md` 新增 C16，将 latest promoted robustness 记录为 `promoted evidence with caveat`。`npm.cmd run research:evidence:check` 通过，命中 `.run/eval-promoted/robustness_2026-05-28T03-08-43Z/manifest.json`；`npm.cmd run eval:archive:drift` 通过且无 blocking drift。robustness promotion 的 `needs_manual_review` 当前解释为 manifest `scenarioIds` 索引修复引起的 review 级 drift，不是 metric / baseline / strict gate 回退。
- 2026-05-28 Mermaid / Figure 3 图形链路：新增 `paper/diagrams/trace_evidence_chain_figure3.mmd`，将 Branna forgiveness seed01 trace walkthrough 转成 Mermaid 图形源；新增本地 Mermaid CLI 依赖、`scripts/render_mermaid_figures.ps1`、`npm.cmd run paper:figures` / `paper:figures:check`，脚本会自动发现本机 Chrome / Edge 并把 puppeteer 临时配置写入 `.run/mermaid/`。Figure 3 已补第二条 Tomas repair trace lane 与 process-suite aggregate guardrail annotation；`npm.cmd run paper:figures` 可生成 `paper/generated/figures/*.svg`、`*.png` 与 `*.pdf`，LaTeX 当前直接 include rendered PNG。当前仍需 publication wording review。
- 2026-05-28 Eval robustness 收紧：`npm.cmd run eval:robustness` 通过，60/60 source perturbation checks，`phase2.evidence_robustness.strict_gate.v1` 的 18 项检查全部通过；domain 分域组 `loomstead.coding.v0` 为 32/32、`loomstead.town.v0` 为 12/12，均为 invariance rate `1.0`；输出 `phase2.evidence_robustness.domain_signature.v2.coding` 与 `.narrative` 签名摘要。`npm.cmd run eval:robustness:export` 生成 `.run/eval-runs/robustness_2026-05-28T02-26-00Z`，artifactCount=7，新增 `strict_gate.json`、`signature_summary.json` 与 manifest `evalGates`；`npm.cmd run eval:archive:check` 通过，`npm.cmd run eval:archive:drift` 写入 drift report 且无 blocking drift；`npm.cmd run paper:tables` 可消费 robustness metrics，但本地 paper generated 文件会随当前 `.run` 内容刷新。
- 2026-05-28 Eval robustness clean two-seed 证据：在提交 `4e0c80c` 后从 clean worktree 运行 `python scripts/run_agent_eval.py --suite robustness --seeds 2 --export-dir .run/eval-runs`，生成 `.run/eval-runs/robustness_2026-05-28T02-47-54Z`；manifest `git.dirty=false`，seedCount process/domain 均为 2，120/120 source perturbation checks 通过，strict gate 18/18 通过；coding 分域 64/64、town 分域 24/24，invariance rate 均为 `1.0`。`npm.cmd run eval:archive:check` 通过；`npm.cmd run eval:archive:drift` 无 blocking drift；`npm.cmd run eval:archive:promote -- robustness_2026-05-28T02-47-54Z --promotion-purpose regression ...` 已复制到 `.run/eval-promoted/robustness_2026-05-28T02-47-54Z`，promotionStatus 为 `needs_manual_review`，原因是 drift policy 对 seed/gate 摘要变化要求人工说明。
- 2026-05-28 Eval robustness clean five-seed 证据：在提交 `3d66186` 后从 clean worktree 运行 `python scripts/run_agent_eval.py --suite robustness --seeds 5 --export-dir .run/eval-runs`，生成 `.run/eval-runs/robustness_2026-05-28T02-55-13Z`；manifest `git.dirty=false`，seedCount process/domain 均为 5，300/300 source perturbation checks 通过，strict gate 18/18 通过；process 分组 80/80、coding 分域 160/160、town 分域 60/60，invariance rate 均为 `1.0`。`npm.cmd run eval:archive:check` 通过；`npm.cmd run eval:archive:drift` 无 blocking drift；`npm.cmd run eval:archive:promote -- robustness_2026-05-28T02-55-13Z --promotion-purpose regression ...` 已复制到 `.run/eval-promoted/robustness_2026-05-28T02-55-13Z`，promotionStatus 为 `needs_manual_review`，原因是 drift policy 对 seed/gate 摘要变化要求人工说明。
- 2026-05-28 Eval robustness manifest 索引补修：`backend/app/eval/runner.py` 的 manifest `scenarioIds` 现在会扫描 robustness 的 `process.items` / `domain.items`。提交 `c283f81` 后从 clean worktree 重跑 `python scripts/run_agent_eval.py --suite robustness --seeds 5 --export-dir .run/eval-runs`，生成 `.run/eval-runs/robustness_2026-05-28T03-08-43Z`；manifest `git.dirty=false` 且 `scenarioIds` 包含 4 个 process、8 个 coding 和 3 个 narrative 场景；300/300 source perturbation checks、strict gate 18/18、process 80/80、coding 160/160、town 60/60 均通过。`npm.cmd run eval:archive:check` / `npm.cmd run eval:archive:drift` 通过且无 blocking drift；已 promote 到 `.run/eval-promoted/robustness_2026-05-28T03-08-43Z`，promotionStatus 仍为 `needs_manual_review`，原因是 drift policy 对 scenario/gate 摘要变化要求人工说明。
- 2026-05-28 Research evidence check：新增 `scripts/check_research_evidence.py` 与 `npm.cmd run research:evidence:check`，默认读取 latest promoted robustness manifest 并检查 strict gate、minimum seeds、process / coding / narrative `scenarioIds`、domain groups、signature kinds 和关键 artifact kinds；当前命中 `.run/eval-promoted/robustness_2026-05-28T03-08-43Z/manifest.json` 且通过。

- 2026-05-27 Eval 主线推进：narrative domain 新增 `narrative.domain_counterfactual_replay.v1`，对目标关系边、目标主观记忆、目标学习启发式和完整记忆上下文做 route-level evidence removal replay；`npm.cmd run eval:domain` 为 11/11，aggregate `counterfactual_tool_selection_change_rate=0.645238`，town mean `0.333333`，coding mean `0.762203`；`npm.cmd run eval:domain:export` 生成 `.run/eval-runs/domain_2026-05-27T07-20-04Z`，artifactCount=76，并含 3 个 narrative replay artifact 与既有 coding replay artifact；`npm.cmd run eval:archive:check` 通过；`context:resume` / `context:handoff` 已验证 manual gates 不再截断当前 7 条。
- 2026-05-27 Eval / Research 接续推进：domain suite 的 `--seeds` 已从 process 线扩展到 cross-domain adapter，`npm.cmd run eval:domain -- --seeds 2` 为 22/22；`npm.cmd run eval:domain:export -- --seeds 2` 生成 `.run/eval-runs/domain_2026-05-27T08-21-49Z`，artifactCount=144，per-scenario / domain evidence 导出按 `_seedXX` 避免覆盖；`npm.cmd run paper:tables` 已刷新 Table 5，显示 coding 16/16、town 6/6、deterministic repeats=2 与 CF route 指标。
- 2026-05-27 晚间 Eval / Paper 证据刷新：从干净 tracked diff 状态重跑 `npm.cmd run eval:domain:export -- --seeds 5`，生成 `.run/eval-runs/domain_2026-05-27T13-29-21Z`，manifest `git.dirty=false`，artifactCount=351；`npm.cmd run paper:tables` 已刷新 Table 5，显示 cross-domain 55/55、coding 40/40、town 15/15、deterministic repeats=5 与 CF route 指标；`npm.cmd run eval:archive:check` 通过，当前 archive index 统计 33 个有效 run、1189 个 artifact。
- 2026-05-27 晚间 Process / Paper 证据刷新：在提交 `71e9f07` 后从干净 tracked diff 状态重跑 `npm.cmd run eval:process:export -- --seeds 5`，生成 `.run/eval-runs/run_2026-05-27T13-37-33Z`，manifest `git.dirty=false`，20/20 通过，artifactCount=127；`npm.cmd run paper:tables` 已刷新 Table 2，显示 process suite seeds=5、passed=20/20。该 rule-mode export 的 `llmEvidence.source=latest_cache`，不刷新真实 provider 通过证据。
- 2026-05-27 夜间并行推进：后端 `ToolDefinition.served_needs` + CapabilityRegistry 语义过滤已落地，`python scripts/check_capability_served_needs.py` 通过并已加入 `npm.cmd run check`；Eval 新增 `scripts/build_eval_reviewer_packet.py` 与 `docs/eval_reviewer_sampling_packet.md`，示例命令生成 `.run/eval-reviewer-packets/packet_2026-05-27_manual_reviewer_main_review2`，sampleCount=4，manual gate 为 `manual_review_required`；Paper 新增 Figure 3 walkthrough 草稿 `paper/trace_walkthroughs/figure3_trace_walkthrough_pf_branna_seed01.md`，仍需人工图形化与措辞审阅。
- 2026-05-27 深夜三路非阻塞推进：后端 `candidateScores` 新增 `scoreComponentSourceRefs` / `scoreExplanationRefs` 并由 `python scripts/smoke_test.py` 覆盖；Eval 新增 `npm.cmd run eval:robustness`，示例导出 `.run/eval-runs/robustness_2026-05-27T15-31-47Z` 为 48/48 source perturbation checks；`npm.cmd run eval:archive:check` 当前通过，统计 38 个有效 run、1332 个 artifact；Godot Research Dock Trace Copy 空态 / tooltip / 错误提示已落地，`client:env`、`client:run:check` 和 `check_godot_project.py` 已由子线验证。
- 2026-05-26 三线并行推进：coding domain 新增 `coding.domain_counterfactual_replay.v1`，逐项移除 post-patch tests、review source links、derived dependency graph、single-file replay、dependency chain、reviewer arbitration sources 等证据后复算 review route；`npm.cmd run eval:domain` 为 11/11，aggregate `counterfactual_tool_selection_change_rate=0.554329`，coding mean `0.762203`；`npm.cmd run eval:domain:export` 生成 `.run/eval-runs/domain_2026-05-26T14-14-58Z`，artifactCount=73，并含 8 个 `domain_evidence_counterfactual_replay_json` artifact。
- 2026-05-26 真实 Godot 窗口复验发现 Trace Tab `Prev` / `Next` 按钮和热键在单条结果下无可见反馈，且 `4 中断` filter、Copy 按钮和来源按钮有横向溢出；已改为过滤按钮网格、Copy 独立行、Prev/Next 循环导航、单条结果提示、物理键兜底和来源按钮单列截断；`client:run:check`、`client:env`、`check_godot_project.py`、Godot headless import、`check`、`context:check` 和 `git diff --check` 通过。
- 2026-05-26 真实 Godot 窗口复验发现 `memory.result_observed` 行和 source chip 可发现性不足：`memory.result_observed` 只藏在 detail `type` 字段里，source chip 外观像标签；已补显式行名、观察记忆提示、来源跳转按钮文案和聚焦状态提示，主人随后确认通过，可转入 Eval 证据链收紧阶段。
- 2026-05-26 上下文治理收缩：`docs/agent_context.md` 从长事实堆叠改为短入口；`docs/current_status.md` 聚焦当前事实、manual gate 和下一步；接续流程开始收敛到 `context:resume`。
- 2026-05-25 Trace 体验闭环代码已落地：`GET /api/debug.phase2` 支持 `focusEventId` / `focusTraceId`，`recentTraceEvents[]` 支持 `sourceLinks[]`，响应可返回 `traceFocus`；Godot Research Dock Trace detail 新增“证据链”chip，点击 source chip 会重拉 focus 并选中源事件；Copy trace 会复制当前 trace JSON。
- 2026-05-25 晚间 Godot 可读性补修已落地：NPC 一览双层行、集中字号 / 布局缩放和 Tab 底部滚动留白；主人随后确认非全屏滚动到底、6 NPC 密度和 HUD / TopBanner 遮挡风险修复。
- 2026-05-24 Round 2 已落地：Process Eval cloud / mixed provider 接入、Web Debug Phase 2 三卡片、跨域测试框架矩阵和 JavaScript smoke dry-run。
- 2026-05-24 stability 证据口径已收紧：24h / 72h stability 和 72h determinism 以硬门禁不变量为准，run-specific exact count 只记录在 artifact 中。

## 4. 开发前硬约束

- 后端 Runtime 是权威世界状态修改点；Godot 本地坐标只做表现，不写回权威世界。
- LLM 输出只生成文本、结构化建议或工具意图；世界状态变更必须经过 Runtime 规则、schema 校验和 fallback。
- 密钥、私有模型配置、本机绝对路径和临时 overlay 不写入仓库。
- 已整理的 eval 证据 artifact 可进入提交态以支持家里 / 公司交替开发；未整理 `.run/` 临时产物继续排除。
- 新增 API、事件类型、schema、eval artifact、Debug 字段或 Godot 消费字段前，先写清数据契约。
- 未由代码、命令或人工窗口验证的能力必须标注 `manual unverified` 或同等说明。
- Phase 2 直接使用 MotivationEngine；不并行扩写旧 `LifeActionExecutor`。

## 5. 人工验收与本机门禁

- `manual verified`：2026-05-21 主人确认 Phase 1 可以收口，默认 `world_main.tscn` 进入完成基线。
- `manual verified`：2026-05-25 主人确认 UI 重设计后整体观感与主路径无大问题。
- `manual verified`：2026-05-25 晚间主人确认 Research Dock 可读性补修，包括非全屏滚动到底、NPC 密度和遮挡风险。
- `manual verified`：2026-05-26 主人确认 Trace 时间线中 `memory.result_observed` 行可发现，来源跳转按钮可点击并可进入下一阶段。
- `manual unverified`：最新 Godot Trace 补修代码已落地；真实窗口仍需复验 `Prev` / `Next` 循环、逗号/句号/左右方括号热键、Copy 短反馈、`4 中断` filter 不溢出和 source link 按钮不越界。
- `manual unverified`：真实 LLM 最新成功证据仍沿用 2026-05-23；2026-05-24 的真实 provider 尝试因 `HTTP 402 Insufficient Balance` 未形成通过证据。
- `manual unverified`：`prompt_ready` 资产尚未生成、筛选、登记源图或接入 Godot registry。

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

按任务线选择最小必要命令。真实 LLM、真实 Godot 窗口和玩家手感验收不属于默认离线门禁。

## 7. 下一轮建议

- Eval 线已新增 strict gate、scenarioIds 索引、coding / narrative 分域签名与 latest promoted robustness evidence 自动检查；promotion drift 说明、research claim review 和 Mermaid figure 渲染链路已补，下一步可生成 / 复核人工 reviewer 抽样包，或继续 polish Figure 3 的第二条 trace / aggregate annotation。
- Godot trace 最新窗口复验暂缓；后续等后端 Agent / Eval 主线稳定后再集中做展示层复验和 polish，避免每次新增 trace / 内容 / 字段后反复进入中间态窗口验收和小修循环，不重开 Phase 1 旧玩法扩写。
- Research 线下一步围绕 `.run/eval-runs/domain_2026-05-27T13-29-21Z` 和 `paper/research_claim_review_2026-05-28.md` 写 claim prose / Table 5 说明，措辞保持 research-preview。
- Paper 线已把 `paper/trace_walkthroughs/figure3_trace_walkthrough_pf_branna_seed01.md` 转成 `paper/diagrams/trace_evidence_chain_figure3.mmd` 图形草案，并通过 `npm.cmd run paper:figures` 渲染到 `paper/generated/figures/`；第二条 trace 与 aggregate annotation 已补，下一步是继续人工修正 artifact 中的 mojibake 标签和图形措辞。
- LLM / Debug 线只在切换模型、key、profile、prompt 或需要刷新真实成本证据时运行 `npm.cmd run llm:smoke`。
- 资产线按 `docs/asset_batches/prompt_ready_export.md` 推进前，先结合 `docs/open_questions.md` 的资产范围调整重新排序。
