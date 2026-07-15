"""アプリケーション設定の読み込みと型付き設定モデル。"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass(frozen=True)
class CalibrationConfig:
    parameters_file: str


@dataclass(frozen=True)
class MarkerConfig:
    size_m: float
    dictionary: str
    expected_id: Optional[int]


@dataclass(frozen=True)
class WindowConfig:
    name: str
    width: int
    height: int
    x_pos: int
    y_pos: int


@dataclass(frozen=True)
class UIConfig:
    camera_window: WindowConfig
    wireframe_window: WindowConfig


@dataclass(frozen=True)
class ProcessingConfig:
    wireframe_scale: float


@dataclass(frozen=True)
class DebugConfig:
    show_marker_info: bool
    show_pose_info: bool
    enable_3d_render: bool
    render_mode: str


@dataclass(frozen=True)
class AppConfig:
    calibration: CalibrationConfig
    marker: MarkerConfig
    ui: UIConfig
    processing: ProcessingConfig
    debug: DebugConfig


def _require_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"設定の{name}はマッピングで指定してください")
    return value


def _window_config(value: Any, name: str) -> WindowConfig:
    data = _require_mapping(value, name)
    return WindowConfig(
        name=str(data["name"]),
        width=int(data["width"]),
        height=int(data["height"]),
        x_pos=int(data["x_pos"]),
        y_pos=int(data["y_pos"]),
    )


def load_config(config_file: str = "config.yaml") -> AppConfig:
    """YAML設定を読み込み、検証済みの型付き設定を返します。"""
    path = Path(config_file)
    if not path.exists():
        raise FileNotFoundError(f"設定ファイルが見つかりません: {config_file}")

    with path.open("r", encoding="utf-8") as file:
        raw = _require_mapping(yaml.safe_load(file), "ルート")

    calibration = _require_mapping(raw["calibration"], "calibration")
    marker = _require_mapping(raw["marker"], "marker")
    processing = _require_mapping(raw["processing"], "processing")
    debug = _require_mapping(raw["debug"], "debug")
    ui = _require_mapping(raw["ui"], "ui")

    render_mode = str(debug["render_mode"]).lower()
    if render_mode not in {"opencv", "matplotlib"}:
        raise ValueError("debug.render_modeはopencvまたはmatplotlibを指定してください")

    expected_id = marker.get("expected_id")
    if expected_id is not None:
        expected_id = int(expected_id)

    return AppConfig(
        calibration=CalibrationConfig(parameters_file=str(calibration["parameters_file"])),
        marker=MarkerConfig(
            size_m=float(marker["size_m"]),
            dictionary=str(marker["dictionary"]),
            expected_id=expected_id,
        ),
        ui=UIConfig(
            camera_window=_window_config(ui["camera_window"], "ui.camera_window"),
            wireframe_window=_window_config(ui["wireframe_window"], "ui.wireframe_window"),
        ),
        processing=ProcessingConfig(wireframe_scale=float(processing["wireframe_scale"])),
        debug=DebugConfig(
            show_marker_info=bool(debug["show_marker_info"]),
            show_pose_info=bool(debug["show_pose_info"]),
            enable_3d_render=bool(debug["enable_3d_render"]),
            render_mode=render_mode,
        ),
    )
