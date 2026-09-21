# -*- coding: utf-8 -*-
"""生成应用图标 app.ico / app.png

设计：iOS 风格圆角方块 + 蓝色渐变底 + 白色能垒曲线（反应路径势能剖面）
用法： python make_icon.py
"""
from PIL import Image, ImageDraw, ImageFilter

SIZE = 1024          # 输出基准尺寸
SS = 2               # 超采样倍数（先大后缩，边缘更平滑）
TOP = (77, 163, 255)     # #4DA3FF
BOTTOM = (0, 82, 204)    # #0052CC

# 归一化坐标 (0~1)，y 向下：平 - 峰 - 谷 - 峰 - 平
PROFILE = [(0.155, 0.620), (0.290, 0.620), (0.410, 0.300),
           (0.530, 0.700), (0.660, 0.330), (0.790, 0.600),
           (0.880, 0.600)]


def _gradient(size):
    grad = Image.new("RGB", (1, size))
    for y in range(size):
        t = y / max(1, size - 1)
        grad.putpixel((0, y), tuple(
            int(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3)))
    return grad.resize((size, size))


def draw_icon(size=SIZE, ss=SS):
    w = size * ss
    # 圆角方块 + 渐变
    mask = Image.new("L", (w, w), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, w - 1, w - 1], radius=int(0.225 * w), fill=255)
    img = Image.new("RGBA", (w, w), (0, 0, 0, 0))
    img.paste(_gradient(w), (0, 0), mask)

    # 曲线路径点
    pts = [(x * w, y * w) for x, y in PROFILE]
    lw = int(0.066 * w)
    dot = int(0.030 * w)

    # 阴影层
    shadow = Image.new("RGBA", (w, w), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    off = int(0.016 * w)
    sd.line([(x, y + off) for x, y in pts], fill=(0, 30, 80, 110),
            width=lw, joint="curve")
    for x, y in pts:
        sd.ellipse([x - dot, y + off - dot, x + dot, y + off + dot],
                   fill=(0, 30, 80, 110))
    shadow = shadow.filter(ImageFilter.GaussianBlur(0.018 * w))
    img = Image.alpha_composite(img, shadow)

    # 白色曲线
    line = Image.new("RGBA", (w, w), (0, 0, 0, 0))
    ld = ImageDraw.Draw(line)
    ld.line(pts, fill=(255, 255, 255, 255), width=lw, joint="curve")
    for x, y in pts:
        ld.ellipse([x - dot, y - dot, x + dot, y + dot],
                   fill=(255, 255, 255, 255))
    # 端点圆头
    for x, y in (pts[0], pts[-1]):
        ld.ellipse([x - lw / 2, y - lw / 2, x + lw / 2, y + lw / 2],
                   fill=(255, 255, 255, 255))
    img = Image.alpha_composite(img, line)

    return img.resize((size, size), Image.LANCZOS)


def main():
    icon = draw_icon(SIZE)
    icon.save("app.png")
    icon.save("app.ico", format="ICO",
              sizes=[(256, 256), (128, 128), (64, 64), (48, 48),
                     (32, 32), (16, 16)])
    print("saved app.png, app.ico")


if __name__ == "__main__":
    main()
