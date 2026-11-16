#!/usr/bin/env python3
"""
Devpost Global AI Agent Hackathon: Pitch & Architecture Copilot
全栈后端服务：提供赛道查询、项目评估引擎、架构与路演提纲生成，并托管前端交互页面。
"""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

TRACKS: dict[str, dict[str, Any]] = {
    "ai-agents": {
        "id": "ai-agents",
        "name": "AI Agents & Autonomous Workflows",
        "focus": "多步推理、工具调用、自主执行闭环",
        "weights": {"innovation": 0.30, "feasibility": 0.25, "demo_readiness": 0.25, "track_fit": 0.20},
        "recommended_core": ["Agent Planner & Tool Router", "Persistent Task Queue", "Verification Guardrails"],
    },
    "devtools": {
        "id": "devtools",
        "name": "Full-Stack Developer Tools",
        "focus": "工程效率、CLI/SDK 体验、自动化 CI/CD 集成",
        "weights": {"innovation": 0.25, "feasibility": 0.30, "demo_readiness": 0.25, "track_fit": 0.20},
        "recommended_core": ["REST/CLI Engine", "Spec/Schema Validator", "Interactive Playground UI"],
    },
    "web3-ai": {
        "id": "web3-ai",
        "name": "Web3 & Decentralized AI",
        "focus": "链上可验证性、Agent 自主资产协作、去中心化激励",
        "weights": {"innovation": 0.35, "feasibility": 0.20, "demo_readiness": 0.20, "track_fit": 0.25},
        "recommended_core": ["Wallet & Signature Adapter", "Verifiable Execution Log", "Contract State Indexer"],
    },
    "multimodal": {
        "id": "multimodal",
        "name": "Multimodal Copilot",
        "focus": "语音/图像/文档联合理解与实时交互体验",
        "weights": {"innovation": 0.30, "feasibility": 0.20, "demo_readiness": 0.30, "track_fit": 0.20},
        "recommended_core": ["Media Ingestion Pipeline", "Streaming UI Canvas", "Context Memory Store"],
    },
}


def _normalize_tech_stack(raw_stack: Any) -> list[str]:
    if isinstance(raw_stack, list):
        return [str(x).strip() for x in raw_stack if str(x).strip()]
    if isinstance(raw_stack, str):
        return [x.strip() for x in raw_stack.replace("，", ",").split(",") if x.strip()]
    return []


def analyze_project(payload: dict[str, Any]) -> dict[str, Any]:
    """根据项目描述、赛道、技术栈与团队人数生成确定性评分、架构模块、风控建议与 Pitch 提纲。"""
    project_name = str(payload.get("project_name", "")).strip()
    problem_statement = str(payload.get("problem_statement", "")).strip()
    if not project_name or not problem_statement:
        raise ValueError("project_name 和 problem_statement 为必填项")

    track_id = str(payload.get("track", "ai-agents")).strip().lower()
    if track_id not in TRACKS:
        track_id = "ai-agents"
    track_info = TRACKS[track_id]

    tech_stack = _normalize_tech_stack(payload.get("tech_stack"))
    try:
        team_size = max(1, min(6, int(payload.get("team_size", 2))))
    except (TypeError, ValueError):
        team_size = 2

    stack_lower = " ".join(tech_stack).lower()
    has_frontend = any(k in stack_lower for k in ("react", "next", "vue", "html", "tailwind", "vite", "web"))
    has_backend = any(k in stack_lower for k in ("python", "fastapi", "node", "express", "go", "api", "flask"))
    has_ai = any(k in stack_lower for k in ("agent", "llm", "gemini", "openai", "claude", "muse", "rag", "mcp"))
    has_test = any(k in stack_lower for k in ("test", "pytest", "unittest", "playwright", "vitest"))

    problem_len = len(problem_statement)
    innovation = min(98, 68 + (12 if has_ai else 4) + (10 if problem_len >= 40 else 4) + (5 if len(tech_stack) >= 3 else 0))
    feasibility = min(98, 65 + (10 if has_backend else 3) + (10 if has_frontend else 3) + (8 if has_test else 2) + (4 if team_size >= 2 else 0))
    demo_readiness = min(98, 64 + (14 if has_frontend else 4) + (10 if has_backend else 3) + (6 if problem_len >= 25 else 2))
    track_fit = min(98, 72 + (14 if has_ai or track_id == "devtools" else 6) + (8 if len(tech_stack) >= 2 else 2))

    weights = track_info["weights"]
    overall_score = round(
        innovation * weights["innovation"]
        + feasibility * weights["feasibility"]
        + demo_readiness * weights["demo_readiness"]
        + track_fit * weights["track_fit"]
    )

    architecture_modules = [
        {
            "layer": "Frontend UI",
            "module": "Interactive Live Demo Dashboard",
            "priority": "P0",
            "reason": "评委评审时优先体验可点击的前端交互流，建议首屏即展示核心工作流。",
        },
        {
            "layer": "Core Engine",
            "module": track_info["recommended_core"][0],
            "priority": "P0",
            "reason": f"契合 {track_info['name']} 赛道的核心技术考察点：{track_info['focus']}。",
        },
        {
            "layer": "State & Queue",
            "module": track_info["recommended_core"][1],
            "priority": "P1",
            "reason": "确保演示过程中任务状态、输入输出历史可追溯且可重放。",
        },
        {
            "layer": "Verification & Demo",
            "module": track_info["recommended_core"][2],
            "priority": "P1",
            "reason": "配合一键填充示例数据与自动化 API 测试，消除现场 Demo 翻车风险。",
        },
    ]

    risk_warnings: list[str] = []
    if not has_frontend:
        risk_warnings.append("技术栈中缺少明确的前端交互层，建议增加轻量 Web UI 以便评委在 30 秒内直观体验。")
    if not has_test:
        risk_warnings.append("建议补充自动化冒烟测试脚本，防止 Hackathon 冲刺阶段修改破坏核心接口。")
    if team_size == 1:
        risk_warnings.append("单人全栈参赛时间紧凑，建议优先打通核心闭环 Demo，避免过早引入复杂基础设施或付费外部依赖。")
    if len(tech_stack) > 6:
        risk_warnings.append("技术栈组件偏多，存在集成联调耗时风险，建议收敛为单一主力语言和零配置本地服务。")
    if not risk_warnings:
        risk_warnings.append("当前技术栈与团队规模匹配度良好，请重点把控 3 分钟录屏/现场 Demo 的流畅度与边界异常兜底。")

    stack_display = ", ".join(tech_stack) if tech_stack else "Full-Stack Web + Python API"
    pitch_outline = [
        {
            "section": "1. Hook (0:00 - 0:25)",
            "talking_point": f"以高频痛点切入：用 {project_name} 在几分钟内解决传统流程中耗时且易错的瓶颈。",
        },
        {
            "section": "2. Problem (0:25 - 0:50)",
            "talking_point": f"聚焦真实问题：{problem_statement}",
        },
        {
            "section": "3. Solution (0:50 - 1:25)",
            "talking_point": f"介绍 {project_name} 如何围绕 {track_info['name']} 提供端到端自动化工作台，降低上手门槛。",
        },
        {
            "section": "4. Architecture (1:25 - 1:55)",
            "talking_point": f"展示核心技术栈（{stack_display}）及分层模块：{', '.join(track_info['recommended_core'])}。",
        },
        {
            "section": "5. Live Demo Flow (1:55 - 2:35)",
            "talking_point": "现场演示输入真实场景参数 -> 实时生成可量化评估结果 -> 一键导出并验证测试通过。",
        },
        {
            "section": "6. Impact & Next (2:35 - 3:00)",
            "talking_point": "总结项目可扩展性、开源仓库地址以及赛后持续演进路线。",
        },
    ]

    return {
        "project_name": project_name,
        "track": track_info["id"],
        "track_name": track_info["name"],
        "team_size": team_size,
        "overall_score": overall_score,
        "dimensions": {
            "innovation": innovation,
            "feasibility": feasibility,
            "demo_readiness": demo_readiness,
            "track_fit": track_fit,
        },
        "architecture_modules": architecture_modules,
        "risk_warnings": risk_warnings,
        "pitch_outline": pitch_outline,
    }


class CopilotHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def _send_json(self, payload: dict[str, Any], status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path.startswith("/api/health"):
            self._send_json(
                {
                    "status": "ok",
                    "service": "pitch-architecture-copilot",
                    "tracks_count": len(TRACKS),
                }
            )
            return

        if self.path.startswith("/api/tracks"):
            self._send_json({"tracks": list(TRACKS.values())})
            return

        super().do_GET()

    def do_POST(self) -> None:
        if self.path.startswith("/api/analyze"):
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
                result = analyze_project(payload)
            except json.JSONDecodeError:
                self._send_json({"error": "请求体必须为合法 JSON"}, status=HTTPStatus.BAD_REQUEST)
                return
            except ValueError as err:
                self._send_json({"error": str(err)}, status=HTTPStatus.BAD_REQUEST)
                return

            self._send_json(result, status=HTTPStatus.OK)
            return

        self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args) -> None:
        pass


def create_server(host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), CopilotHandler)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    server = create_server("127.0.0.1", port)
    print(f"Pitch & Architecture Copilot running at http://127.0.0.1:{port}")
    server.serve_forever()
