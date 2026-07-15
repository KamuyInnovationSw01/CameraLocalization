"""フレーム処理、描画、デバッグ出力のアプリケーションパイプライン。"""

from typing import Optional

import numpy as np

from config import AppConfig
from marker_detector import MarkerDetector
from pose_estimator import PoseEstimator
from ui_manager import UIManager
from wireframe_renderer import WireframeRenderer


class FramePipeline:
    """1フレームの検出、姿勢推定、描画をまとめて実行します。"""

    def __init__(
        self,
        config: AppConfig,
        marker_detector: MarkerDetector,
        pose_estimator: PoseEstimator,
        wireframe_renderer: WireframeRenderer,
        ui_manager: UIManager,
    ):
        self.config = config
        self.marker_detector = marker_detector
        self.pose_estimator = pose_estimator
        self.wireframe_renderer = wireframe_renderer
        self.ui_manager = ui_manager

    def process_frame(self, frame: np.ndarray) -> tuple[dict, Optional[dict]]:
        corners, ids, _rejected = self.marker_detector.detect_markers(frame)
        marker_info = self.marker_detector.get_marker_info(
            corners,
            ids,
            self.config.marker.size_m,
        )
        marker_info["corners"] = corners
        marker_info["ids"] = ids

        pose_info = None
        if marker_info["detected"] and marker_info["markers"]:
            marker = marker_info["markers"][0]
            success, rvec, tvec = self.pose_estimator.estimate_marker_pose(
                marker_corners=marker["corners"],
                marker_size_m=self.config.marker.size_m,
            )
            if success:
                pose_info = self.pose_estimator.get_pose_info(rvec, tvec)
                pose_info["rvec"] = rvec
                pose_info["tvec"] = tvec

        return marker_info, pose_info

    def render_output(
        self,
        frame: np.ndarray,
        marker_info: dict,
        pose_info: Optional[dict],
    ) -> tuple[np.ndarray, np.ndarray]:
        camera_frame = self.marker_detector.draw_detected_markers(
            frame,
            marker_info.get("corners") if marker_info["detected"] else None,
            marker_info.get("ids") if marker_info["detected"] else None,
        )
        wireframe_frame = np.full(
            (
                self.ui_manager.wireframe_window_size[1],
                self.ui_manager.wireframe_window_size[0],
                3,
            ),
            50,
            dtype=np.uint8,
        )

        if pose_info is not None and self.config.debug.enable_3d_render:
            try:
                if self.config.debug.render_mode == "matplotlib":
                    wireframe_frame = self.wireframe_renderer.draw_3d_view_matplotlib(
                        rvec=pose_info["rvec"],
                        tvec=pose_info["tvec"],
                        marker_size_m=self.config.marker.size_m,
                    )
                else:
                    wireframe_frame = self.wireframe_renderer.draw_3d_view(
                        rvec=pose_info["rvec"],
                        tvec=pose_info["tvec"],
                        marker_size_m=self.config.marker.size_m,
                    )
            except Exception as error:
                print(f"3Dビュー描画エラー: {error}")

        if self.config.debug.show_marker_info:
            camera_frame = self.ui_manager.draw_debug_info(
                camera_frame,
                marker_count=marker_info.get("count", 0),
                pose_distance=pose_info.get("translation_distance_m", 0) if pose_info else 0,
                rotation_angle=pose_info.get("rotation_angle_deg", 0) if pose_info else 0,
            )

        return camera_frame, wireframe_frame

    def print_info(self, marker_info: dict, pose_info: Optional[dict]) -> None:
        if self.config.debug.show_marker_info:
            if marker_info["detected"]:
                print(f"\n検出されたマーカー: {marker_info['count']} 個")
                for marker in marker_info["markers"]:
                    print(
                        f"  - ID: {marker['id']}, "
                        f"中心: ({marker['center'][0]:.1f}, {marker['center'][1]:.1f})"
                    )
            else:
                print("\nマーカーが検出されていません。")

        if self.config.debug.show_pose_info and pose_info is not None:
            print("ポーズ情報:")
            print(f"  - 距離: {pose_info['translation_distance_m']:.3f} m")
            print(f"  - 回転角: {pose_info['rotation_angle_deg']:.1f} deg")
            print(
                f"  - カメラ位置: ({pose_info['camera_position'][0]:.3f}, "
                f"{pose_info['camera_position'][1]:.3f}, "
                f"{pose_info['camera_position'][2]:.3f})"
            )
