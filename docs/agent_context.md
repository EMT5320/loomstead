---
status: active
owner_lane: context-governance
last_verified: 2026-06-01
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

`Loomstead` 是 narrative-primary 的可解释多 Agent 叙事运行时与研究环境：Director 用 Motivational Delegation 间接驱动少量深度 NPC 朝过程约束目标演化，用 Process Fidelity Eval 验证过程可信度。差异化主轴：**少而深 + 可解释 + 可评估**。

## 3. 当前阶段

- Phase 1（活着的世界）已收口；`world_main.tscn` 是默认完成基线。
- Phase 2（骨架建立期）rule-level scaffold 已超额完成；B 真实 LLM 证据线已完成本轮 artifact 收口。
- `P2.exit` 研究向硬验收已通过 promoted-with-caveat 口径；当前进入 `P_demo.exit` 求职展示线。
- 不再扩 Phase 1 旧玩法线；不在已稳定基础设施层（manifest / archive / promote / drift / strict gate）继续无 trigger 加固。

## 4. 当前边界

- 后端持有权威世界状态；Godot 只做表现 + 合法工具调用。
- LLM 输出进入可见结果前必须经过解析、规则校验、fallback 和事件记录。
- 密钥只放 `config/models.local.json`、`config/models.json` 或环境变量。
- 常规 `check` / `smoke` 不访问真实 LLM；真实 provider 证据由 `npm.cmd run llm:smoke` 单独刷新。
- Godot headless / dry-run 不等同真实窗口验收；真实窗口体验需要人工记录。
- 新增 schema、事件字段、Debug 字段、eval artifact、Godot 消费字段前先明确数据契约。
- claim level 升级只能由主人显式确认；AI 助手只能维持或降级。

## 5. 最近下一步

- Showcase Mode v1 已进入收口批次：后端 `/api/showcase/starlight` + Godot 默认可见 `ShowcasePanel` + `F1` / `Tab` / `Deep dive` 路由已落地；离线门禁已通过，Computer Use 真实窗口 spot-check 已确认首屏摘要、`F1`、`Tab`、`Deep dive` 可用；最终 demo 视频 / GIF / 截图仍待录制。
- B 真实 LLM 证据线：4 个 Process Fidelity GoalSpec × 5 seed × 5 baseline 的 cloud provider usage 已整理并 promote 到 `.run/eval-promoted/run_2026-05-29T13-57-50Z`；C2/C3/C4 已获主人确认使用 `promoted with caveat`，promotion note 已写入，机器状态仍保留 git.dirty / drift caveat。
- A 求职展示线（进行中）：README Watch / Research 双入口、`paper/blog_main.md`、`docs/demo_capture_plan.md`、`docs/showcase_manifest.md` 与 `showcase:check` 已落地；Figure/Table 覆盖率已到 70%。当前优先级调整为先执行中文 Human Rating blind pilot v0，验证 Process Fidelity 外部效度信号，再决定最终 demo polish 包装重点。
- Human Rating Pilot Gate：`docs/human_rating_pilot_gate.md` 已作为当前 gate；`npm.cmd run eval:human-rating:packet -- --packet-id human_rating_pilot_2026-06-01_zh_v0` 生成中文盲评包，等待 3-5 名非作者 reviewer 填写评分。
- C Phase 4 玩家成为变量线：gossip 真扩散 + 1 跨日 emergence scenario
- D Phase 3 内容深度线：4 核心 NPC 完整数据 + 5 作物 / 25 物品 / 30 工具

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
npm.cmd run eval:archive:check
npm.cmd run eval:archive:drift
npm.cmd run research:evidence:check
npm.cmd run eval:human-rating:packet
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
