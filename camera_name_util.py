#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
カメラデバイス名取得ユーティリティ
pygrabber（DirectShow）を使用してカメラ製品名を自動取得します。
"""

from typing import Dict
import cv2


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
        return {}
    except Exception:
        return {}


def get_camera_info_list_with_names() -> list:
    """
    利用可能なカメラのリストと詳細情報を取得します（製品名自動取得版）。
    
    Returns:
        list: カメラ情報リスト
    """
    camera_info_list = []
    
    # pygrabberから製品名を取得
    camera_names = get_camera_names_auto()
    
    # 利用可能なカメラをスキャン
    for camera_id in range(10):
        cap = cv2.VideoCapture(camera_id)
        if cap.isOpened():
            try:
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                
                # カメラ名を取得（pygrabberから取得、なければID）
                camera_name = camera_names.get(camera_id)
                if not camera_name:
                    camera_name = f"Camera {camera_id}"
                
                camera_info = {
                    'id': camera_id,
                    'width': width,
                    'height': height,
                    'fps': fps,
                    'name': camera_name
                }
                camera_info_list.append(camera_info)
            except Exception as e:
                print(f"カメラ {camera_id} の情報取得エラー: {e}")
            finally:
                cap.release()
    
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
