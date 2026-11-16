# CloudAgentCluster — Hackathon 全自动监控、Spec 中转与自主研发系统

一套**零外部付费模型 API 成本、支持周末关机无人值守排队**的 Hackathon 自动化参赛开发流水线：

1. **云端 7×24h 监控与设计（Muse AI）**：每日定时巡检 Devpost、Lablab.ai、DoraHacks，筛选 Top 1~2 比赛，生成 `spec.md` 与 `plan.md` 并通过中转网站表单提交。
2. **中转网站与零 API 自动入库（GitHub Pages + GitHub Actions）**：
   - `site/index.html`：可视化看板，支持在线阅读 `Spec` / `Plan`、过滤搜索、一键重新触发队列与跳转 GitHub 仓库。
   - `site/submit.html`：为 Muse AI 浏览器自动化设计的固定 ID 表单工作台，通过 GitHub Issue + 纯 Python 脚本零 API 入库。
3. **Antigravity 每日定时读取与全栈研发**：
   - 每日 `10:00` 与 `20:00` 自动运行，调用 `scripts/sync_and_queue.py` 读取网站 `pending_dev` 任务队列；
   - 基于 `Spec` 与 `Plan` 自动开发全栈可交互 Web 应用至 `projects/<slug>/` 并运行测试；
   - 调用 `scripts/publish_project.py` 自动创建独立 GitHub 新仓库（或自动兜底推送至主仓库 `projects/<slug>/`）并更新网站状态为 `completed`。

## 快速体验与文档

- **配置 Muse AI 与开启 GitHub Pages**：详见 [docs/muse-ai-playbook.md](docs/muse-ai-playbook.md)
- **Antigravity 自动研发规范 Skill**：详见 [.agent/skills/hackathon-auto-dev/SKILL.md](.agent/skills/hackathon-auto-dev/SKILL.md)
- **端到端示例全栈项目**：[projects/demo-ai-agent-copilot/](projects/demo-ai-agent-copilot/)

## 运行全部自动化测试

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
python -m unittest discover -s projects/demo-ai-agent-copilot/tests -p "test_*.py" -v
```
