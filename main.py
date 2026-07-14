"""
メインアプリケーション
USB カメラでARマーカーを撮影し、カメラのポーズをワイヤフレーム3Dで表示します。
"""

import cv2
import yaml
import os
import sys
import numpy as np
from typing import Tuple, Optional

from camera_handler import CameraHandler
from marker_detector import MarkerDetector
from pose_estimator import PoseEstimator
from wireframe_renderer import WireframeRenderer
from ui_manager import UIManager


class CameraLocalizationApp:
    """カメラローカライゼーションアプリケーション"""
    
    def __init__(self, config_file: str = "config.yaml"):
        """
        アプリケーションを初期化します。
        
        Args:
            config_file: 設定ファイルのパス
        """
        self.config = self._load_config(config_file)
        self.running = False
        
        # 各モジュールを初期化
        self.camera_handler = None
        self.marker_detector = None
        self.pose_estimator = None
        self.wireframe_renderer = None
        self.ui_manager = None
        
        self._initialize_modules()
    
    def _load_config(self, config_file: str) -> dict:
        """
        設定ファイルを読み込みます。
        
        Args:
            config_file: 設定ファイルのパス
        
        Returns:
            dict: 設定情報
        """
        if not os.path.exists(config_file):
            print(f"エラー: 設定ファイル {config_file} が見つかりません。")
            sys.exit(1)
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        print(f"設定ファイルを読み込みました: {config_file}")
        return config
    
    def _initialize_modules(self):
        """各モジュールを初期化します。"""
        import threading
        import time
        
        print("\n=== モジュール初期化開始 ===")
        
        # 1. カメラハンドラー
        print("\n[1] カメラハンドラーを初期化中...")
        print("    カメラを検出中...(最初のカメラを使用します)")
        
        # バックグラウンドでカメラリストを取得
        camera_info_list = [None]  # 初期値
        detection_complete = threading.Event()
        
        def detect_cameras():
            camera_info_list[0] = CameraHandler.get_camera_info_list()
            detection_complete.set()
        
        detect_thread = threading.Thread(target=detect_cameras, daemon=True)
        detect_thread.start()
        
        # カメラ検出待機（タイムアウト 15秒、進捗表示）
        elapsed = 0
        print("    ", end="", flush=True)
        while elapsed < 15:
            if detection_complete.wait(timeout=0.5):
                break
            elapsed += 0.5
            if int(elapsed) % 2 == 0:
                print(".", end="", flush=True)
        
        print()
        
        camera_info_list = camera_info_list[0]
        
        if not camera_info_list:
            print("エラー: 利用可能なカメラが見つかりません。")
            sys.exit(1)
        
        # カメラIDを選択
        if len(camera_info_list) == 1:
            camera_id = camera_info_list[0]['id']
            info = camera_info_list[0]
            print(f"    [OK] カメラ {camera_id} ({info['name']}) を使用します: {info['width']}x{info['height']}@{info['fps']:.1f}fps")
        else:
            print(f"\n    利用可能なカメラ:")
            for i, info in enumerate(camera_info_list):
                print(f"      [{i}] カメラID {info['id']:d} - {info['name']} ({info['width']:d}x{info['height']:d} @ {info['fps']:.1f}fps)")
            
            camera_id = None
            while camera_id is None:
                try:
                    user_input = input(f"\n    使用するカメラを選択してください (0-{len(camera_info_list)-1}): ")
                    selected_index = int(user_input)
                    if 0 <= selected_index < len(camera_info_list):
                        camera_id = camera_info_list[selected_index]['id']
                    else:
                        print(f"    エラー: インデックス {selected_index} は無効です")
                except (ValueError, EOFError) as e:
                    if isinstance(e, EOFError):
                        # デフォルト: 最初のカメラ
                        camera_id = camera_info_list[0]['id']
                        print(f"    (入力がないため、最初のカメラ {camera_id} を使用します)")
                    else:
                        print("    エラー: 数値を入力してください")
        
        # 解像度選択
        print(f"\n    [カメラ {camera_id} の利用可能な解像度を検索中...]")
        available_resolutions = CameraHandler.get_available_resolutions(camera_id)
        
        selected_width = None
        selected_height = None
        
        if available_resolutions:
            print(f"\n    利用可能な解像度（{len(available_resolutions)} 個）:")
            for i, (width, height) in enumerate(available_resolutions):
                print(f"      [{i}] {width}x{height}")
            
            resolution_index = None
            while resolution_index is None:
                try:
                    user_input = input(f"\n    使用する解像度を選択してください (0-{len(available_resolutions)-1}): ")
                    resolution_index = int(user_input)
                    if not (0 <= resolution_index < len(available_resolutions)):
                        print(f"    エラー: インデックス {resolution_index} は無効です")
                        resolution_index = None
                except (ValueError, EOFError) as e:
                    if isinstance(e, EOFError):
                        # デフォルト: 最初の解像度
                        resolution_index = 0
                        print(f"    (入力がないため、最初の解像度を使用します)")
                    else:
                        print("    エラー: 数値を入力してください")
            
            selected_width, selected_height = available_resolutions[resolution_index]
            print(f"    [OK] 解像度を選択: {selected_width}x{selected_height}")
        else:
            print("    警告: 利用可能な解像度が取得できません。デフォルト設定を使用します。")
        
        # カメラ初期化
        self.camera_handler = CameraHandler(
            camera_id=camera_id,
            width=selected_width,
            height=selected_height
        )
        if not self.camera_handler.initialize():
            print(f"    エラー: カメラ {camera_id} 初期化に失敗しました。")
            sys.exit(1)
        
        # 2. マーカー検出器
        print("\n[2] マーカー検出器を初期化中...")
        marker_dict = self.config['marker']['dictionary']
        self.marker_detector = MarkerDetector(dictionary_name=marker_dict)
        print(f"    [OK] マーカー検出器を初期化しました（辞書: {marker_dict}）")
        
        # 3. ポーズ推定器
        print("\n[3] ポーズ推定器を初期化中...")
        calib_file = self.config['calibration']['parameters_file']
        try:
            self.pose_estimator = PoseEstimator(calib_file)
            print(f"    [OK] ポーズ推定器を初期化しました")
        except Exception as e:
            print(f"    エラー: ポーズ推定器初期化に失敗しました: {e}")
            sys.exit(1)
        
        # 4. ワイヤフレーム描画器
        print("\n[4] ワイヤフレーム描画器を初期化中...")
        camera_matrix = self.pose_estimator.get_camera_matrix()
        wireframe_scale = self.config['processing']['wireframe_scale']
        self.wireframe_renderer = WireframeRenderer(
            camera_matrix=camera_matrix,
            wireframe_scale=wireframe_scale
        )
        print(f"    [OK] ワイヤフレーム描画器を初期化しました")
        
        # 5. UI マネージャー
        print("\n[5] UI マネージャーを初期化中...")
        self.ui_manager = UIManager(
            camera_config=self.config['ui']['camera_window'],
            wireframe_config=self.config['ui']['wireframe_window']
        )
        print(f"    [OK] UI マネージャーを初期化しました")
        
        print("\n=== モジュール初期化完了 ===\n")
    
    def process_frame(self, frame) -> Tuple[Optional[dict], Optional[dict]]:
        """
        フレームを処理してマーカー検出とポーズ推定を行います。
        
        Args:
            frame: 入力フレーム
        
        Returns:
            Tuple containing:
                - marker_info: マーカー情報
                - pose_info: ポーズ情報
        """
        # マーカー検出
        corners, ids, rejected = self.marker_detector.detect_markers(frame)
        
        marker_size_m = self.config['marker']['size_m']
        marker_info = self.marker_detector.get_marker_info(corners, ids, marker_size_m)
        
        # corner と ids を marker_info に追加（後の処理用）
        marker_info['corners'] = corners
        marker_info['ids'] = ids
        
        pose_info = None
        
        # マーカーが検出された場合、ポーズを推定
        if marker_info['detected'] and len(marker_info['markers']) > 0:
            # 最初のマーカーを使用
            marker = marker_info['markers'][0]
            marker_corners = marker['corners']
            
            success, rvec, tvec = self.pose_estimator.estimate_marker_pose(
                marker_corners=marker_corners,
                marker_size_m=marker_size_m
            )
            
            if success:
                pose_info = self.pose_estimator.get_pose_info(rvec, tvec)
                pose_info['rvec'] = rvec  # OpenCV形式で保存
                pose_info['tvec'] = tvec
        
        return marker_info, pose_info
    
    def render_output(
        self,
        frame: np.ndarray,
        marker_info: dict,
        pose_info: Optional[dict]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        出力フレームをレンダリングします。
        
        Args:
            frame: 入力フレーム
            marker_info: マーカー情報
            pose_info: ポーズ情報
        
        Returns:
            Tuple containing:
                - camera_frame: 描画されたカメラフレーム（マーカーのみ）
                - wireframe_frame: 3D ワイヤフレームフレーム（マーカー + 座標軸）
        """
        # 左ウィンドウ：カメラフレーム + マーカー検出結果のみ
        camera_frame = self.marker_detector.draw_detected_markers(
            frame,
            marker_info.get('corners') if marker_info['detected'] else None,
            marker_info.get('ids') if marker_info['detected'] else None
        )
        
        # 右ウィンドウ：3D ビュー（ワイヤフレーム + マーカー + 座標軸）
        wireframe_frame = np.full(
            (self.ui_manager.wireframe_window_size[1],
             self.ui_manager.wireframe_window_size[0], 3),
            50, dtype=np.uint8
        )
        
        # ポーズが推定できた場合、3D ビューを描画
        # パフォーマンス最適化：draw_enable フラグで制御
        enable_3d_render = self.config.get('debug', {}).get('enable_3d_render', True)
        
        if pose_info is not None and enable_3d_render:
            render_mode = self.config.get('debug', {}).get('render_mode', 'opencv').lower()
            marker_size_m = self.config['marker']['size_m']
            
            if render_mode == 'matplotlib':
                try:
                    wireframe_frame = self.wireframe_renderer.draw_3d_view_matplotlib(
                        rvec=pose_info['rvec'],
                        tvec=pose_info['tvec'],
                        marker_size_m=marker_size_m
                    )
                except Exception as e:
                    print(f"⚠ matplotlibでの3D ビュー描画エラー: {e}。OpenCVモードにフォールバックします。")
                    # エラーが発生した場合、自動的に高速な OpenCV 描画にフォールバック
                    try:
                        wireframe_frame = self.wireframe_renderer.draw_3d_view(
                            rvec=pose_info['rvec'],
                            tvec=pose_info['tvec'],
                            marker_size_m=marker_size_m
                        )
                    except Exception as fe:
                        print(f"⚠ フォールバック（OpenCV）描画エラー: {fe}")
            else:  # opencv モード、またはデフォルト
                try:
                    wireframe_frame = self.wireframe_renderer.draw_3d_view(
                        rvec=pose_info['rvec'],
                        tvec=pose_info['tvec'],
                        marker_size_m=marker_size_m
                    )
                except Exception as e:
                    print(f"⚠ OpenCVでの3D ビュー描画エラー: {e}")
        
        # デバッグ情報をカメラフレームに追加
        if self.config['debug']['show_marker_info']:
            marker_count = marker_info.get('count', 0)
            camera_frame = self.ui_manager.draw_debug_info(
                camera_frame,
                marker_count=marker_count,
                pose_distance=pose_info.get('translation_distance_m', 0) if pose_info else 0,
                rotation_angle=pose_info.get('rotation_angle_deg', 0) if pose_info else 0
            )
        
        return camera_frame, wireframe_frame
    
    def print_info(self, marker_info: dict, pose_info: Optional[dict]):
        """
        ターミナルに情報を出力します。
        
        Args:
            marker_info: マーカー情報
            pose_info: ポーズ情報
        """
        if self.config['debug']['show_marker_info']:
            if marker_info['detected']:
                print(f"\n検出されたマーカー: {marker_info['count']} 個")
                for marker in marker_info['markers']:
                    print(f"  - ID: {marker['id']}, 中心: ({marker['center'][0]:.1f}, {marker['center'][1]:.1f})")
            else:
                print("\nマーカーが検出されていません。")
        
        if self.config['debug']['show_pose_info'] and pose_info is not None:
            print(f"ポーズ情報:")
            print(f"  - 距離: {pose_info['translation_distance_m']:.3f} m")
            print(f"  - 回転角: {pose_info['rotation_angle_deg']:.1f} deg")
            print(f"  - カメラ位置: ({pose_info['camera_position'][0]:.3f}, {pose_info['camera_position'][1]:.3f}, {pose_info['camera_position'][2]:.3f})")
    
    def run(self):
        """メインループを実行します。"""
        import time
        
        self.running = True
        print("\n=== アプリケーション開始 ===")
        print("キーボード操作:")
        print("  - 'q' or 'ESC': 終了")
        print("  - 's': フレームをキャプチャ")
        print()
        
        frame_count = 0
        
        try:
            while self.running:
                # フレーム取得
                t_start = time.time()
                ret, frame = self.camera_handler.get_frame()
                if not ret:
                    print("フレーム取得エラー")
                    break
                t_frame = time.time() - t_start
                
                # フレーム処理
                t_start = time.time()
                marker_info, pose_info = self.process_frame(frame)
                t_process = time.time() - t_start
                
                # 出力フレームのレンダリング
                t_start = time.time()
                camera_frame, wireframe_frame = self.render_output(
                    frame, marker_info, pose_info
                )
                t_render = time.time() - t_start
                
                # 表示
                t_start = time.time()
                self.ui_manager.display_frames(camera_frame, wireframe_frame)
                t_display = time.time() - t_start
                
                # ターミナルに情報を出力（フレーム数を制限して出力）
                if frame_count % 30 == 0:  # 30フレームごと
                    self.print_info(marker_info, pose_info)
                    print(f"[Performance] Frame:{t_frame*1000:.1f}ms Process:{t_process*1000:.1f}ms Render:{t_render*1000:.1f}ms Display:{t_display*1000:.1f}ms")
                
                frame_count += 1
                
                # キー入力を処理
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:  # 'q' or ESC
                    print("\n終了します...")
                    self.running = False
                elif key == ord('s'):
                    cv2.imwrite(f"capture_{frame_count}.png", frame)
                    print(f"フレームをキャプチャしました: capture_{frame_count}.png")
                
        except KeyboardInterrupt:
            print("\n\nキーボード割り込みで終了します...")
            self.running = False
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """アプリケーションをクリーンアップします。"""
        print("\n=== クリーンアップ中 ===")
        
        if self.ui_manager:
            self.ui_manager.cleanup()
        
        if self.camera_handler:
            self.camera_handler.release()
        
        cv2.destroyAllWindows()
        print("=== アプリケーション終了 ===\n")


def main():
    """メイン関数"""
    # アプリケーションを作成
    app = CameraLocalizationApp(config_file="config.yaml")
    
    # メインループを実行
    app.run()


if __name__ == "__main__":
    main()
