/**
 * AgentBazaar — Browser Agent Runtime & Interactive UI
 * Conforms to Open Agentic Web specification
 */

const app = {
  // Application State
  state: {
    agents: [],
    selectedAgent: null,
    activeTab: 'market',
    activeCapability: '',
    searchQuery: '',
    activeScenario: 'compare-price',
    
    // Runtime execution state
    currentRun: null,
    runSteps: [],
    currentStepIndex: 0,
    isPlaying: false,
    isPaused: false,
    isTakeover: false,
    playbackTimer: null,
    
    // External site state
    externalSiteData: null,
  },

  // Initialize
  async init() {
    this.bindEvents();
    this.loadLLMSettings();
    await this.fetchAgents();
    this.renderScenarioForm();
  },

  bindEvents() {
    // Escape key closes modals
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.closeRegisterModal();
        this.closeAgentDetailModal();
      }
    });
  },

  // Tab Navigation
  switchTab(tabId) {
    this.state.activeTab = tabId;
    document.querySelectorAll('.nav-item').forEach(el => {
      el.classList.toggle('active', el.dataset.tab === tabId);
    });
    document.querySelectorAll('.view-section').forEach(el => {
      el.classList.toggle('active', el.id === `view-${tabId}`);
    });

    if (tabId === 'trust') {
      this.renderTrustBoard();
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  },

  // API Client
  async api(endpoint, options = {}) {
    try {
      const res = await fetch(endpoint, {
        headers: {
          'Content-Type': 'application/json',
          ...(options.headers || {})
        },
        ...options
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(errData.detail || `Request failed with status ${res.status}`);
      }
      return await res.json();
    } catch (err) {
      console.error('API Error:', err);
      throw err;
    }
  },

  // Marketplace & Agents
  async fetchAgents() {
    try {
      const data = await this.api('/api/agents');
      this.state.agents = data.agents || [];
      this.renderMarketplace();
      this.updateStats();
    } catch (err) {
      const cont = document.getElementById('agents-container');
      if (cont) cont.innerHTML = `<div class="empty-state">❌ 获取智能体列表失败: ${err.message}</div>`;
    }
  },

  updateStats() {
    const countEl = document.getElementById('stat-agent-count');
    const avgTrustEl = document.getElementById('stat-avg-trust');
    if (!this.state.agents.length) return;

    if (countEl) countEl.innerText = this.state.agents.length;
    const avg = Math.round(
      this.state.agents.reduce((acc, a) => acc + (a.trust_score || 0), 0) / this.state.agents.length
    );
    if (avgTrustEl) avgTrustEl.innerText = avg;
  },

  filterByCapability(cap) {
    this.state.activeCapability = cap;
    document.querySelectorAll('#capability-pills .filter-pill').forEach(btn => {
      if (!cap) {
        btn.classList.toggle('active', btn.innerText.includes('全部'));
      } else {
        btn.classList.toggle('active', btn.innerText.includes(cap));
      }
    });
    this.renderMarketplace();
  },

  onSearchInput(val) {
    this.state.searchQuery = val.trim().toLowerCase();
    this.renderMarketplace();
  },

  getAgentAvatar(agent) {
    if (agent.id.includes('tea')) return '🍵';
    if (agent.id.includes('flower')) return '🌸';
    if (agent.id.includes('book')) return '📚';
    if (agent.id.includes('repair')) return '🔧';
    if (agent.id.includes('cafe')) return '☕';
    if (agent.id.includes('stationery')) return '🖌️';
    return '🏪';
  },

  getTrustBadgeClass(score) {
    if (score >= 80) return 'trust-high';
    if (score >= 50) return 'trust-mid';
    return 'trust-low';
  },

  renderMarketplace() {
    const container = document.getElementById('agents-container');
    if (!container) return;

    let filtered = this.state.agents;

    if (this.state.activeCapability) {
      const targetCap = this.state.activeCapability.toLowerCase();
      filtered = filtered.filter(a =>
        a.capabilities.some(c => c.toLowerCase() === targetCap)
      );
    }

    if (this.state.searchQuery) {
      const q = this.state.searchQuery;
      filtered = filtered.filter(a =>
        a.name.toLowerCase().includes(q) ||
        a.description.toLowerCase().includes(q) ||
        a.id.toLowerCase().includes(q) ||
        a.capabilities.some(c => c.toLowerCase().includes(q))
      );
    }

    if (filtered.length === 0) {
      container.innerHTML = `
        <div class="empty-state" style="grid-column: 1 / -1;">
          <span class="empty-icon">🔍</span>
          <p>未找到匹配的商家智能体</p>
          <small>请尝试调整搜索词或能力筛选标签</small>
        </div>
      `;
      return;
    }

    container.innerHTML = filtered.map(agent => {
      const avatar = this.getAgentAvatar(agent);
      const trustClass = this.getTrustBadgeClass(agent.trust_score);
      const successRate = agent.calls_total > 0
        ? Math.round((agent.calls_ok / agent.calls_total) * 100)
        : 100;

      const capsHtml = agent.capabilities.map(c => `
        <span class="cap-badge">${c}</span>
      `).join('');

      return `
        <div class="agent-card" onclick="app.openAgentDetail('${agent.id}')">
          <div>
            <div class="agent-card-top">
              <div class="agent-card-title">
                <span class="agent-avatar">${avatar}</span>
                <div>
                  <h3>${agent.name}</h3>
                  <span class="mono-id">${agent.id}</span>
                </div>
              </div>
              <span class="trust-badge ${trustClass}">
                🛡️ ${agent.trust_score} 分
              </span>
            </div>
            <p class="agent-desc">${agent.description}</p>
            <div class="caps-row">${capsHtml}</div>
          </div>

          <div class="agent-card-bottom">
            <span>成功率: <strong>${successRate}%</strong> (${agent.calls_ok}/${agent.calls_total})</span>
            <span>p50: <strong>${agent.p50_latency_ms}ms</strong></span>
            <span>${agent.price_range}</span>
          </div>
        </div>
      `;
    }).join('');
  },

  // Agent Detail & Interactive Test Invoke
  async openAgentDetail(agentId) {
    try {
      const agent = await this.api(`/api/agents/${agentId}`);
      this.state.selectedAgent = agent;

      document.getElementById('modal-agent-avatar').innerText = this.getAgentAvatar(agent);
      document.getElementById('modal-agent-name').innerText = agent.name;
      document.getElementById('modal-agent-id').innerText = agent.id;
      document.getElementById('modal-agent-desc').innerText = agent.description;

      const capsRow = document.getElementById('modal-agent-caps');
      capsRow.innerHTML = agent.capabilities.map(c => `<span class="cap-badge">${c}</span>`).join('');

      const badge = document.getElementById('modal-trust-badge');
      badge.innerText = agent.trust_score;
      badge.className = `trust-badge-large ${this.getTrustBadgeClass(agent.trust_score)}`;

      // Breakdown bars
      const bk = agent.trust_breakdown || { verifiable: 30, success_rate: 38, latency: 28 };
      document.getElementById('bar-val-verifiable').innerText = `${bk.verifiable} / 30`;
      document.getElementById('bar-fill-verifiable').style.width = `${(bk.verifiable / 30) * 100}%`;

      document.getElementById('bar-val-success').innerText = `${bk.success_rate} / 40`;
      document.getElementById('bar-fill-success').style.width = `${(bk.success_rate / 40) * 100}%`;

      document.getElementById('bar-val-latency').innerText = `${bk.latency} / 30`;
      document.getElementById('bar-fill-latency').style.width = `${(bk.latency / 30) * 100}%`;

      document.getElementById('modal-stat-total').innerText = agent.calls_total;
      document.getElementById('modal-stat-ok').innerText = agent.calls_ok;
      document.getElementById('modal-stat-p50').innerText = `${agent.p50_latency_ms}ms`;
      document.getElementById('modal-stat-price').innerText = agent.price_range;

      // Populate capability select
      const select = document.getElementById('invoke-capability-select');
      select.innerHTML = agent.capabilities.map(c => `<option value="${c}">${c}</option>`).join('');
      this.onInvokeCapChange(agent.capabilities[0]);

      // Reset result area
      document.getElementById('invoke-result-container').style.display = 'none';

      document.getElementById('modal-agent-detail').classList.add('active');
    } catch (err) {
      alert(`无法加载智能体详情: ${err.message}`);
    }
  },

  closeAgentDetailModal() {
    document.getElementById('modal-agent-detail').classList.remove('active');
  },

  onInvokeCapChange(cap) {
    const input = document.getElementById('invoke-params-input');
    if (!input) return;

    if (cap === 'price.quote') {
      input.value = JSON.stringify({ item: "龙井 250g", quantity: 1 });
    } else if (cap === 'stock.check') {
      input.value = JSON.stringify({ item: "特选商品" });
    } else if (cap === 'order.status') {
      input.value = JSON.stringify({ order_id: "ORD-2026-88992" });
    } else if (cap === 'appointment.book') {
      input.value = JSON.stringify({ service: "到店体验", slot: "明日 14:00–15:30", customer_name: "体验者" });
    } else {
      input.value = JSON.stringify({});
    }
  },

  async executeTestInvoke() {
    if (!this.state.selectedAgent) return;
    const btn = document.getElementById('btn-invoke-submit');
    const cap = document.getElementById('invoke-capability-select').value;
    const paramsRaw = document.getElementById('invoke-params-input').value;

    let params = {};
    try {
      params = JSON.parse(paramsRaw);
    } catch (e) {
      alert('请输入合法的 JSON 参数');
      return;
    }

    btn.disabled = true;
    btn.innerHTML = '调用中...';

    try {
      const res = await this.api(`/api/agents/${this.state.selectedAgent.id}/invoke`, {
        method: 'POST',
        body: JSON.stringify({ capability: cap, params })
      });

      const resBox = document.getElementById('invoke-result-container');
      const jsonPre = document.getElementById('invoke-result-json');
      const badgeStatus = document.getElementById('invoke-badge-status');
      const badgeLat = document.getElementById('invoke-badge-lat');

      resBox.style.display = 'block';
      jsonPre.innerText = JSON.stringify(res, null, 2);
      badgeLat.innerText = `耗时: ${res.latency_ms}ms`;

      if (res.ok) {
        badgeStatus.className = 'badge badge-success';
        badgeStatus.innerText = '调用成功 200 OK';
      } else {
        badgeStatus.className = 'badge badge-warning';
        badgeStatus.innerText = '返回错误';
      }

      // Refresh agent list and detail stats
      await this.fetchAgents();
      const updated = await this.api(`/api/agents/${this.state.selectedAgent.id}`);
      this.state.selectedAgent = updated;
      document.getElementById('modal-trust-badge').innerText = updated.trust_score;
      document.getElementById('modal-stat-total').innerText = updated.calls_total;
      document.getElementById('modal-stat-ok').innerText = updated.calls_ok;
      document.getElementById('modal-stat-p50').innerText = `${updated.p50_latency_ms}ms`;
    } catch (err) {
      alert(`调用失败: ${err.message}`);
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<span>⚡</span> 发起调用';
    }
  },

  // Register Modal
  openRegisterModal() {
    document.getElementById('modal-register').classList.add('active');
  },

  closeRegisterModal() {
    document.getElementById('modal-register').classList.remove('active');
  },

  async handleRegisterSubmit(e) {
    e.preventDefault();
    const name = document.getElementById('reg-name').value.trim();
    const description = document.getElementById('reg-desc').value.trim();
    const price_range = document.getElementById('reg-price').value.trim();
    const hours = document.getElementById('reg-hours').value.trim();
    const endpoint = document.getElementById('reg-endpoint').value.trim();

    const checkedCaps = Array.from(
      document.querySelectorAll('input[name="reg-caps"]:checked')
    ).map(el => el.value);

    if (checkedCaps.length === 0) {
      alert('请至少勾选一项对外开放的智能体能力');
      return;
    }

    try {
      await this.api('/api/agents', {
        method: 'POST',
        body: JSON.stringify({
          name,
          description,
          capabilities: checkedCaps,
          price_range,
          hours,
          endpoint: endpoint || undefined
        })
      });

      this.closeRegisterModal();
      document.getElementById('form-register-agent').reset();
      await this.fetchAgents();
      this.switchTab('market');
      alert(`智能体 "${name}" 发布成功，已同步至 Open Agentic Web 注册表！`);
    } catch (err) {
      alert(`发布失败: ${err.message}`);
    }
  },

  // Playground & Scenario Execution
  selectScenario(sc) {
    this.state.activeScenario = sc;
    document.querySelectorAll('#scenario-selector .scenario-btn').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('onclick').includes(sc));
    });
    this.renderScenarioForm();
  },

  renderScenarioForm() {
    const formCont = document.getElementById('scenario-form-container');
    const presetsCont = document.getElementById('quick-presets');
    if (!formCont) return;

    if (this.state.activeScenario === 'compare-price') {
      formCont.innerHTML = `
        <div class="form-group">
          <label>对比商品品类/名称</label>
          <input type="text" id="play-item" class="form-input" value="龙井 250g">
        </div>
        <div class="form-group">
          <label>采购数量</label>
          <input type="number" id="play-qty" class="form-input" value="2" min="1" max="100">
        </div>
      `;
      presetsCont.innerHTML = `
        <span class="preset-chip" onclick="app.setPlaygroundPreset('龙井 250g', 2)">西湖龙井 250g (x2)</span>
        <span class="preset-chip" onclick="app.setPlaygroundPreset('玫瑰花束', 1)">香槟玫瑰花束 (x1)</span>
        <span class="preset-chip" onclick="app.setPlaygroundPreset('智能体未来', 3)">《智能体未来》 (x3)</span>
        <span class="preset-chip" onclick="app.setPlaygroundPreset('咖啡豆', 2)">精品手冲咖啡豆 (x2)</span>
      `;
    } else if (this.state.activeScenario === 'track-order') {
      formCont.innerHTML = `
        <div class="form-group">
          <label>全网订单号</label>
          <input type="text" id="play-order-id" class="form-input" value="ORD-2026-88992">
        </div>
      `;
      presetsCont.innerHTML = `
        <span class="preset-chip" onclick="app.setOrderPreset('ORD-2026-88992')">ORD-2026-88992 (极客快修)</span>
        <span class="preset-chip" onclick="app.setOrderPreset('ORD-CAFE-1082')">ORD-CAFE-1082 (转角咖啡)</span>
        <span class="preset-chip" onclick="app.setOrderPreset('ORD-TEA-5541')">ORD-TEA-5541 (云雾茶行)</span>
      `;
    } else if (this.state.activeScenario === 'book-appointment') {
      const appointmentAgents = this.state.agents.filter(a => a.capabilities.includes('appointment.book'));
      const options = appointmentAgents.map(a => `<option value="${a.id}">${a.name} (${a.hours})</option>`).join('');

      formCont.innerHTML = `
        <div class="form-group">
          <label>选择商家智能体</label>
          <select id="play-book-merchant" class="form-input">${options}</select>
        </div>
        <div class="form-group">
          <label>预约服务项目</label>
          <input type="text" id="play-book-service" class="form-input" value="精品茶席品鉴与原产地茶叶评测">
        </div>
        <div class="form-group">
          <label>预约时段</label>
          <input type="text" id="play-book-slot" class="form-input" value="明日 15:00–16:30">
        </div>
        <div class="form-row">
          <div class="form-group col-half">
            <label>预约人姓名</label>
            <input type="text" id="play-book-name" class="form-input" value="李先生">
          </div>
          <div class="form-group col-half">
            <label>联系电话</label>
            <input type="text" id="play-book-contact" class="form-input" value="13800138000">
          </div>
        </div>
      `;
      presetsCont.innerHTML = `
        <span class="preset-chip" onclick="app.setAppointmentPreset('shop-tea-001', '特级龙井现场冲泡品鉴', '明日 15:00–16:30')">云雾茶行品茶</span>
        <span class="preset-chip" onclick="app.setAppointmentPreset('service-repair-004', '屏幕总成快速更换与全面除尘', '周六 10:30–12:00')">极客快修换屏</span>
        <span class="preset-chip" onclick="app.setAppointmentPreset('shop-book-003', '周末开放网络与智能体读书沙龙席位', '周日 14:00–17:00')">书肆读书会</span>
      `;
    }
  },

  setPlaygroundPreset(item, qty) {
    const iEl = document.getElementById('play-item');
    const qEl = document.getElementById('play-qty');
    if (iEl) iEl.value = item;
    if (qEl) qEl.value = qty;
  },

  setOrderPreset(ord) {
    const oEl = document.getElementById('play-order-id');
    if (oEl) oEl.value = ord;
  },

  setAppointmentPreset(merchantId, service, slot) {
    const mEl = document.getElementById('play-book-merchant');
    const sEl = document.getElementById('play-book-service');
    const tEl = document.getElementById('play-book-slot');
    if (mEl) mEl.value = merchantId;
    if (sEl) sEl.value = service;
    if (tEl) tEl.value = slot;
  },

  getScenarioPayload() {
    if (this.state.activeScenario === 'compare-price') {
      return {
        item: document.getElementById('play-item')?.value || '龙井 250g',
        quantity: parseInt(document.getElementById('play-qty')?.value || '1', 10)
      };
    } else if (this.state.activeScenario === 'track-order') {
      return {
        order_id: document.getElementById('play-order-id')?.value || 'ORD-2026-88992'
      };
    } else if (this.state.activeScenario === 'book-appointment') {
      return {
        merchant_id: document.getElementById('play-book-merchant')?.value,
        service: document.getElementById('play-book-service')?.value,
        slot: document.getElementById('play-book-slot')?.value,
        customer_name: document.getElementById('play-book-name')?.value,
        contact: document.getElementById('play-book-contact')?.value
      };
    }
    return {};
  },

  async startRun() {
    // Clear previous timers
    if (this.state.playbackTimer) {
      clearTimeout(this.state.playbackTimer);
      this.state.playbackTimer = null;
    }

    const payload = this.getScenarioPayload();
    const btnStart = document.getElementById('btn-run-start');
    const btnPause = document.getElementById('btn-run-pause');
    const btnStep = document.getElementById('btn-run-step');
    const btnTakeover = document.getElementById('btn-run-takeover');
    const statusText = document.getElementById('runtime-status-text');
    const statusDot = document.querySelector('.status-indicator');

    btnStart.disabled = true;
    btnPause.disabled = false;
    btnStep.disabled = true;
    btnTakeover.disabled = false;

    statusDot.className = 'status-indicator running';
    statusText.innerText = '智能体网络协同运行中...';

    // Clear timeline & result
    document.getElementById('timeline-list').innerHTML = '';
    document.getElementById('result-content-container').innerHTML = `
      <div class="empty-state">
        <span class="empty-icon">⏳</span>
        <p>正在执行协作分析...</p>
      </div>
    `;
    document.getElementById('result-status-badge').style.display = 'none';

    try {
      const run = await this.api('/api/runs', {
        method: 'POST',
        body: JSON.stringify({
          scenario: this.state.activeScenario,
          input: payload
        })
      });

      this.state.currentRun = run;
      this.state.runSteps = run.steps || [];
      this.state.currentStepIndex = 0;
      this.state.isPlaying = true;
      this.state.isPaused = false;
      this.state.isTakeover = false;

      // Animate playback step by step
      this.playNextStep();
    } catch (err) {
      alert(`运行失败: ${err.message}`);
      btnStart.disabled = false;
      btnPause.disabled = true;
      statusDot.className = 'status-indicator ready';
      statusText.innerText = '运行失败';
    }
  },

  playNextStep() {
    if (!this.state.isPlaying || this.state.isPaused) return;

    if (this.state.currentStepIndex >= this.state.runSteps.length) {
      this.finishRun();
      return;
    }

    const step = this.state.runSteps[this.state.currentStepIndex];
    this.appendTimelineStep(step, this.state.currentStepIndex + 1);
    this.state.currentStepIndex++;
    this.updateMetrics();

    // Schedule next step with delay
    const delay = Math.max(350, Math.min(750, (step.latency_ms || 100) * 4));
    this.state.playbackTimer = setTimeout(() => {
      this.playNextStep();
    }, delay);
  },

  togglePause() {
    if (!this.state.isPlaying) return;

    const pauseIcon = document.getElementById('pause-icon');
    const pauseText = document.getElementById('pause-text');
    const statusDot = document.querySelector('.status-indicator');
    const statusText = document.getElementById('runtime-status-text');
    const btnStep = document.getElementById('btn-run-step');

    if (this.state.isPaused) {
      // Resume
      this.state.isPaused = false;
      pauseIcon.innerText = '⏸';
      pauseText.innerText = '暂停';
      statusDot.className = 'status-indicator running';
      statusText.innerText = '运行恢复中...';
      btnStep.disabled = true;
      this.playNextStep();
    } else {
      // Pause
      this.state.isPaused = true;
      if (this.state.playbackTimer) clearTimeout(this.state.playbackTimer);
      pauseIcon.innerText = '▶';
      pauseText.innerText = '继续';
      statusDot.className = 'status-indicator paused';
      statusText.innerText = '运行时已暂停，可单步执行或随时恢复';
      btnStep.disabled = false;
    }
  },

  stepNext() {
    if (this.state.currentStepIndex >= this.state.runSteps.length) {
      this.finishRun();
      return;
    }
    const step = this.state.runSteps[this.state.currentStepIndex];
    this.appendTimelineStep(step, this.state.currentStepIndex + 1);
    this.state.currentStepIndex++;
    this.updateMetrics();

    if (this.state.currentStepIndex >= this.state.runSteps.length) {
      this.finishRun();
    }
  },

  takeoverRun() {
    this.state.isTakeover = true;
    this.state.isPaused = true;
    if (this.state.playbackTimer) clearTimeout(this.state.playbackTimer);

    const statusDot = document.querySelector('.status-indicator');
    const statusText = document.getElementById('runtime-status-text');
    statusDot.className = 'status-indicator paused';
    statusText.innerText = '🕹️ 已接管控制权：自动流程暂停，请使用“单步执行”推进';

    document.getElementById('btn-run-step').disabled = false;
    document.getElementById('pause-text').innerText = '恢复自动';
    document.getElementById('pause-icon').innerText = '▶';
  },

  finishRun() {
    this.state.isPlaying = false;
    this.state.isPaused = false;

    document.getElementById('btn-run-start').disabled = false;
    document.getElementById('btn-run-pause').disabled = true;
    document.getElementById('btn-run-step').disabled = true;
    document.getElementById('btn-run-takeover').disabled = true;

    const statusDot = document.querySelector('.status-indicator');
    const statusText = document.getElementById('runtime-status-text');
    statusDot.className = 'status-indicator ready';
    statusText.innerText = '协作执行顺利完成！汇总成果已生成';

    document.getElementById('result-status-badge').style.display = 'inline-flex';
    this.renderResultDashboard();
    this.fetchAgents(); // Refresh stats updated during run
  },

  appendTimelineStep(step, count) {
    const list = document.getElementById('timeline-list');
    const counter = document.getElementById('timeline-counter');
    if (!list) return;

    if (counter) counter.innerText = `${count} / ${this.state.runSteps.length} 步`;

    // Remove active highlight from earlier steps
    document.querySelectorAll('.timeline-step-card').forEach(c => c.classList.remove('active-step'));

    const stepId = `step-card-${count}`;
    const card = document.createElement('div');
    card.id = stepId;
    card.className = 'timeline-step-card active-step';

    let actionLabel = step.action;
    if (step.action === 'discover_agents') actionLabel = '🔍 发现服务智能体';
    else if (step.action === 'verify_trust') actionLabel = '🛡️ 校验信任凭证';
    else if (step.action === 'invoke_quote') actionLabel = '💰 获取商品报价';
    else if (step.action === 'aggregate_quotes') actionLabel = '⚖️ 比价汇总分析';
    else if (step.action === 'query_status') actionLabel = '🚚 实时物流追踪';
    else if (step.action === 'cross_check_warehouse') actionLabel = '📦 跨仓出库核实';
    else if (step.action === 'check_slot_availability') actionLabel = '🕒 预约时段排期';
    else if (step.action === 'confirm_booking') actionLabel = '🎟️ 生成数字凭证';

    const detailMsg = typeof step.detail === 'object' && step.detail.message
      ? step.detail.message
      : (typeof step.detail === 'string' ? step.detail : JSON.stringify(step.detail));

    card.innerHTML = `
      <div class="step-card-head">
        <div style="display:flex; align-items:center; gap:0.5rem;">
          <span class="step-num-pill">#${step.step}</span>
          <span class="step-agent-tag">@${step.agent_id}</span>
        </div>
        <div class="step-meta-right">
          <span>${step.latency_ms}ms</span>
          <span class="badge ${step.status === 'success' ? 'badge-success' : 'badge-warning'}">${step.status}</span>
        </div>
      </div>
      <div style="font-weight:600; font-size:0.85rem; margin-bottom:0.25rem;">${actionLabel}</div>
      <p class="step-desc">${detailMsg}</p>
      <button class="step-payload-toggle" onclick="app.toggleStepPayload('${stepId}')">查看 Payload 报文</button>
      <div class="step-payload-pre" style="display:none;">${JSON.stringify(step.detail, null, 2)}</div>
    `;

    list.appendChild(card);
    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  },

  toggleStepPayload(stepId) {
    const card = document.getElementById(stepId);
    if (!card) return;
    const pre = card.querySelector('.step-payload-pre');
    if (!pre) return;
    pre.style.display = pre.style.display === 'none' ? 'block' : 'none';
  },

  updateMetrics() {
    const stepsCount = this.state.currentStepIndex;
    const executed = this.state.runSteps.slice(0, stepsCount);
    const agentsInvolved = new Set(executed.map(s => s.agent_id)).size;
    const totalLatency = executed.reduce((acc, s) => acc + (s.latency_ms || 0), 0);

    const elSteps = document.getElementById('metric-step-count');
    const elAgents = document.getElementById('metric-agents-involved');
    const elLatency = document.getElementById('metric-total-latency');

    if (elSteps) elSteps.innerText = stepsCount;
    if (elAgents) elAgents.innerText = agentsInvolved;
    if (elLatency) elLatency.innerText = `${totalLatency}ms`;
  },

  renderResultDashboard() {
    const container = document.getElementById('result-content-container');
    if (!container || !this.state.currentRun) return;

    const res = this.state.currentRun.result;
    if (!res) return;

    if (this.state.activeScenario === 'compare-price') {
      const best = res.best_quote;
      const quotes = res.all_quotes || [];

      const rows = quotes.map(q => `
        <tr class="${best && q.merchant_id === best.merchant_id ? 'best-row' : ''}">
          <td>
            <strong>${q.merchant}</strong>
            <br><small class="mono-meta">${q.merchant_id}</small>
          </td>
          <td>¥${q.unit_price}</td>
          <td>${q.quantity}</td>
          <td><strong>¥${q.total}</strong></td>
          <td>${best && q.merchant_id === best.merchant_id ? '<span class="badge badge-success">最优低价</span>' : '<span class="mono-meta">普通报价</span>'}</td>
        </tr>
      `).join('');

      container.innerHTML = `
        <div class="best-quote-banner">
          <span style="font-size:0.85rem; color:#065f46; font-weight:600;">🏆 最优报价商家: ${best ? best.merchant : '无'}</span>
          <div class="quote-highlight-price">¥${best ? best.total : 0}</div>
          <p style="font-size:0.85rem; color:#047857;">商品: ${res.item} (数量: ${res.quantity}) | 单价: ¥${best ? best.unit_price : 0}</p>
        </div>

        <table class="quote-table">
          <thead>
            <tr>
              <th>商家</th>
              <th>单价</th>
              <th>数量</th>
              <th>总价</th>
              <th>评估</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
        
        <p style="font-size:0.8rem; color:var(--text-muted); margin-top:1rem;">
          提示：所有报价由商家智能体实时生成，已自动校验并更新各商家信任分。
        </p>
      `;
    } else if (this.state.activeScenario === 'track-order') {
      const info = res.tracking_info;
      if (!info) {
        container.innerHTML = `<div class="empty-state">❌ ${res.error || '无物流追踪结果'}</div>`;
        return;
      }

      const timelineHtml = (info.timeline || []).map(tl => `
        <div class="mini-bar-row" style="margin-bottom:0.5rem;">
          <strong style="width:50px; font-family:var(--font-mono);">${tl.time}</strong>
          <span>${tl.event}</span>
        </div>
      `).join('');

      container.innerHTML = `
        <div class="best-quote-banner" style="background:#f0f9ff; border-color:#bae6fd;">
          <span style="font-size:0.85rem; color:#0369a1; font-weight:600;">订单追踪结果: ${info.status_text}</span>
          <div class="quote-highlight-price" style="color:#0284c7; font-size:1.6rem;">${info.current_location}</div>
          <p style="font-size:0.85rem; color:#0369a1;">单号: ${info.order_id} | 承运方: ${info.carrier}</p>
        </div>

        <div style="background:var(--bg-surface-soft); padding:1rem; border-radius:var(--radius-md); border:1px solid var(--border-color);">
          <h4 style="font-size:0.85rem; font-weight:700; margin-bottom:0.75rem;">物流流转日志</h4>
          ${timelineHtml}
        </div>
      `;
    } else if (this.state.activeScenario === 'book-appointment') {
      const appt = res.appointment;
      if (!appt) {
        container.innerHTML = `<div class="empty-state">❌ ${res.error || '预约未成功'}</div>`;
        return;
      }

      container.innerHTML = `
        <div class="appointment-pass">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong style="color:var(--primary); font-size:1.05rem;">AgentBazaar 数字服务预约凭证</strong>
            <span class="badge badge-success">已确认 CONFIRMED</span>
          </div>

          <div class="pass-code-banner">
            <span style="font-size:0.75rem; color:var(--text-muted); display:block;">智能体验据校验码</span>
            <div class="pass-code">${appt.confirmation_code}</div>
          </div>

          <div style="display:flex; flex-direction:column; gap:0.4rem; font-size:0.85rem;">
            <div><strong>服务商家:</strong> ${appt.merchant} (${appt.merchant_id})</div>
            <div><strong>预约项目:</strong> ${appt.service}</div>
            <div><strong>服务时段:</strong> ${appt.slot}</div>
            <div><strong>客户信息:</strong> ${appt.customer_name} (${appt.contact})</div>
            <div><strong>服务地址:</strong> ${appt.address}</div>
          </div>
          
          <div style="margin-top:0.85rem; padding-top:0.65rem; border-top:1px dashed #d1fae5; font-size:0.75rem; color:#047857;">
            ${appt.instructions}
          </div>
        </div>
      `;
    }
  },

  // Trust Board
  renderTrustBoard() {
    const tbody = document.getElementById('trust-leaderboard-body');
    if (!tbody) return;

    // Sort by trust score desc
    const sorted = [...this.state.agents].sort((a, b) => b.trust_score - a.trust_score);

    tbody.innerHTML = sorted.map((agent, idx) => {
      const bk = agent.trust_breakdown || { verifiable: 30, success_rate: 38, latency: 28 };
      const successRate = agent.calls_total > 0
        ? Math.round((agent.calls_ok / agent.calls_total) * 100)
        : 100;

      let grade = 'A+';
      let gradeClass = 'badge-success';
      if (agent.trust_score < 70) { grade = 'B'; gradeClass = 'badge-warning'; }
      else if (agent.trust_score < 85) { grade = 'A'; gradeClass = 'badge-success'; }

      return `
        <tr>
          <td><strong style="font-size:1.1rem; color:var(--primary);">#${idx + 1}</strong></td>
          <td>
            <div style="display:flex; align-items:center; gap:0.5rem;">
              <span style="font-size:1.25rem;">${this.getAgentAvatar(agent)}</span>
              <div>
                <strong>${agent.name}</strong>
                <br><span class="mono-id">${agent.id}</span>
              </div>
            </div>
          </td>
          <td>
            <span class="trust-badge ${this.getTrustBadgeClass(agent.trust_score)}">
              🛡️ ${agent.trust_score} 分
            </span>
          </td>
          <td>
            <div class="trust-bars-compact">
              <div class="mini-bar-row">
                <span class="mini-bar-lbl">验真 30:</span>
                <div class="mini-bar-track">
                  <div class="mini-bar-fill fill-green" style="width:${(bk.verifiable / 30) * 100}%;"></div>
                </div>
                <span>${bk.verifiable}</span>
              </div>
              <div class="mini-bar-row">
                <span class="mini-bar-lbl">成功 40:</span>
                <div class="mini-bar-track">
                  <div class="mini-bar-fill fill-blue" style="width:${(bk.success_rate / 40) * 100}%;"></div>
                </div>
                <span>${bk.success_rate}</span>
              </div>
              <div class="mini-bar-row">
                <span class="mini-bar-lbl">延迟 30:</span>
                <div class="mini-bar-track">
                  <div class="mini-bar-fill fill-amber" style="width:${(bk.latency / 30) * 100}%;"></div>
                </div>
                <span>${bk.latency}</span>
              </div>
            </div>
          </td>
          <td>
            <strong>${successRate}%</strong>
            <br><span class="mono-meta">${agent.calls_ok} / ${agent.calls_total}</span>
          </td>
          <td><strong class="mono-id">${agent.p50_latency_ms}ms</strong></td>
          <td><span class="badge ${gradeClass}">${grade} 级信誉</span></td>
        </tr>
      `;
    }).join('');
  },

  // Cross-Site Discovery
  async discoverExternalSite() {
    const urlInput = document.getElementById('cross-site-url');
    const container = document.getElementById('cross-site-results');
    if (!urlInput || !container) return;

    const url = urlInput.value.trim();
    if (!url) {
      alert('请输入目标站点 URL');
      return;
    }

    container.innerHTML = '<div class="loading-spinner">正在联网检索目标站点的 Open Agentic Web Manifest...</div>';

    try {
      const data = await this.api(`/api/discover?url=${encodeURIComponent(url)}`);
      this.state.externalSiteData = data;

      if (!data.ok) {
        container.innerHTML = `
          <div class="empty-state" style="background:#fef2f2; border:1px solid #fecaca; border-radius:var(--radius-md);">
            <span class="empty-icon">❌</span>
            <strong>抓取外部站点 Manifest 失败</strong>
            <p style="color:#b91c1c; font-size:0.85rem; margin-top:0.4rem;">${data.error}</p>
          </div>
        `;
        return;
      }

      const agentsList = (data.agents || []).map(a => `
        <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:1rem; margin-bottom:0.75rem;">
          <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div>
              <strong style="font-size:1rem;">${a.name || a.id}</strong>
              <span class="mono-id" style="margin-left:0.5rem;">${a.id}</span>
              <p style="font-size:0.85rem; color:var(--text-muted); margin-top:0.3rem;">${a.description || '无详细描述'}</p>
            </div>
            <span class="trust-badge ${this.getTrustBadgeClass(a.trust_score || 80)}">🛡️ ${a.trust_score || 80}</span>
          </div>
          <div style="margin-top:0.6rem; display:flex; flex-wrap:wrap; gap:0.35rem;">
            ${(a.capabilities || []).map(c => `<span class="cap-badge">${c}</span>`).join('')}
          </div>
          <div style="margin-top:0.75rem; display:flex; justify-content:space-between; align-items:center; border-top:1px solid #f1ede4; padding-top:0.5rem; font-size:0.8rem;">
            <span class="mono-meta">调用端点: ${a.endpoint}</span>
            <button class="btn btn-outline btn-sm" onclick="app.invokeDiscoveredAgent('${a.id}', '${(a.capabilities || ['price.quote'])[0]}')">
              跨站发起试调用
            </button>
          </div>
        </div>
      `).join('');

      container.innerHTML = `
        <div style="background:#ecfdf5; border:1px solid #a7f3d0; border-radius:var(--radius-md); padding:1.25rem; margin-bottom:1.25rem;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <h3 style="color:#065f46; font-size:1.1rem;">✅ 成功发现 Open Agentic Web 节点</h3>
            <span class="badge badge-success">网络规范: ${data.network} / v${data.version}</span>
          </div>
          <p style="font-size:0.85rem; color:#047857; margin-top:0.4rem;">
            站点: <strong>${data.name}</strong> | 已检索到 <strong>${data.agents_count}</strong> 个可调用智能体门面
          </p>
        </div>

        <div>${agentsList}</div>
      `;
    } catch (err) {
      container.innerHTML = `<div class="empty-state">❌ 发现异常: ${err.message}</div>`;
    }
  },

  invokeDiscoveredAgent(agentId, capability) {
    this.openAgentDetail(agentId);
  },

  // Settings & BYO LLM
  loadLLMSettings() {
    const base = localStorage.getItem('agentbazaar_llm_base') || '';
    const key = localStorage.getItem('agentbazaar_llm_key') || '';
    const model = localStorage.getItem('agentbazaar_llm_model') || 'gpt-4o-mini';

    const elBase = document.getElementById('setting-llm-base');
    const elKey = document.getElementById('setting-llm-key');
    const elModel = document.getElementById('setting-llm-model');
    const elMode = document.getElementById('metric-engine-mode');

    if (elBase) elBase.value = base;
    if (elKey) elKey.value = key;
    if (elModel) elModel.value = model;

    if (elMode) {
      elMode.innerText = key ? `BYO (${model})` : '本地规则引擎';
    }
  },

  saveLLMSettings() {
    const base = document.getElementById('setting-llm-base')?.value.trim() || '';
    const key = document.getElementById('setting-llm-key')?.value.trim() || '';
    const model = document.getElementById('setting-llm-model')?.value.trim() || 'gpt-4o-mini';

    localStorage.setItem('agentbazaar_llm_base', base);
    localStorage.setItem('agentbazaar_llm_key', key);
    localStorage.setItem('agentbazaar_llm_model', model);

    const tip = document.getElementById('setting-saved-tip');
    if (tip) {
      tip.style.display = 'inline';
      setTimeout(() => { tip.style.display = 'none'; }, 2500);
    }
    this.loadLLMSettings();
  },

  clearLLMSettings() {
    localStorage.removeItem('agentbazaar_llm_base');
    localStorage.removeItem('agentbazaar_llm_key');
    localStorage.removeItem('agentbazaar_llm_model');

    const elBase = document.getElementById('setting-llm-base');
    const elKey = document.getElementById('setting-llm-key');
    if (elBase) elBase.value = '';
    if (elKey) elKey.value = '';

    this.loadLLMSettings();
    alert('已清除浏览器本地的大模型 API Key');
  },

  exportManifestDownload() {
    window.location.href = '/.well-known/agent-network.json';
  },

  openExportManifest() {
    window.open('/.well-known/agent-network.json', '_blank');
  },

  async resetDemoData() {
    if (!confirm('确定要重置数据库吗？所有新增的测试记录将被清除，并恢复至 6 个初始种子智能体。')) {
      return;
    }

    try {
      await this.api('/api/reset', { method: 'POST' });
      await this.fetchAgents();
      this.switchTab('market');
      alert('演示数据库已重置为干净种子数据！');
    } catch (err) {
      alert(`重置失败: ${err.message}`);
    }
  }
};

// Auto start when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  app.init();
});
