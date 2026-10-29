import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.processing import (  # noqa: E402
    Params, PostureEngine, Sample, angle_between, mean_vector, window_rms,
)

UPRIGHT = [0.0, 9.8, 0.0]
LEANING = [0.0, 8.0, 5.6]  # ~35 derajat dari tegak


def feed_both(eng, t, body_rms=0.05, seat_rms=0.03, grav=UPRIGHT):
    eng.feed(1, Sample(t, body_rms, list(grav)))
    eng.feed(2, Sample(t, seat_rms, [0.0, 0.0, 9.8]))


class ProcessingTests(unittest.TestCase):
    def test_rms_still_vs_moving(self):
        self.assertLess(window_rms([9.8, 9.81, 9.79, 9.8]), 0.05)
        self.assertGreater(window_rms([9.8, 12.0, 7.5, 11.0]), 1.0)
        self.assertEqual(window_rms([]), 0.0)

    def test_mean_vector(self):
        self.assertEqual(mean_vector([[1, 2, 3], [3, 4, 5]]), [2.0, 3.0, 4.0])

    def test_angle(self):
        self.assertAlmostEqual(angle_between(UPRIGHT, UPRIGHT), 0.0, places=3)
        self.assertAlmostEqual(angle_between([1, 0, 0], [0, 1, 0]), 90.0, places=3)
        self.assertGreater(angle_between(UPRIGHT, LEANING), 30)


class EngineTests(unittest.TestCase):
    def make(self):
        eng = PostureEngine(Params(lean_hold_s=5, sit_limit_s=60, break_reset_s=10, away_hold_s=2))
        feed_both(eng, 0)
        eng.calibrate()
        return eng

    def test_offline_and_calibrate(self):
        eng = PostureEngine()
        self.assertEqual(eng.evaluate(0)["state"], "OFFLINE")
        feed_both(eng, 0)
        self.assertEqual(eng.evaluate(0.5)["state"], "CALIBRATE")
        eng.calibrate()
        self.assertEqual(eng.evaluate(0.5)["state"], "GOOD")

    def test_slouch_needs_hold_time(self):
        eng = self.make()
        feed_both(eng, 1, grav=LEANING)
        self.assertEqual(eng.evaluate(1)["state"], "GOOD")  # baru mulai condong
        feed_both(eng, 4, grav=LEANING)
        self.assertEqual(eng.evaluate(4)["state"], "GOOD")
        feed_both(eng, 7, grav=LEANING)
        res = eng.evaluate(7)
        self.assertEqual(res["state"], "SLOUCH")
        self.assertGreater(res["lean_deg"], 30)

    def test_slouch_recovers(self):
        eng = self.make()
        for t in (1, 4, 7):
            feed_both(eng, t, grav=LEANING)
            eng.evaluate(t)
        feed_both(eng, 8, grav=UPRIGHT)
        self.assertEqual(eng.evaluate(8)["state"], "GOOD")

    def test_break_after_long_stillness(self):
        eng = self.make()
        for t in range(1, 70, 3):
            feed_both(eng, t)
            res = eng.evaluate(t)
        self.assertEqual(res["state"], "BREAK")

    def test_movement_resets_still_timer(self):
        eng = self.make()
        for t in range(1, 50, 3):
            feed_both(eng, t)
            eng.evaluate(t)
        feed_both(eng, 50, body_rms=0.6)  # peregangan
        feed_both(eng, 62)
        self.assertEqual(eng.evaluate(62)["state"], "GOOD")

    def test_away_when_body_moves_and_seat_still(self):
        eng = self.make()
        feed_both(eng, 1, body_rms=2.0, seat_rms=0.02)
        eng.evaluate(1)
        feed_both(eng, 4, body_rms=2.0, seat_rms=0.02)
        self.assertEqual(eng.evaluate(4)["state"], "AWAY")

    def test_common_motion(self):
        eng = self.make()
        feed_both(eng, 1, body_rms=2.0, seat_rms=2.0)
        self.assertEqual(eng.evaluate(1)["state"], "COMMON_MOTION")

    def test_stale_edge_goes_offline(self):
        eng = self.make()
        self.assertEqual(eng.evaluate(30)["state"], "OFFLINE")

    def test_pause(self):
        eng = self.make()
        eng.monitoring = False
        self.assertEqual(eng.evaluate(1)["state"], "PAUSED")


if __name__ == "__main__":
    unittest.main()
