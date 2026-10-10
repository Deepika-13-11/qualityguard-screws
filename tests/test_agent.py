import os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import qualityguard_agent as qg


class TestTools(unittest.TestCase):
    def test_cpk_centered(self):
        self.assertAlmostEqual(qg.calculate_cpk(10, 1, 7, 13), 1.0)

    def test_cpk_zero_sd(self):
        self.assertIsNone(qg.calculate_cpk(10, 0, 7, 13))

    def test_tolerance(self):
        self.assertEqual(qg.check_tolerance([1, 5, 9], 2, 8), [1, 9])

    def test_trend_upward(self):
        hist = [{"features": {"x": {"mean": 1.0}}}, {"features": {"x": {"mean": 2.0}}}]
        self.assertIn("UPWARD", qg.detect_trend(hist, "x", 3.0, 0.5))

    def test_trend_none(self):
        hist = [{"features": {"x": {"mean": 1.0}}}, {"features": {"x": {"mean": 3.0}}}]
        self.assertIsNone(qg.detect_trend(hist, "x", 2.0, 0.5))


class TestAgent(unittest.TestCase):
    def setUp(self):
        self.specs = qg.load_specs(os.path.join(os.path.dirname(__file__), "..", "specs.json"))
        self.tmp = tempfile.mkdtemp()
        self.agent = qg.QualityGuardAgent(
            self.specs, qg.Memory(os.path.join(self.tmp, "h.json")), use_llm=False)

    def _csv(self, head):
        path = os.path.join(self.tmp, "b.csv")
        with open(path, "w") as f:
            f.write("part_no,thread_pitch_diameter,shank_length,head_diameter\n")
            for i, h in enumerate(head, 1):
                f.write(f"{i},{7.10 + i * 0.001},{30.0 + i * 0.01},{h}\n")
        return path

    def test_good_batch_released(self):
        rep = self.agent.run(self._csv([12.82 + i * 0.01 for i in range(10)]))
        self.assertTrue(rep["disposition"].startswith("RELEASE"))

    def test_oversize_head_rejected(self):
        rep = self.agent.run(self._csv([13.1] * 10))
        self.assertEqual(rep["disposition"], "REJECTED (QUARANTINED)")

    def test_missing_column(self):
        path = os.path.join(self.tmp, "bad.csv")
        with open(path, "w") as f:
            f.write("part_no,head_diameter\n1,12.9\n")
        with self.assertRaises(ValueError):
            qg.read_cmm_csv(path, self.specs)


if __name__ == "__main__":
    unittest.main()
