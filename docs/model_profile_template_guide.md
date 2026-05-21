---
status: active
owner_lane: llm-debug
last_verified: 2026-05-21
startup_load: on-demand
source_of_truth: true
scope: model profile templates, local overrides, and configuration checks
---

# 模型 Profile 配置与 LLM 验证说明

本文记录当前 LLM 接入验证的 profile 约定，覆盖玩家对话、事件反应和夜间反思三条路径。

## 配置文件职责

- `config/models.json`：本机实际调试配置，已加入 gitignore，可从公开模板复制后按需修改。
- `config/models.example.json`：已提交的公开模板，默认 `activeProvider` 为 `rule`，保证无密钥也能启动和检查。
- `config/models.local.example.json`：本地密钥覆盖模板，复制为 `config/models.local.json` 后再填真实 key。
- `config/models.local.json`：本地私密覆盖文件，应保持 gitignore，不提交。

## 推荐管理方式

当前采用“配置文件为主、Web 面板辅助”的方式管理 LLM：

1. `config/models.example.json` 负责可提交的 provider、profile、NPC 路由和 feature 路由模板。
2. `config/models.json` 负责本机实际联调配置，不提交。
3. `config/models.local.json` 只放本机密钥或临时私有覆盖，不提交。
4. `npm.cmd run model:check` 负责检查 JSON 结构、profile 引用和公开配置是否误写 `apiKey`。
5. Web 观察台的 **LLM 配置** 卡片负责展示当前运行模式、profile、key 是否已配置、结构校验结果。
6. 修改配置文件后，可在 Web 面板点“重载配置”，触发 `POST /api/model-config/reload`，避免每次小改都重启服务器。
7. “对话 Smoke” 会触发一次玩家对话，真实调用或规则 fallback 由当前 provider 和密钥状态决定。

这种分层能同时满足后端 agent 联调、真实模型质量对比和密钥隔离。

## Profile 选择路径

运行时通过 `ModelConfigStore.resolve_profile(agent_id, feature)` 解析 profile，当前顺序是：

1. `npcProfiles[agent_id]`
2. `featureProfiles[feature]`
3. `defaultProfile`
4. `fallbackProfile`

本轮重点 feature 映射：

| 功能 | feature 名 | 默认 profile | 运行入口 |
| --- | --- | --- | --- |
| 玩家对话 | `dialogue` | `dialogue_story` | `AgentRuntime._handle_player_talk()` |
| 事件反应 | `event_reaction` | `event_reaction_fast` | `AgentRuntime._write_starlight_dialogue()` |
| 夜间反思 | `night_reflection` | `night_reflection_deep` | `AgentRuntime._write_starlight_reflections()` |

注意：玩家对话会传入目标 NPC 的 `agent_id`，因此 `npcProfiles` 中的 NPC 专属 profile 会优先于 `featureProfiles.dialogue`。事件反应和夜间反思当前按功能 profile 选择。

## 密钥配置

推荐二选一：

### 方式 A：环境变量

PowerShell 示例：

```powershell
$env:DEEPSEEK_API_KEY = "你的真实 key"
# 或使用项目统一兜底变量：
$env:AGENT_TOWN_API_KEY = "你的真实 key"
# 如需临时覆盖兼容 OpenAI-compatible 地址或模型，可按需设置：
$env:AGENT_TOWN_BASE_URL = "https://api.deepseek.com"
$env:AGENT_TOWN_MODEL = "请按官方文档复核后的模型名"
```

当前环境变量前缀仍保留 `AGENT_TOWN_*`，用于兼容既有脚本、本机配置和 smoke 流程。Phase 2 骨架重构时可迁移到 `LOOMSTEAD_*`，并保留兼容 shim。

### 方式 B：本地覆盖文件

```powershell
Copy-Item config/models.local.example.json config/models.local.json
# 然后只在 config/models.local.json 填真实 key
```

提交前检查：

```powershell
git check-ignore -v config/models.local.json
git diff -- config/models.json config/models.example.json config/models.local.example.json docs/model_profile_template_guide.md
```

## 模型名与参数复核

`model`、`baseUrl`、`maxTokens`、`temperature`、超时与 JSON 输出能力都属于供应商侧会变动的信息。每次真实接入前，应按当前官方文档复核，并把变更保留在本地配置或经过审查后再改公开模板。

当前模板给 `dialogue`、`event_reaction`、`night_reflection` 相关 profile 增加了：

- `responseFormat: {"type": "json_object"}`：用于 OpenAI-compatible JSON 输出模式。
- `pricing`：用于 Debug usage 里的成本估算字段；字段单位为每 100 万 tokens。

`pricing.source` 记录价格来源快照。供应商价格可能调整，真实成本以供应商账单为准。

## Debug 验收字段

三条 LLM 验证路径的 debug 记录需要包含：

- `providerMode`
- `profileName`
- `apiKeyConfigured`
- `messages`
- `rawText`
- `parsed`
- `usage`
- `latency`
- `fallbackReason`

`messages` 和 `rawText` 用于本地调试时复现提示词与模型输出，禁止写入 API key、Authorization header 或其它密钥材料。

`usage` 至少需要覆盖：

- `tokens`
- `promptTokens`
- `completionTokens`
- `cacheHitPromptTokens`
- `cacheMissPromptTokens`
- `latencyMs`
- `cost`
- `costInput`
- `costOutput`
- `costEstimated`
- `currency`
- `model`
- `profileName`

## 无 key 与有 key 的验收

无真实 key 时：

```powershell
npm.cmd run model:check
npm.cmd run check
npm.cmd run smoke
```

期望：规则 fallback 可用，三个 feature 的 debug 结构仍生成。

有真实 key 时：

1. 设置环境变量、`config/models.local.json` 或本机 gitignored 的 `config/models.json`。
2. 运行 `npm.cmd run smoke`，脚本会尝试用 `provider_mode="cloud"` 触发 `dialogue`、`event_reaction` 和 `night_reflection`。
3. 普通 smoke 如果遇到网络、鉴权或供应商异常，会打印 `[llm-smoke] fallback` 并保留规则 fallback 结果，避免离线环境阻塞基础检查。
4. 需要强制真实云端 smoke 成功时，使用：

   ```powershell
   $env:AGENT_TOWN_REQUIRE_REAL_LLM_SMOKE = "1"
   npm.cmd run smoke
   Remove-Item Env:\AGENT_TOWN_REQUIRE_REAL_LLM_SMOKE
   ```

5. 观察 `[llm-smoke]` 摘要：只展示 profile、model、tokens、latency、cost、fallbackReason、rawTextLength 和 messageCount。
6. 启动服务并打开 Web 观察台。
7. 在 **LLM 配置** 卡片点“重载配置”，确认 `localConfigLoaded` 和 `apiKeyConfigured`。
8. 点“对话 Smoke”或执行一次事件结算，记录 debug 中的 `providerMode`、`profileName`、`apiKeyConfigured`、`usage`、`latency` 与 `fallbackReason`。
9. 输出证据时只展示 `apiKeyConfigured: true`，不展示真实 key。
