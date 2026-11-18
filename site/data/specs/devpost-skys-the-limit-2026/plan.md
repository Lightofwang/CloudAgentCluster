# DraftLens 实施计划

## Phase 0 — 准备（0.5 天）

- 初始化仓库：`README.md`（项目介绍、启动方式、JetBrains 工具说明）、`LICENSE`（MIT）、`.gitignore`。
- 确定技术栈版本：Python 3.11、FastAPI 0.110+、uvicorn、SQLite（标准库 `sqlite3`）、前端零框架。
- 准备 8 支虚构战队、40 名选手、60 名英雄、120 场对局的种子数据草表（含对阵胜率矩阵与协同 / 克制系数）。
- 确认 JetBrains 工具：PyCharm 写后端、WebStorm 写前端、JetBrains Air 并行智能体辅助（记录 AI 工作流，用于 Best AI-Powered Workflow Story 附加奖素材）。

## Phase 1 — 后端（2 天）

### 1.1 数据层
- `app/db.py`：SQLite 连接与建表（`teams`、`players`、`matches`、`champions`、`matchups`、`drafts`）。
- `app/seed.py`：种子数据导入脚本，幂等（`INSERT OR REPLACE` + 导入前校验计数）。
- 种子数据校验：战队 8 支、选手 40 名、英雄 60 名、对局 120 场，对阵矩阵对称性自检。

### 1.2 战队 / 选手 / 对局接口
- `app/routers/teams.py`：`GET /api/teams`、`GET /api/teams/{id}`、`GET /api/players`、`GET /api/matches`、`GET /api/champions`。
- 分页与过滤：`limit` 默认 20、上限 100；`style` 过滤；不存在的 id 返回 404。

### 1.3 侦察报告引擎
- `app/services/scout.py`：按战队与最近 N 场聚合目标控制率、视野分、一血率、15 分钟经济差、英雄偏好。
- `GET /api/scout/{team_id}`：返回报告 JSON + 一句话风格总结（规则模板生成）。
- 边界：对局数不足时返回已分析场次并标注 `matches_analyzed < requested`。

### 1.4 选角模拟与 Fearless Draft
- `app/services/draft.py`：选角会话状态机（`lobby → banning/picking → game_done → next_game`），标准 Ban/Pick 顺序表，BO3/BO5 系列赛。
- `POST /api/draft` 创建会话；`/ban`、`/pick` 校验轮次、方阵与 Fearless 规则（系列赛内已选英雄不可重复，违例返回 400）。
- `app/services/recommend.py`：推荐引擎——对阵胜率、协同、克制、选手熟练度四项加权打分，返回 Top 3 + 中文解释理由。
- `GET /api/grid/status`：返回 `{"mode": "sample-data", "grid_connected": false}`，预留 GRID 接入点。
- `GET /api/health` 健康检查。

### 1.5 后端验收
- `uvicorn` 启动后手动跑通：建队 → 侦察报告 → 创建选角会话 → 完整一局 Ban/Pick → 推荐 → 下一局（验证已选英雄被锁定）。
- 记录 5 条以上 curl 示例进 README。

## Phase 2 — 前端（2 天）

### 2.1 骨架与样式
- `static/index.html`、`static/css/style.css`、`static/js/app.js`；深色电竞主题、响应式布局（窄屏导航折叠）。
- 顶部栏 + 左侧导航 + 主内容区；五个页面以 JS 路由切换（hash 路由，无刷新）。

### 2.2 页面实现
- **总览页**：数据卡 + 最近对局表（`GET /api/matches?limit=10`）。
- **战队页**：战队卡片网格 + 详情抽屉（选手表、近 5 场）。
- **侦察报告页**：对手选择器 → `GET /api/scout/{id}` → 目标控制率条形图 + 经济差 Canvas 折线图 + 风格总结。
- **选角模拟页**（重点）：Ban/Pick 板实时渲染、英雄池搜索与位置过滤、点击 Ban/Pick、推荐面板（Top 3 卡片 + 理由）、系列赛历史条；Fearless 锁定英雄置灰并标注“本系列赛已选”。
- **历史页**：系列赛列表与复盘（`GET /api/draft/{id}/history`）。

### 2.3 前后端联调
- 统一 `api.js` 封装 `fetch` + 错误提示（中文 toast）。
- 空状态与加载态：无数据时显示引导文案，不出现空白页。
- 浏览器端到端走查：创建 BO3 系列赛并打满三局，确认前端状态与后端一致。

## Phase 3 — 自动化测试与验证（1 天）

### 3.1 自动化测试
- `tests/test_api.py`（unittest + FastAPI TestClient）：
  - 战队 / 选手 / 对局接口返回结构与分页；
  - 侦察报告聚合值与种子数据手工核算一致；
  - 选角会话：顺序校验、Fearless 规则（重复 Pick 返回 400）、BO3 三局流转；
  - 推荐接口返回 3 条且分数单调递减、理由非空。
- `tests/test_seed.py`：种子数据计数与矩阵对称性。
- 目标：测试全部通过，`python -m unittest discover -s tests -v` 零失败。

### 3.2 整体验证
- 全新环境复现：`rm -f app.db && python -m app.seed && uvicorn main:app`，确认一键启动。
- 性能抽查：侦察与推荐接口本地 p95 < 200ms（`time curl` 抽样 20 次）。
- 录制演示视频（≤ 3 分钟）：侦察报告 → 一局选角模拟 → 推荐解释，配英文字幕。

### 3.3 提交
- 推送公开 GitHub 仓库（含 LICENSE 与 README 启动说明）。
- 在 cloud9.devpost.com 注册并提交：仓库链接、演示视频（YouTube 公开）、英文项目描述、Category 2 声明。
- 整理 Best AI-Powered Workflow Story 素材：JetBrains Air 并行开发过程截图 / 记录。

## 风险与应对

| 风险 | 应对 |
|---|---|
| GRID 数据需注册且未必及时获批 | 示例数据先行，GRID 只作为可选项标注，不阻塞开发 |
| Fearless 规则状态机边界复杂 | 状态机集中在 `draft.py`，以单测覆盖全部非法转移 |
| 推荐解释可信度 | 只引用种子数据中的真实对阵数字，不编造胜率 |
| 截止 2027-01-12，时间充裕但需留出录屏与提交缓冲 | 12 月底前完成 Phase 3，1 月初只做打磨与提交 |
