"""
カメラハンドラーモジュール
USB カメラからリアルタイムでフレームを取得します。
"""

import cv2
import numpy as np
from typing import Optional, Tuple, List


class CameraHandler:
    """USB カメラからのフレーム取得を管理するクラス"""
    
    def __init__(self, camera_id: int = 0):
        """
        カメラハンドラーを初期化します。
        
        Args:
            camera_id: 使用するカメラデバイスID（デフォルト: 0）
        """
        self.camera_id = camera_id
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
            self.cap = cv2.VideoCapture(self.camera_id)
            
            if not self.cap.isOpened():
                print(f"エラー: カメラ {self.camera_id} を開くことができません。")
                return False
            
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
    def get_camera_info_list() -> list:
        """
        利用可能なカメラのリストと詳細情報を取得します（製品名自動取得版）。
        
        Returns:
            list: カメラ情報リスト [{'id': 0, 'width': 640, 'height': 480, 'fps': 30.0, 'name': '...'}, ...]
        """
        from camera_name_util import get_camera_info_list_with_names
        
        return get_camera_info_list_with_names()
