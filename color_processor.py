"""颜色处理与聚类模块。

该模块实现了图像颜色压缩流程，包括：
- RGB 到 LAB 的颜色空间转换
- LAB 距离计算
- 手写 K-means 聚类
- 将中心颜色映射回 MARD221 色库
"""

import numpy as np
from mard221_data import MARD221_FULL

MARD221_COLORS = [item["rgb"] for item in MARD221_FULL]   
MARD221_NAMES = [item["id"] for item in MARD221_FULL]  

def rgb_to_lab(rgb):
    rgb = np.asarray(rgb, dtype=np.float32)
    rgb_lin = rgb / 255.0
    mask = rgb_lin <= 0.04045
    rgb_lin[mask] = rgb_lin[mask] / 12.92
    rgb_lin[~mask] = ((rgb_lin[~mask] + 0.055) / 1.055) ** 2.4

    M = np.array([
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041]
    ])
    xyz = np.dot(rgb_lin, M.T)
    Xn, Yn, Zn = 0.95047, 1.0, 0.94583

    def f(t):
        delta = 6.0 / 29.0
        return np.where(t > (delta ** 3), t ** (1/3), t / (3 * delta ** 2) + 4/29)

    xr = f(xyz[..., 0] / Xn)
    yr = f(xyz[..., 1] / Yn)
    zr = f(xyz[..., 2] / Zn)

    L = 116 * yr - 16
    a = 500 * (xr - yr)
    b = 200 * (yr - zr)
    return np.stack([L, a, b], axis=-1)

def lab_distance(lab1, lab2):
    return np.sqrt(np.sum((lab1 - lab2) ** 2, axis=-1))

def kmeans(X, k, max_iter=100, tol=1e-4, random_seed=None):
    if random_seed is not None:
        np.random.seed(random_seed)
    N = X.shape[0]
    indices = np.random.choice(N, k, replace=False)
    centers = X[indices].copy()
    for _ in range(max_iter):
        dist = np.sqrt(((X - centers[:, np.newaxis]) ** 2).sum(axis=2))
        labels = np.argmin(dist, axis=0)
        new_centers = np.array([X[labels == i].mean(axis=0) if np.any(labels == i) else centers[i]
                                for i in range(k)])
        if np.linalg.norm(new_centers - centers) < tol:
            centers = new_centers
            break
        centers = new_centers
    return labels, centers

def map_centers_to_mard(centers_lab):
    if not hasattr(map_centers_to_mard, '_mard_lab'):
        mard_rgb = np.array(MARD221_COLORS, dtype=np.float32)
        mard_lab = rgb_to_lab(mard_rgb)
        map_centers_to_mard._mard_lab = mard_lab
    mard_lab = map_centers_to_mard._mard_lab

    indices = []
    for c in centers_lab:
        dists = lab_distance(c, mard_lab)
        idx = np.argmin(dists)
        indices.append(idx)
    return np.array(indices)

def process_image_to_mard(img_array, target_w, target_h, k):
    from PIL import Image

    img = Image.fromarray(img_array)
    img_resized = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    pixels = np.array(img_resized, dtype=np.float32)
    h, w, _ = pixels.shape
    pixels_rgb = pixels.reshape(-1, 3)
    pixels_lab = rgb_to_lab(pixels_rgb)

    labels, centers_lab = kmeans(pixels_lab, k, random_seed=42)
    mard_indices_for_centers = map_centers_to_mard(centers_lab)
    pixel_mard_indices = mard_indices_for_centers[labels]
    grid = pixel_mard_indices.reshape(h, w)

    unique, counts = np.unique(grid, return_counts=True)
    color_counts = dict(zip(unique.tolist(), counts.tolist()))
    return grid, color_counts