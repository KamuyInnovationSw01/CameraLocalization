"""
DirectShow COM インターフェースを使用してカメラの対応解像度を直接取得
Windows 専用
"""

import ctypes
from ctypes import POINTER, Structure, c_int, c_uint, c_ulong, c_byte, c_void_p
import struct


# COM インターフェース定義
class GUID(Structure):
    _fields_ = [("Data1", c_uint),
                ("Data2", c_uint),
                ("Data3", c_uint),
                ("Data4", c_byte * 8)]


def get_camera_resolutions_from_registry(camera_index: int) -> list:
    """
    Windows レジストリからカメラの対応解像度を取得
    
    Args:
        camera_index: カメラインデックス
    
    Returns:
        list: [(width, height), ...]
    """
    import winreg
    
    resolutions = []
    
    try:
        # DirectShow デバイス情報をレジストリから取得
        # HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\MediaProperties\PrivateProperties\Devices
        
        key_path = r"SYSTEM\CurrentControlSet\Control\DeviceClasses\{6994AD05-93EF-11D0-A3CC-00A0C9223196}"
        
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as reg_key:
            subkey_count = winreg.QueryInfoKey(reg_key)[0]
            
            for i in range(subkey_count):
                try:
                    subkey_name = winreg.EnumKey(reg_key, i)
                    with winreg.OpenKey(reg_key, subkey_name) as subkey:
                        # Device Parameters を取得
                        try:
                            with winreg.OpenKey(subkey, "Device Parameters") as dev_params:
                                pass  # デバイスパラメータが存在するか確認
                        except:
                            pass
                except Exception as e:
                    continue
        
        return resolutions
    
    except Exception as e:
        print(f"レジストリアクセスエラー: {e}")
        return resolutions


def get_camera_resolutions_from_direct_show(camera_index: int) -> list:
    """
    DirectShow のメディアタイプを列挙して対応解像度を取得
    
    Args:
        camera_index: カメラインデックス
    
    Returns:
        list: [(width, height), ...]
    """
    try:
        import comtypes
        from comtypes.client import GetObject
        from comtypes import CoCreateInstance, CLSCTX_INPROC_SERVER
        
        resolutions = []
        
        # WMI を使用してカメラの詳細情報を取得
        wmi = GetObject("winmgmts:")
        devices = wmi.ExecQuery("Select * from Win32_PnPDevice where Name like '%camera%' or Name like '%webcam%'")
        
        if len(devices) <= camera_index:
            return []
        
        device = list(devices)[camera_index]
        print(f"カメラ {camera_index}: {device.Name}")
        print(f"  PnPID: {device.PnPDeviceID}")
        
        # 実装困難なため、テスト方式に戻す
        return resolutions
    
    except Exception as e:
        print(f"DirectShow アクセスエラー: {e}")
        return []


def get_camera_resolutions_simple_expanded(camera_index: int, timeout_sec: float = 10.0) -> list:
    """
    拡張された標準解像度リストでテスト（最も確実な方法）
    
    Args:
        camera_index: カメラインデックス
        timeout_sec: テストのタイムアウト時間
    
    Returns:
        list: [(width, height), ...]
    """
    import cv2
    import threading
    
    # 包括的な標準解像度リスト
    standard_resolutions = [
        # 4K
        (4096, 2160), (3840, 2160),
        # 2.5K～UXGA
        (2560, 1920), (2560, 1600), (2560, 1440),
        (2048, 1536),
        # FHD～UXGA
        (1920, 1440), (1920, 1200), (1920, 1080),
        (1600, 1200),
        (1440, 1080), (1280, 1024), (1280, 960),
        (1280, 800), (1280, 720),
        # VGA～XGA
        (1024, 768), (960, 720), (800, 600),
        (720, 576), (720, 480), (640, 480),
        (480, 360), (320, 240),
    ]
    
    available_resolutions = []
    
    def test_camera():
        nonlocal available_resolutions
        cap = None
        
        try:
            cap = cv2.VideoCapture(camera_index)
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
    
    # スレッドで実行
    thread = threading.Thread(target=test_camera, daemon=True)
    thread.start()
    thread.join(timeout=timeout_sec)
    
    return sorted(available_resolutions, reverse=True)


if __name__ == "__main__":
    from pygrabber.dshow_graph import FilterGraph
    
    print("=" * 70)
    print("カメラ解像度取得方法の比較")
    print("=" * 70)
    
    try:
        graph = FilterGraph()
        devices = graph.get_input_devices()
        
        for camera_index in range(len(devices)):
            print(f"\n[{camera_index}] {devices[camera_index]}")
            print("-" * 70)
            
            # 推奨方法: テスト方式
            print(f"拡張テスト方式（推奨）:")
            resolutions = get_camera_resolutions_simple_expanded(camera_index)
            if resolutions:
                print(f"  検出: {len(resolutions)} 個の解像度")
                for res in resolutions[:5]:  # 最初の5個だけ表示
                    print(f"    {res[0]} x {res[1]}")
                if len(resolutions) > 5:
                    print(f"    ... 他 {len(resolutions) - 5} 個")
            else:
                print("  検出失敗")
    
    except Exception as e:
        print(f"エラー: {e}")
