# DraftLens — LoL Macro Scouting & Fearless Draft Management System

DraftLens is a high-performance macro scouting and Fearless Draft workbench tailored for competitive League of Legends coaches, analysts, and esports teams. It unifies pre-match scouting, objective control profiling, gold differential analysis, and turn-based draft simulations with strict multi-game Fearless Draft rule enforcement.

## System Highlights

1. **Zero External API Dependency**: Entirely self-contained with a local SQLite database, pre-seeded with 8 competitive teams, 40 players across 5 standard roles, 60 champions with role assignments, and 120 historic match records.
2. **Deterministic Heuristic Recommendation Engine**: Evaluates matchups locally using weighted formula:
   $$\text{Score} = w_1 \cdot \text{WinRate} + w_2 \cdot \text{Synergy} + w_3 \cdot \text{Counter} + w_4 \cdot \text{PlayerComfort}$$
   Returns Top 3 recommendations with clear contextual explanations in Chinese.
3. **Strict Global Fearless Draft Enforcement**: Champions picked in earlier games of a series are globally locked from selection in subsequent games, validated directly by backend state transitions.
4. **Interactive Single-Page Interface**: Clean esports dark theme with responsive navigation, interactive HTML5 Canvas gold difference graphs, and real-time turn tracking.
5. **GRID Data Ready**: Pre-configured status endpoint (`GET /api/grid/status`) prepared for optional official esports telemetry feeds.

---

## JetBrains Development Workflow

Built following an AI-assisted JetBrains toolchain:
- **PyCharm**: Used for backend REST API architecture, SQLite database schema design, and unit test suites.
- **WebStorm**: Used for single-page application structure, CSS design system, and HTML5 Canvas curve rendering.
- **AI Agent Orchestration**: Multi-phase design and testing automated with local verification loops.

---

## Quick Start

### 1. Requirements
- Python 3.10+ (tested on Python 3.11 & 3.14)
- FastAPI, Uvicorn, Pydantic, HTTPX

```bash
pip install -r requirements.txt
```

### 2. Seed Database
Initialize and seed the local SQLite database (`data/draftlens.db`):
```bash
python3 -m app.seed
```

### 3. Start Application
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Open your browser at `http://localhost:8000`.

---

## API Quick Reference & Curl Examples

### 1. Health Check
```bash
curl -s http://127.0.0.1:8000/api/health
# {"status": "ok"}
```

### 2. List Teams by Style
```bash
curl -s "http://127.0.0.1:8000/api/teams?style=early-aggression"
```

### 3. Generate Macro Scouting Report
```bash
curl -s "http://127.0.0.1:8000/api/scout/t01?matches=5"
```
Response includes objective control percentages, vision scores, gold difference at 15 minutes, gold difference curve points, and rule-generated tactical summary.

### 4. Create Fearless Draft Session (BO3)
```bash
curl -s -X POST http://127.0.0.1:8000/api/draft \
  -H "Content-Type: application/json" \
  -d '{"blue_team_id": "t01", "red_team_id": "t02", "series_type": "BO3"}'
```

### 5. Execute Ban / Pick
```bash
# Blue side Turn 0 Ban
curl -s -X POST http://127.0.0.1:8000/api/draft/<DRAFT_ID>/ban \
  -H "Content-Type: application/json" \
  -d '{"champion_id": "c001", "side": "blue"}'
```

### 6. Query Heuristic Recommendations
```bash
curl -s -X POST http://127.0.0.1:8000/api/draft/<DRAFT_ID>/recommend
```

### 7. Advance to Next Game (Series Progression)
```bash
curl -s -X POST http://127.0.0.1:8000/api/draft/<DRAFT_ID>/next-game \
  -H "Content-Type: application/json" \
  -d '{"winner": "blue"}'
```

---

## Automated Test Suite

Run full automated tests:
```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```
All 16 unit tests verify entity counts, matrix symmetry, API contracts, 400 rejection on Fearless Draft duplicate picks, and responsive static asset delivery.
