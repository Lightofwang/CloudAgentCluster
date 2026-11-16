# Spec: Devpost Global AI Agent Hackathon — Pitch & Architecture Copilot

## 1. 项目概述
本项目是为 **Devpost Global AI Agent Hackathon** 设计的全栈可交互 Web 应用，旨在帮助极客马拉松参赛者在比赛初期快速完成：
1. **创意竞争力与赛道契合度评估**
2. **系统架构模块清单与风控检查**
3. **3 分钟路演 Pitch Deck 演讲提纲自动生成**

## 2. 核心功能需求

### 2.1 比赛赛道与评分标准查询 (`GET /api/tracks`)
- 预置常见 Hackathon 赛道模板（如 `AI Agents & Automation`、`Full-Stack Developer Tools`、`Web3 & Decentralized AI`、`Multimodal Copilot`）。
- 每个赛道提供评分权重（创新性、技术深度、演示完整性、商业潜力）与推荐基础架构组件。

### 2.2 实时项目分析与评估引擎 (`POST /api/analyze`)
- **输入参数**：
  - `project_name` (str): 项目名称
  - `track` (str): 目标赛道 ID
  - `problem_statement` (str): 解决的核心痛点
  - `tech_stack` (list[str] | str): 拟使用的技术栈
  - `team_size` (int): 团队人数 (1-6)
- **输出数据结构**：
  - `overall_score` (int, 0-100): 综合推荐度评分
  - `dimensions` (dict): 分项得分（`innovation`, `feasibility`, `demo_readiness`, `track_fit`）
  - `architecture_modules` (list[dict]): 推荐的系统模块与优先级清单
  - `risk_warnings` (list[str]): 结合团队规模与比赛时长的落地风险提示
  - `pitch_outline` (list[dict]): 包含 Hook、Problem、Solution、Architecture、Demo Flow、Impact 的 6 段式 3 分钟路演提纲

### 2.3 健康检查 (`GET /api/health`)
- 返回服务运行状态、版本与可用赛道数量。

## 3. 技术架构与部署约束
- **后端**：Python 标准库 HTTP JSON API 服务（`http.server.ThreadingHTTPServer`），零第三方依赖，同时在同端口静态托管 `frontend/` 页面，避免跨域问题并实现一条命令启动。
- **前端**：原生现代化深色响应式交互面板（HTML5 + CSS3 + ES6），支持表单输入、赛道选择、实时调用 `/api/analyze`、进度条可视化分项得分、架构卡片和一键复制 Pitch 提纲。
- **测试**：基于 Python `unittest` 的端到端 HTTP 接口与静态资源测试。
