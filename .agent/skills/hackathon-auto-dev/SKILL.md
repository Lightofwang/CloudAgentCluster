---
name: hackathon-auto-dev
description: 自动从 CloudAgentCluster 中转网站/队列读取 pending_dev 状态的 Hackathon Spec 与 Plan，开发完整全栈可交互 Web 应用，通过测试验证后推送至 GitHub 并回写网站状态。
---

# Hackathon Spec Reader & Auto Developer Workflow

每当定时任务触发或手动唤醒执行 Hackathon 自动研发时，请严格按以下四步流程执行（支持本地 Antigravity App 与 EC2 CLI 多节点并行不冲突）：

## Step 1: 通过 Git CAS 原子抢单锁定下一个待开发任务 (`claim`)
运行以下命令通过远端 Git 原子推送抢占下一个 `pending_dev`（或已超时的僵尸 `in_progress`）任务：

```bash
python scripts/sync_and_queue.py claim --json
```

- 该命令会自动 `git pull --rebase`、将目标任务标记为 `in_progress` 并附上当前节点 `claimed_by` 与 `claimed_at`，再立即 `git push origin main` 完成分布式锁定。
- 若返回 `null`，说明当前队列为空或均已被其他节点（如 EC2 CLI）领取锁定，直接向用户汇报“队列为空或已被其他节点接管”并结束任务。
- 若多台机器（本地 + EC2）同时抢到同一任务，推送失败方会自动回滚并改抢下一个任务，**绝不会重复开发同一个比赛**。
- 开发完一个任务后，可循环再次调用 `claim --json` 领取下一个积压任务，直到返回 `null` 为止。

## Step 2: 精读已抢占任务的 Spec & Plan
针对上一步抢到的比赛 `<slug>`：
1. 查看完整元信息（可选）：
   ```bash
   python scripts/sync_and_queue.py get --slug <slug>
   ```
2. 完整阅读对应的设计文档：
   - `site/data/specs/<slug>/spec.md`
   - `site/data/specs/<slug>/plan.md`

## Step 3: 生成全栈脚手架并实现完整业务代码
1. 初始化项目骨架：
   ```bash
   python scripts/scaffold_fullstack.py --slug <slug>
   ```
2. 在 `projects/<slug>/` 目录中严格按照 `SPEC.md` 和 `PLAN.md` 编写实际可用的全栈 Web 应用：
   - `backend/server.py`（或对应的后端模块）：实现所有 Spec 中定义的 REST API、输入校验与核心业务逻辑；
   - `frontend/`：实现美观、可交互、能完整走通比赛 Demo 场景的前端网页；
   - `tests/test_app.py`：编写端到端 HTTP 接口与静态前端验证测试用例；
   - `README.md`：更新真实的项目启动方法、API 说明与测试指令。
3. 运行项目单元测试并确认全部通过：
   ```bash
   python -m unittest discover -s projects/<slug>/tests -p "test_*.py" -v
   ```

## Step 4: 验证并推送到 GitHub、更新网站状态
运行发布脚本：

```bash
python scripts/publish_project.py --slug <slug>
```

该脚本会自动完成：
1. 重新运行 `projects/<slug>/tests/` 校验全部测试通过；
2. 若配置了 `GITHUB_TOKEN` / `GH_TOKEN`，自动在 GitHub 创建独立新仓库 `hackathon-<slug>` 并推送代码；若未配置 Token，自动无缝兜底归档到主仓库 `projects/<slug>/` 并推送；
3. 将 `site/data/hackathons.json` 中该比赛状态更新为 `completed` 并填充 `repo_url`，使中转网站看板实时更新。
