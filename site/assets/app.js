(function () {
  "use strict";

  const state = {
    config: {
      github_owner: "Lightofwang",
      github_repo: "CloudAgentCluster",
      default_branch: "main",
    },
    hackathons: [],
    currentItem: null,
    currentTab: "spec",
    showRaw: false,
    specCache: {},
    planCache: {},
  };

  function showToast(msg) {
    const toast = document.getElementById("toast");
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.add("show");
    setTimeout(() => toast.classList.remove("show"), 3200);
  }

  function escapeHtml(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function slugify(text) {
    return String(text || "")
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 64) || "hackathon-project";
  }

  function renderMarkdown(md) {
    const lines = String(md || "").replace(/\r\n/g, "\n").split("\n");
    let html = "";
    let inCode = false;
    let inList = false;

    const closeList = () => {
      if (inList) {
        html += "</ul>";
        inList = false;
      }
    };

    const formatInline = (text) => {
      return escapeHtml(text)
        .replace(/`([^`]+)`/g, "<code>$1</code>")
        .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
        .replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    };

    for (const line of lines) {
      if (line.trim().startsWith("```")) {
        closeList();
        if (!inCode) {
          inCode = true;
          html += "<pre><code>";
        } else {
          inCode = false;
          html += "</code></pre>";
        }
        continue;
      }

      if (inCode) {
        html += escapeHtml(line) + "\n";
        continue;
      }

      const trimmed = line.trim();
      if (!trimmed) {
        closeList();
        continue;
      }

      if (trimmed.startsWith("### ")) {
        closeList();
        html += `<h3>${formatInline(trimmed.slice(4))}</h3>`;
      } else if (trimmed.startsWith("## ")) {
        closeList();
        html += `<h2>${formatInline(trimmed.slice(3))}</h2>`;
      } else if (trimmed.startsWith("# ")) {
        closeList();
        html += `<h1>${formatInline(trimmed.slice(2))}</h1>`;
      } else if (/^[-*]\s+/.test(trimmed) || /^\d+\.\s+/.test(trimmed)) {
        if (!inList) {
          html += "<ul>";
          inList = true;
        }
        const itemText = trimmed.replace(/^([-*]|\d+\.)\s+/, "");
        html += `<li>${formatInline(itemText)}</li>`;
      } else {
        closeList();
        html += `<p>${formatInline(trimmed)}</p>`;
      }
    }

    closeList();
    if (inCode) html += "</code></pre>";
    return `<div class="markdown-view">${html}</div>`;
  }

  async function loadConfigAndData() {
    try {
      const resp = await fetch("data/hackathons.json?t=" + Date.now());
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      const data = await resp.json();
      if (data.site_config) {
        state.config = Object.assign({}, state.config, data.site_config);
      }
      state.hackathons = Array.isArray(data.hackathons) ? data.hackathons : [];
      const updatedEl = document.getElementById("last-updated");
      if (updatedEl) updatedEl.textContent = data.updated_at || "-";
      const repoLink = document.getElementById("nav-repo-link");
      if (repoLink) {
        repoLink.href = `https://github.com/${state.config.github_owner}/${state.config.github_repo}`;
      }
      return data;
    } catch (err) {
      console.error("Failed to load hackathons.json:", err);
      return null;
    }
  }

  function renderDashboard() {
    const container = document.getElementById("cards-container");
    if (!container) return;

    const platformFilter = (document.getElementById("filter-platform")?.value || "all").toLowerCase();
    const statusFilter = (document.getElementById("filter-status")?.value || "all").toLowerCase();
    const searchQuery = (document.getElementById("filter-search")?.value || "").trim().toLowerCase();

    const total = state.hackathons.length;
    const pending = state.hackathons.filter((h) => h.status === "pending_dev").length;
    const progress = state.hackathons.filter((h) => h.status === "in_progress").length;
    const completed = state.hackathons.filter((h) => h.status === "completed").length;

    document.getElementById("stat-total").textContent = String(total);
    document.getElementById("stat-pending").textContent = String(pending);
    document.getElementById("stat-progress").textContent = String(progress);
    document.getElementById("stat-completed").textContent = String(completed);

    const filtered = state.hackathons.filter((item) => {
      const p = (item.platform || "other").toLowerCase();
      const s = (item.status || "pending_dev").toLowerCase();
      if (platformFilter !== "all" && p !== platformFilter) return false;
      if (statusFilter !== "all" && s !== statusFilter) return false;
      if (searchQuery) {
        const hay = [item.title, item.slug, item.summary, ...(item.tags || [])]
          .join(" ")
          .toLowerCase();
        if (!hay.includes(searchQuery)) return false;
      }
      return true;
    });

    if (filtered.length === 0) {
      container.innerHTML = `<div class="empty-state" style="grid-column:1/-1;">暂无符合筛选条件的 Hackathon 任务。你可以点击右上角「+ 提交 Spec / Plan」添加新任务。</div>`;
      return;
    }

    const statusLabels = {
      pending_dev: "Pending Dev · 待开发",
      in_progress: "In Progress · 开发中",
      completed: "Completed · 已推 GitHub",
      failed: "Failed · 待重试",
    };

    container.innerHTML = filtered
      .map((item) => {
        const platform = (item.platform || "other").toLowerCase();
        const badgeClass = ["devpost", "lablab", "dorahacks"].includes(platform)
          ? `badge-${platform}`
          : "badge-other";
        const status = item.status || "pending_dev";
        const tagsHtml = (item.tags || [])
          .map((t) => `<span class="tag">${escapeHtml(t)}</span>`)
          .join("");
        const repoButton = item.repo_url
          ? `<a href="${escapeHtml(item.repo_url)}" target="_blank" rel="noopener" class="btn btn-success btn-sm">查看 GitHub 代码 ↗</a>`
          : "";

        return `
          <article class="card" data-slug="${escapeHtml(item.slug)}">
            <div class="card-top">
              <div class="badge-row">
                <span class="badge ${badgeClass}">${escapeHtml(platform)}</span>
                <span class="badge status-${escapeHtml(status)}">${escapeHtml(statusLabels[status] || status)}</span>
              </div>
              <span class="score-pill">匹配度 ${escapeHtml(item.match_score || 90)}分</span>
            </div>
            <h3 class="card-title">${escapeHtml(item.title)}</h3>
            <p class="card-summary">${escapeHtml(item.summary || "由 Muse AI 自动分析生成的参赛全栈项目规范。")}</p>
            <div class="meta-grid">
              <div>奖金：<strong>${escapeHtml(item.prize_pool || "TBD")}</strong></div>
              <div>截止：<strong>${escapeHtml((item.deadline || "TBD").slice(0, 10))}</strong></div>
              <div>Slug：<strong>${escapeHtml(item.slug)}</strong></div>
              <div>来源：<a href="${escapeHtml(item.source_url || "#")}" target="_blank" rel="noopener">原比赛页 ↗</a></div>
            </div>
            <div class="tags-list">${tagsHtml}</div>
            <div class="card-actions">
              <button class="btn btn-primary btn-sm js-open-modal" data-slug="${escapeHtml(item.slug)}" data-tab="spec">阅读 Spec & Plan</button>
              <button class="btn btn-warning btn-sm js-open-modal" data-slug="${escapeHtml(item.slug)}" data-tab="trigger">一键触发/重跑</button>
              ${repoButton}
            </div>
          </article>
        `;
      })
      .join("");

    container.querySelectorAll(".js-open-modal").forEach((btn) => {
      btn.addEventListener("click", () => {
        const slug = btn.getAttribute("data-slug");
        const tab = btn.getAttribute("data-tab") || "spec";
        openModal(slug, tab);
      });
    });
  }

  async function fetchTextCached(path, cacheObj, slug) {
    if (cacheObj[slug] !== undefined) return cacheObj[slug];
    try {
      const resp = await fetch(`${path}?t=${Date.now()}`);
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      const text = await resp.text();
      cacheObj[slug] = text;
      return text;
    } catch (err) {
      return `无法加载文件 (${path})：${err.message}`;
    }
  }

  async function openModal(slug, tab) {
    const item = state.hackathons.find((h) => h.slug === slug);
    if (!item) return;
    state.currentItem = item;
    state.currentTab = tab;

    document.getElementById("modal-title").textContent = item.title;
    document.getElementById("modal-subtitle").textContent = `Slug: ${item.slug} · 平台: ${item.platform} · 状态: ${item.status}`;
    document.getElementById("spec-modal").classList.add("open");
    await renderModalContent();
  }

  async function renderModalContent() {
    const item = state.currentItem;
    if (!item) return;

    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    const activeTabBtn = document.getElementById(`tab-${state.currentTab}`);
    if (activeTabBtn) activeTabBtn.classList.add("active");

    const modalBody = document.getElementById("modal-body");
    const rawLink = document.getElementById("link-raw-file");
    const toggleRawBtn = document.getElementById("btn-toggle-raw");

    if (state.currentTab === "trigger") {
      rawLink.style.display = "none";
      toggleRawBtn.style.display = "none";
      const owner = state.config.github_owner;
      const repo = state.config.github_repo;
      const triggerBody = encodeURIComponent(
        `<!--TRIGGER_DEV_START-->\n{"reset_slug": "${item.slug}"}\n<!--TRIGGER_DEV_END-->\n\n请重置比赛 \`${item.slug}\` 为 \`pending_dev\` 状态以重新执行 Antigravity 自动开发。`
      );
      const issueUrl = `https://github.com/${owner}/${repo}/issues/new?labels=trigger-dev&title=${encodeURIComponent("[Trigger Dev] " + item.slug)}&body=${triggerBody}`;
      const localCmd = `python scripts/sync_and_queue.py get --slug ${item.slug}`;
      const devCmd = `python scripts/ingest_spec.py --reset-slug ${item.slug}`;

      modalBody.innerHTML = `
        <div class="notice">
          <strong>双模式触发说明：</strong> 当你点击云端重置后，状态会变回 <code>pending_dev</code>，下次 Antigravity 每日定时任务（10:00 / 20:00）启动时会自动拉取并开发；如果你当前就在电脑旁，可以直接复制下方命令让本地 Antigravity 立即开发。
        </div>
        <div class="card" style="margin-bottom:14px;">
          <h4>方式 1：通过 GitHub Actions 云端重置并重新排队</h4>
          <p class="card-summary">打开预填充的 GitHub Issue 页面并提交，GitHub Actions 将自动把状态重置为 <code>pending_dev</code>。</p>
          <div><a href="${issueUrl}" target="_blank" rel="noopener" class="btn btn-primary btn-sm">前往 GitHub 触发云端重新排队 ↗</a></div>
        </div>
        <div class="card">
          <h4>方式 2：本地命令行读取 / 重置</h4>
          <p class="card-summary">读取网站 Spec 与 Plan 的命令行：</p>
          <pre class="raw-pre">${escapeHtml(localCmd)}</pre>
          <p class="card-summary">本地重置为 pending_dev 队列：</p>
          <pre class="raw-pre">${escapeHtml(devCmd)}</pre>
          <div><button id="btn-copy-trigger-cmd" class="btn btn-sm">复制本地开发指令</button></div>
        </div>
      `;
      document.getElementById("btn-copy-trigger-cmd")?.addEventListener("click", () => {
        navigator.clipboard?.writeText(localCmd);
        showToast("已复制本地读取指令");
      });
      return;
    }

    rawLink.style.display = "inline-flex";
    toggleRawBtn.style.display = "inline-flex";
    const filePath = state.currentTab === "spec" ? item.spec_path : item.plan_path;
    const cacheObj = state.currentTab === "spec" ? state.specCache : state.planCache;
    rawLink.href = filePath;

    modalBody.innerHTML = `<p class="card-summary">正在读取 ${escapeHtml(filePath)} ...</p>`;
    const content = await fetchTextCached(filePath, cacheObj, item.slug);
    modalBody.innerHTML = state.showRaw
      ? `<pre class="raw-pre">${escapeHtml(content)}</pre>`
      : renderMarkdown(content);
  }

  function initDashboardPage() {
    if (!document.getElementById("cards-container")) return;

    loadConfigAndData().then(() => renderDashboard());

    document.getElementById("btn-refresh")?.addEventListener("click", () => {
      loadConfigAndData().then(() => {
        renderDashboard();
        showToast("已刷新 Hackathon 队列数据");
      });
    });

    ["filter-platform", "filter-status"].forEach((id) => {
      document.getElementById(id)?.addEventListener("change", renderDashboard);
    });
    document.getElementById("filter-search")?.addEventListener("input", renderDashboard);

    document.getElementById("btn-close-modal")?.addEventListener("click", () => {
      document.getElementById("spec-modal").classList.remove("open");
    });
    document.getElementById("spec-modal")?.addEventListener("click", (e) => {
      if (e.target.id === "spec-modal") {
        document.getElementById("spec-modal").classList.remove("open");
      }
    });

    ["spec", "plan", "trigger"].forEach((tab) => {
      document.getElementById(`tab-${tab}`)?.addEventListener("click", () => {
        state.currentTab = tab;
        renderModalContent();
      });
    });

    document.getElementById("btn-toggle-raw")?.addEventListener("click", () => {
      state.showRaw = !state.showRaw;
      renderModalContent();
    });
  }

  function collectFormPayload() {
    const title = document.getElementById("hackathon-title").value.trim();
    const rawSlug = document.getElementById("hackathon-slug").value.trim();
    const slug = rawSlug ? slugify(rawSlug) : slugify(title);
    const platform = document.getElementById("hackathon-platform").value.trim() || "devpost";
    const source_url = document.getElementById("hackathon-url").value.trim();
    const deadline = document.getElementById("hackathon-deadline").value.trim() || "TBD";
    const prize_pool = document.getElementById("hackathon-prize").value.trim() || "TBD";
    const match_score = parseInt(document.getElementById("hackathon-score").value || "90", 10) || 90;
    const tagsRaw = document.getElementById("hackathon-tags").value.trim();
    const tags = tagsRaw
      ? tagsRaw.split(",").map((s) => s.trim()).filter(Boolean)
      : ["AI Agent", "Full-Stack"];
    const summary = document.getElementById("hackathon-summary").value.trim();
    const spec_content = document.getElementById("spec-content").value.trim();
    const plan_content = document.getElementById("plan-content").value.trim();

    return {
      slug,
      title,
      platform,
      source_url,
      deadline,
      prize_pool,
      match_score,
      tags,
      summary,
      project_type: "fullstack-web",
      spec_content,
      plan_content,
    };
  }

  function buildIssueMarkdown(payload) {
    const meta = {
      slug: payload.slug,
      title: payload.title,
      platform: payload.platform,
      source_url: payload.source_url,
      deadline: payload.deadline,
      prize_pool: payload.prize_pool,
      match_score: payload.match_score,
      tags: payload.tags,
      summary: payload.summary,
      project_type: payload.project_type,
    };

    return [
      "<!--HACKATHON_META_START-->",
      "```json",
      JSON.stringify(meta, null, 2),
      "```",
      "<!--HACKATHON_META_END-->",
      "",
      "## Spec 设计文档",
      "<!--SPEC_START-->",
      payload.spec_content,
      "<!--SPEC_END-->",
      "",
      "## Plan 实施计划",
      "<!--PLAN_START-->",
      payload.plan_content,
      "<!--PLAN_END-->",
    ].join("\n");
  }

  function validatePayload(payload) {
    if (!payload.title || !payload.spec_content || !payload.plan_content) {
      showToast("请至少填写：比赛名称、Spec 设计文档和 Plan 实施计划");
      return false;
    }
    return true;
  }

  function initSubmitPage() {
    const form = document.getElementById("spec-submit-form");
    if (!form) return;

    loadConfigAndData();

    const tokenInput = document.getElementById("github-token");
    const savedToken = localStorage.getItem("cloudagentcluster_gh_token");
    if (tokenInput && savedToken) tokenInput.value = savedToken;
    tokenInput?.addEventListener("change", () => {
      localStorage.setItem("cloudagentcluster_gh_token", tokenInput.value.trim());
    });

    document.getElementById("hackathon-title")?.addEventListener("input", (e) => {
      const slugInput = document.getElementById("hackathon-slug");
      if (slugInput && !slugInput.dataset.touched) {
        slugInput.value = slugify(e.target.value);
      }
    });
    document.getElementById("hackathon-slug")?.addEventListener("input", (e) => {
      e.target.dataset.touched = "1";
    });

    document.getElementById("btn-fill-sample")?.addEventListener("click", () => {
      document.getElementById("hackathon-title").value = "Lablab.ai Multi-Agent Workflow Hackathon";
      document.getElementById("hackathon-slug").value = "lablab-multi-agent-workflow";
      document.getElementById("hackathon-platform").value = "lablab";
      document.getElementById("hackathon-url").value = "https://lablab.ai/event";
      document.getElementById("hackathon-deadline").value = "2026-12-28T23:59:00Z";
      document.getElementById("hackathon-prize").value = "$30,000";
      document.getElementById("hackathon-score").value = "93";
      document.getElementById("hackathon-tags").value = "Multi-Agent, Full-Stack, Automation";
      document.getElementById("hackathon-summary").value = "可视化多 Agent 任务编排与执行监控全栈控制台。";
      document.getElementById("spec-content").value =
        "# Spec: Multi-Agent Workflow Console\n\n## 1. 目标\n构建支持节点任务编排与执行日志回放的 Web 控制台。\n\n## 2. 接口\n- GET /api/workflows\n- POST /api/workflows/run";
      document.getElementById("plan-content").value =
        "# Plan: Multi-Agent Workflow Console\n\n## Phase 1: Python 后端 API\n实现工作流注册与模拟执行引擎。\n\n## Phase 2: 前端可视化看板\n提供流程图列表和运行状态面板。";
      showToast("已填充示例 Spec & Plan 模板");
    });

    document.getElementById("btn-submit-issue")?.addEventListener("click", () => {
      const payload = collectFormPayload();
      if (!validatePayload(payload)) return;

      const md = buildIssueMarkdown(payload);
      document.getElementById("payload-preview").textContent = md;
      document.getElementById("payload-preview-box").style.display = "block";

      const owner = state.config.github_owner;
      const repo = state.config.github_repo;
      const issueTitle = `[Hackathon Spec] ${payload.title}`;
      const url = `https://github.com/${owner}/${repo}/issues/new?labels=hackathon-spec&title=${encodeURIComponent(issueTitle)}&body=${encodeURIComponent(md)}`;
      window.open(url, "_blank", "noopener");
      showToast("已打开 GitHub Issue 页面，点击 Submit new issue 即可自动入库");
    });

    document.getElementById("btn-submit-api")?.addEventListener("click", async () => {
      const payload = collectFormPayload();
      if (!validatePayload(payload)) return;
      const token = (document.getElementById("github-token")?.value || "").trim();
      if (!token) {
        showToast("未填写 GitHub Token，请使用左侧免 Token 跳转提交按钮");
        return;
      }

      const md = buildIssueMarkdown(payload);
      const owner = state.config.github_owner;
      const repo = state.config.github_repo;
      try {
        const resp = await fetch(`https://api.github.com/repos/${owner}/${repo}/issues`, {
          method: "POST",
          headers: {
            "Accept": "application/vnd.github+json",
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            title: `[Hackathon Spec] ${payload.title}`,
            body: md,
            labels: ["hackathon-spec"],
          }),
        });
        if (!resp.ok) {
          const errText = await resp.text();
          throw new Error(`HTTP ${resp.status}: ${errText}`);
        }
        const data = await resp.json();
        showToast(`提交成功！Issue #${data.number} 已创建，GitHub Actions 正在入库`);
      } catch (err) {
        showToast("API 提交失败：" + err.message);
      }
    });

    document.getElementById("btn-download-json")?.addEventListener("click", () => {
      const payload = collectFormPayload();
      if (!validatePayload(payload)) return;
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `${payload.slug}.json`;
      a.click();
      URL.revokeObjectURL(a.href);
      showToast(`已导出 ${payload.slug}.json`);
    });

    document.getElementById("btn-copy-markdown")?.addEventListener("click", () => {
      const payload = collectFormPayload();
      if (!validatePayload(payload)) return;
      const md = buildIssueMarkdown(payload);
      document.getElementById("payload-preview").textContent = md;
      document.getElementById("payload-preview-box").style.display = "block";
      navigator.clipboard?.writeText(md);
      showToast("已复制结构化 Markdown 到剪贴板");
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initDashboardPage();
    initSubmitPage();
  });
})();
