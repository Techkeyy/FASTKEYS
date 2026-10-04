"""Read-only deployment evidence; public HTTP cannot prove a Render build SHA."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import requests

url = "https://fastkeys.onrender.com"
result = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "url": url}
for name, route in (("health", "/api/health"), ("frontend", "/")):
    response = requests.get(url + route, timeout=60)
    result[name] = {"http_status": response.status_code}
    if name == "health":
        result[name]["body"] = response.json()
    else:
        baseline = subprocess.check_output(
            ["git", "show", "04f1c2fc1b7f95aae752cc38efe52ebea8202bb2:web/index.html"]
        )
        normalize = lambda content: content.replace(b"\r\n", b"\n").strip()
        result[name]["sha256"] = hashlib.sha256(response.content).hexdigest()
        result[name]["matches_baseline_html"] = normalize(response.content) == normalize(baseline)
        result[name]["contains_rebuild_heading"] = "Hear it." in response.text
result["local_head"] = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
result["render_dashboard"] = "Not inspected; HTTP health does not identify Render deployment ID or build SHA."
Path("evidence/deployment-proof.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
