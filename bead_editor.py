"""豆子颜色编辑核心逻辑模块。

该模块提供与 GUI 无关的纯函数，供颜色编辑功能及其单元测试使用：
- recount_colors：根据网格重新计算颜色使用统计
- line_cells_between：用于平滑拖拽绘制的 Bresenham 直线插值
- edited_mask_from：与原始网格不同的单元格的布尔掩码
"""
import numpy as np

def recount_colors(grid):
    """重新计算颜色适用统计"""
    unique, counts = np.unique(grid, return_counts=True)
    valid_mask = unique!=-1
    unique=unique[valid_mask]
    counts=counts[valid_mask]
    return dict(zip(unique.tolist(), counts.tolist()))

def line_cells_between(r0, c0, r1, c1):
    """用于平滑拖拽绘制的 Bresenham 直线插值"""
    cells = []
    dr = abs(r1 - r0)
    dc = abs(c1 - c0)
    sr =-1 if r0 >= r1 else +1
    sc =-1 if c0 >= c1 else +1
    err = dr - dc
    r, c = r0, c0
    while True:
        cells.append((r, c))
        if r == r1 and c == c1:
            break
        e2 =err + err
        if e2 > -dc:
            err -= dc
            r += sr
        if e2 < dr:
            err += dr
            c += sc
    return cells

def edited_mask_from(grid, original_grid):
    """与原始网格不同的单元格的布尔掩码"""
    return grid != original_grid