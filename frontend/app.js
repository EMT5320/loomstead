const state = { data: null, auto: null };

state.modelConfig = null;
state.modelAction = null;
state.debugSnapshot = null;
state.debugError = null;

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { 'content-type': 'application/json' }, ...options });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

async function load() {
  state.data = await api('/api/state');
  state.modelConfig = state.data.modelConfig;
  try {
    state.debugSnapshot = await api('/api/debug?limit=12');
    state.debugError = null;
  } catch (error) {
    state.debugSnapshot = null;
    state.debugError = error.message;
  }
  render();
}

function render() {
  const data = state.data;
  if (!data) return;
  $('clock').textContent = `Day ${data.clock.day} · ${String(data.clock.hour).padStart(2, '0')}:00 · ${data.clock.phase}${data.clock.paused ? ' · Paused' : ''}`;
  renderStats(data);
  renderMap(data);
  renderAgents(data);
  renderEvents(data);
  renderDebugOverview(data);
  renderDebug(data);
  renderModelConfig(data);
}

function renderStats(data) {
  $('stats').innerHTML = Object.entries({ 和谐: data.townStats.harmony, 经济: data.townStats.economy, 健康: data.townStats.health, 好奇: data.townStats.curiosity, 出生: data.population.births, 成长: data.population.growthEvents }).map(([k, v]) => `<div class="stat"><span>${k}</span><b>${v}</b></div>`).join('');
}

function renderMap(data) {
  const map = $('map');
  map.innerHTML = '';
  for (const location of data.locations) {
    const el = document.createElement('div');
    el.className = 'location';
    el.style.left = `${location.x}%`; el.style.top = `${location.y}%`; el.style.boxShadow = `0 0 32px ${location.color}55`;
    el.innerHTML = `<b>${location.name}</b><small>${location.description}</small>`;
    map.appendChild(el);
  }
  for (const agent of data.agents.filter((a) => a.alive)) {
    const location = data.locations.find((item) => item.id === agent.locationId);
    const jitter = hash(agent.id) % 12 - 6;
    const dot = document.createElement('div');
    dot.className = 'agent-dot'; dot.style.left = `${location.x + jitter / 2}%`; dot.style.top = `${location.y + jitter}%`; dot.title = `${agent.name} · ${agent.job}`; dot.textContent = agent.name.slice(0, 1);
    map.appendChild(dot);
    const last = agent.decisionHistory.at(-1)?.parsed?.speech;
    if (last) {
      const bubble = document.createElement('div');
      bubble.className = 'bubble'; bubble.style.left = dot.style.left; bubble.style.top = dot.style.top; bubble.textContent = `${agent.name}: ${last}`;
      map.appendChild(bubble);
    }
  }
}

function renderAgents(data) {
  $('agents').innerHTML = data.agents.map((agent) => `<div class="agent"><div><b>${agent.name}</b><br><small>${agent.job} · ${agent.lifeStage} · ${data.locations.find((l) => l.id === agent.locationId)?.name}</small></div><div>心情 ${agent.status.mood}<br>精力 ${agent.status.energy}</div></div>`).join('');
}

function renderEvents(data) {
  $('events').innerHTML = data.events.slice(-18).reverse().map((event) => `<div class="event"><b>${event.type}</b><br><small>${new Date(event.createdAt).toLocaleTimeString()}</small><div>${event.payload.summary ?? event.payload.message ?? event.payload.speech ?? ''}</div></div>`).join('');
}

function renderDebug(data) {
  const latest = [...data.agents].flatMap((agent) => agent.decisionHistory.map((debug) => ({ agent: agent.name, ...debug }))).sort((a, b) => b.tick - a.tick)[0];
  $('debug').textContent = latest ? JSON.stringify(latest, null, 2) : '等待第一轮决策...';
}

function renderDebugOverview(data) {
  const debug = state.debugSnapshot;
  if (!debug) {
    $('debugOverview').innerHTML = `<p class="muted">Debug API 暂不可用：${escapeHtml(state.debugError || '等待下一轮刷新')}</p>`;
    return;
  }
  const decisionBudget = debug.phase2?.decisionBudget || {};
  const providerActuals = decisionBudget.providerActuals || {};
  const debugTurns = debug.debugTurns?.items || [];
  const fallbacks = debug.providerFallbacks?.items || [];
  const director = debug.director || {};
  const skills = debug.skills || {};
  $('debugOverview').innerHTML = `
    <div class="debug-grid">
      ${renderProviderTotals(providerActuals.totals || {}, debugTurns)}
      ${renderDirectorSkillSummary(director, skills)}
    </div>
    <details open><summary>Provider cost by feature</summary>${renderProviderByFeature(providerActuals.byFeature || {})}</details>
    <details open><summary>Recent provider calls</summary>${renderRecentProviderCalls(providerActuals.recent || [], debugTurns)}</details>
    <details><summary>Fallbacks</summary>${renderFallbacks(fallbacks)}</details>
  `;
}

function renderProviderTotals(totals, debugTurns) {
  const fallbackCount = Number(totals.fallbackCalls || 0);
  const cloudCalls = Number(totals.cloudCalls || 0);
  const latest = latestProviderCall(totals, debugTurns);
  return `<section class="debug-card">
    <b>Provider / Cost</b>
    <div class="metric-row"><span>calls</span><strong>${formatNumber(totals.calls || debugTurns.length)}</strong></div>
    <div class="metric-row"><span>cloud / rule</span><strong>${formatNumber(cloudCalls)} / ${formatNumber(totals.ruleCalls || 0)}</strong></div>
    <div class="metric-row"><span>tokens</span><strong>${formatNumber(totals.tokens || latest.tokens || 0)}</strong></div>
    <div class="metric-row"><span>cost</span><strong>${formatCost(totals.cost || latest.cost, totals.currency || latest.currency)}</strong></div>
    <div class="metric-row"><span>avg latency</span><strong>${formatLatency(totals.latencyAvgMs || latest.latencyMs)}</strong></div>
    <div class="metric-row"><span>fallback</span><strong class="${fallbackCount ? 'warn' : 'ok'}">${fallbackCount ? `${fallbackCount} 次` : '无'}</strong></div>
  </section>`;
}

function renderDirectorSkillSummary(director, skills) {
  const directorState = director.state || {};
  const queue = director.queue || {};
  const skillItems = skills.items || [];
  const activeSkills = skillItems.filter((item) => ['activated', 'active', 'available'].includes(String(item.status || ''))).length;
  const lifecycleCount = skillItems.reduce((sum, item) => sum + ((item.lifecycle || []).length), 0);
  return `<section class="debug-card">
    <b>Director / Skill</b>
    <div class="metric-row"><span>active focus</span><strong>${escapeHtml(formatActiveFocus(directorState.activeFocus))}</strong></div>
    <div class="metric-row"><span>pending beats</span><strong>${formatNumber(queue.pendingCount || 0)}</strong></div>
    <div class="metric-row"><span>activated skills</span><strong>${formatNumber((directorState.activatedEventSkills || []).length)}</strong></div>
    <div class="metric-row"><span>skill status</span><strong>${formatNumber(activeSkills)} / ${formatNumber(skillItems.length)}</strong></div>
    <div class="metric-row"><span>lifecycle events</span><strong>${formatNumber(lifecycleCount)}</strong></div>
  </section>`;
}

function renderProviderByFeature(byFeature) {
  const rows = Object.entries(byFeature);
  if (!rows.length) return '<p class="muted">暂无真实 provider usage；触发对话 Smoke 或真实 LLM smoke 后会显示。</p>';
  return `<div class="debug-table">${rows.map(([feature, totals]) => `
    <div class="debug-row">
      <b>${escapeHtml(feature)}</b>
      <span>${formatNumber(totals.calls || 0)} calls</span>
      <span>${formatNumber(totals.tokens || 0)} tokens</span>
      <span>${formatLatency(totals.latencyAvgMs)}</span>
      <span>${formatCost(totals.cost, totals.currency)}</span>
    </div>`).join('')}</div>`;
}

function renderRecentProviderCalls(recent, debugTurns) {
  const records = recent.length ? recent : debugTurns.map((turn) => ({ ...turn.debug?.providerUsageRecord, feature: turn.feature, profileName: turn.profileName, fallbackReason: turn.fallbackReason })).filter((item) => item.feature);
  if (!records.length) return '<p class="muted">暂无 provider 调用记录。</p>';
  return `<div class="debug-table">${records.slice(-8).reverse().map((item) => `
    <div class="debug-row">
      <b>${escapeHtml(item.feature || '-')}</b>
      <span>${escapeHtml(item.profileName || item.model || '-')}</span>
      <span>${formatNumber(item.tokens || 0)} tokens</span>
      <span>${formatLatency(item.latencyMs)}</span>
      <span>${formatCost(item.cost, item.currency)}</span>
      <span class="${item.fallbackReason ? 'warn' : 'ok'}">${escapeHtml(item.fallbackReason || 'no fallback')}</span>
    </div>`).join('')}</div>`;
}

function renderFallbacks(fallbacks) {
  if (!fallbacks.length) return '<p class="ok">暂无 fallback 记录。</p>';
  return `<div class="debug-table">${fallbacks.slice(-8).reverse().map((item) => `
    <div class="debug-row fallback-row">
      <b>${escapeHtml(item.feature || item.eventType || '-')}</b>
      <span>${escapeHtml(item.profileName || '-')} → ${escapeHtml(item.fallbackProfile || 'rule')}</span>
      <span class="warn">${escapeHtml(item.reason || 'unknown')}</span>
    </div>`).join('')}</div>`;
}

function renderModelConfig(data) {
  const config = state.modelConfig || data.modelConfig;
  if (!config) return;
  const validation = config.validation || { ok: true, errors: [], warnings: [] };
  const profiles = Object.entries(config.profiles || {}).map(([name, profile]) => renderProfileCard(name, profile)).join('');
  const featureProfiles = renderMapping(config.featureProfiles || {});
  const npcProfiles = renderMapping(config.npcProfiles || {});
  const statusClass = validation.ok ? 'ok' : 'warn';
  $('modelConfig').innerHTML = `
    <div class="model-row"><span>运行模式</span><b>${escapeHtml(data.providerMode || config.activeProvider || 'rule')}</b></div>
    <div class="model-row"><span>配置模式</span><b>${escapeHtml(config.activeProvider || 'rule')}</b></div>
    <div class="model-row"><span>默认 / 兜底</span><b>${escapeHtml(config.defaultProfile)} / ${escapeHtml(config.fallbackProfile)}</b></div>
    <div class="model-row"><span>本地 overlay</span><b class="${config.localConfigLoaded ? 'ok' : 'muted'}">${config.localConfigLoaded ? '已加载' : '未加载'}</b></div>
    <div class="model-row"><span>结构校验</span><b class="${statusClass}">${validation.ok ? '通过' : '异常'}</b></div>
    ${renderValidationMessages(validation)}
    <details open><summary>Profiles</summary>${profiles || '<p class="muted">暂无 profile</p>'}</details>
    <details><summary>Feature 路由</summary>${featureProfiles || '<p class="muted">暂无 feature 路由</p>'}</details>
    <details><summary>NPC 路由</summary>${npcProfiles || '<p class="muted">暂无 NPC 路由</p>'}</details>
  `;
  $('modelAction').textContent = state.modelAction || '密钥只从环境变量或本地 overlay 读取，前端不会展示真实 key。';
}

function renderProfileCard(name, profile) {
  const keyStatus = profile.provider === 'cloud' ? (profile.apiKeyConfigured ? 'key-ok' : 'key-missing') : 'key-ok';
  const modelText = profile.provider === 'cloud' ? `${profile.model || '默认模型'} · ${profile.temperature ?? '默认温度'} · ${profile.maxTokens ?? '默认上限'} tokens` : '规则兜底';
  return `<div class="profile-card">
    <b>${escapeHtml(name)}</b>
    <small>${escapeHtml(profile.provider || 'cloud')} · ${escapeHtml(modelText)}</small>
    <span class="${keyStatus}">${profile.apiKeyConfigured ? 'key 已配置' : profile.provider === 'cloud' ? 'key 未配置' : '无需 key'}</span>
  </div>`;
}

function renderMapping(mapping) {
  return Object.entries(mapping).map(([key, value]) => `<div class="model-chip"><span>${escapeHtml(key)}</span><b>${escapeHtml(value)}</b></div>`).join('');
}

function renderValidationMessages(validation) {
  const messages = [...(validation.errors || []), ...(validation.warnings || [])];
  if (!messages.length) return '';
  return `<ul class="model-warnings">${messages.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`;
}

function latestProviderCall(totals, debugTurns) {
  const latest = [...debugTurns].reverse().map((turn) => turn.debug?.providerUsageRecord || turn.debug?.usage || turn.usage || {}).find((item) => item && Object.keys(item).length);
  return {
    tokens: latest?.tokens || totals.tokens || 0,
    cost: latest?.cost || totals.cost || 0,
    currency: latest?.currency || totals.currency,
    latencyMs: latest?.latencyMs || totals.latencyAvgMs || 0,
  };
}

function formatActiveFocus(focus) {
  if (!focus) return 'none';
  if (typeof focus === 'string') return focus;
  if (typeof focus === 'object') {
    const type = focus.type || 'focus';
    const id = focus.skillId || focus.eventId || focus.beatId || '';
    return [type, id].filter(Boolean).join(' · ');
  }
  return String(focus);
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString('zh-CN');
}

function formatLatency(value) {
  const numeric = Number(value || 0);
  return numeric > 0 ? `${Math.round(numeric).toLocaleString('zh-CN')}ms` : 'n/a';
}

function formatCost(value, currency) {
  const numeric = Number(value || 0);
  if (!numeric) return '0';
  return `${numeric.toFixed(8)} ${currency || ''}`.trim();
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
}

function hash(text) { return [...text].reduce((sum, ch) => sum + ch.charCodeAt(0), 0); }

function setModelAction(message) {
  state.modelAction = message;
  if ($('modelAction')) $('modelAction').textContent = message;
}

function latestDebugSummary(data) {
  const agentDebug = data.agents ? [...data.agents].flatMap((agent) => agent.decisionHistory.map((debug) => ({ agent: agent.name, ...debug }))).sort((a, b) => b.tick - a.tick)[0] : null;
  const eventDebug = [...(data.recentEvents || data.events || [])].reverse().map((event) => event.payload?.debug).find((debug) => debug);
  const latest = agentDebug || eventDebug;
  if (!latest) return 'Smoke 已触发，但暂未找到 Debug 记录。';
  const usage = latest.usage || latest.providerUsageRecord || {};
  const latency = usage.latencyMs || latest.latency?.ms || latest.latency;
  return `Smoke 结果：${latest.providerMode} · ${latest.profileName} · ${latest.provider} · fallback=${latest.fallbackReason || '无'} · tokens=${usage.tokens ?? 'n/a'} · latency=${latency ?? 'n/a'}ms · cost=${formatCost(usage.cost, usage.currency)}`;
}

$('stepBtn').onclick = async () => { await api('/api/step', { method: 'POST', body: '{}' }); await load(); };
$('autoBtn').onclick = () => { if (state.auto) { clearInterval(state.auto); state.auto = null; return; } state.auto = setInterval(async () => { await api('/api/step', { method: 'POST', body: '{}' }); await load(); }, 1400); };
$('pauseBtn').onclick = async () => { await api('/api/developer', { method: 'POST', body: JSON.stringify({ type: state.data.clock.paused ? 'resume' : 'pause' }) }); await load(); };
$('eventBtn').onclick = async () => { await api('/api/developer', { method: 'POST', body: JSON.stringify({ type: 'injectEvent', eventType: 'town.festival', message: '开发者注入：今晚中央广场临时举办星灯节。' }) }); await load(); };
$('refreshModelBtn').onclick = async () => {
  try {
    state.modelConfig = await api('/api/model-config');
    setModelAction('已刷新公开模型配置。');
    render();
  } catch (error) {
    setModelAction(`刷新失败：${error.message}`);
  }
};
$('reloadModelBtn').onclick = async () => {
  try {
    const result = await api('/api/model-config/reload', { method: 'POST', body: '{}' });
    state.modelConfig = result.modelConfig;
    setModelAction(`已热重载配置：providerMode=${result.providerMode}`);
    await load();
  } catch (error) {
    setModelAction(`热重载失败：${error.message}`);
  }
};
$('llmSmokeBtn').onclick = async () => {
  try {
    // 只触发一次玩家对话 smoke；是否调用真实模型由后端配置和密钥状态决定。
    const result = await api('/api/player/action', { method: 'POST', body: JSON.stringify({ type: 'talk', targetId: 'mira', locationId: 'plaza', topic: 'llm_ui_smoke', message: '请用一句话介绍今晚小镇的气氛，并保持轻幻想田园口吻。' }) });
    setModelAction(latestDebugSummary(result.state));
    await load();
  } catch (error) {
    setModelAction(`Smoke 失败：${error.message}`);
  }
};

try { const es = new EventSource('/api/events'); es.onmessage = () => load(); } catch {}
load();
