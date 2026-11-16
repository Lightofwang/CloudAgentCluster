/**
 * GraphLens — Connected-Context Agent Memory Workbench
 * Interactive Force-Directed Graph Canvas & Full-Stack Controller
 */

(function () {
  "use strict";

  // --- State ---
  const state = {
    nodes: [],
    edges: [],
    nodeMap: new Map(), // id -> node
    selectedNode: null,
    highlightedNeighbourIds: new Set(),
    highlightedEdgeIds: new Set(),
    pathNodes: [],
    pathEdges: [],
    pathMode: false,
    pathStartNode: null,
    transform: { x: 0, y: 0, k: 1 },
    isDraggingNode: false,
    draggedNode: null,
    isPanning: false,
    panStart: { x: 0, y: 0 },
    activeTab: "tab-ingest",
    activeTraceId: null,
  };

  // Label color palette
  const LABEL_COLORS = {
    Person: "#f59e0b",   // Amber
    Project: "#06b6d4",  // Cyan
    Topic: "#a855f7",    // Purple
    Tool: "#10b981",     // Emerald
    Date: "#f43f5e",     // Rose
    Entity: "#38bdf8",   // Light Blue fallback
  };

  // DOM Elements
  const canvas = document.getElementById("graphCanvas");
  const ctx = canvas.getContext("2d");
  const canvasContainer = document.getElementById("canvasContainer");

  // Stats elements
  const statDocs = document.getElementById("statDocs");
  const statChunks = document.getElementById("statChunks");
  const statEntities = document.getElementById("statEntities");
  const statRelations = document.getElementById("statRelations");
  const statSteps = document.getElementById("statSteps");

  // Action buttons
  const btnLoadDemo = document.getElementById("btnLoadDemo");
  const btnResetDemo = document.getElementById("btnResetDemo");
  const btnExportStore = document.getElementById("btnExportStore");
  const btnZoomIn = document.getElementById("btnZoomIn");
  const btnZoomOut = document.getElementById("btnZoomOut");
  const btnResetView = document.getElementById("btnResetView");
  const btnTogglePathMode = document.getElementById("btnTogglePathMode");
  const pathModeBadge = document.getElementById("pathModeBadge");
  const pathResultBox = document.getElementById("pathResultBox");

  // Ingest tab
  const docTitle = document.getElementById("docTitle");
  const docText = document.getElementById("docText");
  const fileUpload = document.getElementById("fileUpload");
  const btnIngest = document.getElementById("btnIngest");
  const ingestFeedback = document.getElementById("ingestFeedback");
  const docList = document.getElementById("docList");

  // Search & Filter
  const nodeSearchInput = document.getElementById("nodeSearchInput");
  const labelCheckboxes = document.querySelectorAll(".label-filter");

  // Ask tab
  const askInput = document.getElementById("askInput");
  const btnAsk = document.getElementById("btnAsk");
  const askResultContainer = document.getElementById("askResultContainer");

  // Traces tab
  const tracesList = document.getElementById("tracesList");
  const traceTimeline = document.getElementById("traceTimeline");
  const activeTraceTitle = document.getElementById("activeTraceTitle");

  // Cypher Console
  const cypherBar = document.getElementById("cypherBar");
  const cypherHeaderToggle = document.getElementById("cypherHeaderToggle");
  const cypherToggleIcon = document.getElementById("cypherToggleIcon");
  const cypherInput = document.getElementById("cypherInput");
  const btnRunCypher = document.getElementById("btnRunCypher");
  const confirmDestructive = document.getElementById("confirmDestructive");
  const cypherElapsedBadge = document.getElementById("cypherElapsedBadge");
  const cypherResultSection = document.getElementById("cypherResultSection");
  const cypherResultOutput = document.getElementById("cypherResultOutput");
  const resultCountInfo = document.getElementById("resultCountInfo");

  // Right Inspector
  const rightPanelTitle = document.getElementById("rightPanelTitle");
  const inspectorContent = document.getElementById("inspectorContent");
  const btnClearSelection = document.getElementById("btnClearSelection");

  // --- Initialization ---
  function init() {
    setupCanvas();
    setupEventListeners();
    refreshAll();
  }

  function setupCanvas() {
    resizeCanvas();
    window.addEventListener("resize", () => {
      resizeCanvas();
      render();
    });
  }

  function resizeCanvas() {
    const rect = canvasContainer.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;
    if (state.transform.x === 0 && state.transform.y === 0) {
      state.transform.x = rect.width / 2;
      state.transform.y = rect.height / 2;
    }
  }

  // --- API Client ---
  async function apiGet(endpoint) {
    const res = await fetch(endpoint);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Request failed");
    }
    return res.json();
  }

  async function apiPost(endpoint, data) {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Request failed");
    }
    return res.json();
  }

  async function apiDelete(endpoint) {
    const res = await fetch(endpoint, { method: "DELETE" });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Request failed");
    }
    return res.json();
  }

  // --- Data Loading ---
  async function refreshAll() {
    await Promise.all([
      fetchStats(),
      fetchGraphData(),
      fetchDocuments(),
      fetchTraces(),
    ]);
  }

  async function fetchStats() {
    try {
      const data = await apiGet("/api/stats");
      statDocs.textContent = data.documents;
      statChunks.textContent = data.chunks;
      statEntities.textContent = data.entities;
      statRelations.textContent = data.relationships;
      statSteps.textContent = data.steps;
    } catch (e) {
      console.warn("Failed to fetch stats:", e);
    }
  }

  async function fetchGraphData() {
    try {
      const activeLabels = Array.from(labelCheckboxes)
        .filter((cb) => cb.checked)
        .map((cb) => cb.value)
        .join(",");

      const url = activeLabels ? `/api/graph?limit=300&labels=${activeLabels}` : "/api/graph?limit=300";
      const data = await apiGet(url);

      const oldMap = state.nodeMap;
      const newNodes = [];
      const newMap = new Map();

      // Degree counter
      const degrees = {};
      data.edges.forEach((e) => {
        degrees[e.from] = (degrees[e.from] || 0) + 1;
        degrees[e.to] = (degrees[e.to] || 0) + 1;
      });

      data.nodes.forEach((n) => {
        const existing = oldMap.get(n.id);
        const nodeObj = {
          id: n.id,
          elementId: n.element_id,
          label: n.label || "Entity",
          name: n.name || "Unnamed",
          properties: n.properties || {},
          degree: degrees[n.id] || 0,
          radius: Math.max(10, Math.min(26, 10 + (degrees[n.id] || 0) * 2)),
          x: existing ? existing.x : (Math.random() - 0.5) * 400,
          y: existing ? existing.y : (Math.random() - 0.5) * 400,
          vx: existing ? existing.vx : 0,
          vy: existing ? existing.vy : 0,
        };
        newNodes.push(nodeObj);
        newMap.set(n.id, nodeObj);
      });

      const validEdges = [];
      data.edges.forEach((e) => {
        const source = newMap.get(e.from);
        const target = newMap.get(e.to);
        if (source && target) {
          validEdges.push({
            id: e.id,
            source: source,
            target: target,
            type: e.type,
          });
        }
      });

      state.nodes = newNodes;
      state.edges = validEdges;
      state.nodeMap = newMap;

      // Start physics simulation
      startSimulation();
    } catch (e) {
      console.error("Failed to load graph:", e);
    }
  }

  async function fetchDocuments() {
    try {
      const data = await apiGet("/api/documents");
      docList.innerHTML = "";
      if (data.documents.length === 0) {
        docList.innerHTML = `<p style="font-size: 11px; color: var(--text-muted);">No documents ingested yet.</p>`;
        return;
      }

      data.documents.forEach((doc) => {
        const item = document.createElement("div");
        item.className = "detail-card";
        item.style.padding = "8px";
        item.style.marginBottom = "4px";
        item.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <strong style="font-size: 12px; color: var(--text-primary); cursor: pointer;" title="View document chunks">${escapeHtml(doc.title)}</strong>
            <button class="btn btn-danger btn-sm" style="padding: 2px 6px; font-size: 10px;" data-del-id="${doc.id}">Delete</button>
          </div>
          <div style="font-size: 10px; color: var(--text-muted); margin-top: 4px;">
            ${doc.source} · ${doc.chunk_count} chunk(s)
          </div>
        `;

        // Click to view
        item.querySelector("strong").addEventListener("click", () => inspectDocument(doc.id));

        // Click to delete
        item.querySelector("button").addEventListener("click", async (ev) => {
          ev.stopPropagation();
          if (confirm(`Delete "${doc.title}" and its chunks?`)) {
            try {
              await apiDelete(`/api/documents/${doc.id}`);
              refreshAll();
            } catch (err) {
              alert(err.message);
            }
          }
        });

        docList.appendChild(item);
      });
    } catch (e) {
      console.warn("Failed to fetch documents:", e);
    }
  }

  async function inspectDocument(docId) {
    try {
      const doc = await apiGet(`/api/documents/${docId}`);
      rightPanelTitle.textContent = "Document View";
      btnClearSelection.style.display = "inline-flex";

      let chunksHtml = "";
      doc.chunks.forEach((c) => {
        chunksHtml += `
          <div style="background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 4px; padding: 6px; margin-top: 6px; font-size: 11px; color: #cbd5e1;">
            <div style="color: var(--accent-cyan); font-weight: 600; font-size: 10px; margin-bottom: 2px;">Chunk #${c.position + 1} (${c.id})</div>
            ${escapeHtml(c.text)}
          </div>
        `;
      });

      inspectorContent.innerHTML = `
        <div class="detail-card">
          <h4 style="font-size: 13px; color: var(--accent-cyan); margin-bottom: 6px;">${escapeHtml(doc.title)}</h4>
          <div class="detail-row"><span class="detail-label">ID:</span><span class="detail-val">${doc.id}</span></div>
          <div class="detail-row"><span class="detail-label">Source:</span><span class="detail-val">${doc.source}</span></div>
          <div class="detail-row"><span class="detail-label">Created:</span><span class="detail-val">${doc.created_at}</span></div>
        </div>
        <div class="detail-card">
          <label>Full Text</label>
          <p style="font-size: 11px; color: var(--text-secondary); line-height: 1.4; max-height: 120px; overflow-y: auto;">
            ${escapeHtml(doc.text)}
          </p>
        </div>
        <div class="detail-card">
          <label>Sentence Chunks (${doc.chunks.length})</label>
          <div style="max-height: 250px; overflow-y: auto;">
            ${chunksHtml}
          </div>
        </div>
      `;
    } catch (e) {
      alert("Failed to inspect document: " + e.message);
    }
  }

  async function fetchTraces() {
    try {
      const data = await apiGet("/api/traces");
      tracesList.innerHTML = "";
      if (data.traces.length === 0) {
        tracesList.innerHTML = `<p style="font-size: 11px; color: var(--text-muted);">No traces recorded yet.</p>`;
        traceTimeline.innerHTML = "";
        return;
      }

      data.traces.forEach((tr, idx) => {
        const item = document.createElement("div");
        item.className = "detail-card";
        item.style.padding = "8px";
        item.style.cursor = "pointer";
        item.style.marginBottom = "4px";
        item.innerHTML = `
          <strong style="font-size: 12px; color: var(--accent-cyan);">${escapeHtml(tr.name)}</strong>
          <div style="font-size: 10px; color: var(--text-muted); margin-top: 2px;">
            ${tr.step_count} step(s) · ${tr.id}
          </div>
        `;
        item.addEventListener("click", () => loadTraceDetail(tr.id, tr.name));
        tracesList.appendChild(item);

        if (idx === 0 && !state.activeTraceId) {
          loadTraceDetail(tr.id, tr.name);
        }
      });
    } catch (e) {
      console.warn("Failed to fetch traces:", e);
    }
  }

  async function loadTraceDetail(traceId, traceName) {
    state.activeTraceId = traceId;
    activeTraceTitle.textContent = `Timeline: ${traceName}`;
    try {
      const tr = await apiGet(`/api/traces/${traceId}`);
      traceTimeline.innerHTML = "";

      tr.steps.forEach((s) => {
        const stepEl = document.createElement("div");
        stepEl.className = "timeline-step";

        const entitiesBadges = (s.entities || [])
          .map((ent) => `<span class="citation-chip" style="font-size: 10px; cursor: pointer;" data-ent-name="${escapeHtml(ent)}">${escapeHtml(ent)}</span>`)
          .join(" ");

        stepEl.innerHTML = `
          <div class="timeline-dot"></div>
          <div class="timeline-header">
            <span style="color: var(--accent-amber); font-family: var(--font-mono); font-size: 10px;">[${s.kind.toUpperCase()}]</span>
            ${escapeHtml(s.name)}
          </div>
          <div class="timeline-desc">${escapeHtml(s.detail)}</div>
          ${entitiesBadges ? `<div style="margin-top: 4px;">${entitiesBadges}</div>` : ""}
        `;

        // Click entity badge to focus on canvas
        stepEl.querySelectorAll(".citation-chip").forEach((chip) => {
          chip.addEventListener("click", (e) => {
            e.stopPropagation();
            const entName = chip.dataset.entName;
            focusNodeByName(entName);
          });
        });

        traceTimeline.appendChild(stepEl);
      });
    } catch (e) {
      console.warn("Failed to load trace detail:", e);
    }
  }

  // --- Force-Directed Physics Simulation ---
  let animFrameId = null;
  let alpha = 1.0;

  function startSimulation() {
    alpha = 1.0;
    if (animFrameId) cancelAnimationFrame(animFrameId);
    tick();
  }

  function tick() {
    if (alpha > 0.005) {
      stepPhysics();
      alpha *= 0.985;
      render();
      animFrameId = requestAnimationFrame(tick);
    } else {
      render();
    }
  }

  function stepPhysics() {
    const nodes = state.nodes;
    const edges = state.edges;
    const k = 100;
    const k2 = k * k;

    // Repulsion between all node pairs
    for (let i = 0; i < nodes.length; i++) {
      const u = nodes[i];
      for (let j = i + 1; j < nodes.length; j++) {
        const v = nodes[j];
        let dx = v.x - u.x;
        let dy = v.y - u.y;
        let dist = Math.hypot(dx, dy) || 1;
        if (dist < 400) {
          const force = (k2 / (dist * dist)) * alpha * 0.8;
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          if (u !== state.draggedNode) {
            u.vx -= fx;
            u.vy -= fy;
          }
          if (v !== state.draggedNode) {
            v.vx += fx;
            v.vy += fy;
          }
        }
      }
    }

    // Spring attraction along edges
    for (let i = 0; i < edges.length; i++) {
      const e = edges[i];
      const u = e.source;
      const v = e.target;
      let dx = v.x - u.x;
      let dy = v.y - u.y;
      let dist = Math.hypot(dx, dy) || 1;
      const force = ((dist - k) / k) * alpha * 0.4;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      if (u !== state.draggedNode) {
        u.vx += fx;
        u.vy += fy;
      }
      if (v !== state.draggedNode) {
        v.vx -= fx;
        v.vy -= fy;
      }
    }

    // Centering gravity pull
    for (let i = 0; i < nodes.length; i++) {
      const u = nodes[i];
      if (u !== state.draggedNode) {
        u.vx -= u.x * 0.004 * alpha;
        u.vy -= u.y * 0.004 * alpha;

        // Damping and position update
        u.vx *= 0.85;
        u.vy *= 0.85;
        u.x += u.vx;
        u.y += u.vy;
      }
    }
  }

  // --- Canvas Rendering ---
  function render() {
    const rect = canvasContainer.getBoundingClientRect();
    ctx.save();
    ctx.clearRect(0, 0, rect.width, rect.height);

    // Transform
    ctx.translate(state.transform.x, state.transform.y);
    ctx.scale(state.transform.k, state.transform.k);

    const hasSelection = state.selectedNode !== null;
    const hasPath = state.pathNodes.length > 0;

    // 1. Draw Edges
    state.edges.forEach((e) => {
      const isHighlighted = state.highlightedEdgeIds.has(e.id);
      const isPathEdge = state.pathEdges.some((pe) => (pe.source === e.source && pe.target === e.target) || (pe.source === e.target && pe.target === e.source));

      ctx.beginPath();
      ctx.moveTo(e.source.x, e.source.y);
      ctx.lineTo(e.target.x, e.target.y);

      if (isPathEdge) {
        ctx.strokeStyle = "#f59e0b";
        ctx.lineWidth = 3 / state.transform.k;
        ctx.globalAlpha = 1.0;
      } else if (isHighlighted) {
        ctx.strokeStyle = "#38bdf8";
        ctx.lineWidth = 2 / state.transform.k;
        ctx.globalAlpha = 0.95;
      } else {
        ctx.strokeStyle = "#334155";
        ctx.lineWidth = 1 / state.transform.k;
        ctx.globalAlpha = hasSelection || hasPath ? 0.15 : 0.6;
      }
      ctx.stroke();

      // Render edge label if zoomed in or highlighted
      if ((state.transform.k > 0.8 || isHighlighted || isPathEdge) && (hasSelection ? isHighlighted || isPathEdge : true)) {
        const mx = (e.source.x + e.target.x) / 2;
        const my = (e.source.y + e.target.y) / 2;
        ctx.font = `${Math.max(8, 10 / state.transform.k)}px var(--font-mono)`;
        ctx.fillStyle = isPathEdge ? "#fbbf24" : isHighlighted ? "#7dd3fc" : "#64748b";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(e.type, mx, my - 4);
      }
    });

    // 2. Draw Nodes
    state.nodes.forEach((n) => {
      const isSelected = state.selectedNode === n;
      const isNeighbour = state.highlightedNeighbourIds.has(n.id);
      const isPathNode = state.pathNodes.some((pn) => pn.id === n.id);

      let alphaVal = 1.0;
      if (hasPath) {
        alphaVal = isPathNode ? 1.0 : 0.2;
      } else if (hasSelection) {
        alphaVal = isSelected || isNeighbour ? 1.0 : 0.2;
      }

      ctx.globalAlpha = alphaVal;

      // Outer glow for selected or path node
      if (isSelected || isPathNode) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.radius + 6, 0, Math.PI * 2);
        ctx.fillStyle = isPathNode ? "rgba(245, 158, 11, 0.4)" : "rgba(56, 189, 248, 0.4)";
        ctx.fill();
      }

      // Main Node Circle
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
      ctx.fillStyle = LABEL_COLORS[n.label] || LABEL_COLORS.Entity;
      ctx.fill();

      ctx.strokeStyle = isSelected ? "#ffffff" : isPathNode ? "#fbbf24" : "#0f172a";
      ctx.lineWidth = 2 / state.transform.k;
      ctx.stroke();

      // Node Label text
      const fontSize = Math.max(9, Math.min(14, 11 / state.transform.k));
      ctx.font = `600 ${fontSize}px var(--font-sans)`;
      ctx.fillStyle = isSelected || isPathNode ? "#ffffff" : "#f1f5f9";
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.fillText(n.name, n.x, n.y + n.radius + 3);
    });

    ctx.restore();
  }

  // --- Interactions: Node Selection & Inspection ---
  function selectNode(node) {
    state.selectedNode = node;
    state.pathNodes = [];
    state.pathEdges = [];

    if (!node) {
      state.highlightedNeighbourIds.clear();
      state.highlightedEdgeIds.clear();
      rightPanelTitle.textContent = "Inspector";
      btnClearSelection.style.display = "none";
      inspectorContent.innerHTML = `
        <div class="detail-card">
          <p style="font-size: 12px; color: var(--text-secondary); line-height: 1.5;">
            Click any node in the graph to inspect its properties, degree, and 1-hop neighbourhood.
          </p>
        </div>
      `;
      render();
      return;
    }

    btnClearSelection.style.display = "inline-flex";
    rightPanelTitle.textContent = `${node.label} Inspector`;

    // Find 1-hop neighbours
    const neighbourIds = new Set();
    const edgeIds = new Set();
    const connectedDetails = [];

    state.edges.forEach((e) => {
      if (e.source.id === node.id) {
        neighbourIds.add(e.target.id);
        edgeIds.add(e.id);
        connectedDetails.push({ dir: "out", rel: e.type, target: e.target });
      } else if (e.target.id === node.id) {
        neighbourIds.add(e.source.id);
        edgeIds.add(e.id);
        connectedDetails.push({ dir: "in", rel: e.type, target: e.source });
      }
    });

    state.highlightedNeighbourIds = neighbourIds;
    state.highlightedEdgeIds = edgeIds;

    let neighboursHtml = "";
    connectedDetails.forEach((item) => {
      const arrow = item.dir === "out" ? "→" : "←";
      neighboursHtml += `
        <div class="detail-row" style="cursor: pointer;" data-jump-id="${item.target.id}">
          <span class="detail-label" style="font-family: var(--font-mono); font-size: 11px;">
            ${arrow} [${item.rel}]
          </span>
          <span class="detail-val" style="color: ${LABEL_COLORS[item.target.label] || 'var(--text-primary)'}; font-size: 11px;">
            ${escapeHtml(item.target.name)} (${item.target.label})
          </span>
        </div>
      `;
    });

    inspectorContent.innerHTML = `
      <div class="detail-card">
        <h4 style="font-size: 14px; color: ${LABEL_COLORS[node.label]}; margin-bottom: 6px; display: flex; align-items: center; gap: 6px;">
          <span class="legend-dot" style="background: ${LABEL_COLORS[node.label]};"></span>
          ${escapeHtml(node.name)}
        </h4>
        <div class="detail-row"><span class="detail-label">Label:</span><span class="detail-val">${node.label}</span></div>
        <div class="detail-row"><span class="detail-label">Degree:</span><span class="detail-val">${node.degree} connections</span></div>
        <div class="detail-row"><span class="detail-label">Graph ID:</span><span class="detail-val">${node.id}</span></div>
        <div class="detail-row"><span class="detail-label">Element ID:</span><span class="detail-val">${node.elementId || '—'}</span></div>
      </div>

      <div class="detail-card">
        <label>1-Hop Connected Entities (${connectedDetails.length})</label>
        <div style="max-height: 220px; overflow-y: auto;">
          ${neighboursHtml || '<p style="font-size: 11px; color: var(--text-muted);">No direct relationships.</p>'}
        </div>
      </div>
    `;

    // Click neighbour to jump
    inspectorContent.querySelectorAll("[data-jump-id]").forEach((el) => {
      el.addEventListener("click", () => {
        const targetNode = state.nodeMap.get(el.dataset.jumpId);
        if (targetNode) selectNode(targetNode);
      });
    });

    render();
  }

  // --- Path Mode ---
  function togglePathMode() {
    state.pathMode = !state.pathMode;
    state.pathStartNode = null;
    state.pathNodes = [];
    state.pathEdges = [];

    if (state.pathMode) {
      pathModeBadge.style.display = "block";
      btnTogglePathMode.classList.add("btn-accent");
      btnTogglePathMode.innerHTML = "<span>📍</span> Path Mode (Active - Pick Start Node)";
      pathResultBox.textContent = "Select starting node on the canvas...";
    } else {
      pathModeBadge.style.display = "none";
      btnTogglePathMode.classList.remove("btn-accent");
      btnTogglePathMode.innerHTML = "<span>📍</span> Toggle Path Mode (Pick 2 Nodes)";
      pathResultBox.textContent = "";
      render();
    }
  }

  async function handlePathNodeClick(node) {
    if (!state.pathStartNode) {
      state.pathStartNode = node;
      pathModeBadge.textContent = `Start: ${node.name}. Now click End Node...`;
      pathResultBox.textContent = `Start node: ${node.name} (${node.label}). Click destination node...`;
      state.pathNodes = [node];
      render();
    } else {
      const start = state.pathStartNode;
      const end = node;
      pathModeBadge.textContent = `Computing shortest path ${start.name} ➔ ${end.name}...`;

      try {
        const data = await apiGet(`/api/graph/path?from=${encodeURIComponent(start.id)}&to=${encodeURIComponent(end.id)}`);
        highlightPathResult(start, end, data);
      } catch (err) {
        pathResultBox.innerHTML = `<span style="color: var(--danger);">No path found between ${start.name} and ${end.name}.</span>`;
        state.pathStartNode = null;
      }
    }
  }

  function highlightPathResult(startNode, endNode, pathData) {
    state.pathNodes = [];
    state.pathEdges = [];
    const steps = pathData.path || [];

    // Map names to node objects
    const nameMap = new Map();
    state.nodes.forEach((n) => nameMap.set(n.name, n));

    const pathNodesList = [];
    steps.forEach((step, idx) => {
      const u = nameMap.get(step.from);
      const v = nameMap.get(step.to);
      if (u && !pathNodesList.includes(u)) pathNodesList.push(u);
      if (v && !pathNodesList.includes(v)) pathNodesList.push(v);
      if (u && v) {
        state.pathEdges.push({ source: u, target: v, type: step.type });
      }
    });

    state.pathNodes = pathNodesList;

    let pathHtml = `
      <div class="alert alert-success">
        <strong>Path Found!</strong> ${pathData.length} hop(s)
      </div>
      <div style="font-size: 12px; line-height: 1.6; margin-top: 6px;">
    `;

    steps.forEach((step, idx) => {
      pathHtml += `
        <div style="margin-bottom: 4px;">
          ${idx + 1}. <strong>${escapeHtml(step.from)}</strong>
          <span style="font-family: var(--font-mono); color: var(--accent-amber); font-size: 11px;">-[${step.type}]➔</span>
          <strong>${escapeHtml(step.to)}</strong>
        </div>
      `;
    });
    pathHtml += `</div>`;

    pathResultBox.innerHTML = pathHtml;
    pathModeBadge.textContent = `Path Found: ${startNode.name} ➔ ${endNode.name} (${pathData.length} hops)`;

    // Show path in Inspector
    rightPanelTitle.textContent = "Shortest Path Result";
    btnClearSelection.style.display = "inline-flex";
    inspectorContent.innerHTML = `
      <div class="detail-card">
        <h4 style="font-size: 13px; color: var(--accent-amber); margin-bottom: 6px;">
          Shortest Path (${pathData.length} hops)
        </h4>
        <div class="detail-row"><span class="detail-label">Start:</span><span class="detail-val">${startNode.name}</span></div>
        <div class="detail-row"><span class="detail-label">Target:</span><span class="detail-val">${endNode.name}</span></div>
      </div>
      <div class="detail-card">
        <label>Traversed Sequence</label>
        ${pathHtml}
      </div>
    `;

    render();
  }

  function focusNodeByName(name) {
    const target = state.nodes.find((n) => n.name.toLowerCase() === name.toLowerCase());
    if (target) {
      selectNode(target);
      // Center camera
      const rect = canvasContainer.getBoundingClientRect();
      state.transform.x = rect.width / 2 - target.x * state.transform.k;
      state.transform.y = rect.height / 2 - target.y * state.transform.k;
      render();
    }
  }

  // --- Canvas Mouse & Touch Handlers ---
  function screenToWorld(sx, sy) {
    return {
      x: (sx - state.transform.x) / state.transform.k,
      y: (sy - state.transform.y) / state.transform.k,
    };
  }

  function findNodeAt(x, y) {
    for (let i = state.nodes.length - 1; i >= 0; i--) {
      const n = state.nodes[i];
      const dist = Math.hypot(n.x - x, n.y - y);
      if (dist <= n.radius + 3) return n;
    }
    return null;
  }

  canvas.addEventListener("mousedown", (ev) => {
    const rect = canvas.getBoundingClientRect();
    const mouseX = ev.clientX - rect.left;
    const mouseY = ev.clientY - rect.top;
    const world = screenToWorld(mouseX, mouseY);
    const clickedNode = findNodeAt(world.x, world.y);

    if (clickedNode) {
      if (state.pathMode) {
        handlePathNodeClick(clickedNode);
        return;
      }
      state.isDraggingNode = true;
      state.draggedNode = clickedNode;
      selectNode(clickedNode);
    } else {
      state.isPanning = true;
      state.panStart = { x: ev.clientX - state.transform.x, y: ev.clientY - state.transform.y };
    }
  });

  window.addEventListener("mousemove", (ev) => {
    if (state.isDraggingNode && state.draggedNode) {
      const rect = canvas.getBoundingClientRect();
      const mouseX = ev.clientX - rect.left;
      const mouseY = ev.clientY - rect.top;
      const world = screenToWorld(mouseX, mouseY);
      state.draggedNode.x = world.x;
      state.draggedNode.y = world.y;
      state.draggedNode.vx = 0;
      state.draggedNode.vy = 0;
      alpha = 0.3; // Wake up physics slightly
      render();
    } else if (state.isPanning) {
      state.transform.x = ev.clientX - state.panStart.x;
      state.transform.y = ev.clientY - state.panStart.y;
      render();
    }
  });

  window.addEventListener("mouseup", () => {
    state.isDraggingNode = false;
    state.draggedNode = null;
    state.isPanning = false;
  });

  canvas.addEventListener("wheel", (ev) => {
    ev.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const mouseX = ev.clientX - rect.left;
    const mouseY = ev.clientY - rect.top;
    const zoomFactor = ev.deltaY < 0 ? 1.1 : 0.9;
    const newK = Math.max(0.15, Math.min(4.0, state.transform.k * zoomFactor));

    // Zoom centered on cursor
    state.transform.x = mouseX - (mouseX - state.transform.x) * (newK / state.transform.k);
    state.transform.y = mouseY - (mouseY - state.transform.y) * (newK / state.transform.k);
    state.transform.k = newK;

    render();
  }, { passive: false });

  // --- Event Listeners Setup ---
  function setupEventListeners() {
    // Tabs
    document.querySelectorAll(".nav-tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        document.querySelectorAll(".nav-tab").forEach((t) => t.classList.remove("active"));
        document.querySelectorAll(".tab-pane").forEach((p) => p.classList.remove("active"));
        tab.classList.add("active");
        const targetPane = document.getElementById(tab.dataset.tab);
        if (targetPane) targetPane.classList.add("active");
        state.activeTab = tab.dataset.tab;
      });
    });

    // Zoom & Reset buttons
    btnZoomIn.addEventListener("click", () => {
      state.transform.k = Math.min(4.0, state.transform.k * 1.25);
      render();
    });
    btnZoomOut.addEventListener("click", () => {
      state.transform.k = Math.max(0.15, state.transform.k * 0.8);
      render();
    });
    btnResetView.addEventListener("click", () => {
      const rect = canvasContainer.getBoundingClientRect();
      state.transform = { x: rect.width / 2, y: rect.height / 2, k: 1 };
      render();
    });

    // Path mode toggle
    btnTogglePathMode.addEventListener("click", togglePathMode);

    // Clear selection
    btnClearSelection.addEventListener("click", () => selectNode(null));

    // Label filters
    labelCheckboxes.forEach((cb) => {
      cb.addEventListener("change", () => fetchGraphData());
    });

    // Node search
    nodeSearchInput.addEventListener("input", () => {
      const q = nodeSearchInput.value.trim().toLowerCase();
      if (!q) {
        selectNode(null);
        return;
      }
      const match = state.nodes.find((n) => n.name.toLowerCase().includes(q));
      if (match) {
        selectNode(match);
      }
    });

    // Ingest Button
    btnIngest.addEventListener("click", async () => {
      const title = docTitle.value.trim();
      const text = docText.value.trim();
      const file = fileUpload.files[0];

      if (!text && !file) {
        alert("Please paste text or select a file to ingest.");
        return;
      }

      btnIngest.disabled = true;
      btnIngest.textContent = "Ingesting...";
      ingestFeedback.style.display = "block";
      ingestFeedback.className = "alert alert-success";
      ingestFeedback.textContent = "Extracting entities & building graph...";

      try {
        let res;
        if (file) {
          const formData = new FormData();
          formData.append("file", file);
          const uploadRes = await fetch("/api/documents/upload", { method: "POST", body: formData });
          if (!uploadRes.ok) throw new Error(await uploadRes.text());
          res = await uploadRes.json();
        } else {
          res = await apiPost("/api/documents", { title: title || "Untitled Note", text: text, source: "paste" });
        }

        ingestFeedback.innerHTML = `
          <strong>Ingestion Successful!</strong><br>
          Created ${res.chunks_created} chunk(s), ${res.entities_found} entities, and ${res.relationships_created} relationship(s).
        `;
        docTitle.value = "";
        docText.value = "";
        fileUpload.value = "";
        refreshAll();
      } catch (err) {
        ingestFeedback.className = "alert alert-error";
        ingestFeedback.textContent = "Ingestion failed: " + err.message;
      } finally {
        btnIngest.disabled = false;
        btnIngest.innerHTML = "<span>📥</span> Extract & Ingest Note";
      }
    });

    // Ask Button
    btnAsk.addEventListener("click", async () => {
      const q = askInput.value.trim();
      if (!q) return;

      btnAsk.disabled = true;
      btnAsk.textContent = "Querying Graph...";
      askResultContainer.innerHTML = `<p style="font-size: 11px; color: var(--text-muted); margin-top: 10px;">Traversing knowledge graph & citing evidence...</p>`;

      try {
        const res = await apiPost("/api/ask", { question: q });
        renderAskResult(res);
      } catch (err) {
        askResultContainer.innerHTML = `<div class="alert alert-error" style="margin-top: 10px;">${escapeHtml(err.message)}</div>`;
      } finally {
        btnAsk.disabled = false;
        btnAsk.innerHTML = "<span>✨</span> Ask GraphLens";
      }
    });

    // Prompt Chips in Ask
    document.querySelectorAll(".prompt-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        askInput.value = chip.textContent.trim();
        btnAsk.click();
      });
    });

    // Demo Data Seeding & Reset
    btnLoadDemo.addEventListener("click", async () => {
      btnLoadDemo.disabled = true;
      try {
        const res = await apiPost("/api/demo/seed", {});
        alert(`Demo data loaded successfully!\n${res.documents} docs, ${res.entities} entities, ${res.relationships} relationships, ${res.steps} steps.`);
        refreshAll();
      } catch (err) {
        alert("Failed to load demo data: " + err.message);
      } finally {
        btnLoadDemo.disabled = false;
      }
    });

    btnResetDemo.addEventListener("click", async () => {
      if (confirm("Reset will wipe the graph database and re-seed clean demo data. Continue?")) {
        btnResetDemo.disabled = true;
        try {
          const res = await apiPost("/api/demo/reset", {});
          alert(`Graph store reset and reseeded!\n${res.documents} docs, ${res.entities} entities, ${res.relationships} relationships.`);
          refreshAll();
        } catch (err) {
          alert("Failed to reset store: " + err.message);
        } finally {
          btnResetDemo.disabled = false;
        }
      }
    });

    // Export Store
    btnExportStore.addEventListener("click", () => {
      window.location.href = "/api/store/export";
    });

    // Cypher Console
    cypherHeaderToggle.addEventListener("click", () => {
      cypherBar.classList.toggle("collapsed");
      cypherToggleIcon.textContent = cypherBar.classList.contains("collapsed") ? "▲" : "▼";
    });

    // Example query chips
    document.querySelectorAll(".query-chip").forEach((chip) => {
      chip.addEventListener("click", (e) => {
        e.stopPropagation();
        cypherInput.value = chip.dataset.q;
        runCypherConsole();
      });
    });

    btnRunCypher.addEventListener("click", runCypherConsole);
  }

  function renderAskResult(res) {
    let citationsHtml = "";
    (res.citations || []).forEach((c) => {
      citationsHtml += `<span class="citation-chip" title="Score: ${c.score}">${escapeHtml(c.path)}</span> `;
    });

    let evidenceHtml = "";
    (res.evidence_chunks || []).forEach((chunk) => {
      evidenceHtml += `
        <div style="background: rgba(15, 23, 42, 0.6); padding: 6px; border-radius: 4px; margin-top: 4px; font-size: 11px;">
          <span style="color: var(--accent-cyan); font-weight: 600;">[Score: ${chunk.score}]</span> ${escapeHtml(chunk.text)}
        </div>
      `;
    });

    const answerCardHtml = `
      <div class="answer-box">
        <div style="font-weight: 700; font-size: 11px; color: var(--accent-cyan); margin-bottom: 4px;">GRAPH-GROUNDED ANSWER</div>
        <div class="answer-text">${escapeHtml(res.answer)}</div>
        ${citationsHtml ? `<div style="margin-top: 8px;"><label style="margin-bottom: 2px;">Citations:</label>${citationsHtml}</div>` : ""}
        
        <div class="expander" id="expanderTrace">
          <span>▶ Why this answer? (Inspect Evidence &amp; Cypher)</span>
        </div>
        <div class="expander-content" id="expanderContentTrace">
          <div style="color: var(--accent-amber); font-weight: 600; margin-bottom: 2px;">Cypher Query:</div>
          <div style="margin-bottom: 8px; color: #7dd3fc;">${escapeHtml(res.cypher_used || 'N/A')}</div>
          ${evidenceHtml ? `<div style="color: var(--accent-purple); font-weight: 600; margin-bottom: 2px;">Evidence Chunks:</div>${evidenceHtml}` : ""}
        </div>
      </div>
    `;

    askResultContainer.innerHTML = answerCardHtml;

    // Toggle expander
    const expBtn = document.getElementById("expanderTrace");
    const expContent = document.getElementById("expanderContentTrace");
    if (expBtn && expContent) {
      expBtn.addEventListener("click", () => {
        const isHidden = expContent.style.display === "none" || !expContent.style.display;
        expContent.style.display = isHidden ? "block" : "none";
        expBtn.querySelector("span").textContent = isHidden
          ? "▼ Why this answer? (Hide Evidence)"
          : "▶ Why this answer? (Inspect Evidence & Cypher)";
      });
    }

    // Also show in Right Inspector for maximum prominence
    rightPanelTitle.textContent = "Answer & Grounding";
    btnClearSelection.style.display = "inline-flex";
    inspectorContent.innerHTML = `
      <div class="detail-card">
        <h4 style="font-size: 13px; color: var(--accent-cyan); margin-bottom: 6px;">Grounding Analysis</h4>
        ${answerCardHtml}
      </div>
    `;
  }

  async function runCypherConsole() {
    const q = cypherInput.value.trim();
    if (!q) return;

    btnRunCypher.disabled = true;
    btnRunCypher.textContent = "Running...";
    cypherElapsedBadge.style.display = "none";
    cypherResultSection.style.display = "block";
    cypherResultOutput.innerHTML = `<span style="font-size: 11px; color: var(--text-muted);">Executing on Relate...</span>`;

    try {
      const res = await apiPost("/api/graph/query", {
        cypher: q,
        params: {},
        confirm: confirmDestructive.checked,
      });

      cypherElapsedBadge.textContent = `${res.elapsed_ms} ms`;
      cypherElapsedBadge.style.display = "inline-block";
      resultCountInfo.textContent = `${res.rows.length} row(s)`;

      renderCypherOutput(res);

      // Refresh graph if query might have mutated the graph
      if (q.toUpperCase().includes("CREATE") || q.toUpperCase().includes("DELETE") || q.toUpperCase().includes("MERGE")) {
        refreshAll();
      }
    } catch (err) {
      cypherResultOutput.innerHTML = `<div class="alert alert-error">${escapeHtml(err.message)}</div>`;
    } finally {
      btnRunCypher.disabled = false;
      btnRunCypher.innerHTML = "<span>▶</span> Execute";
    }
  }

  function renderCypherOutput(res) {
    if (!res.rows || res.rows.length === 0) {
      cypherResultOutput.innerHTML = `<p style="font-size: 11px; color: var(--text-muted);">Query returned 0 rows. (Execution: ${res.elapsed_ms} ms)</p>`;
      return;
    }

    const cols = res.columns.length > 0 ? res.columns : Object.keys(res.rows[0]);
    let tableHtml = `<table class="results-table"><thead><tr>`;
    cols.forEach((c) => {
      tableHtml += `<th>${escapeHtml(c)}</th>`;
    });
    tableHtml += `</tr></thead><tbody>`;

    res.rows.forEach((row) => {
      tableHtml += `<tr>`;
      cols.forEach((c) => {
        const val = row[c] !== undefined ? row[c] : "";
        const valStr = typeof val === "object" ? JSON.stringify(val) : String(val);
        tableHtml += `<td>${escapeHtml(valStr)}</td>`;
      });
      tableHtml += `</tr>`;
    });
    tableHtml += `</tbody></table>`;

    cypherResultOutput.innerHTML = tableHtml;
  }

  function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Run on DOM loaded
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
