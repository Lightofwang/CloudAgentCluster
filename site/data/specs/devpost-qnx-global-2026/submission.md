# TraceLens 后续提交清单（QNX Global Hackathon 2026）

## 项目速览

TraceLens 是面向 QNX 8.0 开发者的**主机端系统可观测性工作台**：解析 QNX 内核 trace 事件与 slog2 日志，在浏览器里用 Canvas 时间线可视化线程调度，并自动检测优先级反转、错失截止期、中断风暴、消息队列积压四类实时系统异常，给出修复建议。参赛类别为 **Developer Tooling & Host Tools**（主机工具是官方认可的参赛形态之一）。据项目 RESULT.md，24/24 自动化测试通过，10 万行 trace 解析约 2 秒。

- **代码位置**：CloudAgentCluster 仓库内的项目目录
  https://github.com/Lightofwang/CloudAgentCluster/tree/main/projects/devpost-qnx-global-2026
- **本地运行**：
  ```bash
  cd projects/devpost-qnx-global-2026
  pip install -r requirements.txt
  uvicorn main:app --port 8000
  ```
  然后浏览器打开 `http://localhost:8000`。
- **提交截止**：2026 年 12 月 15 日 14:00 美国东部时间（EST，UTC−5）= **北京时间 2026 年 12 月 16 日 03:00**。请按北京时间 12 月 15 日晚间完成提交，不要卡点。
- **奖金**：总奖金池 $50,000（现金）。本类别 Best of Developer Tooling & Host Tools $4,000、Runner-Up $2,000；另可竞争 Grand Prize $10,000、Best Use of QNX-specific Technologies $3,500、Honorable Mention $1,000。
- **项目时间合规**：项目于 2026-11-18 完成，落在官方提交期（2026-11-02 至 12-15）内，符合「提交期内新建」要求。

---

## 一、演示视频要求

**结论：必需。时长小于 3 分钟，上传 YouTube 并设为公开。**

官方规则原文要点（rules 页 Submission Requirements + 主页 What to Submit）：

- 视频应展示项目「在其所构建的设备上运行」——TraceLens 是主机工具，即展示它在主机（你的电脑）上实际运行的样子。
- 评委不保证观看超过 3 分钟的部分，前 30 秒必须讲清项目是什么。
- 不得使用无授权的第三方商标或版权音乐。
- 语言要求：所有提交材料须为英文，非英文材料必须提供英文翻译——视频请用英文讲解，或至少加英文字幕。

**分步录制脚本（目标总时长约 2 分 30 秒）**

准备：本地启动 TraceLens（`uvicorn main:app --port 8000`），浏览器全屏打开 `http://localhost:8000`；若已完成第四节的「真实数据补救」，提前把真实 QNX trace 文件准备好。

| 时间 | 画面 | 讲解要点（英文） |
|---|---|---|
| 0:00–0:20 | 总览页 | 一句话痛点：QNX 实时系统出问题时，开发者很难看清某一时刻各线程在干什么；TraceLens 把内核 trace 变成浏览器里的时间线。 |
| 0:20–0:50 | 上传/生成 trace | 优先上传真实 QNX 采集的 trace（见第四节）；没有则点「生成示例 trace」并口头说明这是内置生成器产出的示例数据（诚实标注，不要说成真实目标机数据）。展示解析统计（总行数、成功数）。 |
| 0:50–1:30 | 时间线页 | 缩放、拖动时间轴；点击一个线程色块弹出事件详情；指出中断标记线。强调线程状态（RUNNING/READY/BLOCKED）直接对应 QNX 调度。 |
| 1:30–1:55 | 统计页 | CPU 占用、IPC 通道消息量、脉冲频率、中断统计各扫一眼。 |
| 1:55–2:35 | 异常页 | 点开一条「优先级反转」异常，看描述与修复建议；点「在时间线中定位」跳回时间线对应窗口——这是全片高潮。 |
| 2:35–2:55 | 参考页 + 收尾 | 展示 QEMU / Raspberry Pi 5 真实采集路径说明，一句话收尾：TraceLens 让 QNX 8.0 的目标系统行为人人可看、可查。 |

录完后：上传 YouTube、设为公开、把链接回填到第三节的表单里。

---

## 二、公开部署要求

**结论：官方不要求 live URL，不需要部署。**

官方提交物只有三样：公开代码仓库链接、文字描述、演示视频。规则的 Testing 条款明确：评委不一定会实际运行项目，可能仅凭文字描述、图片和视频评审；要求只是项目在评审期结束（2027-01-29）前保持免费、无限制可访问——即**仓库保持公开**即可。

因此：

- 不要为这个比赛做公开部署，把精力放在仓库完整性和视频上。
- 补充说明：本项目是带 Python 后端的 FastAPI 应用，Netlify（GhostFeed 用过的先例）只能托管静态站点、跑不了后端，本来也不适用；Vercel（收不到短信验证码）和 VPS 直部署（暴露公网 IP）同样排除。官方既然不要求，此项直接跳过。

---

## 三、平台表单填写

在 Devpost 的「Enter a Submission」页面填写（字段名以表单实际显示为准，个别可选字段待打开表单确认）：

- **类别（单选，必填）**：`Developer Tooling & Host Tools`
- **代码仓库 URL**：
  `https://github.com/Lightofwang/CloudAgentCluster/tree/main/projects/devpost-qnx-global-2026`
- **演示视频 URL**：第一节录好的 YouTube 公开链接（录完回填）。
- **项目名**：TraceLens for QNX
- **Tagline（英文一句话）**：
  > TraceLens turns raw QNX 8.0 kernel traces into an interactive browser timeline that pinpoints priority inversions, deadline misses, and interrupt storms.
- **文字描述（英文，必填）**——pitch 草稿要点如下，可直接扩写成文：
  1. 问题：QNX 8.0 用在车载、机器人、医疗等实时系统里，调度异常（优先级反转、错失截止期）难以复现和定位，传统做法依赖重型 IDE 和人工翻日志。
  2. 方案：TraceLens 是主机端 Web 工作台，解析 QNX 内核 trace 事件（线程状态变迁、内核调用、中断、IPC 消息、脉冲）与 slog2 日志，生成可缩放的调度时间线，并用本地规则引擎自动检出四类异常并给出修复建议（如改用优先级继承互斥锁）。
  3. **QNX 关联证据段（官方专门要求，务必写）**：指名具体文件供评委核查——`app/qnx_trace.py` 按 QNX 内核事件类实现流式解析；`app/services/` 下的统计与异常模块围绕 QNX 的进程/线程/通道/脉冲概念建模；仓库 README 给出在 QEMU x86_64 与 Raspberry Pi 5 上用 `tracelogger` / `slog2info` 采集真实 QNX 8.0 trace 并导入的完整路径。同时诚实说明：内置生成器（`app/generator.py`）用于无目标硬件时演示，生成的是符合 QNX 事件模型的示例数据。
  4. 工程量佐证：24 个自动化测试全过；10 万行 trace 约 2 秒解析完；零付费 API、纯本地运行。
- **构建与运行说明（规则要求必须写明）**：QNX 版本 = QNX SDP 8.0；目标形态 = 主机工具（Windows/macOS/Linux 主机运行，数据源为 QNX 8.0 目标机，含 QEMU 与 Raspberry Pi 5 采集路径）；工具链 = Python 3.11 + FastAPI（QNX 侧使用 tracelogger / traceprinter / slog2info）。仓库 README 已有 Quickstart，表单里再贴一份简版。
- **Built with 标签（建议）**：`qnx`、`python`、`fastapi`、`sqlite`、`javascript`、`html5-canvas`（表单是否提供该字段及确切写法：待确认）。
- **可选加分项**：Best Codelab / Tutorial 奖金奖（$3,500）需要在表单指定字段填一篇教程/codelab 的 URL——是否参加：待确认（要参加需另写一篇教人在 QNX 8.0 上抓 trace 并用 TraceLens 分析的教程）。Best Use of QNX-specific Technologies（$3,500）无额外字段，靠描述和演示争取。

---

## 四、评审权重与提交前检查

### 评审方式（官方 rules 页第 6 节）

- **第一阶段（pass/fail）**：先过关——项目须契合主题、真正应用了所要求的技术（QNX 8.0）。不过关直接淘汰，不进入评分。
- **第二阶段：四项等权重，各 25%**：
  1. **Technological Implementation（技术实现）**——做得好不好、是否真正有效地用了 QNX 8.0；代码是否体现真实工程量、是否「真正为 QNX 构建或在 QNX 上运行」。同分时先比这一项。
  2. **Design（设计）**——是否是完整连贯的产品体验，而不只是技术验证。
  3. **Potential Impact（潜在影响）**——是否可信、具体地解决 QNX 所服务市场（车载、机器人、医疗等）的真实问题，并说明为什么实时系统底座是正确选择。
  4. **Innovation & AI Creativity（创新性）**——用法是否新颖不显而易见，是否真正理解问题空间。

### ⚠️ 单独重点：QNX 8.0 真实性风险（本项目最大的过关风险）

**官方原文怎么要求：**

- 主页与 rules 页都写明：仓库「必须表明项目真正为 QNX 8.0 构建或在其上运行，而不是仅仅在 README 里写了 QNX 8.0 的名字」（"must show that the project genuinely builds for or runs on QNX 8.0, not merely that QNX 8.0 is named in the README"）。
- 同时官方给主机工具留了合规口径（Evidence of QNX use 一节）：主机端开发工具可以靠「专门用于构建、分析、测试、部署、调试或管理 QNX 8.0 软件的输出或功能」成立；解释型语言、跑在其它操作系统上的工具同样可以合格，前提是**清楚展示与 QNX 的实质关联，并在提交描述中指出相关文件、函数、输出或演示供评委核查**。

**当前成品的差距（诚实清单）：**

1. **演示数据 100% 是模拟的**：目前所有跑通的演示都来自内置确定性 trace 生成器（`app/generator.py`），从未有一份真实 QNX 8.0 目标机的 trace 完整跑通过「采集 → 导入 → 分析」链路。
2. **README 写的转换桥不存在**：README 的 QEMU 采集路径提到用 `qnx-trace-export` 把 `tracelogger` 的原始 trace 转成 JSONL——已核查整个仓库文件树，**这个工具并不存在于代码中**。`tracelogger` 产出的原始 trace 文件目前无法直接导入。
3. **已打通的真实入口只有两条**：slog2 文本日志（解析器已实现且有测试覆盖）和按 TraceLens 自定义 JSONL schema 手工构造的文件。内核 trace 事件这条线还差「真实格式 → JSONL」的转换。

**补救路径（按成本从低到高，提交前至少完成第 1 条）：**

1. **QEMU 真实采集跑通一次**：通过 QNX Everywhere 免费获取 QNX SDP 8.0（非商业使用免费、无需目标硬件），在 QEMU 里启动 QNX 8.0，跑一个小程序并用 `tracelogger` + `slog2info` 采集；把真实 slog2 日志直接导入 TraceLens（已支持），并把 traceprinter 导出的事件转成 JSONL 导入。把这一段录进演示视频——「能分析真实 QNX 数据」从文档承诺变成现场演示，第一阶段过关和技术实现分都靠它。
2. **补上转换桥**：实现 README 里承诺的 `qnx-trace-export`（traceprinter 文本输出 → TraceLens JSONL），让 README 的 Method A 名副其实。
3. **有 Raspberry Pi 5 的话**：在实机上重复第 1 条，视频里出镜实机画面说服力最强（非必需）。

注意：无论补救做到哪一步，描述和视频里都不要把生成器数据说成真实目标机数据——项目 spec 里本来就有这条诚实原则，照做即可。

### 提交前逐项检查

- [ ] 演示视频 < 3 分钟、YouTube 公开、英文讲解或英文字幕、无未授权商标/音乐
- [ ] **仓库根目录补 LICENSE 文件**：官方要求仓库包含开源许可证且能在仓库主页 About 区被识别——目前许可证只在项目子目录里（`projects/devpost-qnx-global-2026/LICENSE`），CloudAgentCluster 仓库根目录没有，GitHub 识别不到。提交前把同一份 LICENSE 放一份到仓库根目录（已核查：根目录 LICENSE 当前不存在）
- [ ] 仓库保持公开，且评审期结束（2027-01-29）前不要转私有、不要删
- [ ] 表单类别选 `Developer Tooling & Host Tools`
- [ ] 英文描述已包含第三节的 QNX 关联证据段（指名 `app/qnx_trace.py` 等具体文件）
- [ ] 构建与运行说明写明 QNX 版本（SDP 8.0）、目标（主机工具 + QEMU/RPi5 采集）、工具链
- [ ] QNX 真实性补救至少完成第 1 条（QEMU 真实采集跑通并录入视频），或已明确接受只靠主机工具口径 + slog2 真实日志参赛
- [ ] 在 Devpost 上先点了 Join Hackathon 完成报名，再走 Enter a Submission 提交
- [ ] 提交完成时间不晚于北京时间 2026-12-16 03:00（建议 12-15 晚间完成）
- [ ] （中奖后才需要，先知道即可）非美国居民需填 W-8BEN 税表、获奖声明须在发出后 10 个工作日内返回——标准 Devpost 领奖流程，无额外 KYC

### 待确认项

- Devpost 提交表单的确切字段构成（Built with 标签字段、Codelab 指定字段的位置）——打开实际表单时核对。
- 是否参加 Best Codelab / Tutorial 奖金奖（需另写教程）——待决定。
- QNX Everywhere / SDP 8.0 的免费许可是否已申请到手——做 QEMU 真实采集前先确认。
