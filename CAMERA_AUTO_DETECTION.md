# カメラ自動検出セットアップガイド

## 概要

このアプリケーションは `pygrabber` ライブラリを使用してWindows上のUSBカメラ製品名を自動検出します。

## インストール手順

### 方法1: pygrabberをインストール（推奨）

`pygrabber` を使用することで、カメラの正確な製品名を自動的に検出できます：

```bash
pip install pygrabber
```

**インストール後の動作:**
```
利用可能なカメラ:
  [0] カメラID 0 - ASUS FHD Webcam (640x480 @ 30.0fps)
  [1] カメラID 1 - eMeet Nova (640x480 @ 30.0fps)
  [2] カメラID 2 - USB Camera 2 (640x480 @ -1.0fps)
  [3] カメラID 3 - USB Camera 3 (640x480 @ -1.0fps)
```

### 方法2: pygrabberなしで実行（フォールバック）

`pygrabber` がインストールされていない場合、アプリケーションは自動的に一般的なカメラ名（"Camera 0", "Camera 1" など）を使用します：

```
利用可能なカメラ:
  [0] カメラID 0 - Camera 0 (640x480 @ 30.0fps)
  [1] カメラID 1 - Camera 1 (640x480 @ 30.0fps)
  [2] カメラID 2 - Camera 2 (640x480 @ -1.0fps)
  [3] カメラID 3 - Camera 3 (640x480 @ -1.0fps)
```

## テスト

デモスクリプトで動作確認できます：

```bash
python demo_camera_selection.py
```

## 実装詳細

### カメラ名検出のフロー

1. `camera_name_util.get_camera_names_auto()` を呼び出し
2. pygrabber が利用可能な場合:
   - `FilterGraph().get_input_devices()` でカメラ製品名を取得
   - 例: `{0: 'ASUS FHD Webcam', 1: 'eMeet Nova', ...}`
3. pygrabber が利用不可の場合:
   - 空の辞書を返す（フォールバック）
4. OpenCVでカメラ解像度・FPSを取得
5. カメラ情報を結合して表示

### コンポーネント

- **camera_name_util.py**: pygrabberを使用した自動検出ロジック
- **camera_handler.py**: `get_camera_info_list()` で自動検出を使用
- **main.py**: config.yamlのマッピングを削除し、自動検出のみ使用

## トラブルシューティング

### pygrabberのインストールに失敗した場合

```bash
# Visual C++ Build Tools が必要な場合がある
pip install --upgrade setuptools wheel
pip install pygrabber
```

### カメラ名が表示されない場合

- pygrabber がインストールされていない可能性
- `pip list | findstr pygrabber` で確認
- インストールされていない場合は上述の「方法2」でフォールバック動作します

## 参考資料

- pygrabber: https://github.com/rndshffld/pygrabber
- DirectShow: Windows標準のビデオキャプチャAPI

