# カメラローカライゼーション - ARマーカー ポーズ推定

USBカメラでARマーカー（ArUco）を撮影し、カメラの3次元姿勢（位置・向き）をリアルタイムで3Dワイヤフレーム表示するアプリケーションです。

## 主な特徴

- **リアルタイム ArUco マーカー検出・姿勢推定**（OpenCV ArUco + solvePnP）
- **OpenCVによる高速3D可視化**（カメラ本体・フラスタム・視線方向）
- **右手系の3Dビュー**（マーカーの正面方向を画面上向きに表示）
- **2ウィンドウ表示**（左：カメラ映像、右：独立3Dビュー）
- **再投影誤差による姿勢推定結果の確認**

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
| `matplotlib` | 任意の詳細表示モード用の3D可視化 |

### 2. カメラキャリブレーションパラメータの準備

現在の設定では `eMeetNova.json` を使用します。別のカメラ用キャリブレーションを使う場合は、`config.yaml` の `calibration.parameters_file` を変更してください。キャリブレーションファイルには以下の情報を含めます:

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

### 0. 仮想環境の有効化

```bash
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Windows (Command Prompt)
.\.venv\Scripts\activate.bat

# Linux/Mac
source .venv/bin/activate
```

### 基本実行

```bash
python main.py
```

**Windows で仮想環境が正しく有効化されない場合:**

```bash
# 明示的に仮想環境の Python を指定して実行
.\.venv\Scripts\python.exe .\main.py
```

起動時にカメラ一覧が表示されるので、使用するカメラの ID を入力します。

### カメラと解像度の選択

アプリケーション起動後、以下の2つのステップで選択が必要です：

**ステップ1: カメラ選択**
```
利用可能なカメラ:
  [0] カメラID 0 - ASUS FHD webcam (1920x1080 @ 30.0fps)
  [1] カメラID 1 - eMeet Nova (640x480 @ 30.0fps)
  [2] カメラID 2 - Camera (NVIDIA Broadcast) (640x480 @ 0.0fps)

使用するカメラを選択してください (0-2):  # 例：1
```

**ステップ2: 解像度選択**

選択したカメラの利用可能な解像度が自動検出され表示されます：
```
利用可能な解像度（9 個）:
  [0] 4096x2160
  [1] 3840x2160
  [2] 2560x1920
  [3] 1920x1080
  [4] 1280x960
  [5] 1280x720
  [6] 640x480
  [7] 480x360
  [8] 320x240

使用する解像度を選択してください (0-8):  # 例：6
✓ 解像度を選択: 640x480
```

**解像度検出について**

- **方式**: まず `pygrabber` のDirectShowフォーマットを取得し、失敗時は23個の標準解像度（4K～QVGA）をOpenCVで試して、実際に対応している解像度を検出
- **時間**: 通常数秒～10秒（カメラ応答速度に依存）
- **カバレッジ**：
  - ASUS webcam: 1920×1080 対応
  - NVIDIA Broadcast: 4096×2160 ～ 320×240 の9解像度対応
  - OBS Virtual: 4096×2160 ～ 480×360 の22解像度対応

> **注意**: 解像度検索には数秒かかる場合があります。カメラが応答しない場合、「警告」が表示されますが、アプリケーションは続行します。

**注意**: 解像度検索には数秒かかる場合があります（各解像度の試行テスト中）。

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

debug:
  enable_3d_render: true
  render_mode: "opencv"       # 高速描画。必要なら"matplotlib"にも変更可能
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

- **マーカー**（赤い正方形 + 座標軸）：原点（z=0）に配置
- **カメラ本体**（オレンジの長方体）：カメラ位置と向きを表現
- **フラスタム**（シアン）：カメラ前方の視錐台
- **視線方向**（黄色矢印）：カメラ光軸（マーカーへの方向）
- **座標軸**（赤=X, 緑=Y, 青=Z）：マーカー原点からの基準軸
- **自動フィット**：表示対象全体を検出し、上下左右に余白を確保して画面内に表示

### 座標系

ポーズ推定ではOpenCVの座標系をそのまま使用します。`solvePnP` の結果は次の変換を表します。

```text
p_camera = R @ p_marker + tvec
```

`rvec` と `tvec` の片方だけを反転したり、鏡映行列を回転行列として扱ったりすると、再投影を満たさないため、推定後の値は変更しません。カメラ位置は次式で求めます。

```text
camera_position = -R.T @ tvec
```

3Dビューの仮想カメラは右手系LookAtで構築し、マーカーの `+Z`（正面方向）が画面上向きになるように表示します。

### 平面マーカーの反転曖昧性への対応

`SOLVEPNP_IPPE_SQUARE`（平面正方形専用ソルバ）で推定した `rvec` と `tvec` をそのまま保持します。
推定直後にマーカー四隅を再投影し、コンソールへ平均・最大誤差を表示します。

```text
再投影誤差 (pix): 平均=0.259, 最大=0.261
```

---

## ディレクトリ構成

```
CameraLocalization/
├── main.py                    # メインアプリケーション（イベントループ）
├── camera_handler.py          # USB カメラ制御モジュール
├── camera_name_util.py        # カメラ名取得ユーティリティ
├── marker_detector.py         # ArUco マーカー検出モジュール
├── pose_estimator.py          # ポーズ推定（OpenCV座標系・再投影誤差確認）
├── wireframe_renderer.py      # OpenCVによる高速3Dビュー描画
├── ui_manager.py              # 2ウィンドウ UI 管理
├── generate_markers.py        # ArUco マーカー生成スクリプト
├── config.yaml                # 設定ファイル
├── eMeetNova.json             # eMeet Nova 用キャリブレーション
├── center.json                # 追加のキャリブレーション例（現在の既定値では未使用）
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
  - `rvec` と `tvec` はsolvePnPの結果をそのまま保持
  - 再投影誤差（平均・最大）をコンソールへ出力
  - 回転角・距離・カメラ位置を `get_pose_info()` で辞書返却

### 3. 3Dビュー描画（`wireframe_renderer.py`）

- **標準バックエンド**: OpenCV（`render_mode: "opencv"`）
- **詳細バックエンド**: matplotlib（`render_mode: "matplotlib"` で選択可能。失敗時はOpenCVへフォールバック）
- **投影**: 右手系LookAt + `cv2.projectPoints`
- **表示内容**:
  - マーカー、カメラ本体、フラスタム、光軸、座標軸
  - 全頂点から算出する自動フィットと上下左右50pxの余白
  - マーカーの+Z正面方向を画面上向きにした表示

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
- 正面付近で表示が不安定な場合は、コンソールの再投影誤差とカメラ解像度・キャリブレーションの一致を確認する

### matplotlib 関連エラー
- `AttributeError: 'RendererAgg' object has no attribute 'tostring_rgb'`
  → matplotlib バージョンアップに伴う API 変更。新 API `buffer_rgba()` を使用（本アプリは対応済み）

---

## パフォーマンス

- **フレームレート**: 30 FPS 目標
- **遅延**: OpenCV描画を標準とする低遅延構成（matplotlibは詳細表示用の任意モード）
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

## トラブルシューティング

### カメラ名が "Camera 0", "Camera 1" と表示される場合

**原因**: `pygrabber` パッケージが正しくインポートされていません（主に Windows の仮想環境設定問題）

**解決方法**:

1. 仮想環境が正しく有効化されているか確認：
   ```bash
   python -c "import pygrabber; print('OK')"
   ```

2. 仮想環境が有効化されていない場合、明示的に指定：
   ```bash
   # PowerShell
  .\.venv\Scripts\python.exe .\main.py

   # Command Prompt
   .venv\Scripts\python.exe main.py
   ```

3. それでも解決しない場合は、`pygrabber` を再インストール：
   ```bash
   pip uninstall pygrabber -y
   pip install pygrabber==0.2
   ```

### カメラフレームが取得できない場合

- USB カメラが正しく接続されているか確認
- 他のアプリケーションがカメラを使用していないか確認
- カメラドライバを再インストール

### マーカーが検出されない場合

- マーカーが DICT_4X4_50 で生成されているか確認
- マーカーが十分に明るいか、高コントラストか確認
- マーカーサイズが config.yaml で正しく設定されているか確認
- カメラキャリブレーションファイルが正しいか確認

### モジュール依存エラーが発生する場合

```bash
# requirements.txt から再インストール
pip install -r requirements.txt
```

---

## カメラ自動検出について

このアプリケーションは Windows DirectShow API を使用して、接続されているカメラの**製品名**を自動検出します。

- **Windows**: pygrabber（DirectShow）を使用
- **Linux/Mac**: 対応予定

カメラ名が表示されない場合でも、アプリケーションは正常に動作します（通常の ID ベースのカメラアクセス）

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
