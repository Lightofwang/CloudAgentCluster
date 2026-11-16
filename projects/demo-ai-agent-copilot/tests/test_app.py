import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "backend"))

from server import create_server  # noqa: E402


class TestCopilotApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server("127.0.0.1", 0)
        cls.port = cls.server.server_address[1]
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_frontend_and_health(self):
        with urllib.request.urlopen(f"{self.base_url}/") as resp:
            self.assertEqual(resp.status, 200)
            html = resp.read().decode("utf-8")
            self.assertIn("Pitch & Architecture Copilot", html)

        with urllib.request.urlopen(f"{self.base_url}/api/health") as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "ok")
            self.assertGreaterEqual(data["tracks_count"], 4)

    def test_tracks_endpoint(self):
        with urllib.request.urlopen(f"{self.base_url}/api/tracks") as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertGreaterEqual(len(data["tracks"]), 4)

    def test_analyze_success_and_validation(self):
        payload = json.dumps(
            {
                "project_name": "AgentHub",
                "track": "ai-agents",
                "problem_statement": "自动抓取全球 Hackathon 并生成完整架构与原型代码。",
                "tech_stack": ["Python API", "Web UI", "AI Agent", "Unittest"],
                "team_size": 2,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/analyze",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            res = json.loads(resp.read().decode("utf-8"))
            self.assertIn("overall_score", res)
            self.assertGreaterEqual(res["overall_score"], 60)
            self.assertEqual(len(res["pitch_outline"]), 6)
            self.assertGreaterEqual(len(res["architecture_modules"]), 4)

        # 验证缺失必填字段返回 400
        bad_payload = json.dumps({"project_name": "OnlyName"}).encode("utf-8")
        bad_req = urllib.request.Request(
            f"{self.base_url}/api/analyze",
            data=bad_payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(bad_req)
        self.assertEqual(ctx.exception.code, 400)
        ctx.exception.close()


if __name__ == "__main__":
    unittest.main()
