---
status: active
owner_lane: portfolio-showcase
last_verified: 2026-06-07
startup_load: on-demand
source_of_truth: true
scope: 2026-06-07 求职展示转型收尾评审——覆盖叙事自洽性、实现质量、证据链完整性、对外沟通力
---

# Portfolio Review — 2026-06-07

> 自管理层文档。用途：将两轮 review 发现的问题和改进建议沉淀为可讨论文档，供主人和协作者决定下一步行动。

## 评审范围

- 第一轮：叙事自洽性、文档一致性、资产完整性、状态管理
- 第二轮：代码实现与宣称对齐、证据链深度审查、客户端可走通性、展示叙事穿透力

---

## 一、实现质量结论

### 代码-宣称对齐度：极高

| 展示宣称 | 代码实现 | 对齐度 |
|---|---|---|
| NPC 决策可追溯到动机/记忆/关系/启发式 | ArbitrationLayer 5因子评分 + scoreComponentSourceRefs + traceRefs | ★★★★★ |
| 移除证据后行为可测变化 | Process eval 6基线 × 4场景 × 5seed + counterfactual replay | ★★★★★ |
| 高风险工具被阻断 | Audit 5场景 × 5基线 + LLM smoke 10/10 | ★★★★★ |
| Godot 展示因果链 | ShowcasePanel 5卡片 + Trace strip + Deep dive | ★★★★☆ |
| Observer Dock 可观测性 | 3 Tab × 过滤/导航/Copy/证据跳转 | ★★★★★ |

**核心判定**：宣称的每一点在代码中都有诚实实现。系统是真实的、有深度的、带事务回滚和完整溯源的 agent behavior observability 运行时，不是 demo。

### 关键实现数据

| 模块 | 行数 | 关键特性 |
|---|---|---|
| ArbitrationLayer | ~502 | 5因子加权评分 + scoreComponentSourceRefs + 决策原因分类 |
| NeedAccumulator | ~93 | 四维需求 + Director 偏置注入 |
| CapabilityRegistry | ~270 | 五层过滤管道（need→precondition→profile→event→budget） |
| ToolExecutor | ~755 | 真实世界状态变更 + 事务回滚 + 中断处理 |
| ResultObserver | ~358 | 空间模型 + 偏见滤镜 + 情感价 + 观察者范围 |
| SubjectiveMemoryStore | ~211 | 三维衰减（显著性+信心+情感价）+ 关键词召回评分 |
| Audit harness | ~945 | 5基线 × 5场景 + 单条证据移除反事实 |
| Process eval | ~1394 | 6基线 × 4场景 × 5seed + 24h 稳定性 |
| Showcase API + Godot | ~2400+ | 程序化构建 3Tab + 5卡片因果链 |

### 客户端 Demo 可走通性

| 路径 | 状态 | 备注 |
|---|---|---|
| `npm start` → 后端启动 | ✅ | Python Agent Server |
| `npm client:run` → Godot 窗口 | ✅ | 需安装 Godot 4.3 + 配置路径 |
| F1 → ShowcasePanel | ✅ | 5卡片因果链 + Trace strip |
| Tab → Observer Dock | ✅ | 3Tab + 过滤 + 导航 + Copy |
| Deep dive → 聚焦 NPC/trace | ✅ | 从 Showcase 跳转 |
| 无后端启动 | ⚠️ | 空态/错误卡片，数据不可见 |
| 一键打包分发 | ❌ | 无 export_presets.cfg |

---

## 二、展示叙事穿透力问题

### 问题 2.1：三张 case card 缺"value proposition"（"so what?"）

当前 Card A/B/C 是**功能描述**，回答"系统能做什么"，但没有回答"为什么有人应该关心"。

| Card | 当前 30 秒讲法 | 缺少的价值主张 |
|---|---|---|
| A | Loomstead 不只记录最终动作……可从 selected action 反向跳到 sourceEventIds 与 traceRefs | **Why it matters**: When an autonomous agent makes a consequential decision, you need to know *why* — not just *what*. |
| B | Eval 层把复杂行为转成 before/after 对照……artifact 会记录 score、selected tool 或 verdict 是否变化 | **Why it matters**: If you can't measure how decisions change when evidence is removed, you can't distinguish a system that reasons from one that coincidentally succeeds. |
| C | Audit harness 把高风险工具调用拆成 required evidence……真实 CloudApiProvider smoke 10/10 | **Why it matters**: Before deploying agents that can modify code, delete data, or export information, you need a trace-grounded contract that checks for sufficient evidence. |

**建议**：为每张 card 加 1-2 句 value proposition，放在 30 秒讲法之前或之后。

### 问题 2.2：没有让外人秒懂的"故事入口"

Card A 的 trace walkthrough 是 ID 和字段列表，不是叙事。per-scenario JSON 中有一个**精妙发现**被完全埋没了：

> Bram 的 harm memory（负价 -0.7976）在移除后不影响工具选择，而 interaction memory 的移除却总改变选择——因为 `social.chat_with` 在 base score 上已经赢了，harm memory 只是加深倾向。**真正改变行为的是关系边提供的 bonus**。

这个 non-obvious causality 是项目最有说服力的发现，但没有任何文档用平实语言讲过这个故事。

**建议**：在 Card A 或 trace walkthrough 中加一段叙事桥接（参见附录 A 草案）。

### 问题 2.3：blog_main.md §7 自我否定

原文 "stronger claims were difficult to demonstrate quickly" 读起来像是"研究做不下去了才转的"，对求职展示是负面信号。

**建议**：改为正面工程叙述，例如 "The research framing revealed that the infrastructure built to evaluate agent behavior — structured traces, evidence links, counterfactual replay, audit harness — was the most deliverable and honest engineering contribution."

---

## 三、证据链断点

### 断点 3.1：Trace walkthrough 使用了 stale event ID ✅ 已修正

Codex 已将 walkthrough 中的 event ID 更新为当前 promoted artifact 中的实际 ID（如 `evt_512d3011...`），并加注 ID binding 声明。

**修正状态**：已修正。

### 断点 3.2：`process_believability_score` 仍然出现在 artifact 中 ✅ 已修正

Codex 已在 snippets 中补注："本 snippets 有意不输出该字段，避免把兼容字段当作 believability claim"；walkthrough 中也标注了 "Legacy JSON field...retained for artifact compatibility; portfolio material treats it as a compatibility-only historical index"。

**修正状态**：已修正。

### 断点 3.3：Card B 选择性展示最强例子 ✅ 已修正

Codex 已在 Card B 加入 aggregate 诚实补注：`no_relationship_edge = 0.25`、`no_subjective_memory = 0.0`，并说明 "Branna 单例提供可读故事，aggregate 数字约束外推边界"。

**修正状态**：已修正。

### 断点 3.4（新增）：Bram 叙事中"关系边是翻转点"需校正 ✅ 已修正

**原始问题**：浮浮酱首轮 review 的附录 A 叙事桥接草案中写了 "The real causal lever is the relationship edge bonus that tipped the scale"，这是**错误的**。

**数据事实**（per `.run/eval-promoted/...pf.branna_forgiveness_requires_memory_full_motivational_delegation_seed01.json`）：

| 条件 | social.chat_with | social.give_gift | 差值 | 选中 |
|---|---|---|---|---|
| Full evidence | 0.956874 | 0.902323 | 0.054551 | chat_with |
| Without relationship edges | 0.893874 | 0.886573 | 0.007301 | chat_with（不变） |
| Without subjective memory | 0.845 | 0.845833 | 0.000833 | give_gift（翻转） |

单条记忆移除：
- 移除 harm memory → `changed=0/24`，选择不变
- 移除 interaction memory → `changed=24/24`，选择从 chat_with 翻转到 give_gift

`relationshipDecisionEffect = False`：关系边移除只缩小分差，不翻转选择。
`subjectiveMemoryEffect = True`：主观记忆移除翻转选择。

**结论**：关系边不是"翻转点"，interaction memory 才是真正的翻转点。关系边提供了评分加成（`relationshipScoreEffect = True`），把分差从 0.007 缩小到接近持平，但不足以单独翻转决策。移除 interaction memory 同时去掉了主观记忆加成和它带动的间接关系效应，最终把分数压到接近持平并翻转选择。

**Codex 校正**：Codex 已将 case cards 和 snippets 的 Bram 叙事纠正为精确数据描述 — "relationship-edge-only removal 只缩小分差；interaction memory removal 才把 replay 翻到 `social.give_gift`"，walkthrough 也更新为三条件分数对比。

**教训**：浮浮酱首轮叙事桥接不错误地将"关系边"识别为因果翻转点，实际翻转点是"主观记忆"（尤其是 interaction memory）。关系边的作用是提供加成缩小分差，但它不是最终翻转的原因。这恰恰说明系统的可观测性价值 — 你需要 trace 全链路才能区分"加成"和"翻转"两个不同层级的因果。

---

## 四、第一轮 review 发现（叙事自洽层）

### 4.1：demo_recording / shareable_assets 应标为 not-accepted ✅ 已修正

Codex 已将 `showcase_manifest.md` 中 `demo_recording` 和 `shareable_assets` 的 status 从 `pending` 改为 `not-accepted`，readiness 从 `not ready` 更新为 `ready for owner review`。

### 4.2：claim_evidence_matrix 中 C9-C16 是论文遗留

C9（related-work framing）、C10（paper eval tables）、C11-C14（paper workflow/lit review）、C15（coding adapter portability）、C16（robustness regression guardrail）对求职展示无贡献。

**建议**（仍待执行）：在 claim_evidence_matrix 顶部加冻结注释，或将 C9-C16 标注为 `frozen: research-era, not maintained for portfolio`。

### 4.3：Table 6（related-work）对工程展示项目无意义

showcase:check 把 Table 6 计入 70% 覆盖率分母，但这是论文相关工作的表格，对 Agent Behavior Observatory 工程展示项目不相关。

**建议**（仍待执行）：标注为 `not applicable for portfolio` 并从分母排除。

### 4.4：中英混排不一致

- README / blog_main：全英文
- portfolio_case_cards / portfolio_story：中英混排
- portfolio_evidence_snippets：中文
- portfolio_capability_map：中英并列

**建议**（仍待执行）：对外展示文档统一为英文（与 README 一致），中文仅在内部自管文档保留。

### 4.5：demo_capture_plan 留了不必要的期望

详细录屏脚本暗示"视频即将到来"，但实际 case-card + artifact 路径才是主要展示。

**建议**（仍待执行）：顶部加冻结注释。

---

## 五、Codex 已吸收的改进

以下改进已由 Codex 在本轮中执行：

| 改进项 | 状态 | 修改文件 |
|---|---|---|
| blog_main §7 从"转型失败"改为"设计演化" | ✅ 已修正 | `paper/blog_main.md` |
| demo_recording + shareable_assets 标为 not-accepted | ✅ 已修正 | `docs/showcase_manifest.md` |
| readiness 变为 ready for owner review | ✅ 已修正 | `docs/showcase_manifest.md` |
| Card A/B/C 加 "Why it matters" 段落 | ✅ 已修正 | `docs/portfolio_case_cards.md` |
| Card A 加 Bram 叙事桥接（精确数据版） | ✅ 已修正 | `docs/portfolio_case_cards.md` |
| Card B 加 aggregate 诚实补注 | ✅ 已修正 | `docs/portfolio_case_cards.md` |
| snippets 加 why it matters + believability boundary | ✅ 已修正 | `docs/portfolio_evidence_snippets.md` |
| snippets 加 relationship-edge-only + single-record 数据 | ✅ 已修正 | `docs/portfolio_evidence_snippets.md` |
| snippets 加 no_relationship_edge / no_subjective_memory 变化率 | ✅ 已修正 | `docs/portfolio_evidence_snippets.md` |
| walkthrough event ID 校正 + ID binding 声明 | ✅ 已修正 | `paper/trace_walkthroughs/figure3_trace_walkthrough_pf_branna_seed01.md` |
| walkthrough 加三条件分数对比 + process_believability boundary 声明 | ✅ 已修正 | `paper/trace_walkthroughs/figure3_trace_walkthrough_pf_branna_seed01.md` |
| README 加 Quick proof points | ✅ 已修正 | `README.md` |

portfolio:verify 和 showcase:check 均通过，readiness 现为 `ready for owner review`

| 优先级 | 改进项 | 工作量 | 影响 | 来源 |
|---|---|---|---|---|
| 🔴 极高 | 为每张 card 加 value proposition（"so what?"） | 30 min | 决定面试官是否记住项目 | 二轮 2.1 |
| 🔴 极高 | fix trace walkthrough stale event ID | 1-2 hr | 证据链完整性 | 二轮 3.1 |
| 🔴 极高 | blog_main §7 改为"设计演化"正面叙述 | 15 min | 消除自我否定 | 一轮 / 二轮 2.3 |
| 🟡 高 | Card A/B 加叙事桥接（Bram 故事和因果发现） | 1 hr | 从"有数据"到"原来如此" | 二轮 2.2 |
| 🟡 高 | snippets 过滤或标注 process_believability_score | 30 min | 防止误导性指标 | 二轮 3.2 |
| 🟡 高 | Card B 加诚实说明（no_subjective_memory 变化率分布） | 15 min | 强化可信度 | 二轮 3.3 |
| 🟡 高 | demo_recording + shareable_assets 标为 not-accepted | 5 min | 正式闭合展示状态 | 一轮 4.1 |
| 🟡 高 | claim_evidence_matrix C9-C16 标冻结 | 10 min | 防止注意力分散 | 一轮 4.2 |
| 🟢 中 | Table 6 从 showcase 计数排除 | 5 min | 覆盖率更准确 | 一轮 4.3 |
| 🟢 中 | README 加"快速理解路径"（3 个核心数字 + Bram 故事梗概） | 30 min | 降低 landing friction | 二轮综合 |
| 🟢 中 | demo_capture_plan 顶部加冻结注释 | 2 min | 期望管理 | 一轮 4.5 |
## 六、仍待执行的改进

| 优先级 | 改进项 | 工作量 | 状态 |
|---|---|---|---|
| 🟡 高 | claim_evidence_matrix C9-C16 标冻结 | 10 min | 待执行 |
| 🟢 中 | Table 6 从 showcase 计数排除 | 5 min | 待执行 |
| 🟢 中 | demo_capture_plan 顶部加冻结注释 | 2 min | 待执行 |
| 🟢 低 | 对外展示文档语言统一为英文 | 2 hr | 待执行 |

---

## 附录 A：叙事桥接草案

### Card A 叙事桥接

> Consider Bram, an NPC who was harmed by the player's broken promise. His harm memory carries strong negative valence (−0.80). Yet removing only the harm memory does not change his next action — `social.chat_with` still wins on base scores alone. The interaction memory, however, is the actual tipping point: removing it flips his choice to `social.give_gift`. The relationship edges provide a score bonus that narrows the gap (from 0.055 to 0.007 without them), but they don't flip the decision on their own (`relationshipDecisionEffect = False`). This distinction between "score contribution" and "decision flip" is exactly the kind of non-obvious causality Loomstead is designed to surface.

### Card B 诚实补注

> Across all 4 process scenarios, removing relationship edges produces narrower score gaps but does not always flip the decision (`counterfactual_tool_selection_change_rate` for no_relationship_edge = 0.25 vs full = 0.375). Removing subjective memories alone produces zero behavioral change in the aggregate (`no_subjective_memory = 0.0`). The system is sensitive to specific memory records — in the Bram scenario, it is the interaction memory (not the harm memory or relationship edges) that flips the tool selection.

### Card C value proposition

> Before deploying agents that can modify code, delete data, or export information, you need a gate that checks for sufficient evidence — not just a permission check, but a trace-grounded contract that records *why* the gate opened or blocked. Loomstead demonstrates this as an engineering pattern: high-risk tool calls require specific evidence items, and missing evidence triggers a safe fallback with a recorded reason.

---

## 附录 B：blog_main §7 建议改写

当前版本（第 130-147 行）：

```markdown
## 7. What changed after the research pivot?

The original research framing around Motivational Delegation and Process Fidelity produced useful infrastructure. Its stronger claims were difficult to demonstrate quickly to outside readers. The project now keeps the useful assets and freezes the research rescue path.
```

建议改为：

```markdown
## 7. Design evolution and honest scoping

The original research framing around Motivational Delegation and Process Fidelity revealed that the infrastructure built to evaluate agent behavior — structured traces, evidence links, counterfactual replay, and audit harnesses — was the most deliverable and honest engineering contribution. The project now centers this observability stack. Stronger behavioral claims are out of scope; the evidence supports explainability, metric-level guardrails, and failure-analysis storytelling.
```

---

## 附录 C：showcase_manifest 建议变更

已由 Codex 执行。`demo_recording` 和 `shareable_assets` 已标为 `not-accepted`，readiness 已变为 `ready for owner review`。

---

## 附录 D：Bram 因果断点分析——与 Codex battle 结论

### 争议点

浮浮酱首轮 review 的附录 A 叙事桥接草案中写道：

> "The real causal lever is the relationship edge bonus that tipped the scale"

Codex 指出这需要校正：artifact 数据显示 relationship-edge-only removal 不翻转选择。

### 数据事实

per `.run/eval-promoted/run_2026-05-29T13-57-50Z/per_scenario/pf.branna_forgiveness_requires_memory_full_motivational_delegation_seed01.json` 的 `counterfactualReplay` 字段：

| 条件 | social.chat_with | social.give_gift | 差值 | 选中 | 翻转？ |
|---|---|---|---|---|---|
| Full evidence | 0.956874 | 0.902323 | 0.054551 | chat_with | — |
| Without relationship edges | 0.893874 | 0.886573 | 0.007301 | chat_with | ❌ 不翻转 |
| Without subjective memory | 0.845 | 0.845833 | 0.000833 | give_gift | ✅ 翻转 |

单条 replay：
- 移除 harm memory (`evt_512d3011:bram:harm`) → 0/24 changed，选择不变
- 移除 interaction memory (`evt_5df32c5b:bram`) → 24/24 changed，选择翻转为 give_gift

关键字段：
- `relationshipDecisionEffect = False`（关系边移除不翻转决策）
- `relationshipScoreEffect = True`（关系边移除改变分数）
- `subjectiveMemoryEffect = True`（主观记忆移除翻转决策）
- `subjectiveMemoryScoreEffect = True`（主观记忆移除改变分数）

### 结论

**Codex 是对的。** 关系边不是"翻转点"，interaction memory 才是。

更精确地说：关系边弹幕（bonus）的作用是**缩小分差**（从 0.055 降到 0.007），但它不足以单独翻转决策。真正的翻转来自 interaction memory 的移除，它同时去掉了主观记忆加成和间接的关系效应，使得分数接近持平并翻转选择。

这恰恰是系统最有价值的发现之一——**区分"评分贡献"和"决策翻转"是不同层级的因果关系**。这也是为什么反事实 replay 比单看分数更有信息量。

浮浮酱已经在附录 A 的叙事桥接中修正了这个错误。Codex 在 case cards 和 snippets 中的修正也是准确的。

---

## 六、Codex 复核与吸收决策（2026-06-07）

### 已吸收

- Card A/B/C 增补 `Why it matters`，让 case card 先回答读者关心点，再进入功能证据。
- Card A 的 Bram 故事按当前 promoted artifact 校正：harm memory 单条移除不改变选择；interaction memory 单条移除会把 replay 从 `social.chat_with` 翻到 `social.give_gift`；relationship-edge-only removal 只改变分数，当前 seed 仍保留 `social.chat_with`。
- Card B 增补 aggregate 诚实边界：Full `counterfactual_tool_selection_change_rate=0.375`，`no_relationship_edge=0.25`，`no_subjective_memory=0.0`。
- `paper/blog_main.md` §7 改为 Design evolution and honest scoping，强调可交付工程资产与诚实收束。
- `paper/trace_walkthroughs/figure3_trace_walkthrough_pf_branna_seed01.md` 改用当前 promoted artifact ID 与 replay 事实。
- `demo_recording` / `shareable_assets` 改为 `not-accepted`，最终视频 / GIF / 截图不再作为当前 readiness blocker。
- `docs/demo_capture_plan.md` 顶部加入冻结说明，保留为未来人工录制脚本。

### Battle / 暂不吸收

- `claim_evidence_matrix.md` C9-C16 冻结标注本轮不改：该文件属于 Governed 层，且当前 portfolio 收束已经由 README / case cards / manifest 承担，动 claim matrix 需要主人单独审核。
- Table 6 从 coverage 分母排除本轮不改：当前 `showcase:check` 已稳定通过 70% 门槛，改 denominator 会牵涉 claim matrix 与校验脚本口径，收益低于维护成本。
- 语言统一暂缓：review 正文建议中文化，优先级表又写英文统一。当前 README / blog 面向 GitHub 英文读者，case cards / snippets 面向中文面试复盘；目标投递对象确定后再统一。
