#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
カメラデバイス名取得ユーティリティ
pygrabber（DirectShow）を使用してカメラ製品名を自動取得します。
"""

from typing import Dict, Optional
import cv2

# グローバルキャッシュ
_camera_info_cache: Optional[list] = None


def get_camera_names_auto() -> Dict[int, str]:
    """
    pygrabber を使用してカメラ製品名を自動取得します。
    pygrabber がインストールされていない場合は空の辞書を返します。
    
    Returns:
        Dict[int, str]: {カメラID: 製品名}
    """
    try:
        from pygrabber.dshow_graph import FilterGraph
        
        devices = FilterGraph().get_input_devices()
        camera_names = {}
        
        for device_index, device_name in enumerate(devices):
            camera_names[device_index] = device_name
        
        return camera_names
    except ImportError:
        # pygrabber not installed - fall back to generic camera names
        return {}
    except Exception:
        # Camera name detection failed - fall back to generic camera names
        return {}


def get_camera_info_list_with_names() -> list:
    """
    利用可能なカメラのリストと詳細情報を取得します（キャッシング対応版）。
    初回は全カメラを検出、2回目以降はキャッシュから返す（応答性向上）。
    
    Returns:
        list: カメラ情報リスト
    """
    global _camera_info_cache
    
    # キャッシュが存在する場合はそれを返す
    if _camera_info_cache is not None:
        return _camera_info_cache
    
    import threading
    
    camera_info_list = []
    
    # [1] pygrabber から利用可能なカメラを取得
    camera_names_dict = {}
    try:
        from pygrabber.dshow_graph import FilterGraph
        
        graph = FilterGraph()
        devices = graph.get_input_devices()
        
        for device_index, device_name in enumerate(devices):
            camera_names_dict[device_index] = device_name
    
    except (ImportError, Exception):
        pass  # pygrabber が利用できない場合はスキップ
    
    # [2] pygrabber からカメラ一覧を取得できた場合はそれを使う
    if camera_names_dict:
        # pygrabber が検出したカメラのみ処理
        for camera_id, camera_name in camera_names_dict.items():
            try:
                # 高速取得: cv2.VideoCapture はタイムアウト付き
                cap = cv2.VideoCapture(camera_id)
                
                if cap.isOpened():
                    try:
                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        fps = cap.get(cv2.CAP_PROP_FPS)
                        
                        camera_info = {
                            'id': camera_id,
                            'width': width,
                            'height': height,
                            'fps': fps,
                            'name': camera_name
                        }
                        camera_info_list.append(camera_info)
                    
                    finally:
                        cap.release()
            
            except Exception:
                pass
    
    # [3] フォールバック: pygrabber が利用できない場合のみスキャン（タイムアウト付き）
    else:
        def test_camera(camera_id, results):
            """カメラの存在と情報を取得"""
            try:
                cap = cv2.VideoCapture(camera_id)
                
                if cap.isOpened():
                    try:
                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        fps = cap.get(cv2.CAP_PROP_FPS)
                        
                        camera_info = {
                            'id': camera_id,
                            'width': width,
                            'height': height,
                            'fps': fps,
                            'name': f"Camera {camera_id}"
                        }
                        results.append(camera_info)
                    
                    finally:
                        cap.release()
            
            except Exception:
                pass
        
        # スレッドでパラレル実行
        results = []
        threads = []
        for camera_id in range(10):
            thread = threading.Thread(target=test_camera, args=(camera_id, results), daemon=True)
            thread.start()
            threads.append((camera_id, thread))
        
        # 各スレッドの完了を待機（タイムアウト: 0.2秒/スレッド）
        for camera_id, thread in threads:
            thread.join(timeout=0.2)
        
        camera_info_list = sorted(results, key=lambda x: x['id'])
    
    # キャッシュに保存
    _camera_info_cache = camera_info_list
    
    return camera_info_list


if __name__ == "__main__":
    # テスト実行
    print("=" * 60)
    print("Auto Camera Detection Test")
    print("=" * 60)
    print()
    
    print("[1] Detecting camera names via pygrabber...")
    camera_names = get_camera_names_auto()
    if camera_names:
        print(f"Found {len(camera_names)} camera names:")
        for cam_id, name in camera_names.items():
            print(f"  Camera {cam_id}: {name}")
    else:
        print("pygrabber not available or no cameras detected")
    print()
    
    print("[2] Getting detailed camera info...")
    camera_info_list = get_camera_info_list_with_names()
    for info in camera_info_list:
        print(f"  Camera {info['id']}: {info['name']} ({info['width']}x{info['height']} @ {info['fps']:.1f}fps)")
    print()
