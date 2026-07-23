"""フレーム処理、描画、デバッグ出力のアプリケーションパイプライン。"""

from typing import Optional

import cv2
import numpy as np

from config import AppConfig
from marker_detector import MarkerDetector
from markerless_localizer import MarkerlessLocalizer
from pose_estimator import PoseEstimator
from ui_manager import UIManager
from wireframe_renderer import WireframeRenderer


class FramePipeline:
    """1フレームの検出、姿勢推定、描画をまとめて実行します。

    ``localization.mode``に応じてArUco検出器またはマーカーレスローカライザーを
    呼び分けます。後段の描画とデバッグ出力が扱いやすいよう、両方式とも検出情報
    と姿勢情報の辞書を返すインターフェースにそろえています。
    """

    def __init__(
        self,
        config: AppConfig,
        marker_detector: Optional[MarkerDetector],
        markerless_localizer: Optional[MarkerlessLocalizer],
        pose_estimator: PoseEstimator,
        wireframe_renderer: WireframeRenderer,
        ui_manager: UIManager,
    ):
        self.config = config
        self.marker_detector = marker_detector
        self.markerless_localizer = markerless_localizer
        self.pose_estimator = pose_estimator
        self.wireframe_renderer = wireframe_renderer
        self.ui_manager = ui_manager

    def process_frame(self, frame: np.ndarray) -> tuple[dict, Optional[dict]]:
        """1フレームを処理し、検出統計と推定姿勢を返します。"""
        if self.config.localization.mode == "markerless":
            if self.markerless_localizer is None:
                raise RuntimeError("マーカーレスローカライザーが初期化されていません")
            return self.markerless_localizer.estimate_pose(frame)

        marker_detector = self.marker_detector
        if marker_detector is None:
            raise RuntimeError("マーカー検出器が初期化されていません")
        corners, ids, _rejected = marker_detector.detect_markers(frame)
        marker_info = marker_detector.get_marker_info(
            corners,
            np.asarray(ids) if ids is not None else None,
            self.config.marker.size_m,
        )
        pose_info = None
        if marker_info["detected"] and marker_info["markers"]:
            marker = marker_info["markers"][0]
            success, rvec, tvec = self.pose_estimator.estimate_marker_pose(
                marker_corners=marker["corners"],
                marker_size_m=self.config.marker.size_m,
            )
            if success and rvec is not None and tvec is not None:
                pose_info = self.pose_estimator.get_pose_info(rvec, tvec)

        return marker_info, pose_info

    def render_output(
        self,
        frame: np.ndarray,
        marker_info: dict,
        pose_info: Optional[dict],
    ) -> tuple[np.ndarray, np.ndarray]:
        """カメラ映像への情報描画と、姿勢の3Dビュー描画を行います。"""
        # マーカーレス方式には描画可能な四隅がないため、入力フレームをそのまま使います。
        if self.config.localization.mode == "markerless":
            camera_frame = frame.copy()
            camera_frame = self._draw_markerless_matches(camera_frame, marker_info)
        else:
            marker_detector = self.marker_detector
            if marker_detector is None:
                raise RuntimeError("マーカー検出器が初期化されていません")
            camera_frame = marker_detector.draw_detected_markers(
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

        # 姿勢推定に失敗したフレームでは3Dビューを更新せず、初期状態の
        # 暗い背景を表示します。マッチング点はカメラ映像側だけに残します。
        render_pose = pose_info

        if render_pose is not None and self.config.debug.enable_3d_render:
            try:
                wireframe_frame = self.wireframe_renderer.draw_3d_view(
                    rvec=render_pose["rvec"],
                    tvec=render_pose["tvec"],
                    marker_size_m=self.config.marker.size_m,
                    map_points=(
                        marker_info.get("map_points")
                        if self.config.localization.mode == "markerless"
                        else None
                    ),
                    map_point_colors=(
                        marker_info.get("map_point_colors")
                        if self.config.localization.mode == "markerless"
                        else None
                    ),
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

    @staticmethod
    def _draw_markerless_matches(frame: np.ndarray, match_info: dict) -> np.ndarray:
        """現在フレーム上のLightGlue対応点を描画します。

        姿勢推定に採用されたインライアは緑、対応はしたもののRANSACで除外された
        外れ値は赤で表示します。PnPを実行できない対応点不足のフレームでは、
        全対応点を黄色で表示して、検出状態を視覚的に確認できるようにします。
        """
        result = frame.copy()
        points = np.asarray(match_info.get("matched_points", []), dtype=np.float32)
        if points.size == 0:
            return result
        points = points.reshape(-1, 2)
        inlier_indices = set(
            np.asarray(match_info.get("inlier_indices", []), dtype=np.int64).reshape(-1).tolist()
        )
        has_ransac_result = "inliers" in match_info

        for index, point in enumerate(points):
            x, y = np.round(point).astype(int)
            if has_ransac_result:
                color = (0, 255, 0) if index in inlier_indices else (0, 0, 255)
            else:
                color = (0, 255, 255)
            cv2.circle(result, (int(x), int(y)), 4, color, 1, cv2.LINE_AA)
            cv2.drawMarker(
                result,
                (int(x), int(y)),
                color,
                cv2.MARKER_CROSS,
                7,
                1,
                cv2.LINE_AA,
            )

        cv2.putText(
            result,
            "Matches: green=inlier red=outlier yellow=unverified",
            (10, result.shape[0] - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        return result

    def print_info(self, marker_info: dict, pose_info: Optional[dict]) -> None:
        if self.config.debug.show_marker_info:
            if self.config.localization.mode == "markerless":
                print(
                    f"\nマーカーレス対応点: {marker_info.get('count', 0)} 個, "
                    f"インライア: {marker_info.get('inliers', 0)} 個"
                )
            elif marker_info["detected"]:
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
