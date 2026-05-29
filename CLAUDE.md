@AGENTS.md

## Claude Code 适配说明

- 项目共享上下文以 `AGENTS.md` 为主，治理协议以 `docs/context_governance.md` 为准；本文件只放 Claude Code 适配说明。
- 大任务开始前简述将读取的项目文档与目标改动层（圣经 / 管控 / 自管理 / 归档），再进入修改。
- 读取 `docs/` 时按 `AGENTS.md` §5 的开发线路由逐步加载，避免一次性加载全量历史资料。
- `.claude/rules/` 放置路径触发提示；触发对应路径时再加载 lane 文档。
- 治理协议中的开发风格硬约束（推进感优先、反重复劳动、edit on intent）优先级高于"最小修改"等内置默认。
