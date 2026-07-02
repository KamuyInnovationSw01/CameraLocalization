"""
ARマーカー検出モジュール
OpenCV ArUco を使用してマーカーを検出します。
"""

import cv2
import numpy as np
from typing import Optional, Tuple, Dict, List


class MarkerDetector:
    """ArUco マーカーの検出を行うクラス"""
    
    # ArUco 辞書の定義
    DICTIONARY_MAP = {
        "DICT_4X4_50": cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50),
        "DICT_5X5_100": cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_5X5_100),
        "DICT_6X6_250": cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250),
        "DICT_ARUCO_ORIGINAL": cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_ARUCO_ORIGINAL),
    }
    
    def __init__(self, dictionary_name: str = "DICT_4X4_50"):
        """
        マーカー検出器を初期化します。
        
        Args:
            dictionary_name: 使用する ArUco 辞書の名前
        """
        self.dictionary_name = dictionary_name
        self.dictionary = self.DICTIONARY_MAP.get(
            dictionary_name,
            self.DICTIONARY_MAP["DICT_4X4_50"]
        )
        # ArUco 検出器を作成
        self.detector = cv2.aruco.ArucoDetector(self.dictionary)
        
        print(f"マーカー検出器初期化: {dictionary_name}")
    
    def detect_markers(
        self, 
        frame: np.ndarray
    ) -> Tuple[Optional[np.ndarray], Optional[List[int]], Optional[np.ndarray]]:
        """
        フレーム内のマーカーを検出します。
        
        Args:
            frame: 入力画像（BGR）
        
        Returns:
            Tuple containing:
                - corners: 検出されたマーカーのコーナー座標 (N, 4, 2)
                - ids: マーカーID (N,)
                - rejected: 検出されなかった候補 (M, 4, 2)
        """
        # グレースケールに変換
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # マーカーを検出
        corners, ids, rejected = self.detector.detectMarkers(gray)
        
        # ID があることを確認
        if ids is not None:
            ids = ids.flatten()
        
        return corners, ids, rejected
    
    def get_marker_info(
        self,
        corners: Optional[np.ndarray],
        ids: Optional[np.ndarray],
        marker_size_m: float
    ) -> Dict:
        """
        検出されたマーカーの情報を取得します。
        
        Args:
            corners: マーカーのコーナー座標
            ids: マーカーID
            marker_size_m: マーカーのサイズ（メートル）
        
        Returns:
            Dict: マーカー情報の辞書
        """
        info = {
            "detected": False,
            "count": 0,
            "markers": []
        }
        
        if corners is None or ids is None:
            return info
        
        info["detected"] = True
        info["count"] = len(ids)
        
        # 各マーカーの情報を取得
        for i, (corner, marker_id) in enumerate(zip(corners, ids)):
            corner = corner[0]  # (4, 2) に変換
            
            # マーカーの中心座標
            center_x = np.mean(corner[:, 0])
            center_y = np.mean(corner[:, 1])
            
            # マーカーの回転角（最初の辺との角度）
            edge_vector = corner[1] - corner[0]
            angle = np.arctan2(edge_vector[1], edge_vector[0])
            angle_deg = np.degrees(angle)
            
            marker_info = {
                "id": int(marker_id),
                "center": (float(center_x), float(center_y)),
                "corners": corner.tolist(),
                "angle_deg": float(angle_deg),
                "size_m": marker_size_m
            }
            
            info["markers"].append(marker_info)
        
        return info
    
    def draw_detected_markers(
        self,
        frame: np.ndarray,
        corners: Optional[np.ndarray],
        ids: Optional[np.ndarray]
    ) -> np.ndarray:
        """
        検出されたマーカーをフレームに描画します。
        
        Args:
            frame: 入力画像
            corners: マーカーのコーナー座標
            ids: マーカーID
        
        Returns:
            np.ndarray: マーカーが描画された画像
        """
        result = frame.copy()
        
        if corners is None or ids is None:
            return result
        
        # マーカーを描画
        result = cv2.aruco.drawDetectedMarkers(result, corners, ids)
        
        # マーカーIDと中心座標を描画
        for corner, marker_id in zip(corners, ids):
            corner = corner[0]
            center_x = int(np.mean(corner[:, 0]))
            center_y = int(np.mean(corner[:, 1]))
            
            # マーカーIDをテキストで表示
            cv2.putText(
                result,
                f"ID: {marker_id}",
                (center_x - 30, center_y - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )
        
        return result
