import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import cv2
import numpy as np

from pose_estimator import PoseEstimator


class PoseEstimatorTest(unittest.TestCase):
    def _create_calibration_file(self, directory: str) -> str:
        path = Path(directory) / "calibration.json"
        path.write_text(
            json.dumps(
                {
                    "imageSize": [640, 480],
                    "cameraMatrix": [
                        [800.0, 0.0, 320.0],
                        [0.0, 800.0, 240.0],
                        [0.0, 0.0, 1.0],
                    ],
                    "distCoeffs": [0.0, 0.0, 0.0, 0.0, 0.0],
                }
            ),
            encoding="utf-8",
        )
        return str(path)

    def test_get_pose_info_keeps_vectors_as_numpy_arrays(self):
        with TemporaryDirectory() as directory:
            estimator = PoseEstimator(self._create_calibration_file(directory))

        rvec = np.zeros((3, 1), dtype=np.float32)
        tvec = np.array([[0.0], [0.0], [1.0]], dtype=np.float32)
        pose_info = estimator.get_pose_info(rvec, tvec)

        self.assertIsInstance(pose_info["rvec"], np.ndarray)
        self.assertIsInstance(pose_info["tvec"], np.ndarray)
        np.testing.assert_allclose(pose_info["camera_position"], [0.0, 0.0, -1.0])

    def test_estimate_marker_pose_reprojects_synthetic_marker(self):
        with TemporaryDirectory() as directory:
            estimator = PoseEstimator(self._create_calibration_file(directory))

        marker_size = 0.1
        object_points = np.array(
            [
                [-marker_size / 2, marker_size / 2, 0],
                [marker_size / 2, marker_size / 2, 0],
                [marker_size / 2, -marker_size / 2, 0],
                [-marker_size / 2, -marker_size / 2, 0],
            ],
            dtype=np.float32,
        )
        image_points, _ = cv2.projectPoints(
            object_points,
            np.zeros((3, 1), dtype=np.float32),
            np.array([[0.0], [0.0], [0.8]], dtype=np.float32),
            estimator.get_camera_matrix(),
            estimator.get_dist_coeffs(),
        )

        success, rvec, tvec = estimator.estimate_marker_pose(
            image_points.reshape(4, 2), marker_size
        )

        self.assertTrue(success)
        self.assertIsNotNone(rvec)
        self.assertIsNotNone(tvec)
        self.assertAlmostEqual(float(tvec[2, 0]), 0.8, places=2)


if __name__ == "__main__":
    unittest.main()
