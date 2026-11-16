import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "scripts"))

from ingest_spec import DEFAULT_PASSCODE, expected_passcode_hash, ingest_entry, parse_issue_markdown  # noqa: E402
from publish_project import publish_project  # noqa: E402
from scaffold_fullstack import scaffold_project  # noqa: E402
from sync_and_queue import _is_owner_trusted, mark_status, sync_from_site_url  # noqa: E402


class QuietHTTPHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        pass


class TestHackathonPipeline(unittest.TestCase):
    def setUp(self):
        self.tmp_obj = tempfile.TemporaryDirectory()
        self.tmp_root = Path(self.tmp_obj.name)
        (self.tmp_root / "site" / "data" / "specs").mkdir(parents=True, exist_ok=True)
        (self.tmp_root / "projects").mkdir(parents=True, exist_ok=True)

        # 初始化隔离测试的 hackathons.json
        init_index = {
            "updated_at": "2026-11-16T10:00:00+08:00",
            "site_config": {
                "github_owner": "Lightofwang",
                "github_repo": "CloudAgentCluster",
                "default_branch": "main",
            },
            "hackathons": [],
        }
        (self.tmp_root / "site" / "data" / "hackathons.json").write_text(
            json.dumps(init_index, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp_obj.cleanup()

    def test_01_ingest_from_structured_issue_markdown(self):
        issue_body = """
<!--HACKATHON_META_START-->
```json
{
  "slug": "lablab-agent-mesh-2026",
  "title": "Lablab Agent Mesh Hackathon",
  "platform": "lablab",
  "source_url": "https://lablab.ai/event/agent-mesh",
  "deadline": "2026-12-30T23:59:00Z",
  "prize_pool": "$30,000",
  "match_score": 94,
  "tags": ["AI Agent", "Full-Stack"],
  "summary": "多节点 Agent 协同编排演示面板"
}
```
<!--HACKATHON_META_END-->

<!--SPEC_START-->
# Spec: Lablab Agent Mesh
## 1. 功能
提供实时 Agent 拓扑状态查询 API。
<!--SPEC_END-->

<!--PLAN_START-->
# Plan: Lablab Agent Mesh
## Phase 1
完成后端与前端集成测试。
<!--PLAN_END-->
"""
        payload = parse_issue_markdown(issue_body, title="[Hackathon Spec] Lablab Agent Mesh Hackathon")
        entry = ingest_entry(payload, self.tmp_root)

        self.assertEqual(entry["slug"], "lablab-agent-mesh-2026")
        self.assertEqual(entry["status"], "pending_dev")
        spec_file = self.tmp_root / "site" / "data" / "specs" / "lablab-agent-mesh-2026" / "spec.md"
        plan_file = self.tmp_root / "site" / "data" / "specs" / "lablab-agent-mesh-2026" / "plan.md"
        self.assertTrue(spec_file.exists())
        self.assertTrue(plan_file.exists())
        self.assertIn("Lablab Agent Mesh", spec_file.read_text(encoding="utf-8"))

        index_data = json.loads((self.tmp_root / "site" / "data" / "hackathons.json").read_text(encoding="utf-8"))
        self.assertEqual(len(index_data["hackathons"]), 1)
        self.assertEqual(index_data["hackathons"][0]["slug"], "lablab-agent-mesh-2026")

    def test_02_ingest_from_issue_form_headings_and_reset(self):
        form_body = """
### 比赛名称 (Title)
DoraHacks DeAI Builder Challenge

### 唯一标识 (Slug)
dorahacks-deai-builder

### 所属平台 (Platform)
dorahacks

### 比赛链接 (Source URL)
https://dorahacks.io/hackathon/deai

### 奖金池 (Prize Pool)
$40,000

### 匹配度评分 (1-100)
91

### 标签 (Tags)
Web3, AI Agent

### 一句话简介 (Summary)
去中心化 AI 任务调度看板

### Spec 设计文档 (spec.md)
# Spec: DeAI Builder
提供链下 Agent 执行校验接口。

### Plan 实施计划 (plan.md)
# Plan: DeAI Builder
实现 HTTP 校验服务与前端视图。
"""
        payload = parse_issue_markdown(form_body)
        entry = ingest_entry(payload, self.tmp_root)
        self.assertEqual(entry["slug"], "dorahacks-deai-builder")
        self.assertEqual(entry["platform"], "dorahacks")
        self.assertEqual(entry["match_score"], 91)

        # 标记完成再测试 trigger-dev 重置
        mark_status("dorahacks-deai-builder", "completed", self.tmp_root, repo_url="https://github.com/test/repo")
        reset_payload = parse_issue_markdown('<!--TRIGGER_DEV_START-->\n{"reset_slug": "dorahacks-deai-builder"}\n<!--TRIGGER_DEV_END-->')
        reset_entry = ingest_entry(reset_payload, self.tmp_root)
        self.assertEqual(reset_entry["status"], "pending_dev")
        self.assertEqual(reset_entry["completed_at"], "")

    def test_03_remote_site_http_sync_scaffold_and_publish_dry_run(self):
        # 1. 准备一个托管在“远端网站”目录上的 Spec/Plan 数据源
        remote_site_dir = self.tmp_root / "remote_pages_site"
        (remote_site_dir / "data" / "specs" / "remote-hack-2026").mkdir(parents=True, exist_ok=True)
        (remote_site_dir / "data" / "specs" / "remote-hack-2026" / "spec.md").write_text(
            "# Spec: Remote Hackathon Project\n\n支持通过网站远程读取 Spec 并自动开发。",
            encoding="utf-8",
        )
        (remote_site_dir / "data" / "specs" / "remote-hack-2026" / "plan.md").write_text(
            "# Plan: Remote Hackathon Project\n\n1. 构建全栈脚手架 2. 运行自动化测试。",
            encoding="utf-8",
        )
        remote_index = {
            "updated_at": "2026-11-16T10:30:00+08:00",
            "site_config": {
                "github_owner": "Lightofwang",
                "github_repo": "CloudAgentCluster",
                "default_branch": "main",
            },
            "hackathons": [
                {
                    "id": "remote-hack-2026",
                    "slug": "remote-hack-2026",
                    "title": "Remote HTTP Sync Test Hackathon",
                    "platform": "devpost",
                    "source_url": "https://devpost.com/hackathons/remote",
                    "deadline": "2026-12-31T23:59:00Z",
                    "prize_pool": "$10,000",
                    "tags": ["AI", "Web"],
                    "match_score": 95,
                    "status": "pending_dev",
                    "spec_path": "data/specs/remote-hack-2026/spec.md",
                    "plan_path": "data/specs/remote-hack-2026/plan.md",
                    "project_type": "fullstack-web",
                    "summary": "测试从网站 HTTP URL 拉取队列并生成代码",
                    "repo_url": "",
                    "fallback_path": "projects/remote-hack-2026",
                    "created_at": "2026-11-16T10:30:00+08:00",
                    "completed_at": "",
                }
            ],
        }
        (remote_site_dir / "data" / "hackathons.json").write_text(
            json.dumps(remote_index, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        handler = partial(QuietHTTPHandler, directory=str(remote_site_dir))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            site_url = f"http://127.0.0.1:{port}"
            synced = sync_from_site_url(site_url, self.tmp_root)
            self.assertEqual(len(synced["hackathons"]), 1)
            self.assertEqual(synced["hackathons"][0]["slug"], "remote-hack-2026")

            local_spec = self.tmp_root / "site" / "data" / "specs" / "remote-hack-2026" / "spec.md"
            local_plan = self.tmp_root / "site" / "data" / "specs" / "remote-hack-2026" / "plan.md"
            self.assertTrue(local_spec.exists())
            self.assertTrue(local_plan.exists())
            self.assertIn("Remote Hackathon Project", local_spec.read_text(encoding="utf-8"))

            # 2. 生成全栈脚手架
            project_dir = scaffold_project("remote-hack-2026", self.tmp_root)
            self.assertTrue((project_dir / "backend" / "server.py").exists())
            self.assertTrue((project_dir / "frontend" / "index.html").exists())
            self.assertTrue((project_dir / "tests" / "test_app.py").exists())

            # 3. 执行 publish_project --dry-run（真实执行脚手架里的 unittest 并流转状态）
            result = publish_project("remote-hack-2026", self.tmp_root, dry_run=True)
            self.assertTrue(result["tests_passed"])
            self.assertEqual(result["entry"]["status"], "completed")
            self.assertEqual(
                result["repo_url"],
                "https://github.com/Lightofwang/CloudAgentCluster/tree/main/projects/remote-hack-2026",
            )
        finally:
            server.shutdown()
            server.server_close()

    def test_04_cli_list_from_real_site_via_http(self):
        """验证通过命令行调用 scripts/sync_and_queue.py list --site-url 读取真实 site/ 目录。"""
        handler = partial(QuietHTTPHandler, directory=str(ROOT_DIR / "site"))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            # 将真实 site/ 复制到临时目录以验证 CLI 同步不污染工作区文件
            cli_root = self.tmp_root / "cli_workspace"
            shutil.copytree(ROOT_DIR / "site", cli_root / "site")
            res = subprocess.run(
                [
                    sys.executable,
                    str(ROOT_DIR / "scripts" / "sync_and_queue.py"),
                    "list",
                    "--root-dir",
                    str(cli_root),
                    "--site-url",
                    f"http://127.0.0.1:{port}",
                    "--json",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(res.returncode, 0, msg=res.stderr)
            items = json.loads(res.stdout)
            self.assertGreaterEqual(len(items), 1)
            self.assertIn("demo-ai-agent-copilot", [item["slug"] for item in items])
        finally:
            server.shutdown()
            server.server_close()

    def test_05_security_rejects_unauthorized_actor_and_wrong_passcode(self):
        base_payload = {
            "slug": "sec-test-hack",
            "title": "Security Gate Test",
            "platform": "devpost",
            "spec_content": "# Spec",
            "plan_content": "# Plan",
            "auth_hash": expected_passcode_hash(),
        }

        # 1. 非本人提交必须被拒绝
        with self.assertRaises(PermissionError):
            ingest_entry(base_payload, self.tmp_root, actor="random-stranger", require_auth=True)

        # 2. 口令错误或缺失必须被拒绝
        bad_pass_payload = dict(base_payload)
        bad_pass_payload["auth_hash"] = "0" * 64
        with self.assertRaises(PermissionError):
            ingest_entry(bad_pass_payload, self.tmp_root, actor="Lightofwang", require_auth=True)

        # 3. 本人 + 正确口令（或明文 passcode）放行入库
        valid_payload = dict(base_payload)
        valid_payload.pop("auth_hash")
        valid_payload["passcode"] = DEFAULT_PASSCODE
        entry = ingest_entry(valid_payload, self.tmp_root, actor="Lightofwang", require_auth=True)
        self.assertEqual(entry["submitted_by"], "Lightofwang")
        self.assertTrue(_is_owner_trusted(entry))
        self.assertFalse(_is_owner_trusted({"slug": "evil", "submitted_by": "attacker"}))


if __name__ == "__main__":
    unittest.main()
