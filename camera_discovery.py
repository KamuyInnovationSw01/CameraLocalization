"""カメラ一覧、製品名、基本情報の検出。"""

from dataclasses import dataclass
from typing import Optional
import threading

import cv2


@dataclass(frozen=True)
class CameraInfo:
    id: int
    width: int
    height: int
    fps: float
    name: str


_camera_info_cache: Optional[list[CameraInfo]] = None


def get_camera_info_list() -> list[CameraInfo]:
    """利用可能なカメラを検出し、製品名と基本情報を返します。"""
    global _camera_info_cache
    if _camera_info_cache is not None:
        return _camera_info_cache

    camera_info_list: list[CameraInfo] = []
    camera_names: dict[int, str] = {}
    try:
        from pygrabber.dshow_graph import FilterGraph

        devices = FilterGraph().get_input_devices()
        camera_names = {index: name for index, name in enumerate(devices)}
    except (ImportError, Exception):
        pass

    if camera_names:
        for camera_id, camera_name in camera_names.items():
            info = _read_camera_info(camera_id, camera_name)
            if info is not None:
                camera_info_list.append(info)
    else:
        results: list[CameraInfo] = []
        threads = []
        for camera_id in range(10):
            thread = threading.Thread(
                target=_append_camera_info,
                args=(camera_id, results),
                daemon=True,
            )
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join(timeout=0.2)
        camera_info_list = sorted(results, key=lambda info: info.id)

    _camera_info_cache = camera_info_list
    return camera_info_list


def _append_camera_info(camera_id: int, results: list[CameraInfo]) -> None:
    info = _read_camera_info(camera_id, f"Camera {camera_id}")
    if info is not None:
        results.append(info)


def _read_camera_info(camera_id: int, name: str) -> Optional[CameraInfo]:
    try:
        cap = cv2.VideoCapture(camera_id)
        if not cap.isOpened():
            return None

        try:
            return CameraInfo(
                id=camera_id,
                width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                fps=cap.get(cv2.CAP_PROP_FPS),
                name=name,
            )
        finally:
            cap.release()
    except Exception:
        return None
