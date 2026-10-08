"""SocioVerse2-native P/E/B/collector adapter for Unfire's synthetic review study.
No real human or LLM; purely rule-driven, reproducible, synthetic.
"""
from __future__ import annotations
from statistics import mean
from typing import Any
from socioverse.abc import DecisionModel, EnvironmentProvider, MetricCollector, PopulationProvider
from socioverse.engine import register
from socioverse.schemas import (
    Action, EnvironmentBundle, EnvironmentLayer, InteractionStructure,
    Observation, Persona, PopulationBundle, PropagationMode,
    SimulationConfig, StudySpec,
)
from .run import Request, make_requests

def safe_div(a: float, b: float) -> float:
    return round(a / b, 4) if b else 0.0

@register("population", "unfire_approval.pop")
class RequestPopulation(PopulationProvider):
    def __init__(self, bundle: PopulationBundle):
        self.n = int(bundle.provider_args.get("n_agents", 100))
        self.n_steps = int(bundle.provider_args.get("n_steps", 12))
        self.people: list[Request] = []
    def build(self, seed: int) -> list[Persona]:
        self.people = make_requests(seed, self.n, self.n_steps)
        return [
            Persona(agent_id=r.id, group_key=r.priority,
                    attributes={"risk": r.risk, "arrival": r.arrival, "priority": r.priority},
                    init_state={"status": "pending"})
            for r in self.people
        ]
    def neighbors(self, aid: str) -> list[str]:
        return []

@register("environment", "unfire_approval.env")
class RequestEnvironment(EnvironmentProvider):
    def __init__(self, bundle: EnvironmentBundle):
        self.n = int(bundle.provider_args.get("n_agents", 100))
        self.n_steps = int(bundle.provider_args.get("n_steps", 12))
        self.requests: dict[str, Request] = {}
        self.decisions: dict[str, dict] = {}
    def reset(self, seed: int) -> None:
        self.requests = {r.id: r for r in make_requests(seed, self.n, self.n_steps)}
        self.decisions = {}
    def advance_to(self, t: int) -> list:
        return []
    def observe_batch(self, agent_ids: list[str], t: int, round_idx: int = 0) -> list[Observation]:
        out = []
        for aid in agent_ids:
            r = self.requests[aid]
            out.append(Observation(agent_id=aid, step=t,
                local_physical={
                    "risk": r.risk, "evidence_complete": r.evidence_complete,
                    "forbidden": r.forbidden, "arrival": r.arrival,
                    "deadline": r.deadline, "priority": r.priority,
                    "oracle_safe": r.oracle_safe,
                    "status": self.decisions.get(aid, {}).get("decision", "pending")},
                macro_physical={"reviewer_capacity": 0}))
        return out
    def apply(self, actions: list[Action]) -> None:
        for a in actions:
            if a.kind != "approval_decision":
                continue
            assert a.agent_id not in self.decisions
            r = self.requests[a.agent_id]
            self.decisions[a.agent_id] = {
                "decision": a.payload["decision"],
                "at_step": a.step,
                "latency": a.step - r.arrival,
                "oracle_safe": r.oracle_safe,
                "priority": r.priority,
            }
    def agent_state(self, aid: str) -> dict:
        return self.decisions.get(aid, {"decision": "pending"})
    def snapshot(self) -> dict:
        return {"terminal_count": len(self.decisions), "pending_count": len(self.requests)-len(self.decisions)}

@register("decision", "unfire_approval.decision")
class ReviewDecisionModel(DecisionModel):
    def __init__(self, arm: str = "capacity_review", reviewer_capacity: int = 8, **unused):
        if arm not in ("ungated", "static", "capacity_review"):
            raise ValueError("unknown arm")
        self.arm, self.capacity = arm, int(reviewer_capacity)
        if self.capacity < 1:
            raise ValueError("reviewer_capacity must be positive")
    def decide_batch(self, obs: list[Observation], memories: dict[str, Any]) -> list[Action]:
        if not obs: return []
        t = obs[0].step
        pending = [ob for ob in obs if ob.local_physical["status"] == "pending"
                   and ob.local_physical["arrival"] <= t]
        pending.sort(key=lambda o: (o.local_physical["arrival"], o.agent_id))
        decisions: dict[str, tuple[str,str]] = {}
        high_queue = []
        for ob in pending:
            p = ob.local_physical
            if self.arm == "ungated":
                decisions[ob.agent_id] = ("execute", "no gate")
            elif self.arm == "static":
                decisions[ob.agent_id] = (("deny", "static risk threshold") if p["risk"] == "high"
                                          else ("execute", "static below threshold"))
            elif p["forbidden"]:
                decisions[ob.agent_id] = ("deny", "forbidden action flag")
            elif p["risk"] == "low":
                decisions[ob.agent_id] = ("execute", "low risk rule")
            elif t > p["deadline"]:
                decisions[ob.agent_id] = ("expired", "review deadline missed")
            else:
                high_queue.append(ob)
        for ob in high_queue[:self.capacity]:
            p = ob.local_physical
            decisions[ob.agent_id] = (("execute", "scripted reviewer accepted evidence")
                                      if p["evidence_complete"] else
                                      ("deny", "scripted reviewer rejected missing evidence"))
        return [Action(agent_id=ob.agent_id, step=t, kind="approval_decision",
                       payload={"decision": decisions[ob.agent_id][0]},
                       source="rule", rationale=[decisions[ob.agent_id][1]])
                for ob in pending if ob.agent_id in decisions]

@register("collector", "unfire_approval.collector")
class ReviewMetricCollector(MetricCollector):
    _COLUMNS = ["unsafe_action_rate","safe_task_completion","false_denial_rate",
                "review_expirations","terminal_count","mean_latency","urgent_safe_completion",
                "standard_safe_completion"]
    def collect(self, env: Any, actions: list[Action], t: int) -> dict[str, Any]:
        terms = list(env.decisions.items())
        reqs = list(env.requests.values())
        execution = [env.requests[aid] for aid, d in terms if d["decision"] == "execute"]
        oracle_safe = [r for r in reqs if r.oracle_safe]
        denied_safe = [aid for aid,d in terms if d["decision"] != "execute" and env.requests[aid].oracle_safe]
        safe_done = [r for r in execution if r.oracle_safe]
        d = {
            "unsafe_action_rate": safe_div(sum(not r.oracle_safe for r in execution), len(execution)),
            "safe_task_completion": safe_div(len(safe_done), len(oracle_safe)),
            "false_denial_rate": safe_div(len(denied_safe), len(oracle_safe)),
            "review_expirations": sum(x["decision"]=="expired" for _,x in terms),
            "terminal_count": len(terms),
            "mean_latency": round(mean([x["latency"] for _,x in terms]),4) if terms else 0,
        }
        for key in ("urgent","standard"):
            d[key+"_safe_completion"] = safe_div(
                sum(r.oracle_safe and r.priority==key for r in execution),
                sum(r.oracle_safe and r.priority==key for r in reqs))
        return d
    def columns(self) -> list[str]:
        return list(self._COLUMNS)

def make_bundles(seed: int = 11, n_agents: int = 100, n_steps: int = 18,
                 arm: str = "capacity_review", reviewer_capacity: int = 8):
    study_id = "unfire_approval_gates"
    metrics = ReviewMetricCollector._COLUMNS
    study = StudySpec(
        study_id=study_id, title="Human Approval Gates under Bounded Synthetic Reviewer Capacity",
        research_question="How do review policies trade unsafe task execution against false denial and delay?",
        hypothesis="Scripted capacity-limited review lowers unsafe synthetic execution, but may expire safe work when overloaded.",
        study_type="longitudinal", n_steps=n_steps, seed=seed, metrics=metrics,
        domain="multi-agent-governance", tags=["human-ai", "approval", "synthetic", "reproducible"],
        legacy_simulator="from_scratch",
        provider_refs=["unfire_approval.pop","unfire_approval.env","unfire_approval.decision",
                       "unfire_approval.collector"],
        adjustable_params=["reviewer_capacity","n_agents","arm","seed"],
        status="demo-only")
    env = EnvironmentBundle(study_id=study_id, provider_ref="unfire_approval.env",
        provider_args={"n_agents":n_agents,"n_steps":12},
        layers=[EnvironmentLayer(name="request_queue",modality="physical",scope="macro",
                dynamics="endogenous",description="synthetic action queue and review decisions")])
    pop = PopulationBundle(study_id=study_id, provider_ref="unfire_approval.pop",
        provider_args={"n_agents":n_agents,"n_steps":12},
        interaction=InteractionStructure(kind="none"),
        propagation=PropagationMode.CONTAGION)
    sim = SimulationConfig(study_id=study_id, n_steps=n_steps, seed=seed,
        decision_ref="unfire_approval.decision",
        decision_args={"arm":arm,"reviewer_capacity":reviewer_capacity},
        collector_ref="unfire_approval.collector",interaction_rounds=1)
    return study,env,pop,sim
