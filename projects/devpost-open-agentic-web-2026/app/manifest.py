"""Manifest generation conforming to Open Agentic Web specification and external discovery."""

import json
import urllib.parse
import urllib.request
from typing import Any, Dict, List
from app.models import Agent


def generate_agent_network_manifest(agents: List[Agent], base_url: str = "") -> Dict[str, Any]:
    """Generate Open Agentic Web compliant manifest at /.well-known/agent-network.json."""
    agent_manifests = []
    for a in agents:
        ep = a.endpoint
        if base_url and ep.startswith("/"):
            ep = f"{base_url.rstrip('/')}{ep}"
        agent_manifests.append(
            {
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "capabilities": a.capabilities,
                "endpoint": ep,
                "trust_score": a.trust_score,
                "price_range": a.price_range,
                "hours": a.hours,
                "verification": {
                    "verifiable_score": a.trust_breakdown.verifiable,
                    "success_rate_score": a.trust_breakdown.success_rate,
                    "latency_score": a.trust_breakdown.latency,
                },
            }
        )

    return {
        "network": "agentbazaar",
        "version": "0.1",
        "name": "AgentBazaar Open Registry",
        "description": "Open Agentic Web directory and trust registry for merchant and autonomous agents",
        "protocol": "open-agentic-web",
        "protocol_version": "0.1.0",
        "agents": agent_manifests,
    }


def fetch_and_discover(url: str) -> Dict[str, Any]:
    """Fetch and parse external site's agent-network.json manifest."""
    raw_url = url.strip()
    if not raw_url.startswith(("http://", "https://")):
        raw_url = f"http://{raw_url}"

    parsed = urllib.parse.urlparse(raw_url)
    # If path doesn't point to a json file, append /.well-known/agent-network.json
    if not parsed.path or parsed.path == "/":
        target_url = f"{parsed.scheme}://{parsed.netloc}/.well-known/agent-network.json"
    else:
        target_url = raw_url

    req = urllib.request.Request(
        target_url,
        headers={
            "User-Agent": "AgentBazaar-Crawler/0.1.0 (+https://github.com/agentbazaar)",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status != 200:
                return {
                    "ok": False,
                    "url": target_url,
                    "error": f"HTTP status {response.status}: {response.reason}",
                }
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read().decode(charset)
            data = json.loads(body)

            # Validate basic manifest structure
            agents = data.get("agents", [])
            network = data.get("network", "unknown")
            return {
                "ok": True,
                "url": target_url,
                "network": network,
                "version": data.get("version", "0.1"),
                "name": data.get("name", "External Agentic Site"),
                "description": data.get("description", ""),
                "agents_count": len(agents),
                "agents": agents,
            }
    except Exception as e:
        return {
            "ok": False,
            "url": target_url,
            "error": f"Failed to discover manifest: {str(e)}",
        }
