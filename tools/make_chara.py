# -*- coding: utf-8 -*-
"""从原版角色表情图里裁出计时器用得到的表情，导出为 webp，并生成 src/chara.css。

素材来源（大肥鱼项目署名许可 1.0，允许使用/修改/分享/商用，须署名）：
    作者：YunYueSama
    仓库：https://github.com/YunYueSama/codex-deepseek-pet
    文件：assets/whale/expressions.png

本脚本只做技术处理（裁切、转格式、内联），不修改角色造型。
用法: python tools/make_chara.py
"""
import base64
import os
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit('需要 Pillow')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src')
OUTDIR = os.path.join(SRC, 'chara')
SRCIMG = os.path.join(ROOT, 'tools', 'assets', 'expressions.png')
URL = 'https://raw.githubusercontent.com/YunYueSama/codex-deepseek-pet/main/assets/whale/expressions.png'

# 表情图是 4x4 的图集，每格 512x512
GRID = 4
# 统一裁切框（保证各表情画布一致，切换时不跳动）
BOX = (55, 40, 455, 500)

# 计时器只用到 5 个表情
TILES = [
    ('normal', 2),   # 平静（待机）
    ('happy',  7),   # 闭眼笑（计时中）
    ('cheer',  9),   # 闪闪发光（名言提醒 / 完成任务）
    ('think',  4),   # 手放胸前（暂停）
    ('sad',   11),   # 委屈（没填任务名）
]


def main():
    if not os.path.exists(SRCIMG):
        os.makedirs(os.path.dirname(SRCIMG), exist_ok=True)
        print('下载原图 ->', SRCIMG)
        import urllib.request
        req = urllib.request.Request(URL, headers={'User-Agent': 'dsh'})
        with urllib.request.urlopen(req, timeout=120) as r, open(SRCIMG, 'wb') as f:
            f.write(r.read())

    os.makedirs(OUTDIR, exist_ok=True)
    sheet = Image.open(SRCIMG).convert('RGBA')
    cw = sheet.width // GRID
    ch = sheet.height // GRID

    rules = []
    total = 0
    for name, idx in TILES:
        r, c = divmod(idx, GRID)
        tile = sheet.crop((c * cw, r * ch, (c + 1) * cw, (r + 1) * ch)).crop(BOX)
        path = os.path.join(OUTDIR, 'chara-%s.webp' % name)
        tile.save(path, 'WEBP', quality=92, method=6)
        size = os.path.getsize(path)
        total += size
        with open(path, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('ascii')
        rules.append('.ci-%s{background-image:url("data:image/webp;base64,%s")}' % (name, b64))
        print('  %-9s tile#%-2d %5.1f KB' % (name, idx, size / 1024.0))

    css = ('/* 角色立绘：原版表情图裁切而来（技术处理，未改造型）。\n'
           '   作者：YunYueSama  仓库：https://github.com/YunYueSama/codex-deepseek-pet */\n'
           + '\n'.join(rules) + '\n')
    with open(os.path.join(SRC, 'chara.css'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(css)
    print('合计 %.1f KB，已写入 src/chara.css' % (total / 1024.0))


if __name__ == '__main__':
    main()
