# Unfire Approval Gates — SocioVerse Challenge 2026 / Track C

**Entrant:** Omar Baró · Unfire Research · Independent developer, Spain
**Status:** Reproducible *synthetic* study implemented with SocioVerse2 Core providers. **Not submitted to the competition portal.**

## Research question
How do deterministic human-review proxies with finite capacity trade off unsafe agent actions, false denials and service delays?

## Population, Environment, Behavior (P/E/B)
- **Population:** 100 immutable synthetic requests per seed (11, 29, 47, 83, 101), with simulated risk, evidence completeness, forbidden-action marker and standard/urgent priority.
- **Environment:** 12 arrival time steps, deadlines, bounded reviewer capacity, traceable terminal decisions. SocioVerse2 runs for 18 steps to cover expirations.
- **Behavior:** (1) ungated execution, (2) static risk threshold, (3) scripted capacity-limited reviewer. No real reviewer or live model is used.
- **Native adapter:** socioverse PopulationProvider, EnvironmentProvider, DecisionModel and MetricCollector in native_model.py; registered provider refs are captured in schema-validated study/environment/population/simulation files.

## Reproduction (Python >=3.11)
At the root of the official SocioVerse2 repository, install package with `python3.12 -m venv .venv && .venv/bin/python -m pip install -e .`; place this folder under `studies/unfire_approval_gates`, then:

    .venv/bin/python -m studies.unfire_approval_gates.run_native

This reproduces 20 native runs: 5 seeds × (ungated, static, capacity_review at capacity 2 and 8). Each run writes a DuckDB trajectory in `trajectory/native` and the JSON index `native_summary.json`.

Independent standard-library verification:

    cd studies/unfire_approval_gates
    python3 -m unittest discover -s tests -v
    python3 run.py --review-capacity 8
    python3 run.py --review-capacity 2 --out trajectory/capacity2

These write paired-run CSV, summary JSON and SHA-256 integrity metadata. No key, API subscription or third-party model is needed.

## Outcomes measured
Unsafe action rate among executed tasks; completion among oracle-safe tasks; false denials; missed review deadlines; mean latency; differences between purely synthetic priority groups.

## What these results do NOT show
- No real human participants; the simulated reviewer acts according to a deterministic synthetic oracle, and safe behavior is substantially built into the rules.
- No proof of true-world safety, fairness, productivity gains or statistical generalization to organizations.
- No paid LLM calls, therefore no meaningful estimate of real Apertus/GPT inference behavior, latency or cost.
- No proprietary BOLT internals, genuine client traffic or nonpublic datasets.

## Competition completion checklist
Preliminary proposal PDF (1–2 pages) is ready, but upload through SocioVerse2 Studies remains pending platform-account verification. Final challenge requires 4–8-page research report, reproducible code package, and actual-run demo video <=5 minutes by October 31, 2026 (Beijing time).

License: Apache-2.0. Study is derived from the public interface design of SocioVerse2, but does not copy the reference study's policy logic.
