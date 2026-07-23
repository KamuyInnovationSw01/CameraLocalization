"""
3D ワイヤフレーム描画モジュール
カメラのポーズをフラスタム + ボディ + 光軸矢印で描画します。
"""

import numpy as np
import cv2
from typing import Tuple

class WireframeRenderer:
    """3D ワイヤフレーム描画を行うクラス"""
    
    def __init__(
        self,
        camera_matrix: np.ndarray,
        wireframe_scale: float = 0.15,
        image_size: tuple[int, int] | None = None,
    ):
        """
        ワイヤフレーム描画器を初期化します。
        
        Args:
            camera_matrix: カメラ行列 (3, 3)
            wireframe_scale: ワイヤフレームのスケール（相対的）
            image_size: キャリブレーション画像サイズ (width, height)。指定時は
                この画像の四隅からフラスタムを計算します。
        """
        self.camera_matrix = camera_matrix.copy()
        self.wireframe_scale = wireframe_scale
        # 3Dビューの仮想投影では歪みを適用しないため、OpenCVの型付き引数として
        # 明示的なゼロ歪み係数を渡します。
        self.zero_dist_coeffs = np.zeros(5, dtype=np.float32)
        if image_size is None:
            # 旧呼び出しとの互換用。通常はキャリブレーションの実画像サイズを渡します。
            self.image_size = (
                int(round(2 * self.camera_matrix[0, 2])),
                int(round(2 * self.camera_matrix[1, 2])),
            )
        else:
            self.image_size = (int(image_size[0]), int(image_size[1]))
        
        # ウィンドウサイズ（描画用）
        self.window_width = 960
        self.window_height = 720
        
        # 背景色
        self.bg_color = (50, 50, 50)  # 暗いグレー

    def create_frustum_vertices(self, depth: float) -> np.ndarray:
        """カメラ行列の画角に一致するフラスタム頂点を作成します。

        画像平面の四隅をピンホールカメラモデルで逆投影します。
        ``x=(u-cx)z/fx``、``y=(v-cy)z/fy``なので、固定の開き係数ではなく
        実際の焦点距離と主点から水平・垂直画角、および主点の偏りを反映できます。
        頂点順は左上、右上、右下、左下で、OpenCVの+Z方向を奥とします。
        """
        fx = float(self.camera_matrix[0, 0])
        fy = float(self.camera_matrix[1, 1])
        cx = float(self.camera_matrix[0, 2])
        cy = float(self.camera_matrix[1, 2])
        width, height = self.image_size
        if fx <= 0 or fy <= 0 or width <= 0 or height <= 0:
            raise ValueError("カメラ行列または画像サイズが不正です")

        corners = np.array(
            [[0.0, 0.0], [float(width), 0.0], [float(width), float(height)], [0.0, float(height)]],
            dtype=np.float32,
        )
        xy = np.empty_like(corners)
        xy[:, 0] = (corners[:, 0] - cx) / fx * depth
        xy[:, 1] = (corners[:, 1] - cy) / fy * depth
        return np.vstack([np.zeros((1, 3), dtype=np.float32), np.column_stack([xy, np.full(4, depth)])])
    
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
        
        # フラスタムはカメラ行列から算出します。これにより、カメラごとの
        # 水平・垂直画角や主点のずれが3Dビューへ反映されます。
        frustum_vertices = self.create_frustum_vertices(frustum_depth)
        
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
            distCoeffs=self.zero_dist_coeffs
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
        marker_size_m: float = 0.1,
        map_points: np.ndarray | None = None,
        map_point_colors: np.ndarray | None = None,
    ) -> np.ndarray:
        """
        3D ワイヤフレーム + マーカー + 座標軸の独立したビューを作成します。
        
        Args:
            rvec: 回転ベクトル
            tvec: 並進ベクトル
            marker_size_m: マーカーサイズ（メートル）
            map_points: マーカーレス時に表示する基準座標系の3Dマップ点。
            map_point_colors: map_pointsと同じ順序のBGR色配列。
        
        Returns:
            np.ndarray: 3D ビュー画像
        """
        # 背景を作成
        view = np.full((self.window_height, self.window_width, 3), 
                       self.bg_color, dtype=np.uint8)
        
        # 1. 3D 形状の定義
        # カメラのワイヤフレーム構造を作成（ローカル座標系）
        vertices_local, camera_edges = self.create_camera_wireframe()
        
        markerless_mode = map_points is not None

        # マーカー頂点の作成（世界座標系、Z=0平面）。マーカーレス時は
        # マーカーそのものを表示せず、代わりにmap_pointsを表示します。
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
        
        # マーカーの座標軸（世界座標系の中心から）。マーカーレス時は
        # マップ上の人工的な原点・軸を表示しないため使用しません。
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

        # マーカーレス表示では、基準座標系の+Zが画面下向きになるように、
        # 表示用座標だけをX軸まわり180度回転します。diag(1,-1,-1)は
        # 行列式が+1の正規回転なので、右手系を維持したままZ方向を反転できます。
        # 推定値や保存済みマップの座標そのものは変更しません。
        display_rotation = (
            np.diag([1.0, -1.0, -1.0]).astype(np.float32)
            if markerless_mode
            else np.eye(3, dtype=np.float32)
        )
        camera_pos = display_rotation @ camera_pos
        
        # カメラローカルの頂点群を世界座標系に変換
        # p_world = R_wc @ p_local + camera_pos
        vertices_world = (
            display_rotation @ (R_wc @ vertices_local.T)
        ).T + camera_pos

        # 表示対象の基準点を先に作ります。仮想カメラをシーンの大きさに対して
        # 十分遠ざけることで、透視投影による奥行き方向の誇張を抑えます。
        display_points = (
            (
                display_rotation
                @ np.asarray(map_points, dtype=np.float32).T
            ).T
            if markerless_mode
            else np.vstack([marker_vertices, axis_vertices])
        )
        scene_points = np.vstack([display_points, vertices_world.astype(np.float32)])
        scene_extent = max(float(np.max(np.linalg.norm(scene_points, axis=1))), 0.15)
        
        # 3. 仮想第3者カメラ（LookAtビューポーズ）の構築
        # 全体が常にいいパースで画面中央に収まるように仮想カメラの位置とターゲットを動的に調整
        dist = np.linalg.norm(camera_pos)
        dist = max(0.15, dist)  # 最低スケサインターバル
        
        # 注視点はマーカー(原点)から少しカメラ側に寄せた位置
        if markerless_mode and len(map_points) > 0:
            map_center = np.mean(
                display_rotation @ np.asarray(map_points, dtype=np.float32).T,
                axis=1,
            )
            target = map_center * 0.7 + camera_pos * 0.3
        else:
            target = camera_pos * 0.3
        
        # 斜め右上（Xがプラス、Yがマイナス、Zがプラス）から見下ろす基本方向
        view_dir = np.array([0.7, -1.3, 0.9], dtype=np.float32)
        view_dir /= np.linalg.norm(view_dir)
        
        # 仮想カメラの座標。従来の距離だけでなくシーンの大きさも考慮して
        # 後退させます。距離を大きくすると透視投影のパースが弱くなります。
        eye_distance = max(dist * 1.7, scene_extent * 4.0)
        eye = target + view_dir * eye_distance
        
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
        all_vertices_world = np.vstack([display_points, vertices_world.astype(np.float32)])
        identity_camera = np.eye(3, dtype=np.float32)
        normalized_points, _ = cv2.projectPoints(
            all_vertices_world,
            r_view,
            t_view,
            identity_camera,
            self.zero_dist_coeffs
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
        display_2d, _ = cv2.projectPoints(
            display_points, r_view, t_view, K_virtual, self.zero_dist_coeffs
        )
        display_2d = display_2d.reshape(-1, 2)
        axis_2d: np.ndarray | None = None
        
        # カメラワイヤフレーム
        cam_vertices_2d, _ = cv2.projectPoints(
            vertices_world.astype(np.float32),
            r_view,
            t_view,
            K_virtual,
            self.zero_dist_coeffs,
        )
        cam_vertices_2d = cam_vertices_2d.reshape(-1, 2)
        
        # 6. レンダリング/描画
        if markerless_mode:
            # マーカーレス時は、保存済みマップ点を対応状態別に描画します。
            colors = (
                np.asarray(map_point_colors, dtype=np.uint8)
                if map_point_colors is not None
                else np.tile(np.array([[150, 150, 150]], dtype=np.uint8), (len(display_2d), 1))
            )
            for point, color in zip(display_2d, colors):
                cv2.circle(view, tuple(np.round(point).astype(int)), 3, tuple(int(v) for v in color), -1)
        else:
            # markerモードでは従来どおりマーカー四角形と座標軸を描画します。
            marker_2d = display_2d[:4]
            axis_2d = display_2d[4:]
            try:
                overlay = view.copy()
                cv2.fillPoly(overlay, [marker_2d.astype(np.int32)], (0, 0, 120))
                cv2.addWeighted(overlay, 0.25, view, 0.75, 0, view)
                for edge in marker_edges:
                    p1 = tuple(marker_2d[edge[0]].astype(int))
                    p2 = tuple(marker_2d[edge[1]].astype(int))
                    cv2.line(view, p1, p2, (0, 0, 180), 2)
            except Exception:
                pass

            origin = tuple(axis_2d[0].astype(int))
            for axis_index, color, label in (
                (1, (0, 0, 255), "X_m"),
                (2, (0, 255, 0), "Y_m"),
                (3, (255, 0, 0), "Z_m"),
            ):
                axis_point = tuple(axis_2d[axis_index].astype(int))
                cv2.line(view, origin, axis_point, color, 2)
                cv2.putText(view, label, (axis_point[0] + 5, axis_point[1] + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
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
        if axis_2d is not None:
            cv2.circle(view, tuple(axis_2d[0].astype(int)), 6, (255, 255, 0), 2)
        
        # E. テキストレイアウト説明
        title = "3D View: Camera Pose + Map" if markerless_mode else "3D View: Camera Pose + Marker Axes"
        legend = (
            "Gray: Map | Green: Inlier | Red: Outlier | Yellow: Unverified"
            if markerless_mode
            else "Orange: Camera Body | Cyan: Frustum | Yellow: Optical Axis | Red: Marker"
        )
        cv2.putText(view, title, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(view, legend,
               (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        return view


    __all__ = ["WireframeRenderer"]
