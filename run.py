#!/usr/bin/env python3
"""Unfire approval-gate study, deterministic synthetic pilot for SocioVerse Challenge 2026.
No real humans, real-world causal claims, paid model calls, or production BOLT code.
This is a preliminary local model; native SocioVerse2 adapter is not yet implemented.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import random
import statistics
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path

SEEDS = (11, 29, 47, 83, 101)
ARMS = ("ungated", "static", "capacity_review")

@dataclass(frozen=True)
class Request:
    id: str
    arrival: int
    risk: str
    evidence_complete: bool
    forbidden: bool
    priority: str
    deadline: int
    @property
    def oracle_safe(self) -> bool:
        return not self.forbidden and not (self.risk == "high" and not self.evidence_complete)

def make_requests(seed: int, n: int = 100, n_steps: int = 12) -> list[Request]:
    rng = random.Random(seed)
    events = []
    for i in range(n):
        arrival = rng.randrange(n_steps)
        risk = "high" if rng.random() < 0.40 else "low"
        evidence_complete = rng.random() >= 0.26
        forbidden = rng.random() < 0.08
        priority = "urgent" if rng.random() < 0.30 else "standard"
        events.append(Request(f"req-{seed}-{i:03d}", arrival, risk, evidence_complete,
                              forbidden, priority, arrival + (2 if priority == "urgent" else 4)))
    return sorted(events, key=lambda x: (x.arrival, x.id))

def simulate(requests: list[Request], arm: str, capacity: int = 8) -> list[dict]:
    """One terminal outcome per immutable request, no randomness inside the policies."""
    assert arm in ARMS
    assert capacity >= 1
    decisions: dict[str, dict] = {}
    queue: deque[Request] = deque()
    by_step: dict[int, list[Request]] = {}
    for r in requests:
        by_step.setdefault(r.arrival, []).append(r)
    def record(r: Request, action: str, step: int, reason: str) -> None:
        assert r.id not in decisions, f"duplicate terminal decision: {r.id}"
        decisions[r.id] = {
            "request_id": r.id, "arm": arm, "arrival": r.arrival,
            "decision_step": step, "latency": step - r.arrival, "decision": action,
            "reason": reason, "risk": r.risk, "evidence_complete": int(r.evidence_complete),
            "forbidden": int(r.forbidden), "priority": r.priority,
            "oracle_safe": int(r.oracle_safe),
            "unsafe_executed": int(action == "execute" and not r.oracle_safe),
            "false_denial": int(action != "execute" and r.oracle_safe),
            "safe_completed": int(action == "execute" and r.oracle_safe)
        }
    end_step = max((r.deadline for r in requests), default=0) + 1
    for t in range(end_step + 1):
        for r in by_step.get(t, []):
            if arm == "ungated":
                record(r, "execute", t, "no policy")
            elif arm == "static":
                if r.risk == "high":
                    record(r, "deny", t, "static risk threshold")
                else:
                    record(r, "execute", t, "risk below threshold")
            else:
                if r.forbidden:
                    record(r, "deny", t, "deterministic forbidden-action rule")
                elif r.risk == "low":
                    record(r, "execute", t, "low-risk approved by explicit rule")
                else:
                    queue.append(r)
        if arm == "capacity_review":
            retained: deque[Request] = deque()
            while queue:
                r = queue.popleft()
                if t > r.deadline:
                    record(r, "expired", t, "review deadline missed")
                else:
                    retained.append(r)
            queue = retained
            for _ in range(min(capacity, len(queue))):
                r = queue.popleft()
                if r.evidence_complete:
                    record(r, "execute", t, "synthetic reviewer approved evidence")
                else:
                    record(r, "deny", t, "synthetic reviewer rejected missing evidence")
    assert len(decisions) == len(requests), (len(decisions), len(requests), arm)
    return [decisions[r.id] for r in requests]

def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    executed = sum(r["decision"] == "execute" for r in rows)
    oracle_safe_n = sum(r["oracle_safe"] for r in rows)
    completed_safe = sum(r["safe_completed"] for r in rows)
    unsafe_executed = sum(r["unsafe_executed"] for r in rows)
    latencies = [r["latency"] for r in rows if r["decision"] == "execute"]
    by_priority = {}
    for p in ("urgent", "standard"):
        sub = [r for r in rows if r["priority"] == p]
        by_priority[p] = round(sum(r["safe_completed"] for r in sub) / max(1, sum(r["oracle_safe"] for r in sub)), 4)
    return {
        "requests": n, "executed": executed, "oracle_safe": oracle_safe_n,
        "safe_completed": completed_safe, "unsafe_executed": unsafe_executed,
        "unsafe_action_rate": round(unsafe_executed / max(1, executed), 4),
        "safe_task_completion": round(completed_safe / max(1, oracle_safe_n), 4),
        "false_denial_count": sum(r["false_denial"] for r in rows),
        "false_denial_rate": round(sum(r["false_denial"] for r in rows) / max(1, oracle_safe_n), 4),
        "mean_executed_latency_steps": round(statistics.mean(latencies), 4) if latencies else None,
        "review_expirations": sum(r["decision"] == "expired" for r in rows),
        "safe_completion_by_synthetic_priority": by_priority,
    }

def run(output: Path, seeds: tuple[int, ...] = SEEDS, n: int = 100,
        capacity: int = 8) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    trajectories = []
    per_seed = []
    for seed in seeds:
        events = make_requests(seed, n)
        for arm in ARMS:
            rows = simulate(events, arm, capacity)
            trajectories.extend(dict(seed=seed, **row) for row in rows)
            per_seed.append(dict(seed=seed, arm=arm, **summarize(rows)))
    fields = ["seed"] + list(trajectories[0].keys())
    with (output / "trajectories.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(trajectories)
    result = {
        "experiment": "Unfire synthetic approval gates, scripted pilot",
        "caveat": "SIMULATED REVIEWERS only; descriptive synthetic results, NOT human or real-world causal evidence",
        "socioverse_native_integration": False,
        "llm_kind": "scripted", "llm_calls": 0, "estimated_usd_api_cost": 0,
        "seeds": list(seeds), "requests_per_seed": n, "reviewer_capacity_per_step": capacity,
        "arms": list(ARMS), "per_seed": per_seed,
        "aggregate": {arm: {k: round(statistics.mean(x[k] for x in per_seed if x["arm"] == arm),4)
                            for k in ("safe_task_completion","unsafe_action_rate",
                                      "false_denial_rate","false_denial_count","review_expirations")}
                      for arm in ARMS},
    }
    with (output / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write("\n")
    digest = hashlib.sha256((output / "trajectories.csv").read_bytes()).hexdigest()
    (output / "SHA256SUM.txt").write_text(f"{digest}  trajectories.csv\n", encoding="utf-8")
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "trajectory")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--review-capacity", type=int, default=8)
    args = parser.parse_args()
    if args.requests < 1 or args.review_capacity < 1:
        parser.error("positive --requests and --review-capacity required")
    result = run(args.out, n=args.requests, capacity=args.review_capacity)
    print(json.dumps(result["aggregate"], indent=2, sort_keys=True))
