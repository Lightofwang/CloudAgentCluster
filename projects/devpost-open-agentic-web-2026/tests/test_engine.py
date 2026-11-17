"""Unit tests for local deterministic rule engine in AgentBazaar."""

import unittest
from app.engine import execute_agent_capability, run_orchestration
from app.models import Agent, TrustBreakdown
from app.registry import AgentRegistry


class TestRuleEngine(unittest.TestCase):
    def setUp(self):
        self.mock_tea_agent = Agent(
            id="shop-tea-001",
            name="云雾茶行",
            description="本地名茶行",
            capabilities=["price.quote", "stock.check", "appointment.book"],
            endpoint="/api/agents/shop-tea-001/invoke",
            price_range="¥50–¥500",
            hours="09:00–21:00",
            trust_score=90,
            trust_breakdown=TrustBreakdown(verifiable=30, success_rate=35, latency=25),
            calls_total=10,
            calls_ok=9,
            p50_latency_ms=180,
            latencies=[180],
        )

    def test_price_quote_determinism(self):
        """Calling price quote for the same item must return consistent and positive results."""
        ok1, lat1, res1, err1 = execute_agent_capability(
            self.mock_tea_agent, "price.quote", {"item": "龙井 250g", "quantity": 2}
        )
        self.assertTrue(ok1)
        self.assertIsNone(err1)
        self.assertEqual(res1["quantity"], 2)
        self.assertEqual(res1["total"], res1["unit_price"] * 2)

        ok2, lat2, res2, err2 = execute_agent_capability(
            self.mock_tea_agent, "price.quote", {"item": "龙井 250g", "quantity": 2}
        )
        self.assertTrue(ok2)
        # Check deterministic unit price
        self.assertEqual(res1["unit_price"], res2["unit_price"])
        self.assertEqual(res1["total"], res2["total"])

    def test_stock_check_determinism(self):
        """Stock check must return reproducible stock counts."""
        ok1, _, res1, _ = execute_agent_capability(
            self.mock_tea_agent, "stock.check", {"item": "高山普洱"}
        )
        self.assertTrue(ok1)
        self.assertTrue(res1["in_stock"])
        self.assertGreater(res1["quantity"], 0)

        ok2, _, res2, _ = execute_agent_capability(
            self.mock_tea_agent, "stock.check", {"item": "高山普洱"}
        )
        self.assertEqual(res1["quantity"], res2["quantity"])

    def test_appointment_booking(self):
        """Booking appointment must return confirmed status and confirmation code AB-XXXXXX."""
        ok, lat, res, err = execute_agent_capability(
            self.mock_tea_agent,
            "appointment.book",
            {
                "service": "品茶席位",
                "slot": "明日 14:00–16:00",
                "customer_name": "张先生",
                "contact": "13800000000",
            },
        )
        self.assertTrue(ok)
        self.assertIsNone(err)
        self.assertEqual(res["status"], "confirmed")
        self.assertTrue(res["confirmation_code"].startswith("AB-"))
        self.assertEqual(res["customer_name"], "张先生")

    def test_unsupported_capability(self):
        """Calling an unregistered capability must fail gracefully with descriptive error."""
        ok, lat, res, err = execute_agent_capability(
            self.mock_tea_agent, "flight.booking", {"destination": "Tokyo"}
        )
        self.assertFalse(ok)
        self.assertIsNone(res)
        self.assertIn("not supported", err)

    def test_multi_agent_orchestration_price_comparison(self):
        """Test multi-agent compare-price scenario end to end."""
        registry = AgentRegistry()
        run = run_orchestration(
            registry=registry,
            scenario="compare-price",
            input_data={"item": "龙井 250g", "quantity": 2},
        )
        self.assertEqual(run.status, "completed")
        self.assertGreaterEqual(len(run.steps), 3)
        self.assertIn("best_quote", run.result)
        self.assertIn("all_quotes", run.result)
        self.assertGreater(len(run.result["all_quotes"]), 0)


if __name__ == "__main__":
    unittest.main()
