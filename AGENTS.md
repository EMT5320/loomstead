# Loomstead 项目上下文入口

本文是 `Loomstead` 的共享上下文入口，帮助 Codex、Claude Code 和其他开发助手快速了解项目定位、事实源和渐进式阅读路线。它不定义固定回复格式或通用行为约束；具体任务仍以当前对话、代码事实和对应源文档为准。

## 1. 项目定位

- 项目名：`Loomstead`。
- 当前方向（2026-05-19 重定位后）：**可解释的多 Agent 叙事运行时**——通过 Director / Event Skill、主观记忆、关系演化、启发式学习与 Debug Trace，让少量深度 NPC（4 核心 + 2 stub）在可玩的 Godot 生活模拟切片中产生可追踪成长。差异化主轴：**少而深 + 可解释 + 可评估**。
- 技术骨架：Godot 4.x 客户端 + Python Agent Server + Web Debug / 研究控制台。
- 当前阶段：Phase 1（活着的世界）已收口，Phase 2（骨架建立期）启动中。
- 2026-05-20 研究 framing 增补：narrative-primary / task-secondary，研究主卖点为 Motivational Delegation + Process Fidelity Eval；Phase 2 骨架增加 ResearchFraming / DomainAdapter / ProcessFidelityEval 三项（详见 `docs/research_framing_motivational_delegation.md`）。

## 2. 新会话阅读路线

1. 推荐先读 `docs/agent_context.md`，快速确认当前入口、边界、命令和最近下一步。
2. 再按任务线加载对应文档，避免一次性读取全部历史资料。
3. 涉及实现或状态更新时，核对 `docs/current_status.md`，区分已验证事实、部分完成和人工未验收内容。
4. 长期方向通常参考 `docs/project_vision.md`；当前实现事实通常参考 `docs/current_status.md`。
5. 历史草案、旧 handoff 和早期观察台描述建议只作背景，当前事实以 active 文档为准。
6. 读取 `docs/*.md` 时可先看 frontmatter：`active` 表示当前参考，`snapshot` 表示阶段证据，`source_of_truth=false` 表示不作为当前事实源。

## 3. 文档分层

### 核心入口

- `docs/agent_context.md`：新对话第一入口，保持短、准、可执行。
- `docs/current_status.md`：当前代码事实、缺口、验收命令和人工验收状态。
- `docs/README.md`：文档索引和分层读取路线。

### 决策源

- `docs/project_vision.md`：产品愿景、长期方向和成功标准（2026-05-19 重定位 / 2026-05-20 研究 framing 增补）。
- `docs/research_framing_motivational_delegation.md`：研究定位与核心反论点，定义 narrative-primary / task-secondary、Motivational Delegation、Process Fidelity Eval、baseline matrix。
- `docs/agent_loop_architecture.md`：**NPC agent loop 核心圣经**——三层工具、动机系统、双轨记忆、启发式学习、仲裁、Eval。
- `docs/world_entity_model.md`：世界实体 schema + 工具空间。
- `docs/agentic_game_design.md`：多层 Agent 系统设计（Director / Skill / Memory / Model 分工）。
- `docs/gameplay_system_architecture.md`：游戏本体架构、地图主循环、Godot / 后端边界。
- `docs/production_roadmap.md`：生产化阶段路线（Phase 1 已收口 + Phase 2 详细方案）。
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
- 归档历史：`docs/archive/`（仅供溯源，通常不作为当前事实源）。

## 4. 协作注意事项

- 改动通常聚焦当前任务；跨开发线变更时，建议说明影响面。
- 状态文档倾向记录已核对事实；人工窗口、真实 API key、真实玩家体验等未验收内容建议标注 `manual unverified` 或等价说明。
- 后端、Godot、资产和愿景文档有各自上下文入口，跨线修改前可先确认对应源文档。
- 密钥、私有模型配置、本地绝对路径保留在本机配置或环境变量中。
- `.tmp`、`.run/`、本地 `.claude/settings.local.json` 等临时文件属于本地工作区内容。

## 5. 常用验证命令

Windows PowerShell 下常用命令：

```powershell
npm.cmd run context:check
npm.cmd run check
npm.cmd run context:brief
npm.cmd run smoke
npm.cmd run llm:smoke
npm.cmd run asset:check
npm.cmd run client:env
npm.cmd run client:run:check
git diff --check
```

按任务线选择最小必要命令。`npm.cmd run check` 与 `npm.cmd run smoke` 默认不访问真实 LLM；需要验收真实模型链路、刷新 token / latency / cost 证据或切换 key/profile 后，单独运行 `npm.cmd run llm:smoke`。调整上下文治理文件时，建议运行 `npm.cmd run context:check` 和 `git diff --check`。

## 6. 协作信息参考

后续协作中通常有用的信息包括：

- 触达的关键文件或开发线。
- 实际运行的验证命令和结果。
- 仍依赖人工窗口、真实 API key 或外部工具的验证点。
- 自然的后续任务。

## 7. Claude Code 适配说明

Claude Code 读取 `CLAUDE.md`。本仓库的 `CLAUDE.md` 会导入本文，避免维护两份长期上下文。Claude 路径提示放在 `.claude/rules/`，覆盖 docs、backend、Godot 和 assets 四类高频路径，并保持按路径触发。
