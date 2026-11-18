# DraftLens — Project Implementation Result

## Overview

- **Project**: DraftLens — LoL Macro Scouting & Fearless Draft Management System
- **Category**: Category 2: LoL Macro Scouting & Draft Management System
- **Entry Slug**: `devpost-skys-the-limit-2026`
- **Tech Stack**: Python 3.11/3.14 + FastAPI + SQLite3 + Vanilla HTML5/CSS3/ES6 (Zero build step)
- **External API Dependencies**: 0 (Fully self-contained local SQLite storage and deterministic heuristic computation)

---

## What Was Built

### 1. Data Layer (`app/db.py`, `app/seed.py`)
- SQLite schema with 6 relational tables: `teams`, `players`, `champions`, `matches`, `matchups`, `drafts`.
- Idempotent seed data generator providing:
  - **8 Fictional Teams**: Across tactical styles (`early-aggression`, `late-macro`, `skirmish`).
  - **40 Players**: 5 players per team mapped to standard roles (`TOP`, `JUG`, `MID`, `ADC`, `SUP`) with comfort champion pools and KDA stats.
  - **60 Champions**: 12 champions per role with balanced win rates, pick rates, and distinct aesthetic palettes.
  - **120 Match Records**: Complete with duration, first blood flags, vision scores, neutral objectives (dragons, barons, heralds, towers), and time-stamped gold differential curves (minutes 5, 10, 15, 20, 25, 30).
  - **3,540 Matchup Pairs**: Mathematical symmetry enforced ($WinRate_{A,B} + WinRate_{B,A} = 1.0$, $Synergy_{A,B} = Synergy_{B,A}$, $Counter_{A,B} = -Counter_{B,A}$).

### 2. REST API Endpoints (`app/routers/`)
- `GET /api/health`: Health status.
- `GET /api/grid/status`: GRID official telemetry readiness status (`mode: sample-data`).
- `GET /api/teams` & `GET /api/teams/{id}`: Roster lookup, style filtering, and match histories.
- `GET /api/players`: Role-based player pool search.
- `GET /api/matches`: Match history with pagination.
- `GET /api/champions`: Champion pool filtering by role.
- `GET /api/scout/{team_id}`: Macro scouting report aggregation.
- `POST /api/draft`: Series creation (`BO1`, `BO3`, `BO5`).
- `GET /api/draft/{id}`: Live session state inspection.
- `POST /api/draft/{id}/ban`: Turn-validated champion ban.
- `POST /api/draft/{id}/pick`: Turn-validated champion pick with Fearless rule enforcement.
- `POST /api/draft/{id}/recommend`: Real-time heuristic candidate scoring.
- `POST /api/draft/{id}/next-game`: Multi-game series advancement and global pool locking.
- `GET /api/draft/{id}/history`: Completed series retrospective.

### 3. Core Business Engines (`app/services/`)
- **Macro Scouting Engine (`app/services/scout.py`)**:
  - Aggregates neutral objective rates (dragon, herald, baron).
  - Computes 15-minute gold differential and builds average gold curve.
  - Generates Chinese tactical style analysis templates based on statistical thresholds.
  - Identifies top 5 signature champion preferences for target opponents.
- **Fearless Draft State Machine (`app/services/draft.py`)**:
  - Full 20-turn competitive draft sequence (10 bans, 10 picks across alternating phases).
  - Enforces turn ownership, action types, and single-game selection exclusivity.
  - Enforces global **Fearless Draft** rule: Any champion selected in earlier games of a series is locked across all future games, returning HTTP 400 (`champion already picked in this series (Fearless Draft)`).
  - Coordinates multi-game series progression (BO3/BO5) and game win tracking.
- **Local Heuristic Recommendation Engine (`app/services/recommend.py`)**:
  - Deterministic evaluation using:
    $$Score = 0.35 \times WinRate + 0.25 \times Synergy + 0.25 \times Counter + 0.15 \times PlayerComfort$$
  - Returns Top 3 candidate champions in descending score order with actionable explanations.
  - Automatically filters out all banned, selected, and Fearless-locked champions.

### 4. Esports Web Interface (`static/`)
- **Esports Dark Theme**: Custom modern dark theme with glowing neon side indicators and responsive navigation.
- **5 Comprehensive Views**:
  1. *Overview*: Macro league metrics and recent match log.
  2. *Teams & Rosters*: Card grid with style filters and detail modal displaying player champion pools and recent form.
  3. *Macro Scouting*: Interactive query panel, objective progress bars, and custom HTML5 Canvas gold difference chart.
  4. *Fearless Draft Simulator*: Interactive Ban/Pick board, real-time turn pulse banner, live champion search/role filter grid, Fearless locked badges, Top 3 recommendation panel, and post-game transition controls.
  5. *Series History*: Review of past series drafts with per-game rosters.
- **Toast Notifications**: Chinese floating toast notifications for user interactions and validation errors.

---

## How to Run

### Installation
```bash
cd projects/devpost-skys-the-limit-2026
pip install -r requirements.txt
```

### Database Initialization
```bash
python3 -m app.seed
```

### Start Server
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Navigate to `http://127.0.0.1:8000` to interact with the full single-page application.

---

## Test Results

### 1. Automated Unit Test Suite
Ran via `python3 -m unittest discover -s tests -p "test_*.py" -v`:

```
test_champions_endpoint (test_api.TestDraftLensAPI.test_champions_endpoint) ... ok
test_draft_session_and_recommendations (test_api.TestDraftLensAPI.test_draft_session_and_recommendations) ... ok
test_fearless_draft_rule_across_games (test_api.TestDraftLensAPI.test_fearless_draft_rule_across_games) ... ok
test_grid_status (test_api.TestDraftLensAPI.test_grid_status) ... ok
test_health_check (test_api.TestDraftLensAPI.test_health_check) ... ok
test_matches_endpoint (test_api.TestDraftLensAPI.test_matches_endpoint) ... ok
test_players_endpoint (test_api.TestDraftLensAPI.test_players_endpoint) ... ok
test_scout_report (test_api.TestDraftLensAPI.test_scout_report) ... ok
test_static_assets (test_api.TestDraftLensAPI.test_static_assets) ... ok
test_team_detail_and_404 (test_api.TestDraftLensAPI.test_team_detail_and_404) ... ok
test_teams_list_and_filter (test_api.TestDraftLensAPI.test_teams_list_and_filter) ... ok
test_champion_role_distribution (test_seed.TestSeedIntegrity.test_champion_role_distribution) ... ok
test_entity_counts (test_seed.TestSeedIntegrity.test_entity_counts) ... ok
test_idempotence (test_seed.TestSeedIntegrity.test_idempotence) ... ok
test_matchup_matrix_symmetry (test_seed.TestSeedIntegrity.test_matchup_matrix_symmetry) ... ok
test_team_roster_composition (test_seed.TestSeedIntegrity.test_team_roster_composition) ... ok

----------------------------------------------------------------------
Ran 16 tests in 0.69s

OK
```

### 2. Performance Verification
Measured over 25 samples on local test runner:
- **Macro Scouting API (`GET /api/scout/t01?matches=5`)**:
  - $p_{50}$: 5.94 ms
  - $p_{95}$: 7.10 ms (Specification requirement: $< 200$ ms)
- **Heuristic Recommendation API (`POST /api/draft/{id}/recommend`)**:
  - $p_{50}$: 11.61 ms
  - $p_{95}$: 14.47 ms (Specification requirement: $< 200$ ms)

### 3. Fearless Rule Compliance
- Validated via `test_fearless_draft_rule_across_games`: Game 1 picks were locked in Game 2. Attempts to pick previously chosen champions triggered immediate HTTP 400 rejection with `{"detail": "champion already picked in this series (Fearless Draft)"}`.
