#!/usr/bin/env python3
"""Self-contained mechanism reproduction for the ReSAISE 2026 paper
"Backend and Composition Faults in an Unattended LLM-Agent System."

This script reproduces the three measured deltas from the paper on minimal,
self-contained implementations of the three patterns, with no external
dependency. It is a *mechanism reproduction*: the numbers match the paper
because the patterns are deterministic. The paper's headline figures
(results.json) were produced by fault_injection_harness.py against a private
production subsystem (a daily-report agent + the OpenClaw agent registry) that
is not redistributable because it contains personal data; for the A and C legs
that harness imports the real production functions, whereas this demo uses
faithful local stand-ins so anyone can run it. See README.md.

Run:  python3 standalone_demo.py
Expect: A 4/4 vs 0/4 ; B blast radius 1 vs 6 ; C 3/3 vs 0/3
"""
import json, subprocess, tempfile, os

# ---------------------------------------------------------------- Pattern A
# A task whose result can come from the model or, on failure, from data.
def task_with_fallback(backend):
    """Real-shape agent: try the backend, fall back to a data-only answer."""
    try:
        out = backend()
        if not (out and out.strip()):
            raise ValueError("empty")
        return out
    except Exception:
        return "[degraded] data-only answer"          # always returns something

def task_no_fallback(backend):
    """Ablated: no fallback path; a backend failure yields nothing/raises."""
    return backend()

def fault(kind):
    def run():
        if kind == "timeout":   raise subprocess.TimeoutExpired(["x"], 1)
        if kind == "nonzero":   raise subprocess.CalledProcessError(1, ["x"])
        if kind == "empty":     return ""
        if kind == "notfound":  raise FileNotFoundError("x")
    return run

def leg_A():
    faults = ["timeout", "nonzero", "empty", "notfound"]
    patt = abl = 0
    for k in faults:
        if (task_with_fallback(fault(k)) or "").strip(): patt += 1
        try:
            if (task_no_fallback(fault(k)) or "").strip(): abl += 1
        except Exception:
            pass
    return patt, abl, len(faults)

# ---------------------------------------------------------------- Pattern B
def registry_patterned(agents):
    out = []
    for i, a in enumerate(agents):
        try: out.append(a(i))
        except Exception: out.append("")        # isolated
    return out

def registry_ablated(agents):
    return [a(i) for i, a in enumerate(agents)]  # one raise aborts all

def leg_B(n=6):
    agents = [lambda i: f"ok-{i}"] * n
    agents[2] = lambda i: (_ for _ in ()).throw(ValueError("boom"))
    patt = sum(1 for s in registry_patterned(agents) if s)
    try:
        abl = sum(1 for s in registry_ablated(agents) if s)
    except Exception:
        abl = 0
    return n - patt, n - abl, n          # blast radius = agents lost

# ---------------------------------------------------------------- Pattern C
def build_patterned(path):
    try:
        with open(path) as fh: data = json.load(fh)
    except Exception:
        data = {"items": []}                  # defensive: degrade, keep building
    return "REPORT(" + str(len(data.get("items", []))) + ")"

def build_ablated(path):
    with open(path) as fh: data = json.load(fh)   # raw load: throws on corrupt
    return "REPORT(" + str(len(data.get("items", []))) + ")"

def leg_C(trials=3):
    patt = abl = 0
    for _ in range(trials):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "src.json")
        open(p, "w").write("{ not valid json ]")
        try:
            if build_patterned(p): patt += 1
        except Exception:
            pass
        try:
            if build_ablated(p): abl += 1
        except Exception:
            pass
    return patt, abl, trials

if __name__ == "__main__":
    a_p, a_a, a_n = leg_A()
    b_p, b_a, b_n = leg_B()
    c_p, c_a, c_n = leg_C()
    print("Pattern A  fallback   : patterned %d/%d  vs  ablated %d/%d" % (a_p, a_n, a_a, a_n))
    print("Pattern B  isolation  : blast radius %d agent  vs  %d agents (of %d)" % (b_p, b_a, b_n))
    print("Pattern C  loader     : patterned %d/%d  vs  ablated %d/%d" % (c_p, c_n, c_a, c_n))
    assert (a_p, a_a) == (4, 0) and (b_p, b_a) == (1, 6) and (c_p, c_a) == (3, 0)
    print("\nOK: reproduces the paper's deltas (Table 3).")
