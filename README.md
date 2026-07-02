# カメラローカライゼーション - ARマーカー ポーズ推定

USBカメラでARマーカー（ArUco）を撮影し、カメラの3次元姿勢（位置・向き）をリアルタイムで3Dワイヤフレーム表示するアプリケーションです。

## 主な特徴

- **リアルタイム ArUco マーカー検出・姿勢推定**（OpenCV ArUco + solvePnP）
- **matplotlib による高品質3D可視化**（3D グリッドボックス・カメラ本体・フラスタム・視線方向）
- **マーカーを底面に配置した直感的な3Dビュー**（カメラが上から見下ろす構成）
- **2ウィンドウ表示**（左：カメラ映像、右：独立3Dビュー）
- **平面マーカー反転曖昧性への頑健な対応**

---

## システム要件

- **OS**: Windows 10/11（Linux/Mac対応可能）
- **Python**: 3.8 以上（3.11 で動作確認）
- **USB カメラ**: 接続済み
- **メモリ**: 2GB 以上推奨

---

## インストール

### 1. 依存ライブラリのインストール

```bash
pip install -r requirements.txt
```

必要なライブラリ:

| ライブラリ | 用途 |
|-----------|------|
| `opencv-contrib-python` | コンピュータビジョン・ArUco検出・solvePnP |
| `numpy` | 数値計算・行列演算 |
| `PyYAML` | 設定ファイル読み込み |
| `matplotlib` | 高品質3D可視化（3D グリッドボックス描画） |

### 2. カメラキャリブレーションパラメータの準備

`center.json`（または `eMeetNova.json` 等の別ファイル）に以下の情報を含めます:

```json
{
  "imageSize": [1920, 1080],
  "cameraMatrix": [
    [fx, 0, cx],
    [0, fy, cy],
    [0, 0, 1]
  ],
  "distCoeffs": [[k1, k2, p1, p2, k3]],
  "rvecs": [...],
  "tvecs": [...]
}
```

---

## 使用方法

### 基本実行

```bash
python main.py
```

起動時にカメラ一覧が表示されるので、使用するカメラの ID を入力します。

### 設定のカスタマイズ

`config.yaml` で以下を設定可能:

```yaml
marker:
  size_m: 0.1                    # マーカーサイズ（メートル）
  dictionary: "DICT_4X4_50"      # ArUco辞書タイプ

calibration:
  parameters_file: "eMeetNova.json"   # キャリブレーションファイル

ui:
  camera_window: {width: 960, height: 720, x_pos: 0, y_pos: 0}
  wireframe_window: {width: 960, height: 720, x_pos: 960, y_pos: 0}
```

### キーボード操作

| キー | 動作 |
|------|------|
| **q** または **ESC** | アプリケーションを終了 |
| **s** | 現在のフレームをキャプチャして保存 |

---

## 3Dビューの仕様

右ウィンドウには以下の要素が描画されます。

### 表示要素

- **3D グリッドボックス**（半透明）：マーカーとカメラを内包する自動スケールのグリッド
- **マーカー**（赤い正方形 + 座標軸）：**底面中央**（z=0）に配置
- **カメラ本体**（オレンジの長方体）：カメラ位置と向きを表現
- **フラスタム**（シアン）：カメラ前方の視錐台
- **視線方向**（黄色矢印）：カメラ光軸（マーカーへの方向）
- **座標軸**（赤=X, 緑=Y, 青=Z）：マーカー原点からの基準軸

### 座標系

本アプリのワールド座標系は **「マーカー底面中央が原点、+Z が上（カメラがいる方向）」** として統一しています。
OpenCV の `solvePnP` 規約（`+Z` がカメラ前方）とは z 軸の向きが逆のため、`pose_estimator.py` 内で
`R = R @ diag(1,1,-1)` による座標系統一変換を実施しています。

### 平面マーカーの反転曖昧性への対応

平面マーカーは**正面付近で反転解**（カメラがマーカー裏側にある）を返すことがあります。
本アプリでは以下の2段階で対処しています。

1. **`pose_estimator.py`**: `SOLVEPNP_IPPE_SQUARE`（平面正方形専用ソルバ）を使用。
   `dot(tvec, R[:,2]) > 0` を反転解と判定し、`tvec` と `R` を反射補正。
2. **`wireframe_renderer.py`**: カメラ本体の表示向きを **look-at 方式**で構築
   （カメラ位置からマーカー原点を向く方向を光軸とする）し、ロール角の自由度による
   カメラ向きの不確定を吸収。

これにより**正面捕捉時にカメラがマーカー上方から下向きに安定描画**されます。

---

## ディレクトリ構成

```
CameraLocalization/
├── main.py                    # メインアプリケーション（イベントループ）
├── camera_handler.py          # USB カメラ制御モジュール
├── camera_name_util.py        # カメラ名取得ユーティリティ
├── marker_detector.py         # ArUco マーカー検出モジュール
├── pose_estimator.py          # ポーズ推定（反転解補正・座標系統一込み）
├── wireframe_renderer.py      # matplotlib による3D グリッドボックス描画
├── ui_manager.py              # 2ウィンドウ UI 管理
├── generate_markers.py        # ArUco マーカー生成スクリプト
├── config.yaml                # 設定ファイル
├── eMeetNova.json             # eMeet Nova 用キャリブレーション
├── center.json                # デフォルトキャリブレーション
├── requirements.txt           # 依存ライブラリ
├── README.md                  # このファイル
├── Specification.md           # 仕様書
├── CAMERA_AUTO_DETECTION.md   # カメラ自動検出の説明
└── MARKER_GENERATION_GUIDE.md # マーカー生成ガイド
```

---

## 機能詳細

### 1. マーカー検出（`marker_detector.py`）

- **ライブラリ**: OpenCV ArUco (`cv2.aruco.ArucoDetector`)
- **対応辞書**: DICT_4X4_50（設定で変更可能）
- **リアルタイム検出**: カメラフレームから自動検出

### 2. ポーズ推定（`pose_estimator.py`）

- **ソルバ**: `cv2.SOLVEPNP_IPPE_SQUARE`（平面正方形マーカー専用）
- **入力**: マーカー4コーナー画像座標 + 3D オブジェクト座標（z=0 平面）
- **出力**: 回転ベクトル `rvec`、並進ベクトル `tvec`
- **後処理**:
  - 反転解検出・補正（`dot(tvec, R[:,2])` ベース）
  - 座標系統一（OpenCV規約 → アプリ規約）
  - 回転角・距離・カメラ位置を `get_pose_info()` で辞書返却

### 3. 3D グリッドボックス描画（`wireframe_renderer.py`）

- **バックエンド**: matplotlib + `mpl_toolkits.mplot3d`
- **画像変換**: `FigureCanvasAgg` → `buffer_rgba()` → OpenCV BGR
- **表示内容**:
  - 自動スケールの3D グリッドボックス（XY: マーカーとカメラを包含、Z: カメラ位置の 1.25 倍）
  - 実寸アスペクト比（`ax.set_box_aspect`）で歪みなし
  - 固定視点（`ax.view_init(elev=20, azim=-70)`）で再現性確保
  - マーカー / カメラ本体 / フラスタム / 視線方向 / 座標軸

### 4. UI（`ui_manager.py`）

- **2ウィンドウ表示**:
  - **左ウィンドウ** (0, 0): カメラ映像 + マーカー検出オーバーレイ
  - **右ウィンドウ** (960, 0): 独立 3D ビュー
- ウィンドウ位置指定で作業しやすい配置

---

## トラブルシューティング

### カメラが認識されない
- USB 接続を確認
- 複数のカメラがある場合、起動時のカメラ一覧から該当 ID を選択
- 他のアプリケーションでカメラを使用していないか確認

### マーカーが検出されない
- 照明条件を確認
- マーカーサイズが `config.yaml` の `marker.size_m` と一致しているか確認
- `marker.dictionary` が印刷したマーカーと一致しているか確認
- マーカーが歪んでいないか確認

### キャリブレーションエラー
- キャリブレーション JSON ファイルが存在するか確認
- ファイルが正しい JSON 形式か確認
- カメラ行列のサイズが (3, 3) か確認

### カメラの3D 表示位置がおかしい
- `pose_estimator.py` の補正が正しく機能しているか確認
- 正面付近（回転角 ≈ 180°）では反転解が発生しやすいため、look-at 方式で安定表示される

### matplotlib 関連エラー
- `AttributeError: 'RendererAgg' object has no attribute 'tostring_rgb'`
  → matplotlib バージョンアップに伴う API 変更。新 API `buffer_rgba()` を使用（本アプリは対応済み）

---

## パフォーマンス

- **フレームレート**: 30 FPS 目標
- **遅延**: 低遅延（matplotlib 描画は数 ms 程度）
- **CPU 使用率**: 中程度（実機 eMeet Nova で実用的に動作）

---

## カスタマイズ例

### 異なるサイズのマーカーを使う

```yaml
# config.yaml
marker:
  size_m: 0.15  # 15cm × 15cm
```

### 別のキャリブレーションデータを使う

```yaml
calibration:
  parameters_file: "my_calibration.json"
```

### ArUco 辞書を変更

```yaml
marker:
  dictionary: "DICT_6X6_250"  # より大きなマーカー
```

---

## 関連ドキュメント

- [Specification.md](Specification.md): システム仕様書
- [CAMERA_AUTO_DETECTION.md](CAMERA_AUTO_DETECTION.md): カメラ自動検出の説明
- [MARKER_GENERATION_GUIDE.md](MARKER_GENERATION_GUIDE.md): ArUco マーカー生成ガイド

---

## ライセンスと参考資料

- **OpenCV**: https://opencv.org/
- **ArUco**: OpenCV contrib モジュール
- **matplotlib**: https://matplotlib.org/

---

## 今後の拡張

- 複数マーカーへの対応
- GPU 高速化
- 異なるマーカータイプの対応
- データベースへのログ出力
- Web インターフェース
