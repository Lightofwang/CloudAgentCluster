# DraftLens — LoL 宏观侦察与 Fearless Draft 管理系统

## 项目概述

DraftLens 是为 Cloud9 × JetBrains Sky's the Limit Hackathon 2026（Category 2：LoL Macro Scouting & Draft Management System）打造的全栈 Web 应用。它把英雄联盟教练赛前准备中最耗时的三件事——战队侦察、宏观数据分析、Ban/Pick 选角模拟——收进一个本地可运行的工作台。

- **目标用户**：职业 / 半职业战队教练、分析师。
- **核心价值**：输入对手战队，即可得到宏观侦察报告（目标控制、视野、经济曲线）；在交互式选角板上模拟 Fearless Draft（全局 BP 规则：系列赛内已选英雄不可重复），并由本地启发式引擎给出选角推荐。
- **技术栈**：Python 3.11 + FastAPI（后端）+ SQLite；原生 HTML/CSS/JS 单页前端（零构建步骤）；零付费 API，全部数据本地内置。
- **数据来源**：内置示例数据集（虚构战队 / 选手 / 对局记录，避免真实赛事数据授权问题）；预留 GRID 官方数据接入点（`GET /api/grid/status` 标注可选接入，GRID 数据为可选项，规则明确说明非必需）。
- **开发工具合规**：全程使用 JetBrains 工具开发（PyCharm / WebStorm + JetBrains Air 智能体并行开发流程），并以此角逐 Best AI-Powered Workflow Story 附加奖。

## 核心功能

### 1. 战队与选手数据库
- 战队列表、详情（胜率、分均目标、风格标签：前期进攻 / 运营后期 / 打架型）。
- 选手列表（位置、分均 KDA、英雄池、近期状态）。
- 对局记录（比分、时长、经济曲线采样点、大小龙 / 先锋 / 男爵控制）。

### 2. 宏观侦察报告（Macro Scouting）
- 选择对手战队与最近 N 场，生成报告：目标控制率（小龙 / 先锋 / 男爵）、场均视野分、一血率、前 15 分钟经济差、阵容偏好（前中期 / 后期）。
- 经济差曲线图（Canvas 折线图）与目标时间轴。

### 3. Fearless Draft 选角模拟器
- 交互式 Ban/Pick 板：蓝红双方按标准顺序轮流 Ban/Pick。
- 全局 BP 规则：同一系列赛（BO3/BO5 多局）内已被选过的英雄自动锁定、不可重复选择。
- 每局结束可结算并进入下一局，历史选角保留在系列赛面板中。

### 4. 选角推荐引擎（本地启发式，无外部 API）
- 基于内置对阵历史与协同 / 克制矩阵打分：`score = matchup_winrate * w1 + synergy * w2 + counter * w3 + player_comfort * w4`。
- 推荐 Top 3 候选英雄并给出理由（例如“对阵胜率 62%，与已选打野协同 +0.18”）。
- 推荐结果可解释、可复核，全部计算在本地完成。

### 5. 历史与导出
- 系列赛历史记录、选角复盘对比；报告导出为 JSON。

## REST API 端点与 JSON Schema

基础路径：`/api`，响应均为 JSON。错误格式：`{"detail": "<message>"}`，HTTP 状态码遵循 REST 惯例。

### 战队与选手

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/teams` | 战队列表（支持 `?style=` 过滤） |
| GET | `/api/teams/{team_id}` | 战队详情 |
| GET | `/api/players?team_id=` | 选手列表 |
| GET | `/api/matches?team_id=&limit=` | 对局记录 |
| GET | `/api/champions` | 英雄列表（含位置、对阵矩阵摘要） |

`Team` schema：
```json
{
  "id": "t01",
  "name": "Nova Lynx",
  "region": "Fictional League",
  "style": "early-aggression",
  "win_rate": 0.68,
  "avg_game_minutes": 31.2,
  "objective_rates": {"dragon": 0.62, "herald": 0.55, "baron": 0.48},
  "first_blood_rate": 0.57,
  "avg_vision_score": 78.4
}
```

`Match` schema：
```json
{
  "id": "m101",
  "team_id": "t01",
  "opponent_id": "t02",
  "result": "win",
  "duration_minutes": 32,
  "gold_diff_curve": [{"minute": 5, "diff": 400}, {"minute": 15, "diff": 1800}],
  "objectives": {"dragons": 3, "barons": 1, "towers": 8}
}
```

### 侦察报告

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/scout/{team_id}?matches=5` | 宏观侦察报告 |

响应：
```json
{
  "team_id": "t01",
  "matches_analyzed": 5,
  "objective_rates": {"dragon": 0.6, "herald": 0.6, "baron": 0.4},
  "avg_vision_score": 76.1,
  "first_blood_rate": 0.6,
  "gold_diff_at_15": 1250,
  "style_summary": "前期进攻型：15 分钟平均领先 1250 经济，优先控小龙",
  "champion_preferences": [{"champion": "Azir", "pick_rate": 0.8}]
}
```

### 选角模拟

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/draft` | 创建系列赛选角会话 |
| GET | `/api/draft/{draft_id}` | 会话状态（含各局 Ban/Pick） |
| POST | `/api/draft/{draft_id}/ban` | Ban 英雄 |
| POST | `/api/draft/{draft_id}/pick` | Pick 英雄 |
| POST | `/api/draft/{draft_id}/recommend` | 获取当前轮次推荐 Top 3 |
| POST | `/api/draft/{draft_id}/next-game` | 结算本局并进入下一局 |
| GET | `/api/draft/{draft_id}/history` | 系列赛历史 |

创建会话请求：
```json
{"blue_team_id": "t01", "red_team_id": "t02", "series_type": "BO3"}
```

Ban/Pick 请求：
```json
{"champion_id": "c012", "side": "blue"}
```

推荐响应：
```json
{
  "recommendations": [
    {"champion_id": "c005", "champion_name": "Sejuani", "score": 0.81,
     "reasons": ["对阵胜率 62%", "与已选打野协同 +0.18", "选手熟练度高"]}
  ]
}
```

Fearless 规则由后端强制执行：已被选英雄再次 Pick 返回 `400 {"detail": "champion already picked in this series (Fearless Draft)"}`。

### 其他

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/grid/status` | GRID 数据接入状态（示例数据模式 / 已接入） |
| GET | `/api/health` | 健康检查 `{"status": "ok"}` |

## 前端 UI 布局

单页应用，左侧导航 + 主内容区，深色电竞主题。

- **顶部栏**：DraftLens 标志、系列赛选择器（BO3/BO5）、当前局数指示。
- **左侧导航**：总览 / 战队 / 侦察报告 / 选角模拟 / 历史。
- **总览页**：四张数据卡（参赛战队数、对局数、英雄数、系列赛数）+ 最近对局表。
- **战队页**：战队卡片网格，点击进入详情（选手表 + 风格雷达描述 + 近 5 场结果）。
- **侦察报告页**：对手选择器 + 报告面板（目标控制率条形图、经济差 Canvas 折线图、阵容偏好表、一句话风格总结）。
- **选角模拟页**（核心页）：中央 Ban/Pick 板（蓝方左、红方右，Ban 区在上、Pick 区在下），右侧英雄池（按位置过滤 + 搜索框，已选英雄置灰锁定），底部推荐面板（Top 3 卡片 + 解释），系列赛历史条。
- **历史页**：已完成系列赛列表与每局选角复盘。
- **交互细节**：所有操作即时反馈（无整页刷新）；`fetch` 调用失败时显示中文错误提示；移动端窄屏时导航折叠。

## 非功能约束

- **零付费**：不调用任何付费 API；推荐引擎为本地启发式计算；数据全部内置 SQLite + JSON 种子文件。
- **本地运行**：`pip install -r requirements.txt && uvicorn main:app --reload` 即可启动；前端为 `static/` 下静态文件，由 FastAPI 同源托管，无跨域问题。
- **性能**：侦察报告与推荐接口 p95 < 200ms（本地）；种子数据量：8 支战队、40 名选手、120 场对局、60 名英雄。
- **可复现**：种子数据脚本幂等（重复运行不产生重复数据）；README 含一键启动、API 速查与录屏脚本。
- **提交合规**：公开 GitHub 仓库 + 开源 LICENSE；演示视频 ≤ 3 分钟（展示侦察报告 + 一局完整选角模拟）；英文项目描述。
- **数据诚实**：示例数据明确标注为虚构演示数据；GRID 为可选项，不伪装成已接入官方数据。
