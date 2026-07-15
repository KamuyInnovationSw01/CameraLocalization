import unittest

from config import AppConfig, load_config


class ConfigTest(unittest.TestCase):
    def test_load_config_returns_typed_settings(self):
        config = load_config("config.yaml")

        self.assertIsInstance(config, AppConfig)
        self.assertEqual(config.marker.dictionary, "DICT_4X4_50")
        self.assertEqual(config.processing.wireframe_scale, 0.15)
        self.assertNotIn("target_fps", config.processing.__dict__)


if __name__ == "__main__":
    unittest.main()
