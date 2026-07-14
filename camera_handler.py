"""
カメラハンドラーモジュール
USB カメラからリアルタイムでフレームを取得します。
"""

import cv2
import numpy as np
from typing import Optional, Tuple, List


class CameraHandler:
    """USB カメラからのフレーム取得を管理するクラス"""
    
    def __init__(self, camera_id: int = 0, width: int = None, height: int = None):
        """
        カメラハンドラーを初期化します。
        
        Args:
            camera_id: 使用するカメラデバイスID（デフォルト: 0）
            width: 要求する解像度幅（デフォルト: Noneで自動）
            height: 要求する解像度高さ（デフォルト: Noneで自動）
        """
        self.camera_id = camera_id
        self.requested_width = width
        self.requested_height = height
        self.cap = None
        self.width = None
        self.height = None
        self.fps = None
        
    def initialize(self) -> bool:
        """
        カメラを初期化します。
        
        Returns:
            bool: 初期化が成功したかどうか
        """
        try:
            # DirectShow バックエンドを使用（Windows）
            self.cap = cv2.VideoCapture(self.camera_id, cv2.CAP_DSHOW)
            
            if not self.cap.isOpened():
                print(f"エラー: カメラ {self.camera_id} を開くことができません。")
                return False
            
            # 解像度を設定（要求されている場合）
            if self.requested_width is not None and self.requested_height is not None:
                # 設定前に現在の値をリセット
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                
                # 要求された解像度を設定
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.requested_width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.requested_height)
                
                # フレームレート設定（30FPS を推奨）
                self.cap.set(cv2.CAP_PROP_FPS, 30)
                
                # バッファサイズを最小化
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # 設定を安定させるため、数フレーム読み込み
            for _ in range(5):
                ret, _ = self.cap.read()
                if not ret:
                    # フレーム取得失敗時は別バックエンドを試す
                    self.cap.release()
                    print(f"⚠ DirectShow バックエンドでフレーム取得失敗。別バックエンドを試します...")
                    self.cap = cv2.VideoCapture(self.camera_id)
                    
                    if not self.cap.isOpened():
                        print(f"エラー: カメラ {self.camera_id} を開くことができません。")
                        return False
                    
                    # 通常バックエンド での設定
                    if self.requested_width is not None and self.requested_height is not None:
                        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.requested_width)
                        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.requested_height)
                    
                    break
            
            # カメラプロパティを取得
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            print(f"カメラ初期化成功: {self.width}x{self.height} @ {self.fps} FPS")
            return True
            
        except Exception as e:
            print(f"カメラ初期化エラー: {e}")
            return False
    
    def get_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        カメラからフレームを取得します。
        
        Returns:
            Tuple[bool, Optional[np.ndarray]]: (成功フラグ, フレーム画像)
        """
        if self.cap is None:
            return False, None
        
        ret, frame = self.cap.read()
        
        if not ret:
            print("フレーム読み込みエラー")
            return False, None
        
        return True, frame
    
    def release(self):
        """カメラをリリースします。"""
        if self.cap is not None:
            self.cap.release()
            print("カメラをリリースしました。")
    
    def get_resolution(self) -> Tuple[int, int]:
        """
        カメラの解像度を取得します。
        
        Returns:
            Tuple[int, int]: (幅, 高さ)
        """
        return self.width, self.height
    
    @staticmethod
    def list_available_cameras() -> List[int]:
        """
        利用可能なカメラのリストを取得します。
        
        Returns:
            List[int]: 利用可能なカメラのID リスト
        """
        available_cameras = []
        
        for i in range(10):  # 最大10台を検査
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available_cameras.append(i)
                cap.release()
        
        return available_cameras
    
    @staticmethod
    def get_available_resolutions(camera_id: int, timeout_sec: float = 10.0) -> List[Tuple[int, int]]:
        """
        指定したカメラの利用可能な解像度を取得します。
        DirectShow APIから直接フォーマット情報を取得します。
        
        Args:
            camera_id: カメラのID
            timeout_sec: 処理のタイムアウト（秒）- デフォルト 10秒
        
        Returns:
            List[Tuple[int, int]]: [(width, height), ...] 形式（大きい順）
        """
        import threading
        
        available_resolutions = []
        
        def get_formats_via_pygrabber():
            nonlocal available_resolutions
            
            try:
                from pygrabber.dshow_graph import FilterGraph
                
                graph = FilterGraph()
                
                try:
                    # デバイスを追加
                    graph.add_video_input_device(camera_id)
                    
                    # 追加した入力デバイスを取得
                    device = graph.get_input_device()
                    
                    if device is None:
                        return
                    
                    # デバイスの対応フォーマットを取得
                    formats = device.get_formats()
                    
                    if not formats:
                        return
                    
                    # 重複を排除して解像度をリストアップ
                    resolutions_set = set()
                    for fmt in formats:
                        # fmt は辞書形式: {'width': int, 'height': int, ...}
                        if isinstance(fmt, dict):
                            if 'width' in fmt and 'height' in fmt:
                                width = int(fmt['width'])
                                height = int(fmt['height'])
                                resolutions_set.add((width, height))
                    
                    available_resolutions = sorted(list(resolutions_set), reverse=True)
                
                finally:
                    # グラフのクリーンアップ
                    try:
                        graph.remove_filters()
                    except:
                        pass
            
            except ImportError:
                # pygrabber が利用できない場合はフォールバック
                get_formats_fallback()
            
            except Exception as e:
                # DirectShow取得失敗時はフォールバック
                get_formats_fallback()
        
        def get_formats_fallback():
            """フォールバック: 標準解像度をテスト"""
            nonlocal available_resolutions
            
            # 包括的な標準解像度リスト
            standard_resolutions = [
                (4096, 2160), (3840, 2160),
                (2560, 1920), (2560, 1600), (2560, 1440),
                (2048, 1536),
                (1920, 1440), (1920, 1200), (1920, 1080),
                (1600, 1200),
                (1440, 1080), (1280, 1024), (1280, 960),
                (1280, 800), (1280, 720),
                (1024, 768), (960, 720), (800, 600),
                (720, 576), (720, 480), (640, 480),
                (480, 360), (320, 240),
            ]
            
            cap = None
            try:
                cap = cv2.VideoCapture(camera_id)
                if not cap.isOpened():
                    return
                
                for width, height in standard_resolutions:
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                    
                    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    
                    if actual_width == width and actual_height == height:
                        if (width, height) not in available_resolutions:
                            available_resolutions.append((width, height))
            
            finally:
                if cap is not None:
                    cap.release()
        
        # スレッドで実行（タイムアウト機能付き）
        thread = threading.Thread(target=get_formats_via_pygrabber, daemon=True)
        thread.start()
        thread.join(timeout=timeout_sec)
        
        return available_resolutions
    
    @staticmethod
    def get_camera_info_list() -> list:
        """
        利用可能なカメラのリストと詳細情報を取得します（製品名自動取得版）。
        
        Returns:
            list: カメラ情報リスト [{'id': 0, 'width': 640, 'height': 480, 'fps': 30.0, 'name': '...'}, ...]
        """
        from camera_name_util import get_camera_info_list_with_names
        
        return get_camera_info_list_with_names()
