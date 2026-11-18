"""Seed data integrity and matrix symmetry test suite."""

from __future__ import annotations

import unittest
from app.db import get_connection, init_db
from app.seed import seed_database


class TestSeedIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_database()

    def test_entity_counts(self):
        conn = get_connection()
        cur = conn.cursor()
        try:
            team_count = cur.execute("SELECT COUNT(*) FROM teams").fetchone()[0]
            player_count = cur.execute("SELECT COUNT(*) FROM players").fetchone()[0]
            champ_count = cur.execute("SELECT COUNT(*) FROM champions").fetchone()[0]
            match_count = cur.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
            matchup_count = cur.execute("SELECT COUNT(*) FROM matchups").fetchone()[0]

            self.assertEqual(team_count, 8, "Expected 8 teams")
            self.assertEqual(player_count, 40, "Expected 40 players (5 per team)")
            self.assertEqual(champ_count, 60, "Expected 60 champions")
            self.assertEqual(match_count, 120, "Expected 120 match records")
            self.assertEqual(matchup_count, 60 * 59, "Expected 3540 matchup records")
        finally:
            conn.close()

    def test_team_roster_composition(self):
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT id FROM teams")
            team_ids = [r[0] for r in cur.fetchall()]
            expected_roles = {"TOP", "JUG", "MID", "ADC", "SUP"}

            for tid in team_ids:
                cur.execute("SELECT role FROM players WHERE team_id = ?", (tid,))
                roles = {r[0] for r in cur.fetchall()}
                self.assertEqual(roles, expected_roles, f"Team {tid} missing standard roles")
        finally:
            conn.close()

    def test_champion_role_distribution(self):
        conn = get_connection()
        cur = conn.cursor()
        try:
            for role in ["TOP", "JUG", "MID", "ADC", "SUP"]:
                cur.execute("SELECT COUNT(*) FROM champions WHERE role = ?", (role,))
                count = cur.fetchone()[0]
                self.assertEqual(count, 12, f"Expected 12 champions for role {role}")
        finally:
            conn.close()

    def test_matchup_matrix_symmetry(self):
        conn = get_connection()
        cur = conn.cursor()
        try:
            # Query a sample of 200 random pairs to verify mathematical symmetry
            cur.execute("""
            SELECT m1.champion_a, m1.champion_b, m1.winrate, m1.synergy, m1.counter,
                   m2.winrate, m2.synergy, m2.counter
            FROM matchups m1
            JOIN matchups m2 ON m1.champion_a = m2.champion_b AND m1.champion_b = m2.champion_a
            LIMIT 200
            """)
            rows = cur.fetchall()
            self.assertGreater(len(rows), 0, "Matchup pairs should exist")

            for r in rows:
                c_a, c_b, wr1, syn1, cnt1, wr2, syn2, cnt2 = r
                # Winrate sum should equal 1.0 (within float tolerance)
                self.assertAlmostEqual(wr1 + wr2, 1.0, places=2, msg=f"Winrate asymmetry between {c_a} and {c_b}")
                # Synergy should be symmetric
                self.assertAlmostEqual(syn1, syn2, places=2, msg=f"Synergy asymmetry between {c_a} and {c_b}")
                # Counter should be anti-symmetric
                self.assertAlmostEqual(cnt1 + cnt2, 0.0, places=2, msg=f"Counter anti-symmetry error between {c_a} and {c_b}")
        finally:
            conn.close()

    def test_idempotence(self):
        # Running seed again should produce the identical counts without error
        res = seed_database()
        self.assertEqual(res["teams"], 8)
        self.assertEqual(res["players"], 40)
        self.assertEqual(res["champions"], 60)
        self.assertEqual(res["matches"], 120)


if __name__ == "__main__":
    unittest.main()
