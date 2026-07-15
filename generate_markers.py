"""
ArUco マーカー生成・プリント プログラム

config.yaml の marker セクションを参照して、
ArUco マーカーを生成し、PNG/PDF 形式で出力します。
"""

import cv2
import numpy as np
import argparse
import os

from aruco_dictionary import get_aruco_dictionary
from config import load_config


class ArUcoMarkerGenerator:
    """ArUco マーカーを生成・出力するクラス"""
    
    def __init__(self, config_file: str = "config.yaml"):
        """
        マーカー生成器を初期化します。
        
        Args:
            config_file: 設定ファイルのパス
        """
        self.config = load_config(config_file)
        self.dictionary_name = self.config.marker.dictionary
        self.dictionary = get_aruco_dictionary(self.dictionary_name)
        self.marker_size_m = self.config.marker.size_m
        self.marker_id = self.config.marker.expected_id
        
        print("ArUco マーカー生成器を初期化しました")
        print(f"  辞書: {self.dictionary_name}")
        print(f"  マーカーサイズ: {self.marker_size_m} m")
        print(f"  マーカーID: {self.marker_id if self.marker_id is not None else 'なし（全て生成）'}")
    
    def generate_marker(self, marker_id: int, pixels_per_inch: int = 300) -> np.ndarray:
        """
        単一のマーカーを生成します。
        
        Args:
            marker_id: マーカーID
            pixels_per_inch: 解像度 (DPI相当)
        
        Returns:
            np.ndarray: マーカー画像（グレースケール）
        """
        # マーカーサイズをピクセルに変換（インチ単位での計算）
        # 1インチ = 2.54cm
        marker_size_inches = self.marker_size_m * 100 / 2.54
        marker_size_pixels = int(marker_size_inches * pixels_per_inch)
        
        # マーカー生成
        marker_image = cv2.aruco.generateImageMarker(
            dictionary=self.dictionary,
            id=marker_id,
            sidePixels=marker_size_pixels,
            borderBits=1
        )
        
        return marker_image
    
    def generate_marker_chart(
        self,
        num_cols: int = 4,
        num_rows: int = 4,
        start_id: int = 0,
        margin_pixels: int = 50
    ) -> np.ndarray:
        """
        複数マーカーのチャート画像を生成します。
        
        Args:
            num_cols: 列数
            num_rows: 行数
            start_id: 開始ID
            margin_pixels: マージン（ピクセル）
        
        Returns:
            np.ndarray: チャート画像
        """
        # 単一マーカーを生成して寸法を取得
        sample_marker = self.generate_marker(start_id)
        marker_height, marker_width = sample_marker.shape
        
        # チャート全体のサイズを計算
        total_width = num_cols * marker_width + (num_cols + 1) * margin_pixels
        total_height = num_rows * marker_height + (num_rows + 1) * margin_pixels
        
        # 白背景のキャンバス作成
        chart = np.ones((total_height, total_width), dtype=np.uint8) * 255
        
        # マーカーをレイアウト
        marker_count = 0
        for row in range(num_rows):
            for col in range(num_cols):
                marker_id = start_id + marker_count
                
                # マーカーを生成
                marker = self.generate_marker(marker_id)
                
                # マーカーを配置
                y_start = row * marker_height + (row + 1) * margin_pixels
                x_start = col * marker_width + (col + 1) * margin_pixels
                y_end = y_start + marker_height
                x_end = x_start + marker_width
                
                chart[y_start:y_end, x_start:x_end] = marker
                
                marker_count += 1
        
        return chart
    
    def save_marker_as_png(
        self,
        marker_id: int,
        output_file: str,
        pixels_per_inch: int = 300
    ):
        """
        マーカーをPNG形式で保存します。
        
        Args:
            marker_id: マーカーID
            output_file: 出力ファイルパス
            pixels_per_inch: 解像度 (DPI相当)
        """
        marker = self.generate_marker(marker_id, pixels_per_inch)
        cv2.imwrite(output_file, marker)
        print(f"マーカー {marker_id} を保存しました: {output_file}")
    
    def save_chart_as_png(
        self,
        output_file: str,
        num_cols: int = 4,
        num_rows: int = 4,
        start_id: int = 0,
        margin_pixels: int = 50
    ):
        """
        チャート画像をPNG形式で保存します。
        
        Args:
            output_file: 出力ファイルパス
            num_cols: 列数
            num_rows: 行数
            start_id: 開始ID
            margin_pixels: マージン（ピクセル）
        """
        chart = self.generate_marker_chart(num_cols, num_rows, start_id, margin_pixels)
        cv2.imwrite(output_file, chart)
        print(f"マーカーチャート ({num_rows}×{num_cols}) を保存しました: {output_file}")
    
    def save_marker_as_pdf(
        self,
        marker_id: int,
        output_file: str,
        dpi: int = 300
    ):
        """
        マーカーをPDF形式で保存します。
        
        注: reportlab が必要です。インストール: pip install reportlab
        
        Args:
            marker_id: マーカーID
            output_file: 出力ファイルパス
            dpi: 解像度
        """
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import inch
            
            # マーカーを画像として生成
            marker = self.generate_marker(marker_id, dpi)
            
            # マーカーサイズをインチで計算
            marker_size_inches = self.marker_size_m * 100 / 2.54
            
            # PDF作成
            pdf_width = (marker_size_inches + 0.5) * inch
            pdf_height = (marker_size_inches + 0.5) * inch
            
            c = canvas.Canvas(output_file, pagesize=(pdf_width, pdf_height))
            
            # 画像を一時ファイルに保存して埋め込む
            temp_file = "__temp_marker.png"
            cv2.imwrite(temp_file, marker)
            c.drawImage(temp_file, 0.25*inch, 0.25*inch, 
                       width=marker_size_inches*inch, 
                       height=marker_size_inches*inch)
            c.save()
            
            # 一時ファイル削除
            if os.path.exists(temp_file):
                os.remove(temp_file)
            
            print(f"マーカー {marker_id} をPDFで保存しました: {output_file}")
        
        except ImportError:
            print("エラー: reportlab と Pillow が必要です。")
            print("インストールコマンド: pip install reportlab Pillow")
    
    def save_chart_as_pdf(
        self,
        output_file: str,
        num_cols: int = 4,
        num_rows: int = 4,
        start_id: int = 0,
        dpi: int = 300
    ):
        """
        チャート画像をPDF形式で保存します。
        
        Args:
            output_file: 出力ファイルパス
            num_cols: 列数
            num_rows: 行数
            start_id: 開始ID
            dpi: 解像度
        """
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import inch
            
            # チャートを画像として生成
            chart = self.generate_marker_chart(num_cols, num_rows, start_id)
            
            # チャートサイズを計算
            marker_size_inches = self.marker_size_m * 100 / 2.54
            margin_inches = 0.4
            chart_width = (num_cols * marker_size_inches + (num_cols + 1) * margin_inches) * inch
            chart_height = (num_rows * marker_size_inches + (num_rows + 1) * margin_inches) * inch
            
            # PDF作成
            c = canvas.Canvas(output_file, pagesize=(chart_width, chart_height))
            
            # 画像を一時ファイルに保存して埋め込む
            temp_file = "__temp_chart.png"
            cv2.imwrite(temp_file, chart)
            c.drawImage(temp_file, 0, 0, width=chart_width, height=chart_height)
            c.save()
            
            # 一時ファイル削除
            if os.path.exists(temp_file):
                os.remove(temp_file)
            
            print(f"マーカーチャート ({num_rows}×{num_cols}) をPDFで保存しました: {output_file}")
        
        except ImportError:
            print("エラー: reportlab が必要です。")
            print("インストールコマンド: pip install reportlab")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="ArUco マーカーを生成してプリント用ファイルを出力します"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="設定ファイルのパス (デフォルト: config.yaml)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="aruco_marker",
        help="出力ファイル名（拡張子なし） (デフォルト: aruco_marker)"
    )
    
    parser.add_argument(
        "--format",
        type=str,
        choices=["png", "pdf"],
        default="png",
        help="出力形式 (デフォルト: png)"
    )
    
    parser.add_argument(
        "--chart",
        action="store_true",
        help="単一マーカーではなくチャート（複数マーカー）を生成"
    )
    
    parser.add_argument(
        "--cols",
        type=int,
        default=4,
        help="チャートの列数 (デフォルト: 4)"
    )
    
    parser.add_argument(
        "--rows",
        type=int,
        default=4,
        help="チャートの行数 (デフォルト: 4)"
    )
    
    parser.add_argument(
        "--start-id",
        type=int,
        default=0,
        help="チャート生成時の開始マーカーID (デフォルト: 0)"
    )
    
    parser.add_argument(
        "--marker-id",
        type=int,
        default=None,
        help="単一マーカー生成時のマーカーID (デフォルト: config.yaml の値)"
    )
    
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="出力解像度 (DPI、デフォルト: 300)"
    )
    
    args = parser.parse_args()
    
    # マーカー生成器を初期化
    try:
        generator = ArUcoMarkerGenerator(config_file=args.config)
    except Exception as e:
        print(f"初期化エラー: {e}")
        return 1
    
    # 出力ファイル名を作成
    output_ext = ".pdf" if args.format == "pdf" else ".png"
    output_file = args.output if args.output.endswith(output_ext) else args.output + output_ext
    
    try:
        if args.chart:
            # チャート生成
            if args.format == "pdf":
                generator.save_chart_as_pdf(
                    output_file,
                    num_cols=args.cols,
                    num_rows=args.rows,
                    start_id=args.start_id,
                    dpi=args.dpi
                )
            else:
                generator.save_chart_as_png(
                    output_file,
                    num_cols=args.cols,
                    num_rows=args.rows,
                    start_id=args.start_id
                )
        else:
            # 単一マーカー生成
            marker_id = args.marker_id if args.marker_id is not None else generator.marker_id
            
            if marker_id is None:
                print("エラー: マーカーIDが指定されていません。")
                print("--marker-id オプションか config.yaml の expected_id を指定してください。")
                return 1
            
            if args.format == "pdf":
                generator.save_marker_as_pdf(
                    marker_id,
                    output_file,
                    dpi=args.dpi
                )
            else:
                generator.save_marker_as_png(
                    marker_id,
                    output_file,
                    pixels_per_inch=args.dpi
                )
        
        print(f"\n✓ ファイルが正常に生成されました: {output_file}")
        return 0
    
    except Exception as e:
        print(f"エラー: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
