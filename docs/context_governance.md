---
status: active
owner_lane: context-governance
last_verified: 2026-06-02
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
5. **推进感不等于 KPI**：能动性条款是判断辅助而非计分项，防止 AI 为"满足规则字面 / 刷指标"而盲目推进或机械合规（见 §3.0）。

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

### 3.0 元原则：规则是手段不是 KPI

本节所有风格条款是**判断辅助，不是计分指标**。它们存在是为了让 AI 助手做出对项目真实价值最有利的判断，而不是被当作必须刷满的 KPI：

1. **以真实价值为准绳**。当某条风格条款的字面要求与"对研究 / 产品 / 主人真实有利"冲突时，以真实价值为准并停下与主人对齐，而不是机械满足条款字面。
2. **推进与审慎都不是默认值**。边界清晰、风险可逆时主动推进；证据不足、影响不可逆、跨越边界时主动审慎。两者由具体情境的价值和风险决定，不存在"必须永远激进"或"必须永远保守"。
3. **不为制造推进感而推进**。不得为了触发汇报而拆碎或虚报里程碑，不得为了"看起来在升级 claim"而堆叠证据。里程碑由 exit criteria 客观定义，claim level 由证据真实强度和主人确认决定。
4. **古德哈特警戒**。claim level、推进力、改动量等任何指标一旦被当作目标去优化，就不再是好的度量；发现自己在"优化指标"而非"解决问题"时，停下质疑。

### 3.1 推进感优先

1. **解决问题 > 最小改动**。如果整体设计需要重构来获得正确解，就重构；不要用一连串补丁绕过结构性问题。
2. **完成一个里程碑就停下来汇报**，不要默默进入下一个里程碑。汇报模板见 §5。
3. **优先解决对研究或用户体验真正有价值的问题**；claim level 升级是价值兑现后的*结果*，不是直接追逐的目标（见 §3.0）。纯基础设施加固只在被 drift / regression / 真实 bug 触发时进行。
4. **保守和激进都不是默认值**（见 §3.0）。边界清晰、风险可逆时主动选最直接、最有推进力的路径；边界不清或影响不可逆时主动审慎并对齐。

### 3.2 反重复劳动

1. **避免无价值的重复 export / promote**。如果发现"刚刚做过几乎相同的事"，先停下质疑是否在原地打磨。但因 bug 修复、口径变更或主人要求需要重跑 / 重新 promote 时，说明理由后即可进行——这是对"无意义重复"的警戒，不是时间锁。
2. **不要为已稳定的基础设施层（manifest、archive、promote、drift policy 等）加新闸门**，除非被破坏性 drift / 真实 reviewer 反馈触发。
3. **不要以"补一份新 doc 解释为什么没退化"代替推进**。drift 解释属于自管理层短记录，不应膨胀为独立长文。

### 3.3 边界与许可

1. **跨圣经层契约的改动必须先和主人对齐**，不允许在 commit / chat 中默默修订。
2. **管控层文档的改动必须附"为什么"**，并在 commit message 第一行说明改动性质（重构 / 收缩 / 新增 checkpoint / 协议修订）。
3. **真实 LLM、人工 reviewer、玩家手感、API key、外部充值这类需要主人或外部资源配合的 blocker，必须显式标注并询问**，不能默默绕过或假装已完成。遇到这类 blocker 时停下询问是正确行为，不是推进不足。
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
| 2026-05-29 | 治理去 KPI 化：加 §3.0 元原则，软化 claim-level / 保守默认 / 24h 重复窗 / blocker 措辞为权衡式；.run 双环境策略落地（eval-runs 回归本地，promote 闸门跨机同步） | 防止能动性条款被当 KPI 盲目优化；eval-runs 全量入库不可持续 | 管控层（本协议 / AGENTS / .gitignore / claim_matrix） |
| 2026-06-02 | Loomstead 战略收缩为二线 portfolio 工程展示项目；Human Rating pilot 关闭，C2/C3/C4 限定为 metric / explainability 级 `promoted with caveat` | 数据核查发现 `hard_delegation` 是 metric stub，memory / relationship ablation 未在 promoted scenarios 中产生 `goalToolEvents` 行为分化；继续包装 human-believability / 论文主线会造成 overclaim，主人确认 `AlgoCoach-Flywheel` 为求职 + 论文主力 | 管控层（AGENTS / phase_checkpoints / claim_matrix / context entries） |

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
