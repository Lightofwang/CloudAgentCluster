"""Comprehensive FastAPI HTTP endpoints and Fearless Draft rule tests."""

from __future__ import annotations

import unittest
from fastapi.testclient import TestClient
from main import app
from app.db import init_db
from app.seed import seed_database
from app.services.draft import DRAFT_TURNS


class TestDraftLensAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_database()
        cls.client = TestClient(app)

    # -------------------------------------------------------------
    # 1. System & Info Endpoints
    # -------------------------------------------------------------
    def test_health_check(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})

    def test_grid_status(self):
        resp = self.client.get("/api/grid/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("mode"), "sample-data")
        self.assertFalse(data.get("grid_connected"))

    # -------------------------------------------------------------
    # 2. Teams, Players, Matches, Champions
    # -------------------------------------------------------------
    def test_teams_list_and_filter(self):
        # All teams
        resp = self.client.get("/api/teams")
        self.assertEqual(resp.status_code, 200)
        teams = resp.json()
        self.assertEqual(len(teams), 8)

        # Filter by style
        resp = self.client.get("/api/teams?style=early-aggression")
        self.assertEqual(resp.status_code, 200)
        filtered = resp.json()
        self.assertGreaterEqual(len(filtered), 1)
        for t in filtered:
            self.assertEqual(t["style"], "early-aggression")

    def test_team_detail_and_404(self):
        resp = self.client.get("/api/teams/t01")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["id"], "t01")
        self.assertIn("players", data)
        self.assertEqual(len(data["players"]), 5)
        self.assertIn("recent_matches", data)

        # 404 for unknown
        resp_404 = self.client.get("/api/teams/unknown_team_xyz")
        self.assertEqual(resp_404.status_code, 404)

    def test_players_endpoint(self):
        resp = self.client.get("/api/players")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 40)

        resp_team = self.client.get("/api/players?team_id=t01")
        self.assertEqual(resp_team.status_code, 200)
        self.assertEqual(len(resp_team.json()), 5)

    def test_matches_endpoint(self):
        # Default limit 20
        resp = self.client.get("/api/matches")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 20)

        # Custom limit
        resp_custom = self.client.get("/api/matches?limit=5")
        self.assertEqual(resp_custom.status_code, 200)
        self.assertEqual(len(resp_custom.json()), 5)

        # Filter by team
        resp_team = self.client.get("/api/matches?team_id=t01&limit=10")
        self.assertEqual(resp_team.status_code, 200)
        for m in resp_team.json():
            self.assertTrue(m["team_id"] == "t01" or m["opponent_id"] == "t01")

    def test_champions_endpoint(self):
        resp = self.client.get("/api/champions")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 60)

        resp_mid = self.client.get("/api/champions?role=MID")
        self.assertEqual(resp_mid.status_code, 200)
        self.assertEqual(len(resp_mid.json()), 12)
        for c in resp_mid.json():
            self.assertEqual(c["role"], "MID")

    # -------------------------------------------------------------
    # 3. Macro Scouting Report
    # -------------------------------------------------------------
    def test_scout_report(self):
        resp = self.client.get("/api/scout/t01?matches=5")
        self.assertEqual(resp.status_code, 200)
        report = resp.json()

        self.assertEqual(report["team_id"], "t01")
        self.assertIn("matches_analyzed", report)
        self.assertIn("objective_rates", report)
        self.assertIn("dragon", report["objective_rates"])
        self.assertIn("baron", report["objective_rates"])
        self.assertIn("herald", report["objective_rates"])
        self.assertIn("avg_vision_score", report)
        self.assertIn("first_blood_rate", report)
        self.assertIn("gold_diff_at_15", report)
        self.assertIn("gold_diff_curve", report)
        self.assertIn("style_summary", report)
        self.assertTrue(len(report["style_summary"]) > 5)
        self.assertIn("champion_preferences", report)
        self.assertLessEqual(len(report["champion_preferences"]), 5)

        # 404 for unknown team
        resp_404 = self.client.get("/api/scout/t99999")
        self.assertEqual(resp_404.status_code, 404)

    # -------------------------------------------------------------
    # 4. Draft Simulator & Fearless Draft Rules
    # -------------------------------------------------------------
    def test_draft_session_and_recommendations(self):
        # Create draft session
        resp = self.client.post("/api/draft", json={
            "blue_team_id": "t01",
            "red_team_id": "t02",
            "series_type": "BO3",
        })
        self.assertEqual(resp.status_code, 200)
        draft = resp.json()
        draft_id = draft["id"]
        self.assertEqual(draft["current_game"], 1)
        self.assertEqual(draft["current_turn_index"], 0)
        self.assertEqual(draft["status"], "in_progress")

        # Turn 0 is Blue Ban
        # Illegal action: Red attempts to ban out of turn
        resp_err = self.client.post(f"/api/draft/{draft_id}/ban", json={
            "champion_id": "c001",
            "side": "red",
        })
        self.assertEqual(resp_err.status_code, 400)
        self.assertIn("Turn mismatch", resp_err.json()["detail"])

        # Illegal action: Blue attempts to pick instead of ban
        resp_err_act = self.client.post(f"/api/draft/{draft_id}/pick", json={
            "champion_id": "c001",
            "side": "blue",
        })
        self.assertEqual(resp_err_act.status_code, 400)
        self.assertIn("Action mismatch", resp_err_act.json()["detail"])

        # Legal Turn 0: Blue Bans c001
        resp_ok = self.client.post(f"/api/draft/{draft_id}/ban", json={
            "champion_id": "c001",
            "side": "blue",
        })
        self.assertEqual(resp_ok.status_code, 200)
        draft = resp_ok.json()
        self.assertEqual(draft["current_turn_index"], 1)

        # Recommendation Engine Check for Turn 1 (Red Ban)
        rec_resp = self.client.post(f"/api/draft/{draft_id}/recommend")
        self.assertEqual(rec_resp.status_code, 200)
        rec_data = rec_resp.json()
        recs = rec_data.get("recommendations", [])
        self.assertEqual(len(recs), 3, "Expected Top 3 recommendations")
        self.assertGreaterEqual(recs[0]["score"], recs[1]["score"])
        self.assertGreaterEqual(recs[1]["score"], recs[2]["score"])
        for r in recs:
            self.assertTrue(len(r["reasons"]) > 0, "Reasons should be non-empty")
            self.assertNotEqual(r["champion_id"], "c001", "Banned champion c001 should not be recommended")

    def test_fearless_draft_rule_across_games(self):
        """Simulate Game 1 completely, advance to Game 2, and ensure Fearless Draft locks Game 1 picks."""
        resp = self.client.post("/api/draft", json={
            "blue_team_id": "t01",
            "red_team_id": "t02",
            "series_type": "BO3",
        })
        self.assertEqual(resp.status_code, 200)
        draft_id = resp.json()["id"]

        # 20 distinct champions for Game 1
        # c001..c010 for bans, c011..c020 for picks
        game1_picks = []
        for i, turn in enumerate(DRAFT_TURNS):
            cid = f"c{i+1:03d}"
            endpoint = "/ban" if turn["action"] == "ban" else "/pick"
            res = self.client.post(f"/api/draft/{draft_id}{endpoint}", json={
                "champion_id": cid,
                "side": turn["side"],
            })
            self.assertEqual(res.status_code, 200, f"Turn {i} ({turn['label']}) failed: {res.text}")
            if turn["action"] == "pick":
                game1_picks.append(cid)

        self.assertEqual(len(game1_picks), 10, "10 picks expected in Game 1")

        # Advance to Game 2 (Blue wins Game 1)
        res_next = self.client.post(f"/api/draft/{draft_id}/next-game", json={"winner": "blue"})
        self.assertEqual(res_next.status_code, 200)
        state_g2 = res_next.json()
        self.assertEqual(state_g2["current_game"], 2)
        self.assertEqual(state_g2["blue_score"], 1)
        self.assertEqual(state_g2["red_score"], 0)
        self.assertEqual(state_g2["current_turn_index"], 0)

        # Confirm all 10 picks are in series_picked_champions
        for p in game1_picks:
            self.assertIn(p, state_g2["series_picked_champions"])

        # Play 6 bans in Game 2 (c021..c026)
        for i in range(6):
            turn = DRAFT_TURNS[i]
            cid = f"c{21+i:03d}"
            res = self.client.post(f"/api/draft/{draft_id}/ban", json={
                "champion_id": cid,
                "side": turn["side"],
            })
            self.assertEqual(res.status_code, 200)

        # Now Turn 6: Blue Pick 1!
        # Attempt to pick any champion from Game 1 picks -> MUST fail with 400 Fearless Draft!
        locked_cid = game1_picks[0]
        res_illegal = self.client.post(f"/api/draft/{draft_id}/pick", json={
            "champion_id": locked_cid,
            "side": "blue",
        })
        self.assertEqual(res_illegal.status_code, 400)
        self.assertIn("champion already picked in this series (Fearless Draft)", res_illegal.json()["detail"])

        # Attempting a valid fresh pick (e.g. c030) should succeed!
        res_legal = self.client.post(f"/api/draft/{draft_id}/pick", json={
            "champion_id": "c030",
            "side": "blue",
        })
        self.assertEqual(res_legal.status_code, 200)

        # Verify series history
        hist_resp = self.client.get(f"/api/draft/{draft_id}/history")
        self.assertEqual(hist_resp.status_code, 200)
        hist = hist_resp.json()
        self.assertEqual(hist["total_games"], 2)
        self.assertEqual(hist["blue_team"]["score"], 1)

    # -------------------------------------------------------------
    # 5. Static Assets
    # -------------------------------------------------------------
    def test_static_assets(self):
        resp_index = self.client.get("/")
        self.assertEqual(resp_index.status_code, 200)
        self.assertIn("DraftLens", resp_index.text)

        resp_css = self.client.get("/static/css/style.css")
        self.assertEqual(resp_css.status_code, 200)

        resp_js = self.client.get("/static/js/app.js")
        self.assertEqual(resp_js.status_code, 200)


if __name__ == "__main__":
    unittest.main()
