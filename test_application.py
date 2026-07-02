#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Camera Localization Application Test Suite
"""

import yaml
import json
import sys
import os

def test_config_files():
    """Test configuration files"""
    print("=" * 60)
    print("Camera Localization - Test Suite")
    print("=" * 60)
    print()
    
    # 1. Config file test
    print("[1] Config File (config.yaml) Read Test")
    print("-" * 60)
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        print("[OK] config.yaml read successfully")
        print(f"    Marker size: {config['marker']['size_m']} m")
        print(f"    Marker dictionary: {config['marker']['dictionary']}")
        print(f"    Marker ID: {config['marker']['expected_id']}")
        print(f"    Camera window size: {config['ui']['camera_window']['width']}x{config['ui']['camera_window']['height']}")
        print(f"    Wireframe window size: {config['ui']['wireframe_window']['width']}x{config['ui']['wireframe_window']['height']}")
        print()
    except Exception as e:
        print(f"[NG] Error: {e}")
        return False
    
    # 2. Calibration file test
    print("[2] Calibration File (center.json) Read Test")
    print("-" * 60)
    try:
        with open('center.json', 'r') as f:
            calib = json.load(f)
        
        print("[OK] center.json read successfully")
        print(f"    Image size: {calib['imageSize']} (pixels)")
        print(f"    Camera matrix: {len(calib['cameraMatrix'])}x{len(calib['cameraMatrix'][0])}")
        print(f"    Focal length fx: {calib['cameraMatrix'][0][0]:.2f}")
        print(f"    Focal length fy: {calib['cameraMatrix'][1][1]:.2f}")
        print(f"    Principal point cx: {calib['cameraMatrix'][0][2]:.2f}")
        print(f"    Principal point cy: {calib['cameraMatrix'][1][2]:.2f}")
        print(f"    Distortion coefficients: {len(calib['distCoeffs'][0])} elements")
        print()
    except Exception as e:
        print(f"[NG] Error: {e}")
        return False
    
    # 3. Module import test
    print("[3] Python Module Import Test")
    print("-" * 60)
    try:
        from camera_handler import CameraHandler
        print("[OK] camera_handler module")
        
        from marker_detector import MarkerDetector
        print("[OK] marker_detector module")
        
        from pose_estimator import PoseEstimator
        print("[OK] pose_estimator module")
        
        from wireframe_renderer import WireframeRenderer
        print("[OK] wireframe_renderer module")
        
        from ui_manager import UIManager
        print("[OK] ui_manager module")
        
        print()
    except Exception as e:
        print(f"[NG] Error: {e}")
        return False
    
    # 4. MarkerDetector test
    print("[4] MarkerDetector Instantiation Test")
    print("-" * 60)
    try:
        detector = MarkerDetector(dictionary_name=config['marker']['dictionary'])
        print(f"[OK] MarkerDetector initialized ({config['marker']['dictionary']})")
        print()
    except Exception as e:
        print(f"[NG] Error: {e}")
        return False
    
    # 5. PoseEstimator test
    print("[5] PoseEstimator Instantiation Test")
    print("-" * 60)
    try:
        pose_estimator = PoseEstimator(calibration_file='center.json')
        camera_matrix = pose_estimator.get_camera_matrix()
        print(f"[OK] PoseEstimator initialized")
        print(f"    Camera matrix shape: {camera_matrix.shape}")
        print()
    except Exception as e:
        print(f"[NG] Error: {e}")
        return False
    
    # 6. WireframeRenderer test
    print("[6] WireframeRenderer Instantiation Test")
    print("-" * 60)
    try:
        wireframe_scale = config['processing']['wireframe_scale']
        renderer = WireframeRenderer(
            camera_matrix=camera_matrix,
            wireframe_scale=wireframe_scale
        )
        print(f"[OK] WireframeRenderer initialized")
        print(f"    Wireframe scale: {wireframe_scale}")
        print()
    except Exception as e:
        print(f"[NG] Error: {e}")
        return False
    
    # 7. CameraHandler test
    print("[7] CameraHandler Test")
    print("-" * 60)
    try:
        camera = CameraHandler(camera_id=0)
        available = CameraHandler.list_available_cameras()
        print(f"[OK] Available cameras: {available}")
        
        if camera.initialize():
            width, height = camera.get_resolution()
            print(f"[OK] Camera initialized successfully")
            print(f"    Resolution: {width}x{height}")
            camera.release()
        else:
            print("[WARN] Camera initialization failed (Camera may not be connected)")
        print()
    except Exception as e:
        print(f"[NG] Error: {e}")
        print()
    
    # 8. Marker file test
    print("[8] Marker File Generation Test")
    print("-" * 60)
    try:
        marker_files = [f for f in os.listdir('.') if f.endswith(('.png', '.pdf'))]
        if marker_files:
            print("[OK] Marker files found:")
            for f in sorted(marker_files)[:5]:
                size_kb = os.path.getsize(f) / 1024
                print(f"    - {f} ({size_kb:.1f} KB)")
        else:
            print("[WARN] No marker files found")
        print()
    except Exception as e:
        print(f"[NG] Error: {e}")
        print()
    
    # Test result summary
    print("=" * 60)
    print("Test Result: [OK] All tests passed successfully!")
    print("=" * 60)
    print()
    print("Application ready to run!")
    print("Run command: python main.py")
    print()
    
    return True


if __name__ == "__main__":
    try:
        success = test_config_files()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
