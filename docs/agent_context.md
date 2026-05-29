---
status: active
owner_lane: context-governance
last_verified: 2026-05-28
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
- Phase 2（骨架建立期）rule-level scaffold 已超额完成，正在 `P2.skeleton` checkpoint，等待主人选定下一阶段方向。
- 候选方向见 `docs/phase_checkpoints.md` §P2.skeleton。浮浮酱推荐 `B 真实 LLM 证据线 → A 求职展示线`。
- 不再扩 Phase 1 旧玩法线；不在已稳定基础设施层（manifest / archive / promote / drift / strict gate）继续无 trigger 加固。

## 4. 当前边界

- 后端持有权威世界状态；Godot 只做表现 + 合法工具调用。
- LLM 输出进入可见结果前必须经过解析、规则校验、fallback 和事件记录。
- 密钥只放 `config/models.local.json`、`config/models.json` 或环境变量。
- 常规 `check` / `smoke` 不访问真实 LLM；真实 provider 证据由 `npm.cmd run llm:smoke` 单独刷新。
- Godot headless / dry-run 不等同真实窗口验收；真实窗口体验需要人工记录。
- 新增 schema、事件字段、Debug 字段、eval artifact、Godot 消费字段前先明确数据契约。
- claim level 升级只能由主人显式确认；AI 助手只能维持或降级。

## 5. 最近下一步（待主人选定方向）

按治理协议 §5 输出 checkpoint review 后停下：

- B 真实 LLM 证据线（推荐）：1 GoalSpec × 5 seed × 3 baseline 真实 provider 证据，升级 C2/C3/C4 claim level
- A 求职展示线：60 秒 demo 录屏 + 技术博客主文 + README portfolio 化
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
- 跨家里 / 公司同步时 `.run/eval-promoted/` / `.run/eval-reviewer-packets/` / `.run/process-llm-evidence/` 可随 Git 同步；`.run/eval-runs/` 滚动导出区按本地临时产物处理。
