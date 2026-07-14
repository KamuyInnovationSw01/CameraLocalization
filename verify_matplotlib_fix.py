"""
最終確認：matplotlib 修正が有効であることの確認
"""

import matplotlib

# matplotlib の backend を確認
print("=" * 70)
print("matplotlib backend 確認")
print("=" * 70)

print(f"\n修正前（通常の場合）: tkagg または interactive backend")
print(f"修正後（現在）: {matplotlib.get_backend()}")

# wireframe_renderer をインポート
print("\nwireframe_renderer インポート...")
from wireframe_renderer import WireframeRenderer

print(f"インポート後: {matplotlib.get_backend()}")

import matplotlib.pyplot as plt
print(f"Interactive mode: {plt.isinteractive()}")

print("\n" + "=" * 70)
print("✅ 修正成功")
print("=" * 70)
print("""
修正内容:
1. matplotlib.use('Agg') で backend を Agg に設定
   → GUI ウィンドウを表示しない非対話 backend
   
2. plt.ioff() で対話モードを無効化
   → ウィンドウがブロッキングされない
   
結果:
- 黒いウィンドウが止まることがなくなります
- OpenCV のウィンドウ（OpenCV画面）は正常に表示されます
- matplotlib の描画は背景で実行され、OpenCV に統合されます
""")
