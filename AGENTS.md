# Loomstead 项目代理入口

本文是 `loomstead` 的共享代理入口，供 Codex、Claude Code 和其他开发助手在新会话启动时读取。它只放长期有效的工作规则和渐进式加载路线，具体事实以 `docs/` 中对应源文档为准。

## 1. 项目定位

- 项目名：`Loomstead`。
- 当前方向（2026-05-19 重定位后）：**可解释的多 Agent 叙事运行时**——通过 Director / Event Skill、主观记忆、关系演化、启发式学习与 Debug Trace，让少量深度 NPC（4 核心 + 2 stub）在可玩的 Godot 生活模拟切片中产生可追踪成长。差异化主轴：**少而深 + 可解释 + 可评估**。
- 技术骨架：Godot 4.x 客户端 + Python Agent Server + Web Debug / 研究控制台。
- 当前阶段：Phase 1（活着的世界）收口中，Phase 2（骨架建立期）待启动。
- 2026-05-20 研究 framing 增补：narrative-primary / task-secondary，研究主卖点为 Motivational Delegation + Process Fidelity Eval；Phase 2 骨架增加 ResearchFraming / DomainAdapter / ProcessFidelityEval 三项（详见 `docs/research_framing_motivational_delegation.md`）。

## 2. 新会话启动协议

1. 先读 `docs/agent_context.md`，确认当前入口、边界、命令和最近下一步。
2. 再按任务线加载对应文档，避免一次性读取全部历史资料。
3. 修改前核对 `docs/current_status.md` 与 `docs/goal_board.md`，区分已验证事实、部分完成和人工未验收内容。
4. 长期方向冲突时，以 `docs/project_vision.md` 为准；当前事实冲突时，以 `docs/current_status.md` 为准。
5. 历史草案、旧 handoff 和早期观察台描述只能作背景，不得直接当作当前实现事实。
6. 读取任一 `docs/*.md` 时先看 frontmatter：`active` 可作为当前参考，`snapshot` 只代表阶段证据，`source_of_truth=false` 不得覆盖当前事实源。

## 3. 文档分层

### 必读入口

- `docs/agent_context.md`：新对话第一入口，保持短、准、可执行。
- `docs/current_status.md`：当前代码事实、缺口、验收命令和人工验收状态。
- `docs/goal_board.md`：开发线看板、并行写入边界和收口格式。
- `docs/README.md`：文档索引和分层读取路线。

### 决策源

- `docs/project_vision.md`：产品愿景、长期方向和成功标准（2026-05-19 重定位 / 2026-05-20 研究 framing 增补）。
- `docs/research_framing_motivational_delegation.md`：研究定位与核心反论点，定义 narrative-primary / task-secondary、Motivational Delegation、Process Fidelity Eval、baseline matrix。
- `docs/agent_loop_architecture.md`：**NPC agent loop 核心圣经**——三层工具、动机系统、双轨记忆、启发式学习、仲裁、Eval。
- `docs/world_entity_model.md`：世界实体 schema + 工具空间。
- `docs/agentic_game_design.md`：多层 Agent 系统设计（Director / Skill / Memory / Model 分工）。
- `docs/gameplay_system_architecture.md`：游戏本体架构、地图主循环、Godot / 后端边界。
- `docs/production_roadmap.md`：生产化阶段路线（Phase 1 收口 + Phase 2 详细方案）。
- `docs/process_fidelity_eval_spec.md`：研究向 Eval 指标、hard delegation baseline、ablation protocol、dataset 输出规格。
- `docs/cross_domain_adapter.md`：跨域 adapter 接口，保证小镇 primary、为 task-secondary 验证保留路径。
- `docs/open_questions.md`：已确认决策、剩余问题和实现中验证点。

### 按任务线读取

- 后端 / Director / Event Skill / Agent Loop：`docs/agent_loop_architecture.md`、`docs/world_entity_model.md`、`docs/agentic_game_design.md`、`backend/`、`scripts/check.py`。
- Godot 客户端：`docs/production_roadmap.md`、`docs/gameplay_system_architecture.md`、`docs/game_client_environment.md`、`clients/godot/README.md`、`clients/godot/`。
- 内容 / NPC 深度卡：`docs/game_content_storyline.md`、`docs/npc_deep_card_spec.md`、`backend/app/content/`。
- LLM / Debug / Eval：`docs/model_profile_template_guide.md`、`config/`、`backend/app/providers/`、`docs/agent_loop_architecture.md` §10、`docs/process_fidelity_eval_spec.md`、Debug API 相关代码。
- 研究 framing / 跨域 adapter：`docs/research_framing_motivational_delegation.md`、`docs/process_fidelity_eval_spec.md`、`docs/cross_domain_adapter.md`；实现阶段转为代码后进入 `backend/app/domain/`、`backend/app/eval/`。
- 资产管线：`docs/art_direction.md`、`docs/asset_generation_prompts.md`、`docs/map_sprite_style_guide.md`、`assets/manifests/asset_manifest.json`。
- 上下文治理：`AGENTS.md`、`CLAUDE.md`、`docs/agent_context.md`、`scripts/build_agent_context.py`。
- 归档历史：`docs/archive/`（仅供溯源，不得作为当前事实源）。

## 4. 写入边界

- 只修改当前任务需要的文件，跨开发线变更必须在回复中说明原因。
- 状态文档只能写已核对事实；人工窗口、真实 API key、真实玩家体验等未验收内容必须标注 `manual unverified` 或等价说明。
- 后端任务默认不改 Godot、资产和大段愿景文档；资产任务默认不改运行逻辑。
- 不把密钥、私有模型配置、本地绝对路径写入可提交文件。
- `.tmp`、`.run/`、本地 `.claude/settings.local.json` 等临时文件不得提交。

## 5. 常用验收命令

优先使用 Windows PowerShell 命令：

```powershell
npm.cmd run context:check
npm.cmd run check
npm.cmd run context:brief
npm.cmd run smoke
npm.cmd run asset:check
npm.cmd run client:env
npm.cmd run client:run:check
git diff --check
```

按任务线选择最小必要命令。改动上下文治理文件时，至少运行 `npm.cmd run context:check` 和 `git diff --check`。

## 6. 交接格式

每轮结束时按以下格式汇报：

- 改了什么：列出关键文件。
- 如何验证：列出实际运行命令和结果。
- 仍未验证：明确人工验收、真实 API key 或外部工具依赖。
- 下一步：给出 1～3 个可直接开工的任务。

## 7. Claude Code 兼容说明

Claude Code 读取 `CLAUDE.md`。本仓库的 `CLAUDE.md` 会导入本文，避免维护两份长期规则。Claude 专用路径规则已放入 `.claude/rules/`，覆盖 docs、backend、Godot 和 assets 四类高频路径，并保持按路径触发。
