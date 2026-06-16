# Replication package — LLM-agent fleet reliability

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20712413.svg)](https://doi.org/10.5281/zenodo.20712413)

Replication artifacts for the paper:

> **Backend and Composition Faults in an Unattended LLM-Agent System: A Fault-Injection Study and Field Log** (ReSAISE 2026, 4th IEEE Workshop on Reliable and Secure AI for Software Engineering, co-located with ISSRE 2026).

Release tag: `v1.0`. Archived at Zenodo: **DOI [10.5281/zenodo.20712413](https://doi.org/10.5281/zenodo.20712413)** (concept DOI, resolves to latest).

## What's here

| File | What it is | Runnable here? |
|---|---|---|
| `standalone_demo.py` | Self-contained reproduction of the three measured deltas; also shows the exact ablation logic of each guard. | **Yes** — `python3 standalone_demo.py` |
| `mine_logs.py` | The retrospective log classifier that produced `retrospective.json`. Point its `LOGS` list at your own logs. | Needs operator logs (private) |
| `results.json` | Fault-injection outputs (Table 3 in the paper). | — |
| `retrospective.json` | Incident counts by class and date (Section V-D, Fig. 4). **Snippet text and full paths redacted**; counts/classes/dates are unchanged. | — |

## Reproducing the headline result

```
python3 standalone_demo.py
```

Expected output:

```
Pattern A  fallback   : patterned 4/4  vs  ablated 0/4
Pattern B  isolation  : blast radius 1 agent  vs  6 agents (of 6)
Pattern C  loader     : patterned 3/3  vs  ablated 0/3
OK: reproduces the paper's deltas (Table 3).
```

This is a **mechanism reproduction**: the numbers match because the patterns are
deterministic. It lets anyone verify the logic of each guard and its ablation
without the private testbed.

## On the private testbed (honesty note)

The paper's measured A and C legs ran against a production subsystem — a
daily-report agent plus an agent registry — that is **not redistributable**
because it processes personal data and would disclose the operator's domain.
`results.json` is that subsystem's output. The B (isolation) leg is a faithful
re-implementation of the registry loop, which the paper flags as a mechanism
demonstration rather than a measurement (Table 2). `standalone_demo.py`
implements the same three guards and their ablations on clean, self-contained
stand-ins, reproduces all three deltas, and is the inspectable, runnable form of
the measurement logic.

The retrospective logs themselves are operator-private and are not included;
`retrospective.json` carries the redacted incident records (class, date, source
basename) that the paper's counts are computed from. The Telegram `409`
duplicate-consumer incident discussed as Pattern C's motivation predates this
log window and is not present in these artifacts, as the paper states.

## License

MIT — see `LICENSE`.
