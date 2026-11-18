# DraftLens

DraftLens is a macro scouting and fearless draft management platform designed for competitive tactical gaming teams. It provides match analytics, objective control reporting, gold difference curves, and a deterministic draft simulation board supporting multi-game Fearless Draft rules.

## Features
- **Team & Player Roster**: Comprehensive database of competitive teams, player stats, and champion performance.
- **Macro Scouting**: Automated scouting reports calculating objective control rates (dragon, herald, baron), vision scores, first blood percentage, and 15-minute gold differential.
- **Fearless Draft Simulator**: Turn-based draft board enforcing global Fearless Draft rules (previously picked champions are locked across games in a series).
- **Recommendation Engine**: Heuristic scoring engine evaluating counter picks, role synergies, win rates, and player proficiency.
- **Zero Paid APIs**: Fully self-contained local SQLite database with rich synthetic benchmark data.

## JetBrains AI Workflow
Developed with JetBrains tooling and structured AI workflows:
- Backend services developed with PyCharm.
- Frontend interface and visual canvas graphs designed with WebStorm.
- Multi-agent orchestration simulating parallel development streams.

## Quick Start

### Installation
```bash
pip install -r requirements.txt
```

### Database Initialization
```bash
python3 -m app.seed
```

### Start Server
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```
Open your browser at `http://localhost:8000`.

## Testing
```bash
python3 -m unittest discover -s tests -v
```
