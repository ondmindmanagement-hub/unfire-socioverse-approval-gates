"""Deterministic checks for synthetic approval study."""
import csv
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run as study

class StudyTests(unittest.TestCase):
    def test_same_seed_same_workload(self):
        self.assertEqual(study.make_requests(11), study.make_requests(11))
        self.assertNotEqual(study.make_requests(11), study.make_requests(29))

    def test_paired_arms_receive_same_requests(self):
        events = study.make_requests(11, 70)
        ids = [r.id for r in events]
        for arm in study.ARMS:
            self.assertEqual([r["request_id"] for r in study.simulate(events, arm)], ids)

    def test_no_duplicate_or_missing_terminals(self):
        for n in (1, 70, 120):
            events = study.make_requests(47, n)
            for arm in study.ARMS:
                outcomes = study.simulate(events, arm, capacity=2)
                self.assertEqual(len(outcomes), n)
                self.assertEqual(len(set(r["request_id"] for r in outcomes)), n)
                self.assertTrue(all(r["decision_step"] >= r["arrival"] for r in outcomes))

    def test_human_review_never_executes_oracle_unsafe(self):
        for seed in study.SEEDS:
            rows = study.simulate(study.make_requests(seed, 120), "capacity_review", 2)
            self.assertEqual(sum(r["unsafe_executed"] for r in rows), 0)

    def test_ungated_executes_everything(self):
        rows = study.simulate(study.make_requests(11), "ungated")
        self.assertTrue(all(r["decision"] == "execute" for r in rows))

    def test_static_false_denials_possible(self):
        rows = study.simulate(study.make_requests(11, 120), "static")
        self.assertGreater(sum(r["false_denial"] for r in rows), 0)

    def test_exact_reproducibility(self):
        with tempfile.TemporaryDirectory() as d:
            a = study.run(Path(d)/"a", seeds=(11,29), n=80, capacity=2)
            b = study.run(Path(d)/"b", seeds=(11,29), n=80, capacity=2)
            self.assertEqual(a, b)
            self.assertEqual((Path(d)/"a"/"SHA256SUM.txt").read_text(), (Path(d)/"b"/"SHA256SUM.txt").read_text())
            with (Path(d)/"a"/"trajectories.csv").open() as f:
                self.assertEqual(sum(1 for _ in csv.DictReader(f)), 2*80*3)

    def test_no_real_participant_claim(self):
        with tempfile.TemporaryDirectory() as d:
            report = study.run(Path(d), seeds=(11,), n=12)
            self.assertEqual(report["llm_calls"], 0)
            self.assertFalse(report["socioverse_native_integration"])
            self.assertIn("SIMULATED", report["caveat"])

if __name__ == "__main__":
    unittest.main()
