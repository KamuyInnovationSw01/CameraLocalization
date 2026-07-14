"""
3D ワイヤフレーム描画モジュール
カメラのポーズをフラスタム + ボディ + 光軸矢印で描画します。
"""

import numpy as np
import cv2
from typing import Optional, Tuple

# matplotlib を非対話モードに設定
import matplotlib
matplotlib.use('Agg')  # GUI ウィンドウを表示しない backend
import matplotlib.pyplot as plt
plt.ioff()  # 対話モードを無効化

from matplotlib.backends.backend_agg import FigureCanvasAgg
from mpl_toolkits.mplot3d import Axes3D


class WireframeRenderer:
    """3D ワイヤフレーム描画を行うクラス"""
    
    def __init__(self, camera_matrix: np.ndarray, wireframe_scale: float = 0.15):
        """
        ワイヤフレーム描画器を初期化します。
        
        Args:
            camera_matrix: カメラ行列 (3, 3)
            wireframe_scale: ワイヤフレームのスケール（相対的）
        """
        self.camera_matrix = camera_matrix.copy()
        self.wireframe_scale = wireframe_scale
        
        # ウィンドウサイズ（描画用）
        self.window_width = 960
        self.window_height = 720
        
        # 背景色
        self.bg_color = (50, 50, 50)  # 暗いグレー
    
    def create_camera_wireframe(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        カメラのワイヤフレーム構造を作成します（カメラ座標系）。
        
        仕様:
            - カメラボディ: 幅5cm, 高さ5cm, 奥行き10cm の直方体
            - 視点位置: 前面中央 (0, 0, 0)
            - フラスタム: 視点から奥行き10cm まで
        
        Returns:
            Tuple containing:
                - vertices: 3D 頂点座標 (N, 3)
                - edges: 頂点のインデックスペア (M, 2)
        """
        # カメラボディの寸法（メートル）
        body_width = 0.05   # 5 cm
        body_height = 0.05  # 5 cm
        body_length = 0.1   # 10 cm
        
        # フラスタムの奥行き（メートル）
        frustum_depth = 0.1  # 10 cm
        
        # フラスタム（視点からのピラミッド形）のコーナー座標
        # 視点: (0, 0, 0)
        # 前面（視点直前）: z=0 付近の小さい矩形
        # 背面: z=frustum_depth の大きい矩形
        # 
        # フラスタムのFOV（視野角）を定義（ボディ寸法から推定）
        fov_factor = 1.5  # フラスタムの開き具合
        
        frustum_vertices = np.array([
            [0, 0, 0],                                      # 0: 視点（前面中央）
            # 背面（奥行き10cm）のコーナー
            [-body_width / 2 * fov_factor, -body_height / 2 * fov_factor, frustum_depth],   # 1: 左上奥
            [body_width / 2 * fov_factor, -body_height / 2 * fov_factor, frustum_depth],    # 2: 右上奥
            [body_width / 2 * fov_factor, body_height / 2 * fov_factor, frustum_depth],     # 3: 右下奥
            [-body_width / 2 * fov_factor, body_height / 2 * fov_factor, frustum_depth],    # 4: 左下奥
        ], dtype=np.float32)
        
        # ボディ（直方体）の座標
        # 視点 (z=0) から見て後ろ側 (z < 0) に伸ばす
        body_vertices = np.array([
            # 視点に近い面 (z=0)
            [-body_width / 2, -body_height / 2, 0],   # 5
            [body_width / 2, -body_height / 2, 0],    # 6
            [body_width / 2, body_height / 2, 0],     # 7
            [-body_width / 2, body_height / 2, 0],    # 8
            # 背面 (z=-body_length)
            [-body_width / 2, -body_height / 2, -body_length], # 9
            [body_width / 2, -body_height / 2, -body_length],  # 10
            [body_width / 2, body_height / 2, -body_length],   # 11
            [-body_width / 2, body_height / 2, -body_length],  # 12
        ], dtype=np.float32)
        
        # 光軸矢印（Z軸の正方向、視点から奥へ）
        arrow_length = frustum_depth * 1.2
        arrow_head_size = 0.01
        optical_axis_vertices = np.array([
            [0, 0, 0],                          # 13: 起点（視点）
            [0, 0, arrow_length],               # 14: 先端
            # 矢印の先端部分
            [-arrow_head_size, 0, arrow_length - arrow_head_size * 2],  # 15
            [arrow_head_size, 0, arrow_length - arrow_head_size * 2],   # 16
            [0, -arrow_head_size, arrow_length - arrow_head_size * 2],  # 17
            [0, arrow_head_size, arrow_length - arrow_head_size * 2],   # 18
        ], dtype=np.float32)
        
        # 全頂点を統合
        vertices = np.vstack([frustum_vertices, body_vertices, optical_axis_vertices])
        
        # エッジ定義（頂点インデックスペア）
        # フラスタム: 視点(0)から背面のコーナー(1-4)へのピラミッド
        frustum_edges = np.array([
            [0, 1], [0, 2], [0, 3], [0, 4],  # 視点から背面コーナーへ
            [1, 2], [2, 3], [3, 4], [4, 1],  # 背面の矩形枠
        ])
        
        # ボディ: 幅5cm, 高さ5cm, 奥行き10cm の直方体
        # インデックス: 5-8(前面 z=0), 9-12(背面 z=-0.1m)
        body_edges = np.array([
            [5, 6], [6, 7], [7, 8], [8, 5],   # 前面（z=0）の矩形
            [9, 10], [10, 11], [11, 12], [12, 9],  # 背面（z=-0.1m）の矩形
            [5, 9], [6, 10], [7, 11], [8, 12],  # 側面の線
        ])
        
        # 光軸: 視点から奥へ向かう矢印
        optical_axis_edges = np.array([
            [13, 14],  # 光軸本体
            [14, 15], [14, 16], [14, 17], [14, 18],  # 矢印の先端
        ])
        
        edges = np.vstack([frustum_edges, body_edges, optical_axis_edges])
        
        return vertices, edges
    
    def project_3d_to_2d(
        self,
        vertices_3d: np.ndarray,
        rvec: np.ndarray,
        tvec: np.ndarray
    ) -> np.ndarray:
        """
        3D 頂点を 2D 画像座標に投影します。
        
        Args:
            vertices_3d: 3D 頂点座標 (N, 3)
            rvec: 回転ベクトル (3,)
            tvec: 並進ベクトル (3,)
        
        Returns:
            np.ndarray: 2D 投影座標 (N, 2)
        """
        # カメラ座標系から画像座標系への変換
        image_points, _ = cv2.projectPoints(
            objectPoints=vertices_3d,
            rvec=rvec,
            tvec=tvec,
            cameraMatrix=self.camera_matrix,
            distCoeffs=None
        )
        
        return image_points.reshape(-1, 2)
    
    def draw_wireframe(
        self,
        frame: np.ndarray,
        rvec: np.ndarray,
        tvec: np.ndarray
    ) -> np.ndarray:
        """
        カメラのワイヤフレームをフレームに描画します（2D 投影）。
        
        Args:
            frame: 入力画像
            rvec: 回転ベクトル
            tvec: 並進ベクトル
        
        Returns:
            np.ndarray: ワイヤフレームが描画された画像
        """
        result = frame.copy()
        
        # ワイヤフレーム構造を作成
        vertices_3d, edges = self.create_camera_wireframe()
        
        # 3D頂点を2D投影座標に変換
        vertices_2d = self.project_3d_to_2d(vertices_3d, rvec, tvec)
        
        # エッジを描画
        for edge in edges:
            p1 = tuple(vertices_2d[edge[0]].astype(int))
            p2 = tuple(vertices_2d[edge[1]].astype(int))
            
            # エッジの種類によって色を分ける
            if edge[0] == 0 or edge[1] == 0:  # フラスタムエッジ
                color = (0, 255, 0)  # 緑
                thickness = 2
            elif edge[0] >= 5 and edge[1] >= 5:  # ボディエッジ
                color = (255, 0, 0)  # 青
                thickness = 2
            else:  # 光軸エッジ
                color = (0, 255, 255)  # 黄
                thickness = 3
            
            cv2.line(result, p1, p2, color, thickness)
        
        # 頂点を描画
        for i, vertex in enumerate(vertices_2d):
            pos = tuple(vertex.astype(int))
            if i == 0:  # カメラ原点
                cv2.circle(result, pos, 5, (255, 255, 255), -1)
            elif i >= 13:  # 光軸
                cv2.circle(result, pos, 3, (0, 255, 255), -1)
            else:
                cv2.circle(result, pos, 3, (100, 100, 100), -1)
        
        return result
    
    def draw_3d_view(
        self,
        rvec: np.ndarray,
        tvec: np.ndarray,
        marker_size_m: float = 0.1
    ) -> np.ndarray:
        """
        3D ワイヤフレーム + マーカー + 座標軸の独立したビューを作成します。
        
        Args:
            rvec: 回転ベクトル
            tvec: 並進ベクトル
            marker_size_m: マーカーサイズ（メートル）
        
        Returns:
            np.ndarray: 3D ビュー画像
        """
        # 背景を作成
        view = np.full((self.window_height, self.window_width, 3), 
                       self.bg_color, dtype=np.uint8)
        
        # 1. 3D 形状の定義
        # カメラのワイヤフレーム構造を作成（ローカル座標系）
        vertices_local, camera_edges = self.create_camera_wireframe()
        
        # マーカー頂点の作成（世界座標系、Z=0平面）
        half_marker = marker_size_m / 2.0
        marker_vertices = np.array([
            [-half_marker, -half_marker, 0],
            [half_marker, -half_marker, 0],
            [half_marker, half_marker, 0],
            [-half_marker, half_marker, 0]
        ], dtype=np.float32)
        
        marker_edges = np.array([
            [0, 1], [1, 2], [2, 3], [3, 0]
        ])
        
        # マーカーの座標軸（世界座標系の中心から）
        axis_length = marker_size_m * 1.5
        axis_vertices = np.array([
            [0, 0, 0],                  # 原点
            [axis_length, 0, 0],        # X軸
            [0, axis_length, 0],        # Y軸
            [0, 0, axis_length]         # Z軸
        ], dtype=np.float32)
        
        # 2. カメラ位置・姿勢の計算（カメラ座標 → 世界座標）
        rotation_matrix, _ = cv2.Rodrigues(rvec)
        R_wc = rotation_matrix.T
        camera_pos = (-R_wc @ tvec).ravel()
        
        # カメラローカルの頂点群を世界座標系に変換
        # p_world = R_wc @ p_local + camera_pos
        vertices_world = (R_wc @ vertices_local.T).T + camera_pos
        
        # 3. 仮想第3者カメラ（LookAtビューポーズ）の構築
        # 全体が常にいいパースで画面中央に収まるように仮想カメラの位置とターゲットを動的に調整
        dist = np.linalg.norm(camera_pos)
        dist = max(0.15, dist)  # 最低スケサインターバル
        
        # 注視点はマーカー(原点)から少しカメラ側に寄せた位置
        target = camera_pos * 0.3
        
        # 斜め右上（Xがプラス、Yがマイナス、Zがプラス）から見下ろす基本方向
        view_dir = np.array([0.7, -1.3, 0.9], dtype=np.float32)
        view_dir /= np.linalg.norm(view_dir)
        
        # 仮想カメラの座標
        eye = target + view_dir * (dist * 1.7)
        
        # 仮想カメラの回転/並進行列の計算 (LookAt)
        up = np.array([0, 0, 1], dtype=np.float32)  # 世界座標のZ軸が上方向
        # OpenCVの投影規約ではカメラの+Zが前方なので、注視点へ向かう
        # ベクトルを仮想カメラの+Z軸にする。
        z_axis = target - eye
        z_axis /= np.linalg.norm(z_axis)
        
        # 画像座標のYは下向きなので、マーカーの+Z（正面）を
        # 3Dビュー上方へ表示するには、カメラの+Yを世界の-Zへ向ける。
        # z_axis, x_axis, y_axis の順で右手系を維持する。
        x_axis = np.cross(z_axis, up)
        x_axis_norm = np.linalg.norm(x_axis)
        if x_axis_norm < 1e-5:  # 真上からの特異点回避
            x_axis = np.array([1, 0, 0], dtype=np.float32)
        else:
            x_axis /= x_axis_norm
            
        y_axis = np.cross(z_axis, x_axis)
        
        R_view = np.vstack([x_axis, y_axis, z_axis])  # 3x3
        t_view = -R_view @ eye
        r_view, _ = cv2.Rodrigues(R_view)
        
        # 4. 全ての表示対象が画面内に収まる仮想カメラ行列を作る。
        # 投影前の全頂点から焦点距離と主点を計算することで、カメラが
        # マーカーから離れた場合でも、カメラ本体が画面外へ出ないようにする。
        all_vertices_world = np.vstack([
            marker_vertices,
            axis_vertices,
            vertices_world.astype(np.float32)
        ])
        identity_camera = np.eye(3, dtype=np.float32)
        normalized_points, _ = cv2.projectPoints(
            all_vertices_world,
            r_view,
            t_view,
            identity_camera,
            None
        )
        normalized_points = normalized_points.reshape(-1, 2)

        finite_points = normalized_points[np.isfinite(normalized_points).all(axis=1)]
        if len(finite_points) == 0:
            finite_points = np.zeros((1, 2), dtype=np.float32)

        x_min, y_min = finite_points.min(axis=0)
        x_max, y_max = finite_points.max(axis=0)
        margin = 50.0
        available_width = max(1.0, self.window_width - 2.0 * margin)
        available_height = max(1.0, self.window_height - 2.0 * margin)
        f_virtual = min(
            available_width / max(float(x_max - x_min), 1e-6),
            available_height / max(float(y_max - y_min), 1e-6)
        )
        cx_virtual = self.window_width / 2.0 - f_virtual * (float(x_min) + float(x_max)) / 2.0
        cy_virtual = self.window_height / 2.0 - f_virtual * (float(y_min) + float(y_max)) / 2.0
        K_virtual = np.array([
            [f_virtual, 0, cx_virtual],
            [0, f_virtual, cy_virtual],
            [0, 0, 1]
        ], dtype=np.float32)
        
        # 5. 各3D点群を2D画像座標に投影
        # マーカー
        marker_2d, _ = cv2.projectPoints(marker_vertices, r_view, t_view, K_virtual, None)
        marker_2d = marker_2d.reshape(-1, 2)
        
        # 座標軸
        axis_2d, _ = cv2.projectPoints(axis_vertices, r_view, t_view, K_virtual, None)
        axis_2d = axis_2d.reshape(-1, 2)
        
        # カメラワイヤフレーム
        cam_vertices_2d, _ = cv2.projectPoints(vertices_world.astype(np.float32), r_view, t_view, K_virtual, None)
        cam_vertices_2d = cam_vertices_2d.reshape(-1, 2)
        
        # 6. レンダリング/描画
        # A. マーカー用半透明塗りつぶしと枠線
        try:
            overlay = view.copy()
            cv2.fillPoly(overlay, [marker_2d.astype(np.int32)], (0, 0, 120))  # 濃い赤
            cv2.addWeighted(overlay, 0.25, view, 0.75, 0, view)
            for edge in marker_edges:
                p1 = tuple(marker_2d[edge[0]].astype(int))
                p2 = tuple(marker_2d[edge[1]].astype(int))
                cv2.line(view, p1, p2, (0, 0, 180), 2)  # 赤い枠線
        except Exception:
            pass
            
        # B. 座標軸（世界座標の原点中心、マーカー基準）
        origin = tuple(axis_2d[0].astype(int))
        # X軸 (赤)
        x_pt = tuple(axis_2d[1].astype(int))
        cv2.line(view, origin, x_pt, (0, 0, 255), 2)
        cv2.putText(view, "X_m", (x_pt[0] + 5, x_pt[1] + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        # Y軸 (緑)
        y_pt = tuple(axis_2d[2].astype(int))
        cv2.line(view, origin, y_pt, (0, 255, 0), 2)
        cv2.putText(view, "Y_m", (y_pt[0] + 5, y_pt[1] + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        # Z軸 (青)
        z_pt = tuple(axis_2d[3].astype(int))
        cv2.line(view, origin, z_pt, (255, 0, 0), 2)
        cv2.putText(view, "Z_m", (z_pt[0] + 5, z_pt[1] + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
        
        # C. カメラワイヤフレーム
        for edge in camera_edges:
            p1 = tuple(cam_vertices_2d[edge[0]].astype(int))
            p2 = tuple(cam_vertices_2d[edge[1]].astype(int))
            
            # 各パーツで色を変える
            # インデックス定義:
            # 0: 視点
            # 1-4: フラスタム背面コーナー
            # 5-12: ボディ
            # 13-18: 光軸
            if 0 <= edge[0] <= 4 and 0 <= edge[1] <= 4:  # フラスタムエッジ（視点からの線と背面の枠線）
                color = (255, 255, 0)  # シアン
                thickness = 2
            elif edge[0] >= 13 or edge[1] >= 13:  # 光軸矢印
                color = (0, 255, 255)  # 黄色
                thickness = 2
            else:  # ボディエッジ (5-12)
                color = (0, 165, 255)  # オレンジ
                thickness = 2
                
            cv2.line(view, p1, p2, color, thickness)
            
        # D. カメラ位置のハイライト
        cam_center = tuple(cam_vertices_2d[0].astype(int))
        cv2.circle(view, cam_center, 6, (0, 255, 255), -1)  # 黄色の光学中心マーク
        cv2.circle(view, origin, 6, (255, 255, 0), 2)       # シアンのマーカー原点マーク
        
        # E. テキストレイアウト説明
        cv2.putText(view, "3D View: Camera Pose + Marker Axes", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(view, "Orange: Camera Body | Cyan: Frustum | Yellow: Optical Axis | Red: Marker",
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        return view
    
    def draw_3d_view_matplotlib(
        self,
        rvec: np.ndarray,
        tvec: np.ndarray,
        marker_size_m: float = 0.1
    ) -> np.ndarray:
        """
        matplotlibを使用した3D ビューの作成。
        3次元グリッドボックス + マーカー（底面）+ カメラワイヤフレーム
        
        Args:
            rvec: 回転ベクトル
            tvec: 並進ベクトル
            marker_size_m: マーカーサイズ（メートル）
        
        Returns:
            np.ndarray: RGB画像 (720, 960, 3)
        """
        # matplotlibの図を作成（背景色あり）
        fig = plt.figure(figsize=(960/100, 720/100), dpi=100, facecolor=(0.2, 0.2, 0.2))
        ax = fig.add_subplot(111, projection='3d')
        
        # 回転マトリックスを取得
        rotation_matrix, _ = cv2.Rodrigues(rvec)
        
        # マーカー座標系でのカメラ位置：camera_pos = -R^T @ tvec
        # 反転解補正は pose_estimator 側で実施済みなのでここではそのまま使う
        camera_pos = (-rotation_matrix.T @ tvec).ravel()
        R_wc = rotation_matrix.T   # カメラ座標系 → 世界座標系（表示用）
        
        # グリッドボックスのサイズ（マーカーとカメラが収まるよう自動スケール）
        # XY方向：マーカーとカメラのXYオフセットを包含
        xy_extent = max(marker_size_m, abs(camera_pos[0]), abs(camera_pos[1])) * 1.4
        xy_extent = max(0.2, xy_extent)
        # Z方向：底面(0)からカメラの少し上まで
        box_height = max(0.3, camera_pos[2] * 1.25)
        
        grid_range = np.linspace(-xy_extent, xy_extent, 5)
        z_range = np.linspace(0, box_height, 5)
        
        # 底面グリッド（X-Y平面、z=0：マーカーが置かれる面）
        for g in grid_range:
            ax.plot([g, g], [-xy_extent, xy_extent], [0, 0], 
                   'gray', alpha=0.3, linewidth=0.5)
            ax.plot([-xy_extent, xy_extent], [g, g], [0, 0], 
                   'gray', alpha=0.3, linewidth=0.5)
        
        # 側面グリッド（奥の2面）
        for z in z_range:
            ax.plot([-xy_extent, xy_extent], [xy_extent, xy_extent], [z, z], 
                   'gray', alpha=0.1, linewidth=0.5)
            ax.plot([xy_extent, xy_extent], [-xy_extent, xy_extent], [z, z], 
                   'gray', alpha=0.1, linewidth=0.5)
        
        # ボックスの枠線（底面 z=0、頂面 z=box_height）
        box_vertices = np.array([
            [-xy_extent, -xy_extent, 0],
            [xy_extent, -xy_extent, 0],
            [xy_extent, xy_extent, 0],
            [-xy_extent, xy_extent, 0],
            [-xy_extent, -xy_extent, box_height],
            [xy_extent, -xy_extent, box_height],
            [xy_extent, xy_extent, box_height],
            [-xy_extent, xy_extent, box_height],
        ])
        
        box_edges = [
            [0, 1], [1, 2], [2, 3], [3, 0],  # 底面
            [4, 5], [5, 6], [6, 7], [7, 4],  # 頂面
            [0, 4], [1, 5], [2, 6], [3, 7],  # 側面
        ]
        
        for edge in box_edges:
            p1 = box_vertices[edge[0]]
            p2 = box_vertices[edge[1]]
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], [p1[2], p2[2]], 
                   'white', alpha=0.3, linewidth=1)
        
        # マーカーを底面中央（原点、z=0）に平置きで描画（赤い正方形）
        # マーカーは世界座標系の基準なので回転を適用せずXY平面に配置する
        half_marker = marker_size_m / 2
        marker_corners = np.array([
            [-half_marker, -half_marker, 0],
            [half_marker, -half_marker, 0],
            [half_marker, half_marker, 0],
            [-half_marker, half_marker, 0],
            [-half_marker, -half_marker, 0],  # 閉じる
        ])
        ax.plot(marker_corners[:, 0], marker_corners[:, 1], marker_corners[:, 2],
               'r-', linewidth=3, label='Marker')
        ax.scatter(marker_corners[:4, 0], marker_corners[:4, 1], marker_corners[:4, 2],
                  color='red', s=50, marker='o')
        
        # === カメラの描画 ===
        # カメラ本体（長方形の箱）をカメラ座標系で定義し世界座標へ変換
        cam_scale = marker_size_m * 1.0
        bw, bh, bd = cam_scale * 0.5, cam_scale * 0.5, cam_scale * 1.0  # 幅・高さ・奥行
        body_local = np.array([
            [-bw, -bh, -bd], [bw, -bh, -bd], [bw, bh, -bd], [-bw, bh, -bd],  # 背面
            [-bw, -bh, 0.0], [bw, -bh, 0.0], [bw, bh, 0.0], [-bw, bh, 0.0],  # 前面（レンズ側）
        ])
        body_world = (R_wc @ body_local.T).T + camera_pos
        body_edges = [
            [0, 1], [1, 2], [2, 3], [3, 0],  # 背面
            [4, 5], [5, 6], [6, 7], [7, 4],  # 前面
            [0, 4], [1, 5], [2, 6], [3, 7],  # 奥行
        ]
        for i, edge in enumerate(body_edges):
            p1 = body_world[edge[0]]
            p2 = body_world[edge[1]]
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], [p1[2], p2[2]],
                   'orange', linewidth=2, label='Camera Body' if i == 0 else '')
        
        # フラスタム（前面レンズからの視錐台）
        # +Zが光軸方向 = カメラが見る方向（マーカーへ）
        fscale = marker_size_m * 1.5
        frustum_local = np.array([
            [0, 0, 0],
            [-fscale, -fscale, fscale * 2],
            [fscale, -fscale, fscale * 2],
            [fscale, fscale, fscale * 2],
            [-fscale, fscale, fscale * 2],
        ])
        
        # カメラ座標系 → 世界（マーカー）座標系へ変換
        # p_world = R^T @ p_cam + camera_pos （ポーズの逆変換）
        frustum_world = (R_wc @ frustum_local.T).T + camera_pos
        
        # フラスタムの描画
        frustum_edges = [[0, 1], [0, 2], [0, 3], [0, 4], [1, 2], [2, 3], [3, 4], [4, 1]]
        for i, edge in enumerate(frustum_edges):
            p1 = frustum_world[edge[0]]
            p2 = frustum_world[edge[1]]
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], [p1[2], p2[2]], 
                   'cyan', alpha=0.7, linewidth=1.5, label='Frustum' if i == 0 else '')
        
        # カメラ位置を表示
        ax.scatter(*camera_pos, color='cyan', s=200, marker='*', label='Camera', zorder=5)
        
        # 視線方向（光軸）：カメラから+Z方向（見ている向き、マーカーへ）に矢印
        optical_dir = R_wc @ np.array([0, 0, fscale * 2.5])
        ax.quiver(camera_pos[0], camera_pos[1], camera_pos[2],
                 optical_dir[0], optical_dir[1], optical_dir[2],
                 color='yellow', arrow_length_ratio=0.15, linewidth=2, label='View Direction')
        
        # 座標軸の描画（マーカー中心から）
        axis_length = marker_size_m * 1.2
        ax.quiver(0, 0, 0, axis_length, 0, 0, color='red', arrow_length_ratio=0.2, linewidth=2, label='X')
        ax.quiver(0, 0, 0, 0, axis_length, 0, color='green', arrow_length_ratio=0.2, linewidth=2, label='Y')
        ax.quiver(0, 0, 0, 0, 0, axis_length, color='blue', arrow_length_ratio=0.2, linewidth=2, label='Z')
        
        # マーカーの原点を強調
        ax.scatter(0, 0, 0, color='white', s=150, marker='o', edgecolors='yellow', 
                  linewidths=2, zorder=5, label='Marker Origin')
        
        # 軸設定
        ax.set_xlabel('X (m)', color='white')
        ax.set_ylabel('Y (m)', color='white')
        ax.set_zlabel('Z (m)', color='white')
        ax.set_xlim(-xy_extent, xy_extent)
        ax.set_ylim(-xy_extent, xy_extent)
        ax.set_zlim(0, box_height)  # マーカーが底面(z=0)に来るように
        # 実寸に合わせたアスペクト比（歪みをなくしカメラ位置を正しく表示）
        ax.set_box_aspect((2 * xy_extent, 2 * xy_extent, box_height))
        # 視点：マーカーを底面、カメラを上方に見やすく
        ax.view_init(elev=20, azim=-70)
        
        # 背景色と軸色の設定
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False
        ax.xaxis.pane.set_edgecolor('gray')
        ax.yaxis.pane.set_edgecolor('gray')
        ax.zaxis.pane.set_edgecolor('gray')
        ax.grid(True, alpha=0.2)
        
        # ラベル色を白に
        for label in ax.get_xticklabels() + ax.get_yticklabels() + ax.get_zticklabels():
            label.set_color('white')
        
        # タイトルと凡例
        ax.set_title('3D Camera Pose Visualization (Marker at Bottom)', color='white', fontsize=12)
        ax.legend(loc='upper left', fontsize=8, facecolor=(0.3, 0.3, 0.3), edgecolor='white')
        
        # matplotlibの図をNumpy配列に変換
        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        renderer = canvas.get_renderer()
        
        # RGBA バッファを取得
        buf = renderer.buffer_rgba()
        size = canvas.get_width_height()
        
        # RGB画像に変換
        image = np.frombuffer(buf, dtype=np.uint8)
        image = image.reshape(size[1], size[0], 4)  # RGBAチャンネル
        image_rgb = image[:, :, :3]  # RGB部分のみ取得
        
        # BGR形式に変換（OpenCV用）
        image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
        
        # 図を閉じてメモリ解放
        plt.close(fig)
        
        return image_bgr
