# -*- coding: utf-8 -*-
########################################################################################
# plot_core.py  —  能垒图绘制核心 (纯逻辑，无任何 GUI 依赖)                            #
#   供 PySide6 / 其他界面复用：数据插值、绘制、Excel/CSV 读取、配色与样式常量          #
########################################################################################

import os
import re
import csv

import numpy as np

from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator
from matplotlib import rcParams

# =====================================================================================
#  全局风格常量 (iOS 配色)
# =====================================================================================
BG        = "#F2F2F7"   # 系统分组背景
CARD      = "#FFFFFF"   # 卡片
CARD_SOFT = "#F7F7FA"   # 输入框填充
TRACK     = "#E9E9EB"   # 开关 / 分段控件轨道
BORDER    = "#E3E3E8"   # 分隔线
TEXT      = "#1C1C1E"   # 主文字
SUB       = "#8E8E93"   # 次要文字
BLUE      = "#007AFF"   # 强调色
BLUE_D    = "#0060DF"
GREEN     = "#34C759"
RED       = "#FF3B30"
ORANGE    = "#FF9500"

FONT = "Microsoft YaHei UI"   # 运行时自动探测替换

rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "PingFang SC",
                               "Segoe UI", "Arial", "DejaVu Sans"]
rcParams["axes.unicode_minus"] = False

# 绘图类型显示名 -> 内部标识
PLOT_TYPES = [
    ("横线 + 曲线", "Line_Curve"),
    ("平滑曲线", "Curve"),
    ("虚实折线", "Line_Dot"),
    ("MEP 平滑曲线", "MEP_Curve"),
    ("MEP 横线 + 曲线", "MEP_Line_Curve"),
    ("MEP 虚实折线", "MEP_Line_Dot"),
]
PLOT_MAP = {disp: key for disp, key in PLOT_TYPES}
PLOT_REV = {key: disp for disp, key in PLOT_TYPES}

STYLE_NAMES = ["实线", "虚线", "点线", "点划线"]
STYLE_MAP = {"实线": "-", "虚线": "--", "点线": ":", "点划线": "-."}
STYLE_REV = {v: k for k, v in STYLE_MAP.items()}

LEGEND = [("左上", "upper left"), ("右上", "upper right"),
          ("左下", "lower left"), ("右下", "lower right"), ("最佳", "best")]
LEGEND_MAP = {d: k for d, k in LEGEND}
LEGEND_REV = {k: d for d, k in LEGEND}

ROT_CENTER = [("居中", "center"), ("左", "left"), ("右", "right")]
ROT_MAP = {d: k for d, k in ROT_CENTER}
ROT_REV = {k: d for d, k in ROT_CENTER}

# 台阶上能量数值的对齐方式
ALIGN = [("居左", "left"), ("居中", "center"), ("居右", "right")]
ALIGN_MAP = {d: k for d, k in ALIGN}
ALIGN_REV = {k: d for d, k in ALIGN}

# 默认示例数据 (启动即可看到效果)
SAMPLE_LABELS = ["1", "TS1", "2", "TS2", "3"]
SAMPLE_PATHS = [
    {"name": "路径 A", "color": "#FF3B30", "style": "-",
     "values": [0.00, 1.25, -0.45, 0.85, -1.10]},
    {"name": "路径 B", "color": "#007AFF", "style": "-",
     "values": [0.00, 1.95, -0.20, 1.40, -0.90]},
    {"name": "路径 C", "color": "#34C759", "style": "-",
     "values": [0.00, 0.95, -0.60, 1.10, -1.35]},
]

# =====================================================================================
#  一、绘图核心 (移植并修正自原始脚本，去除全局变量与 Excel 依赖)
# =====================================================================================
def curve_points(y_small, y_large, direction):
    """产生余弦曲线插点"""
    if direction == "up":
        x_up = np.linspace(np.pi, 2 * np.pi, 50)
        y_curve = [y_small + (y_large - y_small) * (j + 1) / 2
                   for j in np.cos(x_up).tolist()]
    else:
        x_down = np.linspace(0, np.pi, 50)
        y_curve = [y_small + (y_large - y_small) * (j + 1) / 2
                   for j in np.cos(x_down).tolist()]
    return y_curve

def interpolate_cos(x, y):
    """在驻点上产生一系列余弦曲线插值点"""
    x_new, y_smooth = [], []
    for i in range(len(x) - 1):
        x_new += np.linspace(x[i], x[i + 1], 50).tolist()
        if y[i] < y[i + 1]:
            y_smooth += curve_points(y[i], y[i + 1], "up")
        elif y[i] > y[i + 1]:
            y_smooth += curve_points(y[i + 1], y[i], "down")
        else:
            y_smooth += np.linspace(y[i], y[i + 1], 50).tolist()
    return x_new, y_smooth

def y_extreme(y):
    """返回 y (可含空数据、可嵌套) 中的最大值与最小值"""
    flat = []
    for item in y:
        if isinstance(item, (list, tuple)):
            flat.extend(item)
        else:
            flat.append(item)
    vals = [v for v in flat if v != "" and v is not None]
    return (max(vals), min(vals)) if vals else (1.0, -1.0)

def y_list_min(y):
    """逐节点取各路径的最小值，得到最稳定自旋态能量曲线"""
    out = []
    for col in zip(*y):
        vals = [v for v in col if v != "" and v is not None]
        out.append(min(vals) if vals else "")
    return out

def _valid(x, y):
    xs, ys = [], []
    for xi, yi in zip(x, y):
        if yi != "" and yi is not None:
            xs.append(xi)
            ys.append(yi)
    return xs, ys

def _is_ts(name):
    """判断节点是否为过渡态 (含 TS / ts / 过渡态)"""
    return re.search(r"TS|ts|过渡态", str(name)) is not None

def draw_curve(ax, x, y, color, lstyle, lw, labels, show_text, fs,
               align="center"):
    """平滑余弦曲线样式"""
    for i in range(len(y)):
        xs, ys = _valid(x, y[i])
        if not xs:
            continue
        ax.scatter(xs, ys, s=42, color=color[i], zorder=4)
        xn, yn = interpolate_cos(xs, ys)
        if xn:
            ax.plot(xn, yn, lw=lw, label=labels[i], color=color[i],
                    linestyle=lstyle[i], zorder=3)
        if show_text:
            for xi, yi in zip(xs, ys):
                tx, ha = _anchor(xi, 0.0, align)
                ax.text(tx, yi, "{:.2f}".format(yi), fontsize=fs,
                        color=color[i], ha=ha, va="bottom")


def _anchor(x_center, half, align):
    """根据对齐方式返回能量数值文本的 (横坐标, ha)"""
    if align == "left":
        return x_center - half, "left"
    if align == "right":
        return x_center + half, "right"
    return x_center, "center"

def draw_line_split(ax, x, y, color, lw, show_text, fs, align="center"):
    """绘制单条分段实线(横线)，返回加倍后的坐标"""
    y_new, x_new = [], []
    for idx, yi in enumerate(y):
        if yi != "" and yi is not None:
            y_new += [yi, yi]
            x_new += [2 * idx + 1, 2 * idx + 2]
    i = 0
    while i < len(y_new):
        ax.plot([x_new[i], x_new[i + 1]], [y_new[i], y_new[i + 1]],
                linestyle="-", lw=lw, color=color, zorder=3)
        i += 2
    if show_text:
        for idx, yi in enumerate(y):
            if yi != "" and yi is not None:
                tx, ha = _anchor(2 * idx + 1.5, 0.5, align)
                ax.text(tx, yi, "{:.2f}".format(yi),
                        fontsize=fs, color=color, ha=ha, va="bottom")
    return x_new, y_new

def draw_line_dot(ax, x, y, color, lw, labels, show_text, fs, align="center"):
    """虚实折线样式 (实线横段 + 虚线连接)"""
    ymax, ymin = y_extreme(y)
    bias = (ymax - ymin) / 50 if ymax != ymin else 0.05
    for i in range(len(y)):
        xn, yn = draw_line_split(ax, x, y[i], color[i], lw, False, fs)
        ax.plot(xn, yn, linestyle="--", lw=max(0.8, lw - 1),
                color=color[i], label=labels[i], zorder=3)
        if show_text:
            for idx, yi in enumerate(y[i]):
                if yi != "" and yi is not None:
                    tx, ha = _anchor(2 * idx + 1.5, 0.5, align)
                    ax.text(tx, yi + bias, "{:.2f}".format(yi),
                            fontsize=fs, color=color[i], ha=ha)

def draw_line_curve(ax, y_ini, tick_labels, color, lw, label, show_text, fs,
                    align="center"):
    """横线 + 曲线样式 (中间体画横线，过渡态画曲线)"""
    x_ini = [i * 2 + 2 for i in range(len(y_ini))]
    x, y = [], []
    for i in range(len(y_ini)):
        if y_ini[i] == "" or y_ini[i] is None:
            continue
        if _is_ts(tick_labels[i]):
            y.append(y_ini[i])
            x.append(x_ini[i])
        else:
            y += [y_ini[i], y_ini[i]]
            x += [x_ini[i] - 0.5, x_ini[i] + 0.5]

    if len(x) >= 2:
        xn, yn = [], []
        for i in range(len(x) - 1):
            xn += np.linspace(x[i], x[i + 1], 50).tolist()
            if y[i] < y[i + 1]:
                yn += curve_points(y[i], y[i + 1], "up")
            elif y[i] > y[i + 1]:
                yn += curve_points(y[i + 1], y[i], "down")
            else:
                yn += np.linspace(y[i], y[i + 1], 50).tolist()
        ax.plot(xn, yn, lw=lw, color=color, label=label, zorder=3)

    if show_text:
        for i in range(len(y_ini)):
            if y_ini[i] != "" and y_ini[i] is not None:
                tx, ha = _anchor(x_ini[i], 0.5, align)
                ax.text(tx, y_ini[i], "{:.2f}".format(y_ini[i]),
                        fontsize=fs, color=color, ha=ha, va="bottom")
    return x_ini

def draw_scatter(ax, x_sticks, y, color, lw, labels, show_text, fs,
                 align="center"):
    """散点 + 长横线 (用于其他自旋态)"""
    for i in range(len(y)):
        xs, ys = [], []
        for j in range(len(y[i])):
            if y[i][j] != "" and y[i][j] is not None:
                xs.append(x_sticks[j])
                ys.append(y[i][j])
                if show_text:
                    tx, ha = _anchor(x_sticks[j], 0.5, align)
                    ax.text(tx, y[i][j], "{:.2f}".format(y[i][j]),
                            fontsize=fs, color=color[i], ha=ha, va="bottom")
        if xs:
            ax.scatter(xs, ys, color=color[i], label=labels[i], marker="_",
                       s=1200, linewidths=lw, zorder=4)

def relax_texts(ax, texts, iterations=40):
    """轻量级文字避让 (adjustText 缺失时的后备方案)，仅做纵向平移"""
    try:
        fig = ax.figure
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
    except Exception:
        return
    for _ in range(iterations):
        boxes = []
        for t in texts:
            try:
                boxes.append(t.get_window_extent(renderer=renderer))
            except Exception:
                boxes.append(None)
        moved = False
        for i in range(len(texts)):
            if boxes[i] is None:
                continue
            for j in range(i + 1, len(texts)):
                if boxes[j] is None or not boxes[i].overlaps(boxes[j]):
                    continue
                shift = (boxes[i].y1 - boxes[j].y0) + 2.0
                xd, yd = texts[j].get_position()
                p = ax.transData.transform((xd, yd))
                nd = ax.transData.inverted().transform((p[0], p[1] + shift))
                texts[j].set_position((nd[0], nd[1]))
                moved = True
        if not moved:
            break
        try:
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
        except Exception:
            break

def style_axes(ax, modern=True, grid=True, axisfs=13):
    """应用坐标轴风格"""
    if modern:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color("#C7C7CC")
            ax.spines[s].set_linewidth(1.0)
        ax.tick_params(colors="#8E8E93", length=3, width=1.0)
        if grid:
            ax.grid(True, axis="y", color="#E5E5EA", linestyle="-", linewidth=0.9)
            ax.set_axisbelow(True)
    else:
        for s in ax.spines.values():
            s.set_color("#333333")
        if grid:
            ax.grid(True, color="#DDDDDD", linestyle="--", linewidth=0.6)
            ax.set_axisbelow(True)
    ax.tick_params(labelsize=max(6, axisfs - 1))

def render_profile(fig, cfg):
    """根据配置 cfg 在 Figure 上重绘整张能垒图"""
    labels = cfg["labels"]
    paths = cfg["paths"]
    n = len(labels)

    fig.clear()
    ax = fig.add_subplot(111)
    ax.set_facecolor("white")

    style = cfg["plottype"]
    lw = float(cfg["linewidth"])
    fs = int(cfg["datafont"])
    axisfs = int(cfg["axisfont"])
    show = bool(cfg["showtext"])
    align = cfg.get("textalign", "center")

    x = [i + 1 for i in range(n)]
    ys = [p["values"] for p in paths]
    colors = [p["color"] for p in paths]
    lstyles = [p["style"] for p in paths]
    names = [p["name"] for p in paths]
    ymin_list = y_list_min(ys)

    xtick_pos = None

    if style == "Curve":
        draw_curve(ax, x, ys, colors, lstyles, lw, names, show, fs, align)
        xtick_pos = x
        ax.set_xlim(x[0] - 0.6, x[-1] + 0.6)
    elif style == "Line_Curve":
        x_sticks = x
        for i in range(len(paths)):
            x_sticks = draw_line_curve(ax, ys[i], labels, colors[i], lw,
                                       names[i], show, fs, align)
        xtick_pos = x_sticks
        ax.set_xlim(x_sticks[0] - 1.6, x_sticks[-1] + 1.6)
    elif style == "Line_Dot":
        draw_line_dot(ax, x, ys, colors, lw, names, show, fs, align)
        xtick_pos = [i * 2 - 0.5 for i in x]
        ax.set_xlim(x[0] * 2 - 1.6, x[-1] * 2 + 1.1)
    elif style == "MEP_Curve":
        xm = [i * 2 - 0.5 for i in x]
        xn, yn = interpolate_cos(xm, ymin_list)
        if xn:
            ax.plot(xn, yn, color="grey", lw=lw, zorder=3)
        draw_scatter(ax, xm, ys, colors, lw, names, show, fs, align)
        xtick_pos = xm
        ax.set_xlim(x[0] * 2 - 1.6, x[-1] * 2 + 1.6)
    elif style == "MEP_Line_Dot":
        draw_line_dot(ax, x, [ymin_list], ["grey"], lw, [None], False, fs)
        for i in range(len(paths)):
            draw_line_split(ax, x, ys[i], colors[i], lw, False, fs)
        draw_scatter(ax, [i * 2 - 0.5 for i in x], ys, colors, lw, names, show, fs, align)
        xtick_pos = [i * 2 - 0.5 for i in x]
        ax.set_xlim(x[0] * 2 - 1.6, x[-1] * 2 + 1.6)
    else:  # MEP_Line_Curve
        x_sticks = draw_line_curve(ax, ymin_list, labels, "grey", lw,
                                   None, False, fs)
        draw_scatter(ax, x_sticks, ys, colors, lw, names, show, fs, align)
        xtick_pos = x_sticks
        ax.set_xlim(x_sticks[0] - 1.6, x_sticks[-1] + 1.6)

    # ---- x 轴刻度 ----
    xstep = cfg.get("xtick")
    if xstep:
        ax.xaxis.set_major_locator(MultipleLocator(float(xstep)))
        ax.tick_params(axis="x", labelrotation=float(cfg["rotation"]))
    elif xtick_pos:
        ax.set_xticks(xtick_pos)
        ax.set_xticklabels(labels, rotation=float(cfg["rotation"]),
                           ha=cfg["rotcenter"])

    # ---- y 轴范围 ----
    if cfg["autoy"]:
        ymax, ymin = y_extreme(ys)
        pad = (ymax - ymin) * 0.18 if ymax != ymin else 1.0
        ax.set_ylim(ymin - pad, ymax + pad)
    else:
        ax.set_ylim(float(cfg["ymin"]), float(cfg["ymax"]))

    # ---- 手动横轴范围 (留空表示自动) ----
    xlo, xhi = cfg.get("xmin"), cfg.get("xmax")
    if xlo is not None or xhi is not None:
        cur_lo, cur_hi = ax.get_xlim()
        ax.set_xlim(xlo if xlo is not None else cur_lo,
                    xhi if xhi is not None else cur_hi)

    # ---- 纵轴刻度间隔 (留空表示自动) ----
    ystep = cfg.get("ytick")
    if ystep:
        ax.yaxis.set_major_locator(MultipleLocator(float(ystep)))

    # ---- 标题 / 轴标题 ----
    if cfg["title"]:
        ax.set_title(cfg["title"], fontsize=axisfs + 2, color=TEXT, pad=12)
    ax.set_xlabel(cfg["xlabel"], fontsize=axisfs, color=TEXT)
    ax.set_ylabel(cfg["ylabel"], fontsize=axisfs, color=TEXT)

    # ---- 图例 ----
    if cfg["legend"]:
        handles, labs = ax.get_legend_handles_labels()
        pairs = [(h, l) for h, l in zip(handles, labs) if l not in (None, "None", "")]
        if pairs:
            ax.legend([h for h, _ in pairs], [l for _, l in pairs],
                      fontsize=max(7, axisfs - 2), loc=cfg["legendpos"],
                      frameon=not cfg["modern"],
                      framealpha=0.95, borderpad=0.6)

    # ---- 风格 ----
    style_axes(ax, modern=cfg["modern"], grid=cfg["grid"], axisfs=axisfs)

    # ---- 文字避让 ----
    if cfg["adjust"] and ax.texts:
        try:
            from adjustText import adjust_text
            adjust_text(list(ax.texts), ax=ax, only_move={"text": "y"})
        except Exception:
            relax_texts(ax, list(ax.texts))

    try:
        fig.tight_layout()
    except Exception:
        pass

    return ax



# ---------------------------------------------------------------------------
#  数据导入: Excel / CSV
# ---------------------------------------------------------------------------
def _col_index(ref):
    """Excel 单元格引用 -> 列索引 (A->0, B->1 ...)"""
    m = re.match(r"([A-Za-z]+)", str(ref))
    if not m:
        return 0
    n = 0
    for ch in m.group(1).upper():
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def read_xlsx(path):
    """纯标准库读取 .xlsx (无需 openpyxl)，返回二维字符串列表"""
    import zipfile
    from xml.etree import ElementTree as ET
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    with zipfile.ZipFile(path) as z:
        sheets = [n for n in z.namelist()
                  if re.match(r"xl/worksheets/sheet\d+\.xml$", n)]
        sheets.sort(key=lambda s: int(re.search(r"(\d+)", s).group(1)))
        if not sheets:
            raise ValueError("Excel 文件中未找到工作表。")
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall(ns + "si"):
                shared.append("".join(t.text or "" for t in si.iter(ns + "t")))
        root = ET.fromstring(z.read(sheets[0]))
        rows = []
        for row in root.iter(ns + "row"):
            cells = {}
            maxc = -1
            for c in row.findall(ns + "c"):
                ci = _col_index(c.get("r"))
                t = c.get("t")
                v = c.find(ns + "v")
                isv = c.find(ns + "is")
                if t == "s" and v is not None:
                    try:
                        val = shared[int(v.text)]
                    except Exception:
                        val = ""
                elif t == "inlineStr" and isv is not None:
                    val = "".join(x.text or "" for x in isv.iter(ns + "t"))
                elif v is not None:
                    val = v.text
                else:
                    val = ""
                cells[ci] = "" if val is None else str(val)
                maxc = max(maxc, ci)
            rows.append([cells.get(i, "") for i in range(maxc + 1)])
    return rows


def read_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except Exception:
            dialect = csv.excel
        return [list(r) for r in csv.reader(f, dialect)]


def read_table(path):
    """按扩展名读取 .xlsx / .xlsm / .csv，返回二维字符串列表"""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".csv", ".txt", ".tsv"):
        return read_csv(path)
    if ext in (".xlsx", ".xlsm"):
        try:
            return read_xlsx(path)
        except Exception as first:
            try:
                import openpyxl
                wb = openpyxl.load_workbook(path, data_only=True)
                ws = wb.worksheets[0]
                return [["" if c is None else str(c) for c in row]
                        for row in ws.iter_rows(values_only=True)]
            except Exception:
                raise ValueError(f"无法读取 Excel 文件：{first}")
    raise ValueError("仅支持 .xlsx / .xlsm / .csv；.xls 请先另存为 .xlsx")


def normalize_color(value, fallback="#007AFF"):
    """把颜色名 (r/b/red...) 或色值统一转换为 #RRGGBB"""
    s = str(value).strip()
    if not s:
        return fallback
    try:
        from matplotlib.colors import to_hex
        try:
            return to_hex(s).upper()
        except Exception:
            return to_hex("#" + s).upper()
    except Exception:
        return fallback


PALETTE = ["#FF3B30", "#007AFF", "#34C759", "#FF9500",
           "#AF52DE", "#5AC8FA", "#FFCC00", "#FF2D55",
           "#5856D6", "#FF6482", "#30B0C7", "#A2845E"]


# ---------------------------------------------------------------------------
#  数据导出: .xlsx (纯标准库，无需 openpyxl / pandas)
# ---------------------------------------------------------------------------
def _col_name(index):
    """列索引 -> Excel 列名 (0->A, 1->B ...)"""
    name = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        name = chr(65 + rem) + name
    return name


def _xml_escape(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _as_number(value):
    """仅把真正的数值类型写为数字单元格，字符串保持文本"""
    if isinstance(value, bool):
        return None
    if isinstance(value, float):
        return value
    if isinstance(value, int):
        return float(value)
    return None


def write_xlsx(path, rows, sheet_name="Sheet1", header_rows=0):
    """把二维表写出为 .xlsx。header_rows: 前若干行加粗。"""
    import zipfile

    rows = [list(r) for r in rows]
    n_cols = max((len(r) for r in rows), default=0)

    widths = []
    for c in range(n_cols):
        longest = 8
        for r in rows:
            if c < len(r):
                longest = max(longest, len(str(r[c])))
        widths.append(min(34, longest + 2))
    cols_xml = "".join(
        '<col min="%d" max="%d" width="%d" customWidth="1"/>'
        % (i + 1, i + 1, w) for i, w in enumerate(widths))

    sheet = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
             '<worksheet xmlns="http://schemas.openxmlformats.org/'
             'spreadsheetml/2006/main">']
    if cols_xml:
        sheet.append("<cols>%s</cols>" % cols_xml)
    sheet.append("<sheetData>")
    for ri, row in enumerate(rows, start=1):
        style = 1 if ri <= header_rows else 0
        cells = []
        for ci, value in enumerate(row):
            ref = "%s%d" % (_col_name(ci), ri)
            number = _as_number(value)
            if number is not None:
                cells.append('<c r="%s" s="%d"><v>%s</v></c>'
                             % (ref, style, repr(number)))
            elif str(value).strip() == "":
                cells.append('<c r="%s" s="%d"/>' % (ref, style))
            else:
                cells.append(
                    '<c r="%s" s="%d" t="inlineStr"><is>'
                    '<t xml:space="preserve">%s</t></is></c>'
                    % (ref, style, _xml_escape(value)))
        sheet.append('<row r="%d">%s</row>' % (ri, "".join(cells)))
    sheet.append("</sheetData></worksheet>")
    sheet_xml = "".join(sheet)

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '</Types>')

    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>')

    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="%s" sheetId="1" r:id="rId1"/></sheets></workbook>'
        % _xml_escape(sheet_name[:31] or "Sheet1"))

    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        '</Relationships>')

    styles = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
        '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="2"><fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill></fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        '</styleSheet>')

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        z.writestr("xl/styles.xml", styles)
        z.writestr("xl/worksheets/sheet1.xml", sheet_xml)
