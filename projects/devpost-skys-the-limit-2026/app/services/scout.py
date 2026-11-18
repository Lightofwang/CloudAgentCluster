"""Macro Scouting Analysis Service."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from app.db import get_connection, row_to_dict


def generate_scout_report(team_id: str, matches_requested: int = 5) -> Dict[str, Any]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Verify team
        cur.execute("SELECT * FROM teams WHERE id = ?", (team_id,))
        team_row = cur.fetchone()
        if not team_row:
            return None

        team = row_to_dict(team_row)

        # Fetch recent matches for this team
        cur.execute(
            """
            SELECT * FROM matches
            WHERE team_id = ? OR opponent_id = ?
            ORDER BY played_at DESC
            LIMIT ?
            """,
            (team_id, team_id, matches_requested),
        )
        matches = [row_to_dict(m) for m in cur.fetchall()]
        analyzed_count = len(matches)

        if analyzed_count == 0:
            # Fallback to team baseline stats
            obj_rates = team.get("objective_rates", {"dragon": 0.5, "herald": 0.5, "baron": 0.5})
            return {
                "team_id": team_id,
                "team_name": team["name"],
                "matches_analyzed": 0,
                "matches_requested": matches_requested,
                "warning": "No match records found; returning baseline stats.",
                "objective_rates": obj_rates,
                "avg_vision_score": team["avg_vision_score"],
                "first_blood_rate": team["first_blood_rate"],
                "gold_diff_at_15": 0,
                "style_summary": f"基础战队风格：{team['style']}",
                "champion_preferences": [],
                "gold_diff_curve": [],
                "recent_matches": [],
            }

        # Calculate statistics across analyzed matches
        total_dragons = 0
        total_barons = 0
        total_heralds = 0
        total_fb = 0
        total_vision = 0.0
        gold_diff_15_list = []

        minute_diffs: Dict[int, List[int]] = {5: [], 10: [], 15: [], 20: [], 25: [], 30: []}

        for m in matches:
            is_main_team = (m["team_id"] == team_id)
            objs = m.get("objectives", {})
            dragons = objs.get("dragons", 0)
            barons = objs.get("barons", 0)
            heralds = objs.get("heralds", 0)

            # Invert perspective if team was the opponent
            if not is_main_team:
                # If opponent won, main team lost
                team_won = (m["result"] == "loss")
                team_fb = 1 - m.get("first_blood", 0)
                # Approximate objective share
                team_dragons = max(0, 4 - dragons) if team_won else min(1, dragons)
                team_barons = 1 if team_won and barons == 0 else 0
                team_heralds = 1 if team_won and heralds == 0 else 0
                team_vision = round(150.0 - m.get("vision_score", 75.0), 1)
            else:
                team_fb = m.get("first_blood", 0)
                team_dragons = dragons
                team_barons = barons
                team_heralds = heralds
                team_vision = m.get("vision_score", 75.0)

            total_dragons += team_dragons
            total_barons += team_barons
            total_heralds += team_heralds
            total_fb += team_fb
            total_vision += team_vision

            curve = m.get("gold_diff_curve", [])
            for pt in curve:
                m_num = pt.get("minute")
                diff = pt.get("diff", 0)
                if not is_main_team:
                    diff = -diff
                if m_num in minute_diffs:
                    minute_diffs[m_num].append(diff)
                if m_num == 15:
                    gold_diff_15_list.append(diff)

        avg_dragons_rate = round(min(1.0, total_dragons / (analyzed_count * 3.5)), 2)
        avg_baron_rate = round(min(1.0, total_barons / (analyzed_count * 1.5)), 2)
        avg_herald_rate = round(min(1.0, total_heralds / (analyzed_count * 1.5)), 2)
        avg_vision = round(total_vision / analyzed_count, 1)
        fb_rate = round(total_fb / analyzed_count, 2)
        avg_gold_15 = int(sum(gold_diff_15_list) / len(gold_diff_15_list)) if gold_diff_15_list else 0

        # Build aggregated gold diff curve
        avg_curve = []
        for m_num in sorted(minute_diffs.keys()):
            diffs = minute_diffs[m_num]
            if diffs:
                avg_curve.append({
                    "minute": m_num,
                    "diff": int(sum(diffs) / len(diffs)),
                })

        # Fetch champion preferences from player champion pools
        cur.execute("SELECT champion_pool FROM players WHERE team_id = ?", (team_id,))
        player_rows = cur.fetchall()
        champ_counts: Dict[str, float] = {}
        for pr in player_rows:
            pool = json.loads(pr[0]) if isinstance(pr[0], str) else pr[0]
            for c_entry in pool:
                cid = c_entry.get("champion_id")
                comfort = c_entry.get("comfort", 0.5)
                champ_counts[cid] = champ_counts.get(cid, 0.0) + comfort

        # Lookup champion names
        cur.execute("SELECT id, name, role FROM champions")
        all_champs = {r[0]: (r[1], r[2]) for r in cur.fetchall()}

        sorted_champs = sorted(champ_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        champion_preferences = [
            {
                "champion_id": cid,
                "champion": all_champs.get(cid, (cid, ""))[0],
                "role": all_champs.get(cid, (cid, ""))[1],
                "pick_rate": round(min(0.95, score / 4.0), 2),
            }
            for cid, score in sorted_champs
        ]

        # Style summary generated via rule template
        if avg_gold_15 >= 600:
            style_str = f"前期进攻型：15 分钟平均领先 {avg_gold_15} 经济，一血率 {int(fb_rate*100)}%，优先控小龙与先锋推进"
        elif avg_gold_15 <= -300:
            style_str = f"防守反击型：15 分钟平均落后 {abs(avg_gold_15)} 经济，后期大龙控制率 {int(avg_baron_rate*100)}%，重心在 25 分钟后阵地团战"
        else:
            style_str = f"均衡运营型：15 分钟经济差距平稳（{avg_gold_15:+d}），平均视野分 {avg_vision}，擅长资源拉扯与兵线调配"

        result = {
            "team_id": team_id,
            "team_name": team["name"],
            "matches_analyzed": analyzed_count,
            "matches_requested": matches_requested,
            "objective_rates": {
                "dragon": avg_dragons_rate,
                "herald": avg_herald_rate,
                "baron": avg_baron_rate,
            },
            "avg_vision_score": avg_vision,
            "first_blood_rate": fb_rate,
            "gold_diff_at_15": avg_gold_15,
            "style_summary": style_str,
            "champion_preferences": champion_preferences,
            "gold_diff_curve": avg_curve,
            "recent_matches": matches,
        }
        if analyzed_count < matches_requested:
            result["warning"] = f"matches_analyzed ({analyzed_count}) < requested ({matches_requested})"

        return result
    finally:
        conn.close()
