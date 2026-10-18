# -*- coding: utf-8 -*-
"""把 src/app.html 打包成自包含的单文件 HTML（内联立绘 base64）。
用法: python build.py
输出: 上一级目录/学习计时器.html
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'src')
OUT = os.path.join(os.path.dirname(ROOT), '学习计时器.html')


def read(name):
    with open(os.path.join(SRC, name), 'r', encoding='utf-8') as f:
        return f.read()


def main():
    html = read('app.html')
    chara = read('chara.css') if os.path.exists(os.path.join(SRC, 'chara.css')) else ''
    whale = read('whale.html')

    if '/*__CHARA_CSS__*/' not in html:
        sys.exit('app.html 缺少 /*__CHARA_CSS__*/ 占位符（先运行 python tools/make_chara.py）')
    if '<!--__WHALE__-->' not in html:
        sys.exit('app.html 缺少 <!--__WHALE__--> 占位符')

    html = html.replace('/*__CHARA_CSS__*/', chara).replace('<!--__WHALE__-->', whale)

    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write(html)

    print('已生成: %s' % OUT)
    print('大小: %.1f KB' % (os.path.getsize(OUT) / 1024.0))


if __name__ == '__main__':
    main()
