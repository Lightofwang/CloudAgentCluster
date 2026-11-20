# GraphLens — 后续提交清单（submission.md）

- **比赛**：Relate by Neo4j Hackathon（Devpost）
- **比赛页**：https://relate.devpost.com/ ｜ 规则页：https://relate.devpost.com/rules
- **提交截止**：**2026-12-11 18:00 PST（美国太平洋时间）= 2026-12-12 10:00 CST（北京时间）**，无延期；截止前可修改已提交内容。
- **评审期**：2026-12-12 至 2026-12-16；**获奖公布**：2026-12-17（获奖者须在公布后 7 天内回复邮件，并可能需签署资格宣誓书与免责/肖像授权书，见规则第 7 节）。
- **奖品**：硬件共 3 名——一等奖 Mac Studio（M5 Max, 64GB / 1TB，约 $3,799）、二等奖 Mac mini（M6, 32GB / 512GB，约 $1,499）、三等奖 Mac mini（M6, 16GB / 256GB，约 $899），合计约 $6,197。奖品按「每个获奖作品一份」发放，邮寄到一个地址，关税、进口税等费用由获奖者自理（规则第 6 节）。

---

## 项目速览

GraphLens 是一个本地优先的「连接上下文」Agent 记忆工作台：把非结构化的笔记、文档和 Agent 执行轨迹，变成一张可交互探索、可 Cypher 查询、答案可溯源的知识图谱。它解决的问题是：Agent 和个人知识散落在互不关联的文本里，找关系、查来历全靠人脑；GraphLens 用规则抽取器（零付费 API、完全离线）把实体与关系抽出来，存进 Relate 嵌入式图数据库（Neo4j 出品，进程内运行，单文件持久化 `./data/graphlens.rl`），并提供图谱画布、Cypher 控制台和带路径引用的「Ask」图谱问答——每个答案都标注它依据的图路径，评委可逐项检视。

- **代码位置**：GitHub 仓库 `Lightofwang/CloudAgentCluster` 的 `projects/devpost-relate-neo4j-2026/` 目录
  - 仓库：https://github.com/Lightofwang/CloudAgentCluster/tree/main/projects/devpost-relate-neo4j-2026
- **技术栈**：FastAPI 后端 + 原生 HTML/CSS/JS 前端 + Relate（`relate-db` 1.0.1，openCypher 25）；21 个自动化测试全部通过；MIT 协议。
- **本地运行**（Python 3.11+，无需任何 API key）：

```bash
cd projects/devpost-relate-neo4j-2026
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000
# 浏览器打开 http://localhost:8000
```

---

## 一、演示视频要求

### 结论

- **需要录视频**。比赛主页的 SUBMISSION CHECKLIST 把「Demo video, 1-2 minutes」列为提交必备项；规则第 4 节的表述是 demo 二选一：**一段最长 2 分钟的视频，或一个可用的在线 demo 链接**（可另附截图）。本项目没有公开部署（见第二节），所以走视频路线。
- **时长**：1–2 分钟（主页要求），硬上限 2 分钟（规则第 4 节）。
- **形式**：屏幕录制或幻灯片演示都可以（主页原文：a screen share or presentation is fine）。
- **平台**：规则没有指定上传平台，只要求视频是本人原创（拍摄、剪辑、画面设计都算），用到的音乐/图片等第三方素材必须有授权，且**评委无需登录、无需付费即可观看**。Devpost 提交表单一般粘贴 YouTube / Vimeo 链接——**具体接受哪些平台以提交表单实际提示为准（待确认）**。
- **语言**：规则未规定视频语言（待确认）。稳妥做法：英文旁白，或中文讲解 + 英文字幕。

### 录制脚本（按时间轴，总长控制在 1:40–2:00）

录制前：本地按上面命令启动应用，浏览器全屏打开 `http://localhost:8000`，先完整跑一遍流程确认无卡顿；图谱画布是深色主题，录制时把浏览器缩放调到 100%–125% 保证文字可读。

| 时间 | 画面 | 讲解要点 |
|---|---|---|
| 0:00–0:10 | 打开首页，鼠标点顶部 **「⚡ Load Demo Data」** | 一句话开场：GraphLens 把笔记和 Agent 轨迹变成可查询的知识图谱，全部跑在本地的 Relate 嵌入式图数据库里；演示数据 1 秒内载入 12 篇文档、61 个实体、250+ 条关系，图谱画布即时生成。 |
| 0:10–0:25 | 点击图谱中的 **「GhostFeed」** 或 **「Alice」** 节点 | 右侧检查器展示该节点的属性、度数和 1 跳邻居及关系方向——图不是图片，是可检视的活数据。 |
| 0:25–0:50 | 切到左侧 **「Ask」** 标签，提问 **"What is Alice working on?"** | 展示回答 "Alice works on AgentMem and GhostFeed." 以及内联引用 `[Person:Alice] -WORKS_ON-> [Project:GhostFeed]`；展开 "Why this answer?" 面板，露出实际执行的 Cypher 和证据片段——答案零幻觉、全程可溯源，这是最高分维度（Connected context）的核心卖点。 |
| 0:50–1:10 | 点开底部 **Cypher 控制台**，运行示例查询 `MATCH (p:Person)-[:WORKS_ON]->(j:Project) RETURN p.name AS person, j.name AS project` | 强调这是进程内的真 Cypher 引擎（openCypher 25），不是 mock；结果表格即时渲染，并显示毫秒级耗时。 |
| 1:10–1:35 | 切到 **Ingest** 标签，粘贴一句新笔记（如 *"Sarah leads NeoFlow using Python and Docker."*），点 **「Extract & Ingest Note」** | 画布上新节点、新关系实时出现——证明抽取是实时、确定性的，且不需要任何云端 LLM API。 |
| 1:35–2:00 | 点顶部 **「💾 Export .rl」** 下载存储文件；最后切回完整图谱画面收尾 | 收尾句：整个图谱持久化在一个 `.rl` 单文件里，评委可以用 Relate 官方工具打开检视；代码、README、21 个测试都在公开仓库里，clone 下来一分钟就能跑。 |

---

## 二、公开部署要求

### 结论：不需要 live URL，不用部署。

- 规则第 4 节对 demo 的要求是「视频 **或** 在线 demo 链接」二选一；比赛主页明确评委的验证方式是「clone 仓库、本地运行、检视图谱」（Judges should be able to clone it, run it, and see your graph）。录好第一节的视频即满足要求，**不要为这个比赛做公开部署**。
- 参考（仅备查，本次用不上）：本应用是 FastAPI（Python）后端，Netlify 只能托管静态站点与云函数、跑不了这个后端；Vercel 因收不到短信验证码不可用；用户 VPS 直部署会暴露公网 IP，不采用。若日后确实想补一个在线 demo，需要能跑 Python 的托管平台，**可行性待确认**，且不是本比赛的要求。

---

## 三、平台表单填写

提交入口：在 https://relate.devpost.com/ 注册并提交（先点比赛页的注册按钮，再填项目表单）。本比赛**没有赛道/类别划分**（主页原文：Your idea doesn't have to fit a category），所有作品统一评审。

### 规则第 4 节规定的提交内容（逐项备齐）

1. **项目标题与描述**：做什么、为什么有用（文案见下方 pitch 草稿）。
2. **公开 GitHub 仓库链接**：填 `https://github.com/Lightofwang/CloudAgentCluster`，并在描述开头写清项目位于 `projects/devpost-relate-neo4j-2026/` 子目录（本项目在 monorepo 里，不是独立仓库）。
3. **Setup 说明**：让评委能照着安装运行——项目 README 的 Quick Start 已覆盖，表单里再贴一遍核心三步命令即可。
4. **Demo**：第一节的视频链接；可另附 2–3 张截图（图谱全景、Ask 引用面板、Cypher 控制台各一张）。
5. **工具与 AI 使用声明（必填，别漏）**：规则第 4 节要求声明所用的 Product 能力、第三方工具和 AI 工具；第 3 节明确「使用 AI 编程工具必须在提交中描述重要的 AI 使用」。照实写，草稿见下。

### 关键动作：给仓库加 GitHub topic 标签（硬性要求）

- 规则第 3、4 节 + 主页：提交仓库**必须**带 GitHub topic **`relate`**，没有这个标签提交可能被视为不完整；推荐同时加 **`relate-neo4j-hackathon`**。仓库须保持公开并带标签，直到评审结束和获奖公布之后。
- 操作：打开仓库页 → 右侧 About 旁的齿轮图标 → Topics 里输入 `relate` 回车（再加 `relate-neo4j-hackathon`）→ Save changes。
- **当前状态：待确认**——抓取到的仓库页文本没有显示 topics 信息，提交前务必打开仓库页亲眼确认这两个标签已加上（加在 `Lightofwang/CloudAgentCluster` 仓库上）。

### Tagline（一句话，英文，可直接粘贴）

> GraphLens turns your notes and agent traces into a queryable knowledge graph — powered by Relate, 100% local, every answer traceable to the graph.

### 项目介绍 pitch（英文草稿，可直接粘贴后微调）

> **The problem.** AI agents and personal knowledge work drown in disconnected text: notes, docs, and execution traces that never link to each other. The relationships — who works on what, which step touched which entity — are exactly what gets lost.
>
> **What GraphLens does.** GraphLens ingests plain-text notes and agent traces, extracts people, projects, topics, tools, and dates with a transparent rule-based extractor (no LLM API, fully offline), and stores them as a Cypher property graph. You can explore the graph on an interactive canvas, query it in a live Cypher console, and ask questions in the "Ask" tab — answers are composed only from retrieved graph paths and cite them inline, e.g. `[Person:Alice] -WORKS_ON-> [Project:GhostFeed]`, with a "Why this answer?" panel showing the exact Cypher and evidence used.
>
> **How it uses Relate — and why.** Relate is the core of the product, not a storage afterthought: every feature reads from and writes to the embedded store. We chose the **single-file mode** (`./data/graphlens.rl`) so the whole graph is one portable, persistent artifact that judges can download from the app ("Export .rl") and inspect with Relate's own tooling. Entities are deduplicated with Cypher `MERGE`, multi-hop questions are answered with graph traversals including `shortestPath`, and agent runs are recorded as `(:Step)-[:NEXT]->(:Step)` chains linked to the entities they `[:TOUCHES]`. In-process embedding means zero servers, zero signups, zero data leaving the machine.
>
> **Built with:** Python, FastAPI, Relate (`relate-db` 1.0.1, openCypher 25), vanilla HTML/CSS/JS. 21 automated tests, all passing. No paid API keys anywhere.

### 工具与 AI 使用声明（英文草稿）

> **Product capabilities used:** Relate embedded library (Python, `relate-db` 1.0.1), single-file persistent store, openCypher 25 queries including `MERGE`, graph traversals and `shortestPath`. **Third-party tools:** FastAPI / Uvicorn; all other code is dependency-light vanilla Python and JavaScript. **AI tools:** This project was designed and implemented with substantial assistance from AI coding agents (spec drafting, implementation, and test generation), with all code reviewed, run, and verified locally — 21 automated tests pass. No AI/LLM calls happen at runtime; extraction and question answering are deterministic and rule-based.

### 「Built with」标签建议

Devpost 表单的 Built with 字段可填：`python`、`fastapi`、`relate`、`neo4j`、`cypher`、`javascript`（字段的具体名称与可选值以提交表单实际显示为准，待确认）。

### README 对照官方模板（提交前核一遍）

主页给了 README 模板，要求**直接回答 "how are you using Relate, and why?"**，并包含：模式（in memory / directory / single file）与选择理由、图谱建模了什么、Setup and run、数据存放路径（Where the data lives）。项目现有 README 第 1 节已按此结构写明（模式：single file，路径 `./data/graphlens.rl`），提交前再逐项对照确认没有缺项即可。

### 其他合规要点

- **资格**：参赛者须年满 18 岁；一人只能用一个身份参赛；Neo4j 员工及政府机构雇员等不可参赛（规则第 2 节）。
- **新项目要求**：项目必须在 2026-11-11 之后新建（规则第 3 节）——GraphLens 于 2026-11-16 完成，符合。
- **持久化存储**：主页清单要求提交里包含评委可检视的持久化 Relate store（目录或单文件）。本项目为 `./data/graphlens.rl` 单文件：**该文件当前是否已提交进仓库，待确认**；若没有，评委也可启动后点 Load Demo Data 一键生成、再 Export .rl 导出检视（视频 1:35 处已演示这一步），并在表单描述里写明这一点。

---

## 四、评审权重与提交前检查

### 评审维度与权重

比赛主页公布的分值（总分 100）：

| 维度 | 分值 | 对应本项目的发力点 |
|---|---|---|
| Relate and connected context（Relate 与连接上下文的有效使用） | **30** | 最高分项：视频里 Ask 的路径引用、shortestPath、.rl 导出检视都要露出来；pitch 里写清 single-file 模式的选择理由 |
| Functionality and completeness（功能与完整度） | **25** | 一键 Load Demo Data、实时入库、Cypher 控制台都真实可用；21 个测试通过写进描述 |
| Usefulness（实用性） | **20** | 描述开头讲清「Agent 上下文碎片化」这个真实问题和受益人群 |
| Documentation and reproducibility（文档与可复现性） | **15** | README 对照官方模板；确保评委 clone 后 1 分钟内能跑起来 |
| Creativity（创意） | **10** | 「Agent 执行轨迹入图 + 答案可溯源」这个角度在描述里点明 |

**口径差异提示（待确认）**：规则第 5 节的文字称五项标准为「同等权重（weighted equally）」，且名称略有不同（Creativity、Usefulness、Completeness、Clarity、Effective use of connected context），与主页公布的分值表不一致。两个口径下结论相同：**Relate 的有效使用 + 完整可运行**是核心，按主页分值表准备即可；如需较真，以 Devpost 比赛页的最新公布为准。

### 提交前逐项勾选清单

- [ ] 仓库 `Lightofwang/CloudAgentCluster` 已加 GitHub topic **`relate`**（必需）和 **`relate-neo4j-hackathon`**（推荐），且仓库为公开状态
- [ ] 在一台干净环境（或新目录）里按 README 三步命令实测：clone → `pip install -r requirements.txt` → `python -m uvicorn app.main:app --port 8000` → 打开 http://localhost:8000 正常出图谱
- [ ] 点 Load Demo Data、Ask 提问、Cypher 控制台、粘贴新笔记、Export .rl 五个动作逐个实测可用
- [ ] 跑一遍测试：`python -m unittest discover -s tests -v`，确认 21 个测试全过
- [ ] 确认 `./data/graphlens.rl` 持久化文件已在仓库中，或在表单描述中写明「启动后一键生成并可导出」**（待确认）**
- [ ] README 对照官方模板四项（如何用 Relate 及原因 / 模式与理由 / 图谱建模 / 数据路径）无缺项
- [ ] 演示视频已录：时长在 1–2 分钟内，按第一节脚本走完六个镜头，评委免登录可看
- [ ] Devpost 表单：标题、tagline、pitch 描述已填；描述开头注明项目子目录路径 `projects/devpost-relate-neo4j-2026/`
- [ ] Devpost 表单：仓库链接、视频链接、2–3 张截图已填
- [ ] Devpost 表单：工具与 AI 使用声明已填（Relate 能力 + 第三方工具 + AI 辅助开发说明）
- [ ] Built with 标签已填（字段以表单实际显示为准，待确认）
- [ ] 提交后回到比赛页确认作品状态为已提交，且赶在 **2026-12-12 10:00 CST** 截止之前
- [ ] 12 月 17 日公布获奖后留意注册邮箱：若获奖，7 天内回复邮件并按要求提供邮寄地址与税务文件

---

*本清单依据 2026-11-20 抓取的比赛主页、官方规则页与项目 README / RESULT.md 整理；标注「待确认」处为官方页面未写明或抓取信息不足，提交时以 Devpost 表单与比赛页的实际显示为准。*
