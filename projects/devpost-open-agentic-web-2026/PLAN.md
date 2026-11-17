# AgentBazaar — 实施计划

## 总览

- **技术栈**：Python 3.11 + FastAPI + Uvicorn（后端），纯 HTML/CSS/JS 单页应用（前端，无构建步骤），SQLite（仅本地持久化注册表与调用统计，可替换为内存存储），`unittest`（自动化测试）。
- **仓库结构**：

```text
agentbazaar/
├── app/
│   ├── main.py            # FastAPI 入口、静态文件托管
│   ├── models.py          # Agent / Run 数据模型
│   ├── registry.py        # 注册表、信任分计算
│   ├── engine.py          # 本地规则引擎（三个演示场景）
│   ├── manifest.py        # agent-network.json 生成
│   └── seed.py            # 6 个演示智能体种子数据
├── static/
│   ├── index.html
│   ├── styles.css
│   └── app.js             # 浏览器内 Agent Runtime
├── tests/
│   ├── test_api.py
│   ├── test_trust.py
│   └── test_engine.py
├── requirements.txt
└── README.md
```

- **工期估算**：约 10–14 天（含演示视频录制与 Devpost 提交），截止 2027-01-11，时间充裕。

## Phase 1 — 后端（Backend）

### 1.1 项目骨架
- 创建仓库结构与 `requirements.txt`（`fastapi`、`uvicorn`，其余只用标准库）。
- `app/main.py`：创建 FastAPI 应用，挂载 `static/`，实现 `GET /api/health`。
- 验收：`uvicorn app.main:app --reload` 启动后 `curl localhost:8000/api/health` 返回 `{"status": "ok"}`。

### 1.2 注册表与信任分
- `app/models.py`：定义 `Agent`（`id`、`name`、`description`、`capabilities`、`endpoint`、`price_range`、`hours`、`calls_total`、`calls_ok`、延迟样本）与 `Run`（`run_id`、`scenario`、`steps`）模型。
- `app/registry.py`：实现内存注册表（启动时从 SQLite 加载，写入时同步回写）；实现信任分计算：
  - 可验证性 0–30 分：manifest 可访问且域名一致得满分；
  - 成功率 0–40 分：`calls_ok / calls_total` 线性映射；
  - 延迟 0–30 分：p50 延迟分段给分（<200ms 满分，>2000ms 零分）。
- `app/seed.py`：内置 6 个演示智能体（茶行、花店、书店、维修店、咖啡馆、文具店），覆盖报价、库存、预约三类能力。
- 验收：启动后 `GET /api/agents` 返回 6 条种子数据，信任分均在合理区间。

### 1.3 能力调用与本地规则引擎
- `app/engine.py`：实现三个演示场景的规则执行：
  - `price.quote`：按商品名在内置价目表查价，未命中则按品类返回区间价；
  - `stock.check`：返回确定性库存数（由 `hash(agent_id + item) % 20` 派生，保证可复现）；
  - `appointment.book`：校验时间段是否空闲，生成确认码（`AB-` + 6 位随机码）。
- 实现 `POST /api/agents/{agent_id}/invoke`：校验能力是否存在、记录调用结果、更新成功率与延迟统计。
- 验收：对同一商品连续调用两次返回一致结果；对不存在的能力返回 `ok: false` 与明确 `error`。

### 1.4 Manifest 与发现
- `app/manifest.py`：按 Open Agentic Web 规范生成 `agent-network.json`（从注册表实时聚合）。
- 实现 `GET /.well-known/agent-network.json` 与 `GET /api/discover?url=`（用标准库 `urllib` 抓取，10 秒超时，失败返回结构化错误）。
- 实现 `POST /api/runs` 与 `GET /api/runs/{run_id}`：运行按场景编排多步调用，每步记录 `status` 与 `latency_ms`。
- 验收：`curl /.well-known/agent-network.json` 能被外部解析；`/api/discover` 对本站自身 URL 返回成功，对无效 URL 返回 `ok: false`。

## Phase 2 — 前端（Frontend）

### 2.1 页面骨架与样式
- `static/index.html`：四区布局（导航、集市、演示台、信任榜、设置），语义化标签，无外部依赖。
- `static/styles.css`：暖色市集主题，卡片圆角，信任分三色徽章，响应式（<768px 单列）。
- 验收：直接用浏览器打开 `index.html`（或经 FastAPI 访问）四区完整显示，无控制台报错。

### 2.2 集市与智能体详情
- `static/app.js`：`GET /api/agents` 渲染卡片墙；能力筛选与搜索框实时过滤；点击卡片进入详情抽屉，展示信任分细项与“试调用”表单。
- 验收：筛选与搜索即时生效；试调用一次后卡片上的成功率数字实时更新。

### 2.3 演示台（Playground）
- 场景选择器（比价 / 订单追踪 / 预约）+ 输入表单；点击运行后调用 `POST /api/runs`，轮询 `GET /api/runs/{run_id}`，把步骤逐条追加到时间线。
- 实现暂停 / 单步 / 接管三个控制按钮（接管 = 停止自动轮询，允许用户手动点下一步）。
- 右侧结果汇总面板按场景渲染：最低价对比表 / 物流时间线 / 预约确认码。
- 验收：三个场景全流程可跑通；暂停与单步行为符合预期。

### 2.4 信任榜、跨站调用与设置
- 信任榜：按信任分排序，展示评分细项条形图（纯 CSS 宽度条）。
- 跨站调用角：输入 URL → `GET /api/discover` → 展示对方能力列表 → 一键调用并显示结果与来源标注。
- 设置页：LLM key / base URL 存取 localStorage；“导出 manifest”按钮下载本站 `agent-network.json`；“重置演示数据”恢复种子状态。
- 验收：跨站调用对本站自身 URL 可复现；刷新页面后 LLM 配置仍在。

## Phase 3 — 自动化测试与验证（Automated Tests & Verification）

### 3.1 单元测试与 API 测试
- `tests/test_trust.py`：信任分三项边界测试（零调用、全成功、全失败、延迟极值）。
- `tests/test_engine.py`：三个场景规则引擎测试（确定性：同一输入两次结果一致；非法输入返回明确错误）。
- `tests/test_api.py`：用 FastAPI `TestClient` 覆盖全部端点：健康检查、注册、详情、调用、manifest、discover、runs 全流程。
- 运行：`python -m unittest discover -s tests -v`，目标全部通过。

### 3.2 端到端验证清单
- 一条命令启动：`python -m uvicorn app.main:app --port 8000`，浏览器打开 `http://localhost:8000`。
- 手动走查：注册一个新智能体 → 出现在集市 → 试调用成功 → 信任分变化 → 跑一次比价演示 → 导出 manifest。
- 性能抽查：本地调用 p50 < 300ms（用 20 次调用取中位数）；首页加载 < 2s。
- 规范符合性：对照 `github.com/cognizant-ai-labs/agentic-web` 的规范文档逐项核对 manifest 字段与提交材料清单。

### 3.3 提交材料准备
- 公开部署演示站（Netlify 或等效静态托管 + 后端部署，或录制时使用本地运行画面加公开仓库链接）。
- 录制 `<2 分钟`演示视频：参赛者本人出镜讲解（规则要求，非 AI 生成旁白），展示浏览器内运行画面。
- 准备 2–3 张截图与英文项目描述，在 2027-01-11 16:00 UTC 前于 Devpost 提交。
- 提交后在 Devpost 页面确认状态为已提交，并保留提交截图。
