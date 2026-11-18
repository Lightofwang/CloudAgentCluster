/**
 * TraceLens Main Application Orchestrator
 */
document.addEventListener("DOMContentLoaded", () => {
  // App State
  let currentTraceId = null;
  let tracesList = [];
  let currentTraceMeta = null;
  let currentAnomalies = [];
  let currentStats = null;
  let currentTimeline = null;
  let timelineCanvas = null;
  let anomalyFilter = "all";

  // Elements
  const traceSelect = document.getElementById("traceSelect");
  const anomalyNavBadge = document.getElementById("anomalyNavBadge");

  // Init Timeline Canvas
  const canvasEl = document.getElementById("timelineCanvas");
  const tooltipEl = document.getElementById("timelineTooltip");
  if (canvasEl) {
    timelineCanvas = new TimelineCanvas(canvasEl, tooltipEl);
    timelineCanvas.onRangeChange = (startNs, endNs) => {
      updateRangeDisplay(startNs, endNs);
    };
  }

  // --- Router ---
  function handleRoute() {
    const hash = window.location.hash.replace("#", "") || "overview";
    const validViews = ["overview", "timeline", "stats", "anomalies", "reference"];
    const viewName = validViews.includes(hash) ? hash : "overview";

    // Update active nav item
    document.querySelectorAll(".nav-item").forEach(item => {
      if (item.getAttribute("data-view") === viewName) {
        item.classList.add("active");
      } else {
        item.classList.remove("active");
      }
    });

    // Update active section
    document.querySelectorAll(".view-section").forEach(sec => {
      if (sec.id === `view-${viewName}`) {
        sec.classList.add("active");
      } else {
        sec.classList.remove("active");
      }
    });

    // Specific view activations
    if (viewName === "timeline" && timelineCanvas && currentTimeline) {
      setTimeout(() => {
        timelineCanvas.resize();
        timelineCanvas.render();
      }, 50);
    } else if (viewName === "reference") {
      loadReferenceDocs();
    }
  }

  window.addEventListener("hashchange", handleRoute);

  // --- Toast Notifications ---
  function showToast(message, type = "success") {
    const container = document.getElementById("toastContainer");
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transition = "opacity 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  // --- Trace Management ---
  async function loadTraces(selectNewest = false) {
    try {
      tracesList = await api.getTraces();
      populateTraceSelect();
      renderTracesTable();

      if (tracesList.length > 0) {
        if (!currentTraceId || selectNewest || !tracesList.some(t => t.trace_id === currentTraceId)) {
          await selectTrace(tracesList[0].trace_id);
        } else {
          await loadCurrentTraceDetails();
        }
      } else {
        resetWorkspaceToEmpty();
      }
    } catch (err) {
      showToast(`加载 Trace 列表失败: ${err.message}`, "error");
    }
  }

  function populateTraceSelect() {
    traceSelect.innerHTML = "";
    if (tracesList.length === 0) {
      traceSelect.innerHTML = '<option value="">(暂无 Trace 会话)</option>';
      return;
    }

    tracesList.forEach(t => {
      const opt = document.createElement("option");
      opt.value = t.trace_id;
      opt.textContent = `${t.filename} (${t.parsed_events} 事件)`;
      if (t.trace_id === currentTraceId) {
        opt.selected = true;
      }
      traceSelect.appendChild(opt);
    });
  }

  traceSelect.addEventListener("change", (e) => {
    if (e.target.value) {
      selectTrace(e.target.value);
    }
  });

  async function selectTrace(traceId) {
    currentTraceId = traceId;
    traceSelect.value = traceId;
    await loadCurrentTraceDetails();
  }

  async function loadCurrentTraceDetails() {
    if (!currentTraceId) return;
    try {
      // 1. Fetch metadata
      currentTraceMeta = await api.getTrace(currentTraceId);

      // 2. Fetch anomalies
      currentAnomalies = await api.getAnomalies(currentTraceId);
      updateAnomalyBadge();
      renderAnomalies();

      // 3. Fetch stats
      currentStats = await api.getStats(currentTraceId);
      renderOverviewKPIs();
      renderStatsView();

      // 4. Fetch timeline
      currentTimeline = await api.getTimeline(currentTraceId);
      if (timelineCanvas && currentTraceMeta) {
        timelineCanvas.setData(
          currentTimeline,
          currentTraceMeta.time_range.start_ns,
          currentTraceMeta.time_range.end_ns
        );
        initTimelineSlider();
      }
    } catch (err) {
      showToast(`加载 Trace 数据详情失败: ${err.message}`, "error");
    }
  }

  function resetWorkspaceToEmpty() {
    currentTraceId = null;
    currentTraceMeta = null;
    currentAnomalies = [];
    currentStats = null;
    currentTimeline = null;

    document.getElementById("kpiTotalEvents").textContent = "0";
    document.getElementById("kpiDurationText").textContent = "时间跨度: -";
    document.getElementById("kpiThreads").textContent = "0";
    document.getElementById("kpiTopThread").textContent = "-";
    document.getElementById("kpiTopThreadPct").textContent = "CPU 占空比: -";
    document.getElementById("kpiAnomalies").textContent = "0";
    anomalyNavBadge.style.display = "none";
  }

  function updateAnomalyBadge() {
    const count = currentAnomalies.length;
    if (count > 0) {
      anomalyNavBadge.textContent = count;
      anomalyNavBadge.style.display = "inline-block";
    } else {
      anomalyNavBadge.style.display = "none";
    }
  }

  // --- Render Views ---

  // 1. Overview
  function renderOverviewKPIs() {
    if (!currentTraceMeta) return;

    document.getElementById("kpiTotalEvents").textContent = currentTraceMeta.parsed_events.toLocaleString();
    const durationMs = ((currentTraceMeta.time_range.end_ns - currentTraceMeta.time_range.start_ns) / 1_000_000).toFixed(1);
    document.getElementById("kpiDurationText").textContent = `时间跨度: ${durationMs} ms`;

    document.getElementById("kpiThreads").textContent = currentTraceMeta.threads;

    const kpiCard = document.getElementById("kpiAnomalyCard");
    const count = currentAnomalies.length;
    document.getElementById("kpiAnomalies").textContent = count;
    if (count > 0) {
      kpiCard.classList.add("highlight-danger");
    } else {
      kpiCard.classList.remove("highlight-danger");
    }

    if (currentStats && currentStats.cpu && currentStats.cpu.length > 0) {
      const top = currentStats.cpu[0];
      document.getElementById("kpiTopThread").textContent = top.thread_name;
      document.getElementById("kpiTopThreadPct").textContent = `CPU 占空比: ${top.cpu_usage_pct}% [${top.process}]`;
    } else {
      document.getElementById("kpiTopThread").textContent = "-";
      document.getElementById("kpiTopThreadPct").textContent = "CPU 占空比: -";
    }
  }

  function renderTracesTable() {
    const tbody = document.getElementById("traceTableBody");
    tbody.innerHTML = "";
    document.getElementById("traceCountBadge").textContent = `共 ${tracesList.length} 个会话`;

    if (tracesList.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:var(--text-secondary);">暂无 Trace，请点击上方按钮生成或上传</td></tr>';
      return;
    }

    tracesList.forEach(t => {
      const tr = document.createElement("tr");
      const isSelected = t.trace_id === currentTraceId;
      if (isSelected) tr.style.background = "rgba(56, 139, 253, 0.08)";

      const durMs = ((t.time_range.end_ns - t.time_range.start_ns) / 1_000_000).toFixed(0);
      const createdDate = t.created_at ? t.created_at.slice(0, 19).replace("T", " ") : "-";

      tr.innerHTML = `
        <td><code style="color:var(--accent-cyan); font-weight:600;">${t.trace_id}</code></td>
        <td style="font-weight:600;">${t.filename}</td>
        <td>${t.parsed_events.toLocaleString()} / ${t.total_lines.toLocaleString()}</td>
        <td>${durMs} ms</td>
        <td>${t.threads}</td>
        <td style="font-size:0.75rem; color:var(--text-secondary);">${createdDate}</td>
        <td>
          <button class="btn btn-secondary btn-sm btn-select-trace" data-id="${t.trace_id}">${isSelected ? "当前正在分析" : "切换"}</button>
          <button class="btn btn-danger btn-sm btn-delete-trace" data-id="${t.trace_id}" style="margin-left:4px;">删除</button>
        </td>
      `;
      tbody.appendChild(tr);
    });

    tbody.querySelectorAll(".btn-select-trace").forEach(btn => {
      btn.addEventListener("click", () => selectTrace(btn.getAttribute("data-id")));
    });

    tbody.querySelectorAll(".btn-delete-trace").forEach(btn => {
      btn.addEventListener("click", async () => {
        const tid = btn.getAttribute("data-id");
        if (confirm(`确定删除会话 ${tid} 及其关联事件吗？`)) {
          try {
            await api.deleteTrace(tid);
            showToast(`会话 ${tid} 已删除`);
            await loadTraces();
          } catch (err) {
            showToast(`删除失败: ${err.message}`, "error");
          }
        }
      });
    });
  }

  // 2. Timeline Controls
  function initTimelineSlider() {
    if (!currentTraceMeta) return;
    const slider = document.getElementById("zoomSlider");
    slider.value = 0;
    updateRangeDisplay(currentTraceMeta.time_range.start_ns, currentTraceMeta.time_range.end_ns);

    slider.oninput = (e) => {
      const zoomVal = parseInt(e.target.value, 10);
      const totalStart = currentTraceMeta.time_range.start_ns;
      const totalEnd = currentTraceMeta.time_range.end_ns;
      const totalSpan = totalEnd - totalStart;

      // zoom factor from 1.0 (zoomVal=0) to 0.05 (zoomVal=100)
      const ratio = 1.0 - (zoomVal / 100) * 0.95;
      const newSpan = Math.max(100_000, totalSpan * ratio);
      const newEnd = totalStart + newSpan;

      timelineCanvas.setViewRange(totalStart, newEnd);
      updateRangeDisplay(totalStart, newEnd);
    };
  }

  function updateRangeDisplay(startNs, endNs) {
    const rangeDisplay = document.getElementById("rangeDisplay");
    if (rangeDisplay) {
      const s = (startNs / 1_000_000).toFixed(1);
      const e = (endNs / 1_000_000).toFixed(1);
      const d = ((endNs - startNs) / 1_000_000).toFixed(1);
      rangeDisplay.textContent = `${s}ms ~ ${e}ms (窗口: ${d}ms)`;
    }
  }

  document.getElementById("btnResetZoom").addEventListener("click", () => {
    if (!currentTraceMeta || !timelineCanvas) return;
    timelineCanvas.setViewRange(currentTraceMeta.time_range.start_ns, currentTraceMeta.time_range.end_ns);
    document.getElementById("zoomSlider").value = 0;
    updateRangeDisplay(currentTraceMeta.time_range.start_ns, currentTraceMeta.time_range.end_ns);
  });

  document.getElementById("threadFilterInput").addEventListener("input", (e) => {
    if (timelineCanvas) {
      timelineCanvas.setFilter(e.target.value);
    }
  });

  document.getElementById("btnExportTimelinePng").addEventListener("click", () => {
    if (!timelineCanvas) return;
    const dataUrl = timelineCanvas.exportPNG();
    const a = document.createElement("a");
    a.href = dataUrl;
    a.download = `tracelens_${currentTraceId || "timeline"}.png`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    showToast("时间线图片已导出为 PNG 文件");
  });

  // 3. Stats View
  function renderStatsView() {
    if (!currentStats) return;

    // CPU Stats bars
    const cpuContainer = document.getElementById("cpuStatsList");
    cpuContainer.innerHTML = "";
    const cpuList = currentStats.cpu || [];

    if (cpuList.length === 0) {
      cpuContainer.innerHTML = '<div style="color:var(--text-secondary); font-size:0.85rem;">暂无 CPU 线程统计</div>';
    } else {
      cpuList.slice(0, 10).forEach(th => {
        const item = document.createElement("div");
        item.style.marginBottom = "8px";
        item.innerHTML = `
          <div style="display:flex; justify-content:space-between; font-size:0.83rem; margin-bottom:4px;">
            <div>
              <span style="font-weight:600; color:var(--text-primary);">${th.thread_name}</span>
              <span style="font-size:0.75rem; color:var(--accent-cyan); margin-left:6px;">[${th.process}] (TID ${th.thread_id})</span>
            </div>
            <div style="font-family:var(--font-mono); font-weight:700; color:var(--accent-blue);">
              CPU 占空比: ${th.cpu_usage_pct}%
            </div>
          </div>
          <div style="display:flex; height:12px; border-radius:3px; overflow:hidden; background:#21262d;">
            <div title="RUNNING: ${th.running_pct}%" style="width:${th.running_pct}%; background:var(--state-running);"></div>
            <div title="READY: ${th.ready_pct}%" style="width:${th.ready_pct}%; background:var(--state-ready);"></div>
            <div title="BLOCKED: ${th.blocked_pct}%" style="width:${th.blocked_pct}%; background:var(--state-blocked);"></div>
          </div>
          <div style="display:flex; gap:12px; font-size:0.72rem; color:var(--text-secondary); margin-top:2px;">
            <span>运行态: ${th.running_pct}%</span>
            <span>就绪态: ${th.ready_pct}%</span>
            <span>阻塞态: ${th.blocked_pct}%</span>
          </div>
        `;
        cpuContainer.appendChild(item);
      });
    }

    // IPC Metrics Table
    const ipcBody = document.getElementById("ipcTableBody");
    ipcBody.innerHTML = "";
    const ipc = currentStats.ipc || {};
    const channels = ipc.channels || [];
    document.getElementById("ipcTotalsBadge").textContent = `总消息: ${(ipc.total_messages || 0).toLocaleString()} | 总脉冲: ${(ipc.total_pulses || 0).toLocaleString()}`;

    if (channels.length === 0) {
      ipcBody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--text-secondary);">暂无通道数据</td></tr>';
    } else {
      channels.forEach(ch => {
        const tr = document.createElement("tr");
        const avgUs = ch.avg_roundtrip_ns > 0 ? (ch.avg_roundtrip_ns / 1000).toFixed(1) + " µs" : "-";
        tr.innerHTML = `
          <td><code>${ch.channel_id}</code></td>
          <td style="font-weight:600; color:var(--accent-cyan);">${ch.channel_name}</td>
          <td>${ch.message_count.toLocaleString()}</td>
          <td>${ch.pulse_count.toLocaleString()}</td>
          <td style="font-family:var(--font-mono);">${avgUs}</td>
        `;
        ipcBody.appendChild(tr);
      });
    }

    // IRQ Metrics Table
    const irqBody = document.getElementById("irqTableBody");
    irqBody.innerHTML = "";
    const interrupts = currentStats.interrupts || [];

    if (interrupts.length === 0) {
      irqBody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--text-secondary);">暂无中断数据</td></tr>';
    } else {
      interrupts.forEach(ir => {
        const tr = document.createElement("tr");
        const totMs = (ir.total_duration_ns / 1_000_000).toFixed(2) + " ms";
        const avgUs = (ir.avg_duration_ns / 1000).toFixed(1) + " µs";
        const maxUs = (ir.max_duration_ns / 1000).toFixed(1) + " µs";

        tr.innerHTML = `
          <td><span style="font-weight:700; color:var(--accent-red);">IRQ ${ir.irq}</span></td>
          <td>${ir.count.toLocaleString()} 次</td>
          <td>${totMs}</td>
          <td style="font-family:var(--font-mono);">${avgUs}</td>
          <td style="font-family:var(--font-mono);">${maxUs}</td>
        `;
        irqBody.appendChild(tr);
      });
    }
  }

  // 4. Anomalies View
  function renderAnomalies() {
    const container = document.getElementById("anomalyListContainer");
    container.innerHTML = "";

    const filtered = currentAnomalies.filter(a => {
      if (anomalyFilter === "all") return true;
      return a.severity.toLowerCase() === anomalyFilter;
    });

    if (filtered.length === 0) {
      container.innerHTML = '<div style="color:var(--text-secondary); text-align:center; padding:40px 0;">当前过滤条件下无实时异常</div>';
      return;
    }

    filtered.forEach(an => {
      const card = document.createElement("div");
      card.className = `anomaly-card sev-${an.severity.toLowerCase()}`;

      const durMs = ((an.end_ns - an.start_ns) / 1_000_000).toFixed(1);
      const startMs = (an.start_ns / 1_000_000).toFixed(1);
      const endMs = (an.end_ns / 1_000_000).toFixed(1);

      const threadsHtml = (an.threads || []).map(t => `<span class="thread-tag">${t}</span>`).join("");

      card.innerHTML = `
        <div class="anomaly-header">
          <div style="display:flex; align-items:center; gap:8px;">
            <span class="anomaly-badge badge-${an.severity.toLowerCase()}">${an.severity}</span>
            <span class="anomaly-title">${getAnomalyTitleCN(an.type)}</span>
          </div>
          <div class="anomaly-time">t = ${startMs}ms ~ ${endMs}ms (+${durMs}ms)</div>
        </div>
        <div class="anomaly-body">${an.description}</div>
        <div class="anomaly-suggestion">
          <span>💡</span>
          <div><strong>修复建议:</strong> ${an.suggestion}</div>
        </div>
        <div class="anomaly-footer">
          <div class="anomaly-threads-tags">${threadsHtml}</div>
          <button class="btn btn-secondary btn-sm btn-locate-anomaly" data-start="${an.start_ns}" data-end="${an.end_ns}">
            📍 在时间线中定位
          </button>
        </div>
      `;
      container.appendChild(card);
    });

    container.querySelectorAll(".btn-locate-anomaly").forEach(btn => {
      btn.addEventListener("click", () => {
        const s = parseInt(btn.getAttribute("data-start"), 10);
        const e = parseInt(btn.getAttribute("data-end"), 10);
        // Expand window slightly for context
        const padding = Math.max(20_000_000, Math.floor((e - s) * 0.4));
        const viewS = Math.max(0, s - padding);
        const viewE = e + padding;

        window.location.hash = "#timeline";
        setTimeout(() => {
          if (timelineCanvas) {
            timelineCanvas.setViewRange(viewS, viewE);
            updateRangeDisplay(viewS, viewE);
          }
        }, 100);
      });
    });
  }

  function getAnomalyTitleCN(type) {
    switch (type) {
      case "priority-inversion": return "优先级反转 (Priority Inversion)";
      case "deadline-miss": return "错失调度截止期 (Deadline Miss)";
      case "interrupt-storm": return "硬件中断风暴 (Interrupt Storm)";
      case "message-queue-backlog": return "消息队列积压 (Queue Backlog)";
      default: return type;
    }
  }

  document.querySelectorAll(".anomaly-filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".anomaly-filter-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      anomalyFilter = btn.getAttribute("data-sev");
      renderAnomalies();
    });
  });

  // 5. Reference View Docs
  async function loadReferenceDocs() {
    const container = document.getElementById("eventClassesReferenceContainer");
    try {
      const ref = await api.getReference();
      container.innerHTML = "";
      ref.event_classes.forEach(cls => {
        const item = document.createElement("div");
        item.style.background = "var(--bg-tertiary)";
        item.style.padding = "14px";
        item.style.borderRadius = "6px";
        item.style.border = "1px solid var(--border-color)";

        let fieldsList = Object.entries(cls.fields).map(([k, v]) => `<li><code>${k}</code>: ${v}</li>`).join("");

        item.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span style="font-weight:700; color:var(--accent-cyan); font-size:1rem;">${cls.name}</span>
          </div>
          <p style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:8px;">${cls.description}</p>
          <div style="font-size:0.8rem;">
            <strong>字段定义:</strong>
            <ul style="padding-left:18px; margin-top:4px; line-height:1.6; color:var(--text-primary);">${fieldsList}</ul>
          </div>
        `;
        container.appendChild(item);
      });
    } catch (err) {
      container.innerHTML = `<div style="color:var(--accent-red);">加载参考失败: ${err.message}</div>`;
    }
  }

  // --- Modals Management ---
  function openModal(modalId) {
    document.getElementById(modalId).classList.add("active");
  }

  function closeModal(modalId) {
    document.getElementById(modalId).classList.remove("active");
  }

  document.querySelectorAll("[data-close]").forEach(el => {
    el.addEventListener("click", () => {
      closeModal(el.getAttribute("data-close"));
    });
  });

  document.getElementById("btnOpenGenerate").addEventListener("click", () => {
    openModal("modalGenerate");
  });

  document.getElementById("btnOpenUpload").addEventListener("click", () => {
    document.getElementById("uploadDiagnostics").style.display = "none";
    document.getElementById("uploadFileInput").value = "";
    openModal("modalUpload");
  });

  document.getElementById("btnRefreshOverview").addEventListener("click", () => {
    loadTraces();
    showToast("已刷新 Trace 列表与指标");
  });

  // Submit Generate Trace
  document.getElementById("btnSubmitGenerate").addEventListener("click", async () => {
    const btn = document.getElementById("btnSubmitGenerate");
    btn.disabled = true;
    btn.textContent = "正在生成并分析...";

    const threads = parseInt(document.getElementById("genThreads").value, 10) || 8;
    const duration = parseInt(document.getElementById("genDuration").value, 10) || 10;
    const inject = [];
    if (document.getElementById("injPi").checked) inject.push("priority-inversion");
    if (document.getElementById("injDl").checked) inject.push("deadline-miss");
    if (document.getElementById("injIrq").checked) inject.push("interrupt-storm");
    if (document.getElementById("injBk").checked) inject.push("message-queue-backlog");

    try {
      const res = await api.generateTrace({
        threads,
        duration_seconds: duration,
        inject
      });
      showToast(`示例 Trace 生成成功: ${res.parsed_events} 个事件入库`);
      closeModal("modalGenerate");
      await loadTraces(true);
    } catch (err) {
      showToast(`生成失败: ${err.message}`, "error");
    } finally {
      btn.disabled = false;
      btn.textContent = "立即生成并解析";
    }
  });

  // Submit Upload Trace
  document.getElementById("btnSubmitUpload").addEventListener("click", async () => {
    const fileInput = document.getElementById("uploadFileInput");
    if (!fileInput.files || fileInput.files.length === 0) {
      alert("请先选择一个 Trace 文件");
      return;
    }

    const file = fileInput.files[0];
    const btn = document.getElementById("btnSubmitUpload");
    btn.disabled = true;
    btn.textContent = "正在上传流式解析...";

    const diagBox = document.getElementById("uploadDiagnostics");

    try {
      const res = await api.uploadTrace(file);
      diagBox.style.display = "block";
      diagBox.innerHTML = `
        <div style="color:var(--accent-green); font-weight:700;">解析完成！</div>
        <div>总行数: ${res.total_lines}</div>
        <div>成功解析事件: ${res.parsed_events}</div>
        <div>格式错误行: ${res.failed_lines.length}</div>
        ${res.failed_lines.length > 0 ? `<div style="max-height:80px; overflow-y:auto; color:var(--accent-red); margin-top:4px;">${res.failed_lines.slice(0, 5).map(f => `Line ${f.line}: ${f.reason}`).join("<br>")}</div>` : ""}
      `;
      showToast(`文件上传解析完成: ${res.parsed_events} 个事件入库`);
      await loadTraces(true);
    } catch (err) {
      showToast(`上传解析失败: ${err.message}`, "error");
      diagBox.style.display = "block";
      diagBox.innerHTML = `<div style="color:var(--accent-red); font-weight:700;">错误: ${err.message}</div>`;
    } finally {
      btn.disabled = false;
      btn.textContent = "开始上传解析";
    }
  });

  // Initial startup sequence
  handleRoute();
  loadTraces();
});
