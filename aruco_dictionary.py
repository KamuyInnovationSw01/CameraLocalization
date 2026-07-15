"""ArUco辞書の共有定義。"""

import cv2


ARUCO_DICTIONARY_NAMES = {
    "DICT_4X4_50": cv2.aruco.DICT_4X4_50,
    "DICT_5X5_100": cv2.aruco.DICT_5X5_100,
    "DICT_6X6_250": cv2.aruco.DICT_6X6_250,
    "DICT_ARUCO_ORIGINAL": cv2.aruco.DICT_ARUCO_ORIGINAL,
}


def get_aruco_dictionary(dictionary_name: str):
    """名前に対応するArUco辞書を返します。"""
    dictionary_id = ARUCO_DICTIONARY_NAMES.get(
        dictionary_name,
        ARUCO_DICTIONARY_NAMES["DICT_4X4_50"],
    )
    return cv2.aruco.getPredefinedDictionary(dictionary_id)
