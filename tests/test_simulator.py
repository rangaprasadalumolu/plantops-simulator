import tempfile, unittest
from pathlib import Path
from plantops.generate import generate

class SimulatorTests(unittest.TestCase):
    def test_small_dataset_and_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=generate(Path(tmp)/"data",telemetry_n=300)
            self.assertTrue(report["all_checks_pass"])
            self.assertEqual(report["metrics"]["telemetry_points"],300)
            self.assertTrue(report["checks"]["topology_connected_per_facility"])
            self.assertTrue(report["checks"]["ground_truth_separate"])

if __name__=="__main__": unittest.main()
