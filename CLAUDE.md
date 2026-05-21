@AGENTS.md

## Claude Code 适配说明

- 项目共享上下文以 `AGENTS.md` 为主；本文件只放 Claude Code 适配说明。
- 大任务开始前，可简述将读取哪些项目文档，再进入修改。
- 读取 `docs/` 时建议按 `AGENTS.md` 的任务线路由逐步加载，减少无关上下文。
- `.claude/rules/` 放置路径触发提示；触发对应路径时再加载 lane 文档。
