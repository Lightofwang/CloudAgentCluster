(function () {
  "use strict";

  let lastPitchText = "";

  async function loadTracks() {
    const select = document.getElementById("track-select");
    try {
      const resp = await fetch("/api/tracks");
      const data = await resp.json();
      select.innerHTML = (data.tracks || [])
        .map((t) => `<option value="${t.id}">${t.name} (${t.focus})</option>`)
        .join("");
    } catch (err) {
      select.innerHTML = '<option value="ai-agents">AI Agents & Autonomous Workflows</option>';
    }
  }

  function renderResult(data) {
    document.getElementById("empty-hint").style.display = "none";
    document.getElementById("result-view").style.display = "block";
    document.getElementById("btn-copy-pitch").style.display = "inline-block";

    document.getElementById("overall-score").textContent = String(data.overall_score);
    document.getElementById("track-badge").textContent = data.track_name;

    const dimLabels = {
      innovation: "创新性 (Innovation)",
      feasibility: "可行性 (Feasibility)",
      demo_readiness: "演示度 (Demo Readiness)",
      track_fit: "赛道契合 (Track Fit)",
    };

    const dimGrid = document.getElementById("dimensions-grid");
    dimGrid.innerHTML = Object.entries(data.dimensions || {})
      .map(
        ([k, v]) => `
        <div class="dim-item">
          <div class="dim-top"><span>${dimLabels[k] || k}</span><strong>${v}</strong></div>
          <div class="bar-bg"><div class="bar-fill" style="width:${v}%"></div></div>
        </div>
      `
      )
      .join("");

    document.getElementById("arch-list").innerHTML = (data.architecture_modules || [])
      .map(
        (m) => `
        <div class="arch-card">
          <strong>[${m.priority}] ${m.layer} · ${m.module}</strong>
          <div class="muted" style="margin-top:4px;">${m.reason}</div>
        </div>
      `
      )
      .join("");

    document.getElementById("risk-list").innerHTML = (data.risk_warnings || [])
      .map((r) => `<li>${r}</li>`)
      .join("");

    const pitches = data.pitch_outline || [];
    document.getElementById("pitch-list").innerHTML = pitches
      .map(
        (p) => `
        <div class="pitch-card">
          <strong>${p.section}</strong>
          <div style="margin-top:4px;color:#cbd5e1;">${p.talking_point}</div>
        </div>
      `
      )
      .join("");

    lastPitchText = pitches.map((p) => `${p.section}\n${p.talking_point}`).join("\n\n");
  }

  document.addEventListener("DOMContentLoaded", () => {
    loadTracks();

    document.getElementById("btn-sample")?.addEventListener("click", () => {
      document.getElementById("project-name").value = "CloudAgentCluster Autonomous Hub";
      document.getElementById("track-select").value = "ai-agents";
      document.getElementById("team-size").value = "2";
      document.getElementById("tech-stack").value = "Python API, Web Dashboard, AI Agent, Unittest";
      document.getElementById("problem-statement").value =
        "解决个人开发者在周末无法全天候盯盘 Hackathon 比赛、并自动生成工程规范与全栈参赛 Demo 的效率瓶颈。";
    });

    document.getElementById("analyze-form")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const errBox = document.getElementById("error-box");
      errBox.style.display = "none";

      const payload = {
        project_name: document.getElementById("project-name").value.trim(),
        track: document.getElementById("track-select").value,
        team_size: parseInt(document.getElementById("team-size").value || "2", 10),
        tech_stack: document.getElementById("tech-stack").value,
        problem_statement: document.getElementById("problem-statement").value.trim(),
      };

      try {
        const resp = await fetch("/api/analyze", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || "分析失败");
        renderResult(data);
      } catch (err) {
        errBox.textContent = err.message;
        errBox.style.display = "block";
      }
    });

    document.getElementById("btn-copy-pitch")?.addEventListener("click", () => {
      if (lastPitchText) {
        navigator.clipboard?.writeText(lastPitchText);
        document.getElementById("btn-copy-pitch").textContent = "已复制 ✓";
        setTimeout(() => {
          document.getElementById("btn-copy-pitch").textContent = "复制 Pitch 提纲";
        }, 2000);
      }
    });
  });
})();
