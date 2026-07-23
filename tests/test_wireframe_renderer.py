import unittest

import cv2
import numpy as np

from wireframe_renderer import WireframeRenderer


class WireframeRendererTest(unittest.TestCase):
    def setUp(self):
        self.camera_matrix = np.array(
            [
                [800.0, 0.0, 320.0],
                [0.0, 800.0, 240.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float32,
        )
        self.renderer = WireframeRenderer(self.camera_matrix, image_size=(640, 480))

    def test_frustum_matches_camera_intrinsics(self):
        vertices = self.renderer.create_frustum_vertices(0.1)

        np.testing.assert_allclose(
            vertices[1:],
            [
                [-0.04, -0.03, 0.1],
                [0.04, -0.03, 0.1],
                [0.04, 0.03, 0.1],
                [-0.04, 0.03, 0.1],
            ],
        )

    def test_markerless_view_renders_colored_map_points(self):
        map_points = np.array(
            [[0.0, 0.0, 2.0], [0.2, 0.0, 2.0], [0.0, 0.2, 2.0]],
            dtype=np.float32,
        )
        colors = np.array(
            [[150, 150, 150], [0, 255, 0], [0, 0, 255]],
            dtype=np.uint8,
        )

        image = self.renderer.draw_3d_view(
            np.zeros((3, 1), dtype=np.float32),
            np.array([[0.0], [0.0], [1.0]], dtype=np.float32),
            map_points=map_points,
            map_point_colors=colors,
        )

        self.assertEqual(image.shape, (720, 960, 3))
        self.assertGreater(int(np.sum(image)), 0)


if __name__ == "__main__":
    unittest.main()
