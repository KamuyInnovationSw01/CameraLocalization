# ArUco マーカー生成・プリント ガイド

`generate_markers.py` を使用して、ArUco マーカーをプリント用のファイル形式で生成します。

---

## クイックスタート

### 1. config.yaml で指定したマーカーを生成

```bash
python generate_markers.py
```

**出力**: `aruco_marker.png`

`config.yaml` の `marker.expected_id` で指定したマーカーを、PNG形式で生成します。

### 2. マーカーチャート（複数マーカーのグリッド）を生成

```bash
python generate_markers.py --chart --cols 4 --rows 4
```

**出力**: `aruco_marker.png`

4列 × 4行 のマーカーチャート（合計16個のマーカー）を生成します。

### 3. 出力ファイル名を指定

```bash
python generate_markers.py --output my_marker
```

**出力**: `my_marker.png`

---

## 詳細な使い方

### コマンドラインオプション

```
--config CONFIG              設定ファイルのパス (デフォルト: config.yaml)
--output OUTPUT              出力ファイル名（拡張子なし） (デフォルト: aruco_marker)
--format {png,pdf}           出力形式 (デフォルト: png)
--chart                      チャート（複数マーカー）を生成
--cols COLS                  チャートの列数 (デフォルト: 4)
--rows ROWS                  チャートの行数 (デフォルト: 4)
--start-id START_ID          チャート生成時の開始マーカーID (デフォルト: 0)
--marker-id MARKER_ID        単一マーカー生成時のマーカーID
--dpi DPI                    出力解像度 (DPI、デフォルト: 300)
```

---

## 使用例

### 例1: 単一マーカーを生成（高解像度）

```bash
python generate_markers.py --output test_marker --dpi 300
```

- 出力: `test_marker.png`
- 解像度: 300 DPI（プリント品質）
- マーカーID: config.yaml の `marker.expected_id` から取得（デフォルト: 1）

### 例2: 特定のマーカーIDを生成

```bash
python generate_markers.py --marker-id 5 --output marker_5
```

- 出力: `marker_5.png`
- マーカーID: 5
- config.yaml の設定は無視

### 例3: 3×3 のマーカーチャートを生成

```bash
python generate_markers.py --chart --cols 3 --rows 3 --output chart_3x3
```

- 出力: `chart_3x3.png`
- 構成: 3列 × 3行（合計9個のマーカー）
- マーカーID: 0～8（デフォルト）

### 例4: 開始IDを指定してチャートを生成

```bash
python generate_markers.py --chart --start-id 10 --cols 4 --rows 4 --output chart_10to25
```

- 出力: `chart_10to25.png`
- マーカーID: 10～25

### 例5: PDF形式で出力（要 reportlab インストール）

```bash
python generate_markers.py --format pdf --output marker_1.pdf
```

- 出力: `marker_1.pdf`
- 形式: PDF（プリンタ対応）
- 必須: `pip install reportlab`

### 例6: チャートをPDFで出力

```bash
python generate_markers.py --chart --cols 4 --rows 4 --format pdf --output markers_chart.pdf
```

- 出力: `markers_chart.pdf`
- 構成: 4列 × 4行
- 形式: PDF

---

## config.yaml との連携

生成されたマーカーは、`config.yaml` の以下の設定を自動的に参照します：

```yaml
marker:
  size_m: 0.1              # マーカーサイズ（メートル）
  dictionary: "DICT_4X4_50"  # ArUco 辞書タイプ
  expected_id: 1           # デフォルトマーカーID
```

**注**: `--marker-id` を指定した場合は、`expected_id` の設定は無視されます。

---

## プリント方法

### PNG形式でのプリント

1. 生成されたPNG ファイルをプリンタで開く
2. プリント設定で以下を確認:
   - **用紙**: A4 または A5
   - **縮尺**: 100%（縮小しない）
   - **マージン**: なし（フチなし印刷）

### PDF形式でのプリント

```bash
python generate_markers.py --format pdf --output markers.pdf
```

1. Adobe Readerなどで PDF を開く
2. プリント設定:
   - **ページサイズ**: 実際のサイズ
   - **スケーリング**: なし（100%）

---

## マーカーサイズの計算

マーカーの物理サイズはPNG/PDF ファイルのピクセルサイズとDPI値から計算されます。

**計算式**:
$$\text{物理サイズ (cm)} = \frac{\text{ピクセルサイズ}}{\text{DPI}} \times 2.54$$

**例**:
- DPI: 300, ピクセル: 1190
- 物理サイズ: 1190 / 300 × 2.54 ≈ 10 cm

**推奨設定**:
- **300 DPI**: 高品質印刷（推奨）
- **150 DPI**: 標準品質
- **72 DPI**: 画面表示用

---

## トラブルシューティング

### エラー: "ImportError: reportlab"

PDF形式での出力を使用する場合、reportlab をインストール してください。

```bash
pip install reportlab
```

### プリントしたマーカーが正しく検出されない

1. **マーカーサイズの確認**:
   - config.yaml の `marker.size_m` の値が実際のプリント サイズと一致しているか確認
   - DPI設定を確認（300 DPI推奨）

2. **辞書の確認**:
   - config.yaml の `marker.dictionary` がプログラムで使用しているものと一致しているか確認
   - DICT_4X4_50 推奨

3. **プリント品質**:
   - コントラスト（白黒）がはっきりしているか確認
   - スケーリングなしで100% サイズでプリント

4. **カメラの照明**:
   - 十分な照明があるか確認
   - グレアがないか確認

---

## 複数マーカーの管理

複数のマーカーを使い分ける場合の推奨手順：

1. **チャートの生成**:
   ```bash
   python generate_markers.py --chart --cols 4 --rows 5 --output master_chart
   ```

2. **マーカーの識別**:
   - 生成されたチャート画像でマーカーIDを確認
   - 各マーカーをプリント

3. **main.py での使用**:
   - `config.yaml` の `marker.expected_id` を変更
   - または、プログラム内で複数マーカーに対応するよう拡張

---

## バッチ生成スクリプト例

複数のマーカーを一括生成する場合：

```bash
# マーカーID 0～9 を個別に生成
for i in {0..9}; do
    python generate_markers.py --marker-id $i --output marker_${i}
done
```

または Python で:

```python
import subprocess

for marker_id in range(10):
    cmd = [
        "python", "generate_markers.py",
        "--marker-id", str(marker_id),
        "--output", f"marker_{marker_id}"
    ]
    subprocess.run(cmd)
```

---

## FAQ

**Q: マーカーサイズはどのように指定する？**  
A: `config.yaml` の `marker.size_m` で指定（メートル単位）。デフォルト: 0.1 m (10cm)

**Q: 複数マーカーのすべてが同じサイズ？**  
A: はい。チャート内のすべてのマーカーは `marker.size_m` で指定したサイズになります。

**Q: PDFで複数ページに分割したい場合は？**  
A: 複数のチャートを別々に生成してから、PDF結合ツールで統合してください。

**Q: ArUco 辞書を変更できる？**  
A: はい。`config.yaml` の `marker.dictionary` を変更（例: "DICT_6X6_250"）

**Q: 生成されたファイルのDPI情報は保持される？**  
A: PNG形式ではDPI情報が埋め込まれます（メタデータ）。Pillow/PIL で確認可能。

---

## 関連ドキュメント

- [README.md](README.md) - メインアプリケーションの使い方
- [Specification.md](Specification.md) - システム仕様書
- [config.yaml](config.yaml) - 設定ファイル
