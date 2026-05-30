# Implementation Plan: Presentation Showcase（展示层）

## Overview

本实现计划严格遵循设计文档的「基于现状增量、绝不重造」立场。展示层不引入新运行时服务，新增工程实体极少：

1. 一份 Showcase_Manifest 追踪文档（`docs/showcase_manifest.md`）。
2. 一个三合一校验脚本（`scripts/check_showcase.py` + npm `showcase:check`）：口径一致性（R10）/ Figure-Table 覆盖率（R6）/ Showcase_Manifest 结构校验（R11）。
3. Observer Dock 边界行为增量（`observer_panel.gd` / `town_map.gd`）：trace 50 条上限+排序（R4.4）、Copy 反馈 ≥2s（R4.7）、loading vs placeholder（R4.3/R4.9）、同步失败指示（R4.8）、Prev/Next clamp+indicator（R4.5/R4.6）、连接失败指示（R2.4/R2.5）。
4. capture plan 判据补全（`docs/demo_capture_plan.md`）：duration 20-60s / subject 连续可见 ≥5s / caption ≥3s。

测试策略：8 条 Correctness Properties 用 Property-Based Testing（Hypothesis + pytest）覆盖纯函数逻辑，落点 `scripts/tests/test_showcase.py`。GDScript 难以脱离引擎的裁剪/排序/clamp 逻辑以 Python 参考实现做 PBT，GDScript 侧用 example 测试对齐。每条 property 测试 `max_examples >= 100`，注释格式 `# Feature: presentation-showcase, Property {number}: {property_text}`。

人工 Manual_Verification_Gate（最终 demo 视频、真实 Godot 窗口复验、GIF/截图集）是需要主人配合的人工 blocker，在本清单中以「人工验收待办」显式标注，不作为可自动完成的编码任务（见任务 11）。

验证命令（Windows 环境，统一用 `npm.cmd`）：`showcase:check`、`check`、`smoke`、`client:run:check`。

## Tasks

- [ ] 1. 准备 PBT 测试基础设施与脚本目录骨架
  - [ ] 1.1 搭建测试依赖与目录骨架
    - 在 `requirements.txt` 增加开发依赖 `hypothesis` 与 `pytest`（带注释说明仅用于展示层纯函数 PBT/example 测试）
    - 创建 `scripts/tests/` 目录与 `scripts/tests/__init__.py`，新建空的 `scripts/tests/test_showcase.py` 测试骨架（导入 `pytest` / `hypothesis`，确保可被 `python -m pytest scripts/tests` 收集）
    - 新建 `scripts/tests/showcase_refs.py` 空模块骨架，作为 GDScript 逻辑的 Python 参考实现集中落点（供 Property 1/2/8 复用）
    - 不改动现有 `check` / `smoke` 门禁脚本
    - _Requirements: 11.2_

- [ ] 2. 实现 Showcase_Manifest 文档与结构校验纯函数
  - [ ] 2.1 创建 Showcase_Manifest 文档骨架
    - 新建 `docs/showcase_manifest.md`，包含 `## Exit Criteria Status`（5 行：`demo_recording` / `blog_main` / `readme_entry` / `shareable_assets` / `figure_coverage`，列 `exit_id | title | status | verification_state | blocking_reason`）
    - 包含 `## Deliverables` 表（列 `deliverable_id | requirement | verification_state | manual_gate | notes`），覆盖各需求可交付物
    - 包含 `## Figure/Table Coverage`、`## Consistency`、`## Readiness` 区块占位（由 `showcase:check` 回填）
    - 依赖真实 LLM / 人工 reviewer / 真实 Godot 窗口的 deliverable 标 `manual_gate = yes` 且验证态置 `manual unverified`
    - _Requirements: 11.1, 11.2, 11.3_

  - [ ] 2.2 实现 manifest 解析与结构校验纯函数（`scripts/check_showcase.py`）
    - 新建 `scripts/check_showcase.py`，实现防御性逐行解析 `docs/showcase_manifest.md` 的 Exit Criteria / Deliverables 区块为结构化记录
    - 实现 `validate_manifest_structure(records)`：校验 5 条 exit criteria 齐全且 status 合法；每个 deliverable 的 `verification_state` 属于 5 值枚举 {code integrated, command checked, artifact backed, manual verified, manual unverified}；输出 `manifest.errors[]`
    - _Requirements: 11.1, 11.2_

  - [ ]* 2.3 Write property test for manifest 验证态枚举合法性
    - **Property 5: Showcase_Manifest 验证态枚举合法性** — 对任意 deliverable 行集合，结构校验通过当且仅当每个 `verification_state` 属于枚举集合，任一非法取值使校验失败并指出该行
    - 落点 `scripts/tests/test_showcase.py`，Hypothesis `max_examples >= 100`
    - **Validates: Requirements 11.2**

  - [ ] 2.4 实现 readiness 自洽与 manual gate 不变量校验
    - 实现 `compute_readiness(exit_status_list)`：当且仅当 5 条 exit criteria 全部非 pending 时返回 `ready for owner review`，否则列出 pending 项与阻塞的 Manual_Verification_Gate 项
    - 实现 `validate_manual_gate(deliverables)`：依赖真实 LLM / 人工 reviewer / 真实 Godot 窗口的 deliverable 必须 `manual_gate = yes` 且未被离线门禁标记为 satisfied/manual verified，否则报错
    - 校验 not-accepted 行必填 `blocking_reason`、readiness 与 exit status 自洽
    - _Requirements: 11.3, 11.4, 11.5, 1.7_

  - [ ]* 2.5 Write property test for readiness 自洽
    - **Property 6: Showcase_Manifest readiness 自洽** — 对任意 5 条 exit criteria 状态组合，当且仅当全部非 pending 时报告 `ready for owner review`
    - Hypothesis `max_examples >= 100`
    - **Validates: Requirements 11.4**

  - [ ]* 2.6 Write property test for manual gate 不变量
    - **Property 7: Manual gate 不变量** — 命中人工依赖标记的 deliverable，`manual_gate` 必为 yes 且验证态不得被离线门禁标记为 satisfied/manual verified；「依赖人工但 manual_gate=no」必须报错
    - Hypothesis `max_examples >= 100`
    - **Validates: Requirements 1.6, 2.6, 9.4, 11.3**

- [ ] 3. 实现 Figure/Table 覆盖率子检查（R6）
  - [ ] 3.1 实现 claim matrix 解析与覆盖率计算纯函数
    - 在 `scripts/check_showcase.py` 中实现解析 `paper/claim_evidence_matrix.md` 的「Figure / table target」列，拆分为离散 target token
    - 把 non-renderable 目标（Workflow / Limitations box / Regression guardrail note 等）排除出分母
    - 内联 Figure↔文件名映射表（`Figure 1 → system_overview`、`Figure 2 → motivational_delegation_loop`、`Figure 3 → trace_evidence_chain_figure3`、`Figure 4 → 待渲染`）
    - 实现 `compute_coverage(renderable_targets, rendered_set)`：`coverage_percent = |rendered ∩ renderable| / |renderable|`，`pass` 当且仅当 `>= 0.70`，pending 列表为未渲染 renderable target 并携带 blocking_reason
    - 扫描 `paper/generated/figures/` 与 `paper/generated/` 表格文件判定「已渲染」
    - 输出 `coverage.percent` / `coverage.rendered` / `coverage.total` / `coverage.pending[]` / `coverage.pass`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]* 3.2 Write property test for Figure/Table 覆盖率与 pending 集
    - **Property 3: Figure/Table 覆盖率与 pending 集** — 对任意可渲染 target 集合与已渲染子集，`coverage_percent = |rendered ∩ renderable| / |renderable|` 落在 [0,1]；`pass` 当且仅当 `>= 0.70`；pending 列表恰为未渲染 renderable target 且每项带 blocking_reason
    - Hypothesis `max_examples >= 100`
    - **Validates: Requirements 6.2, 6.4**

- [ ] 4. 实现口径一致性子检查（R10）
  - [ ] 4.1 实现 promoted-with-caveat 一致性扫描纯函数
    - 在 `scripts/check_showcase.py` 中实现 `scan_consistency(text, source_name)`：逐行扫描 README.md / `paper/blog_main.md` / `docs/demo_capture_plan.md` / `docs/showcase_manifest.md` 中出现 C2/C3/C4 的语句行
    - 声明 claim 状态的行必须含 promoted-with-caveat 措辞（`promoted with caveat` / `promoted-with-caveat`，大小写不敏感、连字符与空格等价）
    - 内联禁用短语列表（如 `proven` / `confirmed empirically` / `fully validated` 紧邻 C2/C3/C4）→ flag non-compliant 并记录文件+行号
    - 输出 `consistency.compliant`（bool）与 `consistency.violations[]`（文件+行+原因）
    - _Requirements: 7.4, 8.4, 10.1, 10.2, 10.3, 10.4_

  - [ ]* 4.2 Write property test for 口径一致性扫描
    - **Property 4: 口径一致性扫描** — 对任意 showcase material 文本，含 caveat 措辞的 claim 状态行判 compliant；声明状态却缺 caveat 措辞或使用高于 owner-confirmed 级别措辞的行判 non-compliant 并定位到文件与行号
    - Hypothesis `max_examples >= 100`
    - **Validates: Requirements 7.4, 8.4, 10.1, 10.2, 10.3**

- [ ] 5. 组装 check_showcase.py CLI 与回填，接线 npm showcase:check
  - [ ] 5.1 实现 CLI 主入口、JSON 报告与退出码契约
    - 在 `scripts/check_showcase.py` 实现 `main()`：沿用 `check_research_evidence.py` 的 `{ok, check, errors, warnings, ...}` 报告结构，聚合 manifest / coverage / consistency 三子检查
    - 缺失文件（claim matrix / README / blog / capture plan / manifest）记入 `errors[]`；任一子检查 errors 非空 → 退出码 1；仅 warnings → 退出码 0
    - 把 coverage pending 列表与 consistency 结论回填 `docs/showcase_manifest.md` 的 `## Figure/Table Coverage` 与 `## Consistency` 区块
    - _Requirements: 6.4, 6.5, 10.3, 10.4, 11.5, 3.5, 3.6_

  - [ ] 5.2 在 package.json 注册 showcase:check 命令
    - 在 `package.json` scripts 增加 `"showcase:check": "python scripts/check_showcase.py"`
    - 保持可独立运行，不强制纳入已稳定的 `check` 聚合门禁（遵守治理 §3.2）
    - 用 `npm.cmd run showcase:check` 验证脚本可运行并产出 JSON 报告
    - _Requirements: 6.2, 10.1, 11.1_

- [ ] 6. 检查点 — 校验层全绿
  - 运行 `npm.cmd run showcase:check` 确认三子检查通过；运行 `python -m pytest scripts/tests -q` 确认 Property 3/4/5/6/7 全过
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Observer Dock trace 裁剪/排序增量与纯函数抽取（R4.4）
  - [ ] 7.1 抽取 trace 裁剪/排序为可单测纯函数并落地 50 条上限+排序
    - 在 `clients/godot/scripts/world/town_map.gd` 新增常量 `TRACE_RECENT_LIMIT := 50`，把 `_phase2_trace_events_for_filter` / `_phase2_trace_details_for_filter` 的裁剪上限从 4 改为 50，裁剪后 reverse 为 newest→oldest
    - 保证 Prev/Next 与 details 分组共享同一裁剪+排序后的列表；列表不足 50 条时全部返回，空列表保持现有空态文本
    - 在 `scripts/tests/showcase_refs.py` 提供等价 Python 参考实现 `clip_and_sort_trace(events, category, limit=50)` 供 PBT 复用
    - _Requirements: 4.4_

  - [ ]* 7.2 Write property test for trace 裁剪与排序
    - **Property 1: Trace 裁剪与排序** — 对任意 recentTraceEvents 列表与任一过滤类别，输出长度至多 50；每项 eventType 匹配所选类别；顺序为 newest→oldest
    - 对 Python 参考实现做 PBT，Hypothesis `max_examples >= 100`
    - **Validates: Requirements 4.4**

  - [ ]* 7.3 Write GDScript example test 对齐裁剪/排序
    - 在 Godot 测试落点编写 example 测试，验证 `town_map.gd` 裁剪/排序与 Python 参考实现在固定样例上一致（含 >50 条、空列表、单类别过滤）
    - _Requirements: 4.4_

- [ ] 8. Observer Dock Prev/Next 导航、Copy 反馈与摘要增量（R4.5/R4.6/R4.7/R4.2）
  - [ ] 8.1 落地 Prev/Next clamp + position indicator + 同帧 Next 优先
    - 在 `clients/godot/scripts/ui/observer_panel.gd` 复验/补齐索引 clamp 到 `[0, max(0, total-1)]`，position indicator 显示 `当前/总数`
    - 在 `_handle_trace_hotkeys` 保证同一输入帧 Prev+Next 同时触发时应用 Next（Next 覆盖 Prev 的 index 结果，同帧只 set_input_as_handled 一次）
    - 在 `scripts/tests/showcase_refs.py` 提供等价 Python 参考实现 `apply_prev_next(total, ops)` 供 PBT 复用
    - _Requirements: 4.5, 4.6_

  - [ ]* 8.2 Write property test for Prev/Next 导航索引 clamp 与指示自洽
    - **Property 2: Prev/Next 导航索引始终 clamp 且指示自洽** — 对任意 total（≥0）与任意 Prev/Next 操作序列，最终索引落在 `[0, max(0, total-1)]`，position indicator 的 `current/total` 与索引一致（current = index+1）
    - 对 Python 参考实现做 PBT，Hypothesis `max_examples >= 100`
    - **Validates: Requirements 4.5**

  - [ ]* 8.3 Write GDScript example test 对齐同帧 Next 优先（R4.6）
    - example 测试验证同一输入帧 Prev+Next → 应用 Next 并显示对应 trace detail
    - _Requirements: 4.6_

  - [ ] 8.4 落地 Copy 反馈 ≥2 秒
    - 在 `observer_panel.gd` 将 `TRACE_COPY_FEEDBACK_SECONDS` 由 `0.85` 改为 `2.0`，保持 `已复制 ✓` 文案与 tooltip ≥2 秒（复用现有计时器路径与 `DisplayServer.clipboard_set`）
    - _Requirements: 4.7_

  - [ ]* 8.5 Write GDScript example test for Copy 反馈时长常量
    - example 测试断言 `TRACE_COPY_FEEDBACK_SECONDS >= 2.0` 且 Copy 后进入 copy-confirmation 状态
    - _Requirements: 4.7_

  - [ ] 8.6 落地 phase2 section 摘要非空逻辑并抽取纯函数
    - 复验/补齐 motivation / subjectiveMemory / relationshipEdges / heuristics 的 summarize 逻辑：非空 payload 返回非空摘要文本且不等于空态占位文案
    - 在 `scripts/tests/showcase_refs.py` 提供等价 Python 参考实现 `summarize_section(section, payload)` 供 PBT 复用
    - _Requirements: 4.2_

  - [ ]* 8.7 Write property test for phase2 摘要非空
    - **Property 8: Phase2 摘要非空** — 对任意非空 phase2 section payload，对应 summarize 返回非空摘要文本且不等于该 section 空态占位文案
    - 对 Python 参考实现做 PBT，Hypothesis `max_examples >= 100`
    - **Validates: Requirements 4.2**

- [ ] 9. Observer Dock loading/placeholder/同步失败与连接失败指示（R4.3/R4.9/R4.8/R2.4/R2.5）
  - [ ] 9.1 区分 loading 与 placeholder 状态
    - 在 `observer_panel.gd` 的 `set_selected_npc`/NPC 切换时给四个 section 设置 loading 占位文案（如 `加载中…`），区别于已收到但为空的 `SECTION_EMPTY_TEXT`（placeholder）
    - 保证 `set_phase2_debug_summary` 正确覆盖 loading→placeholder 状态切换；选中 NPC 时展示身份四字段（identifier/name/location/anchor）
    - _Requirements: 4.1, 4.3, 4.9_

  - [ ] 9.2 同步失败指示且面板保持可用
    - 复验/补齐 `show_phase2_error()`：错误态显示明确「同步失败」语义指示 + Retry，面板仍可切 Tab、可操作、不崩溃
    - _Requirements: 4.8_

  - [ ] 9.3 后端不可达连接失败指示
    - 在 `clients/godot/scripts/world/api_client.gd` / `world_sync.gd` 的 5 秒连接超时回调中触发 HUD/Observer 层可见「后端不可达」指示，窗口保持响应不崩溃
    - 标注：真实窗口表现需人工复验（见任务 11，Manual_Verification_Gate）
    - _Requirements: 2.4, 2.5_

  - [ ]* 9.4 Write GDScript example tests for 状态指示
    - example 测试覆盖：身份四字段展示（4.1）、loading vs placeholder 区分（4.3/4.9）、同步失败态面板可用（4.8）
    - _Requirements: 4.1, 4.3, 4.8, 4.9_

- [ ] 10. capture plan 判据补全（R1/R2 文档增量）
  - [ ] 10.1 在 demo_capture_plan.md 写明可机检判据语义
    - 在 `docs/demo_capture_plan.md` 显式写明：Demo_Recording duration 20–60s、目标 subject（NPC 生活 / Trace 因果链 / Rashomon）连续可见 ≥5s、C2/C3/C4 caption 连续可见 ≥3s
    - 复验 shot list（每个 subject 至少一个 shot）、后端+Godot 启动命令、推荐录制布局、tick 失败恢复指引齐全（R1.1/R1.5）
    - 复验 Godot 窗口需人工复验的行为清单（Observer Dock trace 过滤+Prev/Next、interruption layout）及各自期望可观察结果（R2.1/R2.2）
    - _Requirements: 1.1, 1.5, 2.1, 2.2_

  - [ ]* 10.2 Write example test for capture plan 判据存在性
    - 在 `scripts/tests/test_showcase.py` 编写 example 测试，断言 `docs/demo_capture_plan.md` 含 duration 20–60s / subject ≥5s / caption ≥3s 判据文本与启动命令段落
    - _Requirements: 1.1, 1.5, 2.1, 2.2_

- [ ] 11. 人工 Manual_Verification_Gate 待办（非编码任务，需主人配合验收）
  - **说明：以下为人工验收 blocker，不能由编码代理自动完成。执行编码任务时不实现本节，仅在 Showcase_Manifest 中将对应 deliverable 标为 `manual unverified` 直到主人/操作者交付。**
  - [ ] 11.1 [人工] 录制最终 demo 视频文件
    - 操作者按 `docs/demo_capture_plan.md` 录制 .mp4：duration 20–60s、目标 subject 连续可见 ≥5s、C2/C3/C4 caption 连续可见 ≥3s；录制前确认后端至少处理一个 tick 无失败
    - 完成后在 Showcase_Manifest 将 `demo_recording` 由 `manual unverified` 标为 `manual verified`
    - _Requirements: 1.2, 1.3, 1.4, 1.6_
  - [ ] 11.2 [人工] 真实 Godot 窗口复验
    - 操作者用 `npm.cmd run client:run` 启动客户端，验证 `world_main.tscn` 10 秒内加载、后端不可达指示可见且窗口稳定不崩溃、trace 导航与 interruption layout 符合期望
    - 完成后在 Showcase_Manifest 标记窗口复验 deliverable 为 `manual verified`
    - _Requirements: 2.3, 2.5, 2.6_
  - [ ] 11.3 [人工] 捕获对外 GIF / 截图集
    - 操作者按录制布局捕获 ≥1 个 GIF（3–15s，目标 subject 连续可见 ≥2s，C2/C3/C4 caption ≥2s）与 ≥1 张静态截图
    - 完成后在 Showcase_Manifest 标记 `shareable_assets` 为 `manual verified`
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [ ] 12. 最终检查点 — 离线门禁与文档收口
  - 运行 `npm.cmd run showcase:check`、`python -m pytest scripts/tests -q`、`npm.cmd run client:run:check`、`npm.cmd run check`、`npm.cmd run smoke` 确认全绿
  - 复验 `docs/showcase_manifest.md`：自动化 deliverable 标 `command checked`/`artifact backed`/`code integrated`，人工 gate 项保持 `manual unverified`，readiness 结论与 exit status 自洽
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- 标记 `*` 的子任务为可选测试任务（property 测试 / example 测试 / GDScript 测试），可为快速 MVP 跳过；核心实现任务不标 `*`。
- 每条 property 测试对应设计文档中的一条 correctness property，注释格式 `# Feature: presentation-showcase, Property {number}: {property_text}`，`max_examples >= 100`。
- GDScript 难以脱离引擎的逻辑（trace 裁剪/排序、Prev/Next clamp、摘要非空）通过 Python 参考实现做 PBT（Property 1/2/8），GDScript 侧以 example 测试对齐，避免在引擎内跑 100 次迭代的高成本。
- 任务 11 为人工 Manual_Verification_Gate，是需要主人配合的 blocker，显式标注为人工验收待办，不作为可自动完成的编码任务。
- 验证命令统一用 `npm.cmd`（Windows 环境）：`showcase:check` / `check` / `smoke` / `client:run:check`。
- 遵循治理 §3.2：`showcase:check` 作为被 `P_demo.exit` 真实 trigger 触发的新命令，默认独立运行，不给已稳定的 eval promote/drift/strict gate 加新闸门。

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1", "10.1"] },
    { "id": 1, "tasks": ["2.2", "7.1"] },
    { "id": 2, "tasks": ["2.4", "8.1"] },
    { "id": 3, "tasks": ["3.1", "8.6", "7.2"] },
    { "id": 4, "tasks": ["4.1", "8.4", "8.7"] },
    { "id": 5, "tasks": ["5.1", "9.1", "8.2"] },
    { "id": 6, "tasks": ["5.2", "9.2", "2.3"] },
    { "id": 7, "tasks": ["9.3", "2.5", "7.3"] },
    { "id": 8, "tasks": ["2.6", "8.3"] },
    { "id": 9, "tasks": ["3.2", "8.5"] },
    { "id": 10, "tasks": ["4.2", "9.4"] },
    { "id": 11, "tasks": ["10.2"] }
  ]
}
```

> 说明：任务 11.1/11.2/11.3 为人工 Manual_Verification_Gate（真实视频 / 真实 Godot 窗口 / GIF 截图），无法由编码代理并行调度执行，故不纳入上述并行调度依赖图；它们在所有相关编码任务完成后由操作者手动验收，并据此更新 Showcase_Manifest。
