# VSCodeでのデバッグ実行ガイド

## 問題
F5キーでデバッグ実行（main.py）を開始するとエラーが発生する。

## 原因の可能性

このアプリケーションはGUI（OpenCV、設定時のみmatplotlib）と**ユーザー入力（カメラ選択）**を使用しているため、デバッグ実行時に以下の問題が生じる可能性があります：

1. **コンソール入力不可**: 仮想環境の標準入力が正しく接続されていない
2. **Pythonインタプリタ不正**: システムの Python が使用されている（仮想環境ではない）
3. **描画バックエンド**: matplotlibモードはOpenCVモードより負荷が高い
4. **debugpy の問題**: 古いバージョンや互換性の問題

## 解決方法

### ステップ1: 設定ファイルが作成されていることを確認
プロジェクトフォルダ内に以下ファイルが存在することを確認してください：

```
.vscode/
├── launch.json    ← デバッグ設定
└── settings.json  ← VS Code 設定
```

### ステップ2: launch.json の確認（既に作成済み）

`.vscode/launch.json` に2つの実行設定が含まれています：

**設定1: 統合ターミナルでの実行（推奨）**
```json
{
    "name": "Python: main.py (統合ターミナル)",
    "console": "integratedTerminal",
    ...
}
```
→ VSCode内のターミナルに出力が表示される  
→ ユーザー入力（カメラ選択）が正常に機能する

**設定2: デバッグコンソールでの実行**
```json
{
    "name": "Python: main.py (デバッグコンソール)",
    "console": "internalConsole",
    ...
}
```

### ステップ3: デバッグ実行

1. **実行設定の選択**  
   VS Codeの「実行」メニュー → 「構成を選択して実行」  
   または  
   左サイドバーの「実行とデバッグ」パネルで設定を選択

2. **実行開始**  
   - `F5` キーを押す、または
   - 「実行」 → 「デバッグの開始」

3. **統合ターミナルの場合**  
   ターミナルに以下が表示されます：
   ```
   設定ファイルを読み込みました: config.yaml
   === モジュール初期化開始 ===
   [1] カメラハンドラーを初期化中...
   利用可能なカメラ:
     [0] カメラID 0 - ASUS FHD webcam (1920x1080 @ 30.0fps)
     [1] カメラID 1 - eMeet Nova (640x480 @ 30.0fps)
     ...
   使用するカメラを選択してください (0-3): 
   ```
   → ここで `1` などの数値を入力

## トラブルシューティング

### 「モジュール 'xxx' が見つかりません」エラー
**原因**: 仮想環境が正しく使用されていない

**解決**:
```powershell
# VSCode の Python インタプリタを設定
# Ctrl + Shift + P → "Python: Select Interpreter" → 
# ".venv\Scripts\python.exe" を選択
```

### コンソール入力が反応しない
**原因**: `console: "internalConsole"` で実行している

**解決**: 
- 実行設定を「統合ターミナル」に変更して再試行

### matplotlibモードで3Dビューが表示されない
**原因**: matplotlibモードの描画に失敗している

**解決**:
- `config.yaml` の `debug.render_mode` を `opencv` に戻す
- 統合ターミナルでの実行を試す

### 姿勢推定と3Dビューの確認

現在の標準描画モードは `config.yaml` の次の設定です。

```yaml
debug:
   enable_3d_render: true
   render_mode: "opencv"
```

`opencv` は `cv2.projectPoints` を使う高速描画です。`matplotlib` は任意の詳細表示モードで、描画に失敗した場合は自動的にOpenCVへフォールバックします。リアルタイム表示ではOpenCVモードを推奨します。

`pose_estimator.py` は `solvePnP` の `rvec` と `tvec` をそのまま使用します。推定後にコンソールへ次の再投影誤差が表示されます。

```text
再投影誤差 (pix): 平均=0.259, 最大=0.261
```

値が大きい場合は、マーカーサイズ、カメラ解像度とキャリブレーション解像度、マーカーのコーナー順を確認してください。カメラ位置は `-R.T @ tvec` で計算されます。

3Dビューは右手系のLookAt投影です。マーカーの `+Z`（正面方向）が画面上向きになるように配置し、表示対象全体から焦点距離と主点を自動計算して、上下左右50pxの余白を確保します。

### 「Permission denied」エラー
**原因**: カメラへのアクセス許可がない

**解決**:
- Windows の設定 → プライバシー → カメラ  
  → VSCode にカメラアクセス許可を与える

## 推奨実行方法

**統合ターミナルでの実行が最適です。**  
理由：
- ✓ ユーザー入力が正常に機能
- ✓ リアルタイム出力が見やすい
- ✓ 仮想環境の Python が確実に使用される
- ✓ OpenCVの高速3D描画が動作

## 手動実行（デバッグなし）

デバッグが不要な場合は、以下のコマンドで実行できます：

```powershell
cd C:\Users\sawada\OneDrive\Source\GithubRepos\CameraLocalization
.\.venv\Scripts\python.exe .\main.py
```

---

## 参考情報

| ファイル | 説明 |
|---------|------|
| `.vscode/launch.json` | VS Code デバッグ設定 |
| `.vscode/settings.json` | VS Code ワークスペース設定 |
| `requirements.txt` | Python パッケージ依存関係 |

