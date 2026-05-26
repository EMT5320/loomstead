---
description: Resume Loomstead context
---

请使用以下接续摘要作为 Loomstead 项目入口：

!`npm.cmd run context:resume`

执行要求：

- 先按摘要判断当前分支、脏区、manual gate 和最近下一步。
- 如需更多背景，读取 `docs/assistant_continuity.md` 与 `docs/agent_context.md`。
- 只在任务进入具体开发线时读取对应源文档和代码。
- 状态更新必须区分 `code integrated`、`command checked`、`manual verified`、`manual unverified`。
