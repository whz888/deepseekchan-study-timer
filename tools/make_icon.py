# -*- coding: utf-8 -*-
"""从原版表情图裁出鲸鱼娘的头像，生成桌面快捷方式用的 .ico。
用法: python tools/make_icon.py
输出: 上一级目录/学习计时器.ico  （以及一张 preview 便于检查）
"""
import os
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit('需要 Pillow')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRCIMG = os.path.join(ROOT, 'tools', 'assets', 'expressions.png')
OUT = os.path.join(os.path.dirname(ROOT), '学习计时器.ico')
PREVIEW = os.path.join(ROOT, 'tools', 'icon-preview.png')

GRID = 4
TILE = 7          # 闭眼笑的那一格，最可爱
HEAD = (148, 52, 368, 272)   # 头像裁切框（正方形：头饰顶到下巴）
SCALE = 0.86      # 头像占图标边长比例
OFFY = 0.06       # 垂直位置（相对图标高度的偏移比例）


def main():
    sheet = Image.open(SRCIMG).convert('RGBA')
    cw = sheet.width // GRID
    r, c = divmod(TILE, GRID)
    tile = sheet.crop((c * cw, r * cw, (c + 1) * cw, (r + 1) * cw))
    head = tile.crop(HEAD)

    size = 256
    canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))

    # 圆角方块 + 从上到下的蓝色渐变
    grad = Image.new('RGBA', (size, size))
    d = ImageDraw.Draw(grad)
    top, bot = (86, 140, 255), (27, 60, 168)
    for y in range(size):
        t = y / (size - 1)
        d.line([(0, y), (size, y)], fill=(
            int(top[0] + (bot[0] - top[0]) * t),
            int(top[1] + (bot[1] - top[1]) * t),
            int(top[2] + (bot[2] - top[2]) * t), 255))
    mask = Image.new('L', (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=52, fill=255)
    canvas.paste(grad, (0, 0), mask)

    # 头像贴在中间
    inner = int(size * SCALE)
    h = head.resize((inner, inner), Image.LANCZOS)
    canvas.alpha_composite(h, ((size - inner) // 2, int(size * OFFY)))

    canvas.save(OUT, sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    canvas.resize((128, 128), Image.LANCZOS).save(PREVIEW)
    print('已生成:', OUT)
    print('预览:', PREVIEW)


if __name__ == '__main__':
    main()
