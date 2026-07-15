import unittest

import numpy as np

from marker_detector import MarkerDetector


class MarkerDetectorTest(unittest.TestCase):
    def test_get_marker_info_without_detection(self):
        detector = MarkerDetector("DICT_4X4_50")

        info = detector.get_marker_info(None, None, 0.1)

        self.assertFalse(info["detected"])
        self.assertEqual(info["count"], 0)
        self.assertEqual(info["markers"], [])

    def test_get_marker_info_contains_marker_geometry(self):
        detector = MarkerDetector("DICT_4X4_50")
        corners = np.array([[[[10, 20], [30, 20], [30, 40], [10, 40]]]], dtype=np.float32)
        ids = np.array([1], dtype=np.int32)

        info = detector.get_marker_info(corners, ids, 0.1)

        self.assertTrue(info["detected"])
        self.assertEqual(info["count"], 1)
        self.assertEqual(info["markers"][0]["id"], 1)
        self.assertEqual(info["markers"][0]["center"], (20.0, 30.0))


if __name__ == "__main__":
    unittest.main()
