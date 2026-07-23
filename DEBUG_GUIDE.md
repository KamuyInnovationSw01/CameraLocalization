# VSCodeでのデバッグ実行ガイド

## 実行環境

このアプリケーションはOpenCVウィンドウとカメラ選択用の標準入力を使うため、VS Codeの統合ターミナルで実行します。

## 原因の可能性

このアプリケーションはOpenCV GUIと**ユーザー入力（カメラ選択）**を使用するため、デバッグ実行時に以下の問題が生じる可能性があります：

1. **コンソール入力不可**: 仮想環境の標準入力が正しく接続されていない
2. **Pythonインタプリタ不正**: システムの Python が使用されている（仮想環境ではない）
3. **debugpy の問題**: 古いバージョンや互換性の問題

## 解決方法

### ステップ1: 設定ファイルが作成されていることを確認
プロジェクトフォルダ内に以下ファイルが存在することを確認してください：

```
.vscode/
├── launch.json    ← デバッグ設定
└── settings.json  ← VS Code 設定
```

### ステップ2: launch.json の確認

`.vscode/launch.json`には、統合ターミナル用の実行設定を1つだけ定義しています。

```json
```json
   "name": "Python: main.py",
    "name": "Python: main.py (統合ターミナル)",
    "console": "integratedTerminal",
    ...
}
デバッグコンソール（`internalConsole`）は標準入力に対応しないため使用しません。
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

### debugpyの初期化中に止まる

次のように`debugpy`の内部で`KeyboardInterrupt`が発生する場合、`main.py`の処理にはまだ到達していません。

```text
debugpy.server
pydevd
KeyboardInterrupt
```

対策は次のとおりです。

1. Python公式版3.11で`.venv`を作成する
2. `Python: Select Interpreter`で`.venv\Scripts\python.exe`を選択する
3. VS Codeを`Developer: Reload Window`で再読み込みする
4. 統合ターミナル構成でF5を実行する

環境を作り直す例：

```powershell
Remove-Item -Recurse -Force .venv
& "C:\Users\<ユーザー名>\AppData\Local\Programs\Python\Python311\python.exe" -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 姿勢推定と3Dビューの確認

現在の標準描画モードは `config.yaml` の次の設定です。

```yaml
debug:
   enable_3d_render: true
```

3DビューはOpenCVの`cv2.projectPoints`を使って描画します。描画バックエンドの切り替えはありません。

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
| `.vscode/launch.json` | VS Code統合ターミナル用デバッグ設定 |
| `.vscode/settings.json` | VS Code ワークスペース設定 |
| `requirements.txt` | Python パッケージ依存関係 |

