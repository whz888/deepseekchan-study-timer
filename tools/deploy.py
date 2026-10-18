# -*- coding: utf-8 -*-
"""把应用装到桌面：复制文件 + 生成带图标的快捷方式（Edge 应用窗口模式）。
用法: python tools/deploy.py
"""
import os
import shutil
import subprocess
import sys
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILT = os.path.join(os.path.dirname(ROOT), '学习计时器.html')
ICON = os.path.join(os.path.dirname(ROOT), '学习计时器.ico')
NAME = '学习计时器'
WIN = '500,760'
# 用「你平时那个 Edge 配置」打开（不带 --user-data-dir）：这样桌面图标和直接双击
# index.html 用的是同一份存档。代价是 Edge 已经在跑时 --window-size 会被忽略，
# 所以页面自己在 hash=#app 时调用 window.resizeTo 把窗口调成小尺寸。
OLD_PROFILE = os.path.join(os.environ.get('LOCALAPPDATA', os.environ['USERPROFILE']),
                           'DeepSeekChanStudyTimer')

README = """学习计时器 —— 使用说明
========================================

【怎么打开】
双击桌面上的「学习计时器」图标即可。它是以应用窗口方式打开的，
没有地址栏、没有标签页，窗口会自动缩成 500×760 的小尺寸，就像一个小软件。
直接双击文件夹里的 index.html 也能用，看到的是同一份记录。

【怎么用】
1. 在输入框里写下这次要学什么（例如「病理学 · 炎症」「英语 · 阅读」）。
2. 点「开始」—— 计时开始，DeepSeek酱会陪着你。
3. 中途要接电话、吃饭：点「暂停」，时间会冻住，回来点「继续」。
4. 这一项学完了：点「结束」，这一段时长就记进统计里了。
5. 想马上换一门：「结束当前任务，换一个」，输入新任务名再点开始。
6. 学着学着想换回之前那门课？下半部分统计里，每个项目、每条明细
   **点一下就直接回去接着记它**，时间照旧累加到同一个项目上。

【忘了开计时怎么办（补记）】
已经学完才发现没按开始？点「开始」下面那行小字「忘了开计时？补记一笔」：
   · 「学的是什么」——点已有的项目名会自动补全；
   · 「补多久」——填分钟数，或者直接点 15 / 30 / 45 / 1 小时 / 1.5 小时 / 2 小时；
   · 选「今天」还是「昨天」，点「记上」。
这段时长会**直接并进那个项目**，跟计时记下来的完全一样：
统计、今日/本周/本月小结、各科目占比都算它一份，
**不会单独列一个「补记」的分类**，看上去就是这一天多学了一会儿。
记错了就在明细里点那一行的 ✕ 删掉。

【忘了按结束怎么办】
每天 23:59:59，应用会自动替你把当天还在走的计时「收尾」——
只结算到当天最后一秒，跨过午夜的那部分不算，省得昨天没结束的钟一直走到今天，
把今天的时间算到昨天的头上。

  · 收尾出来的那一段，明细里会标上「23:59 收尾」，小结里也会写明有几段是自动收的。
  · 如果 23:59 那会儿应用是关着的，下次打开时会自动补收（照样只算到当天 23:59）。
  · 不想要这个行为，可以在右下 ⚙ 里把「每天 23:59 自动收尾」取消勾选。

另外：**关掉窗口就相当于按了暂停**。不会再出现「关着的时候还在偷偷计时」，
下次打开会提示「上次的「某某」还没结束，先停在 32 分钟」，点「继续」接着记。

【名言提醒】
计时过程中每隔几分钟（默认 5 分钟，可在右下 ⚙ 里改成 3/10/15/30 分钟），
DeepSeek酱会换一句名人名言给你打气。右上角的 ♪ 可以开关提示音。

【统计】
下半部分是统计：
  · 「今日」标签 —— 今天每个项目的时长、占比，以及每段的起止明细。
  · 「累计」标签 —— 从开始使用到现在的总时长和各项目分时长。
  · 中间那排小柱子是「近 7 天」每天学了多久，今天那根会亮起来。
点明细行右边的 ✕ 可以删掉记错的那一条（只删记录，不会切任务）。

【学习小结（日 / 周 / 月）】
统计区里有一行「🌙 学习小结 · 日 / 周 / 月 · 让 DeepSeek酱 夸夸你」，点开是一张总结卡片，
上面用三个标签切换「今日 / 本周 / 本月」。每种周期都会给你：

  · 总时长、几个科目、几段专注、连着记了几天（周月是「几天有记录 / 平均每天」）、最长的一段
  · 一根一根的小柱子，看这一周 / 这一个月每天学了多久
  · 每个科目各占多少（占比条）
  · 周、月视图还有「什么时候在学」：凌晨 / 上午 / 下午 / 晚上各占几成
  · 周、月视图最下面有【分析和建议】：和上周 / 上月比、节奏稳不稳、
    科目结构偏不偏、你在哪个时段最有效率，再根据这些给两三条具体建议

卡片顶上 DeepSeek酱会用小朋友的语气夸你几句 —— 只夸不训，
哪怕今天只学了 5 分钟也照样有小红花；喊你「大哥哥」。
认真学完一段（满 1 分钟）时，这行会闪一下提醒你可以看看小结。

【数据存在哪】
存在浏览器本地（localStorage），关掉窗口、重启电脑都不会丢。
它跟着「你平时用的那个 Edge 配置」走，所以：

  · 点桌面图标打开            → 同一份存档
  · 双击文件夹里的 index.html  → 同一份存档
  · 在 Edge 里用标签页打开      → 还是同一份存档

也就是说，不管怎么打开，看到的都是同一份记录。
只有换浏览器、换电脑，或者清空浏览器数据，才会看不到。
想备份/搬机器：右下 ⚙ →「导出备份」存一个 json，到新机器上 ⚙ →「导入」并回来。

【注意】
· 计时用的时间戳是按真实时间算的，就算中途把窗口关掉，
  只要任务还在"计时中"，下次打开会接着算。
· 同一个浏览器里开两个窗口时，一边改了记录，另一边会自动跟着同步。
· 内容仅供个人学习记录使用。

【出处】
角色立绘：网友二创的 DeepSeek「鲸鱼娘 / 蓝色大肥鱼」Q 版形象。
  素材作者 YunYueSama（仓库 codex-deepseek-pet，大肥鱼项目署名许可 1.0），
  本作只做裁切与格式转换，未改造型。
  角色原型为创作者「上善无形」的原创角色「溟月」（CC BY-NC-SA 4.0 开放二创）。
"""


def find_edge():
    cands = [
        os.path.join(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'),
                     r'Microsoft\Edge\Application\msedge.exe'),
        os.path.join(os.environ.get('ProgramFiles', r'C:\Program Files'),
                     r'Microsoft\Edge\Application\msedge.exe'),
        os.path.join(os.environ.get('ProgramFiles', r'C:\Program Files'),
                     r'Google\Chrome\Application\chrome.exe'),
        os.path.join(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'),
                     r'Google\Chrome\Application\chrome.exe'),
    ]
    for c in cands:
        if os.path.exists(c):
            return c
    return None


def main():
    if not os.path.exists(BUILT):
        sys.exit('还没构建，先运行 python build.py')
    edge = find_edge()
    if not edge:
        sys.exit('没找到 Edge/Chrome')

    desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
    if not os.path.isdir(desktop):
        sys.exit('找不到桌面目录: ' + desktop)
    appdir = os.path.join(desktop, NAME)
    os.makedirs(appdir, exist_ok=True)

    shutil.copy2(BUILT, os.path.join(appdir, 'index.html'))
    if os.path.exists(ICON):
        shutil.copy2(ICON, os.path.join(appdir, NAME + '.ico'))
    with open(os.path.join(appdir, '使用说明.txt'), 'w', encoding='utf-8') as f:
        f.write(README)

    target = os.path.join(appdir, 'index.html').replace('\\', '/')
    url = 'file:///' + quote(target, safe='/:') + '#app'
    args = ('--app="%s" --window-size=%s '
            '--no-first-run --no-default-browser-check --disable-sync --no-service-autorun'
            % (url, WIN))
    lnk = os.path.join(desktop, NAME + '.lnk')
    icon = os.path.join(appdir, NAME + '.ico')

    ps = '''
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut("%s")
$sc.TargetPath = "%s"
$sc.Arguments = '%s'
$sc.WorkingDirectory = "%s"
$sc.IconLocation = "%s,0"
$sc.Description = "学习计时器 —— 记录每一段学习时长"
$sc.Save()
Write-Output "OK"
''' % (lnk, edge, args, appdir, icon)

    r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps],
                       capture_output=True)
    out = (r.stdout or b'').decode('utf-8', 'ignore').strip()
    err = (r.stderr or b'').decode('utf-8', 'ignore').strip()
    print('快捷方式:', lnk, '->', out or err)
    print('应用目录:', appdir)
    print('启动命令:', edge, args)

    # 旧版本用的是独立浏览器配置，那份存档里没有任何记录（数据都在默认配置里），清掉免得混淆
    if os.path.isdir(OLD_PROFILE):
        shutil.rmtree(OLD_PROFILE, ignore_errors=True)
        print('已清理旧的独立浏览器配置:', OLD_PROFILE,
              '(还残留说明 Edge 正开着，关掉窗口后可手动删)')


if __name__ == '__main__':
    main()
