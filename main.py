"""カメラローカライゼーションアプリケーションの起動入口。"""

import time
from typing import Optional

import cv2

from camera_discovery import CameraInfo, get_camera_info_list
from camera_handler import CameraHandler
from config import AppConfig, load_config
from marker_detector import MarkerDetector
from markerless_localizer import MarkerlessLocalizer
from pipeline import FramePipeline
from pose_estimator import PoseEstimator
from ui_manager import UIManager
from wireframe_renderer import WireframeRenderer


class CameraLocalizationApp:
    """カメラの初期化とアプリケーションループを管理します。"""

    def __init__(self, config_file: str = "config.yaml"):
        self.config: AppConfig = load_config(config_file)
        print(f"設定ファイルを読み込みました: {config_file}")
        self.running = False
        self.camera_handler: Optional[CameraHandler] = None
        self.ui_manager: Optional[UIManager] = None
        self.pipeline: Optional[FramePipeline] = None
        self._initialize_modules()

    def _initialize_modules(self) -> None:
        """カメラ、検出器、推定器、描画器、UIを設定に従って初期化します。

        マーカー方式とマーカーレス方式は検出器だけが異なるため、選択された
        方式のモジュールだけを生成します。これにより不要なモデル読み込みを
        避け、従来のArUco方式をそのまま利用できます。
        """
        print("\n=== モジュール初期化開始 ===")
        camera_info_list = self._discover_cameras()
        camera_id = self._select_camera(camera_info_list)
        width, height = self._select_resolution(camera_id)

        print("\n[1] カメラハンドラーを初期化中...")
        self.camera_handler = CameraHandler(
            camera_id=camera_id,
            width=width,
            height=height,
        )
        if not self.camera_handler.initialize():
            raise RuntimeError(f"カメラ {camera_id} の初期化に失敗しました")

        # 使わない方式のモジュールはNoneにして、FramePipeline側で分岐します。
        marker_detector = None
        markerless_localizer = None
        if self.config.localization.mode == "markerless":
            print("\n[2] マーカーレスローカライザーを初期化中...")
            markerless_localizer = MarkerlessLocalizer(
                map_file=self.config.markerless.map_file,
                device=self.config.markerless.device,
                max_keypoints=self.config.markerless.max_keypoints,
                min_matches=self.config.markerless.min_matches,
                min_inliers=self.config.markerless.min_inliers,
            )
            print(f"    [OK] マップ: {self.config.markerless.map_file}")
        else:
            print("\n[2] マーカー検出器を初期化中...")
            marker_detector = MarkerDetector(self.config.marker.dictionary)
            print(f"    [OK] 辞書: {self.config.marker.dictionary}")

        print("\n[3] ポーズ推定器を初期化中...")
        pose_estimator = PoseEstimator(self.config.calibration.parameters_file)

        print("\n[4] ワイヤフレーム描画器を初期化中...")
        wireframe_renderer = WireframeRenderer(
            camera_matrix=pose_estimator.get_camera_matrix(),
            wireframe_scale=self.config.processing.wireframe_scale,
            image_size=pose_estimator.get_image_size(),
        )

        print("\n[5] UIマネージャーを初期化中...")
        self.ui_manager = UIManager(
            camera_config=self.config.ui.camera_window,
            wireframe_config=self.config.ui.wireframe_window,
        )

        self.pipeline = FramePipeline(
            config=self.config,
            marker_detector=marker_detector,
            markerless_localizer=markerless_localizer,
            pose_estimator=pose_estimator,
            wireframe_renderer=wireframe_renderer,
            ui_manager=self.ui_manager,
        )
        print("\n=== モジュール初期化完了 ===\n")

    @staticmethod
    def _discover_cameras() -> list[CameraInfo]:
        print("\n[カメラ] 利用可能なカメラを検出中...")
        camera_info_list = get_camera_info_list()
        if not camera_info_list:
            raise RuntimeError("利用可能なカメラが見つかりません")
        return camera_info_list

    @staticmethod
    def _select_camera(camera_info_list: list[CameraInfo]) -> int:
        if len(camera_info_list) == 1:
            info = camera_info_list[0]
            print(
                f"    カメラ {info.id} ({info.name}) を使用します: "
                f"{info.width}x{info.height}@{info.fps:.1f}fps"
            )
            return info.id

        print("\n    利用可能なカメラ:")
        for index, info in enumerate(camera_info_list):
            print(
                f"      [{index}] カメラID {info.id} - {info.name} "
                f"({info.width}x{info.height} @ {info.fps:.1f}fps)"
            )

        while True:
            try:
                selected_index = int(
                    input(f"\n    使用するカメラを選択してください (0-{len(camera_info_list) - 1}): ")
                )
                if 0 <= selected_index < len(camera_info_list):
                    return camera_info_list[selected_index].id
                print(f"    エラー: インデックス {selected_index} は無効です")
            except EOFError:
                return camera_info_list[0].id
            except ValueError:
                print("    エラー: 数値を入力してください")

    @staticmethod
    def _select_resolution(camera_id: int) -> tuple[Optional[int], Optional[int]]:
        print(f"\n    [カメラ {camera_id} の利用可能な解像度を検索中...]")
        resolutions = CameraHandler.get_available_resolutions(camera_id)
        if not resolutions:
            print("    警告: 利用可能な解像度が取得できないため、デフォルト設定を使用します")
            return None, None

        print(f"\n    利用可能な解像度（{len(resolutions)}個）:")
        for index, (width, height) in enumerate(resolutions):
            print(f"      [{index}] {width}x{height}")

        while True:
            try:
                selected_index = int(
                    input(f"\n    使用する解像度を選択してください (0-{len(resolutions) - 1}): ")
                )
                if 0 <= selected_index < len(resolutions):
                    return resolutions[selected_index]
                print(f"    エラー: インデックス {selected_index} は無効です")
            except (ValueError, EOFError):
                print("    入力がないため、最初の解像度を使用します")
                return resolutions[0]

    def run(self) -> None:
        if self.camera_handler is None or self.pipeline is None or self.ui_manager is None:
            raise RuntimeError("アプリケーションが初期化されていません")

        self.running = True
        print("\n=== アプリケーション開始 ===")
        print("キーボード操作: 'q'またはESCで終了、's'でフレームを保存")
        frame_count = 0

        try:
            while self.running:
                started = time.time()
                ret, frame = self.camera_handler.get_frame()
                if not ret or frame is None:
                    print("フレーム取得エラー")
                    break
                frame_time = time.time() - started

                started = time.time()
                marker_info, pose_info = self.pipeline.process_frame(frame)
                process_time = time.time() - started

                started = time.time()
                camera_frame, wireframe_frame = self.pipeline.render_output(
                    frame, marker_info, pose_info
                )
                render_time = time.time() - started

                self.ui_manager.display_frames(camera_frame, wireframe_frame)
                frame_count += 1

                if self.ui_manager.is_window_closed():
                    self.running = False
                    continue

                if frame_count % 30 == 0:
                    self.pipeline.print_info(marker_info, pose_info)
                    print(
                        f"[Performance] Frame:{frame_time * 1000:.1f}ms "
                        f"Process:{process_time * 1000:.1f}ms "
                        f"Render:{render_time * 1000:.1f}ms"
                    )

                key = cv2.waitKey(1) & 0xFF
                if key == ord("q") or key == 27:
                    self.running = False
                elif key == ord("s"):
                    cv2.imwrite(f"capture_{frame_count}.png", frame)
                    print(f"フレームを保存しました: capture_{frame_count}.png")
        except KeyboardInterrupt:
            print("\nキーボード割り込みで終了します")
        finally:
            self.cleanup()

    def cleanup(self) -> None:
        if self.ui_manager is not None:
            self.ui_manager.cleanup()
        if self.camera_handler is not None:
            self.camera_handler.release()
        cv2.destroyAllWindows()


def main() -> None:
    try:
        CameraLocalizationApp().run()
    except (FileNotFoundError, ValueError, RuntimeError) as error:
        print(f"起動エラー: {error}")


if __name__ == "__main__":
    main()
