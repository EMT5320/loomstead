---
status: active
owner_lane: godot-client
last_verified: 2026-05-16
startup_load: on-demand
source_of_truth: true
scope: Godot client setup, launch commands, and environment checks
---

# 游戏客户端开发环境入门

> 本文面向第一次接触 Godot / 游戏客户端开发的本机环境。当前项目使用 Godot 标准版 + GDScript，不使用 C# / Mono 版。

## 已准备环境

当前机器已具备：

| 工具 | 当前用途 |
| --- | --- |
| Python 3.12 | 后端 Agent Server、检查脚本 |
| Node.js / npm | 统一启动和检查入口 |
| Git | 版本管理 |
| Godot 4.6.2 标准版 | 游戏客户端编辑器和运行环境，当前通过 winget 安装 |

Godot 当前由脚本自动查找，优先使用 `GODOT_EXE`，其次查找 winget 安装目录和固定工具目录。当前机器的 winget 安装目录类似：

```text
%LOCALAPPDATA%\Microsoft\WinGet\Packages\GodotEngine.GodotEngine_...\Godot_v4.6.2-stable_win64_console.exe
```

## 必须知道的最少概念

### 1. Godot 是游戏编辑器和运行器

Godot 类似一个轻量游戏开发环境。我们会用它来做：

- 游戏窗口。
- 地图显示。
- 玩家输入。
- NPC 显示。
- 对话框。
- 事件 UI。

### 2. `.tscn` 是场景文件

场景可以理解为游戏里的一个画面或一组节点。

当前入口场景：

```text
clients/godot/scenes/main.tscn
```

### 3. `.gd` 是 GDScript 脚本

GDScript 是 Godot 自带脚本语言，语法接近 Python。

当前关键脚本：

```text
clients/godot/scripts/main.gd
clients/godot/scripts/api_client.gd
clients/godot/scripts/world_sync.gd
```

### 4. Python 后端仍是权威世界

Godot 客户端只负责表现和交互。真正的世界状态仍在 Python 后端：

```text
GET  /api/world/state
POST /api/player/action
```

## 常用命令

### 检查本机 Godot 环境

```powershell
npm.cmd run client:env
```

该命令会用 headless 模式打开 Godot 项目，检查时生成的 Godot 用户数据会放在仓库 `.run/` 目录下，已被 Git 忽略。

### 启动后端

```powershell
npm.cmd run start
```

默认地址：

```text
http://127.0.0.1:8787
```

### 打开 Godot 项目

另开一个 PowerShell：

```powershell
npm.cmd run client:open
```

如果只想检查打开命令会使用哪个 Godot 和项目目录：

```powershell
npm.cmd run client:open:check
```

### 直接运行 Godot 游戏窗口

如果只想快速验收当前 P0 客户端，不进入编辑器：

```powershell
npm.cmd run client:run
```

该命令会先执行一次 Godot headless import，确保 `clients/godot/assets/` 下的 PNG 已生成导入元数据，然后再启动游戏窗口。

如果只想检查运行命令会使用哪个 Godot 和项目目录：

```powershell
npm.cmd run client:run:check
```

也可以手动打开：

```text
D:\Work\tools\godot\4.6.2\Godot_v4.6.2-stable_win64.exe
```

然后选择：

```text
clients/godot/project.godot
```

## 人工验收流程（本轮）

> 以下内容是人工验收步骤与检查项，需在真实窗口中逐项确认。

1. 在仓库根目录执行：

   ```powershell
   npm.cmd run start
   ```

2. 另开一个 PowerShell，执行：

   ```powershell
   npm.cmd run client:run
   ```

3. 看到游戏窗口后人工检查：

   - 地点切换与背景切换可用。
   - NPC 选择可用。
   - `talk` 提交可用。
   - 事件区可看到 `activeEvents` 中的“星灯祭供应短缺”。

4. 点击“查看事件”后人工检查：

   - 能看到事件标题。
   - 能看到事件摘要。
   - 能看到 `choices` 列表。

5. 点击任一选择后人工检查：

   - 能看到 NPC 台词。
   - 能看到关系变化。
   - 能看到记忆写入结果。
   - 能看到夜间反思摘要。

## Phase 2 观察者面板验收流程

> 2026-05-23 已验证 `npm.cmd run client:run` 可以拉起 Godot 4.6.2 真实窗口；以下 UI 行为仍以人工窗口观察为准。

1. 启动后端与游戏窗口：

   ```powershell
   npm.cmd run start
   npm.cmd run client:run
   ```

2. 在 `world_main.tscn` 中按 `Tab` 打开 Observer Panel。
3. 点击任一 NPC，确认面板显示 `npcId`、名称、location、anchor。
4. 等待 Phase 2 Debug 同步，确认 motivation / subjectiveMemory / relationshipEdges / heuristics 摘要不为空。
5. 在 `traceFilter` 中切换 all / decision / tool / interrupt / memory，确认 recentTraceEvents 文本随过滤变化。
6. 点击 `Prev` / `Next`，确认 traceDetails 的单条详情与 `x/y` 序号变化。
7. 点击 `Copy trace`，确认状态行显示“已复制 trace detail”，并能粘贴当前 trace 详情。
8. 如果后端关闭，确认面板显示加载失败状态，游戏窗口本身不崩溃。

## 当前项目阶段

当前 Godot 客户端已经从纯文本面板推进到 P0 视觉主场景：

- 3 张地点背景：农场、广场、酒馆。
- 玩家与 6 个首发 NPC 的 `neutral` 半身立绘。
- 地点移动动作：`POST /api/player/action`。
- NPC 对话动作：`POST /api/player/action`。
- 进行中事件列表、`inspect` 查看按钮、`attend_event` 选择按钮和底部 VN 结果面板。

下一步会继续补基础地图节点、角色站位、交互区域和调试信息入口。

## 常见问题

### 打开 Godot 后看不到状态

先确认后端已经启动：

```powershell
npm.cmd run start
```

浏览器访问：

```text
http://127.0.0.1:8787/api/world/state
```

如果能看到 JSON，说明后端正常。

### PowerShell 不认识 Godot 命令

当前没有把 Godot 加入系统 PATH。请使用：

```powershell
npm.cmd run client:open
```

或直接打开：

```text
D:\Work\tools\godot\4.6.2\Godot_v4.6.2-stable_win64.exe
```

### `client:open` 出现 PowerShell 乱码或引号解析错误

旧脚本里有中文字符串时，Windows PowerShell 5.1 可能按本机代码页读取文件，导致脚本解析失败。当前脚本已改成 ASCII 安全写法。遇到类似问题时先执行：

```powershell
npm.cmd run client:open:check
```

### Godot 生成 `.godot/` 目录

这是 Godot 的本地导入缓存，已经在 `.gitignore` 里忽略，不需要提交。

### Godot 生成 `.png.import` 文件

这是 Godot 对 PNG 源资产的导入元数据，需要随资产一起提交。缺少这些文件时，直接运行游戏窗口可能出现 UI 正常但背景、立绘为空的情况。

### 检查命令生成 `.run/` 目录

`npm.cmd run client:env` 会生成临时运行数据，已经在 `.gitignore` 里忽略，不需要提交。
