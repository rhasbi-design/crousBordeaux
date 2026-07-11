#!/usr/bin/env python3
import json
import os
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlparse

CROUS_URL = os.environ["CROUS_URL"]
STATE_FILE = Path("state.json")

parsed = urlparse(CROUS_URL)
tool_id = int(parsed.path.strip("/").split("/")[1])
bounds_raw = parse_qs(parsed.query)["bounds"][0]
w, n, e, s = (float(x) for x in bounds_raw.split("_"))

payload = {
    "idTool": tool_id,
    "need_aggregation": True,
    "page": 0,
    "pageSize": 24,
    "sector": None,
    "occupationModes": [],
    "location": [{"lon": w, "lat": n}, {"lon": e, "lat": s}],
    "residence": None,
    "equipment": [],
    "price": {"max": 100000},
    "area": {"min": 0},
    "adaptedPmr": False,
}

req = urllib.request.Request(
    f"https://trouverunlogement.lescrous.fr/api/fr/search/{tool_id}",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.load(resp)

results = data.get("results", {})
total = results.get("total", {}).get("value", 0)
items = [
    {
        "id": it.get("id"),
        "address": it.get("residence", {}).get("address"),
        "rent": it.get("rent", {}).get("amount"),
        "bedroomCount": it.get("bedroomCount"),
    }
    for it in results.get("items", [])
]

previous_total = None
if STATE_FILE.exists():
    previous_total = json.loads(STATE_FILE.read_text()).get("total")

changed = previous_total is not None and previous_total != total
STATE_FILE.write_text(json.dumps({"total": total, "items": items}, indent=2, ensure_ascii=False))

print(f"previous={previous_total} current={total} changed={changed}")

gh_output = os.environ.get("GITHUB_OUTPUT")
if gh_output:
    with open(gh_output, "a") as f:
        f.write(f"changed={'true' if changed else 'false'}\n")
        f.write(f"previous={previous_total if previous_total is not None else 'none'}\n")
        f.write(f"total={total}\n")
        summary_lines = [f"- {it['address']} ({it['bedroomCount']} lit(s), {it['rent']}€)" for it in items]
        summary = "\n".join(summary_lines) if summary_lines else "(no listings)"
        f.write("items<<EOF\n" + summary + "\nEOF\n")

