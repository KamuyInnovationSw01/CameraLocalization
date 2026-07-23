"""ALIKEDとLightGlueの遅延ロードおよび画像特徴処理。"""

from pathlib import Path
from typing import Any

import cv2
import numpy as np


class LightGlueFeatures:
    """ALIKED特徴抽出器とLightGlueマッチャーをまとめた遅延初期化ラッパー。

    PyTorchとLightGlueはArUco方式では不要なため、コンストラクター内で遅延して
    importします。これにより、既存のマーカー方式はマーカーレス用依存関係が
    未インストールでも起動できます。
    """

    def __init__(self, device: str = "auto", max_keypoints: int = 2048):
        """特徴処理モデルを指定デバイスへ配置します。

        Args:
            device: ``auto``はCUDAが利用可能ならCUDA、そうでなければCPUを使います。
                ``cuda``はCUDAを必須とし、利用できない場合はエラーにします。
            max_keypoints: 1画像から抽出する最大特徴点数。多いほど対応の余地が
                増えますが、GPUメモリと処理時間も増加します。
        """
        try:
            import torch
            from lightglue import ALIKED, LightGlue
        except ImportError as error:
            raise RuntimeError(
                "マーカーレス方式にはlightglueとPyTorchが必要です。"
                "requirements.txtをインストールしてください。"
            ) from error

        if device not in {"auto", "cuda", "cpu"}:
            raise ValueError("markerless.deviceはauto、cuda、cpuのいずれかを指定してください")
        if device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("markerless.device=cudaですが、CUDA対応GPUが利用できません")

        # モデルと入力テンソルを同じデバイスへ配置します。autoでは実行環境に
        # 応じてCUDAを優先しますが、CPU環境でも同じコードを実行できます。
        self.torch = torch
        self.device = torch.device(
            "cuda" if device == "cuda" or (device == "auto" and torch.cuda.is_available()) else "cpu"
        )
        # eval()で推論モードのモデルにし、各フレームで学習用の重み更新を行わない
        # ようにします。inference_mode()は各メソッド内で適用します。
        self.extractor = ALIKED(max_num_keypoints=max_keypoints).eval().to(self.device)
        self.matcher = LightGlue(features="aliked").eval().to(self.device)
        print(f"マーカーレス特徴処理を初期化しました: ALIKED + LightGlue ({self.device})")

    def extract(self, image: np.ndarray) -> dict[str, Any]:
        """BGR画像からALIKED特徴を抽出します。

        OpenCVはBGR、ALIKEDはRGBのテンソルを想定するため、変換してから
        ``[C, H, W]``形式・0から1の範囲へ整えます。
        """
        if image is None or image.size == 0:
            raise ValueError("特徴抽出対象の画像が空です")
        # OpenCVの画像形式とニューラルネットワークの入力形式を合わせます。
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        tensor = self.torch.from_numpy(rgb).float().permute(2, 0, 1) / 255.0
        with self.torch.inference_mode():
            return self.extractor.extract(tensor.to(self.device))

    def extract_file(self, image_file: str | Path) -> tuple[dict[str, Any], np.ndarray]:
        """画像ファイルを読み込み、特徴量と元画像を返します。

        元画像は参照画像のサイズ保存に使用するため、特徴量と一緒に返します。
        """
        image = cv2.imread(str(image_file), cv2.IMREAD_COLOR)
        if image is None:
            raise FileNotFoundError(f"参照画像を読み込めません: {image_file}")
        return self.extract(image), image

    def match(self, features0: dict[str, Any], features1: dict[str, Any]) -> dict[str, Any]:
        """2画像の特徴量をLightGlueで対応付けます。

        戻り値の ``matches`` は、通常「画像0のキーポイント番号」と「画像1の
        キーポイント番号」の組です。後段でこの番号を各画像の座標へ変換します。
        """
        with self.torch.inference_mode():
            return self.matcher({"image0": features0, "image1": features1})

    @staticmethod
    def to_numpy(value: Any) -> np.ndarray:
        """LightGlueのTensorまたは配列をCPU上のNumPy配列へ変換します。

        LightGlueの出力には、バッチサイズ1でも先頭にバッチ次元が付く場合が
        あります。呼び出し側で必要に応じてその次元を取り除きます。

        CUDA上のTensorを``np.asarray``へ直接渡すと、GPUメモリ上のデータを
        NumPyが読めないためTypeErrorになります。Tensor判定を最初に行い、
        ``detach().cpu().numpy()``で必ずホストメモリへ移してから配列化します。
        LightGlueのバージョンによってはTensorがリストやタプルに包まれるため、
        コンテナの場合は中身も再帰的に変換します。
        """
        if isinstance(value, tuple):
            return np.asarray([LightGlueFeatures.to_numpy(item) for item in value])
        if isinstance(value, list):
            return np.asarray([LightGlueFeatures.to_numpy(item) for item in value])
        if hasattr(value, "detach") and hasattr(value, "cpu"):
            return value.detach().cpu().numpy()
        return np.asarray(value)

    @staticmethod
    def remove_batch_dimension(value: Any) -> np.ndarray:
        """LightGlue出力をNumPy化し、サイズ1の先頭バッチ次元を除去します。"""
        array = LightGlueFeatures.to_numpy(value)
        if array.ndim >= 3 and array.shape[0] == 1:
            return array[0]
        return array

    @staticmethod
    def match_indices(value: Any) -> np.ndarray:
        """LightGlueの対応番号を``(N, 2)``の整数配列へ正規化します。"""
        matches = LightGlueFeatures.remove_batch_dimension(value)
        if matches.size == 0:
            return np.empty((0, 2), dtype=np.int64)
        if matches.ndim != 2 or matches.shape[1] != 2:
            raise ValueError(f"LightGlueのmatchesは(N, 2)形式が必要です: {matches.shape}")
        return np.asarray(matches, dtype=np.int64)

    @staticmethod
    def keypoints(value: Any) -> np.ndarray:
        """LightGlueのキーポイントを``(N, 2)``のfloat32配列へ正規化します。"""
        keypoints = LightGlueFeatures.remove_batch_dimension(value)
        if keypoints.ndim != 2 or keypoints.shape[1] != 2:
            raise ValueError(f"LightGlueのkeypointsは(N, 2)形式が必要です: {keypoints.shape}")
        return np.asarray(keypoints, dtype=np.float32)
