# カメラポーズ推定フロー

## 概要
マーカー検出からカメラポーズ計算までの完全な処理フロー

---

## 処理ステップ

### 1. マーカー検出フェーズ
```
入力フレーム（BGR画像）
        ↓
グレースケール変換
        ↓
ArUco検出器で検出
        ↓
[出力] corners: (N, 4, 2) - マーカーのコーナー座標
       ids:     (N,)     - マーカーID
       rejected: 検出失敗候補
```

**処理ファイル**: `marker_detector.py` の `detect_markers()`

---

### 2. ポーズ推定フェーズ

#### 2-1. 3D-2D対応
```
マーカー3D座標（マーカー座標系）
  - marker_center = (0, 0, 0)
  - marker_size_m で定義（デフォルト 0.1 m）
  - ArUcoの順序（左上、右上、右下、左下）に合わせて4つのコーナーを3D化

        [-L/2, +L/2, 0]  ----  [L/2, +L/2, 0]
             |                   |
             |                   |
        [-L/2, -L/2, 0]  ----  [L/2, -L/2, 0]

         ↕ (一対一対応) ↕

画像平面上のコーナー座標（検出結果）
  - pixel座標 (u, v) × 4
```

**処理ファイル**: `pose_estimator.py` の `estimate_marker_pose()`

---

#### 2-2. solvePnP によるポーズ推定
```
入力:
  ├─ object_points: 3D座標 (4, 3) - マーカーコーナー
  ├─ image_points:  2D座標 (4, 2) - 画像上のコーナー
  ├─ cameraMatrix:  キャリブレーションパラメータ
  └─ flags: SOLVEPNP_IPPE_SQUARE
           （平面正方形マーカー専用）

計算:
  solvePnP → rvec (3,), tvec (3,)

出力:
  ├─ rvec: 回転ベクトル（ロドリゲス表現）
  └─ tvec: 並進ベクトル（メートル）

意味:
  p_camera = R @ p_marker + tvec
  （R = cv2.Rodrigues(rvec) で変換）
```

---

#### 2-3. 座標系の扱い
`solvePnP` の出力はOpenCVの座標系のまま使用します。推定後に `tvec` だけを反転したり、`diag(1, 1, -1)` を回転行列へ掛けたりしません。後者は行列式が `-1` の鏡映変換になり、再投影を壊します。

```
p_camera = R @ p_marker + tvec
R = cv2.Rodrigues(rvec)
```

3Dビューでの表示変換は `wireframe_renderer.py` のみで行います。表示用LookAtは `det(R_view)=+1` の右手系とし、マーカーの `+Z`（正面方向）が画面上向きになるようにします。

#### 2-4. 再投影誤差
推定後の `rvec` と `tvec` で4つの3Dコーナーを再投影し、入力画像コーナーとの差をピクセル単位で計算します。平均と最大をコンソールへ出力します。

```
再投影誤差 (pix): 平均=0.259, 最大=0.261
```

---

### 3. 出力情報

#### ポーズ情報（pose_info）
```python
{
    'distance': float,        # マーカーからの距離 [m]
    'rotation_angle': float,  # 回転角度 [度]
    'camera_position': (x, y, z),  # カメラ位置 [m]
    'rvec': ndarray,         # 回転ベクトル (3,)
    'tvec': ndarray          # 並進ベクトル (3,)
}
```

#### カメラ位置の計算
```
定義:
  camera_pos = -R^T @ tvec

理由:
  マーカー座標系:
    p_camera = R @ p_marker + tvec
  
  マーカー座標系でのカメラ位置は p_camera = 0 のとき：
    0 = R @ p_marker_camera + tvec
    p_marker_camera = -R^(-1) @ tvec
                    = -R^T @ tvec

結果:
  camera_position = -R^T @ tvec
```

---

## コード処理フロー図

```
main.py の process_frame()
  │
  ├─ marker_detector.detect_markers(frame)
  │    └─ [出力] corners, ids, rejected
  │
  ├─ marker_detector.get_marker_info()
  │    └─ [出力] marker_info
  │
  └─ marker_info['detected'] が True の場合:
       │
       ├─ pose_estimator.estimate_marker_pose(
       │      marker_corners, marker_size_m
       │  )
       │   ├─ solvePnP(object_pts, image_pts, K, dist)
       │   │   └─ [出力] rvec, tvec
       │   │
      │   ├─ solvePnPのrvec/tvecを保持
      │   └─ 4隅を再投影して平均・最大誤差を出力
       │
       └─ pose_estimator.get_pose_info(rvec, tvec)
            ├─ R = cv2.Rodrigues(rvec)
            ├─ camera_pos = -R^T @ tvec
            ├─ distance = ||camera_pos||
            └─ [出力] pose_info
```

---

## 実装検証

### テスト実行コマンド
```powershell
.\.venv\Scripts\python.exe .\main.py
# eMeet Novaを選択
# フレーム処理 → マーカー検出 → ポーズ推定
```

### 出力例
```
検出されたマーカー: 1 個
  - ID: 1, 中心: (367.8, 320.8)
ポーズ情報:
  - 距離: 0.107 m
  - 回転角: 90.1 deg
  - カメラ位置: (-0.050, -0.019, 0.092)
```

### 確認項目
- [x] `det(R) = +1` → 有効な回転行列
- [x] 再投影誤差をpix単位で確認できる
- [x] `camera_position = -R.T @ tvec` でカメラ位置を計算
- [x] 3DビューのLookAtが右手系になっている

---

## 関連ファイル

| ファイル | 役割 |
|---------|------|
| `marker_detector.py` | マーカー検出（ArUco） |
| `pose_estimator.py` | ポーズ推定（solvePnP） |
| `wireframe_renderer.py` | 3D可視化 |
| `main.py` | 処理フローのオーケストレーション |

---

## 座標変換の詳細ノート

### 座標系の注意点

**OpenCV solvePnP の出力**:
```
[OpenCV基準]
  +Z: 被写体方向（カメラ前方）
  点 p_marker がマーカー座標系にあるとき
  p_camera = R @ p_marker + tvec
  
  マーカーは +Z 前方にあるなら
  tvec[2] > 0（+Z方向に並進）
```

`solvePnP` の出力を別の表示座標系へ変換する場合でも、`R` と `tvec` を同じ剛体変換として扱う必要があります。鏡映行列を回転行列として扱うことや、`tvec` だけを反転することはできません。現在の実装では推定値を変更せず、表示側の右手系LookAtで見やすい向きに変換しています。

