# TraceLens for QNX — QNX 系统可观测性工作台

## 项目概述

TraceLens 是为 QNX Global Hackathon 2026（Developer Tooling & Host Tools 类别）打造的全栈 Web 应用：面向 QNX 8.0 开发者的目标系统可观测性工作台。它解析 QNX 目标系统的 trace 事件与日志流，可视化线程调度时序，自动发现优先级反转、错失截止期、中断风暴等实时系统异常。

- **目标用户**：在 QNX 8.0 上开发车载、机器人、医疗设备的嵌入式工程师。
- **核心价值**：不用 Momentics 重型 IDE 即可在浏览器里看清“系统在某一时刻到底在跑什么”——时间线、CPU 占用、异常清单一次呈现。
- **与 QNX 的真实关联**：解析器按 QNX trace 事件模型实现（线程状态变迁、内核调用、IPC 消息 / 脉冲、中断事件等事件类），数据模型直接对应 QNX 的进程 / 线程 / 通道 / 脉冲概念；内置 trace 生成器可产出符合该事件模型的示例 trace 流，用于无目标硬件演示；README 记录在 QEMU / Raspberry Pi 5 目标机上采集真实 trace 的路径。
- **技术栈**：Python 3.11 + FastAPI（后端）+ SQLite；原生 HTML/CSS/JS 单页前端；零付费 API，全部本地运行。
- **奖项定位**：主攻 Developer Tooling & Host Tools 类别，兼顾 Best Use of QNX-specific Technologies。

## 核心功能

### 1. Trace 上传与解析
- 上传 trace 文件（JSON Lines 格式，每行一个 QNX trace 事件；同时接受 `slog2` 风格日志行）。
- 解析事件类：线程状态变迁（`READY/RUNNING/BLOCKED`）、内核调用进入 / 退出、中断进入 / 退出、IPC 消息发送 / 接收、脉冲（pulse）投递。
- 校验与错误报告：格式错误的行单独列出，不阻塞整文件解析；返回解析统计（总行数、成功数、失败行号）。

### 2. 调度时间线可视化
- Canvas 时间线：横轴为时间，纵轴为线程，色块表示线程状态（运行 / 就绪 / 阻塞），中断事件以标记线叠加。
- 时间范围缩放与拖动；点击色块查看事件详情（线程、时间戳、持续时长、关联 IPC）。
- 线程筛选器（按进程 / 线程名过滤）。

### 3. CPU 与 IPC 统计
- 每进程 / 线程 CPU 占用率、运行 / 就绪 / 阻塞时间占比。
- IPC 统计：通道消息量 Top 列表、脉冲频率、平均消息往返耗时。
- 中断统计：各中断号触发次数与总耗时。

### 4. 异常检测（本地规则引擎，无外部 API）
- **优先级反转**：低优先级线程持有资源期间，高优先级线程阻塞超过阈值。
- **错失截止期**：周期线程实际运行间隔超过设定周期 1.5 倍。
- **中断风暴**：1 秒窗口内同一中断触发超过阈值。
- **消息队列积压**：通道未处理消息数持续超过阈值。
- 每条异常含严重程度、时间范围、涉及线程与修复建议（例如“提高关键线程优先级或改用优先级继承互斥锁”）。

### 5. 示例 Trace 生成器与报告导出
- 内置生成器：按 QNX 事件模型生成含“正常 + 注入异常”的示例 trace（可调线程数、时长、异常种类），无目标硬件也能完整演示。
- 分析报告导出为 JSON；时间线可导出 PNG（Canvas 导出）。

## REST API 端点与 JSON Schema

基础路径：`/api`，响应均为 JSON。错误格式：`{"detail": "<message>"}`。

### Trace 管理

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/traces/upload` | 上传 trace 文件（multipart，字段 `file`） |
| GET | `/api/traces` | trace 列表 |
| GET | `/api/traces/{trace_id}` | trace 元数据与解析统计 |
| DELETE | `/api/traces/{trace_id}` | 删除 trace 及其事件 |
| POST | `/api/traces/generate` | 生成示例 trace |

上传响应：
```json
{
  "trace_id": "tr_01",
  "filename": "qnx-target-01.trace.jsonl",
  "total_lines": 12000,
  "parsed_events": 11982,
  "failed_lines": [{"line": 451, "reason": "unknown event class"}],
  "time_range": {"start_ns": 0, "end_ns": 5000000000},
  "threads": 14
}
```

生成示例请求：
```json
{"threads": 8, "duration_seconds": 10, "inject": ["priority-inversion", "deadline-miss"]}
```

### 事件与时间线

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/traces/{trace_id}/events?thread_id=&event_class=&limit=200&offset=0` | 事件分页查询 |
| GET | `/api/traces/{trace_id}/timeline?start_ns=&end_ns=` | 时间线数据（按线程聚合的状态段） |
| GET | `/api/traces/{trace_id}/stats` | CPU / IPC / 中断统计 |
| GET | `/api/traces/{trace_id}/anomalies` | 异常清单 |

事件 schema（QNX trace 事件模型子集）：
```json
{
  "id": 1024,
  "timestamp_ns": 123456789,
  "event_class": "thread-state",
  "thread_id": 3,
  "thread_name": "sensor-fusion",
  "process": "fusion-svc",
  "old_state": "READY",
  "new_state": "RUNNING",
  "cpu": 1
}
```

时间线响应：
```json
{
  "threads": [
    {"thread_id": 3, "thread_name": "sensor-fusion", "process": "fusion-svc",
     "segments": [{"start_ns": 0, "end_ns": 1200000, "state": "RUNNING"}]}
  ],
  "interrupts": [{"timestamp_ns": 800000, "irq": 42, "duration_ns": 12000}]
}
```

异常 schema：
```json
{
  "id": "an_01",
  "type": "priority-inversion",
  "severity": "high",
  "start_ns": 2100000000,
  "end_ns": 2350000000,
  "threads": ["sensor-fusion", "logger"],
  "description": "高优先级线程 sensor-fusion 被低优先级线程 logger 阻塞 250ms",
  "suggestion": "对共享资源改用优先级继承互斥锁，或提升 logger 的调度策略"
}
```

### 参考与健康检查

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/reference/event-types` | 支持的 QNX 事件类与字段说明 |
| GET | `/api/health` | 健康检查 `{"status": "ok"}` |

## 前端 UI 布局

单页应用，左侧导航 + 主内容区，深色工程仪表主题。

- **顶部栏**：TraceLens 标志、当前 trace 选择器、时间范围显示。
- **左侧导航**：总览 / 时间线 / 统计 / 异常 / 参考。
- **总览页**：四张数据卡（事件总数、线程数、CPU 占用最高线程、异常数）+ 最近上传列表 + “生成示例 trace”快捷按钮。
- **时间线页**（核心页）：Canvas 时间线（线程状态色块 + 中断标记线），上方时间缩放条，左侧线程筛选器，点击色块弹出事件详情。
- **统计页**：CPU 占用条形图、IPC 消息量表、中断统计表。
- **异常页**：异常清单（按严重程度排序，红 / 黄标识），点击展开描述与修复建议。
- **参考页**：支持的 QNX 事件类说明表 + QEMU / Raspberry Pi 5 真实采集路径说明。
- **交互细节**：上传进度与解析统计即时展示；解析失败行可查看；所有操作无整页刷新，失败时中文提示。

## 非功能约束

- **零付费**：不调用任何付费 API；异常检测为本地规则引擎；数据全部本地 SQLite。
- **本地运行**：`pip install -r requirements.txt && uvicorn main:app --reload` 即可启动；前端为 `static/` 下静态文件，由 FastAPI 同源托管。
- **性能**：10 万行以内 trace 文件解析 < 5 秒；时间线接口 p95 < 300ms（本地）；解析采用流式逐行处理，不一次性载入超大文件到内存。
- **真实 QNX 关联**：解析器与数据模型按 QNX trace 事件模型实现；README 明确说明示例 trace 由生成器产出、真实采集路径（QEMU / Raspberry Pi 5 + Momentics trace 导出），不伪装示例数据为真实目标机数据。
- **提交合规**：公开 GitHub 仓库 + 开源 LICENSE；演示视频 < 3 分钟（上传示例 trace → 时间线 → 异常定位全流程）；英文项目描述。
- **可复现**：种子与生成器确定性（固定随机种子可复现同一示例 trace）；README 含一键启动、API 速查与录屏脚本。
