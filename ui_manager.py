"""
UI マネージャーモジュール
2つのウィンドウ（カメラ映像 + 3D ワイヤフレーム）の管理を行います。
"""

import cv2
import numpy as np
from typing import Tuple, Dict


class UIManager:
    """2ウィンドウ表示の管理を行うクラス"""
    
    def __init__(self, camera_config: Dict, wireframe_config: Dict):
        """
        UI マネージャーを初期化します。
        
        Args:
            camera_config: カメラウィンドウの設定辞書
            wireframe_config: 3D ワイヤフレームウィンドウの設定辞書
        """
        self.camera_window_name = camera_config.get("name", "Camera Feed")
        self.wireframe_window_name = wireframe_config.get("name", "3D Wireframe")
        
        self.camera_window_pos = (camera_config.get("x_pos", 0), 
                                  camera_config.get("y_pos", 0))
        self.wireframe_window_pos = (wireframe_config.get("x_pos", 960), 
                                     wireframe_config.get("y_pos", 0))
        
        self.camera_window_size = (camera_config.get("width", 960),
                                   camera_config.get("height", 720))
        self.wireframe_window_size = (wireframe_config.get("width", 960),
                                      wireframe_config.get("height", 720))
        
        self._create_windows()
    
    def _create_windows(self):
        """ウィンドウを作成して位置を設定します。"""
        # カメラウィンドウを作成
        cv2.namedWindow(self.camera_window_name, cv2.WINDOW_AUTOSIZE)
        cv2.moveWindow(self.camera_window_name, 
                      self.camera_window_pos[0], 
                      self.camera_window_pos[1])
        
        # 3D ワイヤフレームウィンドウを作成
        cv2.namedWindow(self.wireframe_window_name, cv2.WINDOW_AUTOSIZE)
        cv2.moveWindow(self.wireframe_window_name, 
                      self.wireframe_window_pos[0], 
                      self.wireframe_window_pos[1])
        
        print(f"ウィンドウ作成完了:")
        print(f"  - {self.camera_window_name}: ({self.camera_window_pos})")
        print(f"  - {self.wireframe_window_name}: ({self.wireframe_window_pos})")
    
    def display_frames(
        self,
        camera_frame: np.ndarray,
        wireframe_frame: np.ndarray
    ):
        """
        2つのフレームを表示します。
        
        Args:
            camera_frame: カメラ映像フレーム
            wireframe_frame: 3D ワイヤフレームフレーム
        """
        # カメラフレームをリサイズして表示
        camera_resized = cv2.resize(camera_frame, self.camera_window_size)
        cv2.imshow(self.camera_window_name, camera_resized)
        
        # ワイヤフレームフレームをリサイズして表示
        wireframe_resized = cv2.resize(wireframe_frame, self.wireframe_window_size)
        cv2.imshow(self.wireframe_window_name, wireframe_resized)
    
    def add_text_overlay(
        self,
        frame: np.ndarray,
        texts: list,
        position: str = "top_left",
        bg_opacity: float = 0.7
    ) -> np.ndarray:
        """
        フレームにテキストオーバーレイを追加します。
        
        Args:
            frame: 入力フレーム
            texts: 表示するテキストのリスト
            position: テキストの配置位置 ("top_left", "top_right", "bottom_left", "bottom_right")
            bg_opacity: 背景の透明度
        
        Returns:
            np.ndarray: テキストが追加されたフレーム
        """
        result = frame.copy()
        h, w = frame.shape[:2]
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        font_thickness = 1
        line_spacing = 20
        
        # テキストの幅を計算
        text_width = 0
        text_height = len(texts) * line_spacing
        
        for text in texts:
            (tw, th), _ = cv2.getTextSize(text, font, font_scale, font_thickness)
            text_width = max(text_width, tw)
        
        # 背景矩形のパラメータを設定
        padding = 5
        bg_width = text_width + 2 * padding
        bg_height = text_height + 2 * padding
        
        if position == "top_left":
            bg_x1, bg_y1 = 5, 5
        elif position == "top_right":
            bg_x1 = w - bg_width - 5
            bg_y1 = 5
        elif position == "bottom_left":
            bg_x1 = 5
            bg_y1 = h - bg_height - 5
        else:  # bottom_right
            bg_x1 = w - bg_width - 5
            bg_y1 = h - bg_height - 5
        
        bg_x2 = bg_x1 + bg_width
        bg_y2 = bg_y1 + bg_height
        
        # 半透明背景を描画
        overlay = result.copy()
        cv2.rectangle(overlay, (bg_x1, bg_y1), (bg_x2, bg_y2), (0, 0, 0), -1)
        cv2.addWeighted(overlay, bg_opacity, result, 1 - bg_opacity, 0, result)
        
        # テキストを描画
        text_x = bg_x1 + padding
        text_y = bg_y1 + padding + 15
        
        for text in texts:
            cv2.putText(result, text, (text_x, text_y),
                       font, font_scale, (0, 255, 0), font_thickness)
            text_y += line_spacing
        
        return result
    
    def draw_debug_info(
        self,
        frame: np.ndarray,
        marker_count: int = 0,
        pose_distance: float = 0.0,
        rotation_angle: float = 0.0
    ) -> np.ndarray:
        """
        デバッグ情報をフレームに描画します。
        
        Args:
            frame: 入力フレーム
            marker_count: 検出されたマーカー数
            pose_distance: カメラとマーカー間の距離 (m)
            rotation_angle: 回転角度 (度)
        
        Returns:
            np.ndarray: デバッグ情報が描画されたフレーム
        """
        texts = [
            f"Markers: {marker_count}",
            f"Distance: {pose_distance:.3f} m",
            f"Angle: {rotation_angle:.1f} deg"
        ]
        
        return self.add_text_overlay(frame, texts, position="top_left")
    
    def is_window_closed(self) -> bool:
        """
        ウィンドウが閉じられたかを確認します。
        
        Returns:
            bool: どちらかのウィンドウが閉じられたか
        """
        # ウィンドウが存在するかを確認（存在しない = 閉じられた）
        try:
            # ウィンドウの状態を確認（簡易的な方法）
            cv2.getWindowProperty(self.camera_window_name, cv2.WND_PROP_VISIBLE)
            cv2.getWindowProperty(self.wireframe_window_name, cv2.WND_PROP_VISIBLE)
            return False
        except:
            return True
    
    def cleanup(self):
        """ウィンドウをクリーンアップして閉じます。"""
        cv2.destroyWindow(self.camera_window_name)
        cv2.destroyWindow(self.wireframe_window_name)
        print("ウィンドウをクローズしました。")
