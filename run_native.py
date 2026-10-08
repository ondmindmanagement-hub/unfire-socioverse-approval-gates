"""Execute native SocioVerse2 simulation and verify complete trajectories."""
import json
import tempfile
from pathlib import Path
from socioverse.engine import build_simulator
from .native_model import make_bundles

OUT = Path(__file__).parent / "trajectory" / "native"
OUT.mkdir(parents=True, exist_ok=True)
out = []
for seed in (11, 29, 47, 83, 101):
    for arm in ("ungated", "static", "capacity_review"):
        for capacity in ((2, 8) if arm=="capacity_review" else (8,)):
            study, env, pop, sim_cfg = make_bundles(seed=seed, arm=arm, reviewer_capacity=capacity)
            fn = OUT / f"{arm}-{capacity}-{seed}.duckdb"
            if fn.exists():
                fn.unlink()
            runner = build_simulator(env_bundle=env, pop_bundle=pop,
                                     sim_config=sim_cfg, store_path=fn)
            hist = runner.run()
            assert not hist.covers(study.metrics), hist.covers(study.metrics)
            assert len(runner.env.decisions) == 100
            assert len(hist.rows) == 19, len(hist.rows)
            final = hist.rows[-1]
            data = dict(seed=seed, arm=arm, capacity=capacity, n_terminal=100,
                        n_steps=18, metrics={k:final[k] for k in study.metrics})
            out.append(data)
            print(f"NATIVE PASS {arm} capacity={capacity} seed={seed} "
                  f"unsafe={data['metrics']['unsafe_action_rate']} "
                  f"safe_done={data['metrics']['safe_task_completion']}", flush=True)
(OUT / "native_summary.json").write_text(json.dumps(out, indent=2, sort_keys=True)+"\n", encoding="utf-8")
print("NATIVE RUNS PASSED", len(out))
