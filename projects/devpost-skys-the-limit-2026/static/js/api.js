/**
 * DraftLens Frontend API Client
 */

const API_BASE = "/api";

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  const icon = type === "error" ? "⚠️" : type === "success" ? "✅" : "ℹ️";
  toast.innerHTML = `<span>${icon}</span><div>${message}</div>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.3s";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  try {
    const res = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      const errMsg = data.detail || `请求失败 (HTTP ${res.status})`;
      showToast(errMsg, "error");
      throw new Error(errMsg);
    }
    return data;
  } catch (err) {
    if (!err.message.includes("HTTP")) {
      showToast(err.message || "网络请求异常", "error");
    }
    throw err;
  }
}

const api = {
  getHealth: () => request("/health"),
  getGridStatus: () => request("/grid/status"),
  getTeams: (style = "") => request(style ? `/teams?style=${encodeURIComponent(style)}` : "/teams"),
  getTeamDetail: (id) => request(`/teams/${id}`),
  getPlayers: (teamId = "") => request(teamId ? `/players?team_id=${teamId}` : "/players"),
  getMatches: (teamId = "", limit = 20) => request(`/matches?team_id=${teamId}&limit=${limit}`),
  getChampions: (role = "") => request(role ? `/champions?role=${encodeURIComponent(role)}` : "/champions"),
  getScoutReport: (teamId, matches = 5) => request(`/scout/${teamId}?matches=${matches}`),
  createDraft: (blueId, redId, seriesType = "BO3") =>
    request("/draft", {
      method: "POST",
      body: JSON.stringify({ blue_team_id: blueId, red_team_id: redId, series_type: seriesType }),
    }),
  getDraft: (draftId) => request(`/draft/${draftId}`),
  banChampion: (draftId, championId, side) =>
    request(`/draft/${draftId}/ban`, {
      method: "POST",
      body: JSON.stringify({ champion_id: championId, side: side }),
    }),
  pickChampion: (draftId, championId, side) =>
    request(`/draft/${draftId}/pick`, {
      method: "POST",
      body: JSON.stringify({ champion_id: championId, side: side }),
    }),
  getRecommendations: (draftId) =>
    request(`/draft/${draftId}/recommend`, {
      method: "POST",
    }),
  advanceNextGame: (draftId, winner = null) =>
    request(`/draft/${draftId}/next-game`, {
      method: "POST",
      body: JSON.stringify({ winner: winner }),
    }),
  getDraftHistory: (draftId) => request(`/draft/${draftId}/history`),
};

window.api = api;
window.showToast = showToast;
