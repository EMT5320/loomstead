---
status: active
owner_lane: context-governance
last_verified: 2026-05-28
startup_load: first-read
source_of_truth: true
scope: 三层文档边界、改动权限、推进节奏与开发风格硬约束
---

# Loomstead 上下文治理协议

本文是 `Loomstead` 文档系统与 AI 助手协作的根级协议。所有助手在治理入口出现冲突时以本文为准；本文与圣经层文档冲突时，先停下与主人对齐而不是单方修订。

## 1. 治理目标

1. **彻底解决上下文间歇性膨胀、内容漂移和过时堆叠**。状态文档只记当前事实，历史流水交给 git。
2. **明确每份文档的改动权限**，防止 AI 助手在没有许可的情况下重写关键决策。
3. **把推进感作为一等公民**：达成里程碑必须停下来汇报，而不是默默进入下一轮加固。
4. **保留 AI 助手的能动性**：不强求"最小修改"，必要重构允许且鼓励，前提是边界清晰。

## 2. 三层文档边界

每份 markdown 在元信息或本文表格中声明所属层。

### 2.1 圣经层 Canon

定义项目身份与不可随意修订的核心契约。AI 助手**不得自行修改**圣经层；任何改动必须由主人显式许可，并以"研究方向修订"形式记录于本文 §6 决策日志。

| 文档 | 内容主轴 |
|---|---|
| `docs/project_vision.md` | 产品愿景、差异化主轴、成功标准 |
| `docs/research_framing_motivational_delegation.md` | 研究定位、核心反论点、baseline matrix |
| `docs/process_fidelity_eval_spec.md` | Process Fidelity 指标公式与 Eval 验收线 |
| `docs/cross_domain_adapter.md` | 跨域 adapter 接口契约 |
| `docs/world_entity_model.md` | 世界实体 schema 契约 |
| `docs/agent_loop_architecture.md` | NPC agent loop 设计源（含工程清单待后续清理，过渡期暂入圣经层） |

### 2.2 管控层 Governed

承载工程路线、决策和治理协议。AI 助手**可起草改动**，但必须在改动 PR / commit 中附"为什么"段落，并在主人审核合并后才生效。每次改动需更新文档 frontmatter 的 `last_verified`。

| 文档 | 内容主轴 |
|---|---|
| `AGENTS.md` | 跨助手指令入口与风格条款 |
| `CLAUDE.md` | Claude Code 适配薄层 |
| `docs/context_governance.md` | 本治理协议 |
| `docs/production_roadmap.md` | 阶段路线与 exit criteria |
| `docs/phase_checkpoints.md` | 推进感 checkpoint 板 |
| `docs/open_questions.md` | 决策记录与待解问题 |
| `paper/claim_policy.md` | 论文 claim 政策 |
| `paper/claim_evidence_matrix.md` | claim 证据矩阵 |

### 2.3 自管理层 Working

承载实现事实、操作流程与短周期记录。AI 助手**可自主更新**，但必须遵守：

- 单文件软上限 250 行；超过即触发"是否拆分或归档"检讨
- 只记当前事实、当前命令、当前缺口；**不记历史流水**（写完即用，过时即删）
- 同一证据类的事实不重复堆叠多日条目；历史变化由 git history 承载

| 文档 | 内容主轴 |
|---|---|
| `docs/agent_context.md` | 新对话第一入口 |
| `docs/current_status.md` | 当前实现事实与验证状态 |
| `docs/assistant_continuity.md` | 跨助手接续协议 |
| `docs/workflows.md` | workflow 索引 |
| `docs/eval_dataset_archive.md` | Eval 归档操作流程 |
| `docs/eval_reviewer_sampling_packet.md` | Reviewer packet 操作流程 |
| `docs/model_profile_template_guide.md` | 模型 profile 配置流程 |
| `docs/art_direction.md` | 美术方向操作准则 |
| `docs/asset_generation_prompts.md` | 资产 prompt 库 |
| `docs/map_sprite_style_guide.md` | 地图小人风格指南 |
| `docs/game_client_environment.md` | Godot 本机环境备忘 |
| `paper/research_claim_review_*.md` | 单次 claim review 快照 |

### 2.4 归档层 Archive

只读历史，不作为当前事实源。位置：`docs/archive/`。AI 助手不得引用归档文档作为决策依据；如需复活结论，必须先在新核心文档显式吸收。

## 3. 开发风格硬约束

> 这一节是核心反 over-engineering 条款，对 AI 助手的优先级**高于"最小修改"等保守倾向**。

### 3.1 推进感优先

1. **解决问题 > 最小改动**。如果整体设计需要重构来获得正确解，就重构；不要用一连串补丁绕过结构性问题。
2. **完成一个里程碑就停下来汇报**，不要默默进入下一个里程碑。汇报模板见 §5。
3. **优先选能让 claim level 或用户可见体验升级的改动**；纯基础设施加固只在被 drift / regression / 真实 bug 触发时进行。
4. **保守不是默认值**。在边界清晰的前提下，AI 助手应主动选取最直接、最有推进力的实现路径。

### 3.2 反重复劳动

1. **同一份证据 24 小时内不应被 promote 第二次**。如果发现"刚刚做过类似的事"或"又跑了一次几乎相同的 export"，必须先停下质疑是否在原地打磨。
2. **不要为已稳定的基础设施层（manifest、archive、promote、drift policy 等）加新闸门**，除非被破坏性 drift / 真实 reviewer 反馈触发。
3. **不要以"补一份新 doc 解释为什么没退化"代替推进**。drift 解释属于自管理层短记录，不应膨胀为独立长文。

### 3.3 边界与许可

1. **跨圣经层契约的改动必须先和主人对齐**，不允许在 commit / chat 中默默修订。
2. **管控层文档的改动必须附"为什么"**，并在 commit message 第一行说明改动性质（重构 / 收缩 / 新增 checkpoint / 协议修订）。
3. **真实 LLM、人工 reviewer、玩家手感、API key、外部充值这类需要主人或外部资源配合的 blocker，必须显式标注并询问，不能默默回避**。回避会被视为推进不足。
4. **claim level 只能由主人显式确认才能升级**；AI 助手只能维持或降级。

### 3.4 文档纪律

1. 自管理层文档**不写历史 changelog 段落**，git history 是唯一历史源。
2. 自管理层文档**不引用 manual gate 的 commit hash 列表**；用语义描述当前状态即可。
3. 圣经/管控层文档**禁止抄写其他文档的整段内容**；用引用代替。
4. 新增 doc 前先在已有自管理层文档承载；承载不下时再单独成文，且必须先归位三层边界。

## 4. Checkpoint 机制

阶段推进通过 `docs/phase_checkpoints.md` 中的明确 checkpoint 控制：

- 每个 checkpoint 定义 yes/no 判据 (exit criteria)
- AI 助手到达 checkpoint 时**必须停下**，输出 checkpoint review（≤ 200 词，模板见 §5）
- 主人显式选择下一阶段方向后，AI 才能解锁下一个 checkpoint
- 越过 checkpoint 而没有 review 是治理违规，需在下次对话开头补 review

## 5. Checkpoint Review 模板

```md
## Checkpoint <id>: <name>

### 完成项
- <具体已达成的事实>

### 剩余缺口
- <相对 exit criteria 仍未达成的项>

### 下一阶段候选
A. <选项 A：方向 + 估时 + 主要风险>
B. <选项 B：...>
C. <选项 C：...>

### 浮浮酱推荐
<明确推荐 1 项并说明理由>
```

## 6. 决策日志

| 日期 | 决策 | 触发原因 | 影响层 |
|---|---|---|---|
| 2026-05-19 | 项目重定位为 narrative-primary 多 Agent 叙事运行时 | 与规模化竞品差异化 | 圣经层（vision/framing） |
| 2026-05-20 | 研究主卖点改为 Motivational Delegation + Process Fidelity Eval | 强化研究护栏 | 圣经层（research framing） |
| 2026-05-21 | Phase 1 收口，世界默认场景 `world_main.tscn` | 主人窗口验收 | 管控层（roadmap） |
| 2026-05-28 | 上下文治理改革：三层边界、风格条款、checkpoint 机制 | 上下文反复膨胀、推进感缺失 | 管控层（本协议） |

后续治理级决策按"日期 / 决策 / 触发 / 影响层"四列追加。

## 7. 协议生效与例外

- 本协议自 2026-05-28 起对所有 AI 助手生效。
- 老 commit 中的"最小修改"风格语句（散落在 `docs/assistant_continuity.md` 等）以本文为准。
- 当本协议与其他管控层文档出现冲突时，AI 助手必须先停下询问，不得自行调和。

## 8. 验证

调整本协议或迁移文档边界后，建议运行：

```powershell
npm.cmd run context:check
git diff --check
```
