# Muse AI 云端 7×24h Hackathon 监控配置手册

本手册指导你在 **Muse AI (`muse.ai`)** 中配置每日定时任务（Scheduled Task）。即使你的本地电脑在周末关机，Muse AI 依然会在云端每天自动巡检比赛、撰写 `Spec` 与 `Plan`，并提交到我们的零 API 中转网站队列中排队。

---

## 第一步：将本仓库发布到 GitHub 并开启 GitHub Pages

1. 在 GitHub 上创建仓库 `Lightofwang/CloudAgentCluster`（如果尚未创建），然后将本地代码推送到 `main` 分支：
   ```powershell
   cd c:\noWork\CloudAgentCluster
   git remote add origin https://github.com/Lightofwang/CloudAgentCluster.git
   git add -A
   git commit -m "feat: initialize CloudAgentCluster hackathon automation hub"
   git push -u origin main
   ```
2. 打开 GitHub 仓库的 **Settings → Pages**：
   - 将 **Build and deployment → Source** 设置为 **GitHub Actions**。
3. 推送后，`.github/workflows/ingest-and-deploy.yml` 会自动将 `site/` 部署到：
   - **看板主页**：`https://lightofwang.github.io/CloudAgentCluster/`
   - **Muse AI 专用提交页**：`https://lightofwang.github.io/CloudAgentCluster/submit.html`
   - **数据接口 URL**：`https://lightofwang.github.io/CloudAgentCluster/data/hackathons.json`

> （可选）建议在本地设置系统环境变量 `HACKATHON_HUB_URL=https://lightofwang.github.io/CloudAgentCluster`，这样本地定时任务每次唤醒都会优先从线上网站直接读取最新队列。

---

## 第二步：在 Muse AI 中创建每日定时任务

> **安全访问说明（非常重要）**：
> 1. 为防止开源仓库被他人恶意提交，网站已开启**口令 + GitHub 所有者双重保护**：仓库内**只保存口令的不可逆 SHA-256 哈希值**，绝对不会在公开文件里暴露明文口令。你的实际口令保存在本地被忽略的 `.env.local` 中（下方提示词中的 `<YOUR_SECRET_PASSCODE>` 需在复制到 `muse.ai` 时替换为你的真实口令）。
> 2. 如果需要更换口令，可在仓库 **Settings → Secrets and variables → Actions** 中配置 `HUB_PASSCODE`，并同步更新 `site/assets/app.js` 中的哈希值。
> 3. 请在 **Muse AI 云端浏览器**中预先登录一次你本人的 GitHub 账号 **`Lightofwang`**（或配置你的 GitHub PAT），GitHub Actions 仅放行由 `Lightofwang` 提交且口令校验通过的 Issue。

在 `muse.ai` 创建一个 **Daily Scheduled Task**（例如每天上午 **09:00** 运行），并将下方完整 Prompt 中的 `<YOUR_SECRET_PASSCODE>` 替换为你本地 `.env.local` 里保存的口令后复制进去：

```text
You are my automated Hackathon Scout & Architect. Run this task daily:

1. Check the already-queued hackathons first by reading:
   https://lightofwang.github.io/CloudAgentCluster/data/hackathons.json
   Collect all existing `slug` and `source_url` values so we never submit duplicates.

2. Browse and monitor the latest active online hackathons on these 3 platforms:
   - Devpost (https://devpost.com/hackathons)
   - Lablab.ai (https://lablab.ai/event)
   - DoraHacks (https://dorahacks.io/hackathon)

3. Filter for AI, AI Agent, Developer Tools, or Full-Stack Web hackathons that are currently open for registration with clear prizes and at least 3 days left before deadline. Score and pick the Top 1-2 best matching NEW hackathons not already in hackathons.json.

4. For each selected hackathon, design a winning, demo-ready Full-Stack Web Application (Python HTTP/FastAPI backend + modern interactive HTML/CSS/JS frontend, zero paid API keys required to run locally, and automated unittest test suite). Draft two detailed Markdown documents:
   - `spec.md`: Project overview, core features, REST API endpoints & JSON schemas, frontend UI layout, and non-functional constraints.
   - `plan.md`: Step-by-step implementation phases (Phase 1 Backend, Phase 2 Frontend, Phase 3 Automated Tests & Verification).

5. Open my protected submission hub in your browser (the `?key=` parameter automatically unlocks `#submit-passcode`):
   https://lightofwang.github.io/CloudAgentCluster/submit.html?key=<YOUR_SECRET_PASSCODE>
   Verify `#submit-passcode` is filled with `<YOUR_SECRET_PASSCODE>` (if empty, fill it), then fill in the form fields by their fixed IDs:
   - `#submit-passcode`: <YOUR_SECRET_PASSCODE>
   - `#hackathon-title`: Hackathon & project title
   - `#hackathon-slug`: lowercase kebab-case slug (e.g. devpost-agent-arena-2026)
   - `#hackathon-platform`: devpost | lablab | dorahacks
   - `#hackathon-url`: original hackathon URL
   - `#hackathon-deadline`: ISO date or YYYY-MM-DD
   - `#hackathon-prize`: prize pool string (e.g. $25,000)
   - `#hackathon-score`: match score (1-100)
   - `#hackathon-tags`: comma-separated tags
   - `#hackathon-summary`: one-sentence Chinese summary
   - `#spec-content`: full spec.md markdown
   - `#plan-content`: full plan.md markdown

6. Click `#btn-submit-issue` (making sure you are signed in to GitHub as `Lightofwang`) to open the pre-filled GitHub Issue page, then click the green "Submit new issue" button on GitHub so the GitHub Actions pipeline automatically verifies your identity & passcode and ingests the Spec & Plan into the hub!
```

---

## 第三步：启用 Antigravity 每日自动研发（10:00 & 20:00）

- 即使你周末没开电脑，Muse AI 周六、周日提交的所有比赛都会持久化排队在网站上（状态为 `pending_dev`）。
- 平时或周一早上电脑开机后，Antigravity 的定时任务会在 **10:00** 和 **20:00** 自动读取网站上的全部 `pending_dev` 任务，依次开发出完整全栈项目并自动推送至 GitHub！
- **可选独立建库 Token**：如果你希望每场比赛自动在账号 `Lightofwang` 下创建全新独立仓库（如 `Lightofwang/hackathon-<slug>`），只需在本地环境变量中设置 `GITHUB_TOKEN`（需勾选 `repo` 权限）。若未设置，系统会自动无缝将完整项目归档推送到 `CloudAgentCluster/projects/<slug>/`。
