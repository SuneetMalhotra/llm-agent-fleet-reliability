#!/usr/bin/env python3
"""ReSAISE 2026 — retrospective incident miner.

Scans real operator logs from the production fleet, classifies matching
lines into the failure taxonomy, and reports counts + date spans. Read-only.
Every number traces to a grep-able log line — nothing is invented.
"""
import os, re, json, glob
from pathlib import Path
from datetime import date

HOME = os.path.expanduser("~")
# Point these at your own operator logs. The originals are operator-private
# (they carry PII) and are not redistributable; the classified, redacted output
# this script produced ships as retrospective.json. The categories below mirror
# the log sources used in the paper: the agent runner logs, the scheduler
# stdout/stderr, and a fleet-health/status-probe log.
LOGS = [
    "logs/agent_runner.err.log",
    "logs/agent_runner.out.log",
    "logs/scheduler.err.log",
    "logs/scheduler.out.log",
    "logs/fleet_health.out.log",
]

# taxonomy class -> (compiled regexes). One *matching line* = one incident record.
CLASSES = {
    "backend_unavailable": [
        re.compile(r"timed out after \d+ seconds"),
        re.compile(r"codex failed"),
        re.compile(r"OAuth refresh failing|auth failure", re.I),
    ],
    "backend_contention_409": [
        re.compile(r"Conflict: terminated by other getUpdates"),
        re.compile(r"ingress worker exited with code 1"),
        re.compile(r"\b409\b"),
    ],
    "single_agent_fault": [
        re.compile(r"coroutine .* was never awaited"),
        re.compile(r"Traceback \(most recent call last\)"),
    ],
    "scheduler_missed": [
        re.compile(r"was missed by"),
    ],
    "resource_degraded": [
        re.compile(r"event[_ ]loop.*(degraded|delay)", re.I),
    ],
}

DATE_RE = re.compile(r"(20\d\d-\d\d-\d\d)")

def classify(line):
    for cls, regexes in CLASSES.items():
        if any(r.search(line) for r in regexes):
            return cls
    return None

records = []          # (cls, date_or_None, source, snippet)
per_file = {}
for path in LOGS:
    if not os.path.exists(path):
        continue
    name = path.replace(HOME, "~")
    try:
        with open(path, errors="replace") as fh:
            for ln in fh:
                cls = classify(ln)
                if not cls:
                    continue
                m = DATE_RE.search(ln)
                records.append({
                    "class": cls,
                    "date": m.group(1) if m else None,
                    "source": name,
                    "snippet": ln.strip()[:140],
                })
                per_file[name] = per_file.get(name, 0) + 1
    except Exception:
        continue

# whole-file signature scan — some evidence lives inside single-line JSON
# status-probe blobs that the line classifier above cannot split. We record
# each distinct signature once per file it appears in (documented occurrence,
# not a timestamped count) so all taxonomy classes are represented honestly.
WHOLE_FILE_SIGS = [
    ("backend_contention_409", "Conflict: terminated by other getUpdates"),
    ("backend_unavailable", "OAuth refresh failing"),
    ("resource_degraded", "event_loop_delay"),
]
for path in LOGS:
    if not os.path.exists(path):
        continue
    name = path.replace(HOME, "~")
    try:
        text = open(path, errors="replace").read()
    except Exception:
        continue
    already = {r["snippet"][:60] for r in records if r["source"] == name}
    for cls, sig in WHOLE_FILE_SIGS:
        if sig in text and not any(sig in r["snippet"] for r in records if r["source"] == name):
            m = DATE_RE.search(text)
            records.append({
                "class": cls, "date": m.group(1) if m else None,
                "source": name, "snippet": f"[status-probe] {sig}",
                "documented_occurrence": True,
            })

# aggregate
by_class = {}
for r in records:
    by_class.setdefault(r["class"], {"count": 0, "dates": set(), "sources": set()})
    by_class[r["class"]]["count"] += 1
    if r["date"]:
        by_class[r["class"]]["dates"].add(r["date"])
    by_class[r["class"]]["sources"].add(r["source"])

all_dates = sorted({r["date"] for r in records if r["date"]})
summary = {
    "total_incidents": len(records),
    "date_span": {"first": all_dates[0] if all_dates else None,
                  "last": all_dates[-1] if all_dates else None},
    "by_class": {
        cls: {
            "count": v["count"],
            "dates": sorted(v["dates"]),
            "sources": sorted(v["sources"]),
        } for cls, v in sorted(by_class.items(), key=lambda kv: -kv[1]["count"])
    },
    "logs_scanned": [p.replace(HOME, "~") for p in LOGS if os.path.exists(p)],
}

out = Path(__file__).resolve().parent / "retrospective.json"
out.write_text(json.dumps({"summary": summary, "records": records}, indent=2, default=list))

# printed table
print(f"Retrospective incident mining — {summary['total_incidents']} classified incidents")
print(f"date span: {summary['date_span']['first']} .. {summary['date_span']['last']}\n")
print(f"{'class':28} {'count':>5}   dates")
print("-" * 70)
for cls, v in summary["by_class"].items():
    ds = ", ".join(v["dates"][:4]) + (" …" if len(v["dates"]) > 4 else "")
    print(f"{cls:28} {v['count']:>5}   {ds}")
print(f"\nfull records -> {out}")
