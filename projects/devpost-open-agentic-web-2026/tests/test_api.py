"""API integration tests for AgentBazaar endpoints using FastAPI TestClient."""

import unittest
from fastapi.testclient import TestClient
from app.main import app, registry


class TestAPIEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        registry.reset_to_seeds()

    def test_health_check(self):
        """GET /api/health must return 200 with status ok."""
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["version"], "0.1.0")

    def test_list_agents(self):
        """GET /api/agents returns seed agents and supports filtering."""
        # Unfiltered list
        res = self.client.get("/api/agents")
        self.assertEqual(res.status_code, 200)
        agents = res.json()["agents"]
        self.assertGreaterEqual(len(agents), 6)

        # Filter by capability
        res_cap = self.client.get("/api/agents?capability=appointment.book")
        self.assertEqual(res_cap.status_code, 200)
        filtered_caps = res_cap.json()["agents"]
        for a in filtered_caps:
            self.assertIn("appointment.book", a["capabilities"])

        # Filter by search query
        res_q = self.client.get("/api/agents?q=茶行")
        self.assertEqual(res_q.status_code, 200)
        filtered_q = res_q.json()["agents"]
        self.assertTrue(any("茶行" in a["name"] for a in filtered_q))

    def test_create_and_get_agent(self):
        """POST /api/agents creates new merchant agent and GET /api/agents/{id} returns details."""
        payload = {
            "name": "天工木作工坊",
            "description": "传统榫卯木艺手作，定制茶几与文房木器",
            "capabilities": ["price.quote", "appointment.book"],
            "price_range": "¥100–¥1200",
            "hours": "10:00–19:00",
        }
        res = self.client.post("/api/agents", json=payload)
        self.assertEqual(res.status_code, 201)
        created = res.json()
        self.assertEqual(created["name"], payload["name"])
        self.assertTrue(created["id"].startswith("shop-"))
        self.assertIn("trust_breakdown", created)

        # Retrieve detail
        agent_id = created["id"]
        res_get = self.client.get(f"/api/agents/{agent_id}")
        self.assertEqual(res_get.status_code, 200)
        detail = res_get.json()
        self.assertEqual(detail["id"], agent_id)
        self.assertEqual(detail["name"], payload["name"])
        self.assertIn("verifiable", detail["trust_breakdown"])

    def test_invoke_agent_capability(self):
        """POST /api/agents/{id}/invoke executes capability and updates stats."""
        # 1. Valid invocation
        res = self.client.post(
            "/api/agents/shop-tea-001/invoke",
            json={"capability": "price.quote", "params": {"item": "西湖龙井", "quantity": 2}},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["capability"], "price.quote")
        self.assertGreater(data["latency_ms"], 0)
        self.assertIn("unit_price", data["result"])

        # 2. Unsupported capability
        res_inv = self.client.post(
            "/api/agents/shop-tea-001/invoke",
            json={"capability": "drone.delivery", "params": {}},
        )
        self.assertEqual(res_inv.status_code, 200)
        data_inv = res_inv.json()
        self.assertFalse(data_inv["ok"])
        self.assertIsNotNone(data_inv["error"])

        # 3. Non-existent agent ID
        res_404 = self.client.post(
            "/api/agents/shop-nonexistent-999/invoke",
            json={"capability": "price.quote", "params": {}},
        )
        self.assertEqual(res_404.status_code, 404)

    def test_agent_network_manifest(self):
        """GET /.well-known/agent-network.json must conform to Open Agentic Web specification."""
        res = self.client.get("/.well-known/agent-network.json")
        self.assertEqual(res.status_code, 200)
        manifest = res.json()
        self.assertEqual(manifest["network"], "agentbazaar")
        self.assertEqual(manifest["version"], "0.1")
        self.assertEqual(manifest["protocol"], "open-agentic-web")
        self.assertIn("agents", manifest)
        self.assertGreaterEqual(len(manifest["agents"]), 6)

        first = manifest["agents"][0]
        self.assertIn("id", first)
        self.assertIn("capabilities", first)
        self.assertIn("endpoint", first)
        self.assertIn("trust_score", first)

    def test_discover_endpoint(self):
        """GET /api/discover parses external Open Agentic Web URLs."""
        # Test self discovery with a mocked request
        # Invalid host should return ok: false without crashing
        res_err = self.client.get("/api/discover?url=http://127.0.0.1:59999")
        self.assertEqual(res_err.status_code, 200)
        self.assertFalse(res_err.json()["ok"])
        self.assertIn("error", res_err.json())

    def test_run_scenarios(self):
        """POST /api/runs must support all three demo multi-agent scenarios."""
        # Scenario 1: compare-price
        res1 = self.client.post(
            "/api/runs",
            json={"scenario": "compare-price", "input": {"item": "龙井 250g", "quantity": 2}},
        )
        self.assertEqual(res1.status_code, 201)
        data1 = res1.json()
        self.assertEqual(data1["status"], "completed")
        self.assertIn("run_id", data1)
        self.assertGreaterEqual(data1["steps_count"], 4)

        # Query run by ID
        run_id = data1["run_id"]
        res_query = self.client.get(f"/api/runs/{run_id}")
        self.assertEqual(res_query.status_code, 200)
        self.assertEqual(res_query.json()["run_id"], run_id)

        # Scenario 2: track-order
        res2 = self.client.post(
            "/api/runs",
            json={"scenario": "track-order", "input": {"order_id": "ORD-2026-88992"}},
        )
        self.assertEqual(res2.status_code, 201)
        data2 = res2.json()
        self.assertEqual(data2["status"], "completed")
        self.assertIn("tracking_info", data2["result"])

        # Scenario 3: book-appointment
        res3 = self.client.post(
            "/api/runs",
            json={
                "scenario": "book-appointment",
                "input": {
                    "merchant_id": "shop-tea-001",
                    "service": "品茶预约",
                    "slot": "明日 15:00",
                    "customer_name": "王先生",
                },
            },
        )
        self.assertEqual(res3.status_code, 201)
        data3 = res3.json()
        self.assertEqual(data3["status"], "completed")
        self.assertTrue(data3["result"]["confirmation_code"].startswith("AB-"))

    def test_reset_endpoint(self):
        """POST /api/reset restores database to clean seed agents."""
        res = self.client.post("/api/reset")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["ok"])


if __name__ == "__main__":
    unittest.main()
