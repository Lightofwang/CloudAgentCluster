/**
 * TraceLens Timeline Canvas Renderer
 * High-performance HTML5 Canvas rendering for QNX multi-threaded scheduling timelines.
 */
class TimelineCanvas {
  constructor(canvasElement, tooltipElement) {
    this.canvas = canvasElement;
    this.ctx = canvasElement.getContext("2d");
    this.tooltip = tooltipElement;

    // Viewport and data state
    this.threads = [];
    this.interrupts = [];
    this.totalStartNs = 0;
    this.totalEndNs = 1_000_000_000;
    this.viewStartNs = 0;
    this.viewEndNs = 1_000_000_000;

    // Dimensions
    this.leftGutterWidth = 200;
    this.headerHeight = 36;
    this.rowHeight = 34;
    this.interruptBarHeight = 22;

    // Interaction state
    this.isDragging = false;
    this.dragStartX = 0;
    this.dragStartViewStartNs = 0;
    this.dragStartViewEndNs = 0;
    this.hoveredSegment = null;

    // Filter
    this.filterText = "";

    this.initEvents();
    this.resize();
  }

  setData(timelineData, startNs, endNs) {
    this.threads = timelineData.threads || [];
    this.interrupts = timelineData.interrupts || [];
    this.totalStartNs = startNs;
    this.totalEndNs = Math.max(startNs + 1, endNs);
    this.viewStartNs = startNs;
    this.viewEndNs = this.totalEndNs;
    this.resize();
    this.render();
  }

  setViewRange(startNs, endNs) {
    this.viewStartNs = Math.max(this.totalStartNs, startNs);
    this.viewEndNs = Math.min(this.totalEndNs, Math.max(this.viewStartNs + 1000, endNs));
    this.render();
  }

  setFilter(text) {
    this.filterText = (text || "").toLowerCase().trim();
    this.resize();
    this.render();
  }

  getFilteredThreads() {
    if (!this.filterText) return this.threads;
    return this.threads.filter(t => 
      t.thread_name.toLowerCase().includes(this.filterText) ||
      (t.process && t.process.toLowerCase().includes(this.filterText)) ||
      String(t.thread_id).includes(this.filterText)
    );
  }

  resize() {
    const rect = this.canvas.parentElement.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const filteredThreads = this.getFilteredThreads();
    const totalHeight = Math.max(480, this.headerHeight + this.interruptBarHeight + (filteredThreads.length * this.rowHeight) + 20);

    this.canvas.width = rect.width * dpr;
    this.canvas.height = totalHeight * dpr;
    this.canvas.style.width = `${rect.width}` + "px";
    this.canvas.style.height = `${totalHeight}` + "px";
    this.ctx.scale(dpr, dpr);
    this.cssWidth = rect.width;
    this.cssHeight = totalHeight;
  }

  initEvents() {
    window.addEventListener("resize", () => {
      this.resize();
      this.render();
    });

    // Mouse drag for panning
    this.canvas.addEventListener("mousedown", (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      if (x > this.leftGutterWidth) {
        this.isDragging = true;
        this.dragStartX = x;
        this.dragStartViewStartNs = this.viewStartNs;
        this.dragStartViewEndNs = this.viewEndNs;
        this.canvas.style.cursor = "grabbing";
      }
    });

    window.addEventListener("mousemove", (e) => {
      if (this.isDragging) {
        const rect = this.canvas.getBoundingClientRect();
        const currentX = e.clientX - rect.left;
        const deltaX = currentX - this.dragStartX;
        const timelineWidth = this.cssWidth - this.leftGutterWidth;
        const currentWindowNs = this.dragStartViewEndNs - this.dragStartViewStartNs;
        const deltaNs = (deltaX / timelineWidth) * currentWindowNs;

        let newStart = this.dragStartViewStartNs - deltaNs;
        let newEnd = this.dragStartViewEndNs - deltaNs;

        if (newStart < this.totalStartNs) {
          newEnd += (this.totalStartNs - newStart);
          newStart = this.totalStartNs;
        }
        if (newEnd > this.totalEndNs) {
          newStart -= (newEnd - this.totalEndNs);
          newEnd = this.totalEndNs;
        }

        this.viewStartNs = Math.max(this.totalStartNs, newStart);
        this.viewEndNs = Math.min(this.totalEndNs, newEnd);
        this.render();
      } else {
        this.handleHover(e);
      }
    });

    window.addEventListener("mouseup", () => {
      if (this.isDragging) {
        this.isDragging = false;
        this.canvas.style.cursor = "crosshair";
      }
    });

    // Wheel for zooming
    this.canvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      const rect = this.canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      if (mouseX <= this.leftGutterWidth) return;

      const timelineWidth = this.cssWidth - this.leftGutterWidth;
      const mouseRatio = (mouseX - this.leftGutterWidth) / timelineWidth;
      const currentSpan = this.viewEndNs - this.viewStartNs;
      const zoomFactor = e.deltaY < 0 ? 0.75 : 1.35; // zoom in or out

      const newSpan = Math.max(50_000, Math.min(this.totalEndNs - this.totalStartNs, currentSpan * zoomFactor));
      const mouseNs = this.viewStartNs + (currentSpan * mouseRatio);

      let newStart = mouseNs - (newSpan * mouseRatio);
      let newEnd = mouseNs + (newSpan * (1 - mouseRatio));

      if (newStart < this.totalStartNs) newStart = this.totalStartNs;
      if (newEnd > this.totalEndNs) newEnd = this.totalEndNs;

      this.viewStartNs = newStart;
      this.viewEndNs = newEnd;
      this.render();

      if (this.onRangeChange) {
        this.onRangeChange(this.viewStartNs, this.viewEndNs);
      }
    }, { passive: false });
  }

  handleHover(e) {
    if (!this.tooltip) return;
    const rect = this.canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    if (mouseX <= this.leftGutterWidth || mouseY < this.headerHeight) {
      this.tooltip.style.display = "none";
      return;
    }

    const timelineWidth = this.cssWidth - this.leftGutterWidth;
    const timeSpan = this.viewEndNs - this.viewStartNs;
    const mouseNs = this.viewStartNs + ((mouseX - this.leftGutterWidth) / timelineWidth) * timeSpan;

    const filteredThreads = this.getFilteredThreads();
    const rowOffset = mouseY - (this.headerHeight + this.interruptBarHeight);
    const rowIndex = Math.floor(rowOffset / this.rowHeight);

    if (rowIndex >= 0 && rowIndex < filteredThreads.length) {
      const thread = filteredThreads[rowIndex];
      // Find segment at mouseNs
      const seg = (thread.segments || []).find(s => mouseNs >= s.start_ns && mouseNs <= s.end_ns);
      if (seg) {
        const durNs = seg.end_ns - seg.start_ns;
        const durMs = (durNs / 1_000_000).toFixed(2);
        this.tooltip.style.display = "block";
        this.tooltip.style.left = `${e.clientX + 14}` + "px";
        this.tooltip.style.top = `${e.clientY + 10}` + "px";
        this.tooltip.innerHTML = `
          <div style="font-weight:700; color:var(--text-primary); margin-bottom:4px;">${thread.thread_name} (TID ${thread.thread_id})</div>
          <div>进程: <span style="color:var(--accent-cyan)">${thread.process}</span></div>
          <div>状态: <span style="font-weight:700; color:${this.getStateColor(seg.state)}">${seg.state}</span></div>
          <div>持续耗时: <span style="font-family:var(--font-mono)">${durMs} ms (${durNs.toLocaleString()} ns)</span></div>
          <div style="font-size:0.72rem; color:var(--text-muted); margin-top:4px;">t = ${(seg.start_ns / 1_000_000).toFixed(2)}ms ~ ${(seg.end_ns / 1_000_000).toFixed(2)}ms</div>
        `;
        return;
      }
    }

    // Check interrupts row
    if (mouseY >= this.headerHeight && mouseY < this.headerHeight + this.interruptBarHeight) {
      const nearIrq = this.interrupts.find(irq => Math.abs(irq.timestamp_ns - mouseNs) < (timeSpan / timelineWidth) * 8);
      if (nearIrq) {
        this.tooltip.style.display = "block";
        this.tooltip.style.left = `${e.clientX + 14}` + "px";
        this.tooltip.style.top = `${e.clientY + 10}` + "px";
        this.tooltip.innerHTML = `
          <div style="font-weight:700; color:var(--accent-red)">硬件中断 IRQ ${nearIrq.irq}</div>
          <div>时间戳: ${(nearIrq.timestamp_ns / 1_000_000).toFixed(3)} ms</div>
          <div>执行耗时: ${(nearIrq.duration_ns / 1000).toFixed(1)} µs</div>
        `;
        return;
      }
    }

    this.tooltip.style.display = "none";
  }

  getStateColor(state) {
    switch (state) {
      case "RUNNING": return "#2ea043";
      case "READY": return "#d29922";
      case "BLOCKED": return "#30363d";
      default: return "#596371";
    }
  }

  formatTime(ns) {
    if (ns >= 1_000_000_000) {
      return (ns / 1_000_000_000).toFixed(2) + "s";
    } else if (ns >= 1_000_000) {
      return (ns / 1_000_000).toFixed(1) + "ms";
    } else if (ns >= 1_000) {
      return (ns / 1_000).toFixed(0) + "µs";
    }
    return ns + "ns";
  }

  render() {
    const ctx = this.ctx;
    const w = this.cssWidth;
    const h = this.cssHeight;
    const gutter = this.leftGutterWidth;
    const timelineW = w - gutter;
    const spanNs = Math.max(1, this.viewEndNs - this.viewStartNs);

    // Clear canvas
    ctx.fillStyle = "#090d16";
    ctx.fillRect(0, 0, w, h);

    // 1. Draw Time Ruler Header
    ctx.fillStyle = "#121721";
    ctx.fillRect(0, 0, w, this.headerHeight);
    ctx.strokeStyle = "#2b3648";
    ctx.lineWidth = 1;
    ctx.strokeRect(0, 0, w, this.headerHeight);

    // Draw Gutter Header Label
    ctx.fillStyle = "#8b949e";
    ctx.font = "600 11px sans-serif";
    ctx.fillText("QNX 线程 / 进程", 16, 22);

    // Compute intelligent time ticks (e.g. 8 to 12 ticks across ruler)
    const tickCount = 10;
    const rawStep = spanNs / tickCount;
    const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));
    const residual = rawStep / magnitude;
    let stepNs = magnitude;
    if (residual >= 5) stepNs = 5 * magnitude;
    else if (residual >= 2) stepNs = 2 * magnitude;

    const firstTick = Math.ceil(this.viewStartNs / stepNs) * stepNs;

    ctx.font = "10px ui-monospace, monospace";
    ctx.textAlign = "center";
    for (let t = firstTick; t <= this.viewEndNs; t += stepNs) {
      const x = gutter + ((t - this.viewStartNs) / spanNs) * timelineW;
      ctx.strokeStyle = "#2b3648";
      ctx.beginPath();
      ctx.moveTo(x, this.headerHeight - 8);
      ctx.lineTo(x, h);
      ctx.stroke();

      ctx.fillStyle = "#8b949e";
      ctx.fillText(this.formatTime(t), x, 22);
    }
    ctx.textAlign = "left";

    // 2. Draw Interrupts Row
    const irqY = this.headerHeight;
    ctx.fillStyle = "#0f141f";
    ctx.fillRect(0, irqY, w, this.interruptBarHeight);
    ctx.fillStyle = "#f85149";
    ctx.font = "600 10px sans-serif";
    ctx.fillText("⚡ 硬件中断 (IRQ)", 16, irqY + 15);

    // Draw interrupt ticks
    for (const irq of this.interrupts) {
      if (irq.timestamp_ns < this.viewStartNs || irq.timestamp_ns > this.viewEndNs) continue;
      const x = gutter + ((irq.timestamp_ns - this.viewStartNs) / spanNs) * timelineW;
      ctx.fillStyle = "#f85149";
      ctx.fillRect(x - 1, irqY + 3, 2, this.interruptBarHeight - 6);
    }

    // 3. Draw Threads Rows
    const filteredThreads = this.getFilteredThreads();
    let currentY = this.headerHeight + this.interruptBarHeight;

    for (let i = 0; i < filteredThreads.length; i++) {
      const th = filteredThreads[i];
      const isEven = i % 2 === 0;

      // Row background
      ctx.fillStyle = isEven ? "#0c111a" : "#0f1521";
      ctx.fillRect(0, currentY, w, this.rowHeight);

      // Thread label in gutter
      ctx.fillStyle = "#f0f6fc";
      ctx.font = "600 11px sans-serif";
      const name = th.thread_name.length > 18 ? th.thread_name.slice(0, 16) + "…" : th.thread_name;
      ctx.fillText(name, 16, currentY + 16);

      ctx.fillStyle = "#39c5cf";
      ctx.font = "9px ui-monospace, monospace";
      ctx.fillText(`TID ${th.thread_id} [${th.process || "qnx"}]`, 16, currentY + 28);

      // Draw state segments
      for (const seg of (th.segments || [])) {
        if (seg.end_ns < this.viewStartNs || seg.start_ns > this.viewEndNs) continue;

        const segStartClamped = Math.max(seg.start_ns, this.viewStartNs);
        const segEndClamped = Math.min(seg.end_ns, this.viewEndNs);

        const x1 = gutter + ((segStartClamped - this.viewStartNs) / spanNs) * timelineW;
        const x2 = gutter + ((segEndClamped - this.viewStartNs) / spanNs) * timelineW;
        const segW = Math.max(1, x2 - x1);

        ctx.fillStyle = this.getStateColor(seg.state);
        ctx.fillRect(x1, currentY + 4, segW, this.rowHeight - 8);

        // Border for blocked state for contrast
        if (seg.state === "BLOCKED") {
          ctx.strokeStyle = "#484f58";
          ctx.lineWidth = 1;
          ctx.strokeRect(x1, currentY + 4, segW, this.rowHeight - 8);
        }
      }

      // Row bottom divider
      ctx.strokeStyle = "#1b2333";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, currentY + this.rowHeight);
      ctx.lineTo(w, currentY + this.rowHeight);
      ctx.stroke();

      currentY += this.rowHeight;
    }

    // 4. Draw Gutter Separator
    ctx.strokeStyle = "#2b3648";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(gutter, 0);
    ctx.lineTo(gutter, h);
    ctx.stroke();
  }

  exportPNG() {
    return this.canvas.toDataURL("image/png");
  }
}
