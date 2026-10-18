# -*- coding: utf-8 -*-
"""出图：给应用塞一份演示数据，截几张图看效果。
用法: python tools/shots.py <浏览器exe路径> <输出目录>
"""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(os.path.dirname(ROOT), '学习计时器.html')

SEED_TMPL = r"""
<script>
(function(){
  var now = Date.now();
  function d0(off){ var d = new Date(); d.setHours(0,0,0,0); return d.getTime() - off*86400000; }
  var S = [];
  function add(off, task, min, hour){
    var st = d0(off) + hour*3600000;
    S.push({id:'d'+off+task+hour, task:task, start:st, end:st+min*60000, ms:min*60000});
  }
  // 一条「到 23:59 被自动收尾」的记录，用来看小结里的提示
  function addAuto(off, task, min){
    var d = new Date(); d.setHours(0,0,0,0);
    var end = d.getTime() - off*86400000 + 23*3600000 + 59*60000 + 59999;   // 当天 23:59:59
    S.push({id:'a'+off+task, task:task, start:end-min*60000, end:end, ms:min*60000, auto:1});
  }
  addAuto(0,'诊断学 · 过夜收尾',78);
  add(0,'病理学 · 炎症',42,9);
  add(1,'病理学 · 炎症',33,16);
  add(1,'病理学 · 肿瘤',55,10);
  add(1,'英语 · 阅读',20,15);
  add(2,'病理学 · 肿瘤',70,9);
  add(3,'英语 · 阅读',25,13);
  add(4,'生物化学',48,10);
  add(6,'诊断学',60,9);
  add(5,'政治 · 马原',36,20);
  // 再往前铺一点历史，好让「本周 / 本月」两种视图都有东西可看
  add(7,'药理学',45,14);
  add(9,'病理学 · 肿瘤',50,10);
  add(12,'英语 · 阅读',40,20);
  add(15,'生物化学',55,9);
  add(20,'诊断学',45,15);
  add(25,'政治 · 马原',30,21);
  add(33,'病理学 · 炎症',70,10);
  var running = __RUNNING__;
  if (running) {
    add(0,'病理学 · 肿瘤',0,0);              // 占位，稍后删掉
    S.pop();
    S.push({id:'live', task:'英语 · 阅读', start:now-35*60000, end:now, ms:35*60000});
  }
  var cur = running
    ? {task:'病理学 · 肿瘤', startedAt: now-83*60000, accum:0, resumeAt: now-83*60000, paused:false}
    : null;
  localStorage.setItem('deepseekchan-study-timer-v1', JSON.stringify(
    {sessions:S, current:cur, settings:{sound:true, interval:5},
     lastQuoteAt:now, quoteIdx:3, lastTask: running ? '病理学 · 肿瘤' : '英语 · 阅读'}));
})();
</script>
"""

# 页面初始化完成（__READY__）之前点按钮会被丢掉，所以一律先轮询再点
POLL_JS = r"""
function poll(fn){
  var n = 0;
  (function tick(){
    if (window.__READY__ || n++ > 400) { fn(); return; }
    setTimeout(tick, 25);
  })();
}
"""

DRIVE_PAUSE = ('<script>(function(){' + POLL_JS +
               'poll(function(){ document.querySelector("#btnPause").click(); });})();</script>')

DRIVE_DAY = ('<script>(function(){' + POLL_JS +
             'poll(function(){ document.querySelector("#btnDay").click(); });})();</script>')

DRIVE_WEEK = ('<script>(function(){' + POLL_JS +
              'poll(function(){ document.querySelector("#btnDay").click();' +
              ' setTimeout(function(){ document.querySelector(\'#dayTabs [data-period="week"]\').click(); }, 120);' +
              ' });})();</script>')

DRIVE_MONTH = ('<script>(function(){' + POLL_JS +
               'poll(function(){ document.querySelector("#btnDay").click();' +
               ' setTimeout(function(){ document.querySelector(\'#dayTabs [data-period="month"]\').click(); }, 120);' +
               ' });})();</script>')

# 滚到弹层最底下，专门拍「分析和建议」那一段
DRIVE_ADVICE = ('<script>(function(){' + POLL_JS +
                'poll(function(){ document.querySelector("#btnDay").click();' +
                ' setTimeout(function(){ document.querySelector(\'#dayTabs [data-period="week"]\').click();' +
                '  setTimeout(function(){ var b=document.querySelector("#dayModal .modal-card"); b.scrollTop=b.scrollHeight; }, 500);' +
                ' }, 120); });})();</script>')

# 打开 ⚙ 设置面板，看「每天 23:59 自动收尾」那个开关
DRIVE_SETTINGS = ('<script>(function(){' + POLL_JS +
                  'poll(function(){ document.querySelector("#setBtn").click(); });})();</script>')

# 补记弹层：填好名字和 45 分钟，让「45」那个快捷块也亮着
DRIVE_BACKFILL = ('<script>(function(){' + POLL_JS +
                  'poll(function(){ document.querySelector("#btnBackfill").click();' +
                  ' setTimeout(function(){' +
                  '  document.querySelector("#bfTask").value="药理";' +
                  '  document.querySelector("#bfMin").value="45";' +
                  '  document.querySelector(\'#bfChips [data-min="45"]\').classList.add("on");' +
                  ' }, 200); });})();</script>')


def shoot(exe, page_html, out_png, profile_dir, budget=6000, size='500,800'):
    tmp = tempfile.mkdtemp(prefix='stshot_')
    path = os.path.join(tmp, 'app.html')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(page_html)
    cmd = [exe, '--headless=new', '--disable-gpu', '--no-first-run',
           '--user-data-dir=' + profile_dir, '--hide-scrollbars',
           '--force-device-scale-factor=2',
           '--window-size=' + size,
           '--virtual-time-budget=%d' % budget,
           '--screenshot=' + out_png,
           'file:///' + path.replace('\\', '/')]
    subprocess.run(cmd, capture_output=True, timeout=120)


def main():
    exe = sys.argv[1]
    outdir = sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    with open(HTML, 'r', encoding='utf-8') as f:
        src = f.read()

    def with_seed(running):
        seed = SEED_TMPL.replace('__RUNNING__', 'true' if running else 'false')
        return src.replace('<body>', '<body>' + seed, 1)

    prof = tempfile.mkdtemp(prefix='stprof_')
    shoot(exe, with_seed(False), os.path.join(outdir, 'shot_idle.png'), prof)
    shoot(exe, with_seed(True), os.path.join(outdir, 'shot_run.png'), prof, 9000)
    shoot(exe, with_seed(True).replace('</body>', DRIVE_PAUSE + '</body>'),
          os.path.join(outdir, 'shot_pause.png'), prof, 9000)
    shoot(exe, with_seed(False).replace('</body>', DRIVE_DAY + '</body>'),
          os.path.join(outdir, 'shot_day.png'), tempfile.mkdtemp(prefix='stprof3_'), 8000)
    shoot(exe, with_seed(False).replace('</body>', DRIVE_WEEK + '</body>'),
          os.path.join(outdir, 'shot_week.png'), tempfile.mkdtemp(prefix='stprof4_'), 9000)
    shoot(exe, with_seed(False).replace('</body>', DRIVE_MONTH + '</body>'),
          os.path.join(outdir, 'shot_month.png'), tempfile.mkdtemp(prefix='stprof5_'), 9000)
    shoot(exe, with_seed(False).replace('</body>', DRIVE_ADVICE + '</body>'),
          os.path.join(outdir, 'shot_advice.png'), tempfile.mkdtemp(prefix='stprof6_'), 9000)
    shoot(exe, with_seed(False).replace('</body>', DRIVE_SETTINGS + '</body>'),
          os.path.join(outdir, 'shot_settings.png'), tempfile.mkdtemp(prefix='stprof7_'), 6000)
    shoot(exe, with_seed(False).replace('</body>', DRIVE_BACKFILL + '</body>'),
          os.path.join(outdir, 'shot_backfill.png'), tempfile.mkdtemp(prefix='stprof8_'), 7000)

    empty = src.replace('<body>', '<body><script>try{localStorage.removeItem("deepseekchan-study-timer-v1");}catch(e){}</script>', 1)
    shoot(exe, empty, os.path.join(outdir, 'shot_empty.png'), tempfile.mkdtemp(prefix='stprof2_'), 5000)
    shoot(exe, empty.replace('</body>', DRIVE_DAY + '</body>'),
          os.path.join(outdir, 'shot_day_empty.png'), tempfile.mkdtemp(prefix='stprof3_'), 6000)
    print('已输出到', outdir)


if __name__ == '__main__':
    main()
