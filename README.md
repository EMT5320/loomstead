# Agent Valley

> Narrative-primary 的可解释多 Agent 叙事运行时与研究环境，用于研究 Motivational Delegation 与 Process Fidelity Eval 在持久多 Agent 叙事世界中的效果。

`Agent Valley` 使用一个可玩的 Godot 田园生活切片作为 primary validation domain。项目重点不是做大规模“小镇模拟”或完整商业游戏，而是验证：当用户目标带有过程约束时，Director 如何通过动机偏置、事件 Skill、机会/资源调度、信息暴露和约束注入，间接推动拥有长期记忆与关系的自主 NPC 产生可信行动链，并用可复现指标评估过程是否可信。

Agent 助手启动入口请先读 [AGENTS.md](AGENTS.md) 与 [docs/agent_context.md](docs/agent_context.md)。当前事实以 [docs/current_status.md](docs/current_status.md) 为准，长期方向以 [docs/project_vision.md](docs/project_vision.md) 为准，研究 framing 以 [docs/research_framing_motivational_delegation.md](docs/research_framing_motivational_delegation.md) 为准。

## 当前定位

短句版本：

```text
Motivational Delegation for process-constrained goals in persistent multi-agent narratives.
```

项目差异化主轴：

- **少而深**：首版聚焦 4 个核心 NPC + 2 个 stub NPC，优先做深主观记忆、关系演化、启发式经验和可解释决策链路。
- **可解释**：Director、Event Skill、NPC 决策、工具调用、世界变更、主观记忆和关系变化都写入可追踪 trace。
- **可评估**：Process Fidelity Eval 不只看最终状态，还检查是否绕过过程、是否强制 NPC 行动、关系变化是否有记忆证据、Director 是否过度干预。
- **玩家可见**：研究能力必须落到屏幕上的 NPC 行动、事件反应、关系变化、记忆差异和 Debug / 观察者视图，而不是只停留在后端抽象。

## 为什么仍然是“小镇”

小镇是项目的第一研究环境，不是通用架构的开场 demo。Process Fidelity 需要人类能直觉判断“这个过程像不像真的发生过”：

- “两名 NPC 变亲近”不能只看关系数值变高。
- “布兰娜原谅玩家”不能只看 `forgiven=true`。
- “星灯祭顺利举办”不能只看 `festival_success=true`。

这些目标的价值在于中间过程：动机变化、共同经历、误会修复、旁观者反应、长期记忆沉淀和后续行为引用。Godot 生活模拟切片让这些过程能被玩家看到，也让 Debug / Eval 能对照真实世界事件链。

## 当前阶段

- **Phase 1：活着的世界** 已落地，等待真实 Godot 窗口复验。
  - 后端提供权威世界状态、玩家动作 API、Director v0、单个星灯祭 Event Skill、Debug / Memory 查询入口。
  - Godot 默认主场景已接入地图移动、NPC 小人、`/api/world/tick`、世界动态面板、远处事件提示、`E` 键对话和 VN 回执。
  - 仍需人工复验 NPC 分散行动、HUD 暂停/倍速、`WorldPulsePanel`、远处事件 beacon、`E` talk 和错误提示。
- **Phase 2：骨架建立期** 尚未启动。
  - 目标是一次性铺好 ToolDefinition 注册表、MotivationEngine、CapabilityRegistry、双轨主观记忆、HeuristicLibrary、ArbitrationLayer、WorldEntities、EvalFramework、观察者模式和研究 baseline。
  - Phase 2 启动后旧 `LifeActionExecutor` 退役，不与新 MotivationEngine 并行运行。

## 核心系统

```text
Godot Client
  ├─ 玩家移动 / VN 演出 / NPC 与事件可视化
  └─ 观察者模式与 Debug UI（Phase 2+）

Python Agent Server
  ├─ World / Simulation：权威世界状态、合法工具执行、事件流
  ├─ Director：低频叙事节奏、间接干预、Event Skill 激活
  ├─ Event Skill：局部压力源、约束、后果类型、fallback 文本与资产提示
  ├─ NPC Agent Loop：动机、能力过滤、主观记忆、启发式学习、仲裁
  ├─ Provider：RuleBasedProvider + OpenAI-compatible CloudApiProvider
  └─ Eval / Debug：Trace、ablation、Process Fidelity 指标、公开 dataset 输出
```

核心研究链路：

```text
Process-constrained Goal
  -> Director Interventions
  -> NPC Motivation / Opportunity / Information / Constraint Changes
  -> Autonomous Tool Actions
  -> Objective Event Log
  -> Subjective Memory Views + Relationship Edges
  -> Process Fidelity Eval + Debug Trace
```

## 已有能力概览

- Python Agent Server：`GET /api/world/state`、`POST /api/player/action`、`POST /api/world/tick`、Debug / Memory / model config API。
- Director v0：`WorldDigest`、`TensionDetector`、`SkillRouter`、`DirectorBeat`、`DirectorValidator`、`DirectorQueueManager`。
- Event Skill：星灯祭供应短缺事件，包含查看、选择、关系变化、记忆写入、事件反应、夜间反思和统一 outcome record。
- Content Codex：6 份首发 NPC 深度卡，包含语气、秘密、关系阶段、礼物反应、独白种子、谣言钩子和生活行动素材。
- LLM / Debug：RuleBasedProvider、OpenAI-compatible CloudApiProvider、profile 路由、热重载、fallback、token/成本/延迟记录。
- Godot 客户端：Godot 4.x 项目、默认 `world_main.tscn`、地图移动、NPC / 事件 marker、VN 面板、世界动态面板。
- 资产管线：静态背景、事件 CG、角色立绘、地图小人、交互 marker、manifest 校验与 prompt_ready backlog。

更细的当前事实请读 [docs/current_status.md](docs/current_status.md)。

## 本地运行

建议在 Windows PowerShell 中使用 `npm.cmd`，避免 shell 解析差异。

### 启动后端

```powershell
npm.cmd run start
```

后端默认监听本地开发端口，迁移期 Web Debug / 观察台可通过浏览器打开本地服务页面。

### 打开 Godot 主客户端

```powershell
npm.cmd run client:run
```

当前默认进入 `clients/godot/scenes/world_main.tscn`。旧 P0 UI 仍可用：

```powershell
npm.cmd run client:run:legacy
```

### 常用检查

```powershell
npm.cmd run context:check
npm.cmd run check
npm.cmd run smoke
npm.cmd run asset:check
npm.cmd run client:env
npm.cmd run client:run:check
git diff --check
```

按任务线选择最小必要命令；修改上下文治理或文档入口时至少运行 `npm.cmd run context:check` 和 `git diff --check`。

## 模型配置

提交态默认使用规则 fallback，避免无密钥环境阻塞开发。

- 模板：`config/models.example.json`
- 本机配置：`config/models.json`、`config/models.local.json`（已忽略，不提交密钥）
- 推荐检查：

```powershell
npm.cmd run model:check
```

配置支持按 NPC / feature 选择 profile，并在 Debug 记录中展示 provider、profile、messages、rawText、parsed、usage、latency 和 fallbackReason。真实 API key 只能放本地 overlay 或环境变量。

## 文档入口

- [docs/README.md](docs/README.md)：文档索引与渐进式读取路线。
- [docs/project_vision.md](docs/project_vision.md)：长期愿景、差异化和成功标准。
- [docs/research_framing_motivational_delegation.md](docs/research_framing_motivational_delegation.md)：研究定位、核心反论点、baseline matrix。
- [docs/process_fidelity_eval_spec.md](docs/process_fidelity_eval_spec.md)：Process Fidelity 指标、hard delegation baseline、ablation protocol。
- [docs/agent_loop_architecture.md](docs/agent_loop_architecture.md)：NPC agent loop 核心设计。
- [docs/world_entity_model.md](docs/world_entity_model.md)：世界实体 schema 与工具空间。
- [docs/production_roadmap.md](docs/production_roadmap.md)：阶段路线与 Phase 2 骨架清单。
- [docs/current_status.md](docs/current_status.md)：当前实现事实、缺口和人工验收状态。
- [docs/goal_board.md](docs/goal_board.md)：开发线看板、写入边界和交接格式。

归档文档位于 [docs/archive/](docs/archive/)，只供历史溯源，不作为当前事实源。

## 开发边界

- 后端 Runtime 持有权威世界状态；Godot 只读状态、提交玩家动作和展示结果。
- LLM 只生成文本、结构化建议或工具意图；世界状态变更必须经过规则执行、校验和事件记录。
- 新增 NPC / 地点 / 事件 / 工具 / 存档字段前先明确数据契约和 Debug 证据。
- 未经代码、命令或真实窗口验证的能力只能写成待验证，不写成已完成。
- 不提交密钥、本地绝对路径、未登记来源的资产或临时运行文件。

## 研究输出定位

当前目标是研究原型、benchmark environment、demo / dataset / evaluation work，而不是直接承诺 full paper。Phase 2 的硬证据包括：

- process-constrained goal specs。
- Hard Delegation baseline、Direct State Setter、no-memory ablation 等对照。
- EventStore、SubjectiveMemory、RelationshipEdges、Interventions、EvalSummary 可复现导出。
- 能回答“为什么不直接 task delegation”“关系记忆是不是装饰”“与 Smallville 类模拟相比新问题在哪”的量化表格。
