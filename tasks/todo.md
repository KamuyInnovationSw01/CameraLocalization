# カメラローカライゼーション - 3Dワイヤーフレームウィンドウが真っ黒になる問題の修正計画

## 🎯 目的
ビデオウィンドウ（カメラ映像）でマーカーが正しく検出されているにもかかわらず、3Dワイヤーフレームウィンドウが真っ黒（あるいは表示されない）問題を解決します。

## 📋 計画

- [x] **Step 1: 現状チェックと原因分析**
  - [x] 設定ファイル `config.yaml` の内容と `main.py` の実装を精査する
  - [x] 原因特定: `config.yaml` の `enable_3d_render` が `false` になっていることを確認
  - [x] ターミナルログやエラーが発生しているかを検証する（matplotlib のテストで引数のバグを発見・修正、正常描画を確認）

- [x] **Step 2: 選択肢の追加とデフォルト設定の修正**
  - [x] `config.yaml` の `enable_3d_render` を `true` に変更する
  - [x] `config.yaml` に描画モードのパラメータ `render_mode: "opencv"` (デフォルト) を追加
  - [x] `main.py` の `render_output` 内で、描画モードを設定可能なように修正する

- [x] **Step 3: 安全なフォールバックの実装**
  - [x] `matplotlib` で描画エラーが発生した際、自動的に高速な `opencv` の `draw_3d_view` へフォールバックするエラーハンドリングを実装する

- [x] **Step 4: 動作検証テスト**
  - [x] アプリケーション実行による表示確認テスト（matplotlib のテストで引数のバグを発見・修正、正常描画を確認）
  - [x] テストスクリプト等による確認

- [x] **Step 5: レビューとレッスン記録**
  - [x] 結果のドキュメント化と完了マーク
  - [x] `tasks/lessons.md` に問題解決のパターンを記録

## 追加修正レビュー（2026-07-14）

- [x] `solvePnP` の `rvec` / `tvec` を後処理で反転せず、そのまま使用
- [x] カメラ位置を `-R.T @ tvec` で計算
- [x] 再投影誤差（平均・最大、pix）をコンソールへ出力
- [x] 3D描画の標準モードを高速なOpenCVへ変更
- [x] 右手系LookAtでマーカーの `+Z` 正面方向を画面上向きに表示
- [x] 全表示対象を対象にした自動フィットで画面外表示を防止
- [x] `test_*.py` を削除

## 構成整理・実行環境対応（2026-07-15）

- [x] `config.py`を追加し、YAML設定を`dataclass`で型付け
- [x] `camera_name_util.py`を削除し、`camera_discovery.py`へ統合
- [x] `aruco_dictionary.py`を追加し、ArUco辞書定義を共通化
- [x] `pipeline.py`を追加し、フレーム処理を`main.py`から分離
- [x] 未使用設定（`target_fps`、`use_grayscale`、`show_coordinate_frame`）を削除
- [x] `opencv-contrib-python`へ依存を統一
- [x] Python公式版3.11で`.venv`を再構築
- [x] VS Codeデバッグ設定を統合ターミナル1構成へ整理
- [x] matplotlibを遅延import化し、OpenCV標準起動時の初期化停止を回避
- [x] 設定・マーカー検出の単体テスト3件を追加・実行

