# AgentBazaar — 后续提交清单（Submission Checklist）

> 比赛：Open Agentic Web Challenge（Devpost，Cognizant 主办）
> 截止时间：**2027-01-11 16:00 UTC = 2027-01-12 00:00 CST（北京时间）**，无延期说明，提交后截止前可在 Devpost 存草稿修改，截止后不可改。
> 奖金：总池 $13,000+；现金 $10,000（一等奖 $5,000 / 二等奖 $3,000 / 三等奖 $2,000），另有一等奖 $1,500、二等奖 $750、三等奖 $500 的 Mozilla Otari credits 与周边。非美国获奖者领奖需提交 W-8BEN 表（规则原文）。
> 资格备注：规则排除名单为 Brazil、Quebec、Russia、Crimea、Cuba、Iran、North Korea 及 OFAC 全面制裁地区，中国大陆不在排除名单内。

## 项目速览

AgentBazaar 是一个符合 Open Agentic Web 规范的开放智能体集市与信任注册表：小商家无需技术团队即可发布机器可读的能力清单（`/.well-known/agent-network.json`），其他 AI 智能体可发现、验证并调用；站内带原创三维信任评分（来源可验证性 / 调用成功率 / 响应延迟）和浏览器内多智能体协作演示台（比价、订单追踪、服务预约，支持暂停 / 单步 / 人类接管）。

- 代码位置：CloudAgentCluster 仓库 `projects/devpost-open-agentic-web-2026/`（GitHub：https://github.com/Lightofwang/CloudAgentCluster/tree/main/projects/devpost-open-agentic-web-2026 ）
- 本地运行：`cd projects/devpost-open-agentic-web-2026 && pip install -r requirements.txt && python3 -m uvicorn app.main:app --port 8000`，浏览器打开 http://localhost:8000
- 现状：代码已完成，19 项自动化测试全部通过（见项目 RESULT.md）；**尚未公开部署、尚未录制视频、尚未在 Devpost 建提交**——下面三节就是剩余的全部手工工作。

---

## 一、演示视频要求

### 硬性要求（官方原文核对，比赛主页 "What to Submit" + 规则第 4 节）

- **必需**，且必须上传到 **YouTube 并设为公开**，链接填入 Devpost 提交表单。
- 时长：**少于 2 分钟**（原文 "should be less than two (2) minutes. Judges are not required to watch beyond two minutes"——超过 2 分钟的部分评委可以不看，按硬上限对待）。
- 必须包含**项目在浏览器中实际运行的画面**（原文 "should include footage that shows the Project running in a web browser"）。
- **必须有参赛者本人讲解项目**：比赛主页原文为 "must include the Entrant explaining the Project **(not AI generated)**"。
- 不得包含无授权的第三方商标、版权音乐或其他受版权保护素材。
- 语言要求（规则 "Language Requirements"）：所有提交材料须为英文；非英文材料必须提供英文翻译。视频若用中文讲解，**必须配英文字幕**（翻译形式以字幕满足，待确认主办方是否接受仅字幕形式）。

### ⚠️ 与以往做法的冲突（重要）

- 以前项目（GhostFeed 等）用的是 **AI 生成英文旁白**——本比赛**明确禁止**（"(not AI generated)"），沿用会直接违规。
- 规则只要求"参赛者本人讲解"，**没有明文要求露脸出镜**。合规形式可选：
  1. 本人出镜讲解（最稳妥）；
  2. 本人真声配音 + 录屏（不露脸）——是否满足 "Entrant explaining" **待确认**，规则未明文禁止，但也未明文允许；
  3. 本人真声中文讲解 + 英文字幕——字幕能否替代英文讲解 **待确认**。
- 建议：录制前先按方案 2/3 向主办方（Devpost 比赛页讨论区）确认一次；若无回复，按方案 1 或"本人英文真声配音 + 录屏"执行。**无论选哪种，旁白必须是本人声音、本人讲解，不能用任何 AI 语音生成。**

### 分步录制脚本（目标总时长 ≤ 1 分 50 秒，录屏 + 本人讲解）

录制前：本地启动服务（或用已部署的公开地址，见第二节），浏览器开到 http://localhost:8000 ，窗口最大化，先点设置页"重置数据库"恢复 6 个种子商家。

| 时间 | 画面操作 | 讲解要点（英文，自行组织语言） |
|---|---|---|
| 0:00–0:15 | 打开集市首页，缓慢滚动商家卡片墙 | 一句话定位：让没有技术团队的小商家拥有能被 AI 智能体发现、验证、调用的"智能体门面" |
| 0:15–0:35 | 点能力筛选"报价 price.quote"，点开"云雾茶行"卡片，点"发起调用"，展示返回报文与信任分细项 | 每个智能体自动生成规范 manifest；信任分由来源、成功率、延迟三项可验证信号合成 |
| 0:35–1:15 | 切到协作演示台，选"多商家比价"，点快捷预填"西湖龙井 250g (x2)"，点"开始智能体协作"，展示步骤时间线推进；中途点一次"暂停"再"单步执行" | 浏览器内多智能体运行时：发现 → 验信任分 → 并行询价 → 比价汇总；人可随时暂停、单步、接管 |
| 1:15–1:35 | 切到信任榜单页，展示排名与三项得分条；再切到跨站互联，点"抓取并解析 Manifest" | 信任公开透明、低分调用前有风险提示；任意兼容站点可被发现并跨站调用 |
| 1:35–1:50 | 浏览器新开标签打开 `/.well-known/agent-network.json` 原始 JSON，回到首页收尾 | 本站就是开放智能体网络的一个节点，任何智能体无需注册即可读取清单并调用 |

录完检查：总时长 < 2:00；全程有浏览器画面；讲解为本人声音；无版权音乐（建议无背景音乐）；YouTube 设为公开（不是"不公开列出"以外的私密状态）。

---

## 二、公开部署要求

### 硬性要求（官方原文核对）

提交必须提供**公开可访问的站点 URL**，且该站点必须包含：

- [ ] 一个公开可访问、符合规范的 `.json` 文件，描述智能体网络及其能力——即站点根部的 **`/.well-known/agent-network.json`**（本项目已实现该端点，本地验证：http://localhost:8000/.well-known/agent-network.json ）；
- [ ] 一个能在浏览器中运行智能体网络的 `runtime` 文件（本项目为前端 `static/app.js` 内置运行时，随站点一并部署即可）；
- [ ] 一个供用户或智能体与智能体网络交互的界面（本站首页 SPA）；
- [ ] （可选）供用户配置 LLM 与 key 的界面（本站设置页 BYO LLM 已实现，部署后保留即可）；
- [ ] 智能体网络应能与本站交互（本站已满足；与外部站点互调为加分项，跨站互联页可演示）。

规则另要求：项目在评审期结束前（评审期 2027-01-11 至 2027-01-18 PT）**免费、无限制地可供评委测试**，部署后不要关停或加访问限制。

### 部署方案（结合用户约束）

用户约束：**不能用 Vercel**（收不到短信验证码）、**不能在自有 VPS 直接部署**（会暴露公网 IP）。

- 本项目是 FastAPI 服务端应用（需要能跑 Python 后端的托管），不是纯静态站。GhostFeed 曾用 Netlify 成功部署（已验证可行的平台先例），但 Netlify 以静态/函数托管为主，**能否直接承载本项目的 uvicorn 长驻服务待确认**。
- 待确认：最终托管平台。候选方向（均需逐一核实免费额度与 Python 支持后再定）：支持 FastAPI 的免费 PaaS（如 Render / Railway / Fly.io / Hugging Face Spaces 等）——**本清单不臆测可用性，部署前逐个验证**。
- 部署后自检（缺一不可）：
  - [ ] 公开 URL 能打开首页且演示台可完整跑通比价场景；
  - [ ] `https://<你的域名>/.well-known/agent-network.json` 无需登录即可 GET 到合法 JSON；
  - [ ] 无痕窗口（未登录状态）复测一遍，确认无访问限制；
  - [ ] 把最终公开 URL 填入 Devpost 表单的网站地址栏（见第三节）。

---

## 三、平台表单填写（Devpost 提交页）

在 https://cognizant-agenticweb.devpost.com/ 点 "Join Hackathon" 注册后，进入 "Enter a Submission" 填写。官方规则只说"填齐提交页所有必填项"，未逐项列出；以下按 Devpost 标准提交表单 + 本比赛主页 "What to Submit" 整理，**表单实际出现的自定义问题以提交时页面为准（待确认）**。

- **Project name**：`AgentBazaar`
- **Tagline（一句话，英文草稿）**：
  > AgentBazaar — an open marketplace where any small business can publish a machine-readable agent storefront that other AI agents can discover, verify, and call.
- **Website / Live URL**：填第二节部署好的公开地址（必须能打开且根部有 `/.well-known/agent-network.json`）。
- **Video URL**：填第一节录好的 YouTube 公开链接。
- **Text description（英文 pitch 要点草稿，按此结构扩写）**：
  1. Problem: 小商家在智能体时代不可见——没有技术团队就无法被 AI 智能体发现和调用，只能继续依赖高佣金中心化平台。
  2. Solution: AgentBazaar 让商家一键发布符合 Open Agentic Web 规范的能力清单，任何智能体无需注册即可发现、验证、调用。
  3. Trust: 原创三维可验证信任评分（来源可验证性 30 + 调用成功率 40 + 响应延迟 30），细项全公开，解决多智能体之间"敢不敢调"的信任问题。
  4. Demo in browser: 浏览器内多智能体运行时现场演示比价 / 订单追踪 / 预约三场景，支持暂停、单步、人类接管。
  5. Open & free to run: 零付费本地引擎离线可跑，同时支持 BYO LLM key；全部开源，可作为社区基础设施复用。
- **Screenshots**：至少 1 张（硬性要求），建议传 4 张：集市首页、协作演示台运行中、信任榜单、跨站互联结果。
- **Built with 标签建议**：`fastapi`、`python`、`javascript`、`open-agentic-web`（以表单可选标签为准，待确认）。
- **赛道/类别**：本比赛**无分赛道**，所有作品同一池评审；Employee Prize 仅限主办方/合作方员工，与我们无关，不用勾选任何雇员相关项。
- **Otari 相关栏位**：仅"使用了 Mozilla Otari"的项目才需要填 Otari 账号邮箱并写使用反馈；**本项目未使用 Otari**（用的是本地引擎 + BYO LLM），如表单出现该栏位留空即可（待确认表单是否强制）。
- **代码仓库**：Devpost 表单如有 repository 栏，填 CloudAgentCluster 仓库中本项目目录链接（见项目速览）。

---

## 四、评审权重与提交前检查

### 评审方式（规则第 6 节原文核对）

- **Stage One（通过/不通过）**：先判定项目是否为"符合规范的开放智能体网站"——不合规直接淘汰，不进入打分。合规要点即第二节清单（公开站点 + 合规 manifest json + 浏览器 runtime + 交互界面）。
- **Stage Two（打分）**：通过 Stage One 后，按四项**等权重**标准评分（每项约 25%）：
  1. **Technological Implementation（技术实现）**：做得好不好、用没用好开放智能体网络规范；
  2. **Design（设计）**：是完整的产品体验，还是只是技术概念验证；
  3. **Potential Impact（潜在影响）**：是否针对真实受众解决真实问题、演示是否真的解决了它；额外加分点：开发过程中顺带做并分享给社区的工具/服务；
  4. **Quality of the Idea（创意质量）**：用法是否新颖不显然、是否真正理解问题领域。
- 同分时按上述顺序逐项比高低定名次，所以**技术实现是第一 tie-breaker**，视频和文案里要优先把规范符合度讲透。

### 提交前逐项勾选清单

- [ ] 公开 URL 已部署，无痕窗口可打开，演示台比价场景可跑通
- [ ] `<公开 URL>/.well-known/agent-network.json` 可公开 GET 且为合法 JSON
- [ ] 视频 < 2 分钟、YouTube 公开、含浏览器运行画面
- [ ] 视频讲解为**参赛者本人**（非 AI 生成旁白）；非英文讲解已配英文字幕
- [ ] 视频无未授权商标/版权音乐
- [ ] Devpost 描述为英文，覆盖 pitch 五个要点
- [ ] 截图 ≥ 1 张已上传（建议 4 张）
- [ ] 表单中网站 URL、视频 URL 均已填且点开可达
- [ ] Otari 栏位：本项目未使用 Otari，留空（如表单强制要求则待确认处理方式）
- [ ] 提交时间不晚于 **2027-01-12 00:00 CST**（建议至少提前 24 小时提交，留出部署/视频返工时间）
- [ ] 部署在评审期结束（2027-01-19 前后）前保持在线、免费、无访问限制

### 待确认项汇总

1. 本人真声配音（不露脸）是否满足 "Entrant explaining the Project"；中文讲解 + 英文字幕是否可接受——建议录制前在比赛页讨论区问主办方。
2. 最终部署平台：需支持 FastAPI/Python 后端的免费托管，Netlify 能否承载本项目待验证，候选平台逐一核实后再定。
3. Devpost 提交表单的实际字段与自定义问题（Built with 标签、Otari 栏位是否强制）以正式提交时页面为准。
