#!/usr/bin/env python3
"""
为指定的 Hackathon 任务生成全栈可交互 Web 应用基础脚手架 (projects/<slug>/)。
包含：SPEC.md / PLAN.md 副本、Python 标准库后端服务、现代 Web 前端与 unittest 测试套件。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ingest_spec import load_hackathons_index, slugify  # noqa: E402


def _write_if_needed(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def scaffold_project(slug: str, root_dir: Path, force: bool = False) -> Path:
    normalized_slug = slugify(slug)
    index_data = load_hackathons_index(root_dir)
    entry = next(
        (h for h in index_data.get("hackathons", []) if h.get("slug") == normalized_slug),
        None,
    )
    if entry is None:
        raise KeyError(f"未在 site/data/hackathons.json 中找到 slug='{normalized_slug}'")

    spec_src = root_dir / "site" / "data" / "specs" / normalized_slug / "spec.md"
    plan_src = root_dir / "site" / "data" / "specs" / normalized_slug / "plan.md"

    project_dir = root_dir / "projects" / normalized_slug
    (project_dir / "backend").mkdir(parents=True, exist_ok=True)
    (project_dir / "frontend").mkdir(parents=True, exist_ok=True)
    (project_dir / "tests").mkdir(parents=True, exist_ok=True)

    spec_text = spec_src.read_text(encoding="utf-8") if spec_src.exists() else f"# Spec: {entry['title']}\n"
    plan_text = plan_src.read_text(encoding="utf-8") if plan_src.exists() else f"# Plan: {entry['title']}\n"

    _write_if_needed(project_dir / "SPEC.md", spec_text, True)
    _write_if_needed(project_dir / "PLAN.md", plan_text, True)

    title = entry.get("title", normalized_slug)
    summary = entry.get("summary", "Hackathon 全栈原型应用")
    platform = entry.get("platform", "devpost")
    source_url = entry.get("source_url", "")

    readme_content = f"""# {title}

> 自动由 **CloudAgentCluster** 基于中转网站 Spec/Plan 构建的全栈 Hackathon 参赛项目。

- **Slug**: `{normalized_slug}`
- **参赛平台**: `{platform}`
- **原始比赛链接**: {source_url or "N/A"}
- **简介**: {summary}

## 快速启动

```bash
python backend/server.py
```

启动后在浏览器访问 `http://127.0.0.1:8000` 即可体验完整前端与后端 API。

## 运行自动化测试

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

## 设计文档
- [SPEC.md](SPEC.md)
- [PLAN.md](PLAN.md)
"""
    _write_if_needed(project_dir / "README.md", readme_content, force)

    backend_code = f'''#!/usr/bin/env python3
"""全栈 Web 应用后端服务与静态前端托管 ({normalized_slug})。"""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
PROJECT_META = {{
    "slug": {json.dumps(normalized_slug)},
    "title": {json.dumps(title, ensure_ascii=False)},
    "platform": {json.dumps(platform)},
    "status": "ready",
}}


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def _send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path.startswith("/api/health"):
            self._send_json({{"status": "ok", "slug": PROJECT_META["slug"]}})
            return
        if self.path.startswith("/api/info"):
            self._send_json(PROJECT_META)
            return
        super().do_GET()

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{{}}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json({{"error": "Invalid JSON"}}, status=HTTPStatus.BAD_REQUEST)
            return

        if self.path.startswith("/api/echo"):
            self._send_json({{"received": data, "slug": PROJECT_META["slug"]}})
            return

        self._send_json({{"error": "Not found"}}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args) -> None:
        pass


def create_server(host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), AppHandler)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    server = create_server("127.0.0.1", port)
    print(f"Serving {{PROJECT_META['title']}} at http://127.0.0.1:{{port}}")
    server.serve_forever()
'''
    _write_if_needed(project_dir / "backend" / "server.py", backend_code, force)

    html_code = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <main class="wrap">
    <h1>{title}</h1>
    <p>{summary}</p>
    <div id="app-status">正在连接后端 API...</div>
  </main>
  <script src="app.js"></script>
</body>
</html>
"""
    _write_if_needed(project_dir / "frontend" / "index.html", html_code, force)

    css_code = """body {
  font-family: system-ui, -apple-system, sans-serif;
  background: #0f172a;
  color: #e2e8f0;
  margin: 0;
  padding: 40px 20px;
}
.wrap {
  max-width: 880px;
  margin: 0 auto;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 12px;
  padding: 24px;
}
"""
    _write_if_needed(project_dir / "frontend" / "style.css", css_code, force)

    js_code = """fetch("/api/health")
  .then((r) => r.json())
  .then((d) => {
    document.getElementById("app-status").textContent = "后端连接正常：" + JSON.stringify(d);
  })
  .catch((err) => {
    document.getElementById("app-status").textContent = "连接失败：" + err.message;
  });
"""
    _write_if_needed(project_dir / "frontend" / "app.js", js_code, force)

    test_code = """import json
import sys
import threading
import unittest
import urllib.request
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "backend"))

from server import create_server  # noqa: E402


class TestScaffoldApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server("127.0.0.1", 0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_health_and_frontend(self):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/api/health") as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "ok")

        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/") as resp:
            self.assertEqual(resp.status, 200)
            html = resp.read().decode("utf-8")
            self.assertIn("<!DOCTYPE html>", html)


if __name__ == "__main__":
    unittest.main()
"""
    _write_if_needed(project_dir / "tests" / "test_app.py", test_code, force)

    run_json = {
        "runtime": "python",
        "requirements": "",
        "prepare": [],
        "start": ["{python}", "backend/server.py"],
        "health_url": "/api/health",
    }
    _write_if_needed(
        project_dir / "run.json",
        json.dumps(run_json, ensure_ascii=False, indent=2) + "\n",
        force,
    )

    return project_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 Hackathon 全栈项目脚手架")
    parser.add_argument("--slug", required=True, help="比赛 Slug")
    parser.add_argument("--root-dir", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--force", action="store_true", help="强制覆盖已有脚手架文件")
    args = parser.parse_args()

    project_dir = scaffold_project(args.slug, Path(args.root_dir).resolve(), force=args.force)
    print(json.dumps({"slug": slugify(args.slug), "project_dir": project_dir.as_posix()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
