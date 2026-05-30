# Requirements Document

## Introduction

本文档定义 Loomstead 展示层（Presentation Showcase）的需求。Loomstead 是 narrative-primary 的可解释多 Agent 叙事运行时与研究环境，差异化主轴为「少而深 + 可解释 + 可评估」。后端 Agent 系统与 Eval 框架已收口，现进入 `P_demo.exit` 求职展示线，目标是把已有强支撑（trace、Process Fidelity 数据、Hard Delegation vs Full 对比、cloud provider usage、Observer Dock、Web Debug）整理为对外可展示、可解释、可传播的成果。

本展示层服务于 `P_demo.exit` 的五条 exit criteria，并按三个目标维度组织：

- **可观看（Watchable）**：≤ 60 秒 demo 录屏、真实 Godot 窗口可呈现的活着世界。
- **可解释（Explainable）**：Observer Dock 因果链、Trace walkthrough、Figure/Table 渲染。
- **可传播（Shareable）**：README 30 秒入口、技术博客主文、对外 GIF / 截图集、口径一致的 caveat 标注。

本展示层严格遵守治理硬约束：后端持有权威世界状态，Godot 只做表现；LLM 输出进入可见结果前必须经过校验与 fallback；真实 LLM / 人工 reviewer / 真实 Godot 窗口 / 玩家手感属于人工验收，不属于离线门禁，这类 blocker 必须显式标注；新增 schema / 事件字段 / Debug 字段 / Godot 消费字段前先明确数据契约。

## Glossary

- **Showcase_System**: 展示层成果集合的统称，覆盖录屏、可分享素材、文档入口与渲染产物的产出与追踪流程。
- **Capture_Pipeline**: 录制 demo 与可分享素材所使用的启动命令、录制布局与操作流程（当前承载于 `docs/demo_capture_plan.md`）。
- **Capture_Plan**: `docs/demo_capture_plan.md` 中记录的录屏脚本、shot list、启动命令与人工验收清单。
- **Demo_Recording**: 一段时长不超过 60 秒的对外 demo 视频成果，内容为 NPC 自主生活 / Trace 因果链 / Rashomon 记忆中的至少一种。
- **Shareable_Asset_Set**: 至少一组对外可分享的 GIF 与静态截图集合。
- **Observer_Dock**: Godot 客户端 `world_main.tscn` 中读取 `GET /api/debug.phase2` 的研究观察面板，含 motivation / 主观记忆 / 关系边 / heuristics / trace timeline 与 trace 过滤、来源跳转、Copy trace、Prev/Next 导航。
- **Web_Debug_Console**: Web 端调试控制台，展示 provider / fallback / cost 总览、Heuristic Library、Arbitration Trace、Rashomon Memory。
- **Trace_Walkthrough**: 把一条 trace 因果链（intervention → event → 主观记忆 → 关系边 / heuristic → 后续决策 → 结果）改写为人类可读叙述的文档（当前承载于 `paper/trace_walkthroughs/`）。
- **Figure_Pipeline**: 把 Mermaid / 数据来源渲染为 Figure / Table 资产的脚本与产出流程（产出位于 `paper/generated/`）。
- **Figure_Table_Target**: `paper/claim_evidence_matrix.md` 中「Figure / table target」列声明的每一个图表目标。
- **Claim_Evidence_Matrix**: `paper/claim_evidence_matrix.md`，记录每条 claim 的支撑、证据来源与图表目标。
- **README_Portfolio_Entry**: `README.md` 顶部用于对外快速进入的入口区，含「快速看 demo」与「快速看研究」两条 30 秒入口。
- **Blog_Main**: `paper/blog_main.md` 技术博客主文。
- **Showcase_Manifest**: 追踪 `P_demo.exit` 五条 exit criteria 完成状态与人工待办的展示层清单产物。
- **Manual_Verification_Gate**: 标注真实 Godot 窗口 / 真实视频录制 / 人工 reviewer 等人工验收 blocker 的显式状态标记。
- **Authoritative_World_State**: 由 Python Agent Server 持有的权威世界状态。
- **Promoted_With_Caveat**: claim C2 / C3 / C4 当前由主人确认的 claim-level 口径，表示已 promote 但仍带 caveat。
- **Rashomon_Memory_View**: 同一客观事件在不同 NPC 主观记忆中产生差异视角的展示形态。

## Requirements

### Requirement 1: 60 秒 demo 录屏成果（可观看）

**User Story:** As a portfolio reviewer, I want a demo clip no longer than 60 seconds, so that I can grasp Loomstead's living world within one minute.

#### Acceptance Criteria

1. THE Capture_Plan SHALL provide a shot list containing at least one shot for each subject the Demo_Recording is intended to present, the exact local launch commands required to start the backend runtime and the Godot client, and a recommended recording layout that identifies which on-screen views must be visible during capture.
2. WHEN an operator records the Demo_Recording following the Capture_Plan, THE Demo_Recording SHALL have a total play duration of at least 20 seconds and no more than 60 seconds.
3. THE Demo_Recording SHALL display at least one of the following subjects — NPC autonomous life, Trace causal chain, or Rashomon_Memory_View — such that the displayed subject remains continuously visible on screen for at least 5 seconds.
4. WHERE the Demo_Recording references claim C2, C3, or C4, THE Demo_Recording SHALL display a caption stating the Promoted_With_Caveat status that remains continuously visible for at least 3 seconds while the referenced claim content is on screen.
5. IF the backend runtime reports a tick failure before recording, THEN THE Capture_Plan SHALL instruct the operator to restore the backend runtime and to confirm that it processes at least one tick without failure before capturing the Demo_Recording.
6. WHERE producing the final Demo_Recording video file requires a real Godot window, THE Showcase_Manifest SHALL mark the Demo_Recording as manual-verification-pending until an operator records the video file.
7. IF the recorded Demo_Recording exceeds 60 seconds or presents none of the three subjects named in criterion 3, THEN THE Showcase_Manifest SHALL mark the Demo_Recording as not-accepted and indicate which acceptance condition was violated.

### Requirement 2: 真实 Godot 窗口呈现复验（可观看）

**User Story:** As an operator, I want the latest Godot window behavior rechecked, so that the recorded showcase reflects the current trace navigation and interruption layout.

#### Acceptance Criteria

1. THE Capture_Plan SHALL list each Godot window behavior that requires manual window verification before recording, covering at least Observer_Dock trace navigation (trace filtering and Prev/Next navigation) and the interruption layout.
2. THE Capture_Plan SHALL state, for each listed Godot window behavior, the expected observable window result that an operator uses to record a manual pass or fail.
3. WHEN an operator launches the Godot client with the documented run command, THE Godot client SHALL load `world_main.tscn` as the default scene within 10 seconds.
4. WHILE the Godot client cannot reach the backend runtime within a 5-second connection attempt, THE Godot client SHALL display a visible load-failure indication that identifies the backend runtime as unreachable.
5. WHILE the Godot client cannot reach the backend runtime, THE Godot client SHALL keep the game window responsive to operator input and SHALL NOT crash or close.
6. WHERE the Godot window recheck depends on real Godot window experience or player feel, THE Showcase_Manifest SHALL record the Godot window recheck as a Manual_Verification_Gate item and SHALL NOT mark it as satisfied by an offline gate.

### Requirement 3: 表现层与权威世界边界（可观看）

**User Story:** As a runtime maintainer, I want the showcase presentation to stay within presentation boundaries, so that the demo never corrupts authoritative world state.

#### Acceptance Criteria

1. THE Godot client SHALL render Authoritative_World_State for presentation and SHALL submit world-changing requests only as tool actions defined by the backend runtime's tool action interface.
2. THE Godot client SHALL NOT modify Authoritative_World_State directly, and the only channel through which the Godot client can change Authoritative_World_State SHALL be tool action requests that the backend runtime validates and applies.
3. WHEN LLM output is included in any showcase material, THE backend runtime SHALL have applied parsing and rule validation to that output, SHALL have applied fallback handling to any output that failed rule validation, and SHALL have recorded the corresponding event before that output is included.
4. IF LLM output has not completed parsing, rule validation, applicable fallback handling, and event recording, THEN THE backend runtime SHALL exclude that output from every showcase material.
5. WHERE a showcase material introduces a new Debug field, schema field, or Godot consumption field, THE Showcase_System SHALL define a data contract that specifies the field name, data type, allowed value range or value set, producing component, and consuming component before that field is consumed.
6. IF a new Debug field, schema field, or Godot consumption field is consumed before its data contract is defined, THEN THE Showcase_System SHALL flag the consuming showcase material as non-compliant.

### Requirement 4: Observer Dock 因果链展示完整性（可解释）

**User Story:** As a viewer, I want the observer dock to show one NPC's motivation, memory, relationships, heuristics, and trace together, so that I can read why an NPC acted.

#### Acceptance Criteria

1. WHEN an operator selects an NPC in the Observer_Dock, THE Observer_Dock SHALL display the selected NPC identifier, name, location, and anchor.
2. WHEN Phase 2 debug data is synchronized for the selected NPC, THE Observer_Dock SHALL display non-empty motivation, subjective memory, relationship edge, and heuristic summaries.
3. WHILE the Phase 2 debug data for the selected NPC has not yet been received, THE Observer_Dock SHALL display a loading indicator in each motivation, subjective memory, relationship edge, and heuristic section that has not received data.
4. WHEN an operator changes the trace filter among decision, tool, interrupt, and memory categories, THE Observer_Dock SHALL display at most the 50 most recent trace events that match the selected category, ordered from newest to oldest.
5. WHEN an operator triggers Prev or Next navigation, THE Observer_Dock SHALL display the single trace detail at the resulting index clamped to the range from the first to the last available trace detail, together with a position indicator showing the current index and the total number of available trace details.
6. IF Prev and Next navigation are triggered within the same input frame, THEN THE Observer_Dock SHALL apply Next navigation and SHALL display the corresponding trace detail.
7. WHILE a trace detail is selected, WHEN an operator triggers the Copy trace action, THE Observer_Dock SHALL place that trace detail on the clipboard and SHALL display a copy-confirmation state that remains visible for at least 2 seconds.
8. IF the Phase 2 debug data synchronization for the selected NPC fails, THEN THE Observer_Dock SHALL display a synchronization-failure indicator and SHALL keep the Observer_Dock operational.
9. WHILE the received Phase 2 debug data contains no data for a motivation, subjective memory, relationship edge, or heuristic section, THE Observer_Dock SHALL display placeholder text in that section.

### Requirement 5: Trace 因果链可读叙述（可解释）

**User Story:** As an external reader, I want a written walkthrough of one trace causal chain, so that I can follow the earned path without reading raw JSON.

#### Acceptance Criteria

1. THE Trace_Walkthrough SHALL present, as human-readable prose, one written segment for each of the six causal-chain stages — intervention, event, subjective memory, relationship edge or heuristic, later decision, and outcome — arranged in that stated order, so that a reader can follow the entire causal chain without opening the raw JSON trace artifact.
2. THE Trace_Walkthrough SHALL cite the promoted per-scenario artifact that the described trace is derived from using a reference that uniquely identifies that artifact, including the promoted eval run it belongs to and the scenario it covers.
3. THE Trace_Walkthrough SHALL describe one counterfactual replay result that states the tool selected in the baseline replay, states the different tool selected when relationship memory is removed, and identifies removal of relationship memory as the only changed input between the two replays.
4. WHERE the Trace_Walkthrough states one or more process-fidelity numbers, THE Trace_Walkthrough SHALL cite the promoted eval run that produced those numbers using a reference that uniquely identifies that run.
5. WHERE the Trace_Walkthrough states a process-fidelity number, THE Trace_Walkthrough SHALL state that number with the value reported by the cited promoted eval run.
6. WHERE the Trace_Walkthrough states the status of claim C2, C3, or C4, THE Trace_Walkthrough SHALL use the Promoted_With_Caveat wording.

### Requirement 6: Figure 与 Table 渲染覆盖（可解释）

**User Story:** As a research reader, I want most claim figure and table targets rendered, so that the claim evidence matrix is visually backed.

#### Acceptance Criteria

1. THE Figure_Pipeline SHALL render each Figure_Table_Target whose required data source is available, which is the condition under which a Figure_Table_Target is considered completed, into a committed, non-empty asset file located under `paper/generated/`.
2. THE Showcase_System SHALL ensure that the proportion of Figure_Table_Target entries listed in the Claim_Evidence_Matrix that have a rendered asset is at least 70 percent, where a Figure_Table_Target counts as having a rendered asset only when a committed, non-empty asset file for that target exists under `paper/generated/`, and the proportion is computed as the count of covered entries divided by the total count of listed entries.
3. WHEN the Figure_Pipeline regenerates a table from a promoted eval run, THE Figure_Pipeline SHALL source the table data from the promoted manifest referenced by the Claim_Evidence_Matrix.
4. IF a Figure_Table_Target listed in the Claim_Evidence_Matrix has no rendered asset, THEN THE Showcase_Manifest SHALL record that target's identifier as pending together with the blocking reason.
5. IF the promoted manifest referenced by the Claim_Evidence_Matrix is missing or cannot be read when the Figure_Pipeline attempts to regenerate a table, THEN THE Figure_Pipeline SHALL leave any previously committed asset for that target unchanged and SHALL record that target as pending with the blocking reason in the Showcase_Manifest.

### Requirement 7: README 30 秒双入口（可传播）

**User Story:** As a first-time visitor, I want two fast entry points at the top of the README, so that I can choose to watch the demo or read the research in 30 seconds.

#### Acceptance Criteria

1. THE README_Portfolio_Entry SHALL present exactly two entry points before any other content section, where one entry point carries a visible label identifying it as the watch-the-demo entry and the other entry point carries a visible label identifying it as the read-the-research entry.
2. THE README_Portfolio_Entry SHALL link the watch-the-demo entry to the Demo_Recording or to the Capture_Plan.
3. THE README_Portfolio_Entry SHALL link the read-the-research entry to the research framing, the Process Fidelity Eval spec, or the Claim_Evidence_Matrix.
4. WHERE the README_Portfolio_Entry states the status of claim C2, C3, or C4, THE README_Portfolio_Entry SHALL use the Promoted_With_Caveat wording.
5. IF the Demo_Recording is marked manual-verification-pending and its video file does not yet exist, THEN THE README_Portfolio_Entry SHALL link the watch-the-demo entry to the Capture_Plan.
6. IF either entry point links to a target that cannot be resolved to an existing target, THEN THE Showcase_System SHALL flag the README_Portfolio_Entry as non-compliant and SHALL indicate which entry point's link could not be resolved.

### Requirement 8: 技术博客主文覆盖与视觉化（可传播）

**User Story:** As a technical reader, I want one blog-style article, so that I can read the problem, method, evidence, and caveats in one narrative.

#### Acceptance Criteria

1. THE Blog_Main SHALL be a single article that contains a problem-framing section covering the few-but-deep framing, a method section covering Motivational Delegation, an evidence section covering Process Fidelity data, and a caveats section.
2. THE Blog_Main SHALL embed or link the rendered Figure_Pipeline assets for the system overview, the Motivational Delegation loop, and the trace evidence chain figures.
3. WHERE the Blog_Main states one or more Process Fidelity numbers, THE Blog_Main SHALL cite the promoted process eval run that produced those numbers.
4. WHERE the Blog_Main states the status of claim C2, C3, or C4, THE Blog_Main SHALL use the Promoted_With_Caveat wording.
5. THE Blog_Main SHALL state that human process ratings, broader scenario coverage, and a final Godot window capture remain open.
6. IF a figure required by criterion 2 has no rendered Figure_Pipeline asset, THEN THE Showcase_Manifest SHALL record that figure as pending together with the blocking reason.

### Requirement 9: 对外可分享 GIF 与截图集（可传播）

**User Story:** As someone sharing the project, I want at least one shareable GIF and screenshot set, so that I can post the work without a full video.

#### Acceptance Criteria

1. THE Shareable_Asset_Set SHALL contain at least one GIF with a play duration of at least 3 seconds and no more than 15 seconds, and at least one static screenshot.
2. THE Shareable_Asset_Set SHALL ensure that each contained GIF and each contained static screenshot shows at least one of the following subjects — the living town, the Observer_Dock causal view, or a trace evidence detail — and that within each contained GIF the displayed subject remains continuously visible for at least 2 seconds.
3. WHERE the Shareable_Asset_Set references claim C2, C3, or C4 on a contained GIF or static screenshot, THE Shareable_Asset_Set SHALL display on that asset a caption stating the Promoted_With_Caveat status, and within a GIF SHALL keep that caption continuously visible for at least 2 seconds while the referenced claim content is on screen.
4. WHERE producing the GIF and screenshot files requires a real Godot window, THE Showcase_Manifest SHALL mark the Shareable_Asset_Set as manual-verification-pending until an operator captures the files.
5. IF the Shareable_Asset_Set lacks a GIF, lacks a static screenshot, contains an asset that shows none of the subjects named in criterion 2, or references claim C2, C3, or C4 on an asset without the required Promoted_With_Caveat caption, THEN THE Showcase_Manifest SHALL mark the Shareable_Asset_Set as not-accepted and indicate which acceptance condition was violated.

### Requirement 10: 对外口径一致性（可传播）

**User Story:** As the project owner, I want consistent claim wording across showcase materials, so that no external material overclaims beyond the approved level.

#### Acceptance Criteria

1. WHERE a showcase material — limited to the Demo_Recording, Shareable_Asset_Set, README_Portfolio_Entry, Blog_Main, and Trace_Walkthrough — includes any statement or caption that characterizes the validation or support level of claim C2, C3, or C4, THE showcase material SHALL present that status using the Promoted_With_Caveat wording defined in the Glossary.
2. THE Showcase_System SHALL treat Promoted_With_Caveat as the owner-confirmed claim level for claims C2, C3, and C4, SHALL treat any wording that presents such a claim as validated without its caveat or as more fully established than Promoted_With_Caveat as a level above the owner-confirmed level, and SHALL NOT present wording above the owner-confirmed level for these claims unless the owner has explicitly confirmed a higher level.
3. IF a showcase material asserts, for claim C2, C3, or C4, a level above the owner-confirmed Promoted_With_Caveat level, THEN THE Showcase_System SHALL flag that material as non-compliant and SHALL identify the affected claim and the offending material.
4. IF a showcase material refers to the validation or support level of claim C2, C3, or C4 without presenting the Promoted_With_Caveat wording, THEN THE Showcase_System SHALL flag that material as non-compliant and SHALL identify the affected claim and the missing Promoted_With_Caveat wording.

### Requirement 11: 展示层收口追踪（横切）

**User Story:** As the project owner, I want a single tracker for the showcase exit criteria, so that I can see which deliverables are done and which are blocked on manual work.

#### Acceptance Criteria

1. THE Showcase_Manifest SHALL record, for each of the five `P_demo.exit` exit criteria, a completion status that is exactly one of: pending, done, or not-accepted.
2. THE Showcase_Manifest SHALL record, for each deliverable tracked under a `P_demo.exit` exit criterion, a verification state that is exactly one of: code integrated, command checked, artifact backed, manual verified, or manual unverified.
3. WHERE a deliverable depends on a real LLM, a human reviewer, or a real Godot window, THE Showcase_Manifest SHALL record that deliverable as a Manual_Verification_Gate item together with the specific manual dependency that blocks it, and SHALL NOT record that deliverable as satisfied by an offline gate.
4. WHEN every one of the five `P_demo.exit` exit criteria has a completion status other than pending, THE Showcase_Manifest SHALL report the showcase line as ready for owner review.
5. WHILE at least one of the five `P_demo.exit` exit criteria has a completion status of pending, THE Showcase_Manifest SHALL report the showcase line as not ready for owner review and SHALL identify each pending exit criterion and each Manual_Verification_Gate item that blocks it.
