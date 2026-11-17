"""Unit tests for Trust Score calculation in AgentBazaar."""

import unittest
from app.registry import calculate_trust_score


class TestTrustScore(unittest.TestCase):
    def test_ideal_agent(self):
        """Test agent with perfect verification, 100% success rate, and ultra-low latency."""
        score, breakdown = calculate_trust_score(
            verifiable=30,
            calls_ok=100,
            calls_total=100,
            p50_latency_ms=120,
        )
        self.assertEqual(breakdown.verifiable, 30)
        self.assertEqual(breakdown.success_rate, 40)
        self.assertEqual(breakdown.latency, 30)
        self.assertEqual(score, 100)

    def test_zero_calls_new_agent(self):
        """Test newly registered agent with zero calls."""
        score, breakdown = calculate_trust_score(
            verifiable=30,
            calls_ok=0,
            calls_total=0,
            p50_latency_ms=150,
        )
        self.assertEqual(breakdown.verifiable, 30)
        self.assertEqual(breakdown.success_rate, 35)  # Base initial success rate
        self.assertEqual(breakdown.latency, 30)
        self.assertEqual(score, 95)

    def test_all_calls_failed(self):
        """Test agent where all calls failed."""
        score, breakdown = calculate_trust_score(
            verifiable=30,
            calls_ok=0,
            calls_total=50,
            p50_latency_ms=200,
        )
        self.assertEqual(breakdown.verifiable, 30)
        self.assertEqual(breakdown.success_rate, 0)
        self.assertEqual(breakdown.latency, 30)
        self.assertEqual(score, 60)

    def test_high_latency_extremes(self):
        """Test agent exceeding latency thresholds."""
        # > 2000ms latency gets 0 points
        score, breakdown = calculate_trust_score(
            verifiable=30,
            calls_ok=100,
            calls_total=100,
            p50_latency_ms=2500,
        )
        self.assertEqual(breakdown.latency, 0)
        self.assertEqual(breakdown.success_rate, 40)
        self.assertEqual(score, 70)

        # Mid-tier latency: 1100ms should get around 15 points
        score_mid, breakdown_mid = calculate_trust_score(
            verifiable=30,
            calls_ok=100,
            calls_total=100,
            p50_latency_ms=1100,
        )
        self.assertTrue(13 <= breakdown_mid.latency <= 17)

    def test_unverifiable_source(self):
        """Test unverified or external agent with zero verification score."""
        score, breakdown = calculate_trust_score(
            verifiable=0,
            calls_ok=50,
            calls_total=100,
            p50_latency_ms=3000,
        )
        self.assertEqual(breakdown.verifiable, 0)
        self.assertEqual(breakdown.success_rate, 20)
        self.assertEqual(breakdown.latency, 0)
        self.assertEqual(score, 20)

    def test_score_boundaries(self):
        """Test clamping to 0-100 regardless of arbitrary input values."""
        score_low, _ = calculate_trust_score(
            verifiable=-50,
            calls_ok=-10,
            calls_total=10,
            p50_latency_ms=9999,
        )
        self.assertEqual(score_low, 0)

        score_high, _ = calculate_trust_score(
            verifiable=100,
            calls_ok=200,
            calls_total=100,
            p50_latency_ms=10,
        )
        self.assertLessEqual(score_high, 100)


if __name__ == "__main__":
    unittest.main()
