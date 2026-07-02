#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Camera Selection Feature - Demo Script
"""

from camera_handler import CameraHandler

def demo_camera_selection():
    """カメラ選択機能のデモンストレーション"""
    print("=" * 60)
    print("Camera Selection Demo with Auto Detection")
    print("=" * 60)
    print()
    
    # 利用可能なカメラ情報を取得
    print("[1] Detecting available cameras...")
    camera_info_list = CameraHandler.get_camera_info_list()
    
    if not camera_info_list:
        print("No cameras found!")
        return False
    
    print()
    print("Available cameras:")
    for i, info in enumerate(camera_info_list):
        print(f"  [{i}] Camera ID {info['id']:d} - {info['name']} ({info['width']:d}x{info['height']:d} @ {info['fps']:.1f}fps)")
    print()
    
    # カメラ選択ロジック
    if len(camera_info_list) == 1:
        camera_id = camera_info_list[0]['id']
        info = camera_info_list[0]
        print(f"Only 1 camera available. Using camera {camera_id} ({info['name']})")
        print()
    else:
        print("Multiple cameras detected.")
        print("(In actual application, user would be prompted to select)")
        print()
        
        # デモ：最初のカメラを選択
        camera_id = camera_info_list[0]['id']
        info = camera_info_list[0]
        print(f"Selected: Camera {camera_id} ({info['name']})")
        print()
    
    # 選択したカメラで初期化
    print(f"[2] Initializing camera {camera_id}...")
    camera = CameraHandler(camera_id=camera_id)
    
    if camera.initialize():
        width, height = camera.get_resolution()
        print(f"[OK] Camera initialized successfully")
        print(f"    Resolution: {width}x{height}")
        camera.release()
        print()
        return True
    else:
        print(f"[NG] Failed to initialize camera {camera_id}")
        print()
        return False


if __name__ == "__main__":
    print()
    success = demo_camera_selection()
    print("=" * 60)
    if success:
        print("Result: [OK] Camera selection demo completed successfully")
    else:
        print("Result: [NG] Camera selection demo failed")
    print("=" * 60)
    print()
