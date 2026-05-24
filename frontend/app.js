const state = { data: null, auto: null };

state.modelConfig = null;
state.modelAction = null;
state.debugSnapshot = null;
state.debugError = null;
state.phase2Snapshot = null;
state.phase2GlobalSnapshot = null;
state.phase2Error = null;
state.phase2AgentId = '';
state.phase2TraceId = '';
state.phase2SourceEventId = '';

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { 'content-type': 'application/json' }, ...options });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

async function load() {
  state.data = await api('/api/state');
  state.modelConfig = state.data.modelConfig;
  ensurePhase2AgentFilter(state.data);
  try {
    state.debugSnapshot = await api('/api/debug?limit=12');
    state.debugError = null;
  } catch (error) {
    state.debugSnapshot = null;
    state.debugError = error.message;
  }
  await loadPhase2Debug();
  render();
}

async function loadPhase2Debug() {
  try {
    // Rashomon 对比需要跨 NPC 数据；即使 Heuristic 按 NPC 过滤，也保留一份全局快照。
    const globalSnapshot = await api('/api/debug.phase2?limit=80');
    state.phase2GlobalSnapshot = globalSnapshot;
    if (state.phase2AgentId) {
      const query = new URLSearchParams({ limit: '80', agentId: state.phase2AgentId });
      state.phase2Snapshot = await api(`/api/debug.phase2?${query.toString()}`);
    } else {
      state.phase2Snapshot = globalSnapshot;
    }
    state.phase2Error = null;
  } catch (error) {
    state.phase2Snapshot = null;
    state.phase2GlobalSnapshot = null;
    state.phase2Error = error.message;
  }
}

function ensurePhase2AgentFilter(data) {
  const ids = new Set((data?.agents || []).map((agent) => agent.id));
  if (state.phase2AgentId && !ids.has(state.phase2AgentId)) {
    state.phase2AgentId = '';
    state.phase2TraceId = '';
  }
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
    $('debugOverview').innerHTML = `
      <p class="muted">Debug API 暂不可用：${escapeHtml(state.debugError || '等待下一轮刷新')}</p>
      ${renderPhase2DebugCards(data)}
    `;
    bindPhase2DebugControls(data);
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
    ${renderPhase2DebugCards(data)}
  `;
  bindPhase2DebugControls(data);
}

function renderPhase2DebugCards(data) {
  if (state.phase2Error) {
    return `<section class="phase2-debug"><h3>Phase 2 Trace Views</h3><p class="muted">Phase 2 Debug API 暂不可用：${escapeHtml(state.phase2Error)}</p></section>`;
  }
  const phase2 = state.phase2Snapshot;
  if (!phase2) {
    return '<section class="phase2-debug"><h3>Phase 2 Trace Views</h3><p class="muted">正在读取 /api/debug.phase2...</p></section>';
  }
  const globalPhase2 = state.phase2GlobalSnapshot || phase2;
  return `
    <section class="phase2-debug">
      <div class="section-title">
        <div>
          <h3>Phase 2 Trace Views</h3>
          <p class="muted">读取 /api/debug.phase2，聚焦启发式、仲裁评分与 Rashomon 主观记忆。</p>
        </div>
        <span class="schema-badge">${escapeHtml(phase2.traceSchemaVersion || 'phase2.trace')}</span>
      </div>
      <div class="phase2-grid">
        ${renderHeuristicLibraryCard(data, phase2)}
        ${renderArbitrationTraceCard(phase2)}
        ${renderRashomonCard(globalPhase2)}
      </div>
    </section>`;
}

function renderHeuristicLibraryCard(data, phase2) {
  const heuristics = phase2Items(phase2.heuristics);
  const active = heuristics.filter((item) => String(item.status || 'active') === 'active');
  const dormant = heuristics.filter((item) => String(item.status || 'active') !== 'active');
  return `<section class="debug-card phase2-card heuristic-card">
    <div class="card-title-row">
      <b>Heuristic Library</b>
      <select id="phase2AgentSelect" aria-label="按 NPC 过滤启发式">
        ${renderAgentOptions(data)}
      </select>
    </div>
    <div class="metric-row"><span>active / dormant</span><strong>${formatNumber(active.length)} / ${formatNumber(dormant.length)}</strong></div>
    <div class="metric-row"><span>worldTick</span><strong>${formatValue(phase2.heuristics?.worldTick)}</strong></div>
    ${renderHeuristicGroup('活跃启发式', active, '当前筛选范围暂无活跃启发式。')}
    ${renderHeuristicGroup('休眠启发式', dormant, '当前筛选范围暂无休眠启发式。')}
  </section>`;
}

function renderAgentOptions(data) {
  const options = ['<option value="">全部 NPC</option>'];
  for (const agent of data.agents || []) {
    const selected = agent.id === state.phase2AgentId ? ' selected' : '';
    options.push(`<option value="${escapeHtml(agent.id)}"${selected}>${escapeHtml(agent.name)} · ${escapeHtml(agent.id)}</option>`);
  }
  return options.join('');
}

function renderHeuristicGroup(title, items, emptyText) {
  const rows = items.slice(0, 8).map((item) => {
    const activations = firstDefined(item.activations, item.activationCount, item.activationsCount);
    return `<div class="phase2-list-item ${String(item.status || 'active') === 'active' ? 'is-active' : 'is-dormant'}">
      <b>${escapeHtml(item.triggerPattern || item.heuristicId || 'heuristic')}</b>
      <small>${escapeHtml(item.heuristicId || '-')} · ${escapeHtml(item.agentId || '-')} · ${escapeHtml(item.sourceKind || '-')}</small>
      <div class="score-pills">
        <span>effectiveConfidence <strong>${formatScore(item.effectiveConfidence)}</strong></span>
        <span>createdTick <strong>${formatValue(item.createdTick)}</strong></span>
        <span>updatedTick <strong>${formatValue(item.updatedTick)}</strong></span>
        <span>activations <strong>${formatValue(activations, '未透出')}</strong></span>
      </div>
      ${item.narrative ? `<p>${escapeHtml(item.narrative)}</p>` : ''}
    </div>`;
  }).join('');
  return `<div class="phase2-subsection"><h4>${title} (${formatNumber(items.length)})</h4>${rows || `<p class="muted">${emptyText}</p>`}</div>`;
}

function renderArbitrationTraceCard(phase2) {
  const traces = phase2DecisionTraces(phase2);
  if (!traces.length) {
    return `<section class="debug-card phase2-card arbitration-card">
      <b>Arbitration trace</b>
      <p class="muted">暂无 motivation.decision_made trace。通过 /api/world/tick 推进世界后会出现候选工具评分。</p>
    </section>`;
  }
  const selectedTrace = selectedDecisionTrace(traces);
  const details = selectedTrace.details || {};
  const selectedToolId = String(details.selectedToolId || '');
  const candidateScores = Array.isArray(details.candidateScores) ? details.candidateScores : [];
  const missingFields = arbitrationMissingFields(candidateScores);
  return `<section class="debug-card phase2-card arbitration-card">
    <div class="card-title-row">
      <b>Arbitration trace</b>
      <select id="phase2TraceSelect" aria-label="选择 motivation.decision_made trace">
        ${traces.slice().reverse().map((trace) => {
          const key = traceKey(trace);
          const label = `${trace.agentId || details.npcId || '-'} · ${trace.summary || trace.eventType || key}`;
          return `<option value="${escapeHtml(key)}"${traceKey(selectedTrace) === key ? ' selected' : ''}>${escapeHtml(label)}</option>`;
        }).join('')}
      </select>
    </div>
    <div class="trace-meta">
      <span>NPC <strong>${escapeHtml(details.npcId || selectedTrace.agentId || '-')}</strong></span>
      <span>need <strong>${escapeHtml(details.needId || '-')}</strong></span>
      <span>winner <strong>${escapeHtml(selectedToolId || '-')}</strong></span>
      <span>reason <strong>${escapeHtml(details.decisionReason || '-')}</strong></span>
    </div>
    ${missingFields.length ? `<p class="muted">当前后端 trace 未透出 ${escapeHtml(missingFields.join(' / '))}；前端按现有 tierScore、durationScore、subjectiveMemoryBonus 做只读近似。</p>` : ''}
    ${renderCandidateScoreRows(candidateScores, selectedToolId)}
  </section>`;
}

function renderCandidateScoreRows(candidateScores, selectedToolId) {
  if (!candidateScores.length) return '<p class="muted">该 trace 暂无 candidateScores。</p>';
  const rows = candidateScores.map((candidate) => {
    const parts = arbitrationScoreParts(candidate);
    const isWinner = String(candidate.toolId || '') === selectedToolId;
    return `<div class="arbitration-row ${isWinner ? 'winner' : ''}">
      <b>${escapeHtml(candidate.toolId || '-')} ${isWinner ? '<span class="winner-badge">winner</span>' : ''}</b>
      <span title="${escapeHtml(parts.baseScoreNote)}">${formatScore(parts.baseScore)}</span>
      <span>${formatScore(parts.needBonus)}</span>
      <span title="${escapeHtml(parts.capabilityBonusNote)}">${formatScore(parts.capabilityBonus)}</span>
      <span>${formatScore(parts.memoryBonus)}</span>
      <span>${formatScore(parts.heuristicBonus)}</span>
      <span>${formatScore(parts.relationshipBonus)}</span>
      <span>${formatScore(candidate.score)}</span>
    </div>`;
  }).join('');
  return `<div class="arbitration-table">
    <div class="arbitration-row arbitration-head">
      <b>tool</b><span>baseScore</span><span>needBonus</span><span>capabilityBonus</span><span>memoryBonus</span><span>heuristicBonus</span><span>relationshipBonus</span><span>total</span>
    </div>
    ${rows}
  </div>`;
}

function renderRashomonCard(phase2) {
  const memories = phase2Items(phase2.subjectiveMemory).concat(phase2Items({ items: phase2.subjectiveMemory?.archivedItems || [] }));
  const groups = groupMemoriesBySourceEvent(memories);
  if (!groups.length) {
    return `<section class="debug-card phase2-card rashomon-card">
      <b>Rashomon 主观记忆对比</b>
      <p class="muted">暂无带 sourceEventId 的主观记忆。推进世界 tick 后会展示同事件在多 NPC 视角下的差异。</p>
    </section>`;
  }
  const selectedGroup = selectedRashomonGroup(groups);
  return `<section class="debug-card phase2-card rashomon-card">
    <div class="card-title-row">
      <b>Rashomon 主观记忆对比</b>
      <select id="phase2SourceEventSelect" aria-label="选择 sourceEventId">
        ${groups.map((group) => `<option value="${escapeHtml(group.sourceEventId)}"${group.sourceEventId === selectedGroup.sourceEventId ? ' selected' : ''}>${escapeHtml(group.sourceEventId)} · ${formatNumber(group.items.length)} NPC</option>`).join('')}
      </select>
    </div>
    <p class="muted">sourceEventId：${escapeHtml(selectedGroup.sourceEventId)}，共 ${formatNumber(selectedGroup.items.length)} 条主观记忆。</p>
    <div class="rashomon-columns">
      ${selectedGroup.items.map((memory) => `<div class="rashomon-memory">
        <b>${escapeHtml(memory.agentId || '-')}</b>
        <div class="score-pills">
          <span>perspective <strong>${escapeHtml(memory.perspective || '-')}</strong></span>
          <span>valence <strong class="${Number(memory.emotionalValence || 0) < 0 ? 'warn' : 'ok'}">${formatSigned(memory.emotionalValence)}</strong></span>
          <span>confidence <strong>${formatScore(memory.confidence)}</strong></span>
        </div>
        <p>${escapeHtml(memory.text || '')}</p>
      </div>`).join('')}
    </div>
  </section>`;
}

function bindPhase2DebugControls(data) {
  const agentSelect = $('phase2AgentSelect');
  if (agentSelect) {
    agentSelect.onchange = async (event) => {
      state.phase2AgentId = event.target.value;
      state.phase2TraceId = '';
      await loadPhase2Debug();
      render();
    };
  }
  const traceSelect = $('phase2TraceSelect');
  if (traceSelect) {
    traceSelect.onchange = (event) => {
      state.phase2TraceId = event.target.value;
      renderDebugOverview(data);
    };
  }
  const sourceEventSelect = $('phase2SourceEventSelect');
  if (sourceEventSelect) {
    sourceEventSelect.onchange = (event) => {
      state.phase2SourceEventId = event.target.value;
      renderDebugOverview(data);
    };
  }
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

function phase2Items(section) {
  if (Array.isArray(section)) return section;
  if (section && Array.isArray(section.items)) return section.items;
  return [];
}

function phase2DecisionTraces(phase2) {
  const items = Array.isArray(phase2?.recentTraceEvents) ? phase2.recentTraceEvents : [];
  return items.filter((item) => item?.eventType === 'motivation.decision_made' && item.details);
}

function selectedDecisionTrace(traces) {
  const selected = traces.find((trace) => traceKey(trace) === state.phase2TraceId);
  const fallback = selected || traces.at(-1);
  state.phase2TraceId = traceKey(fallback);
  return fallback;
}

function traceKey(trace) {
  return String(trace?.traceId || trace?.eventId || '');
}

function arbitrationMissingFields(candidateScores) {
  const required = ['baseScore', 'needBonus', 'capabilityBonus', 'memoryBonus'];
  const missing = new Set();
  for (const field of required) {
    if (!candidateScores.some((candidate) => candidate[field] !== undefined)) missing.add(field);
  }
  return [...missing];
}

function arbitrationScoreParts(candidate) {
  const tierScore = firstDefined(candidate.tierScore, 0);
  const durationScore = firstDefined(candidate.durationScore, 0);
  const hasBaseScore = candidate.baseScore !== undefined;
  const hasCapabilityBonus = candidate.capabilityBonus !== undefined;
  return {
    baseScore: hasBaseScore ? candidate.baseScore : Number(tierScore || 0) + Number(durationScore || 0),
    baseScoreNote: hasBaseScore ? '后端 baseScore' : '由 tierScore + durationScore 近似',
    needBonus: candidate.needBonus,
    capabilityBonus: hasCapabilityBonus ? candidate.capabilityBonus : candidate.tierScore,
    capabilityBonusNote: hasCapabilityBonus ? '后端 capabilityBonus' : '当前后端仅透出 tierScore',
    memoryBonus: firstDefined(candidate.memoryBonus, candidate.subjectiveMemoryBonus),
    heuristicBonus: candidate.heuristicBonus,
    relationshipBonus: candidate.relationshipBonus,
  };
}

function groupMemoriesBySourceEvent(memories) {
  const buckets = new Map();
  for (const memory of memories) {
    const sourceEventId = String(memory?.sourceEventId || '');
    if (!sourceEventId) continue;
    if (!buckets.has(sourceEventId)) buckets.set(sourceEventId, []);
    buckets.get(sourceEventId).push(memory);
  }
  return [...buckets.entries()]
    .map(([sourceEventId, items]) => ({ sourceEventId, items: items.slice().sort((a, b) => String(a.agentId || '').localeCompare(String(b.agentId || ''))) }))
    .sort((a, b) => b.items.length - a.items.length || a.sourceEventId.localeCompare(b.sourceEventId))
    .slice(0, 12);
}

function selectedRashomonGroup(groups) {
  const selected = groups.find((group) => group.sourceEventId === state.phase2SourceEventId);
  const fallback = selected || groups[0];
  state.phase2SourceEventId = fallback.sourceEventId;
  return fallback;
}

function firstDefined(...values) {
  return values.find((value) => value !== undefined && value !== null);
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

function formatValue(value, fallback = 'n/a') {
  if (value === undefined || value === null || value === '') return fallback;
  if (typeof value === 'number') return Number.isInteger(value) ? formatNumber(value) : formatScore(value);
  return escapeHtml(value);
}

function formatScore(value) {
  if (value === undefined || value === null || value === '') return 'n/a';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return escapeHtml(value);
  return Math.abs(numeric) >= 10 ? numeric.toFixed(2) : numeric.toFixed(4).replace(/0+$/, '').replace(/\.$/, '');
}

function formatSigned(value) {
  if (value === undefined || value === null || value === '') return 'n/a';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return escapeHtml(value);
  const formatted = formatScore(numeric);
  return numeric > 0 ? `+${formatted}` : formatted;
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

async function advanceWorldTick() {
  // Phase 2 主观记忆 / motivation trace / Rashomon sourceEventId 都来自 /api/world/tick，
  // /api/step 只驱动旧的 Agent 轮换调度，不会写 phase2.trace.v1。两条都跑保证 Phase 1 LLM 调用和 Phase 2 主路径同步前进。
  try {
    await api('/api/world/tick', { method: 'POST', body: JSON.stringify({ deltaSeconds: 1800, speed: 1.0 }) });
  } catch (error) {
    console.warn('world tick failed:', error.message);
  }
  try {
    await api('/api/step', { method: 'POST', body: '{}' });
  } catch (error) {
    console.warn('legacy step failed:', error.message);
  }
}

$('stepBtn').onclick = async () => { await advanceWorldTick(); await load(); };
$('autoBtn').onclick = () => { if (state.auto) { clearInterval(state.auto); state.auto = null; return; } state.auto = setInterval(async () => { await advanceWorldTick(); await load(); }, 1400); };
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
