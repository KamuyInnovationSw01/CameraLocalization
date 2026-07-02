"""
ポーズ推定モジュール
検出されたマーカーからカメラのポーズ（回転・並進）を推定します。
"""

import cv2
import numpy as np
import json
from typing import Optional, Tuple, Dict


class PoseEstimator:
    """マーカーからカメラのポーズを推定するクラス"""
    
    def __init__(self, calibration_file: str):
        """
        ポーズ推定器を初期化します。
        
        Args:
            calibration_file: キャリブレーションパラメータのJSONファイルパス
        """
        self.camera_matrix = None
        self.dist_coeffs = None
        self.image_size = None
        
        self._load_calibration(calibration_file)
    
    def _load_calibration(self, calibration_file: str):
        """
        キャリブレーションパラメータを読み込みます。
        
        Args:
            calibration_file: キャリブレーションファイルのパス
        """
        try:
            with open(calibration_file, 'r') as f:
                calib_data = json.load(f)
            
            # キャリブレーションパラメータを取得
            self.camera_matrix = np.array(calib_data["cameraMatrix"], dtype=np.float32)
            self.dist_coeffs = np.array(calib_data["distCoeffs"], dtype=np.float32).flatten()
            self.image_size = tuple(calib_data["imageSize"])
            
            print(f"キャリブレーション読み込み成功: {calibration_file}")
            print(f"カメラ行列:\n{self.camera_matrix}")
            print(f"画像サイズ: {self.image_size}")
            
        except Exception as e:
            print(f"キャリブレーション読み込みエラー: {e}")
            raise
    
    def estimate_marker_pose(
        self,
        marker_corners: np.ndarray,
        marker_size_m: float
    ) -> Tuple[bool, Optional[np.ndarray], Optional[np.ndarray]]:
        """
        単一マーカーからカメラのポーズを推定します。
        
        Args:
            marker_corners: マーカーのコーナー座標 (4, 2)
            marker_size_m: マーカーのサイズ（メートル）
        
        Returns:
            Tuple containing:
                - success: 推定が成功したかどうか
                - rvec: 回転ベクトル (3,)
                - tvec: 並進ベクトル (3,)
        """
        if self.camera_matrix is None:
            print("エラー: キャリブレーションパラメータが読み込まれていません。")
            return False, None, None
        
        # マーカーの3D座標（マーカー座標系）
        # マーカーは z=0 平面上にあると仮定
        object_points = np.array([
            [-marker_size_m / 2, -marker_size_m / 2, 0],
            [marker_size_m / 2, -marker_size_m / 2, 0],
            [marker_size_m / 2, marker_size_m / 2, 0],
            [-marker_size_m / 2, marker_size_m / 2, 0]
        ], dtype=np.float32)
        
        # 画像平面上のマーカーコーナー座標
        image_points = np.array(marker_corners).reshape(4, 2).astype(np.float32)
        
        # solvePnP でポーズを推定
        # SOLVEPNP_IPPE_SQUARE: 平面正方形マーカー専用。複数解を返すが
        # 1 番目の解は反転補正済み（カメラがマーカー前方）を保証。
        success, rvec, tvec = cv2.solvePnP(
            objectPoints=object_points,
            imagePoints=image_points,
            cameraMatrix=self.camera_matrix,
            distCoeffs=self.dist_coeffs,
            useExtrinsicGuess=False,
            flags=cv2.SOLVEPNP_IPPE_SQUARE
        )
        
        if not success:
            return False, None, None
        
        # === 座標系の補正 ===
        # (1) 平面マーカーは正面付近で反転解（カメラがマーカー裏側）を返すことがある。
        #     正しいケース：カメラの+Z方向（=R[:,2]）とtvecが反対向き（dot < 0）
        R, _ = cv2.Rodrigues(rvec)
        if np.dot(tvec.flatten(), R[:, 2]) > 0:
            tvec = -tvec
            R = R @ np.diag([1.0, 1.0, -1.0])  # Z軸反転で姿勢を正す
        # (2) 座標系統一: OpenCV規約の +Z=カメラ前方 を、
        #     本アプリのワールド座標 +Z=上（カメラがいる側）に揃える。
        #     写像 p_world → p_world_new を p' = (X, Y, -Z) とすると
        #       p_camera = R @ p_world + t
        #               = R @ diag(1,1,-1) @ p_world_new + t
        #     よって R_new = R @ diag(1,1,-1)、t_new = t。
        R = R @ np.diag([1.0, 1.0, -1.0])
        rvec, _ = cv2.Rodrigues(R)
        
        return True, rvec, tvec
    
    def get_pose_info(
        self,
        rvec: np.ndarray,
        tvec: np.ndarray
    ) -> Dict:
        """
        ポーズ情報を辞書形式で取得します。
        
        Args:
            rvec: 回転ベクトル
            tvec: 並進ベクトル
        
        Returns:
            Dict: ポーズ情報
        """
        # 回転ベクトルから回転行列を取得
        R, _ = cv2.Rodrigues(rvec)
        
        # 回転の大きさ（度数法）
        angle_rad = np.linalg.norm(rvec)
        angle_deg = np.degrees(angle_rad)
        
        # 並進の大きさ
        distance_m = np.linalg.norm(tvec)
        
        pose_info = {
            "rvec": rvec.flatten().tolist(),  # (3,)
            "tvec": tvec.flatten().tolist(),  # (3,)
            "rotation_matrix": R.tolist(),     # (3, 3)
            "rotation_angle_deg": float(angle_deg),
            "translation_distance_m": float(distance_m),
            "camera_position": tvec.flatten().tolist()  # カメラの位置 (m)
        }
        
        return pose_info
    
    def get_camera_matrix(self) -> np.ndarray:
        """カメラ行列を取得します。"""
        return self.camera_matrix.copy()
    
    def get_dist_coeffs(self) -> np.ndarray:
        """歪み係数を取得します。"""
        return self.dist_coeffs.copy()
