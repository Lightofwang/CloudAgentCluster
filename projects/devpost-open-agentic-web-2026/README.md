# AgentBazaar — 开放智能体集市与信任注册表
*(Open Agentic Web Marketplace & Decentralized Trust Registry)*

[![Open Agentic Web](https://img.shields.io/badge/Specification-Open%20Agentic%20Web%20v0.1-1e4d3a.svg)](https://github.com/cognizant-ai-labs/agentic-web)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com)
[![Zero-Paid-API](https://img.shields.io/badge/Zero--Paid--API-100%25%20Offline%20Ready-success.svg)](#零付费本地引擎与-byo-llm)
[![Tests](https://img.shields.io/badge/Tests-19%20Passed-brightgreen.svg)](#自动化测试与验证)

---

## 📖 项目简介 (Overview)

**AgentBazaar** 是专为 **Open Agentic Web Challenge**（由 Cognizant 主办，MIT Media Lab NANDA、Mozilla Otari 与 AWS 联合参与）打造的开放智能体网站基础设施与去中心化信任注册表。

**一句话定位**：
> **让没有技术团队的实体小商家、独立手艺人也能拥有一个能被全球 AI 智能体秒级发现、可信验证和直接调用的“智能体门面”**。

在传统互联网中，小商家必须依赖高佣金的中心化聚合平台；而在开放智能体网络（Open Agentic Web）中，只要商家在自身站点发布机器可读的 `/.well-known/agent-network.json` 能力清单，任何个人助理、比价智能体或采购机器人都能自主找到并调用他们。

AgentBazaar 同时解决了两大关键瓶颈：
1. **智能体化门槛高**：提供无需编写复杂后端代码的“智能体门面（Agent Facade）”发布与托管；
2. **多智能体缺乏信任机制**：首创**三维可验证信任度量体系（Tri-Signal Verifiable Trust Registry）**，通过机器可验证的客观数据合成 0–100 的公开信誉分，杜绝虚假调用与恶意节点。

---

## 🌟 核心特性 (Key Features)

### 1. 符合 Open Agentic Web 规范的标准 Manifest
- 任何注册的商家智能体会自动生成符合规范的机器可读清单，统一发布在 `/.well-known/agent-network.json`。
- 外部自治智能体无需注册或登录，直接通过标准 HTTP GET 即可检索全部商家开放的能力端点（如 `price.quote`、`stock.check`、`order.status`、`appointment.book`）。

### 2. 原创三维去中心化信任评分（Tri-Signal Trust Registry）
每个智能体拥有 0–100 的透明信任分，由三项不可篡改的客观信号合成：
- **来源可验证性 (0–30分)**：校验 Manifest 可访问性、Endpoint 域名一致性与签名凭据；
- **历史调用成功率 (0–40分)**：基于实际调用日志动态计算 `round(40 * calls_ok / calls_total)`；
- **响应延迟分位数 (0–30分)**：基于真实请求的 p50 往返耗时进行阶梯计分（p50 < 200ms 得满分 30 分，> 2000ms 归零）。
- 评分细项与历史样本在前端公开展示，低于安全阈值的智能体在调用前会显示风险提示。

### 3. 浏览器内多智能体协同运行时 (In-Browser Agent Runtime)
演示台内置轻量级协同调度引擎，支持三种典型实体商家协作场景：
- **多商家并行比价 (`compare-price`)**：用户输入商品名称与数量，调度器自动在注册表中发现具备 `price.quote` 能力的多个商家智能体，校验信任分后并行发起询价并对比最优总价；
- **跨店订单协同追踪 (`track-order`)**：输入订单号，主调物流智能体与跨商家前置仓协同查询，合成完整的流转时间线；
- **端到端服务预约与核验 (`book-appointment`)**：选择服务与时间段，校验营业排期后锁定名额，生成受信任的 `AB-XXXXXX` 数字核验通行证。
- **人机协同可控性 (Human-in-the-Loop)**：支持协作过程的**暂停 (Pause)**、**单步执行 (Step Next)** 与**人类接管 (Takeover)**。

### 4. 跨站互联与网状发现 (Agent-to-Agent Mesh)
- “跨站调用角”允许输入任意外部兼容站点的 URL，抓取对方的 `agent-network.json`，在本地直接发起跨站能力调用，并明确标注来源站点与信誉。

### 5. 零付费本地引擎与 BYO LLM
- **零付费极速运行**：内置确定性本地规则引擎，无网络外部依赖，演示全流程 100% 离线可跑，p50 延迟仅 100ms；
- **BYO LLM 支持**：用户可在前端设置面板填写个人 OpenAI / Gemini 兼容的 API Key 与 Base URL（仅存储于浏览器 `localStorage`，不经服务端传输），无缝切换到真实大语言模型。

---

## 🏛️ 系统架构 (Architecture)

```text
projects/devpost-open-agentic-web-2026/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI 入口、静态资源路由、CORS
│   ├── models.py          # Agent、Run、Step Pydantic 数据模型
│   ├── registry.py        # 内存/SQLite 注册表、信任分动态计算引擎
│   ├── engine.py          # 本地确定性规则引擎与多智能体协作编排
│   ├── manifest.py        # Open Agentic Web 标准 manifest 生成与外部站点抓取
│   └── seed.py            # 6 个精选种子商家智能体
├── static/
│   ├── index.html         # 单页应用（市集、演示台、信任榜、跨站互联、设置）
│   ├── styles.css         # 暖色市集主题、无 CDN 依赖、纯 CSS 进度条与响应式布局
│   └── app.js             # 浏览器内 Agent Runtime、状态机、单步/暂停控制器
├── tests/
│   ├── test_api.py        # API 端点集成测试
│   ├── test_trust.py      # 信任评分边界与数学模型单元测试
│   └── test_engine.py     # 规则引擎与多智能体协同测试
├── requirements.txt
├── SPEC.md                # 赛事规格书
├── PLAN.md                # 实施规划文档
├── RESULT.md              # 成果与验收报告
└── README.md
```

---

## 🚀 快速上手 (Quickstart)

### 1. 环境准备
确保已安装 Python 3.10+。建议在虚拟环境或系统环境中安装依赖：

```bash
cd projects/devpost-open-agentic-web-2026
pip install -r requirements.txt
```

### 2. 一键启动服务
```bash
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后：
- **Web 应用主页**：打开浏览器访问 [http://localhost:8000](http://localhost:8000)
- **Open Agentic Web 规范清单**：[http://localhost:8000/.well-known/agent-network.json](http://localhost:8000/.well-known/agent-network.json)
- **API 文档 (Swagger UI)**：[http://localhost:8000/docs](http://localhost:8000/docs)
- **健康检查**：[http://localhost:8000/api/health](http://localhost:8000/api/health)

---

## 🔌 REST API 规范 (API Endpoints)

所有接口统一返回 `application/json; charset=utf-8`。

| 方法 | 路径 | 描述 |
|---|---|---|
| `GET` | `/.well-known/agent-network.json` | 获取符合 Open Agentic Web 规范的本站智能体清单 |
| `GET` | `/api/health` | 服务健康检查 |
| `GET` | `/api/agents` | 列出已注册智能体，支持 `?capability=` 与 `?q=` 搜索过滤 |
| `POST` | `/api/agents` | 注册新智能体门面（返回 201 与自动生成的 ID/Endpoint） |
| `GET` | `/api/agents/{agent_id}` | 获取单个智能体详情及来源/成功率/延迟三维信任评分细项 |
| `POST` | `/api/agents/{agent_id}/invoke` | 调用指定智能体的某个具体能力（如 `price.quote`） |
| `GET` | `/api/discover?url=<URL>` | 抓取并解析外部 Open Agentic Web 节点的 manifest |
| `POST` | `/api/runs` | 创建一次多智能体协作任务（比价/订单追踪/服务预约） |
| `GET` | `/api/runs/{run_id}` | 获取协作任务执行步骤时间线与最终决策成果 |
| `POST` | `/api/reset` | 重置数据库至初始 6 个种子商家状态 |

---

## 🧪 自动化测试 (Automated Testing)

运行全量测试套件：

```bash
cd projects/devpost-open-agentic-web-2026
python3 -m unittest discover -s tests -v
```

测试覆盖范围包括：
1. **信任评分单元测试 (`test_trust.py`)**：覆盖理想节点 (100分)、零调用新建节点 (95分)、全失败节点、极端延迟 (>2000ms 归零) 及边界截断；
2. **规则引擎确定性测试 (`test_engine.py`)**：验证同商品重复调用的幂等性、确定性库存派生、预约数字通行证及非法能力校验；
3. **API 端点集成测试 (`test_api.py`)**：使用 FastAPI TestClient 全流程覆盖健康检查、注册、试调用、Manifest 导出、跨站发现与协作场景。

---

## ⚖️ 开源协议 (License)

本项目遵循开放源码协议开源发布，代码可在符合比赛规则的前提下自由分发与研究。
