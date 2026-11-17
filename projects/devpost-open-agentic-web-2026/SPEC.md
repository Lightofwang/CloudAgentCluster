# AgentBazaar — 开放智能体集市与信任注册表

## 项目概述

**赛事**：Open Agentic Web Challenge（Devpost，Cognizant 主办，MIT Media Lab NANDA、Mozilla Otari、AWS 参与）
**截止**：2027-01-11 16:00 UTC（2027-01-12 00:00 CST）
**奖金**：$13,000（现金 $10,000：一等奖 $5,000 / 二等奖 $3,000 / 三等奖 $2,000，另加 Mozilla Otari credits 与周边）

AgentBazaar 是一个符合 Open Agentic Web 规范的**开放智能体网站（open agentic website）**：任何小商家、独立服务都可以在上面发布机器可读的智能体能力清单（manifest），其他智能体可以发现、验证并调用它们；人类用户则可以在浏览器里直接观看、干预多智能体协作的全过程。

一句话定位：**让没有技术团队的小商家也能拥有一个能被别的 AI 智能体找到、信任和调用的“智能体门面”**。

### 为什么能赢

- 直击赛事主题：赛事要的是“开放智能体网络的基础设施与第一批页面”，AgentBazaar 同时覆盖“Agentify a website（把网站智能体化）”与“帮助智能体互相发现与信任的工具”两个参赛方向。
- 评审标准全覆盖：技术实现（符合规范的 manifest + 浏览器 runtime）、设计（完整产品体验而非概念验证）、潜在影响（真实受众：小商家）、创意质量（信任评分是原创机制）。
- 零付费可运行：内置规则驱动的本地智能体引擎，演示全程不调用任何付费 API；同时支持用户自带 LLM key（BYO key）切换到真实模型。

## 核心功能

### 1. 智能体注册表（Agent Registry）
- 商家通过表单发布一个智能体：名称、描述、能力列表（capabilities，如 `order.status`、`price.quote`、`appointment.book`）、调用端点、价格区间、营业时间。
- 每个智能体自动生成一份符合 Open Agentic Web 规范的 manifest，发布在 `/.well-known/agent-network.json`，任何外部智能体无需注册即可读取。
- 注册表支持按能力、关键词、信任分排序检索。

### 2. 信任评分（Trust Score）
- 每个智能体一个 0–100 的信任分，由三项可验证信号合成：来源可验证性（manifest 签名/域名一致性）、历史成功率（调用成功占比）、响应延迟分位数。
- 信任分计算过程完全透明，评分细项在详情页公开；低分智能体在调用前会弹出风险提示。

### 3. 浏览器内 Agent Runtime
- 前端内置一个 JavaScript runtime：加载本站（或任意粘贴 URL 的外部站点）的 `agent-network.json`，在浏览器里运行一个多智能体协作流程。
- 演示场景（默认内置三个演示智能体，全部本地运行）：
  1. **比价智能体**：用户输入商品名，三个商家智能体并行报价并返回最低价。
  2. **订单追踪智能体**：输入订单号，跨商家查询物流状态并汇总时间线。
  3. **预约智能体**：选择服务与时间段，完成一次端到端的预约并生成确认码。
- 每一步调用都以时间线形式实时展示：发现 → 校验信任分 → 调用 → 结果汇总，用户可随时暂停、单步执行或接管。

### 4. 跨站调用演示（Agent-to-Agent）
- 两个 AgentBazaar 实例（或一个实例 + 一个静态演示站）互相发现：A 站的比价智能体调用 B 站的报价能力，返回结果并标注来源站点。
- 演示页提供一键生成“可被调用的演示端点”，让评委在自己的浏览器里复现跨站调用。

### 5. LLM 配置（可选）
- 设置面板允许用户填入自己的 LLM API key 与 base URL（仅保存在浏览器 localStorage，不经过后端）。
- 未配置 key 时，全部演示走本地规则引擎；配置后，智能体的“理解用户意图”和“生成自然语言回复”两步走真实模型，其余步骤不变。

## REST API 端点与 JSON Schema

基础 URL：`http://localhost:8000`，全部返回 `application/json`。

### `GET /api/health`
健康检查。

```json
{"status": "ok", "version": "0.1.0"}
```

### `GET /api/agents`
列出已注册智能体，支持 `?capability=` 与 `?q=` 过滤。

```json
{
  "agents": [
    {
      "id": "shop-tea-001",
      "name": "云雾茶行",
      "description": "本地茶叶店：报价、库存查询、预约品茶",
      "capabilities": ["price.quote", "stock.check", "appointment.book"],
      "endpoint": "http://localhost:8000/api/agents/shop-tea-001/invoke",
      "trust_score": 87,
      "calls_total": 128,
      "calls_ok": 121,
      "p50_latency_ms": 210
    }
  ]
}
```

### `POST /api/agents`
注册一个新智能体。

请求体：

```json
{
  "name": "云雾茶行",
  "description": "本地茶叶店",
  "capabilities": ["price.quote", "stock.check"],
  "price_range": "¥50–¥500",
  "hours": "09:00–21:00"
}
```

响应：`201`，返回含自动生成的 `id`、`endpoint` 与初始 `trust_score` 的智能体对象。

### `GET /api/agents/{agent_id}`
单个智能体详情，含信任分细项：

```json
{
  "id": "shop-tea-001",
  "name": "云雾茶行",
  "trust_score": 87,
  "trust_breakdown": {"verifiable": 30, "success_rate": 37, "latency": 20},
  "capabilities": ["price.quote", "stock.check", "appointment.book"]
}
```

### `POST /api/agents/{agent_id}/invoke`
调用某智能体的一个能力（本地规则引擎执行，零付费）。

请求体：

```json
{"capability": "price.quote", "params": {"item": "龙井 250g", "quantity": 2}}
```

响应：

```json
{
  "agent_id": "shop-tea-001",
  "capability": "price.quote",
  "ok": true,
  "latency_ms": 186,
  "result": {"item": "龙井 250g", "unit_price": 128, "currency": "CNY", "total": 256}
}
```

失败时 `ok` 为 `false`，并返回 `error` 字段；每次调用都会更新该智能体的成功率与延迟统计。

### `GET /.well-known/agent-network.json`
本站的智能体网络 manifest，符合 Open Agentic Web 规范：

```json
{
  "network": "agentbazaar",
  "version": "0.1",
  "agents": [
    {"id": "shop-tea-001", "capabilities": ["price.quote"], "endpoint": "/api/agents/shop-tea-001/invoke"}
  ]
}
```

### `GET /api/discover?url=<外部站点 URL>`
抓取任意外部站点的 `agent-network.json` 并返回解析结果（用于跨站调用演示；失败返回 `ok: false` 与原因）。

### `POST /api/runs`
创建一次多智能体协作运行（比价 / 订单追踪 / 预约三选一）。

请求体：

```json
{"scenario": "compare-price", "input": {"item": "龙井 250g", "quantity": 2}}
```

响应：`201`，返回 `run_id`。

### `GET /api/runs/{run_id}`
查询一次运行的步骤时间线（每步含 `step`、`agent_id`、`status`、`detail`、`latency_ms`）。

## 前端 UI 布局

单页应用，纯 HTML/CSS/JS（无构建步骤），通过 FastAPI 的 `StaticFiles` 托管。

- **顶部导航**：Logo（AgentBazaar）、集市 / 演示台 / 信任榜 / 设置 四个锚点。
- **集市（Marketplace）**：左侧能力筛选（报价、库存、预约等）+ 搜索框；右侧智能体卡片墙，每张卡片显示名称、能力标签、信任分徽章（颜色区分：≥80 绿、50–79 黄、<50 红）、成功率与延迟；点击进详情页，可直接试调用。
- **演示台（Playground）**：三栏布局——左：场景选择与输入表单；中：多智能体协作时间线（实时追加步骤，支持暂停/单步/接管）；右：结果汇总面板（最低价 / 物流时间线 / 预约确认码）。
- **信任榜（Trust Board）**：按信任分排序的榜单，展示评分细项与历史调用统计曲线（纯 CSS/SVG 绘制，无外部图表库）。
- **设置（Settings）**：LLM key 与 base URL 配置（仅存 localStorage）、清空演示数据、导出 manifest 按钮。
- **跨站调用角**：输入任意站点 URL，加载其 `agent-network.json` 并展示可调用能力，一键发起调用。

视觉风格：暖色市集主题（米白底 + 深绿点缀），卡片圆角，信任分用徽章强调；全站响应式，移动端单列。

## 非功能约束

- **零付费运行**：默认演示全程本地规则引擎，不依赖任何付费 API；可选 BYO key，不做服务端存储。
- **合规**：实现严格遵循 `github.com/cognizant-ai-labs/agentic-web` 发布的 Open Agentic Web 规范（以提交期开始时的版本为准）；提交材料为公开站点 URL + `<2 分钟`演示视频（由参赛者本人出镜讲解，非 AI 生成）+ 截图。
- **开源**：按赛事要求，项目代码以开源许可证发布。
- **可复现**：`python -m uvicorn app.main:app` 一条命令启动；种子数据内置 6 个演示智能体，首次启动自动加载。
- **性能**：本地调用 p50 < 300ms；页面首次加载 < 2s（无外部 CDN 依赖）。
- **测试**：后端 `unittest` 覆盖全部 API 端点与信任分计算；前端以静态检查 + 手动演示清单验证。

## 提交注意（风险提示）

- 演示视频必须由参赛者本人出镜讲解（规则明确要求“not AI generated”），需提前安排真人录制，不可用生成式旁白代替。
- 获奖后需完成 Devpost 标准领奖流程：获奖者声明（affidavit）与税务表格（非美国居民为 W-8BEN），规则未要求护照等身份证件上传；奖金以现金（银行转账/支票）发放，非加密货币。
