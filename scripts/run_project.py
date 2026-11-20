#!/usr/bin/env python3
"""
CloudAgentCluster 统一项目启动器与隔离环境管理器。
解决 projects/<slug>/ 下各 Hackathon 项目依赖冲突、启动入口不统一、端口冲突等问题：
- 自动为每个需要依赖的项目创建独立 projects/<slug>/.venv（基于 requirements.txt 哈希缓存，避免重复安装）
- 优先读取项目内的 run.json；无 run.json 时自动探测 FastAPI / Python HTTP / Node.js 入口与 seed 脚本
- 自动检测空闲端口（默认从 8000 起顺延），支持多个项目同时并行运行体验
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parent.parent
PROJECTS_DIR = ROOT_DIR / "projects"


def find_free_port(host: str = "127.0.0.1", preferred: int = 8000, max_tries: int = 50) -> int:
    for port in range(preferred, preferred + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex((host, port)) != 0:
                return port
    raise RuntimeError(f"在 {preferred}..{preferred + max_tries - 1} 范围内未找到可用端口")


def _venv_python(project_dir: Path) -> Path:
    venv_dir = project_dir / ".venv"
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _needs_uvicorn(py_file: Path) -> bool:
    if not py_file.exists():
        return False
    text = py_file.read_text(encoding="utf-8", errors="replace")
    return "FastAPI(" in text or "from fastapi" in text


def _has_main_block(py_file: Path) -> bool:
    if not py_file.exists():
        return False
    text = py_file.read_text(encoding="utf-8", errors="replace")
    return "__name__" in text and "__main__" in text


def detect_project_spec(project_dir: Path) -> dict[str, Any]:
    """探测项目的运行时、依赖、预初始化与启动命令。"""
    run_json = project_dir / "run.json"
    if run_json.exists():
        spec = json.loads(run_json.read_text(encoding="utf-8"))
        spec.setdefault("source", "run.json")
        return spec

    req_file = project_dir / "requirements.txt"
    pkg_file = project_dir / "package.json"

    # Python 项目探测
    if (project_dir / "backend" / "server.py").exists():
        return {
            "source": "auto-detect",
            "runtime": "python",
            "requirements": "requirements.txt" if req_file.exists() else "",
            "prepare": [],
            "start": ["{python}", "backend/server.py"],
            "health_url": "/api/health",
        }

    if (project_dir / "main.py").exists() or (project_dir / "app" / "main.py").exists():
        prepare_cmds: list[str] = []
        if _has_main_block(project_dir / "app" / "seed.py"):
            # 仅当目标数据库文件尚不存在时自动 seed，或者首次初始化
            prepare_cmds.append("{python} -m app.seed")

        if (project_dir / "main.py").exists():
            if _needs_uvicorn(project_dir / "main.py") or req_file.exists():
                start_cmd = ["{python}", "-m", "uvicorn", "main:app", "--host", "{host}", "--port", "{port}"]
            else:
                start_cmd = ["{python}", "main.py"]
        else:
            if _needs_uvicorn(project_dir / "app" / "main.py") or req_file.exists():
                start_cmd = ["{python}", "-m", "uvicorn", "app.main:app", "--host", "{host}", "--port", "{port}"]
            else:
                start_cmd = ["{python}", "-m", "app.main"]

        return {
            "source": "auto-detect",
            "runtime": "python",
            "requirements": "requirements.txt" if req_file.exists() else "",
            "prepare": prepare_cmds,
            "start": start_cmd,
            "health_url": "/api/health",
        }

    for entry_name in ("server.py", "app.py"):
        if (project_dir / entry_name).exists():
            return {
                "source": "auto-detect",
                "runtime": "python",
                "requirements": "requirements.txt" if req_file.exists() else "",
                "prepare": [],
                "start": ["{python}", entry_name],
                "health_url": "/",
            }

    # Node.js 项目探测
    if pkg_file.exists():
        pkg_data = json.loads(pkg_file.read_text(encoding="utf-8"))
        scripts = pkg_data.get("scripts", {})
        script_name = "dev" if "dev" in scripts else ("start" if "start" in scripts else "")
        return {
            "source": "auto-detect",
            "runtime": "node",
            "requirements": "package.json",
            "prepare": [],
            "start": ["npm", "run", script_name] if script_name else [],
            "health_url": "/",
        }

    return {
        "source": "unknown",
        "runtime": "unknown",
        "requirements": "",
        "prepare": [],
        "start": [],
        "health_url": "/",
    }


def _format_cmd(cmd: str | list[str], py_exec: str, host: str, port: int) -> list[str]:
    parts = shlex.split(cmd, posix=(os.name != "nt")) if isinstance(cmd, str) else list(cmd)
    return [
        part.replace("{python}", py_exec).replace("{host}", host).replace("{port}", str(port))
        for part in parts
    ]


def ensure_environment(
    project_dir: Path,
    spec: dict[str, Any],
    reseed: bool = False,
    dry_run: bool = False,
) -> str:
    """确保项目独立虚拟环境与依赖已安装，并按需执行首次数据初始化。返回应使用的 Python 路径。"""
    runtime = spec.get("runtime", "python")
    if runtime != "python":
        if runtime == "node" and not (project_dir / "node_modules").exists():
            print(f"[prepare] 正在为 {project_dir.name} 安装 npm 依赖...")
            if not dry_run:
                subprocess.run(["npm", "install"], cwd=str(project_dir), check=True)
        return sys.executable

    req_rel = spec.get("requirements") or ""
    req_path = (project_dir / req_rel) if req_rel else None

    if req_path and req_path.exists():
        venv_py = _venv_python(project_dir)
        req_hash_file = project_dir / ".venv" / ".req_hash"
        current_hash = _file_sha256(req_path)

        if not venv_py.exists():
            print(f"[venv] 正在为 {project_dir.name} 创建独立虚拟环境 (.venv)...")
            if not dry_run:
                subprocess.run([sys.executable, "-m", "venv", str(project_dir / ".venv")], check=True)

        cached_hash = req_hash_file.read_text(encoding="utf-8").strip() if req_hash_file.exists() else ""
        if cached_hash != current_hash:
            print(f"[pip] 正在安装 {project_dir.name}/{req_rel} 依赖（仅首次或依赖变更时执行）...")
            if not dry_run:
                subprocess.run(
                    [str(venv_py), "-m", "pip", "install", "--upgrade", "pip", "-q"],
                    cwd=str(project_dir),
                    check=False,
                )
                subprocess.run(
                    [str(venv_py), "-m", "pip", "install", "-r", str(req_path)],
                    cwd=str(project_dir),
                    check=True,
                )
                req_hash_file.write_text(current_hash, encoding="utf-8")
        py_exec = str(venv_py)
    else:
        py_exec = sys.executable

    # 执行首次初始化脚本（如 app.seed）
    prepare_cmds = spec.get("prepare") or []
    seeded_marker = project_dir / ".venv" / ".seeded"
    if prepare_cmds and (reseed or not seeded_marker.exists()):
        for raw_cmd in prepare_cmds:
            cmd = _format_cmd(raw_cmd, py_exec, "127.0.0.1", 8000)
            print(f"[prepare] 执行初始化: {' '.join(cmd)}")
            if not dry_run:
                subprocess.run(cmd, cwd=str(project_dir), check=True)
        if not dry_run:
            seeded_marker.parent.mkdir(parents=True, exist_ok=True)
            seeded_marker.write_text("ok\n", encoding="utf-8")

    return py_exec


def list_projects(projects_dir: Path) -> list[dict[str, Any]]:
    if not projects_dir.exists():
        return []
    results: list[dict[str, Any]] = []
    for p in sorted(projects_dir.iterdir()):
        if not p.is_dir() or p.name.startswith("."):
            continue
        spec = detect_project_spec(p)
        venv_ready = _venv_python(p).exists() or not bool(spec.get("requirements"))
        results.append(
            {
                "slug": p.name,
                "runtime": spec.get("runtime", "unknown"),
                "source": spec.get("source", "unknown"),
                "requirements": spec.get("requirements") or "none",
                "venv_ready": venv_ready,
                "prepare": spec.get("prepare", []),
                "start": spec.get("start", []),
            }
        )
    return results


def start_project(
    slug: str,
    projects_dir: Path,
    host: str = "127.0.0.1",
    preferred_port: int = 8000,
    no_install: bool = False,
    reseed: bool = False,
    dry_run: bool = False,
) -> int:
    project_dir = projects_dir / slug
    if not project_dir.exists():
        print(f"错误：未找到项目目录 {project_dir}", file=sys.stderr)
        return 1

    spec = detect_project_spec(project_dir)
    if not spec.get("start"):
        print(f"错误：无法识别项目 '{slug}' 的启动入口，请为其添加 run.json", file=sys.stderr)
        return 1

    if no_install:
        venv_py = _venv_python(project_dir)
        py_exec = str(venv_py) if venv_py.exists() else sys.executable
    else:
        py_exec = ensure_environment(project_dir, spec, reseed=reseed, dry_run=dry_run)

    port = find_free_port(host, preferred=preferred_port)
    start_cmd = _format_cmd(spec["start"], py_exec, host, port)

    env = os.environ.copy()
    env["HOST"] = host
    env["PORT"] = str(port)
    env["PYTHONUTF8"] = "1"

    url = f"http://{host}:{port}"
    print("=" * 60)
    print(f"🚀 启动项目: {slug} ({spec.get('runtime')} / {spec.get('source')})")
    print(f"🌐 访问地址: {url}")
    if spec.get("health_url"):
        print(f"💓 健康检查: {url}{spec['health_url']}")
    print(f"💻 执行命令: {' '.join(start_cmd)}")
    print("按 Ctrl+C 可停止当前服务")
    print("=" * 60)

    if dry_run:
        return 0

    try:
        proc = subprocess.run(start_cmd, cwd=str(project_dir), env=env)
        return proc.returncode
    except KeyboardInterrupt:
        print("\n已停止服务。")
        return 0


def test_project(slug: str, projects_dir: Path, no_install: bool = False) -> int:
    project_dir = projects_dir / slug
    if not project_dir.exists():
        print(f"错误：未找到项目目录 {project_dir}", file=sys.stderr)
        return 1

    spec = detect_project_spec(project_dir)
    if no_install:
        venv_py = _venv_python(project_dir)
        py_exec = str(venv_py) if venv_py.exists() else sys.executable
    else:
        py_exec = ensure_environment(project_dir, spec)

    tests_dir = project_dir / "tests"
    if not tests_dir.exists():
        print(f"提示：{slug} 下没有 tests/ 目录。")
        return 0

    cmd = [py_exec, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"]
    print(f"[test] 运行 {slug} 测试: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=str(project_dir))
    return res.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="CloudAgentCluster 统一项目启动与环境管理 CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="列出 projects/ 下的所有项目及探测到的启动方式")
    p_list.add_argument("--projects-dir", default=str(PROJECTS_DIR))
    p_list.add_argument("--json", action="store_true")

    p_prep = sub.add_parser("prepare", help="仅创建独立 .venv、安装依赖并运行初始化脚本")
    p_prep.add_argument("slug", help="projects/ 下的项目目录名")
    p_prep.add_argument("--projects-dir", default=str(PROJECTS_DIR))
    p_prep.add_argument("--reseed", action="store_true", help="强制重新执行初始化脚本")

    p_start = sub.add_parser("start", help="一键准备隔离环境、分配空闲端口并启动项目")
    p_start.add_argument("slug", help="projects/ 下的项目目录名")
    p_start.add_argument("--projects-dir", default=str(PROJECTS_DIR))
    p_start.add_argument("--host", default="127.0.0.1")
    p_start.add_argument("--port", type=int, default=8000, help="首选端口，若被占用将自动顺延")
    p_start.add_argument("--no-install", action="store_true", help="跳过依赖检查直接启动")
    p_start.add_argument("--reseed", action="store_true", help="强制重新执行初始化脚本")
    p_start.add_argument("--dry-run", action="store_true", help="只预览启动命令与分配端口，不实际拉起进程")

    p_test = sub.add_parser("test", help="在项目独立环境中运行单元测试")
    p_test.add_argument("slug", help="projects/ 下的项目目录名")
    p_test.add_argument("--projects-dir", default=str(PROJECTS_DIR))
    p_test.add_argument("--no-install", action="store_true")

    args = parser.parse_args()
    projects_dir = Path(args.projects_dir).resolve()

    if args.command == "list":
        items = list_projects(projects_dir)
        if args.json:
            print(json.dumps(items, ensure_ascii=False, indent=2))
        else:
            if not items:
                print("projects/ 目录下暂无项目。")
            for item in items:
                ready_str = "已就绪" if item["venv_ready"] else "需首次安装依赖"
                cmd_preview = " ".join(item["start"]) if item["start"] else "未识别"
                print(
                    f"- {item['slug']} [{item['runtime']} · {ready_str}]\n"
                    f"  启动命令: {cmd_preview}"
                )
        return 0

    if args.command == "prepare":
        project_dir = projects_dir / args.slug
        if not project_dir.exists():
            print(f"错误：未找到项目目录 {project_dir}", file=sys.stderr)
            return 1
        spec = detect_project_spec(project_dir)
        ensure_environment(project_dir, spec, reseed=args.reseed)
        print(f"✅ 项目 {args.slug} 环境与初始化已就绪。")
        return 0

    if args.command == "start":
        return start_project(
            slug=args.slug,
            projects_dir=projects_dir,
            host=args.host,
            preferred_port=args.port,
            no_install=args.no_install,
            reseed=args.reseed,
            dry_run=args.dry_run,
        )

    if args.command == "test":
        return test_project(slug=args.slug, projects_dir=projects_dir, no_install=args.no_install)

    return 1


if __name__ == "__main__":
    sys.exit(main())
