"""拼豆图纸渲染核心模块。

本模块负责把颜色索引网格转成最终的图纸 PNG。它会生成：
- 单色填充网格
- 5 格 / 10 格分隔线
- 外围编号与坐标边框
- 底部颜色图例与数量统计
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
from math import floor, ceil

from mard221_data import MARD221_FULL

MARD221_COLORS = [item["rgb"] for item in MARD221_FULL]
MARD221_NAMES = [item["id"] for item in MARD221_FULL]


def draw_bead_plan(grid, color_counts, cell_size=30, legend_cols=None):
    """
    绘制拼豆图纸，包含：
    - 内部颜色网格
    - 四周白色编号边框（每格编号从 0 开始）
    - 贯穿网格线（5格细灰，10格粗灰，从中心均匀分布）
    - 底部图例（颜色块 + 色号 + 数量）
    """
    h, w = grid.shape
    if h*w>20000:
        cell_size=min(cell_size,15)
    elif h*w>10000:
        cell_size=min(cell_size,20)
    # 总网格数（包含白色边框）
    total_w_cells = w + 2
    total_h_cells = h + 2

    # 图纸尺寸（像素）
    grid_width = total_w_cells * cell_size
    grid_height = total_h_cells * cell_size

    # 图例区域
    if legend_cols is None:
        item_width = cell_size + 80
        max_width = grid_width - 20
        legend_cols = max(1, int(max_width / item_width))
        legend_cols = min(legend_cols, len(color_counts))

    legend_items = len(color_counts)
    legend_rows = (legend_items + legend_cols - 1) // legend_cols
    legend_height = legend_rows * (cell_size + 10) + 40

    total_width = grid_width
    total_height = grid_height + legend_height

    # 创建白色背景
    img = Image.new('RGB', (total_width, total_height), color='white')
    draw = ImageDraw.Draw(img)

    # 加载字体
    try:
        font_path = "C:/Windows/Fonts/msyh.ttc" if os.name == 'nt' else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        font_small = ImageFont.truetype(font_path, size=10)
        font_legend = ImageFont.truetype(font_path, size=12)
        font_number = ImageFont.truetype(font_path, size=12)  # 编号字体稍大
    except:
        font_small = ImageFont.load_default()
        font_legend = ImageFont.load_default()
        font_number = ImageFont.load_default()

    # ---------- 绘制所有格子 ----------
    # 内部颜色格子
    for y in range(h):
        for x in range(w):
            idx = grid[y, x]
            color = tuple(MARD221_COLORS[idx])
            left = (x + 1) * cell_size
            top = (y + 1) * cell_size
            right = left + cell_size
            bottom = top + cell_size
            draw.rectangle([left, top, right, bottom], fill=color)

            # 在内部格子中写入色号
            color_id = MARD221_NAMES[idx] if idx < len(MARD221_NAMES) else f"MARD-{idx+1:03d}"
            bbox = draw.textbbox((0, 0), color_id, font=font_small)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            tx = left + (cell_size - tw) // 2
            ty = top + (cell_size - th) // 2
            r, g, b = color
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            text_color = 'black' if luminance > 128 else 'white'
            draw.text((tx, ty), color_id, fill=text_color, font=font_small)

    # 白色边框格子
    # 上边
    for x in range(total_w_cells):
        left = x * cell_size
        top = 0
        draw.rectangle([left, top, left + cell_size, top + cell_size], fill='white')
    # 下边
    for x in range(total_w_cells):
        left = x * cell_size
        top = (h + 1) * cell_size
        draw.rectangle([left, top, left + cell_size, top + cell_size], fill='white')
    # 左边
    for y in range(total_h_cells):
        left = 0
        top = y * cell_size
        draw.rectangle([left, top, left + cell_size, top + cell_size], fill='white')
    # 右边
    for y in range(total_h_cells):
        left = (w + 1) * cell_size
        top = y * cell_size
        draw.rectangle([left, top, left + cell_size, top + cell_size], fill='white')

    # ---------- 绘制网格线 ----------
    # 计算统一偏移（宽度方向）
    best_offset_w = 0
    best_diff_w = float('inf')
    for offset in range(10):
        pos5 = list(range(offset, total_w_cells + 1, 5))
        pos10 = list(range(offset, total_w_cells + 1, 10))
        if not pos5 or not pos10:
            continue
        left_blank = pos5[0]
        right_blank5 = total_w_cells - pos5[-1]
        right_blank10 = total_w_cells - pos10[-1]
        diff = abs(left_blank - right_blank5) + abs(left_blank - right_blank10)
        if diff < best_diff_w:
            best_diff_w = diff
            best_offset_w = offset

    x_pos_5 = list(range(best_offset_w, total_w_cells + 1, 5))
    x_pos_10 = list(range(best_offset_w, total_w_cells + 1, 10))

     # 计算统一偏移（高度方向）
    best_offset_h = 0
    best_diff_h = float('inf')
    for offset in range(10):
        pos5 = list(range(offset, total_h_cells + 1, 5))
        pos10 = list(range(offset, total_h_cells + 1, 10))
        if not pos5 or not pos10:
            continue
        top_blank = pos5[0]
        bottom_blank5 = total_h_cells - pos5[-1]
        bottom_blank10 = total_h_cells - pos10[-1]
        diff = abs(top_blank - bottom_blank5) + abs(top_blank - bottom_blank10)
        if diff < best_diff_h:
            best_diff_h = diff
            best_offset_h = offset

    y_pos_5 = list(range(best_offset_h, total_h_cells + 1, 5))
    y_pos_10 = list(range(best_offset_h, total_h_cells + 1, 10))

    # 细竖线（5格）
    for x_idx in x_pos_5:
        if x_idx in x_pos_10:
            continue  # 10格的位置由粗线绘制
        x = x_idx * cell_size
        draw.line([(x, 0), (x, grid_height)], fill=(200, 200, 200), width=1)

    # 细横线（5格）
    for y_idx in y_pos_5:
        if y_idx in y_pos_10:
            continue
        y = y_idx * cell_size
        draw.line([(0, y), (grid_width, y)], fill=(200, 200, 200), width=1)

    # 粗竖线（10格）
    for x_idx in x_pos_10:
        x = x_idx * cell_size
        draw.line([(x, 0), (x, grid_height)], fill=(120, 120, 120), width=2)
    
    # 粗横线（10格）
    for y_idx in y_pos_10:
        y = y_idx * cell_size
        draw.line([(0, y), (grid_width, y)], fill=(120, 120, 120), width=2)

    # ---------- 绘制四周数数编号 ----------
    # 上边编号（行0，列1~w）
    for i in range(w):
        left = (i + 1) * cell_size
        top = 0
        text = str(i+1)
        bbox = draw.textbbox((0, 0), text, font=font_number)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((left + (cell_size - tw) // 2, top + (cell_size - th) // 2),
                  text, fill='black', font=font_number)

    # 下边编号（行 h+1，列1~w）
    for i in range(w):
        left = (i + 1) * cell_size
        top = (h + 1) * cell_size
        text = str(i+1)
        bbox = draw.textbbox((0, 0), text, font=font_number)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((left + (cell_size - tw) // 2, top + (cell_size - th) // 2),
                  text, fill='black', font=font_number)

    # 左边编号（列0，行1~h）
    for j in range(h):
        left = 0
        top = (j + 1) * cell_size
        text = str(j+1)
        bbox = draw.textbbox((0, 0), text, font=font_number)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((left + (cell_size - tw) // 2, top + (cell_size - th) // 2),
                  text, fill='black', font=font_number)

    # 右边编号（列 w+1，行1~h）
    for j in range(h):
        left = (w + 1) * cell_size
        top = (j + 1) * cell_size
        text = str(j+1)
        bbox = draw.textbbox((0, 0), text, font=font_number)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((left + (cell_size - tw) // 2, top + (cell_size - th) // 2),
                  text, fill='black', font=font_number)

    # ---------- 绘制底部图例 ----------
    legend_start_y = grid_height + 10
    sorted_items = sorted(color_counts.items(), key=lambda kv: kv[1], reverse=True)

    draw.text((10, legend_start_y), "Color Legend (MARD)", fill='black', font=font_legend)
    legend_start_y += 20
    item_width = cell_size + 80
    for i, (idx, count) in enumerate(sorted_items):
        col = i % legend_cols
        row = i // legend_cols
        x_pos = 10 + col * item_width   # 留更多空间给文字
        y_pos = legend_start_y + row * (cell_size + 10)

        color = tuple(MARD221_COLORS[idx])
        draw.rectangle([x_pos, y_pos, x_pos + cell_size, y_pos + cell_size], fill=color)
        label = f"{MARD221_NAMES[idx]}: {count}"
        draw.text((x_pos + cell_size + 5, y_pos + 2), label, fill='black', font=font_legend)

    return img