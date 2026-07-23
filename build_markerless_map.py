"""ALIKED/LightGlueで参照画像から簡易3Dマップを生成する準備ソフトウェア。

入力YAMLのposition_mは、基準画像(ref_1)からref_2までのカメラ間距離です。
この1つの既知距離でマップの絶対スケールを決め、ref_3以降は既知3D点から
PnPで姿勢を推定します。移動方向と回転は画像対応から推定します。
"""

import argparse
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import yaml

from markerless_features import LightGlueFeatures
from pose_estimator import PoseEstimator


def _load_reference_spec(spec_file: str) -> list[dict[str, Any]]:
    """参照画像YAMLを読み込み、内部で扱いやすい形式へ正規化します。

    1枚目は基準カメラなので距離を指定せず、2枚目だけに基準カメラとの
    距離を要求します。3枚目以降の距離は、ref_1/ref_2から作った3D点を
    基準にPnPで推定できるため省略可能です。
    """
    with Path(spec_file).open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if not isinstance(data, dict) or not isinstance(data.get("reference_images"), list):
        raise ValueError("reference_images.yamlにはreference_imagesの配列が必要です")
    references = data["reference_images"]
    if len(references) < 2:
        raise ValueError("3Dマップ生成には2枚以上の参照画像が必要です")
    result = []
    for index, item in enumerate(references):
        if not isinstance(item, dict) or "file" not in item:
            raise ValueError(f"参照画像[{index}]にはfileが必要です")
        if index == 0 or index >= 2:
            distance_m = 0.0
        else:
            raw_distance = item.get("position_m", item.get("distance_m"))
            if isinstance(raw_distance, (list, tuple)):
                raise ValueError("position_mは距離の大きさを表す数値で指定してください")
            if raw_distance is None or float(raw_distance) <= 0:
                raise ValueError("ref_2には正のposition_mが必要です")
            distance_m = float(raw_distance)
        result.append({"file": str(item["file"]), "distance_m": distance_m})
    return result


def _matched_pairs(
    features: LightGlueFeatures, first: dict, current: dict
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """基準画像と現在の参照画像の対応番号・2D座標を取り出します。

    LightGlueの対応番号はキーポイント配列のインデックスです。ここでは後段の
    エッセンシャル行列推定に使うため、基準画像座標、現在画像座標、対応番号を
    同じ順序で返します。
    """
    matches = features.match(first, current)
    match_array = features.match_indices(matches["matches"])
    first_points = features.keypoints(first["keypoints"])
    current_points = features.keypoints(current["keypoints"])
    if len(match_array) == 0:
        return (
            np.empty((0, 2), np.float32),
            np.empty((0, 2), np.float32),
            np.empty((0, 2), np.int32),
        )
    return match_array, first_points[match_array[:, 0]], current_points[match_array[:, 1]]


def build_map(spec_file: str, output_file: str, calibration_file: str, device: str, max_keypoints: int) -> None:
    """複数の参照画像から基準座標系の簡易3Dマップを生成します。

    画像ペアごとに次の処理を行います。

    1. ALIKED特徴をLightGlueで対応付ける。
    2. ref_2ではエッセンシャル行列から相対姿勢を復元し、既知距離でスケールする。
    3. ref_3以降では、既存3D点と現在画像の対応点からPnPで姿勢を推定する。
    4. 各画像の新しい対応点を三角測量し、3Dマップへ追加する。

    エッセンシャル行列だけでは移動量の絶対スケールを得られないため、ref_2の
    既知距離で最初の3Dマップを実寸化します。その後はこの3Dマップを基準にする
    ため、ref_3以降の距離入力は不要です。
    """
    references = _load_reference_spec(spec_file)
    pose_estimator = PoseEstimator(calibration_file)
    camera_matrix = pose_estimator.get_camera_matrix().astype(np.float64)
    dist_coeffs = pose_estimator.get_dist_coeffs().astype(np.float64)
    features = LightGlueFeatures(device=device, max_keypoints=max_keypoints)

    # すべての3D点を基準画像1枚目のカメラ座標系へ集約します。
    first_features, first_image = features.extract_file(references[0]["file"])
    anchor_keypoints = features.keypoints(first_features["keypoints"])
    anchor_descriptors = features.remove_batch_dimension(first_features["descriptors"])

    point_sums = np.zeros((len(anchor_keypoints), 3), dtype=np.float64)
    point_counts = np.zeros(len(anchor_keypoints), dtype=np.int32)
    for reference_index, reference in enumerate(references[1:], start=1):
        current_features, _ = features.extract_file(reference["file"])
        match_array, points0, points1 = _matched_pairs(features, first_features, current_features)
        if len(points0) < 8:
            raise RuntimeError(f"対応点が不足しています: {reference['file']} ({len(points0)}点)")

        if reference_index == 1:
            # 初回の2視点だけは3D点がまだないため、エッセンシャル行列を使います。
            # recoverPoseの並進は方向しか持たないので、ref_2の既知距離で実寸化します。
            essential, mask = cv2.findEssentialMat(
                points0, points1, camera_matrix, method=cv2.RANSAC, prob=0.999, threshold=1.0
            )
            if essential is None:
                raise RuntimeError(f"エッセンシャル行列を推定できません: {reference['file']}")
            _, rotation, translation, pose_mask = cv2.recoverPose(
                essential, points0, points1, camera_matrix, mask=mask
            )
            rotation = np.asarray(rotation, dtype=np.float64)
            translation = np.asarray(translation, dtype=np.float64).reshape(3)
            pose_mask = np.asarray(pose_mask, dtype=np.int32)
            translation_norm = np.linalg.norm(translation)
            if translation_norm < 1e-8:
                raise RuntimeError(f"並進方向を推定できません（純粋な回転の可能性）: {reference['file']}")
            translation = translation / translation_norm * reference["distance_m"]
        else:
            # 3枚目以降はref_1の既知3D点を使うため、距離の指定なしでメートル単位の
            # 姿勢を推定できます。未知点は後段でこの姿勢を使って三角測量します。
            known = point_counts[match_array[:, 0].astype(np.int32)] > 0
            if int(known.sum()) < 6:
                raise RuntimeError(
                    f"既知3D点との対応が不足しています: {reference['file']} ({int(known.sum())}点)"
                )
            known_points3d = point_sums[match_array[known, 0].astype(np.int32)] / point_counts[
                match_array[known, 0].astype(np.int32), None
            ]
            success, rvec, translation, inliers = cv2.solvePnPRansac(
                objectPoints=known_points3d.astype(np.float32),
                imagePoints=points1[known].astype(np.float32),
                cameraMatrix=camera_matrix,
                distCoeffs=dist_coeffs,
                iterationsCount=100,
                reprojectionError=3.0,
                confidence=0.99,
                flags=cv2.SOLVEPNP_ITERATIVE,
            )
            if not success or inliers is None or len(inliers) < 6:
                raise RuntimeError(f"既知3D点から姿勢を推定できません: {reference['file']}")
            rotation, _ = cv2.Rodrigues(rvec)
            rotation = np.asarray(rotation, dtype=np.float64)
            translation = np.asarray(translation, dtype=np.float64).reshape(3)
            pose_mask = np.ones(len(points0), dtype=np.int32)

        # OpenCVの投影式 x = K [R|t] X に合わせて、2視点の投影行列を作ります。
        projection0 = camera_matrix @ np.hstack((np.eye(3), np.zeros((3, 1))))
        projection1 = camera_matrix @ np.hstack((rotation, translation.reshape(3, 1)))
        homogeneous = cv2.triangulatePoints(projection0, projection1, points0.T, points1.T)
        points3d = (homogeneous[:3] / homogeneous[3]).T
        depths0 = points3d[:, 2]
        depths1 = (rotation @ points3d.T + translation.reshape(3, 1))[2]
        # 三角測量点が両カメラの前方にあること、数値が有限であることを確認します。
        valid = (
            (pose_mask.reshape(-1) > 0)
            & (depths0 > 0)
            & (depths1 > 0)
            & np.isfinite(points3d).all(axis=1)
        )
        if int(valid.sum()) < 8:
            raise RuntimeError(f"有効な3D点が不足しています: {reference['file']} ({int(valid.sum())}点)")

        # 同じ基準キーポイントが複数の参照画像で復元された場合は平均化します。
        for match, point, is_valid in zip(match_array, points3d, valid):
            if is_valid:
                anchor_index = int(match[0])
                point_sums[anchor_index] += point
                point_counts[anchor_index] += 1
        print(f"3D復元: {reference['file']} 対応点={len(points0)}, 有効点={int(valid.sum())}")

    valid_anchor = point_counts > 0
    if int(valid_anchor.sum()) < 8:
        raise RuntimeError(f"最終的な3D点が不足しています: {int(valid_anchor.sum())}点")
    # 複数視点で観測された基準キーポイントだけをマップへ保存します。
    map_points = point_sums[valid_anchor] / point_counts[valid_anchor, None]
    np.savez_compressed(
        output_file,
        keypoints=anchor_keypoints[valid_anchor].astype(np.float32),
        descriptors=anchor_descriptors[valid_anchor].astype(np.float32),
        points3d=map_points.astype(np.float32),
        camera_matrix=camera_matrix.astype(np.float32),
        image_size=np.array([first_image.shape[1], first_image.shape[0]], dtype=np.int32),
        reference_count=np.array(len(references), dtype=np.int32),
    )
    print(f"マーカーレス3Dマップを保存しました: {output_file} ({len(map_points)}点)")


def main() -> None:
    parser = argparse.ArgumentParser(description="参照画像からマーカーレス簡易3Dマップを生成します")
    parser.add_argument("spec_file", help="参照画像仕様YAML")
    parser.add_argument("--output", default="markerless_map.npz")
    parser.add_argument("--calibration", default="eMeetNova.json")
    parser.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    parser.add_argument("--max-keypoints", type=int, default=2048)
    args = parser.parse_args()
    build_map(args.spec_file, args.output, args.calibration, args.device, args.max_keypoints)


if __name__ == "__main__":
    main()
