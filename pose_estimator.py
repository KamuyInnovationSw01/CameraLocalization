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
        # キャリブレーション読み込み前は未設定ですが、コンストラクター終了時には
        # _load_calibration()によって必ずNumPy配列へ置き換えられます。型注釈を
        # 付けて、Pylanceにも各値の実体が配列であることを伝えます。
        self.camera_matrix: Optional[np.ndarray] = None
        self.dist_coeffs: Optional[np.ndarray] = None
        self.image_size: Optional[tuple[int, int]] = None
        
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
            image_size_values = [int(value) for value in calib_data["imageSize"]]
            if len(image_size_values) != 2:
                raise ValueError("imageSizeは幅と高さの2要素で指定してください")
            self.image_size = (image_size_values[0], image_size_values[1])
            
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
        if self.camera_matrix is None or self.dist_coeffs is None:
            print("エラー: キャリブレーションパラメータが読み込まれていません。")
            return False, None, None

        # 上の条件でNoneを排除したローカル変数を使います。インスタンス属性は
        # Pylanceがメソッド途中で再代入される可能性を考慮するためです。
        camera_matrix = self.camera_matrix
        dist_coeffs = self.dist_coeffs
        
        # マーカーの3D座標（マーカー座標系）
        # ArUcoの順序: 左上(TL) -> 右上(TR) -> 右下(BR) -> 左下(BL)
        object_points = np.array([
            [-marker_size_m / 2,  marker_size_m / 2, 0],
            [ marker_size_m / 2,  marker_size_m / 2, 0],
            [ marker_size_m / 2, -marker_size_m / 2, 0],
            [-marker_size_m / 2, -marker_size_m / 2, 0]
        ], dtype=np.float32)
        
        # 画像平面上のマーカーコーナー座標
        image_points = np.array(marker_corners).reshape(4, 2).astype(np.float32)
        
        # solvePnP でポーズを推定
        # SOLVEPNP_IPPE_SQUARE は平面正方形マーカー用の姿勢推定を行う。
        # 返された rvec と tvec は同じ OpenCV 座標系の変換として扱う。
        success, rvec, tvec = cv2.solvePnP(
            objectPoints=object_points,
            imagePoints=image_points,
            cameraMatrix=camera_matrix,
            distCoeffs=dist_coeffs,
            useExtrinsicGuess=False,
            flags=cv2.SOLVEPNP_IPPE_SQUARE
        )
        
        if not success:
            return False, None, None
        
        # デバッグ出力: solvePnPから直接得られた値を表示
        print("\n--- solvePnP raw output ---")
        print(f"rvec:\n{rvec.flatten()}")
        print(f"tvec:\n{tvec.flatten()}")

        # 推定姿勢でマーカーの3Dコーナーを再投影し、入力コーナーとの差を表示する。
        projected_points, _ = cv2.projectPoints(
            objectPoints=object_points,
            rvec=rvec,
            tvec=tvec,
            cameraMatrix=camera_matrix,
            distCoeffs=dist_coeffs
        )
        projected_points = np.asarray(projected_points, dtype=np.float32)
        reprojection_errors = np.linalg.norm(
            projected_points.reshape(4, 2) - image_points,
            axis=1
        )
        print(f"再投影誤差 (pix): 平均={np.mean(reprojection_errors):.3f}, 最大={np.max(reprojection_errors):.3f}")

        # rvec と tvec は solvePnP の座標系のまま返す。
        # ここで片方だけを反転したり鏡映行列を Rodrigues 変換すると、
        # 再投影を満たさない姿勢になるため、表示用の座標変換は描画側で行う。
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
        # OpenCVの型スタブはMatLikeを返すため、NumPyの行列として明示します。
        R = np.asarray(R, dtype=np.float32)
        
        # 回転の大きさ（度数法）
        angle_rad = np.linalg.norm(rvec)
        angle_deg = np.degrees(angle_rad)
        
        # 並進の大きさ
        distance_m = np.linalg.norm(tvec)
        
        camera_position = (-R.T @ tvec).flatten()

        pose_info = {
            # 描画・再投影でそのまま使えるよう、姿勢ベクトルはNumPy配列で保持します。
            "rvec": rvec.copy(),
            "tvec": tvec.copy(),
            "rotation_matrix": R.tolist(),     # (3, 3)
            "rotation_angle_deg": float(angle_deg),
            "translation_distance_m": float(distance_m),
            "camera_position": camera_position.tolist()  # カメラの位置 (m)
        }
        
        return pose_info
    
    def get_camera_matrix(self) -> np.ndarray:
        """カメラ行列を取得します。"""
        if self.camera_matrix is None:
            raise RuntimeError("カメラ行列が読み込まれていません")
        return self.camera_matrix.copy()
    
    def get_dist_coeffs(self) -> np.ndarray:
        """歪み係数を取得します。"""
        if self.dist_coeffs is None:
            raise RuntimeError("歪み係数が読み込まれていません")
        return self.dist_coeffs.copy()

    def get_image_size(self) -> tuple[int, int]:
        """キャリブレーション時の画像サイズを(width, height)で取得します。"""
        if self.image_size is None:
            raise RuntimeError("画像サイズが読み込まれていません")
        return self.image_size
