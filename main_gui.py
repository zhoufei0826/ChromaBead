"""ChromaBead 图形界面入口。

本模块负责：
- 初始化 PyQt6 主窗口
- 处理图片加载与拖拽交互
- 管理用户参数输入
- 调用图纸生成线程并渲染预览
"""

import sys
import os
import gc
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QSlider, QSpinBox, QMessageBox,
    QGroupBox, QScrollArea, QCheckBox
)
from PyQt6.QtCore import QSizeF, Qt, QThread, pyqtSignal, QEvent
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPageSize, QPixmap, QFont, QImage, QPainter
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from PIL import Image

from color_processor import process_image_to_mard
from bead_core import draw_bead_plan
from mard221_data import MARD221_FULL

MARD221_NAMES = [item["id"] for item in MARD221_FULL]


def pil_to_qimage(img: Image.Image) -> QImage:
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA" if "A" in img.getbands() else "RGB")

    if img.mode == "RGB":
        data = img.tobytes("raw", "RGB")
        qimage = QImage(data, img.width, img.height, img.width * 3, QImage.Format.Format_RGB888)
    else:
        data = img.tobytes("raw", "RGBA")
        qimage = QImage(data, img.width, img.height, img.width * 4, QImage.Format.Format_RGBA8888)

    return qimage.copy()


class GenerateThread(QThread):
    finished = pyqtSignal(object, object)
    error = pyqtSignal(str)

    def __init__(self, img_array, target_w, target_h, k):
        super().__init__()
        self.img_array = img_array
        self.target_w = target_w
        self.target_h = target_h
        self.k = k

    def run(self):
        try:
            grid, counts = process_image_to_mard(
                self.img_array, self.target_w, self.target_h, self.k
            )
            self.finished.emit(grid, counts)
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChromaBead v1.0.1")
        self.setMinimumSize(1100, 780)
        self.resize(1180, 830)

        self.current_image = None
        self.current_grid = None
        self.current_counts = None
        self.aspect_ratio = None
        self.preview_zoom = 1.0
        self.drag_start_pos = None
        self.scroll_bar_positions = None

        self.max_colors = 16
        self.grid_width = 40
        self.grid_height = 40

        self._init_ui()

    def _apply_button_style(self, button, palette="primary"):
        colors = {
            "primary": ("#1f1f1f", "#f5f5f5", "#424242"),
            "secondary": ("#f3f3f3", "#1c1c1c", "#d9d9d9"),
            "success": ("#2f2f2f", "#ffffff", "#4a4a4a"),
            "warn": ("#ededed", "#1a1a1a", "#d4d4d4"),
        }
        base, text, hover = colors.get(palette, colors["primary"])
        button.setStyleSheet(
            f"QPushButton {{"
            f"background: {base}; color: {text}; border: 1px solid {hover}; padding: 6px 12px; font-weight: 600; min-height: 30px; border-radius: 0px; }}"
            f"QPushButton:hover {{ background: {hover}; color: {text}; }}"
            f"QPushButton:disabled {{ background: #e6e6e6; color: #8a8a8a; border-color: #d3d3d3; }}"
        )

    def _create_param_row(self, label_text, slider, spinbox, compact=False):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(8, 4, 8, 4)
        row_layout.setSpacing(12)

        label = QLabel(label_text)
        label.setFixedWidth(170 if compact else 180)
        label.setStyleSheet("color: #1f1f1f; font-weight: 600; font-size: 13px;")
        row_layout.addWidget(label)

        slider.setStyleSheet(
            "QSlider::groove:horizontal { height: 5px; background: #d9d9d9; }"
            "QSlider::handle:horizontal { width: 14px; height: 14px; margin: -4px 0; background: #1f1f1f; border: 1px solid #1f1f1f; }"
            "QSlider::sub-page:horizontal { background: #6c6c6c; }"
        )
        slider.setMinimumHeight(22)
        row_layout.addWidget(slider, 1)

        spinbox.setMinimumHeight(30)
        spinbox.setStyleSheet(
            "QSpinBox { background: #ffffff; border: 1px solid #cfcfcf; padding: 4px 8px; color: #111111; }"
        )
        row_layout.addWidget(spinbox, 0)
        return row

    def _init_ui(self):
        central = QWidget()
        central.setStyleSheet(
            "QWidget { background: #f3f3f3; color: #111111; }"
            "QGroupBox { background: #ffffff; border: 1px solid #d9d9d9; border-radius: 0px; font-weight: 700; padding-top: 12px; color: #111111; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 16px; padding: 0 8px; top: 8px; }"
            "QLabel { color: #1f1f1f; }"
            "QCheckBox { color: #1f1f1f; spacing: 8px; font-weight: 500; }"
            "QScrollArea { border: 1px solid #d9d9d9; background: #ffffff; border-radius: 0px; }"
            "QToolTip { padding: 8px 10px; border: 1px solid #bfbfbf; background: #ffffff; color: #111111; font-size: 13px; border-radius: 0px; }"
        )
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(18)

        header = QWidget()
        header.setObjectName("headerPanel")
        header.setStyleSheet(
            "QWidget#headerPanel { background: #f6f6f6; border: 1px solid #d8d8d8; border-radius: 0px; }"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)

        title = QLabel("ChromaBead")
        title.setStyleSheet("font-size: 23px; font-weight: 700; color: #111111; letter-spacing: 0.5px;")
        header_layout.addWidget(title)

        subtitle = QLabel("图片转拼豆图纸生成器")
        subtitle.setStyleSheet("font-size: 11px; color: #4d4d4d; letter-spacing: 1px; text-transform: uppercase;")
        header_layout.addWidget(subtitle, 1, Qt.AlignmentFlag.AlignRight)
        main_layout.addWidget(header)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(18)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(18)

        load_group = QGroupBox("加载图片")
        load_layout = QHBoxLayout(load_group)
        load_layout.setContentsMargins(16, 12, 16, 12)
        load_layout.setSpacing(12)

        self.btn_open = QPushButton("打开图片")
        self.btn_open.clicked.connect(self.open_image)
        self._apply_button_style(self.btn_open, "primary")
        load_layout.addWidget(self.btn_open)

        self.btn_clear = QPushButton("清除图片")
        self.btn_clear.clicked.connect(self.clear_image)
        self._apply_button_style(self.btn_clear, "secondary")
        load_layout.addWidget(self.btn_clear)

        self.img_label = QLabel("拖拽图片到此处")
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setStyleSheet(
            "border: 1px dashed #b9b9b9; background: #f7f7f7; color: #505050; font-size: 13px; border-radius: 0px;"
        )
        self.img_label.setMinimumHeight(150)
        self.img_label.setScaledContents(False)
        self.setAcceptDrops(True)
        self.img_label.setAcceptDrops(True)
        self.img_label.dragEnterEvent = self.dragEnterEvent
        self.img_label.dropEvent = self.dropEvent
        load_layout.addWidget(self.img_label, 1)
        left_layout.addWidget(load_group)

        param_group = QGroupBox("参数设置")
        param_layout = QVBoxLayout(param_group)
        param_layout.setContentsMargins(24, 18, 16, 16)
        param_layout.setSpacing(10)

        self.color_slider = QSlider(Qt.Orientation.Horizontal)
        self.color_slider.setMinimum(2)
        self.color_slider.setMaximum(64)
        self.color_slider.setValue(self.max_colors)
        self.color_slider.valueChanged.connect(self.on_color_change)
        self.color_spin = QSpinBox()
        self.color_spin.setRange(2, 64)
        self.color_spin.setValue(self.max_colors)
        self.color_spin.valueChanged.connect(self.on_color_spin)
        param_layout.addWidget(self._create_param_row("最大颜色数:", self.color_slider, self.color_spin))

        self.width_slider = QSlider(Qt.Orientation.Horizontal)
        self.width_slider.setMinimum(10)
        self.width_slider.setMaximum(200)
        self.width_slider.setValue(self.grid_width)
        self.width_slider.valueChanged.connect(self.on_width_change)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(10, 200)
        self.width_spin.setValue(self.grid_width)
        self.width_spin.valueChanged.connect(self.on_width_spin)
        param_layout.addWidget(self._create_param_row("图纸宽度:", self.width_slider, self.width_spin))

        self.height_slider = QSlider(Qt.Orientation.Horizontal)
        self.height_slider.setMinimum(10)
        self.height_slider.setMaximum(200)
        self.height_slider.setValue(self.grid_height)
        self.height_slider.valueChanged.connect(self.on_height_change)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(10, 200)
        self.height_spin.setValue(self.grid_height)
        self.height_spin.valueChanged.connect(self.on_height_spin)
        param_layout.addWidget(self._create_param_row("图纸高度:", self.height_slider, self.height_spin))

        aspect_widget = QWidget()
        aspect_layout = QHBoxLayout(aspect_widget)
        aspect_layout.setContentsMargins(8, 6, 0, 6)
        aspect_layout.setSpacing(10)
        self.aspect_checkbox = QCheckBox("等比例缩放（保持原图宽高比）")
        self.aspect_checkbox.toggled.connect(self.on_aspect_toggled)
        aspect_layout.addWidget(self.aspect_checkbox)
        aspect_layout.addStretch()
        aspect_widget.setMinimumHeight(44)
        param_layout.addWidget(aspect_widget)
        left_layout.addWidget(param_group)

        output_group = QGroupBox("生成与保存")
        output_layout = QVBoxLayout(output_group)
        output_layout.setContentsMargins(16, 18, 16, 16)
        output_layout.setSpacing(8)

        row1 = QHBoxLayout()
        self.btn_generate = QPushButton("生成图纸")
        self.btn_generate.clicked.connect(self.generate_plan)
        self._apply_button_style(self.btn_generate, "success")
        row1.addWidget(self.btn_generate, 3)

        self.btn_reset = QPushButton("重置参数")
        self.btn_reset.clicked.connect(self.reset_parameters)
        self._apply_button_style(self.btn_reset, "warn")
        row1.addWidget(self.btn_reset, 1)
        output_layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.btn_save_png = QPushButton("保存 PNG")
        self.btn_save_png.clicked.connect(self.save_png)
        self.btn_save_png.setEnabled(False)
        self._apply_button_style(self.btn_save_png, "primary")
        row2.addWidget(self.btn_save_png, 1)

        self.btn_save_txt = QPushButton("保存颜色清单")
        self.btn_save_txt.clicked.connect(self.save_txt)
        self.btn_save_txt.setEnabled(False)
        self._apply_button_style(self.btn_save_txt, "secondary")
        row2.addWidget(self.btn_save_txt, 1)
        output_layout.addLayout(row2)

        row3 = QHBoxLayout()
        self.btn_export_pdf = QPushButton("导出 PDF")
        self.btn_export_pdf.clicked.connect(self.export_pdf)
        self.btn_export_pdf.setEnabled(False)
        self._apply_button_style(self.btn_export_pdf, "primary")
        row3.addWidget(self.btn_export_pdf)

        self.btn_export_svg = QPushButton("导出 SVG")
        self.btn_export_svg.clicked.connect(self.export_svg)
        self.btn_export_svg.setEnabled(False)
        self._apply_button_style(self.btn_export_svg, "primary")
        row3.addWidget(self.btn_export_svg)

        self.btn_print = QPushButton("打印")
        self.btn_print.clicked.connect(self.print_plan)
        self.btn_print.setEnabled(False)
        self._apply_button_style(self.btn_print, "secondary")
        row3.addWidget(self.btn_print)
        output_layout.addLayout(row3)

        left_layout.addWidget(output_group)

        content_layout.addWidget(left_panel, 1)

        preview_group = QGroupBox("预览结果")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(16, 18, 16, 16)

        preview_top = QWidget()
        preview_top_layout = QHBoxLayout(preview_top)
        preview_top_layout.setContentsMargins(0, 0, 0, 0)
        preview_top_layout.setSpacing(8)

        self.preview_status = QLabel("等待生成")
        self.preview_status.setStyleSheet("color: #222222; font-size: 13px; font-weight: 600; background: #f5f5f5; border: 1px solid #d7d7d7; padding: 7px 10px; border-radius: 0px; qproperty-alignment: AlignCenter;")
        preview_top_layout.addWidget(self.preview_status, 1)

        self.zoom_out = QPushButton("-")
        self.zoom_out.clicked.connect(lambda: self.set_preview_zoom(self.preview_zoom - 0.1))
        self._apply_button_style(self.zoom_out, "secondary")
        self.zoom_out.setFixedWidth(34)
        preview_top_layout.addWidget(self.zoom_out)

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(30, 200)
        self.zoom_slider.setSingleStep(5)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self.on_zoom_change)
        self.zoom_slider.setFixedWidth(140)
        self.zoom_slider.setStyleSheet(
            "QSlider::groove:horizontal { height: 5px; background: #d9d9d9; }"
            "QSlider::handle:horizontal { width: 13px; height: 13px; margin: -4px 0; background: #1f1f1f; border: 1px solid #1f1f1f; }"
            "QSlider::sub-page:horizontal { background: #666666; }"
        )
        preview_top_layout.addWidget(self.zoom_slider)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(48)
        self.zoom_label.setStyleSheet("color: #333333; font-size: 12px; font-weight: 600; qproperty-alignment: AlignCenter;")
        preview_top_layout.addWidget(self.zoom_label)

        self.zoom_in = QPushButton("+")
        self.zoom_in.clicked.connect(lambda: self.set_preview_zoom(self.preview_zoom + 0.1))
        self._apply_button_style(self.zoom_in, "secondary")
        self.zoom_in.setFixedWidth(34)
        preview_top_layout.addWidget(self.zoom_in)

        preview_layout.addWidget(preview_top)

        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setMinimumWidth(420)
        self.preview_scroll.setStyleSheet("QScrollArea { background: #ffffff; border: 1px solid #d9d9d9; }")
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("background: #ffffff; border: 1px solid #d9d9d9; min-height: 420px; margin: 0px;")
        self.preview_label.setMouseTracking(True)
        self.preview_label.installEventFilter(self)
        self.preview_scroll.setWidget(self.preview_label)
        preview_layout.addWidget(self.preview_scroll, 1)

        content_layout.addWidget(preview_group, 1)
        main_layout.addLayout(content_layout)

        self.statusBar().showMessage("就绪")

    # ---------- 事件 ----------
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def wheelEvent(self, event):
        if self.preview_scroll.underMouse() or self.preview_label.underMouse():
            delta = event.angleDelta().y()
            if delta > 0:
                self.set_preview_zoom(self.preview_zoom + 0.1)
            elif delta < 0:
                self.set_preview_zoom(self.preview_zoom - 0.1)
            event.accept()
            return
        super().wheelEvent(event)

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                self.load_image(path)

    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if path:
            self.load_image(path)

    def load_image(self, path):
        try:
            img = Image.open(path).convert('RGB')
            self.current_image = img
            # 记录宽高比
            self.aspect_ratio = img.width / img.height

            # 如果等比例已勾选，则根据当前宽度调整高度
            if self.aspect_checkbox.isChecked():
                self._apply_aspect_ratio(from_width=True)

            thumb = img.copy()
            thumb.thumbnail((300, 300))
            qimg = pil_to_qimage(thumb)
            pix = QPixmap.fromImage(qimg)
            self.img_label.setPixmap(pix)
            self.statusBar().showMessage(f"已加载: {os.path.basename(path)}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载图片失败: {e}")
        finally:
            gc.collect()

    def clear_image(self):
        self.current_image = None
        self.current_grid = None
        self.current_counts = None
        self.aspect_ratio = None
        self.img_label.clear()
        self.img_label.setText("拖拽图片到此处")
        self.preview_label.clear()
        self.preview_label.setStyleSheet("background: #ffffff; border: none;")
        self.preview_status.setText("等待生成")
        self.btn_save_png.setEnabled(False)
        self.btn_save_txt.setEnabled(False)
        self.btn_export_pdf.setEnabled(False)
        self.btn_export_svg.setEnabled(False)
        self.btn_print.setEnabled(False)
        self.statusBar().showMessage("已清除")
        gc.collect()

    def reset_parameters(self):
        self.max_colors = 16
        self.grid_width = 40
        self.grid_height = 40
        self.aspect_checkbox.setChecked(False)
        self.color_slider.setValue(self.max_colors)
        self.width_slider.setValue(self.grid_width)
        self.height_slider.setValue(self.grid_height)
        self.statusBar().showMessage("参数已重置")

    def set_preview_zoom(self, zoom_value):
        self.preview_zoom = max(0.3, min(2.0, zoom_value))
        self.zoom_slider.setValue(int(round(self.preview_zoom * 100)))
        self.zoom_label.setText(f"{int(round(self.preview_zoom * 100))}%")
        if self.current_grid is not None and self.current_counts is not None:
            self._refresh_preview()

    def on_zoom_change(self, value):
        self.preview_zoom = value / 100
        self.zoom_label.setText(f"{value}%")
        if self.current_grid is not None and self.current_counts is not None:
            self._refresh_preview()

    def _refresh_preview(self):
        if self.current_grid is None or self.current_counts is None:
            return
        plan_img = draw_bead_plan(self.current_grid, self.current_counts, cell_size=25)
        qimg = pil_to_qimage(plan_img)
        pix = QPixmap.fromImage(qimg)
        scaled = pix.scaled(
            max(1, int(pix.width() * self.preview_zoom)),
            max(1, int(pix.height() * self.preview_zoom)),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.preview_label.setPixmap(scaled)
        self.preview_label.setFixedSize(scaled.size())

    def on_aspect_toggled(self, checked):
        if checked and self.aspect_ratio is not None:
            self._apply_aspect_ratio(from_width=True)

    def _apply_aspect_ratio(self, from_width=True):
        """根据当前宽度或高度调整另一个维度以保持比例"""
        if self.aspect_ratio is None:
            return

        # 阻塞信号避免循环
        self.width_slider.blockSignals(True)
        self.width_spin.blockSignals(True)
        self.height_slider.blockSignals(True)
        self.height_spin.blockSignals(True)

        if from_width:
            # 根据当前宽度计算高度
            new_w = self.grid_width
            new_h = int(round(new_w / self.aspect_ratio))
            # 限制范围
            new_h = max(10, min(200, new_h))
            self.grid_height = new_h
            self.height_slider.setValue(new_h)
            self.height_spin.setValue(new_h)
        else:
            # 根据当前高度计算宽度
            new_h = self.grid_height
            new_w = int(round(new_h * self.aspect_ratio))
            new_w = max(10, min(200, new_w))
            self.grid_width = new_w
            self.width_slider.setValue(new_w)
            self.width_spin.setValue(new_w)

        # 恢复信号
        self.width_slider.blockSignals(False)
        self.width_spin.blockSignals(False)
        self.height_slider.blockSignals(False)
        self.height_spin.blockSignals(False)

    def on_color_change(self, val):
        self.color_spin.setValue(val)
        self.max_colors = val

    def on_color_spin(self, val):
        self.color_slider.setValue(val)
        self.max_colors = val

    def on_width_change(self, val):
        self.width_spin.setValue(val)
        self.grid_width = val
        if self.aspect_checkbox.isChecked() and self.aspect_ratio is not None:
            self._apply_aspect_ratio(from_width=True)

    def on_width_spin(self, val):
        self.width_slider.setValue(val)
        self.grid_width = val
        if self.aspect_checkbox.isChecked() and self.aspect_ratio is not None:
            self._apply_aspect_ratio(from_width=True)

    def on_height_change(self, val):
        self.height_spin.setValue(val)
        self.grid_height = val
        if self.aspect_checkbox.isChecked() and self.aspect_ratio is not None:
            self._apply_aspect_ratio(from_width=False)

    def on_height_spin(self, val):
        self.height_slider.setValue(val)
        self.grid_height = val
        if self.aspect_checkbox.isChecked() and self.aspect_ratio is not None:
            self._apply_aspect_ratio(from_width=False)

    def generate_plan(self):
        if self.current_image is None:
            QMessageBox.warning(self, "警告", "请先加载一张图片！")
            return

        self.btn_generate.setEnabled(False)
        self.statusBar().showMessage("正在生成图纸，请稍候...")

        self.thread = GenerateThread(
            np.array(self.current_image),
            self.grid_width,
            self.grid_height,
            self.max_colors
        )
        self.thread.finished.connect(self.on_generate_finished)
        self.thread.error.connect(self.on_generate_error)
        self.thread.start()

    def on_generate_finished(self, grid, counts):
        self.current_grid = grid
        self.current_counts = counts
        self.preview_label.setStyleSheet("background: #ffffff; border: 1px solid #d9d9d9; min-height: 420px; margin: 0px;")
        self._refresh_preview()
        self.preview_status.setText(f"已生成：{self.grid_width} * {self.grid_height} 格")
        self.btn_save_png.setEnabled(True)
        self.btn_save_txt.setEnabled(True)
        self.btn_export_pdf.setEnabled(True)
        self.btn_export_svg.setEnabled(True)
        self.btn_print.setEnabled(True)
        self.btn_generate.setEnabled(True)
        self.statusBar().showMessage("图纸生成完成！")
        gc.collect()

    def on_generate_error(self, err):
        QMessageBox.critical(self, "生成失败", f"错误信息: {err}")
        self.btn_generate.setEnabled(True)
        self.statusBar().showMessage("生成失败")

    def save_png(self):
        if self.current_grid is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存 PNG 图纸", "", "PNG Image (*.png)"
        )
        if path:
            plan_img = draw_bead_plan(self.current_grid, self.current_counts, cell_size=25)
            plan_img.save(path)
            self.statusBar().showMessage(f"已保存: {path}")

    def save_txt(self):
        if self.current_counts is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存颜色清单", "", "Text File (*.txt)"
        )
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write("拼豆颜色用量统计\n")
                f.write("==================\n")
                sorted_items = sorted(self.current_counts.items(), key=lambda kv: kv[1], reverse=True)
                total = sum(self.current_counts.values())
                for idx, cnt in sorted_items:
                    name = MARD221_NAMES[idx] if idx < len(MARD221_NAMES) else f"MARD-{idx+1:03d}"
                    f.write(f"{name}: {cnt} 粒\n")
                f.write(f"\n总豆子数: {total} 粒")
            self.statusBar().showMessage(f"已保存: {path}")

    def eventFilter(self, obj, event):
        """处理预览标签的鼠标事件：拖拽平移、滚轮缩放、双击重置"""
        if obj is self.preview_label:
            # ---------- 滚轮缩放 ----------
            if event.type() == QEvent.Type.Wheel:
                delta = event.angleDelta().y()
                if delta > 0:
                    self.set_preview_zoom(self.preview_zoom + 0.1)
                elif delta < 0:
                    self.set_preview_zoom(self.preview_zoom - 0.1)
                return True   # 阻止事件继续传递，避免与主窗口 wheelEvent 冲突

            # ---------- 双击重置缩放 ----------
            if event.type() == QEvent.Type.MouseButtonDblClick:
                # 重置缩放至 100%，并适应窗口
                self.preview_zoom = 1.0
                self.zoom_slider.setValue(100)
                self.zoom_label.setText("100%")
                if self.current_grid is not None and self.current_counts is not None:
                    self._refresh_preview()
                return True

            # ---------- 鼠标拖拽平移 ----------
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.drag_start_pos = event.position().toPoint()
                    self.scroll_bar_positions = (
                        self.preview_scroll.horizontalScrollBar().value(),
                        self.preview_scroll.verticalScrollBar().value()
                    )
                    self.preview_label.setCursor(Qt.CursorShape.ClosedHandCursor)
                    return True

            if event.type() == QEvent.Type.MouseMove:
                if self.drag_start_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
                    delta = event.position().toPoint() - self.drag_start_pos
                    h_scroll = self.preview_scroll.horizontalScrollBar()
                    v_scroll = self.preview_scroll.verticalScrollBar()
                    h_scroll.setValue(self.scroll_bar_positions[0] - delta.x())
                    v_scroll.setValue(self.scroll_bar_positions[1] - delta.y())
                    return True

            if event.type() == QEvent.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.drag_start_pos = None
                    self.scroll_bar_positions = None
                    self.preview_label.setCursor(Qt.CursorShape.OpenHandCursor)
                    return True

        return super().eventFilter(obj, event)

    def export_pdf(self):
        """导出为 PDF 文件（使用 QPrinter）"""
        if self.current_grid is None or self.current_counts is None:
            return
        # 获取保存路径
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 PDF 图纸", "", "PDF Files (*.pdf)"
        )
        if not path:
            return

        # 生成图纸（使用较大分辨率）
        plan_img = draw_bead_plan(self.current_grid, self.current_counts, cell_size=25)
        qimg = pil_to_qimage(plan_img)
        pix = QPixmap.fromImage(qimg)

        # 设置打印机
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(path)
        # 设置页面大小为图纸大小（以点为单位，1/72英寸）
        # 将像素转换为点（假设图像 DPI=96，打印机默认 72dpi，但我们可以直接设置物理尺寸）
        # 更可靠：设置页面大小为图片尺寸（72dpi）
        dpi = 72
        width_pts = pix.width() * (dpi / 96)  # 因为 QPixmap 以 96dpi 存储
        height_pts = pix.height() * (dpi / 96)
        printer.setPageSize(QPrinter.PageSize.Custom)
        printer.setPageSizeMM(QPageSize(QSizeF(width_pts/72, height_pts/72), QPageSize.Unit.Inch))

        painter = QPainter(printer)
        # 绘制图像，缩放至页面
        rect = painter.viewport()
        # 保持比例填充
        scaled_pix = pix.scaled(rect.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        painter.drawPixmap(0, 0, scaled_pix)
        painter.end()
        self.statusBar().showMessage(f"PDF 已导出: {path}")

    def export_svg(self):
        """导出为 SVG 矢量图"""
        if self.current_grid is None or self.current_counts is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 SVG 图纸", "", "SVG Files (*.svg)"
        )
        if not path:
            return
        try:
            from bead_core import draw_bead_plan_svg
            dwg = draw_bead_plan_svg(self.current_grid, self.current_counts, cell_size=25)
            dwg.saveas(path)
            self.statusBar().showMessage(f"SVG 已导出: {path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出 SVG 时出错：{e}")

    def print_plan(self):
        """调用系统打印对话框打印图纸"""
        if self.current_grid is None or self.current_counts is None:
            return
        # 生成图纸
        plan_img = draw_bead_plan(self.current_grid, self.current_counts, cell_size=25)
        qimg = pil_to_qimage(plan_img)
        pix = QPixmap.fromImage(qimg)

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() != QPrintDialog.DialogCode.Accepted:
            return

        painter = QPainter(printer)
        rect = painter.viewport()
        # 缩放至页面，保持比例
        scaled_pix = pix.scaled(rect.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        painter.drawPixmap(0, 0, scaled_pix)
        painter.end()
        self.statusBar().showMessage("打印完成")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("SimSun", 9)
    app.setFont(font)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())