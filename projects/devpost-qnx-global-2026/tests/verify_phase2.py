import os
import sys

proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, proj_root)

from fastapi.testclient import TestClient
from main import app

def test_phase2_frontend_assets():
    client = TestClient(app)

    # 1. Test root / returns index.html
    res = client.get("/")
    assert res.status_code == 200, f"Root / failed: {res.status_code}"
    assert "TraceLens" in res.text
    assert "QNX 8.0" in res.text
    print("[PASS] 1. Root / successfully serves TraceLens HTML")

    # 2. Test static assets
    for asset in ["/static/css/style.css", "/static/js/api.js", "/static/js/timeline_canvas.js", "/static/js/app.js"]:
        res = client.get(asset)
        assert res.status_code == 200, f"Static asset {asset} failed with {res.status_code}"
        assert len(res.text) > 50
        print(f"[PASS] 2. Asset {asset} loaded ({len(res.text)} bytes)")

    # 3. Test static index.html has all 5 view sections
    for view in ["view-overview", "view-timeline", "view-stats", "view-anomalies", "view-reference"]:
        assert f'id="{view}"' in res.text or f'id="{view}"' in client.get("/").text, f"Missing view section: {view}"
    print("[PASS] 3. All 5 SPA view sections present in HTML DOM")

    # 4. Test modals and canvas presence
    index_html = client.get("/").text
    assert 'id="timelineCanvas"' in index_html
    assert 'id="modalGenerate"' in index_html
    assert 'id="modalUpload"' in index_html
    print("[PASS] 4. Canvas element and Generate/Upload modals verified")

    print("\n>>> ALL PHASE 2 FRONTEND ASSET CHECKS PASSED! <<<")

if __name__ == "__main__":
    test_phase2_frontend_assets()
