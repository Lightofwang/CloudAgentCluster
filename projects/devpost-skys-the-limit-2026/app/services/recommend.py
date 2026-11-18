"""Draft Recommendation Engine (Heuristic-based, zero external API)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from app.db import get_connection, row_to_dict
from app.services.draft import DRAFT_TURNS


def get_recommendations(draft_id: str) -> Dict[str, Any]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Draft session '{draft_id}' not found")
        data = row_to_dict(row)

        turn_idx = data["current_turn_index"]
        if turn_idx >= len(DRAFT_TURNS):
            return {"recommendations": []}

        curr_turn = DRAFT_TURNS[turn_idx]
        current_side = curr_turn["side"]
        current_action = curr_turn["action"]
        current_team_id = data["blue_team_id"] if current_side == "blue" else data["red_team_id"]

        # Gather excluded champions:
        # 1. Global fearless locked (if action is pick)
        series_picked = set(data.get("series_picked_champions", []))

        # 2. Currently picked/banned in this game
        games = data.get("games", [])
        curr_game = games[-1] if games else {"blue_bans": [], "red_bans": [], "blue_picks": [], "red_picks": []}

        all_current = (
            curr_game.get("blue_bans", []) +
            curr_game.get("red_bans", []) +
            curr_game.get("blue_picks", []) +
            curr_game.get("red_picks", [])
        )
        current_used_cids = {c["champion_id"] for c in all_current}

        excluded_cids = current_used_cids.copy()
        if current_action == "pick":
            excluded_cids.update(series_picked)

        # Existing allied and enemy picks in current game
        allied_picks = curr_game.get("blue_picks" if current_side == "blue" else "red_picks", [])
        enemy_picks = curr_game.get("red_picks" if current_side == "blue" else "blue_picks", [])

        allied_cids = [c["champion_id"] for c in allied_picks]
        enemy_cids = [c["champion_id"] for c in enemy_picks]

        # Fetch player champion comforts for this team
        cur.execute("SELECT role, champion_pool FROM players WHERE team_id = ?", (current_team_id,))
        player_comforts: Dict[str, float] = {}
        for r_role, r_pool in cur.fetchall():
            pool_list = json.loads(r_pool) if isinstance(r_pool, str) else r_pool
            for entry in pool_list:
                cid = entry.get("champion_id")
                player_comforts[cid] = entry.get("comfort", 0.6)

        # Fetch all champions
        cur.execute("SELECT id, name, title, role, win_rate, pick_rate, ban_rate FROM champions")
        champs = [dict(c) for c in cur.fetchall()]

        # Filter out excluded champions
        candidate_champs = [c for c in champs if c["id"] not in excluded_cids]

        # Fetch matchup table for candidates
        cur.execute("SELECT champion_a, champion_b, winrate, synergy, counter FROM matchups")
        matchup_rows = cur.fetchall()
        matchup_map: Dict[tuple, tuple] = {}
        for ma in matchup_rows:
            matchup_map[(ma[0], ma[1])] = (ma[2], ma[3], ma[4])

        scored_candidates = []
        w1, w2, w3, w4 = 0.35, 0.25, 0.25, 0.15

        for c in candidate_champs:
            cid = c["id"]
            base_wr = c["win_rate"]

            # Calculate synergy with existing allied picks
            syn_scores = []
            syn_reasons = []
            for ally_cid in allied_cids:
                if (cid, ally_cid) in matchup_map:
                    _, syn, _ = matchup_map[(cid, ally_cid)]
                    syn_scores.append(syn)
                    if syn > 0.05:
                        ally_name = next((p["champion_name"] for p in allied_picks if p["champion_id"] == ally_cid), ally_cid)
                        syn_reasons.append(f"与已选{ally_name}协同 +{syn:.2f}")

            avg_syn = sum(syn_scores) / len(syn_scores) if syn_scores else 0.0

            # Calculate counter advantage against enemy picks
            cnt_scores = []
            cnt_reasons = []
            wr_vs_enemies = []
            for enemy_cid in enemy_cids:
                if (cid, enemy_cid) in matchup_map:
                    wr, _, cnt = matchup_map[(cid, enemy_cid)]
                    wr_vs_enemies.append(wr)
                    cnt_scores.append(cnt)
                    if cnt > 0.05:
                        enemy_name = next((p["champion_name"] for p in enemy_picks if p["champion_id"] == enemy_cid), enemy_cid)
                        cnt_reasons.append(f"对阵{enemy_name}对线克制 +{cnt:.2f}")

            avg_cnt = sum(cnt_scores) / len(cnt_scores) if cnt_scores else 0.0
            avg_wr_vs_enemy = sum(wr_vs_enemies) / len(wr_vs_enemies) if wr_vs_enemies else base_wr

            comfort = player_comforts.get(cid, 0.60)

            # Heuristic score calculation
            # Normalize components to roughly [0, 1]
            # base_wr is around 0.50
            # syn is around -0.1 to +0.25 -> (syn + 0.1) / 0.35
            # cnt is around -0.25 to +0.25 -> (cnt + 0.25) / 0.5
            norm_syn = max(0.0, min(1.0, (avg_syn + 0.15) / 0.45))
            norm_cnt = max(0.0, min(1.0, (avg_cnt + 0.25) / 0.50))
            norm_wr = avg_wr_vs_enemy

            total_score = round(
                norm_wr * w1 + norm_syn * w2 + norm_cnt * w3 + comfort * w4,
                2
            )

            # Compile explanation reasons
            reasons = []
            reasons.append(f"对阵胜率 {int(avg_wr_vs_enemy * 100)}%")
            if syn_reasons:
                reasons.append(syn_reasons[0])
            elif avg_syn > 0:
                reasons.append(f"阵容体系协同 +{avg_syn:.2f}")

            if cnt_reasons:
                reasons.append(cnt_reasons[0])
            elif comfort >= 0.80:
                reasons.append("选手熟练度极高")
            elif comfort >= 0.70:
                reasons.append("选手招牌绝活英雄")
            else:
                reasons.append("符合当前版本战术节奏")

            scored_candidates.append({
                "champion_id": cid,
                "champion_name": c["name"],
                "role": c["role"],
                "score": total_score,
                "reasons": reasons[:3],
            })

        # Sort strictly descending by score
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        top3 = scored_candidates[:3]

        return {
            "draft_id": draft_id,
            "turn_index": turn_idx,
            "side": current_side,
            "action": current_action,
            "recommendations": top3,
        }
    finally:
        conn.close()
