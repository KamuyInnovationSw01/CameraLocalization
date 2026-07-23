import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from config import AppConfig, load_config
from build_markerless_map import _load_reference_spec


class ConfigTest(unittest.TestCase):
    def test_load_config_returns_typed_settings(self):
        config = load_config("config.yaml")

        self.assertIsInstance(config, AppConfig)
        self.assertEqual(config.marker.dictionary, "DICT_4X4_50")
        self.assertEqual(config.processing.wireframe_scale, 0.15)
        self.assertNotIn("target_fps", config.processing.__dict__)
        self.assertEqual(config.localization.mode, "markerless")
        self.assertEqual(config.markerless.map_file, "markerless_map.npz")

    def test_reference_spec_requires_distance_only_for_second_image(self):
        with TemporaryDirectory() as directory:
            spec_file = Path(directory) / "references.yaml"
            spec_file.write_text(
                yaml.safe_dump(
                    {
                        "reference_images": [
                            {"file": "ref_1.png"},
                            {"file": "ref_2.png", "position_m": 0.03},
                            {"file": "ref_3.png"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            references = _load_reference_spec(str(spec_file))

        self.assertEqual(references[1]["distance_m"], 0.03)
        self.assertEqual(references[2]["distance_m"], 0.0)

    def test_reference_spec_rejects_missing_second_image_distance(self):
        with TemporaryDirectory() as directory:
            spec_file = Path(directory) / "references.yaml"
            spec_file.write_text(
                yaml.safe_dump(
                    {
                        "reference_images": [
                            {"file": "ref_1.png"},
                            {"file": "ref_2.png"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "ref_2"):
                _load_reference_spec(str(spec_file))


if __name__ == "__main__":
    unittest.main()
