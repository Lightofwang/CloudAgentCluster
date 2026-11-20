# DraftLens 后续提交清单（submission.md）

比赛：Cloud9 × JetBrains Sky's the Limit Hackathon 2026（Devpost）
项目 slug：`devpost-skys-the-limit-2026`
**提交截止：2027-01-12 11:00 太平洋时间（PST, UTC-8）= 北京时间 2027-01-13 03:00 CST**
评审期：2027-01-27 – 2027-02-03（PT）；获奖公布约 2027-02-08（PT）。项目在评审期结束前必须保持可免费、无限制地访问测试。

## 项目速览

DraftLens 是为英雄联盟教练/分析师打造的本地工作台，把赛前三件事收进一个应用：对手宏观侦察报告（目标控制率、视野、前 15 分钟经济差、经济曲线图）、支持 Fearless Draft 全局 BP 规则的 Ban/Pick 选角模拟器（一局选过的英雄在整个系列赛内锁定）、以及给出可解释理由的本地启发式选角推荐引擎（Top 3）。技术栈为 FastAPI + SQLite + 原生 HTML/CSS/JS 单页前端，零付费 API、零外部依赖，内置虚构示例数据（8 队 / 40 选手 / 60 英雄 / 120 场对局），并预留 GRID 官方数据接入点（GRID 为可选项，官方明确非必需）。16 个单元测试全部通过（见 RESULT.md）。

- 代码位置：https://github.com/Lightofwang/CloudAgentCluster/tree/main/projects/devpost-skys-the-limit-2026 （`projects/devpost-skys-the-limit-2026/`）
- 本地运行：`pip install -r requirements.txt` → `python3 -m app.seed` → `uvicorn main:app --port 8000`，浏览器打开 http://localhost:8000

## 一、演示视频要求

- **是否必需：必需。** 官方 Rules 的 Submission Requirements 明确要求提交演示视频。
- **时长：小于 3 分钟**（Rules 原文：视频 "should be less than three (3) minutes"，且评委没有义务看超过 3 分钟的部分）。建议成片控制在 2 分 30 秒 – 2 分 50 秒。
- **平台：YouTube，必须公开可见**，并把链接填到 Devpost 提交表单。
- **内容要求**：必须展示项目在目标设备上真实运行的画面；不得使用无授权的第三方商标、版权音乐等素材。
- **语言**：所有提交材料必须为英文，或提供英文翻译（视频可用英文字幕）。

录制脚本（本地启动应用后录屏，总时长 ≤ 2:50）：

1. **0:00–0:20 开场**：一句话讲清问题——教练赛前靠电子表格做侦察和 BP 准备，慢且易错；DraftLens 把侦察 + Fearless Draft 模拟 + 选角推荐收进一个本地工作台。
2. **0:20–1:00 宏观侦察报告**：打开侦察报告页，选择对手战队 → 展示目标控制率（小龙/先锋/男爵）、场均视野分、前 15 分钟经济差、经济差曲线图和一句话风格总结。
3. **1:00–2:10 Fearless Draft 模拟（核心段）**：创建 BO3 系列赛 → 在选角板上完成一局 Ban/Pick → 点开推荐面板，展示 Top 3 推荐及理由（如"对阵胜率 62%，与已选打野协同 +0.18"）→ 结算进入第 2 局 → 故意点一个第 1 局已选英雄，展示被置灰锁定 / 后端 400 拒绝（Fearless 规则生效）。
4. **2:10–2:35 战队与数据**：快速扫过战队列表/详情（选手英雄池、风格标签），说明数据全部本地内置、零付费 API，并预留了 GRID 接入点。
5. **2:35–2:50 收尾**：说明开发工具链（PyCharm 后端、WebStorm 前端、AI 辅助工作流），回到标题画面结束。

## 二、公开部署要求

- **是否需要 live URL：需要。** DraftLens 是网站类项目，Rules 要求 "Provide a link to a working demo if your project is a website"；且评审期结束（2027-02-03）前项目必须保持免费、无限制可测。只给仓库 + 安装说明是给非网站项目的备选路径，本项目应按网站标准交公开演示链接。
- **部署方案（受用户约束）**：
  - ❌ 不能用 Vercel（收不到短信验证码）；❌ 不能在用户自己的 VPS 上直部署（暴露公网 IP）。
  - ⚠️ Netlify 是 GhostFeed 已验证可行的先例，但 Netlify 托管不了 Python 后端——本项目是 FastAPI 应用，需要支持 Python 的免费托管（如 Render / Hugging Face Spaces 一类，具体平台与免费额度、休眠策略**待确认**后再定）。
  - 部署后自检：首页打开、侦察报告接口、选角模拟全流程各点一遍；确认种子数据已初始化（线上环境也要跑一次 `python3 -m app.seed` 或等价初始化）。
  - 演示链接至少保持在线到 2027-02-03 评审结束。

## 三、平台表单填写

- **先确认报名**：提交前先在比赛页点过 "Join Hackathon" 完成报名（报名后官方会邮件发放 JetBrains 试用码：1 个 All Products Pack 码 + 1 个 AI Ultimate 码，约 5 个工作日内）。
- **类别（Category）**：选 **Category 2 (LoL): Macro Scouting & Draft Management System**（奖项全称 "Best of Category 2 (LoL): League of Legends Macro Scouting & Draft Management System"）。本项目同时覆盖该类别的两个官方 blueprint：automated Macro Scouting Tool 与 Modular Draft Organizer supporting Fearless Draft rules。只能选一个类别。
- **代码仓库**：填 GitHub 公开仓库链接（上方项目速览中的链接）。官方要求仓库含全部源码 + 运行说明，且根目录有可被 GitHub 识别的开源 LICENSE。⚠️ 现状：项目子目录内有 LICENSE，但 CloudAgentCluster 仓库根目录没有 LICENSE 文件，GitHub 仓库主页 About 区不会显示 license——提交前**待确认/待决定**：是给仓库根补 LICENSE，还是在描述中注明子目录 LICENSE 位置。
- **Tagline（英文一句话）**：
  > DraftLens — LoL macro scouting and Fearless Draft management for coaches: scouting reports, draft simulation, and explainable pick recommendations in one local workbench.
- **项目描述（Text description）要点**：必须写清功能，并**逐项说明用了哪些 JetBrains 工具、各自做了什么**（这是硬性要求，也是评审第一维度）。英文草稿要点：
  - Problem: pre-match prep for LoL coaches is scattered across spreadsheets — scouting, macro stats, and draft planning are slow and error-prone.
  - What DraftLens does: (1) macro scouting reports (objective control, vision, gold-diff curves, style summary); (2) a Fearless Draft simulator enforcing the global ban/pick lock across a BO3/BO5 series; (3) a deterministic local recommendation engine returning Top 3 picks with human-readable reasons.
  - Built with JetBrains tools: **PyCharm** for the FastAPI backend, SQLite schema and test suite; **WebStorm** for the single-page frontend and Canvas charting; AI-assisted workflow throughout (与仓库 README 的 JetBrains Development Workflow 一节保持一致)。
  - Zero paid APIs, fully local SQLite demo data (clearly fictional), GRID data integration point reserved (`GET /api/grid/status`); 16 automated tests passing.
- **Methodology write-up（必需，简短一段）**：说明方法与如何解决类别问题——把侦察聚合、Fearless 状态机、启发式打分（对阵胜率/协同/克制/选手熟练度加权）全部放在本地确定性计算，保证教练可复核每条推荐的理由；示例数据用虚构战队避免真实赛事数据授权问题。
- **附加奖（可选，建议顺手交）**：Bonus Prize "Best AI-Powered Workflow Story"（$1,000 现金）——需提供一个直达链接：一篇案例文（博客/文档）或短视频，或仓库内的 `AI_SHOWCASE.md`。⚠️ 仓库目前没有 `AI_SHOWCASE.md`，想角逐需另行补写并在表单填链接。
- **JetBrains 使用证据（风险项）**：官方鼓励把 `.idea`、`.junie` 或 `.air` 文件夹一并提交作为使用证据；当前仓库中没有这些文件夹。且评审 Stage One 是 pass/fail 关，会核查项目是否合理贴合主题并真实使用了 JetBrains 工具——提交前**待确认**如何补齐证据（补交文件夹或在描述中充分说明），这是本项目最大的合规风险点。
- **表单精确字段与 "Built with" 标签列表**：需登录 Devpost 提交表单逐项核对，**待确认**（官方页面未公开完整字段清单）。
- **备注 — GDC 差旅奖励与美签**：Category 2 第一名（Best of）奖品为 $6,000 现金 + $100 Cloud9 商店礼品卡 + JetBrains All Products Pack 一年订阅 + **GDC 2027（旧金山）门票及全包差旅**（往返经济舱机票 + 酒店，至多 5 晚，由主办方订票订房；获奖者需提供出发机场信息并确认能出席）。Rules 第 8(D) 条明确：**获奖者自行负责办理美国签证等入境许可；若因签证等任何原因无法出席，GDC 门票与差旅作废，但现金等其余奖品仍可领取。** 用户在中国、无美签——差旅部分大概率用不上，但不影响 $6,000 现金主体。第二名（Runner-up）为 $2,000 现金 + 礼品卡 + 订阅，不含 GDC。
- **获奖后行政事项（先知道即可）**：获奖需通过身份/资格/创作角色核验，签 affidavit 等 Required Forms 并在收到后 10 个工作日内返回；非美国居民通常需填 W-8BEN 税表；奖品在表格收齐后 60 天内发放。

## 四、评审权重与提交前检查

官方评审分两段：Stage One 为 pass/fail（主题契合 + 真实使用 JetBrains 工具）；Stage Two 五个维度**等权重，各占 20%**：

| 维度 | 权重 | 官方问法 | 本项目对应动作 |
|---|---|---|---|
| Technological Implementation | 20% | 是否充分、熟练地使用了 JetBrains 工具；实现是否真实、非平凡 | 描述中逐项写清 PyCharm/WebStorm 的具体用途；补 JetBrains 使用证据 |
| Design | 20% | 是否是完整连贯的产品体验，而非技术概念验证 | 视频与截图展示完整五视图工作台（总览/战队/侦察/选角/历史） |
| Potential Impact | 20% | 是否可信、具体地解决真实用户的问题 | 描述中点名用户（职业/半职业教练、分析师）与电子表格痛点 |
| Quality of the Idea | 20% | 概念是否新颖、与现有方案有何不同 | 强调 Fearless 全局锁定 + 可解释推荐的组合 |
| Presentation | 20% | 视频是否端到端演示、pitch 是否讲清问题/用户/价值 | 按第一节脚本录制，严控 3 分钟内 |

并列时按上表顺序逐项比高分定胜负（第一维度优先）。

提交前逐项勾选：

- [ ] Devpost 已点 Join Hackathon 完成报名
- [ ] 公开演示链接已部署并自检全流程（见第二节），且会保持在线到 2027-02-03
- [ ] 演示视频 < 3 分钟、YouTube 公开、链接已备好（见第一节脚本）
- [ ] 类别选 Category 2 (LoL): Macro Scouting & Draft Management System
- [ ] 仓库链接可公开访问，含运行说明；LICENSE 位置问题已处理（见第三节）
- [ ] Text description 为英文，含功能说明 + JetBrains 工具逐项说明
- [ ] Methodology write-up 已填
- [ ] （可选）Bonus Prize：AI_SHOWCASE.md 或案例链接已备好并填入表单
- [ ] 表单字段与标签逐项核对（待登录确认）
- [ ] 全部材料为英文或附英文翻译
- [ ] 在北京时间 2027-01-13 03:00 截止前提交（建议提前一天完成，勿卡点）
