"""保存済み簡易3Dマップを使ったリアルタイムカメラローカライザー。"""

from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from markerless_features import LightGlueFeatures


class MarkerlessLocalizer:
    """ALIKED/LightGlue対応点からカメラの6DoF姿勢を推定します。

    保存マップの3D点は、参照画像1枚目のOpenCVカメラ座標系にあります。
    そのためsolvePnPの結果も同じ基準座標系で表され、カメラ位置は
    ``-R.T @ tvec``で求めます。
    """

    def __init__(
        self,
        map_file: str,
        device: str = "auto",
        max_keypoints: int = 2048,
        min_matches: int = 30,
        min_inliers: int = 15,
    ):
        """保存済みマップと推定条件を読み込みます。

        Args:
            map_file: ``build_markerless_map.py``が生成したNPZファイル。
            device: ALIKEDとLightGlueを実行するデバイス。
            max_keypoints: 現在フレームから抽出する最大特徴点数。
            min_matches: PnPを試行するために必要なLightGlue対応点数。
            min_inliers: 姿勢を有効と判定するRANSACインライア数。
        """
        if not Path(map_file).exists():
            raise FileNotFoundError(f"マーカーレス3Dマップが見つかりません: {map_file}")
        # NPZ内の3D点、基準画像特徴、カメラ内部パラメータを読み込みます。
        data = np.load(map_file)
        self.map_keypoints = np.asarray(data["keypoints"], dtype=np.float32)
        self.descriptors = np.asarray(data["descriptors"], dtype=np.float32)
        self.points3d = np.asarray(data["points3d"], dtype=np.float32)
        self.camera_matrix = np.asarray(data["camera_matrix"], dtype=np.float32)
        # マップの3D点は歪み補正済みのピンホール投影として扱います。
        self.zero_dist_coeffs = np.zeros(5, dtype=np.float32)
        self.image_size = tuple(np.asarray(data["image_size"], dtype=np.int32).tolist())
        if len(self.points3d) < 8 or len(self.points3d) != len(self.descriptors):
            raise ValueError("マーカーレス3Dマップの特徴量と3D点の数が一致しません")

        self.features = LightGlueFeatures(device=device, max_keypoints=max_keypoints)
        torch = self.features.torch
        # LightGlueは入力特徴をTorch Tensorで受け取るため、保存済みNumPy配列を
        # モデルと同じデバイスへ移します。バッチ次元は1を追加します。
        self.map_features = {
            "keypoints": torch.from_numpy(self.map_keypoints)[None].to(self.features.device),
            "descriptors": torch.from_numpy(self.descriptors)[None].to(self.features.device),
            "image_size": torch.tensor(self.image_size, device=self.features.device)[None],
        }
        self.min_matches = min_matches
        self.min_inliers = min_inliers
        print(f"マーカーレス3Dマップを読み込みました: {map_file} ({len(self.points3d)}点)")

    def estimate_pose(self, frame: np.ndarray) -> tuple[dict, Optional[dict]]:
        """現在フレームをマップへ対応付け、姿勢を返します。

        対応点が少ない場合やPnPのインライアが不足する場合は、誤った姿勢を
        返さず ``pose_info=None`` とします。戻り値の1つ目は画面表示用の対応点
        統計、2つ目は成功時だけ生成される姿勢情報です。
        """
        current_features = self.features.extract(frame)
        matches = self.features.match(self.map_features, current_features)
        match_array = self.features.match_indices(matches["matches"])
        current_keypoints = self.features.keypoints(current_features["keypoints"])

        # 現在フレーム上の対応点は、姿勢推定の成否に関係なく表示できるように
        # match_infoへ保存します。座標はLightGlueのキーポイント番号から復元します。
        matched_image_points = (
            current_keypoints[match_array[:, 1].astype(np.int64)]
            if len(match_array) > 0
            else np.empty((0, 2), dtype=np.float32)
        )

        # 対応番号を使って、保存済み3D点と現在フレームの2D点を同じ順序で作ります。
        match_info = {
            "detected": len(match_array) >= self.min_matches,
            "count": int(len(match_array)),
            "matched_points": matched_image_points,
            "inlier_indices": np.empty((0,), dtype=np.int64),
            # 3Dビューではマップ全体を表示し、現在フレームと対応した点だけを
            # 対応状態に応じて色付けします。BGR順で灰・黄・赤・緑を保持します。
            "map_points": self.points3d.copy(),
            "map_point_colors": np.tile(
                np.array([[150, 150, 150]], dtype=np.uint8), (len(self.points3d), 1)
            ),
        }
        matched_map_indices = match_array[:, 0].astype(np.int64)
        match_info["map_point_colors"][matched_map_indices] = (0, 255, 255)
        pose_info = None
        if len(match_array) < self.min_matches:
            return match_info, pose_info

        object_points = self.points3d[match_array[:, 0].astype(np.int32)]
        image_points = current_keypoints[match_array[:, 1].astype(np.int32)]
        # 外れ値を含む特徴対応からでも姿勢を推定できるよう、RANSAC付きPnPを使います。
        success, rvec, tvec, inliers = cv2.solvePnPRansac(
            objectPoints=object_points,
            imagePoints=image_points,
            cameraMatrix=self.camera_matrix,
            distCoeffs=self.zero_dist_coeffs,
            iterationsCount=100,
            reprojectionError=3.0,
            confidence=0.99,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )
        inlier_count = 0 if inliers is None else len(inliers)
        match_info["inliers"] = inlier_count
        if inliers is not None:
            # solvePnPRansacのinliersはmatch_array内の行番号です。
            match_info["inlier_indices"] = np.asarray(inliers, dtype=np.int64).reshape(-1)
            inlier_set = set(match_info["inlier_indices"].tolist())
            for match_index, map_index in enumerate(matched_map_indices):
                match_info["map_point_colors"][map_index] = (
                    (0, 255, 0) if match_index in inlier_set else (0, 0, 255)
                )
        if not success or inliers is None or inlier_count < self.min_inliers:
            return match_info, pose_info

        # solvePnPは「3Dマップ座標 -> 現在カメラ座標」の変換を返します。
        # カメラ中心を基準座標系へ戻すには、回転の転置と並進の反転が必要です。
        rotation, _ = cv2.Rodrigues(rvec)
        camera_position = (-rotation.T @ tvec).reshape(3)
        # インライアだけを再投影し、推定結果の画素誤差を品質指標として保存します。
        inlier_indices = np.asarray(inliers, dtype=np.int64)
        projected, _ = cv2.projectPoints(
            object_points[inlier_indices[:, 0]],
            rvec,
            tvec,
            self.camera_matrix,
            self.zero_dist_coeffs,
        )
        reprojection = np.linalg.norm(
            projected.reshape(-1, 2) - image_points[inlier_indices[:, 0]], axis=1
        )
        pose_info = {
            "rvec": rvec,
            "tvec": tvec,
            "rotation_matrix": rotation,
            "camera_position": camera_position,
            "translation_distance_m": float(np.linalg.norm(tvec)),
            "rotation_angle_deg": float(np.degrees(np.linalg.norm(rvec))),
            "reprojection_error_px": float(np.mean(reprojection)),
        }
        return match_info, pose_info
