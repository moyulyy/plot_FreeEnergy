# -*- coding: utf-8 -*-
########################################################################################
# Energy Profile Studio  —  势能面剖面图可视化工作台                                    #
# ------------------------------------------------------------------------------------ #
#  · PySide6 (Qt 6) 实现，iOS 风格界面：左右分栏、圆角卡片、开关/分段控件、平滑滚动      #
#  · 左侧输入数据与参数，右侧实时预览；滚轮缩放 / 拖动平移 / 双击复位（Matplotlib 事件） #
#  · 数据可直接填写，也可从 Excel / CSV 导入                                            #
#  · 绘图核心复用 plot_core.py；原 Tkinter 版本保留为 Plot_EnergyProfile-GUI.py         #
#  · 运行: D:\\miniconda3\\envs\\chem_env\\python.exe Plot_EnergyProfile-Studio.py      #
########################################################################################

import os
import sys
import json
import traceback

import matplotlib

matplotlib.use("QtAgg")

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PySide6.QtCore import (Qt, QTimer, QRectF, QSize, QPointF, Signal, Property,
                            QPropertyAnimation, QEasingCurve, QEvent)
from PySide6.QtGui import (QColor, QPainter, QFont, QPixmap, QIcon, QAction,
                           QKeySequence, QLinearGradient, QBrush, QPen)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QLineEdit, QPushButton,
    QComboBox, QSlider, QScrollArea, QVBoxLayout, QHBoxLayout, QGridLayout,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView,
    QColorDialog, QFileDialog, QMessageBox, QSizePolicy, QGraphicsDropShadowEffect,
    QAbstractButton, QSpacerItem, QToolButton,
)

import plot_core as pc


# =====================================================================================
#  样式表 (iOS 风格)
# =====================================================================================
QSS = """
QMainWindow, QWidget#Root, QWidget#Sidebar, QWidget#ScrollBody {
    background: #F2F2F7;
}
QWidget { font-family: "Microsoft YaHei UI", "Segoe UI", "PingFang SC", sans-serif; }

QLabel { background: transparent; color: #1C1C1E; font-size: 13px; }
QLabel#H1 { font-size: 20px; font-weight: 700; color: #1C1C1E; }
QLabel#H2 { font-size: 11px; color: #8E8E93; }
QLabel#CardTitle { font-size: 12px; font-weight: 700; color: #8E8E93; }
QLabel#Hint { font-size: 11px; color: #8E8E93; }
QLabel#Value { font-size: 12px; font-weight: 700; color: #007AFF; }

QFrame#Card {
    background: #FFFFFF;
    border-radius: 18px;
    border: 1px solid #ECECF1;
}
QFrame#PlotCard {
    background: #FFFFFF;
    border-radius: 18px;
    border: 1px solid #ECECF1;
}

QLineEdit {
    background: #F7F7FA;
    border: 1px solid #E3E3E8;
    border-radius: 9px;
    padding: 7px 10px;
    color: #1C1C1E;
    selection-background-color: #007AFF;
    selection-color: #FFFFFF;
}
QLineEdit:focus { border: 1px solid #007AFF; background: #FFFFFF; }
QLineEdit:disabled { color: #B4B4BA; background: #F1F1F4; }

QComboBox {
    background: #F7F7FA;
    border: 1px solid #E3E3E8;
    border-radius: 9px;
    padding: 6px 10px;
    color: #1C1C1E;
}
QComboBox:focus { border: 1px solid #007AFF; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: #FFFFFF;
    border: 1px solid #E3E3E8;
    border-radius: 10px;
    padding: 4px;
    outline: none;
    selection-background-color: #007AFF;
    selection-color: #FFFFFF;
}

QPushButton#Primary {
    background: #007AFF; color: #FFFFFF; border: none;
    border-radius: 11px; padding: 9px 18px; font-weight: 700;
}
QPushButton#Primary:hover { background: #1A88FF; }
QPushButton#Primary:pressed { background: #0060DF; }

QPushButton#Secondary {
    background: #E9E9EB; color: #007AFF; border: none;
    border-radius: 11px; padding: 9px 16px; font-weight: 700;
}
QPushButton#Secondary:hover { background: #DFDFE4; }
QPushButton#Secondary:pressed { background: #D3D3D9; }

QPushButton#Danger {
    background: #E9E9EB; color: #FF3B30; border: none;
    border-radius: 11px; padding: 9px 16px; font-weight: 700;
}
QPushButton#Danger:hover { background: #F6DEDD; }
QPushButton#Danger:pressed { background: #EFCFCE; }

QPushButton#Step {
    background: #E9E9EB; color: #1C1C1E; border: none;
    border-radius: 9px; font-size: 16px; font-weight: 700;
}
QPushButton#Step:hover { background: #DFDFE4; }
QPushButton#Step:pressed { background: #D3D3D9; }

QSlider::groove:horizontal { height: 4px; background: #E9E9EB; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #007AFF; border-radius: 2px; }
QSlider::handle:horizontal {
    background: #FFFFFF; border: 1px solid #D1D1D6;
    width: 18px; height: 18px; margin: -8px 0; border-radius: 9px;
}
QSlider::handle:horizontal:hover { border: 1px solid #007AFF; }

QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #C7C7CC; border-radius: 5px; min-height: 36px; }
QScrollBar::handle:vertical:hover { background: #AEAEB2; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #C7C7CC; border-radius: 5px; min-width: 36px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

QTableWidget { background: transparent; border: none; gridline-color: transparent; }
QTableWidget::item { border: none; }
QTableWidget::item:selected { background: transparent; }

QToolTip {
    background: #2C2C2E; color: #FFFFFF; border: none;
    padding: 6px 10px; border-radius: 8px;
}
"""


# =====================================================================================
#  应用图标 (与 make_icon.py 生成的 app.ico 一致)
# =====================================================================================
PROFILE_SHAPE = [(0.155, 0.620), (0.290, 0.620), (0.410, 0.300),
                 (0.530, 0.700), (0.660, 0.330), (0.790, 0.600),
                 (0.880, 0.600)]


def app_logo_pixmap(size=256):
    """iOS 风格圆角方块 + 蓝色渐变 + 白色能垒曲线"""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    grad = QLinearGradient(0, 0, 0, size)
    grad.setColorAt(0.0, QColor("#4DA3FF"))
    grad.setColorAt(1.0, QColor("#0052CC"))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(grad))
    radius = 0.225 * size
    p.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)

    pts = [QPointF(x * size, y * size) for x, y in PROFILE_SHAPE]
    pen = QPen(QColor("#FFFFFF"))
    pen.setWidthF(0.066 * size)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    for a, b in zip(pts, pts[1:]):
        p.drawLine(a, b)

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#FFFFFF"))
    r = 0.030 * size
    for pt in pts:
        p.drawEllipse(pt, r, r)
    p.end()
    return pix


# =====================================================================================
#  iOS 风格自定义控件
# =====================================================================================
def _blend(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return QColor(int(c1.red() + (c2.red() - c1.red()) * t),
                  int(c1.green() + (c2.green() - c1.green()) * t),
                  int(c1.blue() + (c2.blue() - c1.blue()) * t))


class Switch(QAbstractButton):
    """iOS 开关 (带过渡动画)"""

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(50, 30)
        self._offset = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate)

    def sizeHint(self):
        return QSize(50, 30)

    def _get_offset(self):
        return self._offset

    def _set_offset(self, value):
        self._offset = float(value)
        self.update()

    offset = Property(float, _get_offset, _set_offset)

    def _animate(self, checked):
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        track = _blend(QColor(pc.TRACK), QColor(pc.GREEN), self._offset)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)
        d = h - 6
        x = 3 + self._offset * (w - d - 6)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QRectF(x, 3, d, d))


class SegmentedControl(QWidget):
    """iOS 分段控件 (带滑动指示块)"""

    currentChanged = Signal(str)

    def __init__(self, items, current=0, parent=None):
        super().__init__(parent)
        self._items = list(items)
        self._index = max(0, min(current, len(self._items) - 1))
        self._indicator = float(self._index)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(34)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        fm = self.fontMetrics()
        self._widths = [fm.horizontalAdvance(t) + 30 for t in self._items]
        self.setFixedWidth(sum(self._widths) + 4)
        self._anim = QPropertyAnimation(self, b"indicator", self)
        self._anim.setDuration(170)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _get_indicator(self):
        return self._indicator

    def _set_indicator(self, value):
        self._indicator = float(value)
        self.update()

    indicator = Property(float, _get_indicator, _set_indicator)

    def _seg_x(self, i):
        return 2 + sum(self._widths[:i])

    def currentText(self):
        return self._items[self._index]

    def currentIndex(self):
        return self._index

    def setCurrentText(self, text):
        if text in self._items:
            self.setCurrentIndex(self._items.index(text))

    def setCurrentIndex(self, index):
        index = max(0, min(index, len(self._items) - 1))
        if index == self._index:
            return
        self._index = index
        self._anim.stop()
        self._anim.setStartValue(self._indicator)
        self._anim.setEndValue(float(index))
        self._anim.start()
        self.currentChanged.emit(self.currentText())

    def mousePressEvent(self, event):
        x = event.position().x()
        acc = 2
        for i, w in enumerate(self._widths):
            if acc <= x <= acc + w:
                self.setCurrentIndex(i)
                return
            acc += w

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        h = self.height()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(pc.TRACK))
        p.drawRoundedRect(QRectF(0, 0, self.width(), h), h / 2, h / 2)
        px = self._seg_x(int(round(self._indicator)))
        pw = self._widths[int(round(self._indicator))]
        p.setBrush(QColor("#FFFFFF"))
        p.drawRoundedRect(QRectF(px + 1, 2, pw - 2, h - 4), (h - 4) / 2, (h - 4) / 2)
        for i, t in enumerate(self._items):
            p.setPen(QColor(pc.TEXT) if i == self._index else QColor(pc.SUB))
            p.drawText(QRectF(self._seg_x(i), 0, self._widths[i], h),
                       Qt.AlignmentFlag.AlignCenter, t)


class Stepper(QWidget):
    """数值步进器"""

    valueChanged = Signal(int)

    def __init__(self, value=5, minimum=2, maximum=20, parent=None):
        super().__init__(parent)
        self._value = value
        self._min, self._max = minimum, maximum
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self._minus = QPushButton("\u2212")
        self._plus = QPushButton("+")
        for b in (self._minus, self._plus):
            b.setObjectName("Step")
            b.setFixedSize(28, 28)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
        self._label = QLabel(str(value))
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setFixedWidth(26)
        self._label.setStyleSheet("font-weight:700;")
        self._minus.clicked.connect(lambda: self._step(-1))
        self._plus.clicked.connect(lambda: self._step(1))
        lay.addWidget(self._minus)
        lay.addWidget(self._label)
        lay.addWidget(self._plus)

    def _step(self, delta):
        value = max(self._min, min(self._max, self._value + delta))
        if value != self._value:
            self.setValue(value)
            self.valueChanged.emit(value)

    def value(self):
        return self._value

    def setValue(self, value):
        self._value = max(self._min, min(self._max, value))
        self._label.setText(str(self._value))


def add_shadow(widget, blur=26, dy=5, alpha=22):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setXOffset(0)
    effect.setYOffset(dy)
    effect.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(effect)


class PlotCanvas(FigureCanvasQTAgg):
    """Matplotlib 画布：滚轮缩放 / 拖动平移 / 双击复位"""

    def __init__(self, figure):
        super().__init__(figure)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.home = None
        self._pan = None
        self.mpl_connect("scroll_event", self._on_scroll)
        self.mpl_connect("button_press_event", self._on_press)
        self.mpl_connect("motion_notify_event", self._on_motion)
        self.mpl_connect("button_release_event", self._on_release)

    def _axes(self):
        return self.figure.axes[0] if self.figure.axes else None

    def _on_scroll(self, event):
        ax = self._axes()
        if ax is None or event.inaxes is None:
            return
        xlim, ylim = ax.get_xlim(), ax.get_ylim()
        xd, yd = ax.transData.inverted().transform((event.x, event.y))
        scale = 0.85 if event.step > 0 else 1.0 / 0.85
        w = (xlim[1] - xlim[0]) * scale
        h = (ylim[1] - ylim[0]) * scale
        fx = (xd - xlim[0]) / (xlim[1] - xlim[0]) if xlim[1] != xlim[0] else 0.5
        fy = (yd - ylim[0]) / (ylim[1] - ylim[0]) if ylim[1] != ylim[0] else 0.5
        ax.set_xlim(xd - fx * w, xd + (1 - fx) * w)
        ax.set_ylim(yd - fy * h, yd + (1 - fy) * h)
        self.draw_idle()

    def _on_press(self, event):
        if event.dblclick:
            self.reset_view()
            return
        if event.button != 1 or event.inaxes is None:
            return
        ax = self._axes()
        if ax is None:
            return
        self._pan = (event.x, event.y, ax.get_xlim(), ax.get_ylim())
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def _on_motion(self, event):
        ax = self._axes()
        if ax is None or self._pan is None or event.x is None:
            return
        px, py, (xlo, xhi), (ylo, yhi) = self._pan
        bbox = ax.get_window_extent()
        if bbox.width <= 0 or bbox.height <= 0:
            return
        dx = (event.x - px) / bbox.width * (xhi - xlo)
        dy = (event.y - py) / bbox.height * (yhi - ylo)
        ax.set_xlim(xlo - dx, xhi - dx)
        ax.set_ylim(ylo - dy, yhi - dy)
        self.draw_idle()

    def _on_release(self, _):
        self._pan = None
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def reset_view(self):
        ax = self._axes()
        if ax is None or self.home is None:
            return
        ax.set_xlim(self.home[0])
        ax.set_ylim(self.home[1])
        self.draw_idle()

    def wheelEvent(self, event):
        # 交给 Matplotlib 基类处理，由它发出 scroll_event
        super().wheelEvent(event)


# =====================================================================================
#  数据表格 (横向 = 路径，纵向 = 台阶)
# =====================================================================================
class DataTable(QTableWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.labels = list(pc.SAMPLE_LABELS)
        self.paths = [{"name": p["name"], "color": p["color"],
                       "style": p["style"], "values": list(p["values"])}
                      for p in pc.SAMPLE_PATHS]
        self._loading = False
        self._label_edits = []
        self._name_edits = []
        self._style_combos = []
        self._color_buttons = []
        self._value_edits = []
        self._edit_index = {}
        self._focus_cell = (3, 1)

        self.setShowGrid(False)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setVisible(False)
        self.setWordWrap(False)
        self._build()

    # ---------- 构建 ----------
    def _line(self, text):
        edit = QLineEdit(str(text))
        edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        edit.textChanged.connect(self._on_edit)
        return edit

    def _pad(self, widget, margin=3):
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(margin, margin, margin, margin)
        lay.addWidget(widget)
        return box

    def _color_qss(self, color):
        return ("QPushButton{background:%s;border:1px solid %s;border-radius:8px;}"
                "QPushButton:hover{border:1px solid %s;}" % (color, pc.BORDER, pc.BLUE))

    def _build(self):
        self._loading = True
        self._edit_index = {}
        m, n = len(self.labels), len(self.paths)
        self.clear()
        self.setRowCount(3 + m)
        self.setColumnCount(1 + n)
        self.setColumnWidth(0, 118)
        for c in range(1, 1 + n):
            self.setColumnWidth(c, 118)
        for r in range(3 + m):
            self.setRowHeight(r, 40)

        for r, text in ((0, "节点 / 路径"), (1, "颜色"), (2, "线型")):
            item = QTableWidgetItem(text)
            item.setForeground(QColor(pc.SUB))
            font = item.font()
            font.setBold(True)
            font.setPointSize(9)
            item.setFont(font)
            self.setItem(r, 0, item)

        self._label_edits = []
        for j, label in enumerate(self.labels):
            edit = self._line(label)
            self._register_edit(edit, 3 + j, 0)
            self._label_edits.append(edit)
            self.setCellWidget(3 + j, 0, self._pad(edit))

        self._name_edits, self._style_combos = [], []
        self._color_buttons, self._value_edits = [], []
        for i, p in enumerate(self.paths):
            col = 1 + i
            name = self._line(p["name"])
            self._register_edit(name, 0, col)
            self._name_edits.append(name)
            self.setCellWidget(0, col, self._pad(name))

            btn = QPushButton()
            btn.setFixedSize(30, 30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self._color_qss(p["color"]))
            btn.clicked.connect(lambda _=False, idx=i, b=btn: self._pick_color(idx, b))
            self._color_buttons.append(btn)
            self.setCellWidget(1, col, self._pad(btn))

            combo = QComboBox()
            combo.addItems(pc.STYLE_NAMES)
            combo.setCurrentText(pc.STYLE_REV.get(p["style"], "实线"))
            combo.currentIndexChanged.connect(self._on_edit)
            self._style_combos.append(combo)
            self.setCellWidget(2, col, self._pad(combo))

            column_edits = []
            for j in range(m):
                value = p["values"][j] if j < len(p["values"]) else ""
                edit = self._line("" if value in ("", None) else value)
                self._register_edit(edit, 3 + j, col)
                column_edits.append(edit)
                self.setCellWidget(3 + j, col, self._pad(edit))
            self._value_edits.append(column_edits)

        self._loading = False

    def _on_edit(self, *_):
        if not self._loading:
            self.changed.emit()

    def _pick_color(self, idx, button):
        color = QColorDialog.getColor(QColor(self.paths[idx]["color"]), self,
                                      "选择路径颜色")
        if color.isValid():
            self.paths[idx]["color"] = color.name().upper()
            button.setStyleSheet(self._color_qss(self.paths[idx]["color"]))
            self.changed.emit()

    # ---------- 粘贴 (支持从 Excel 直接复制一列/一块) ----------
    def _register_edit(self, edit, row, col):
        self._edit_index[edit] = (row, col)
        edit.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.FocusIn and obj in self._edit_index:
            self._focus_cell = self._edit_index[obj]
        if (event.type() == QEvent.Type.KeyPress
                and event.matches(QKeySequence.StandardKey.Paste)):
            self.paste_clipboard()
            return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.Paste):
            self.paste_clipboard()
            return
        super().keyPressEvent(event)

    @staticmethod
    def _clean_cell(text):
        s = str(text).strip()
        if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
            s = s[1:-1].strip()
        return s

    @classmethod
    def parse_clipboard(cls, text):
        """把剪贴板文本解析为二维表 (Excel 复制的一列/一块)"""
        text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
        lines = text.split("\n")
        while lines and lines[-1].strip() == "":
            lines.pop()
        data = []
        for line in lines:
            cells = line.split("\t")
            while cells and cells[-1].strip() == "":
                cells.pop()
            data.append([cls._clean_cell(c) for c in cells])
        return [row for row in data if row]

    def paste_clipboard(self, data=None):
        """把剪贴板内容粘贴到当前单元格，并自动扩展台阶数 / 路径数"""
        if data is None:
            data = self.parse_clipboard(QApplication.clipboard().text())
        if not data:
            return False
        n_rows = len(data)
        n_cols = max(len(r) for r in data)
        r0, c0 = self._focus_cell
        r0 = max(0, min(r0, 2 + len(self.labels)))
        c0 = max(0, min(c0, len(self.paths)))

        points = len(self.labels)
        paths = len(self.paths)
        if r0 >= 3:
            points = max(points, r0 + n_rows - 3)
        if c0 >= 1:
            paths = max(paths, c0 + n_cols - 1)
        elif n_cols > 1:
            paths = max(paths, n_cols - 1)
        if points != len(self.labels) or paths != len(self.paths):
            self.set_counts(points=points, paths=paths)

        self._loading = True
        for i, row in enumerate(data):
            for j, value in enumerate(row):
                self._set_cell(r0 + i, c0 + j, value)
        self._loading = False
        self.changed.emit()
        return True

    def _set_cell(self, row, col, text):
        text = str(text)
        if row >= 3 and col == 0:
            j = row - 3
            if 0 <= j < len(self._label_edits):
                self._label_edits[j].setText(text)
        elif row >= 3 and col >= 1:
            i, j = col - 1, row - 3
            if 0 <= i < len(self._value_edits) and 0 <= j < len(self._value_edits[i]):
                self._value_edits[i][j].setText(text)
        elif row == 0 and col >= 1:
            i = col - 1
            if 0 <= i < len(self._name_edits):
                self._name_edits[i].setText(text)
        elif row == 1 and col >= 1:
            i = col - 1
            if 0 <= i < len(self._color_buttons):
                color = pc.normalize_color(text, self.paths[i]["color"])
                self.paths[i]["color"] = color
                self._color_buttons[i].setStyleSheet(self._color_qss(color))
        elif row == 2 and col >= 1:
            i = col - 1
            if 0 <= i < len(self._style_combos):
                name = pc.STYLE_REV.get(text.strip())
                if name:
                    self._style_combos[i].setCurrentText(name)

    # ---------- 同步 ----------
    def _sync(self):
        m, n = len(self.labels), len(self.paths)
        for j in range(min(m, len(self._label_edits))):
            self.labels[j] = self._label_edits[j].text()
        for i in range(min(n, len(self._name_edits))):
            self.paths[i]["name"] = self._name_edits[i].text()
            self.paths[i]["style"] = pc.STYLE_MAP.get(
                self._style_combos[i].currentText(), "-")
            row = self._value_edits[i]
            self.paths[i]["values"] = [row[j].text() for j in range(min(m, len(row)))]

    # ---------- 增删 ----------
    def set_counts(self, points=None, paths=None):
        self._sync()
        if points is not None:
            while len(self.labels) < points:
                self.labels.append("节点%d" % (len(self.labels) + 1))
                for p in self.paths:
                    p["values"].append("")
            self.labels = self.labels[:points]
            for p in self.paths:
                p["values"] = (list(p["values"]) + [""] * points)[:points]
        if paths is not None:
            while len(self.paths) < paths:
                i = len(self.paths)
                self.paths.append({
                    "name": "路径 %s" % chr(65 + i),
                    "color": pc.PALETTE[i % len(pc.PALETTE)],
                    "style": "-",
                    "values": [""] * len(self.labels)})
            self.paths = self.paths[:paths]
        self._build()

    # ---------- 读取 / 写入 ----------
    def get_data(self):
        self._sync()
        labels = [(s.strip() or "P%d" % (i + 1))
                  for i, s in enumerate(self.labels)]
        paths = []
        for i, p in enumerate(self.paths):
            values = []
            for j, v in enumerate(p["values"]):
                s = str(v).strip()
                if s == "":
                    values.append("")
                else:
                    try:
                        values.append(float(s))
                    except ValueError:
                        raise ValueError(
                            "路径「%s」台阶「%s」的能量值「%s」不是有效数字。"
                            % (p["name"], labels[j], s))
            if any(v != "" for v in values):
                paths.append({"name": p["name"].strip() or "Path %s" % chr(65 + i),
                              "color": p["color"], "style": p["style"],
                              "values": values})
        if not paths:
            raise ValueError("请至少为一条路径输入能量数据。")
        for j in range(len(labels)):
            if all(p["values"][j] == "" for p in paths):
                raise ValueError("台阶「%s」在所有路径中都没有能量数据，"
                                 "请补充或删除该台阶。" % labels[j])
        return labels, paths

    def set_data(self, labels, paths):
        self.labels = [str(s) for s in labels]
        m = len(self.labels)
        self._focus_cell = (3, 1)
        self.paths = []
        for i, p in enumerate(paths):
            values = list(p.get("values", []))
            values = (values + [""] * m)[:m]
            self.paths.append({
                "name": str(p.get("name", "")),
                "color": pc.normalize_color(p.get("color", ""),
                                            pc.PALETTE[i % len(pc.PALETTE)]),
                "style": str(p.get("style", "-")),
                "values": ["" if v in ("", None) else str(v) for v in values]})
        if not self.paths:
            self.paths.append({"name": "路径 A", "color": pc.PALETTE[0],
                               "style": "-", "values": [""] * m})
        self._build()

    # ---------- 导入 ----------
    def load_table(self, rows):
        table = [[("" if c is None else str(c)) for c in row] for row in rows]
        table = [r for r in table if any(c.strip() != "" for c in r)]
        if len(table) < 2:
            raise ValueError("表格内容过少：至少需要 1 行表头 + 1 行数据。")
        names = [c.strip() for c in table[0][1:]]
        while names and names[-1] == "":
            names.pop()
        if not names:
            raise ValueError("未识别到路径名称：第 1 行从第 2 列起应为路径名称。")
        n_paths = len(names)

        def low(x):
            return str(x).strip().lower()

        r = 1
        colors = styles = None
        if len(table) > r and low(table[r][0]) in ("color", "colour", "颜色"):
            colors = [c.strip() for c in table[r][1:1 + n_paths]]
            r += 1
        if len(table) > r and low(table[r][0]) in ("linestyle", "line style",
                                                   "style", "线型", "样式"):
            styles = [c.strip() for c in table[r][1:1 + n_paths]]
            r += 1

        labels, values = [], [[] for _ in range(n_paths)]
        for row in table[r:]:
            label = row[0].strip() if row else ""
            if label == "":
                continue
            labels.append(label)
            for i in range(n_paths):
                values[i].append(row[i + 1].strip() if (i + 1) < len(row) else "")
        if not labels:
            raise ValueError("未识别到台阶（节点）数据行。")
        if len(labels) > 80 or n_paths > 20:
            raise ValueError("数据过大：最多支持 20 条路径、80 个台阶。")

        paths = []
        for i in range(n_paths):
            color = colors[i] if colors and i < len(colors) and colors[i] else ""
            style = styles[i] if styles and i < len(styles) and styles[i] else "-"
            paths.append({"name": names[i] or "Path %s" % chr(65 + i),
                          "color": pc.normalize_color(color, pc.PALETTE[i % len(pc.PALETTE)]),
                          "style": style, "values": values[i]})
        self.set_data(labels, paths)
        return len(labels), len(paths)

    def import_file(self, parent=None):
        path, _ = QFileDialog.getOpenFileName(
            parent or self, "导入反应路径数据", "",
            "Excel / CSV (*.xlsx *.xlsm *.csv *.txt);;Excel (*.xlsx *.xlsm);;"
            "CSV (*.csv);;所有文件 (*)")
        if not path:
            return False
        try:
            rows = pc.read_table(path)
            n_pts, n_paths = self.load_table(rows)
            QMessageBox.information(parent or self, "导入成功",
                                    "已导入 %d 条路径、%d 个台阶。\n%s"
                                    % (n_paths, n_pts, path))
            return True
        except Exception as exc:
            QMessageBox.critical(parent or self, "导入失败", str(exc))
            return False


# =====================================================================================
#  主窗口
# =====================================================================================
class StudioWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Energy Profile Studio · 能垒图工作台")
        self.setWindowIcon(QIcon(app_logo_pixmap(256)))
        self.resize(1520, 940)
        self.setMinimumSize(1280, 800)

        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(260)
        self._render_timer.timeout.connect(lambda: self.render(silent=True))

        central = QWidget()
        central.setObjectName("Root")
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_main(), 1)

        self._install_shortcuts()
        QTimer.singleShot(200, self.render)

    # ------------------------------------------------------------------ 快捷方式
    def _install_shortcuts(self):
        for key, func in ((QKeySequence.StandardKey.Save, self.save_image),
                          (QKeySequence("Ctrl+R"), self.reset_view),
                          (QKeySequence("Ctrl+O"), self._import_table)):
            action = QAction(self)
            action.setShortcut(key)
            action.triggered.connect(func)
            self.addAction(action)

    # ------------------------------------------------------------------ 侧边栏
    def _sidebar_header(self):
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(22, 18, 22, 10)
        lay.setSpacing(12)
        icon = QLabel()
        icon.setFixedSize(42, 42)
        icon.setPixmap(app_logo_pixmap(168).scaled(
            42, 42, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))
        lay.addWidget(icon)
        text_box = QVBoxLayout()
        text_box.setSpacing(0)
        title = QLabel("能垒图工作台")
        title.setObjectName("H1")
        sub = QLabel("Energy Profile Studio")
        sub.setObjectName("H2")
        text_box.addWidget(title)
        text_box.addWidget(sub)
        lay.addLayout(text_box)
        lay.addStretch()
        return box

    def _build_sidebar(self):
        panel = QWidget()
        panel.setObjectName("Sidebar")
        panel.setFixedWidth(626)
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._sidebar_header())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        body.setObjectName("ScrollBody")
        lay = QVBoxLayout(body)
        lay.setContentsMargins(18, 4, 18, 20)
        lay.setSpacing(16)

        self._build_title_card(lay)
        self._build_data_card(lay)
        self._build_style_card(lay)
        self._build_size_card(lay)
        self._build_export_card(lay)
        lay.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        bottom = QWidget()
        bottom.setObjectName("Sidebar")
        bar = QHBoxLayout(bottom)
        bar.setContentsMargins(22, 10, 22, 18)
        bar.setSpacing(10)
        render_btn = QPushButton("生成 / 更新图像")
        render_btn.setObjectName("Primary")
        render_btn.setMinimumHeight(46)
        render_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        render_btn.clicked.connect(lambda: self.render())
        reset_btn = QPushButton("重置参数")
        reset_btn.setObjectName("Secondary")
        reset_btn.setMinimumHeight(46)
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.clicked.connect(self.reset_params)
        bar.addWidget(render_btn, 2)
        bar.addWidget(reset_btn, 1)
        outer.addWidget(bottom)
        return panel

    # ------------------------------------------------------------------ 卡片工具
    def _card(self, parent_layout, title):
        card = QFrame()
        card.setObjectName("Card")
        add_shadow(card)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(10)
        label = QLabel(title)
        label.setObjectName("CardTitle")
        layout.addWidget(label)
        parent_layout.addWidget(card)
        return layout

    def _row(self, parent_layout, label, widget, label_width=90, fill=False):
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        text = QLabel(label)
        text.setMinimumWidth(label_width)
        lay.addWidget(text)
        if fill:
            lay.addWidget(widget, 1)
        else:
            lay.addStretch()
            lay.addWidget(widget)
        parent_layout.addWidget(box)
        return box

    def _stack(self, parent_layout, label, widget):
        parent_layout.addWidget(self._small_label(label))
        parent_layout.addWidget(widget)
        return widget

    def _small_label(self, text):
        label = QLabel(text)
        label.setStyleSheet("font-size:12px;color:#3A3A3C;")
        return label

    def _line(self, text="", placeholder=""):
        edit = QLineEdit(text)
        if placeholder:
            edit.setPlaceholderText(placeholder)
        edit.textChanged.connect(self._schedule_render)
        return edit

    def _combo(self, items, current=None, on_change=True):
        combo = QComboBox()
        combo.addItems(items)
        if current is not None:
            combo.setCurrentText(current)
        if on_change:
            combo.currentIndexChanged.connect(self._schedule_render)
        return combo

    def _slider(self, minimum, maximum, value, step=1, suffix=""):
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        slider.setSingleStep(step)
        slider.setPageStep(step)
        value_label = QLabel(self._fmt(value) + suffix)
        value_label.setObjectName("Value")
        value_label.setFixedWidth(42)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        slider.valueChanged.connect(
            lambda v, l=value_label, s=suffix: l.setText(self._fmt(v) + s))
        slider.valueChanged.connect(self._schedule_render)
        lay.addWidget(slider, 1)
        lay.addWidget(value_label)
        return box, slider

    @staticmethod
    def _fmt(value):
        f = float(value)
        return str(int(f)) if f == int(f) else ("%g" % f)

    # ------------------------------------------------------------------ 卡片内容
    def _build_title_card(self, lay):
        card = self._card(lay, "标题与坐标轴")
        self.inp_title = self._line("Relative Energy Profile along the reaction path")
        self._stack(card, "图表标题", self.inp_title)
        self.inp_xlabel = self._line("Reaction coordinate")
        self._stack(card, "横轴标题", self.inp_xlabel)
        self.inp_ylabel = self._line("Relative Energy \u0394G (eV)")
        self._stack(card, "纵轴标题", self.inp_ylabel)

    def _build_data_card(self, lay):
        card = self._card(lay, "反应路径数据")
        hint = QLabel("横向为多条路径，纵向为每条路径的多个台阶；台阶名含 TS 视为过渡态。"
                      "可直接填写，从 Excel 复制一列后在单元格 Ctrl+V 粘贴，"
                      "缺少的台阶会自动补齐。")
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        card.addWidget(hint)

        controls = QWidget()
        controls_lay = QHBoxLayout(controls)
        controls_lay.setContentsMargins(0, 0, 0, 0)
        controls_lay.setSpacing(8)
        controls_lay.addWidget(self._small_label("台阶数"))
        self.point_stepper = Stepper(len(pc.SAMPLE_LABELS), 2, 80)
        self.point_stepper.valueChanged.connect(self._on_points_changed)
        controls_lay.addWidget(self.point_stepper)
        controls_lay.addSpacing(12)
        controls_lay.addWidget(self._small_label("路径数"))
        self.path_stepper = Stepper(len(pc.SAMPLE_PATHS), 1, 20)
        self.path_stepper.valueChanged.connect(self._on_paths_changed)
        controls_lay.addWidget(self.path_stepper)
        controls_lay.addStretch()
        card.addWidget(controls)

        self.table = DataTable()
        self.table.changed.connect(self._sync_steppers)
        self.table.changed.connect(self._schedule_render)
        self.table.setMinimumHeight(300)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        card.addWidget(self.table)

        tools = QWidget()
        tools_lay = QHBoxLayout(tools)
        tools_lay.setContentsMargins(0, 0, 0, 0)
        tools_lay.setSpacing(8)
        for text, obj, slot in (
                ("导入 Excel / CSV", "Primary", self._import_table),
                ("粘贴", "Secondary", self._paste_clipboard),
                ("载入示例", "Secondary", self._load_sample),
                ("清空", "Danger", self._clear_data)):
            btn = QPushButton(text)
            btn.setObjectName(obj)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(slot)
            tools_lay.addWidget(btn)
        tools_lay.addStretch()
        card.addWidget(tools)

    def _build_style_card(self, lay):
        card = self._card(lay, "绘图样式")
        self.combo_type = self._combo([d for d, _ in pc.PLOT_TYPES],
                                      pc.PLOT_REV["Line_Dot"])
        self.combo_type.setFixedWidth(170)
        self._row(card, "图像类型", self.combo_type)

        self.sw_text = Switch(True)
        self.sw_text.toggled.connect(self._schedule_render)
        self._row(card, "显示能量数值", self.sw_text)

        self.seg_align = SegmentedControl([d for d, _ in pc.ALIGN], 1)
        self.seg_align.currentChanged.connect(lambda *_: self._schedule_render())
        self._row(card, "数值对齐", self.seg_align)

        self.sw_adjust = Switch(False)
        self.sw_adjust.toggled.connect(self._schedule_render)
        self._row(card, "自动避让文字", self.sw_adjust)

        self.sw_legend = Switch(True)
        self.sw_legend.toggled.connect(self._schedule_render)
        self._row(card, "显示图例", self.sw_legend)

        self.combo_legend = self._combo([d for d, _ in pc.LEGEND], "左上")
        self.combo_legend.setFixedWidth(150)
        self._row(card, "图例位置", self.combo_legend)

        self.sw_grid = Switch(True)
        self.sw_grid.toggled.connect(self._schedule_render)
        self._row(card, "显示网格", self.sw_grid)

        self.seg_theme = SegmentedControl(["简约", "经典"], 1)
        self.seg_theme.currentChanged.connect(lambda *_: self._schedule_render())
        self._row(card, "图表风格", self.seg_theme)

    def _build_size_card(self, lay):
        card = self._card(lay, "尺寸与字号")
        box, self.sl_datafont = self._slider(6, 30, 13)
        self._row(card, "数值字号", box, fill=True)
        box, self.sl_axisfont = self._slider(6, 30, 14)
        self._row(card, "坐标轴字号", box, fill=True)
        box, self.sl_linewidth = self._slider(1, 10, 3)
        self._row(card, "曲线宽度", box, fill=True)
        box, self.sl_rotation = self._slider(-90, 90, 0, suffix="°")
        self._row(card, "X 标签旋转", box, fill=True)
        self.combo_rot = self._combo([d for d, _ in pc.ROT_CENTER], "居中")
        self.combo_rot.setFixedWidth(150)
        self._row(card, "旋转对齐", self.combo_rot)

        size = QWidget()
        size_lay = QHBoxLayout(size)
        size_lay.setContentsMargins(0, 0, 0, 0)
        size_lay.setSpacing(6)
        self.inp_figw = self._line("12")
        self.inp_figw.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.inp_figw.setFixedWidth(64)
        self.inp_figh = self._line("7")
        self.inp_figh.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.inp_figh.setFixedWidth(64)
        size_lay.addWidget(self.inp_figw)
        size_lay.addWidget(QLabel("×"))
        size_lay.addWidget(self.inp_figh)
        size_lay.addWidget(QLabel("英寸"))
        size_lay.addStretch()
        self._row(card, "导出尺寸", size)

    def _build_export_card(self, lay):
        card = self._card(lay, "导出与方案")
        self.inp_savepath = self._line("EnergyProfile.png")
        card.addWidget(self._small_label("图片文件名"))
        card.addWidget(self.inp_savepath)
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        specs = [("保存图片", "Primary", self.save_image),
                 ("导出 CSV", "Secondary", self.export_csv),
                 ("导出 Excel", "Secondary", self.export_excel),
                 ("保存方案", "Secondary", self.save_preset),
                 ("载入方案", "Secondary", self.load_preset)]
        for index, (text, obj, slot) in enumerate(specs):
            btn = QPushButton(text)
            btn.setObjectName(obj)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(38)
            btn.clicked.connect(slot)
            grid.addWidget(btn, index // 3, index % 3)
        card.addLayout(grid)

    # ------------------------------------------------------------------ 主区域
    def _build_main(self):
        panel = QWidget()
        panel.setObjectName("Root")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(6, 16, 20, 16)
        lay.setSpacing(12)

        header = QWidget()
        header_lay = QHBoxLayout(header)
        header_lay.setContentsMargins(6, 0, 0, 0)
        header_lay.setSpacing(10)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        title = QLabel("图像预览")
        title.setObjectName("H1")
        hint = QLabel("滚轮缩放 · 拖动平移 · 双击复位")
        hint.setObjectName("H2")
        titles.addWidget(title)
        titles.addWidget(hint)
        header_lay.addLayout(titles)
        header_lay.addStretch()
        save_btn = QPushButton("保存图片")
        save_btn.setObjectName("Primary")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self.save_image)
        reset_btn = QPushButton("重置视图")
        reset_btn.setObjectName("Secondary")
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.clicked.connect(self.reset_view)
        header_lay.addWidget(reset_btn)
        header_lay.addWidget(save_btn)
        lay.addWidget(header)

        plot_card = QFrame()
        plot_card.setObjectName("PlotCard")
        plot_lay = QVBoxLayout(plot_card)
        plot_lay.setContentsMargins(10, 10, 10, 10)
        self.fig = Figure(figsize=(10, 6), dpi=100, facecolor="white")
        self.canvas = PlotCanvas(self.fig)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding,
                                  QSizePolicy.Policy.Expanding)
        plot_lay.addWidget(self.canvas)
        lay.addWidget(plot_card, 1)

        lay.addWidget(self._build_axis_card())
        return panel

    def _build_axis_card(self):
        card = QFrame()
        card.setObjectName("Card")
        add_shadow(card, blur=22, dy=4, alpha=20)
        outer = QVBoxLayout(card)
        outer.setContentsMargins(18, 14, 18, 14)
        outer.setSpacing(8)

        title = QLabel("坐标轴设置")
        title.setObjectName("CardTitle")
        outer.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        def mini(placeholder=""):
            edit = QLineEdit()
            edit.setPlaceholderText(placeholder)
            edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            edit.setFixedWidth(72)
            edit.textChanged.connect(self._schedule_render)
            return edit

        self.ax_xmin = mini("自动")
        self.ax_xmax = mini("自动")
        self.ax_xtick = mini("自动")
        self.ax_ymin = mini()
        self.ax_ymax = mini()
        self.ax_ytick = mini("自动")

        grid.addWidget(self._small_label("横轴范围"), 0, 0)
        grid.addWidget(self.ax_xmin, 0, 1)
        grid.addWidget(QLabel("~"), 0, 2, Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self.ax_xmax, 0, 3)
        grid.addWidget(self._small_label("横轴刻度间隔"), 0, 4)
        grid.addWidget(self.ax_xtick, 0, 5)
        grid.addWidget(self._small_label("留空自动"), 0, 6)

        grid.addWidget(self._small_label("纵轴范围"), 1, 0)
        grid.addWidget(self.ax_ymin, 1, 1)
        grid.addWidget(QLabel("~"), 1, 2, Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self.ax_ymax, 1, 3)
        grid.addWidget(self._small_label("纵轴刻度间隔"), 1, 4)
        grid.addWidget(self.ax_ytick, 1, 5)
        auto_box = QWidget()
        auto_lay = QHBoxLayout(auto_box)
        auto_lay.setContentsMargins(0, 0, 0, 0)
        auto_lay.setSpacing(8)
        auto_lay.addWidget(self._small_label("自动 Y"))
        self.sw_autoy = Switch(True)
        self.sw_autoy.toggled.connect(self._on_autoy_toggled)
        auto_lay.addWidget(self.sw_autoy)
        grid.addWidget(auto_box, 1, 6)
        grid.setColumnStretch(7, 1)
        outer.addLayout(grid)

        self.ax_ymin.setEnabled(False)
        self.ax_ymax.setEnabled(False)
        return card

    # ------------------------------------------------------------------ 事件
    def _on_autoy_toggled(self, checked):
        self.ax_ymin.setEnabled(not checked)
        self.ax_ymax.setEnabled(not checked)
        self._schedule_render()

    def _on_points_changed(self, value):
        self.table.set_counts(points=value)
        self._schedule_render()

    def _on_paths_changed(self, value):
        self.table.set_counts(paths=value)
        self._schedule_render()

    def _sync_steppers(self, *_):
        """粘贴 / 导入后保持台阶数、路径数与表格一致"""
        self.point_stepper.setValue(len(self.table.labels))
        self.path_stepper.setValue(len(self.table.paths))

    def _schedule_render(self, *_):
        self._render_timer.start()

    def _import_table(self):
        if self.table.import_file(self):
            self.point_stepper.setValue(len(self.table.labels))
            self.path_stepper.setValue(len(self.table.paths))
            self.render()

    def _paste_clipboard(self):
        if self.table.paste_clipboard():
            self.point_stepper.setValue(len(self.table.labels))
            self.path_stepper.setValue(len(self.table.paths))
            self.render()

    def _load_sample(self):
        self.table.set_data(pc.SAMPLE_LABELS, pc.SAMPLE_PATHS)
        self.point_stepper.setValue(len(pc.SAMPLE_LABELS))
        self.path_stepper.setValue(len(pc.SAMPLE_PATHS))
        self.render()

    def _clear_data(self):
        self.table.set_data(["1", "TS", "2"],
                            [{"name": "路径 A", "color": pc.PALETTE[0],
                              "style": "-", "values": ["", "", ""]}])
        self.point_stepper.setValue(3)
        self.path_stepper.setValue(1)
        self.render()

    def reset_view(self):
        self.canvas.reset_view()

    # ------------------------------------------------------------------ 配置
    def collect_config(self):
        labels, paths = self.table.get_data()

        def fnum(edit, default):
            try:
                return float(edit.text().strip())
            except Exception:
                return default

        def fopt(edit):
            s = edit.text().strip()
            if s == "" or s.lower() in ("auto", "自动"):
                return None
            try:
                return float(s)
            except Exception:
                return None

        return {
            "title": self.inp_title.text().strip(),
            "xlabel": self.inp_xlabel.text().strip(),
            "ylabel": self.inp_ylabel.text().strip(),
            "labels": labels,
            "paths": paths,
            "plottype": pc.PLOT_MAP.get(self.combo_type.currentText(), "Line_Curve"),
            "showtext": self.sw_text.isChecked(),
            "textalign": pc.ALIGN_MAP.get(self.seg_align.currentText(), "center"),
            "adjust": self.sw_adjust.isChecked(),
            "legend": self.sw_legend.isChecked(),
            "legendpos": pc.LEGEND_MAP.get(self.combo_legend.currentText(), "upper left"),
            "grid": self.sw_grid.isChecked(),
            "modern": self.seg_theme.currentText() == "简约",
            "autoy": self.sw_autoy.isChecked(),
            "ymin": fnum(self.ax_ymin, -2.0),
            "ymax": fnum(self.ax_ymax, 2.0),
            "xmin": fopt(self.ax_xmin),
            "xmax": fopt(self.ax_xmax),
            "xtick": fopt(self.ax_xtick),
            "ytick": fopt(self.ax_ytick),
            "datafont": self.sl_datafont.value(),
            "axisfont": self.sl_axisfont.value(),
            "linewidth": float(self.sl_linewidth.value()),
            "rotation": float(self.sl_rotation.value()),
            "rotcenter": pc.ROT_MAP.get(self.combo_rot.currentText(), "center"),
            "figw": max(4.0, fnum(self.inp_figw, 12.0)),
            "figh": max(3.0, fnum(self.inp_figh, 7.0)),
        }

    # ------------------------------------------------------------------ 渲染
    def render(self, silent=False):
        try:
            cfg = self.collect_config()
        except ValueError as exc:
            if not silent:
                QMessageBox.warning(self, "数据有误", str(exc))
            return
        try:
            ax = pc.render_profile(self.fig, cfg)
            self.canvas.draw()
            self.canvas.home = (ax.get_xlim(), ax.get_ylim())
        except Exception:
            if not silent:
                QMessageBox.critical(self, "绘图失败", traceback.format_exc())

    # ------------------------------------------------------------------ 操作
    def reset_params(self):
        answer = QMessageBox.question(self, "重置参数",
                                      "确定恢复所有参数为默认值吗？（数据表不会被清空）")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.inp_title.setText("Relative Energy Profile along the reaction path")
        self.inp_xlabel.setText("Reaction coordinate")
        self.inp_ylabel.setText("Relative Energy \u0394G (eV)")
        self.combo_type.setCurrentText(pc.PLOT_REV["Line_Dot"])
        self.sw_text.setChecked(True)
        self.seg_align.setCurrentIndex(1)
        self.sw_adjust.setChecked(False)
        self.sw_legend.setChecked(True)
        self.combo_legend.setCurrentText("左上")
        self.sw_grid.setChecked(True)
        self.seg_theme.setCurrentIndex(1)
        self.sl_datafont.setValue(13)
        self.sl_axisfont.setValue(14)
        self.sl_linewidth.setValue(3)
        self.sl_rotation.setValue(0)
        self.combo_rot.setCurrentText("居中")
        self.ax_xmin.clear()
        self.ax_xmax.clear()
        self.ax_xtick.clear()
        self.ax_ymin.setText("-2")
        self.ax_ymax.setText("2")
        self.ax_ytick.clear()
        self.sw_autoy.setChecked(True)
        self.inp_figw.setText("12")
        self.inp_figh.setText("7")
        self.inp_savepath.setText("EnergyProfile.png")
        self.render()

    def save_image(self):
        path = self.inp_savepath.text().strip() or "EnergyProfile.png"
        path, _ = QFileDialog.getSaveFileName(
            self, "保存图片", path,
            "PNG 图片 (*.png);;JPEG 图片 (*.jpg *.jpeg);;PDF 文档 (*.pdf);;"
            "SVG 矢量图 (*.svg);;所有文件 (*)")
        if not path:
            return
        try:
            old = tuple(self.fig.get_size_inches())
            cfg = self.collect_config()
            self.fig.set_size_inches(float(cfg["figw"]), float(cfg["figh"]))
            self.fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
            self.fig.set_size_inches(*old)
            self.canvas.draw_idle()
            self.inp_savepath.setText(path)
            QMessageBox.information(self, "保存成功", "图片已保存至：\n%s" % path)
        except Exception as exc:
            QMessageBox.critical(self, "保存失败", str(exc))

    def _export_rows(self, labels, paths):
        """导出布局，与导入解析格式一致，可往返"""
        rows = [["节点 / 路径"] + [p["name"] for p in paths],
                ["颜色"] + [p["color"] for p in paths],
                ["线型"] + [p["style"] for p in paths]]
        for j, label in enumerate(labels):
            rows.append([label] + [
                "" if p["values"][j] == "" else p["values"][j]
                for p in paths])
        return rows

    def export_csv(self):
        try:
            labels, paths = self.table.get_data()
        except ValueError as exc:
            QMessageBox.warning(self, "数据有误", str(exc))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 CSV", "EnergyProfile.csv",
            "CSV 文件 (*.csv);;所有文件 (*)")
        if not path:
            return
        try:
            import csv
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                csv.writer(handle).writerows(self._export_rows(labels, paths))
            QMessageBox.information(self, "导出成功", "数据已导出至：\n%s" % path)
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))

    def export_excel(self):
        try:
            labels, paths = self.table.get_data()
        except ValueError as exc:
            QMessageBox.warning(self, "数据有误", str(exc))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 Excel", "EnergyProfile.xlsx",
            "Excel 工作簿 (*.xlsx);;所有文件 (*)")
        if not path:
            return
        try:
            pc.write_xlsx(path, self._export_rows(labels, paths),
                          sheet_name="EnergyProfile", header_rows=3)
            QMessageBox.information(self, "导出成功", "数据已导出至：\n%s" % path)
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))

    def save_preset(self):
        try:
            cfg = self.collect_config()
        except Exception as exc:
            QMessageBox.warning(self, "无法保存", str(exc))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存方案", "energy_profile.json",
            "方案文件 (*.json);;所有文件 (*)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(cfg, handle, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "保存成功", "方案已保存至：\n%s" % path)
        except Exception as exc:
            QMessageBox.critical(self, "保存失败", str(exc))

    def load_preset(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "载入方案", "", "方案文件 (*.json);;所有文件 (*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                cfg = json.load(handle)
        except Exception as exc:
            QMessageBox.critical(self, "载入失败", str(exc))
            return

        self.inp_title.setText(cfg.get("title", ""))
        self.inp_xlabel.setText(cfg.get("xlabel", ""))
        self.inp_ylabel.setText(cfg.get("ylabel", ""))
        self.combo_type.setCurrentText(pc.PLOT_REV.get(cfg.get("plottype"),
                                                       pc.PLOT_REV["Line_Curve"]))
        self.sw_text.setChecked(bool(cfg.get("showtext", True)))
        self.seg_align.setCurrentText(pc.ALIGN_REV.get(cfg.get("textalign"), "居中"))
        self.sw_adjust.setChecked(bool(cfg.get("adjust", False)))
        self.sw_legend.setChecked(bool(cfg.get("legend", True)))
        self.combo_legend.setCurrentText(pc.LEGEND_REV.get(cfg.get("legendpos"), "左上"))
        self.sw_grid.setChecked(bool(cfg.get("grid", True)))
        self.seg_theme.setCurrentIndex(0 if cfg.get("modern", True) else 1)
        self.sw_autoy.setChecked(bool(cfg.get("autoy", True)))

        def put(edit, value):
            edit.setText("" if value is None else str(value))

        put(self.ax_xmin, cfg.get("xmin"))
        put(self.ax_xmax, cfg.get("xmax"))
        put(self.ax_xtick, cfg.get("xtick"))
        put(self.ax_ymin, cfg.get("ymin", -2))
        put(self.ax_ymax, cfg.get("ymax", 2))
        put(self.ax_ytick, cfg.get("ytick"))

        self.sl_datafont.setValue(int(cfg.get("datafont", 13)))
        self.sl_axisfont.setValue(int(cfg.get("axisfont", 14)))
        self.sl_linewidth.setValue(int(cfg.get("linewidth", 3)))
        self.sl_rotation.setValue(int(cfg.get("rotation", 0)))
        self.combo_rot.setCurrentText(pc.ROT_REV.get(cfg.get("rotcenter"), "居中"))
        self.inp_figw.setText(str(cfg.get("figw", 12)))
        self.inp_figh.setText(str(cfg.get("figh", 7)))

        self.table.set_data(cfg.get("labels", ["1", "TS", "2"]), cfg.get("paths", []))
        self.point_stepper.setValue(len(self.table.labels))
        self.path_stepper.setValue(len(self.table.paths))
        self.render()


# =====================================================================================
#  启动
# =====================================================================================
def _excepthook(exc_type, exc, tb):
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    base = (os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
            else os.path.dirname(os.path.abspath(__file__)))
    try:
        with open(os.path.join(base, "studio_error.log"), "w",
                  encoding="utf-8") as fh:
            fh.write(text)
    except Exception:
        pass
    try:
        app = QApplication.instance()
        if app is not None:
            QMessageBox.critical(None, "程序错误", text)
    except Exception:
        pass
    sys.__excepthook__(exc_type, exc, tb)


def main():
    sys.excepthook = _excepthook
    QApplication.setApplicationName("Energy Profile Studio")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)
    app.setWindowIcon(QIcon(app_logo_pixmap(256)))
    font = QFont("Microsoft YaHei UI", 10)
    app.setFont(font)
    window = StudioWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
