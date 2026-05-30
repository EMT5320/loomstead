---
status: active
owner_lane: portfolio-showcase
last_verified: 2026-05-30
startup_load: on-demand
source_of_truth: true
scope: 展示层收口追踪（P_demo.exit 五条 exit criteria 状态与人工待办）
---

# Loomstead Showcase Manifest

> 自管理层文档，软上限 250 行。只记当前事实、当前缺口、人工待办；历史变化由 git history 承载。
> 本文是 `P_demo.exit` 求职展示线的收口追踪入口，同时被主人阅读与 `showcase:check` 结构校验（脚本已实现）。

## 字段约定

- `status`（exit criteria）枚举：`pending` / `done` / `not-accepted`。`not-accepted` 行必填 `blocking_reason`。
- `verification_state` 枚举（R11.2，5 值，复用 `AGENTS.md` §6 口径）：`code integrated` / `command checked` / `artifact backed` / `manual verified` / `manual unverified`。
- `manual_gate` 枚举：`yes`（依赖真实 LLM / 人工 reviewer / 真实 Godot 窗口，不得由离线门禁标记为已满足）/ `no`。
- 自动化 deliverable 以 `verification_state` 记录当前证据等级；真实视频 / GIF / 截图 / 真实窗口复验仍保留 `manual unverified`。

## Exit Criteria Status

| exit_id | title | status | verification_state | blocking_reason |
| --- | --- | --- | --- | --- |
| demo_recording | ≤60 秒 demo 录屏（NPC 自主生活 / Trace 因果链 / Rashomon 记忆任选其一） | pending | manual unverified | 最终 demo 视频依赖真实 Godot 窗口人工录制；录屏脚本已落 `docs/demo_capture_plan.md` |
| blog_main | 技术博客主文（少而深 framing + Motivational Delegation + Process Fidelity 数据） | done | command checked | 初稿已落 `paper/blog_main.md`；`showcase:check` 覆盖 C2/C3/C4 口径一致性，主人仍可继续做文风润色 |
| readme_entry | README 顶部「快速看 demo / 快速看研究」两条 30 秒入口 | done | command checked | `README.md` 顶部已收敛为 watch / research 两条入口；证据基线降为补充说明 |
| shareable_assets | ≥1 组对外可分享的 GIF / 截图集 | pending | manual unverified | GIF / 截图依赖真实 Godot 窗口人工捕获 |
| figure_coverage | claim_evidence_matrix 的 Figure/Table target ≥70% 已渲染 | done | command checked | 已渲染 Figure 1/2/3/4 + 多 Table（`paper/generated/`）；`showcase:check` 回填覆盖率 ≥70% |

## Deliverables

| deliverable_id | requirement | verification_state | manual_gate | notes |
| --- | --- | --- | --- | --- |
| capture_plan | R1 | command checked | no | 录屏脚本 / shot list / 启动命令 / caption stack 已落 `docs/demo_capture_plan.md`；example 测试覆盖 duration 20–60s / subject ≥5s / caption ≥3s 判据 |
| readme_dual_entry | R7 | command checked | no | `README.md` 顶部已收敛为 Watch / Research 两条入口；证据基线作为补充说明 |
| blog_main_article | R8 | command checked | no | `paper/blog_main.md` 初稿已落地（framing + Motivational Delegation + Process Fidelity）；口径一致性由 `showcase:check` 扫描 |
| trace_walkthrough | R5 | command checked | no | `paper/trace_walkthroughs/figure3_trace_walkthrough_pf_branna_seed01.md` 已落地（六阶段 + 反事实 + promoted with caveat artifact 引用），并纳入 C2/C3/C4 promoted with caveat 口径扫描 |
| figure_table_render | R6 | command checked | no | `paper/generated/` 已渲染 Figure 1/2/3/4 + 多 Table；覆盖率由 `showcase:check` 回填 |
| showcase_check_script | R6, R10, R11 | command checked | no | 三合一校验脚本 `scripts/check_showcase.py` + npm `showcase:check` 已实现；输出 JSON 报告并回填 coverage / consistency / readiness |
| showcase_mode_v1 | R1, R2, R4 | code integrated | no | Godot 默认可见 `ShowcasePanel` + 后端只读 `/api/showcase/starlight` 聚合包已落地；覆盖 `星灯祭供应短缺` 的 Goal / Director Beat / Event Skill / NPC Decision / Trace Evidence 摘要链；真实窗口观感仍见 `showcase_mode_window_recheck` |
| observer_dock_increment | R4 | code integrated | no | Observer Dock trace 50 条/排序、Copy ≥2s、loading vs placeholder、同步失败指示、Prev/Next clamp+indicator 已落地；真实窗口复验另见 `godot_window_recheck` |
| backend_unreachable_indicator | R2 | code integrated | no | 后端 5 秒连接超时「后端不可达」可见指示已落地；真实窗口表现另需人工复验（见 `godot_window_recheck`） |
| capture_plan_criteria | R1, R2 | command checked | no | capture plan 已写明 duration 20–60s / subject 连续可见 ≥5s / caption ≥3s 判据语义，并由 example 测试守护 |
| final_demo_video | R1 | manual unverified | yes | 最终 demo `.mp4` 依赖真实 Godot 窗口人工录制（任务 11.1）；duration 20–60s、subject 连续可见 ≥5s、C2/C3/C4 caption ≥3s |
| showcase_mode_window_recheck | R2 | manual unverified | yes | 真实 Godot 窗口复验待 Computer Use：启动 10 秒内需读到 Goal / Director Beat / Event Skill / NPC Decision / Trace Evidence；`F1` 切换 ShowcasePanel，`Tab` 打开 Observer Dock，`Deep dive` 定位 NPC / trace |
| godot_window_recheck | R2 | manual unverified | yes | 真实 Godot 窗口复验依赖真实窗口 / 玩家手感（任务 11.2）；含 `world_main.tscn` 加载、trace 导航、interruption layout、后端不可达指示 |
| shareable_gif_screenshots | R9 | manual unverified | yes | 对外 GIF（3–15s，subject ≥2s）+ ≥1 张静态截图依赖真实 Godot 窗口人工捕获（任务 11.3） |

## Figure/Table Coverage

> 由 `showcase:check`（任务 5.1）回填——如实记录覆盖率与待渲染缺口；不放宽阈值、不虚报（已知缺口口径）。

- `coverage_percent`: 0.70
- `rendered_count`: 7
- `renderable_total`: 10
- `pass`: true（门槛 `>= 0.70`）
- `pending[]`:
  - `Table 1`: Table 1: no committed table under paper/generated/ (eval_tables.tex, eval_summary_tables.md, ablation_table.csv)
  - `Table 3`: Table 3: no committed table under paper/generated/ (eval_tables.tex, eval_summary_tables.md, ablation_table.csv)
  - `Table 6`: Table 6: no committed table under paper/generated/ (eval_tables.tex, eval_summary_tables.md, ablation_table.csv)

## Consistency

> 由 `showcase:check`（任务 5.1）回填 C2/C3/C4 口径一致性最近一次扫描结论。

- `compliant`: true
- `violations[]`: 无

口径基线：C2 / C3 / C4 为主人确认的 `promoted with caveat`；所有 showcase material 提及其状态时必须使用该措辞。

## Readiness

> 由 `showcase:check`（任务 5.1）回填，规则见 R11.4 / R11.5。

- `readiness`: not ready for owner review
- `pending_exit_ids`: demo_recording, shareable_assets
- `blocking_manual_gates`: final_demo_video, showcase_mode_window_recheck, godot_window_recheck, shareable_gif_screenshots

当且仅当 5 条 exit criteria 全部非 pending 时报 ready for owner review；当前仍有 pending exit criteria（demo_recording, shareable_assets），故 not ready。
