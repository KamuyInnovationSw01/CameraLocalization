# マーカーレス3Dマップ生成ガイド

マーカーレス方式では、参照画像からALIKEDの局所特徴量とLightGlueの対応点を作り、基準画像を原点とする簡易3Dマップを事前生成します。

## 参照画像の撮影

- `ref_1.png`を基準位置・基準姿勢で撮影します。
- `ref_2.png`以降は、被写体との共通領域が十分に残るように撮影します。
- `ref_2`のカメラ中心が基準位置から離れた距離の大きさだけを、メートル単位で記録します。
- `ref_3`以降は距離の記録は不要です。既知3D点との対応からカメラ姿勢を推定します。
- 回転と移動方向は入力せず、画像特徴から推定します。
- 被写体は剛体であり、十分なテクスチャが必要です。真っ白な壁、反射面、動く被写体、純粋な回転だけの画像列では安定して復元できません。

`reference_images.yaml`の例:

```yaml
reference_images:
  - file: "reference/ref_1.png"
  - file: "reference/ref_2.png"
    position_m: 0.03
  - file: "reference/ref_3.png"
  - file: "reference/ref_4.png"
```

`position_m`はref_1からref_2までの距離の大きさです。基準画像とref_3以降には指定しません。互換のため、ref_2では`distance_m`というキーも使用できます。

## マップ生成

キャリブレーションファイルを指定して実行します。

```powershell
.\.venv\Scripts\python.exe .\build_markerless_map.py .\reference_images.yaml `
  --output .\markerless_map.npz `
  --calibration .\eMeetNova.json `
  --device auto
```

`--device auto`はCUDAが利用可能ならCUDA、利用できなければCPUを選択します。CPUを明示する場合は`--device cpu`、CUDAを必須にする場合は`--device cuda`を指定します。

生成時に以下の条件を満たさない場合は、誤ったマップを保存せずエラーにします。

- 対応特徴点が8点以上ある
- ref_2でエッセンシャル行列から移動方向を復元できる
- 三角測量後に正の深度を持つ3D点が8点以上ある
- ref_3以降で既知3D点が6点以上対応する

## 実行時

`config.yaml`を次のように変更します。

```yaml
localization:
  mode: "markerless"

markerless:
  map_file: "markerless_map.npz"
  device: "auto"
  max_keypoints: 2048
  min_matches: 30
  min_inliers: 15
```

その後、通常の実行コマンドで起動します。

```powershell
.\.venv\Scripts\python.exe .\main.py
```

実行時は現在フレームからALIKED特徴を抽出し、LightGlueでマップの特徴量と対応付けます。対応する3D点と現在画像の2D点を`solvePnPRansac`へ入力し、基準画像1枚目のカメラ座標系に対するカメラ姿勢を推定します。

カメラ映像には対応点を描画します。緑はPnP/RANSACのインライア、赤は外れ値、黄は対応したものの
まだ姿勢推定で検証されていない点です。3Dビューにはマーカー四角形を表示せず、簡易3Dマップの
点を灰（未対応）、黄（未検証）、赤（外れ値）、緑（インライア）で表示します。対応点不足で姿勢を
推定できないフレームでは、3Dビューは暗い背景のままになります。

## 座標系と制約

基準画像1枚目のカメラ座標系を使用します。

- 原点: 1枚目撮影時のカメラ光学中心
- `+Z`: 1枚目撮影時のカメラ前方
- `+X`: 画像右方向
- `+Y`: 画像下方向

推定結果の`camera_position`は、基準カメラから見た現在カメラの位置です。ref_2の移動量は距離の大きさだけを指定し、移動方向は画像対応から選択されます。ref_3以降は、ref_1/ref_2で得た既知3D点からPnPで姿勢を求めるため、距離指定は不要です。ただし、各画像が既知マップの特徴点を十分共有している必要があります。純粋な回転、低テクスチャ、ref_1/ref_2と共通領域が少ない画像では復元できません。

3DビューはOpenCVのみで描画します。マーカーレス表示では表示専用にX軸まわり180度回転を適用するため、
表示上の`+Z`は下向きです。マップデータと推定値の座標は変更しません。
