# Implementation Plan: Pitch & Architecture Copilot

## Phase 1: 后端 API 服务与评估引擎 (`backend/server.py`)
1. 定义预置赛道配置 `TRACKS`（涵盖 `ai-agents`、`devtools`、`web3-ai`、`multimodal` 四个赛道）。
2. 实现确定性加权评估与建议生成函数 `analyze_project(payload)`：
   - 对接输入校验（缺失 `project_name` 或 `problem_statement` 返回 `400 Bad Request`）。
   - 根据问题陈述清晰度、技术栈覆盖度（前端/后端/Agent/测试）、团队人数与赛道匹配度计算各维度得分与总分。
   - 生成分层架构模块（Frontend UI, Core Agent/API, Data/State, Verification/Demo）。
   - 结合时间约束与团队人数输出针对性风险提示与 6 段式 Pitch Deck 提纲。
3. 使用 `ThreadingHTTPServer` 暴露：
   - `GET /api/health`
   - `GET /api/tracks`
   - `POST /api/analyze`
   - 静态资源托管 `frontend/`（支持 `/` -> `index.html`，`style.css`，`app.js`）。

## Phase 2: 响应式前端交互工作台 (`frontend/`)
1. `index.html`：左右分栏布局（左侧项目参数录入区，右侧分析评分、推荐架构清单、风险告警及路演 Pitch 提纲展示区）。
2. `style.css`：现代深色仪表盘风格，带进度条动画与移动端适配。
3. `app.js`：页面加载时请求 `GET /api/tracks` 渲染赛道下拉框；提交表单后请求 `POST /api/analyze` 渲染结果，并提供“填充示例数据”和“复制 Pitch 提纲”功能。

## Phase 3: 自动化测试与验证 (`tests/test_app.py`)
1. 在临时端口 `0`（系统随机可用端口）启动后台测试服务器线程。
2. 覆盖测试场景：
   - `GET /` 返回 `200` 且包含应用标题；
   - `GET /api/health` 返回 `status: "ok"`；
   - `GET /api/tracks` 返回至少 4 个赛道；
   - `POST /api/analyze`（正常数据）返回完整评分、架构模块和 6 段 Pitch 提纲；
   - `POST /api/analyze`（缺失必填字段）返回 `400`。
