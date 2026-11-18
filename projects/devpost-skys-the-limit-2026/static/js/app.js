/**
 * DraftLens Frontend Application Logic
 */

let state = {
  currentRoute: "overview",
  teams: [],
  champions: [],
  currentDraft: null,
  draftRecommendations: [],
  draftRoleFilter: "ALL",
  draftSearchQuery: "",
  activeTeamModal: null,
};

// -------------------------------------------------------------
// Router
// -------------------------------------------------------------
function navigate(route) {
  state.currentRoute = route;
  window.location.hash = route;

  document.querySelectorAll(".nav-link").forEach((link) => {
    link.classList.toggle("active", link.dataset.route === route);
  });

  document.querySelectorAll(".view-section").forEach((sec) => {
    sec.classList.toggle("active", sec.id === `view-${route}`);
  });

  if (route === "overview") loadOverview();
  if (route === "teams") loadTeams();
  if (route === "scout") setupScoutView();
  if (route === "draft") renderDraftView();
  if (route === "history") loadHistoryView();
}

window.addEventListener("hashchange", () => {
  const hash = window.location.hash.replace("#", "") || "overview";
  if (hash !== state.currentRoute) {
    navigate(hash);
  }
});

// -------------------------------------------------------------
// Data Init
// -------------------------------------------------------------
async function initApp() {
  try {
    const [teams, champions] = await Promise.all([
      api.getTeams(),
      api.getChampions(),
    ]);
    state.teams = teams;
    state.champions = champions;

    populateTeamSelects();
    const hash = window.location.hash.replace("#", "") || "overview";
    navigate(hash);
  } catch (err) {
    console.error("Initialization error:", err);
  }
}

function populateTeamSelects() {
  const scoutSelect = document.getElementById("scout-team-select");
  const blueSelect = document.getElementById("draft-blue-team");
  const redSelect = document.getElementById("draft-red-team");

  if (!scoutSelect || !blueSelect || !redSelect) return;

  const options = state.teams
    .map((t) => `<option value="${t.id}">${t.name} (${t.style})</option>`)
    .join("");

  scoutSelect.innerHTML = options;
  blueSelect.innerHTML = options;
  redSelect.innerHTML = options;

  if (state.teams.length > 1) {
    redSelect.selectedIndex = 1;
  }
}

// -------------------------------------------------------------
// View 1: Overview
// -------------------------------------------------------------
async function loadOverview() {
  try {
    const matches = await api.getMatches("", 10);

    document.getElementById("stat-teams").innerText = state.teams.length || 8;
    document.getElementById("stat-champions").innerText = state.champions.length || 60;
    document.getElementById("stat-matches").innerText = 120;
    document.getElementById("stat-series").innerText = state.currentDraft ? 1 : 0;

    const tbody = document.getElementById("overview-matches-tbody");
    if (!tbody) return;

    tbody.innerHTML = matches
      .map((m) => {
        const team = state.teams.find((t) => t.id === m.team_id) || { name: m.team_id };
        const opp = state.teams.find((t) => t.id === m.opponent_id) || { name: m.opponent_id };
        const isWin = m.result === "win";
        const objs = m.objectives || {};

        return `
        <tr>
          <td>${m.played_at || "-"}</td>
          <td><strong>${team.name}</strong></td>
          <td>${opp.name}</td>
          <td><span class="badge ${isWin ? "badge-green" : "badge-red"}">${isWin ? "胜" : "负"}</span></td>
          <td>${m.duration_minutes} 分钟</td>
          <td>🐉 ${objs.dragons || 0} / 👾 ${objs.barons || 0}</td>
        </tr>
      `;
      })
      .join("");
  } catch (err) {
    console.error(err);
  }
}

// -------------------------------------------------------------
// View 2: Teams
// -------------------------------------------------------------
async function loadTeams(filterStyle = "") {
  try {
    const teams = await api.getTeams(filterStyle);
    const container = document.getElementById("teams-grid-container");
    if (!container) return;

    container.innerHTML = teams
      .map(
        (t) => `
      <div class="team-card" onclick="openTeamModal('${t.id}')">
        <div class="team-card-header">
          <div>
            <div class="team-name">${t.name}</div>
            <div class="team-region">${t.region}</div>
          </div>
          <span class="badge badge-blue">${t.style}</span>
        </div>
        <div style="font-size: 13px; color: var(--text-muted); display: flex; flex-direction: column; gap: 4px;">
          <div>胜率：<strong style="color: var(--text-main);">${Math.round(t.win_rate * 100)}%</strong></div>
          <div>场均时长：${t.avg_game_minutes} 分钟</div>
          <div>一血率：${Math.round(t.first_blood_rate * 100)}% | 场均视野：${t.avg_vision_score}</div>
          <div style="margin-top: 6px; font-size: 12px; color: var(--accent);">点击查看选手名单与近况 ➔</div>
        </div>
      </div>
    `
      )
      .join("");
  } catch (err) {
    console.error(err);
  }
}

async function openTeamModal(teamId) {
  try {
    const team = await api.getTeamDetail(teamId);
    state.activeTeamModal = team;

    document.getElementById("modal-team-name").innerText = `${team.name} (${team.style})`;
    document.getElementById("modal-team-stats").innerText = `胜率 ${Math.round(team.win_rate * 100)}% | 场均时长 ${team.avg_game_minutes}m | 视野分 ${team.avg_vision_score}`;

    const playersTbody = document.getElementById("modal-players-tbody");
    playersTbody.innerHTML = (team.players || [])
      .map(
        (p) => `
      <tr>
        <td><span class="badge badge-blue">${p.role}</span></td>
        <td><strong>${p.name}</strong></td>
        <td>${p.kda}</td>
        <td>${(p.champion_pool || []).map((c) => c.champion_id).join(", ")}</td>
        <td><span class="badge badge-gold">${p.recent_form}</span></td>
      </tr>
    `
      )
      .join("");

    document.getElementById("team-detail-modal").classList.add("active");
  } catch (err) {
    console.error(err);
  }
}

function closeTeamModal() {
  document.getElementById("team-detail-modal").classList.remove("active");
}

// -------------------------------------------------------------
// View 3: Macro Scouting Report
// -------------------------------------------------------------
function setupScoutView() {
  if (state.teams.length > 0) {
    const scoutSelect = document.getElementById("scout-team-select");
    if (scoutSelect && !scoutSelect.value) {
      scoutSelect.value = state.teams[0].id;
    }
  }
}

async function fetchScoutReport() {
  const teamId = document.getElementById("scout-team-select").value;
  const matchesCount = parseInt(document.getElementById("scout-matches-count").value, 10) || 5;

  if (!teamId) {
    showToast("请先选择要侦察的战队", "error");
    return;
  }

  try {
    const report = await api.getScoutReport(teamId, matchesCount);
    renderScoutReport(report);
    showToast(`成功生成 ${report.team_name} 宏观侦察报告`, "success");
  } catch (err) {
    console.error(err);
  }
}

function renderScoutReport(report) {
  document.getElementById("scout-result-panel").style.display = "block";
  document.getElementById("scout-summary-text").innerText = report.style_summary || "暂无风格总结";

  document.getElementById("scout-stat-gold15").innerText = `${report.gold_diff_at_15 > 0 ? "+" : ""}${report.gold_diff_at_15}`;
  document.getElementById("scout-stat-gold15").style.color = report.gold_diff_at_15 >= 0 ? "var(--success)" : "var(--danger)";

  document.getElementById("scout-stat-vision").innerText = report.avg_vision_score;
  document.getElementById("scout-stat-fb").innerText = `${Math.round(report.first_blood_rate * 100)}%`;
  document.getElementById("scout-stat-analyzed").innerText = `${report.matches_analyzed} 场`;

  // Objective bars
  const objs = report.objective_rates || {};
  document.getElementById("bar-dragon").style.width = `${Math.round((objs.dragon || 0) * 100)}%`;
  document.getElementById("label-dragon").innerText = `${Math.round((objs.dragon || 0) * 100)}%`;

  document.getElementById("bar-herald").style.width = `${Math.round((objs.herald || 0) * 100)}%`;
  document.getElementById("label-herald").innerText = `${Math.round((objs.herald || 0) * 100)}%`;

  document.getElementById("bar-baron").style.width = `${Math.round((objs.baron || 0) * 100)}%`;
  document.getElementById("label-baron").innerText = `${Math.round((objs.baron || 0) * 100)}%`;

  // Draw Gold Diff Canvas Chart
  drawGoldDiffCurve(report.gold_diff_curve || []);

  // Champion Preferences
  const prefTbody = document.getElementById("scout-prefs-tbody");
  prefTbody.innerHTML = (report.champion_preferences || [])
    .map(
      (c) => `
    <tr>
      <td><span class="badge badge-blue">${c.role}</span></td>
      <td><strong>${c.champion}</strong></td>
      <td>${Math.round(c.pick_rate * 100)}%</td>
      <td><div style="width: 120px; background: #23314d; height: 6px; border-radius: 3px; overflow: hidden;"><div style="width: ${Math.round(c.pick_rate * 100)}%; background: var(--accent); height: 100%;"></div></div></td>
    </tr>
  `
    )
    .join("");
}

function drawGoldDiffCurve(curveData) {
  const canvas = document.getElementById("gold-diff-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;

  ctx.clearRect(0, 0, width, height);

  if (!curveData || curveData.length === 0) {
    ctx.fillStyle = "#64748b";
    ctx.font = "14px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("暂无经济曲线数据", width / 2, height / 2);
    return;
  }

  const padding = 40;
  const zeroY = height / 2;

  // Draw Zero Line
  ctx.strokeStyle = "#334155";
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  ctx.moveTo(padding, zeroY);
  ctx.lineTo(width - padding, zeroY);
  ctx.stroke();
  ctx.setLineDash([]);

  // Labels for Zero
  ctx.fillStyle = "#64748b";
  ctx.font = "11px sans-serif";
  ctx.textAlign = "right";
  ctx.fillText("0 差额", padding - 6, zeroY + 4);

  const maxDiff = Math.max(
    2000,
    ...curveData.map((d) => Math.abs(d.diff))
  );

  const points = curveData.map((pt, idx) => {
    const x = padding + (idx / Math.max(1, curveData.length - 1)) * (width - 2 * padding);
    const y = zeroY - (pt.diff / maxDiff) * (height / 2 - padding);
    return { x, y, diff: pt.diff, minute: pt.minute };
  });

  // Draw filled area
  ctx.beginPath();
  ctx.moveTo(points[0].x, zeroY);
  points.forEach((p) => ctx.lineTo(p.x, p.y));
  ctx.lineTo(points[points.length - 1].x, zeroY);
  ctx.closePath();

  const isLeading = points[points.length - 1].diff >= 0;
  const grad = ctx.createLinearGradient(0, 0, 0, height);
  if (isLeading) {
    grad.addColorStop(0, "rgba(16, 185, 129, 0.25)");
    grad.addColorStop(1, "rgba(16, 185, 129, 0.0)");
  } else {
    grad.addColorStop(0, "rgba(239, 68, 68, 0.0)");
    grad.addColorStop(1, "rgba(239, 68, 68, 0.25)");
  }
  ctx.fillStyle = grad;
  ctx.fill();

  // Draw line
  ctx.beginPath();
  ctx.strokeStyle = isLeading ? "#10b981" : "#ef4444";
  ctx.lineWidth = 3;
  points.forEach((p, idx) => {
    if (idx === 0) ctx.moveTo(p.x, p.y);
    else ctx.lineTo(p.x, p.y);
  });
  ctx.stroke();

  // Draw point circles & minute labels
  points.forEach((p) => {
    ctx.beginPath();
    ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
    ctx.fillStyle = "#fff";
    ctx.fill();
    ctx.strokeStyle = isLeading ? "#10b981" : "#ef4444";
    ctx.lineWidth = 2;
    ctx.stroke();

    // Text diff
    ctx.fillStyle = p.diff >= 0 ? "#34d399" : "#f87171";
    ctx.font = "bold 11px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(`${p.diff > 0 ? "+" : ""}${p.diff}`, p.x, p.y - 10);

    // Minute label
    ctx.fillStyle = "#94a3b8";
    ctx.font = "11px sans-serif";
    ctx.fillText(`${p.minute}m`, p.x, zeroY + 18);
  });
}

// -------------------------------------------------------------
// View 4: Fearless Draft Simulator
// -------------------------------------------------------------
async function startNewDraft() {
  const blueId = document.getElementById("draft-blue-team").value;
  const redId = document.getElementById("draft-red-team").value;
  const seriesType = document.getElementById("draft-series-type").value;

  if (blueId === redId) {
    showToast("红蓝双方不能选择同一支战队", "error");
    return;
  }

  try {
    const draft = await api.createDraft(blueId, redId, seriesType);
    state.currentDraft = draft;
    showToast(`选角系列赛 (${seriesType}) 创建成功！`, "success");
    renderDraftView();
    fetchDraftRecommendations();
  } catch (err) {
    console.error(err);
  }
}

async function renderDraftView() {
  const draft = state.currentDraft;
  const activeContainer = document.getElementById("draft-active-container");
  const emptyNotice = document.getElementById("draft-empty-notice");

  if (!draft) {
    if (activeContainer) activeContainer.style.display = "none";
    if (emptyNotice) emptyNotice.style.display = "block";
    return;
  }

  if (emptyNotice) emptyNotice.style.display = "none";
  if (activeContainer) activeContainer.style.display = "block";

  // Header info
  document.getElementById("draft-blue-name").innerText = draft.blue_team_name;
  document.getElementById("draft-red-name").innerText = draft.red_team_name;
  document.getElementById("draft-score-display").innerText = `${draft.blue_score} : ${draft.red_score}`;
  document.getElementById("draft-series-meta").innerText = `${draft.series_type} · Game ${draft.current_game}`;

  // Current turn banner
  const turnBanner = document.getElementById("draft-turn-banner");
  const turnPulse = document.getElementById("turn-pulse");
  const turnText = document.getElementById("turn-label-text");
  const nextGameBtn = document.getElementById("next-game-btn-container");

  if (draft.game_completed) {
    turnBanner.className = "turn-banner";
    turnPulse.style.display = "none";
    turnText.innerText = `本局选角完成！请结算胜者并进入下一局`;
    nextGameBtn.style.display = "flex";
  } else if (draft.current_turn) {
    nextGameBtn.style.display = "none";
    const ct = draft.current_turn;
    turnPulse.style.display = "block";
    turnBanner.className = `turn-banner ${ct.side === "blue" ? "blue-active" : "red-active"}`;
    turnPulse.style.backgroundColor = ct.side === "blue" ? "var(--blue-team)" : "var(--red-team)";
    turnText.innerText = `轮次 ${ct.index + 1}/20: ${ct.label}`;
  }

  // Render Slots
  const currGame = draft.games[draft.games.length - 1];
  renderBanSlots("blue-bans-row", currGame.blue_bans, 5);
  renderBanSlots("red-bans-row", currGame.red_bans, 5);
  renderPickSlots("blue-picks-list", currGame.blue_picks, "blue");
  renderPickSlots("red-picks-list", currGame.red_picks, "red");

  // Render Fearless Strip
  renderFearlessLockedStrip(draft.series_picked_champions || []);

  // Render Champions Pool
  renderChampionsPool();
}

function renderBanSlots(containerId, bansList, count) {
  const container = document.getElementById(containerId);
  if (!container) return;
  let html = "";
  for (let i = 0; i < count; i++) {
    const ban = bansList[i];
    if (ban) {
      html += `<div class="ban-slot filled" title="${ban.champion_name}">${ban.champion_name}</div>`;
    } else {
      html += `<div class="ban-slot">Ban ${i + 1}</div>`;
    }
  }
  container.innerHTML = html;
}

function renderPickSlots(containerId, picksList, side) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const roles = ["TOP", "JUG", "MID", "ADC", "SUP"];
  let html = "";
  for (let i = 0; i < 5; i++) {
    const pick = picksList[i];
    if (pick) {
      const champ = state.champions.find((c) => c.id === pick.champion_id) || {};
      const color = champ.avatar_color || (side === "blue" ? "#3b82f6" : "#ef4444");
      html += `
        <div class="pick-slot filled ${side}">
          <div class="slot-avatar" style="background-color: ${color};">${champ.name ? champ.name.substring(0, 2) : "P"}</div>
          <div class="slot-info">
            <div class="slot-champ-name">${pick.champion_name}</div>
            <div class="slot-role-label">${pick.role || roles[i]}</div>
          </div>
        </div>
      `;
    } else {
      html += `
        <div class="pick-slot">
          <div class="slot-avatar" style="background-color: #23314d; color: #64748b;">${i + 1}</div>
          <div class="slot-info">
            <div class="slot-champ-name" style="color: var(--text-dim); font-size: 13px;">等待 Pick</div>
            <div class="slot-role-label">${roles[i]}</div>
          </div>
        </div>
      `;
    }
  }
  container.innerHTML = html;
}

function renderFearlessLockedStrip(seriesPicked) {
  const strip = document.getElementById("fearless-locked-strip");
  const countBadge = document.getElementById("fearless-locked-count");
  if (!strip) return;

  if (countBadge) countBadge.innerText = `${seriesPicked.length} 位`;

  if (seriesPicked.length === 0) {
    strip.innerHTML = `<span style="font-size: 12px; color: var(--text-dim);">当前第 1 局，尚未有全局锁定英雄。</span>`;
    return;
  }

  strip.innerHTML = seriesPicked
    .map((cid) => {
      const champ = state.champions.find((c) => c.id === cid) || { name: cid };
      return `<span class="badge badge-red" style="font-size: 11px;">🔒 ${champ.name}</span>`;
    })
    .join(" ");
}

function setDraftRoleFilter(role) {
  state.draftRoleFilter = role;
  document.querySelectorAll(".role-tab-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.role === role);
  });
  renderChampionsPool();
}

function onDraftSearchInput(val) {
  state.draftSearchQuery = val.trim().toLowerCase();
  renderChampionsPool();
}

function renderChampionsPool() {
  const container = document.getElementById("champions-pool-grid");
  if (!container || !state.currentDraft) return;

  const draft = state.currentDraft;
  const currGame = draft.games[draft.games.length - 1];
  const allCurrentGameUsed = [
    ...currGame.blue_bans,
    ...currGame.red_bans,
    ...currGame.blue_picks,
    ...currGame.red_picks,
  ].map((c) => c.champion_id);

  const seriesPicked = new Set(draft.series_picked_champions || []);
  const currentAction = draft.current_turn ? draft.current_turn.action : "pick";

  let filtered = state.champions;
  if (state.draftRoleFilter !== "ALL") {
    filtered = filtered.filter((c) => c.role === state.draftRoleFilter);
  }
  if (state.draftSearchQuery) {
    filtered = filtered.filter((c) =>
      c.name.toLowerCase().includes(state.draftSearchQuery) ||
      c.title.toLowerCase().includes(state.draftSearchQuery)
    );
  }

  container.innerHTML = filtered
    .map((c) => {
      const isCurrentUsed = allCurrentGameUsed.includes(c.id);
      const isFearlessLocked = seriesPicked.has(c.id);

      let cardClass = "champion-card";
      let lockTag = "";
      let onClickAttr = "";

      if (isCurrentUsed) {
        cardClass += " disabled";
      } else if (isFearlessLocked && currentAction === "pick") {
        cardClass += " fearless-locked";
        lockTag = `<span class="fearless-lock-tag">已选</span>`;
      } else {
        onClickAttr = `onclick="onChampionClick('${c.id}')"`;
      }

      return `
        <div class="${cardClass}" ${onClickAttr} title="${c.name} - ${c.title}">
          ${lockTag}
          <div class="champ-avatar" style="background-color: ${c.avatar_color || "#3b82f6"};">
            ${c.name.substring(0, 2)}
          </div>
          <div class="champ-name">${c.name}</div>
          <div class="champ-role">${c.role} · ${Math.round(c.win_rate * 100)}%</div>
        </div>
      `;
    })
    .join("");
}

async function onChampionClick(championId) {
  const draft = state.currentDraft;
  if (!draft || !draft.current_turn) return;

  const ct = draft.current_turn;
  try {
    let updated;
    if (ct.action === "ban") {
      updated = await api.banChampion(draft.id, championId, ct.side);
    } else {
      updated = await api.pickChampion(draft.id, championId, ct.side);
    }
    state.currentDraft = updated;
    renderDraftView();
    if (!updated.game_completed) {
      fetchDraftRecommendations();
    }
  } catch (err) {
    console.error("Action error:", err);
  }
}

async function fetchDraftRecommendations() {
  const draft = state.currentDraft;
  if (!draft || draft.game_completed) return;

  try {
    const res = await api.getRecommendations(draft.id);
    state.draftRecommendations = res.recommendations || [];
    renderRecommendations();
  } catch (err) {
    console.error(err);
  }
}

function renderRecommendations() {
  const container = document.getElementById("recommend-cards-grid");
  if (!container) return;

  if (state.draftRecommendations.length === 0) {
    container.innerHTML = `<div style="font-size: 13px; color: var(--text-dim);">当前暂无候选推荐。</div>`;
    return;
  }

  container.innerHTML = state.draftRecommendations
    .map(
      (r, idx) => `
    <div class="recommend-card">
      <div class="recommend-card-top">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span class="badge ${idx === 0 ? "badge-gold" : "badge-blue"}">Top ${idx + 1}</span>
          <strong style="font-size: 15px;">${r.champion_name}</strong>
          <span class="badge badge-blue">${r.role}</span>
        </div>
        <div style="font-weight: 800; color: var(--gold); font-size: 15px;">
          ${Math.round(r.score * 100)}分
        </div>
      </div>
      <ul class="recommend-reasons">
        ${r.reasons.map((rs) => `<li>${rs}</li>`).join("")}
      </ul>
      <button class="btn btn-secondary" style="font-size: 12px; padding: 4px 10px; margin-top: 4px;" onclick="onChampionClick('${r.champion_id}')">
        ✓ 一键选入 / 操作
      </button>
    </div>
  `
    )
    .join("");
}

async function triggerAdvanceNextGame(winnerSide) {
  const draft = state.currentDraft;
  if (!draft) return;

  try {
    const updated = await api.advanceNextGame(draft.id, winnerSide);
    state.currentDraft = updated;
    showToast(`成功进入 Game ${updated.current_game}！已开启全局 Fearless 锁定`, "success");
    renderDraftView();
    if (!updated.game_completed) {
      fetchDraftRecommendations();
    }
  } catch (err) {
    console.error(err);
  }
}

// -------------------------------------------------------------
// View 5: History
// -------------------------------------------------------------
async function loadHistoryView() {
  const container = document.getElementById("history-content-container");
  if (!container) return;

  if (!state.currentDraft) {
    container.innerHTML = `
      <div style="text-align: center; padding: 40px; color: var(--text-muted);">
        <p>暂无系列赛记录。请先在“选角模拟”中创建并进行一场系列赛。</p>
        <button class="btn btn-primary" style="margin-top: 14px;" onclick="navigate('draft')">前往选角模拟</button>
      </div>
    `;
    return;
  }

  try {
    const hist = await api.getDraftHistory(state.currentDraft.id);
    container.innerHTML = `
      <div class="panel">
        <div class="panel-header">
          <div class="panel-title">系列赛复盘 (${hist.series_type})</div>
          <span class="badge badge-gold">${hist.status === "completed" ? "已完结" : "进行中"}</span>
        </div>
        <div style="margin-bottom: 16px; font-size: 16px; font-weight: 700;">
          <span style="color: var(--blue-light);">${hist.blue_team.name}</span>
          <span style="color: var(--text-muted); margin: 0 8px;">${hist.blue_team.score} : ${hist.red_team.score}</span>
          <span style="color: var(--red-light);">${hist.red_team.name}</span>
        </div>
        <div>
          ${hist.games
            .map(
              (g) => `
            <div style="background-color: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 8px; padding: 14px; margin-bottom: 12px;">
              <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <strong>Game ${g.game_number}</strong>
                <span class="badge ${g.winner === "blue" ? "badge-blue" : "badge-red"}">${g.winner ? (g.winner === "blue" ? "蓝方胜" : "红方胜") : "选角中"}</span>
              </div>
              <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 6px;">
                蓝方 Picks: ${(g.blue_picks || []).map((p) => p.champion_name).join(", ") || "无"}
              </div>
              <div style="font-size: 13px; color: var(--text-muted);">
                红方 Picks: ${(g.red_picks || []).map((p) => p.champion_name).join(", ") || "无"}
              </div>
            </div>
          `
            )
            .join("")}
        </div>
      </div>
    `;
  } catch (err) {
    console.error(err);
  }
}

// -------------------------------------------------------------
// On DOM Ready
// -------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  initApp();
});
