"""Seed data generation and database population for DraftLens."""

from __future__ import annotations

import json
import random
import sqlite3
from typing import Dict, List, Tuple
from app.db import get_connection, init_db

# Fictional Teams
TEAMS_DATA = [
    {
        "id": "t01",
        "name": "Nova Lynx",
        "region": "Fictional League",
        "style": "early-aggression",
        "win_rate": 0.68,
        "avg_game_minutes": 31.2,
        "objective_rates": {"dragon": 0.62, "herald": 0.55, "baron": 0.48},
        "first_blood_rate": 0.57,
        "avg_vision_score": 78.4,
    },
    {
        "id": "t02",
        "name": "Iron Valkyrie",
        "region": "Fictional League",
        "style": "late-macro",
        "win_rate": 0.64,
        "avg_game_minutes": 36.5,
        "objective_rates": {"dragon": 0.54, "herald": 0.46, "baron": 0.61},
        "first_blood_rate": 0.48,
        "avg_vision_score": 84.2,
    },
    {
        "id": "t03",
        "name": "Shadow Vortex",
        "region": "Fictional League",
        "style": "skirmish",
        "win_rate": 0.59,
        "avg_game_minutes": 29.8,
        "objective_rates": {"dragon": 0.58, "herald": 0.62, "baron": 0.44},
        "first_blood_rate": 0.63,
        "avg_vision_score": 71.5,
    },
    {
        "id": "t04",
        "name": "Solar Flare",
        "region": "Fictional League",
        "style": "early-aggression",
        "win_rate": 0.55,
        "avg_game_minutes": 30.5,
        "objective_rates": {"dragon": 0.59, "herald": 0.58, "baron": 0.42},
        "first_blood_rate": 0.54,
        "avg_vision_score": 74.0,
    },
    {
        "id": "t05",
        "name": "Frost Guard",
        "region": "Fictional League",
        "style": "late-macro",
        "win_rate": 0.52,
        "avg_game_minutes": 37.1,
        "objective_rates": {"dragon": 0.51, "herald": 0.42, "baron": 0.56},
        "first_blood_rate": 0.45,
        "avg_vision_score": 82.0,
    },
    {
        "id": "t06",
        "name": "Thunder Strike",
        "region": "Fictional League",
        "style": "skirmish",
        "win_rate": 0.48,
        "avg_game_minutes": 28.9,
        "objective_rates": {"dragon": 0.49, "herald": 0.53, "baron": 0.40},
        "first_blood_rate": 0.52,
        "avg_vision_score": 69.8,
    },
    {
        "id": "t07",
        "name": "Cyber Dragon",
        "region": "Fictional League",
        "style": "late-macro",
        "win_rate": 0.45,
        "avg_game_minutes": 35.8,
        "objective_rates": {"dragon": 0.47, "herald": 0.44, "baron": 0.50},
        "first_blood_rate": 0.43,
        "avg_vision_score": 79.5,
    },
    {
        "id": "t08",
        "name": "Phantom Eclipse",
        "region": "Fictional League",
        "style": "early-aggression",
        "win_rate": 0.42,
        "avg_game_minutes": 32.0,
        "objective_rates": {"dragon": 0.46, "herald": 0.48, "baron": 0.38},
        "first_blood_rate": 0.49,
        "avg_vision_score": 72.3,
    },
]

CHAMPIONS_RAW = [
    # 12 TOP
    ("c001", "Aegis", "The Iron Bastion", "TOP", 0.52, 0.22, 0.12, "#3b82f6"),
    ("c002", "Titan", "Colossus of the Peak", "TOP", 0.51, 0.18, 0.08, "#64748b"),
    ("c003", "Obsidian", "The Molten Edge", "TOP", 0.49, 0.25, 0.15, "#ef4444"),
    ("c004", "Vanguard", "Shield of Dawn", "TOP", 0.53, 0.20, 0.10, "#f59e0b"),
    ("c005", "Paladin", "Radiant Arbiter", "TOP", 0.50, 0.16, 0.06, "#10b981"),
    ("c006", "Quake", "Earthbreaker", "TOP", 0.48, 0.14, 0.05, "#8b5cf6"),
    ("c007", "Grem", "Stone Sentinel", "TOP", 0.51, 0.19, 0.09, "#6b7280"),
    ("c008", "Blade", "Swift Cleaver", "TOP", 0.54, 0.28, 0.22, "#dc2626"),
    ("c009", "Strider", "Highland Warden", "TOP", 0.49, 0.15, 0.04, "#059669"),
    ("c010", "Dusk", "Twilight Sovereign", "TOP", 0.50, 0.21, 0.11, "#4f46e5"),
    ("c011", "Rune", "Ancient Runeplate", "TOP", 0.47, 0.13, 0.03, "#0891b2"),
    ("c012", "Cinder", "Ember Brawler", "TOP", 0.52, 0.23, 0.14, "#ea580c"),

    # 12 JUG
    ("c013", "Bolt", "Storm Claw", "JUG", 0.53, 0.26, 0.19, "#0284c7"),
    ("c014", "Stalker", "Shadow Prowler", "JUG", 0.52, 0.24, 0.16, "#7c3aed"),
    ("c015", "Glacius", "Tundra Behemoth", "JUG", 0.50, 0.21, 0.09, "#38bdf8"),
    ("c016", "Vortex", "Abyssal Maw", "JUG", 0.49, 0.18, 0.08, "#6366f1"),
    ("c017", "Hunter", "Forest Tracker", "JUG", 0.51, 0.22, 0.10, "#16a34a"),
    ("c018", "Surge", "Kinetic Predator", "JUG", 0.54, 0.29, 0.24, "#e11d48"),
    ("c019", "Spectre", "Phantasm of the Wild", "JUG", 0.48, 0.17, 0.07, "#9333ea"),
    ("c020", "Frost", "Permafrost Wyrm", "JUG", 0.50, 0.19, 0.08, "#0ea5e9"),
    ("c021", "Ignis", "Fire Heart Beast", "JUG", 0.51, 0.20, 0.11, "#f97316"),
    ("c022", "Apex", "Primal Chieftain", "JUG", 0.53, 0.25, 0.18, "#d97706"),
    ("c023", "Blight", "Plague Lurker", "JUG", 0.47, 0.14, 0.05, "#84cc16"),
    ("c024", "Torrent", "River Striker", "JUG", 0.50, 0.16, 0.06, "#06b6d4"),

    # 12 MID
    ("c025", "Zephyr", "Gale Magus", "MID", 0.53, 0.31, 0.25, "#38bdf8"),
    ("c026", "Solaria", "Solar Sovereign", "MID", 0.52, 0.28, 0.20, "#eab308"),
    ("c027", "Nyx", "Void Empress", "MID", 0.54, 0.33, 0.28, "#a855f7"),
    ("c028", "Chrono", "Temporal Weaver", "MID", 0.51, 0.24, 0.14, "#06b6d4"),
    ("c029", "Cipher", "Code Spellcaster", "MID", 0.49, 0.20, 0.10, "#14b8a6"),
    ("c030", "Flare", "Phoenix Evoker", "MID", 0.52, 0.27, 0.17, "#f43f5e"),
    ("c031", "Mirage", "Illusionist Grand", "MID", 0.48, 0.19, 0.08, "#c084fc"),
    ("c032", "Zenith", "Star Stargazer", "MID", 0.50, 0.22, 0.11, "#6366f1"),
    ("c033", "Rift", "Dimensional Archmage", "MID", 0.51, 0.25, 0.13, "#ec4899"),
    ("c034", "Tempest", "Thunder Caller", "MID", 0.53, 0.29, 0.21, "#3b82f6"),
    ("c035", "Echo", "Harmonic Pulse", "MID", 0.49, 0.18, 0.07, "#22c55e"),
    ("c036", "Pyra", "Pyroclast Sage", "MID", 0.50, 0.23, 0.12, "#ff6b6b"),

    # 12 ADC
    ("c037", "Striker", "Precision Deadeye", "ADC", 0.53, 0.32, 0.21, "#f43f5e"),
    ("c038", "Gale", "Wind Marksman", "ADC", 0.52, 0.30, 0.18, "#0284c7"),
    ("c039", "Nova", "Cosmic Archer", "ADC", 0.54, 0.34, 0.26, "#8b5cf6"),
    ("c040", "Prism", "Light Cannoneer", "ADC", 0.50, 0.22, 0.10, "#eab308"),
    ("c041", "Dawn", "Daybreak Ranger", "ADC", 0.51, 0.26, 0.14, "#f59e0b"),
    ("c042", "Shade", "Shadow Crossbow", "ADC", 0.49, 0.24, 0.12, "#475569"),
    ("c043", "Breeze", "Stormfeather", "ADC", 0.50, 0.20, 0.08, "#2dd4bf"),
    ("c044", "Ranger", "Outland Scout", "ADC", 0.48, 0.18, 0.06, "#84cc16"),
    ("c045", "Abyss", "Void Ballista", "ADC", 0.52, 0.28, 0.17, "#9333ea"),
    ("c046", "Forge", "Heavy Artificer", "ADC", 0.51, 0.23, 0.11, "#ea580c"),
    ("c047", "Siren", "Tide Hunter", "ADC", 0.49, 0.19, 0.07, "#0284c7"),
    ("c048", "Valkyrie", "Spear of Valhalla", "ADC", 0.53, 0.31, 0.22, "#e11d48"),

    # 12 SUP
    ("c049", "Beacon", "Lighthouse Warden", "SUP", 0.53, 0.28, 0.16, "#eab308"),
    ("c050", "Sentinel", "Guardian of Souls", "SUP", 0.52, 0.25, 0.14, "#10b981"),
    ("c051", "Bastion", "Iron Wall", "SUP", 0.51, 0.23, 0.12, "#3b82f6"),
    ("c052", "Oracle", "Seer of Destiny", "SUP", 0.50, 0.20, 0.09, "#a855f7"),
    ("c053", "Cleric", "Holy Restorer", "SUP", 0.49, 0.18, 0.07, "#22c55e"),
    ("c054", "Weaver", "Thread Binder", "SUP", 0.52, 0.24, 0.13, "#ec4899"),
    ("c055", "Sylvan", "Natures Embrace", "SUP", 0.50, 0.21, 0.08, "#16a34a"),
    ("c056", "Aura", "Harmonic Echo", "SUP", 0.51, 0.22, 0.10, "#06b6d4"),
    ("c057", "Karmae", "Spiritual Shield", "SUP", 0.54, 0.29, 0.20, "#f43f5e"),
    ("c058", "Warden", "Deep Sea Anchor", "SUP", 0.49, 0.19, 0.08, "#0284c7"),
    ("c059", "Phantom", "Grave Keeper", "SUP", 0.48, 0.16, 0.06, "#64748b"),
    ("c060", "Storm", "Thunder Totem", "SUP", 0.51, 0.23, 0.11, "#8b5cf6"),
]


def generate_players(teams: List[Dict]) -> List[Dict]:
    roles = ["TOP", "JUG", "MID", "ADC", "SUP"]
    role_to_champs = {
        "TOP": [c[0] for c in CHAMPIONS_RAW if c[3] == "TOP"],
        "JUG": [c[0] for c in CHAMPIONS_RAW if c[3] == "JUG"],
        "MID": [c[0] for c in CHAMPIONS_RAW if c[3] == "MID"],
        "ADC": [c[0] for c in CHAMPIONS_RAW if c[3] == "ADC"],
        "SUP": [c[0] for c in CHAMPIONS_RAW if c[3] == "SUP"],
    }
    players = []
    pid_counter = 1
    for team in teams:
        team_abbr = team["name"][:3].upper()
        for role in roles:
            pid = f"p{pid_counter:02d}"
            pname = f"{team_abbr}_{role}"
            base_kda = round(3.0 + (team["win_rate"] * 2.0) + (random.random() * 0.8 - 0.4), 2)
            pool = random.sample(role_to_champs[role], k=5)
            champion_pool = [
                {"champion_id": cid, "comfort": round(0.70 + idx * 0.06, 2)}
                for idx, cid in enumerate(pool)
            ]
            form = random.choice(["Great", "Stable", "Peaking", "Hot"])
            players.append({
                "id": pid,
                "team_id": team["id"],
                "name": pname,
                "role": role,
                "kda": base_kda,
                "champion_pool": champion_pool,
                "recent_form": form,
            })
            pid_counter += 1
    return players


def generate_matches(teams: List[Dict]) -> List[Dict]:
    random.seed(42)
    matches = []
    team_ids = [t["id"] for t in teams]
    team_dict = {t["id"]: t for t in teams}

    match_counter = 101
    # 120 matches total
    for i in range(120):
        t1, t2 = random.sample(team_ids, 2)
        win_prob = team_dict[t1]["win_rate"] / (team_dict[t1]["win_rate"] + team_dict[t2]["win_rate"])
        t1_wins = random.random() < win_prob
        result = "win" if t1_wins else "loss"

        duration = round(random.uniform(25.0, 42.0), 1)

        # Generate realistic gold diff curve at min 5, 10, 15, 20, 25, 30
        curve = []
        base_diff = 400 if t1_wins else -400
        for m in [5, 10, 15, 20, 25, 30]:
            if m > duration:
                break
            mult = m / 15.0
            jitter = random.randint(-250, 250)
            diff = int(base_diff * mult + jitter)
            curve.append({"minute": m, "diff": diff})

        fb = 1 if (t1_wins and random.random() < 0.65) or (not t1_wins and random.random() < 0.35) else 0
        dragons = random.randint(2, 4) if t1_wins else random.randint(0, 2)
        barons = random.randint(1, 2) if t1_wins else random.randint(0, 1)
        towers = random.randint(7, 11) if t1_wins else random.randint(1, 5)
        heralds = random.randint(1, 2) if t1_wins else random.randint(0, 1)

        v_score = round(random.uniform(65.0, 95.0), 1)

        matches.append({
            "id": f"m{match_counter}",
            "team_id": t1,
            "opponent_id": t2,
            "result": result,
            "duration_minutes": duration,
            "gold_diff_curve": curve,
            "objectives": {
                "dragons": dragons,
                "barons": barons,
                "towers": towers,
                "heralds": heralds,
            },
            "first_blood": fb,
            "vision_score": v_score,
            "played_at": f"2026-10-{(i % 28) + 1:02d} 18:00:00",
        })
        match_counter += 1

    return matches


def generate_matchups() -> List[Dict]:
    """Generate symmetric matchup records for all 60 champions."""
    random.seed(1337)
    matchups = []
    champ_ids = [c[0] for c in CHAMPIONS_RAW]

    # Pre-generate matrix
    n = len(champ_ids)
    for i in range(n):
        for j in range(i + 1, n):
            c_a = champ_ids[i]
            c_b = champ_ids[j]

            # Winrate between 0.40 and 0.60
            wr_a = round(0.50 + random.uniform(-0.12, 0.12), 2)
            wr_b = round(1.0 - wr_a, 2)

            # Synergy between -0.20 and +0.30 (symmetric)
            syn = round(random.uniform(-0.10, 0.25), 2)

            # Counter advantage between -0.30 and +0.30 (anti-symmetric)
            cnt_a = round(random.uniform(-0.25, 0.25), 2)
            cnt_b = round(-cnt_a, 2)

            matchups.append({
                "champion_a": c_a,
                "champion_b": c_b,
                "winrate": wr_a,
                "synergy": syn,
                "counter": cnt_a,
            })
            matchups.append({
                "champion_a": c_b,
                "champion_b": c_a,
                "winrate": wr_b,
                "synergy": syn,
                "counter": cnt_b,
            })

    return matchups


def seed_database() -> Dict[str, int]:
    init_db()
    conn = get_connection()

    teams = TEAMS_DATA
    players = generate_players(teams)
    matches = generate_matches(teams)
    matchups = generate_matchups()

    with conn:
        # 1. Teams
        for t in teams:
            conn.execute("""
            INSERT OR REPLACE INTO teams (
                id, name, region, style, win_rate, avg_game_minutes,
                objective_rates, first_blood_rate, avg_vision_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                t["id"], t["name"], t["region"], t["style"], t["win_rate"],
                t["avg_game_minutes"], json.dumps(t["objective_rates"]),
                t["first_blood_rate"], t["avg_vision_score"]
            ))

        # 2. Champions
        for c in CHAMPIONS_RAW:
            conn.execute("""
            INSERT OR REPLACE INTO champions (
                id, name, title, role, win_rate, pick_rate, ban_rate, avatar_color
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, c)

        # 3. Players
        for p in players:
            conn.execute("""
            INSERT OR REPLACE INTO players (
                id, team_id, name, role, kda, champion_pool, recent_form
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                p["id"], p["team_id"], p["name"], p["role"], p["kda"],
                json.dumps(p["champion_pool"]), p["recent_form"]
            ))

        # 4. Matches
        for m in matches:
            conn.execute("""
            INSERT OR REPLACE INTO matches (
                id, team_id, opponent_id, result, duration_minutes,
                gold_diff_curve, objectives, first_blood, vision_score, played_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                m["id"], m["team_id"], m["opponent_id"], m["result"],
                m["duration_minutes"], json.dumps(m["gold_diff_curve"]),
                json.dumps(m["objectives"]), m["first_blood"], m["vision_score"],
                m["played_at"]
            ))

        # 5. Matchups
        for mu in matchups:
            conn.execute("""
            INSERT OR REPLACE INTO matchups (
                champion_a, champion_b, winrate, synergy, counter
            ) VALUES (?, ?, ?, ?, ?)
            """, (
                mu["champion_a"], mu["champion_b"], mu["winrate"], mu["synergy"], mu["counter"]
            ))

    # Verify counts
    cur = conn.cursor()
    team_count = cur.execute("SELECT COUNT(*) FROM teams").fetchone()[0]
    player_count = cur.execute("SELECT COUNT(*) FROM players").fetchone()[0]
    champ_count = cur.execute("SELECT COUNT(*) FROM champions").fetchone()[0]
    match_count = cur.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    matchup_count = cur.execute("SELECT COUNT(*) FROM matchups").fetchone()[0]
    conn.close()

    result = {
        "teams": team_count,
        "players": player_count,
        "champions": champ_count,
        "matches": match_count,
        "matchups": matchup_count,
    }
    print(f"[Seed] Successfully seeded: {result}")
    return result


if __name__ == "__main__":
    seed_database()
