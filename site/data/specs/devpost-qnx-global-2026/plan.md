# TraceLens for QNX 实施计划

## Phase 0 — 准备（0.5 天）

- 初始化仓库：`README.md`（项目介绍、QNX 关联说明、启动方式）、`LICENSE`（MIT）、`.gitignore`。
- 精读 QNX 8.0 trace 事件模型公开文档，确定解析器支持的事件类子集：线程状态变迁、内核调用、IPC 消息 / 脉冲、中断进入 / 退出。
- 确定技术栈版本：Python 3.11、FastAPI 0.110+、uvicorn、SQLite（标准库 `sqlite3`）、前端零框架。
- 设计示例 trace 生成器的输出格式（JSON Lines，每行一个事件），与解析器共用同一 schema。

## Phase 1 — 后端（2.5 天）

### 1.1 数据层与解析器
- `app/db.py`：SQLite 建表（`traces`、`events`、`anomalies`），事件表按 `trace_id + timestamp_ns` 建索引。
- `app/qnx_trace.py`：QNX trace 事件解析器——逐行流式解析 JSON Lines，校验事件类与必填字段，格式错误行收集进 `failed_lines` 不中断解析。
- `app/generator.py`：示例 trace 生成器（固定随机种子可复现），可调线程数、时长、可注入异常（优先级反转、错失截止期、中断风暴、消息积压）。

### 1.2 Trace 管理接口
- `POST /api/traces/upload`（multipart 上传，限制 50MB）、`GET /api/traces`、`GET /api/traces/{id}`、`DELETE /api/traces/{id}`、`POST /api/traces/generate`。
- 上传后异步解析改为同步解析（10 万行 < 5 秒目标内直接同步返回统计，避免任务队列复杂度）。

### 1.3 时间线与统计
- `app/services/timeline.py`：由线程状态事件聚合成状态段（合并相邻同状态区间），返回时间线 JSON；中断事件单独序列。
- `app/services/stats.py`：CPU 占用（运行态时长 / 总时长）、IPC 消息量与往返耗时、中断次数与耗时统计。
- `GET /api/traces/{id}/events`（分页 + `thread_id` / `event_class` 过滤）、`/timeline`、`/stats`。

### 1.4 异常检测规则引擎
- `app/services/anomalies.py`：四条规则（优先级反转、错失截止期、中断风暴、消息队列积压），阈值集中在 `app/rules.py` 常量中可调。
- `GET /api/traces/{id}/anomalies`：返回异常清单（严重程度排序）+ 每条的描述与修复建议。
- `GET /api/reference/event-types`：支持的事件类说明；`GET /api/health` 健康检查。

### 1.5 后端验收
- 生成含 4 类注入异常的示例 trace，逐条核对异常检测输出与注入点一致（时间窗口误差 < 5%）。
- 上传含 20 行格式错误的 trace，确认解析统计正确且其余事件完整入库。
- 记录 5 条以上 curl 示例进 README。

## Phase 2 — 前端（2 天）

### 2.1 骨架与样式
- `static/index.html`、`static/css/style.css`、`static/js/app.js`；深色工程仪表主题、响应式布局。
- 顶部栏 + 左侧导航 + 主内容区；五个页面以 JS hash 路由切换。

### 2.2 页面实现
- **总览页**：数据卡 + 最近上传列表 + “生成示例 trace”按钮（调用 `POST /api/traces/generate`）。
- **时间线页**（重点）：Canvas 渲染线程状态色块 + 中断标记线；时间缩放条（range input 控制窗口）；线程筛选器；点击色块弹出事件详情浮层。
- **统计页**：CPU 占用条形图（Canvas）、IPC 消息量表、中断统计表。
- **异常页**：异常清单（严重程度颜色标识），点击展开描述与修复建议。
- **参考页**：事件类说明表 + QEMU / Raspberry Pi 5 真实采集路径说明。

### 2.3 前后端联调
- 统一 `api.js` 封装 `fetch` + 中文错误提示；上传进度条；空状态引导文案。
- 浏览器端到端走查：生成示例 trace → 时间线渲染 → 异常页定位到注入的优先级反转。

## Phase 3 — 自动化测试与验证（1 天）

### 3.1 自动化测试
- `tests/test_parser.py`（unittest）：各事件类解析、错误行收集、超大行数流式解析不爆内存。
- `tests/test_api.py`（FastAPI TestClient）：上传 / 生成 / 事件分页 / 时间线聚合 / 统计 / 异常接口。
- `tests/test_anomalies.py`：四条规则各构造最小复现 trace，断言检出且无误报（纯净 trace 零异常）。
- 目标：`python -m unittest discover -s tests -v` 全部通过。

### 3.2 整体验证
- 全新环境复现：`rm -f app.db && uvicorn main:app`，确认一键启动。
- 性能抽查：10 万行示例 trace 上传解析 < 5 秒，时间线接口本地 p95 < 300ms。
- 录制演示视频（< 3 分钟）：生成示例 trace → 时间线 → 异常定位全流程，配英文字幕。

### 3.3 提交
- 推送公开 GitHub 仓库（含 LICENSE 与 README 启动说明 + QEMU 真实采集路径）。
- 在 qnx.devpost.com 注册并提交：仓库链接、演示视频（YouTube 公开）、英文项目描述、Developer Tooling & Host Tools 类别声明。
- 如时间允许，尝试在 QEMU 中跑 QNX 8.0 并采集一段真实 trace 作为加分素材（非阻塞项）。

## 风险与应对

| 风险 | 应对 |
|---|---|
| QNX trace 事件模型细节理解偏差 | 只实现文档明确的事件类子集；参考页如实说明支持范围，不夸大覆盖面 |
| 无目标硬件，无法验证真实 trace | 示例生成器 + QEMU 采集路径并行；生成器输出即解析器输入，闭环自洽 |
| 10 万行解析性能 | 流式逐行解析 + 批量入库（每 1000 行一次事务提交） |
| 截止 2026-12-15，仅 27 天 | 12 月 10 日前完成 Phase 3，留 5 天缓冲用于录屏与提交 |
