# Loomstead Godot 客户端

这是 `Loomstead` 的首版 Godot 游戏客户端骨架。Phase 1 已于 2026-05-21 收口，当前客户端进入 Phase 2 观察者模式与 Debug 信息面板接入期。

## 当前能力

- 默认主场景：`scenes/world_main.tscn`
- Legacy 回看场景：`scenes/main.tscn`
- API 客户端：`scripts/api_client.gd`，包含 `GET /api/world/state`、`POST /api/player/action`、`POST /api/world/tick` 与 `GET /api/debug.phase2?agentId=...`
- 资产注册：`scripts/asset_registry.gd`
- 世界状态缓存：`scripts/world_sync.gd`
- 运行后读取：`GET /api/world/state`
- 玩家动作统一通过：`POST /api/player/action`
- 世界时间推进：`POST /api/world/tick`，由 `WorldClockService` 驱动，`EventBusService` 分发 NPC 移动和行动事件
- 已能加载 3 张地点背景和玩家 + 6 个首发 NPC 的 `neutral` 半身立绘
- 已能展示 `activeEvents` 中的星灯祭供应短缺事件，并通过 `inspect` / `attend_event` 展示选择结果
- 已支持地图上下文交互：靠近锚点 / 交互体 / 居民 / 事件后显示候选动作，`E`/`Space` 执行；`world_main` 中 `Tab` 打开 Phase 2 观察者面板
- 已新增 Phase 2 观察者面板：`Tab` 显隐，点击 NPC 或按 `E` talk 时同步选中，并显示 npcId / 名称 / location / anchor / motivation / subjectiveMemory / relationshipEdges / heuristics 摘要
- `world_main.tscn` 已接入三场景横向拼图、HUD 暂停/倍速和 NPC tick 移动骨架
- 可通过一条命令直接运行当前 Phase 1 完成基线窗口

## 本地启动

1. 在仓库根目录检查 Godot 环境：

   ```powershell
   npm.cmd run client:env
   ```

2. 启动后端：

   ```powershell
   npm.cmd run start
   ```

3. 直接运行游戏窗口：

   ```powershell
   npm.cmd run client:run
   ```

   该命令会先执行 Godot 资源导入，再打开默认 `world_main.tscn` 游戏窗口。

   如果需要回看旧 P0 UI 场景：

   ```powershell
   npm.cmd run client:run:legacy
   ```

   如果需要进入编辑器：

   ```powershell
   npm.cmd run client:open
   ```

   也可以手动用 Godot 4.x 打开：

   ```text
   clients/godot/project.godot
   ```

## 人工验收步骤（Phase 1 基线）

> Phase 1 已收口。以下步骤保留为回归验证清单，Phase 2 新功能验收会另行追加。

1. 在仓库根目录启动后端：

   ```powershell
   npm.cmd run start
   ```

2. 另开一个 PowerShell 运行游戏窗口：

   ```powershell
   npm.cmd run client:run
   ```

3. 在游戏窗口内人工检查：

   - 默认窗口进入 `world_main.tscn`，能看到 farm / plaza / tavern 三场景横向拼图。
   - 后端运行时，HUD 时间会随 tick 更新，Pause/Resume 和 1x/2x/4x 按钮可见。
   - 至少 3 个 NPC 会根据 `/api/world/tick` 返回事件移动或进入行动状态。
   - 如果后端未启动，HUD 应显示 tick 请求失败，场景本身仍可打开。
   - 如需验证旧 P0 UI，使用 `npm.cmd run client:run:legacy` 后再检查地点切换、地图上下文候选和事件区。

4. 点击“查看事件”后人工检查：

   - 能看到事件标题。
   - 能看到事件摘要。
   - 能看到 `choices` 列表。

5. 点击任一选择后人工检查：

   - 能看到 NPC 台词。
   - 能看到关系变化。
   - 能看到记忆写入结果。
   - 能看到夜间反思摘要。

## 下一步

- Phase 2 观察者面板已展开 `recentTraceEvents`，支持 trace filter、Prev / Next 单条 detail 和 Copy trace；下一步做真实窗口手感验收与空态 / 错误态文案微调。
- 后续再补可点击 trace 行、arbitration trace / process fidelity trace 的可视化展开。
- 等行动反馈图标和生活 UI 组件通过人工筛选后，再接入 `AssetRegistry`。

更完整的新手环境说明见：

```text
docs/game_client_environment.md
```
