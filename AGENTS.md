# Loomstead 跨助手协作入口

本文是 `Loomstead` 所有 AI 助手（Codex / Claude Code / Kiro / 浮浮酱等）的唯一指令入口。其他指令文档（`CLAUDE.md`、`.claude/rules/*.md`）均为薄适配层，规则冲突时以本文与 `docs/context_governance.md` 为准。

## 1. 项目一句话定位

`Loomstead` 是一个 **narrative-primary 的可解释多 Agent 叙事运行时**。2026-06-02 战略收缩后，它不再作为求职 / 论文主力研究线，而是二线 **portfolio 工程展示项目**：通过 Director / Event Skill、NPC runtime、主观记忆、关系演化、Debug Trace 与 Process Fidelity harness 展示 **agent orchestration + observability + eval infra** 能力。C2/C3/C4 仅保留 metric / explainability 级 `promoted with caveat`，不再主张 human-validated believability。

技术骨架：Godot 4.x 客户端 + Python Agent Server + Web Debug / 研究控制台。
长期源文档：`docs/project_vision.md`、`docs/research_framing_motivational_delegation.md`、`docs/agent_loop_architecture.md`；当前收缩事实入口：`docs/agent_context.md`、`docs/current_status.md`、`docs/phase_checkpoints.md`、`docs/portfolio_capability_map.md`。

## 2. 必读治理协议

**所有助手开工前必须先读 `docs/context_governance.md`**。该协议定义三层文档边界、改动权限、推进感优先的开发风格、checkpoint 机制和决策日志。

简化版边界：
- **圣经层 Canon**（不得自行修改）：`docs/project_vision.md`、`docs/research_framing_motivational_delegation.md`、`docs/process_fidelity_eval_spec.md`、`docs/cross_domain_adapter.md`、`docs/world_entity_model.md`、`docs/agent_loop_architecture.md`
- **管控层 Governed**（可起草，主人审核）：`AGENTS.md`、`CLAUDE.md`、`docs/context_governance.md`、`docs/production_roadmap.md`、`docs/phase_checkpoints.md`、`docs/open_questions.md`、`paper/claim_policy.md`、`paper/claim_evidence_matrix.md`
- **自管理层 Working**（可自主更新，软上限 250 行）：`docs/agent_context.md`、`docs/current_status.md`、`docs/assistant_continuity.md`、`docs/workflows.md`、`docs/eval_dataset_archive.md`、`docs/eval_reviewer_sampling_packet.md`、`docs/model_profile_template_guide.md`、`docs/art_direction.md`、`docs/asset_generation_prompts.md`、`docs/map_sprite_style_guide.md`、`docs/game_client_environment.md`、`paper/research_claim_review_*.md`
- **归档层 Archive**：`docs/archive/`，仅供溯源

## 3. 开发风格硬约束

完整版见 `docs/context_governance.md` §3。**元原则（§3.0）：这些条款是判断辅助不是 KPI——以真实价值为准，推进与审慎都不是默认值，不为刷 claim level 或制造推进感而盲目推进、机械合规。** 下面是高频提醒：

1. **解决问题 > 最小改动**。需要重构就重构，不要用补丁链绕过结构性问题。
2. **完成里程碑必须停下汇报**，按治理协议 §5 模板输出 checkpoint review，等主人选方向再继续。
3. **避免无价值的重复 export / promote**；发现"刚做过几乎相同的事"先停下质疑，但 bug 修复 / 口径变更 / 主人要求的重跑说明理由后即可（非时间锁）。
4. **优先解决对研究或用户体验真正有价值的问题**；claim level 升级是价值兑现后的结果而非追逐目标。纯基础设施加固只在被真实 drift / regression / bug 触发时进行。
5. **真实 LLM / 人工 reviewer / API 充值 / 玩家手感这类需要主人配合的 blocker 必须显式询问**，不能默默绕过；遇到这类 blocker 停下询问是正确行为，不是推进不足。
6. **claim level 只能由主人显式确认才能升级**，AI 只能维持或降级。
7. **保守和激进都不是默认值**。边界清晰、风险可逆时选最直接、最有推进力的路径；边界不清或影响不可逆时主动审慎并对齐。

## 4. 新会话最小读取顺序

1. 运行 `npm.cmd run context:resume`，确认分支 / 脏区 / 当前阶段 / manual gate。
2. 读 `docs/context_governance.md`（圣经级治理协议，不读不能动）。
3. 读 `docs/agent_context.md`（当前入口、命令、最近下一步）。
4. 读 `docs/phase_checkpoints.md`（当前位置与下一阶段候选）。
5. 涉及实现 / 状态更新时核对 `docs/current_status.md`。
6. 跨家里 / 公司、多助手、子代理接续时参考 `docs/assistant_continuity.md`。

## 5. 按开发线读取

- 后端 / Director / Event Skill / Agent Loop：`docs/agent_loop_architecture.md`、`docs/world_entity_model.md`、`backend/`、`scripts/check.py`
- Godot 客户端：`docs/production_roadmap.md`、`docs/game_client_environment.md`、`clients/godot/README.md`、`clients/godot/`
- LLM / Debug / Eval：`docs/model_profile_template_guide.md`、`config/`、`backend/app/providers/`、`docs/agent_loop_architecture.md` §10、`docs/process_fidelity_eval_spec.md`、Debug API 相关代码
- 研究 framing / 跨域 adapter：`docs/research_framing_motivational_delegation.md`、`docs/process_fidelity_eval_spec.md`、`docs/cross_domain_adapter.md`
- Eval / Research Evidence：`docs/eval_dataset_archive.md`、`docs/eval_reviewer_sampling_packet.md`、`backend/app/eval/`、`scripts/run_agent_eval.py`
- 内容 / NPC：`backend/app/content/`（schema 已落代码，旧设计文档已归档至 `docs/archive/`）
- 资产：`docs/art_direction.md`、`docs/asset_generation_prompts.md`、`docs/map_sprite_style_guide.md`、`assets/manifests/asset_manifest.json`
- 论文：`paper/outline.md`、`paper/claim_evidence_matrix.md`、`paper/claim_policy.md`、`paper/research_claim_review_*.md`

## 6. 协作约束

- 改动通常聚焦当前任务；跨开发线变更时必须说明影响面。
- 状态文档区分 `code integrated` / `command checked` / `artifact backed` / `manual verified` / `manual unverified`。
- 后端持有权威世界状态；Godot 只做表现 + 合法工具调用。
- LLM 输出进入可见结果前必须经过解析、规则校验、fallback 和事件记录。
- 密钥、私有模型配置、本地绝对路径只放在本机配置或环境变量中。
- 已整理的 eval 证据子树（`.run/eval-promoted/` / `.run/eval-reviewer-packets/` / `.run/process-llm-evidence/`）可随 Git 同步；`.run/eval-runs/` 滚动导出区按本地临时产物处理（具体策略见 `docs/eval_dataset_archive.md`）。
- 新增 schema、事件字段、Debug 字段、eval artifact、Godot 消费字段前，先明确数据契约。

## 7. 常用验证命令

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

按任务线选择最小必要命令。`check` / `smoke` 默认不访问真实 LLM；真实 provider / 真实 Godot 窗口 / 玩家手感属于人工验收，不属于离线门禁。调整治理入口或本文件后建议运行 `npm.cmd run context:check` 和 `git diff --check`。

## 8. 助手适配说明

- **Codex**：默认风格偏保守，本文 §3 的硬约束对 Codex 优先级高于"最小修改"等内置倾向。请显式选取最直接的实现路径，遇到圣经层 / 管控层改动需求时先询问。
- **Claude Code**：通过 `CLAUDE.md` 导入本文。`.claude/rules/` 是路径触发提示，非独立指令源。
- **Kiro / 浮浮酱**：本文加 `docs/context_governance.md` 即完整指令集；不再读已归档的旧设计文档。
- **子代理**：先读 `docs/assistant_continuity.md` 接续协议，再按本文 §5 加载对应开发线源文档。
