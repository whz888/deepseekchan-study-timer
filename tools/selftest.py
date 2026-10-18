# -*- coding: utf-8 -*-
"""自测：把一段驱动脚本注入构建产物，用无头浏览器跑完整流程并回读结果。

覆盖：开始 / 暂停(时间必须冻结) / 继续 / 结束 / 换任务 / 统计累计 / 本地存档 / 关掉后重开恢复
用法: python tools/selftest.py <浏览器exe路径>
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(os.path.dirname(ROOT), '学习计时器.html')

DRIVER = r"""
<script>
(function(){
  // 驱动脚本在解析期执行，此时页面自己的 boot() 还没跑（按钮还没绑事件），
  // 必须等 __READY__ 再动手，否则点击会被丢掉（曾导致截图偶发空白）。
  function ready(fn){
    var n = 0;
    (function tick(){
      if (window.__READY__ || n++ > 400) { fn(); return; }
      setTimeout(tick, 25);
    })();
  }
  var phase = (location.hash || '').replace('#','') || 'phase1';
  var log = [];
  function L(t, v){ log.push(t + ' = ' + v); }
  function done(){
    var pre = document.createElement('pre');
    pre.id = 'TESTLOG';
    pre.textContent = '@@@TESTLOG\n' + log.join('\n') + '\n@@@ENDLOG';
    document.body.appendChild(pre);
  }
  var $ = function(s){ return document.querySelector(s); };
  var sleep = function(ms){ return new Promise(function(r){ setTimeout(r, ms); }); };

  ready(function(){
    var T = window.__TIMER__;
    if (phase === 'phase1') {
      (async function(){
        try {
          // 1. 没填任务名就点开始 -> 应该被拦下
          $('#btnStart').click();
          L('01_no_name_blocked', $('#stateText').textContent + ' / current=' + (T.state.current ? 'yes' : 'null'));

          // 2. 正常开始
          $('#taskInput').value = '病理学 · 炎症';
          $('#btnStart').click();
          L('02_start', $('#stateText').textContent + ' / clock=' + $('#clock').textContent);
          await sleep(3000);
          L('03_after_3s', $('#clock').textContent);

          // 3. 暂停 -> 时间必须冻住
          $('#btnPause').click();
          var p = $('#clock').textContent;
          L('04_paused', $('#stateText').textContent + ' / clock=' + p);
          await sleep(2500);
          L('05_frozen', $('#clock').textContent + '  (期望等于 ' + p + ')');

          // 4. 继续
          $('#btnStart').click();
          L('06_resume_btn', $('#btnStart').textContent + ' / ' + $('#stateText').textContent);
          await sleep(2000);

          // 5. 换任务：先结掉当前这一段
          $('#btnSwitch').click();
          L('07_after_switch', 'sessions=' + T.state.sessions.length + ' current=' + (T.state.current ? 'yes' : 'null'));
          L('08_first_session_ms', T.state.sessions.length ? T.state.sessions[0].ms : 'n/a');

          // 6. 第二个任务
          $('#taskInput').value = '英语 · 阅读';
          $('#btnStart').click();
          await sleep(1500);
          $('#btnStop').click();
          L('09_sessions', JSON.stringify(T.state.sessions.map(function(s){ return s.task + ':' + s.ms; })));
          L('10_total', $('#totalValue').textContent.replace(/\s+/g, ' '));
          L('11_rows', document.querySelectorAll('#list .row').length + ' 个分组');
          L('12_storage_bytes', (localStorage.getItem('deepseekchan-study-timer-v1') || '').length);

          // 7. 切到累计页
          document.querySelectorAll('.tabs button')[1].click();
          L('13_all_tab', $('#totalValue').textContent.replace(/\s+/g, ' '));

          // 8. 回跳到旧项目：先另起一个任务（模拟"学完病理去读药理"），再点统计区里的病理行
          document.querySelectorAll('.tabs button')[0].click();
          $('#taskInput').value = '药理学 · 传出神经系统';
          $('#btnStart').click();
          await sleep(1200);
          L('14_now_task', T.state.current ? T.state.current.task : 'null');
          var target = null;
          Array.prototype.forEach.call(document.querySelectorAll('#list .row.proj'), function (r) {
            if (r.querySelector('.nm').textContent.indexOf('病理学 · 炎症') === 0) target = r;
          });
          L('15_proj_rows', Array.prototype.map.call(document.querySelectorAll('#list .row.proj'), function (r) {
            return r.querySelector('.nm').textContent;
          }).join(' | '));
          L('16_target_clickable', target ? (target.getAttribute('data-resume') || '(no data-resume)') : 'NOT FOUND');
          if (target) target.click();
          await sleep(900);
          L('17_resumed_task', T.state.current ? T.state.current.task : 'null');
          L('18_resumed_clock', $('#clock').textContent + ' / ' + $('#stateText').textContent);
          L('19_all_sessions', JSON.stringify(T.state.sessions.map(function (s) { return s.task + ':' + s.ms; })));

          // 9. 明细行也要能回跳（明细排在 #list 末尾，live 那条不给点）
          L('20_detail_rows', document.querySelectorAll('#list .sess').length +
            ' 行, 可点=' + document.querySelectorAll('#list .sess[data-resume]').length);
          L('21_live_row_not_clickable', T.state.current && T.state.current.task === '病理学 · 炎症'
            ? '当前任务无 data-resume = ' + (document.querySelector('#list .sess[data-resume="病理学 · 炎症"]') ? 'NO' : 'OK')
            : '当前任务不是病理学，跳过');

          // 10. 明细行上的 ✕ 只能删记录，不能顺带把任务切过去
          var delBtn = document.querySelector('#list .sess[data-resume] .del');
          var before = T.state.sessions.length, beforeTask = T.state.current.task;
          if (delBtn) delBtn.click();
          await sleep(400);
          L('22_del_only', 'sessions ' + before + '->' + T.state.sessions.length +
            ' / current 仍然 = ' + (T.state.current ? T.state.current.task : 'null') +
            ' (点 ✕ 前=' + beforeTask + ')');

          // 11. 今日小结：点按钮弹层 -> 数字/点评/项目条都要对得上
          $('#btnStop').click();
          await sleep(600);
          var st = T.dayStat();
          L('23_day_stat', 'total=' + st.total + ' / 段数=' + st.list.length +
            ' / 科目=' + st.items.length + ' / 连续=' + st.streak + ' / 昨天=' + st.prevTotal);
          $('#btnDay').click();
          await sleep(300);
          L('24_modal_open', 'hidden=' + $('#dayModal').hidden +
            ' / 标题=' + $('#dayTotal').textContent + ' / 副标题=' + $('#daySub').textContent);
          L('25_modal_chips', Array.prototype.map.call($('#dayChips').children, function (d) {
            return d.querySelector('b').textContent + d.querySelector('i').textContent; }).join(' | '));
          var cmt = Array.prototype.map.call($('#dayComment').querySelectorAll('p'), function (p) { return p.textContent; });
          L('26_comment_lines', cmt.length + ' 句');
          L('27_comment', cmt.join(' '));
          L('28_modal_body', $('#dayBody').textContent.replace(/\s+/g, ' ').slice(0, 120));
          L('29_bar_count', $('#dayBody').querySelectorAll('.bar').length + ' 条项目条');
          // 点评里不能出现"差/不如/怎么才"这类泄气词
          L('30_no_discourage', /不如|才这么|怎么才|太差|不够努力/.test(cmt.join('')) ? 'FOUND 泄气词' : 'OK 没有泄气词');
          $('#dayClose').click();
          L('31_modal_closed', 'hidden=' + $('#dayModal').hidden);
          // 空记录时的点评也要给台阶，不能冷场
          var keep = T.state.sessions.slice();
          T.state.sessions = [];
          var emptyCmt = T.dayStat();
          T.openDay();
          L('32_empty_day', $('#dayTotal').textContent + ' / ' + $('#daySub').textContent +
            ' / 点评首句=' + $('#dayComment').querySelector('p').textContent);
          L('33_empty_streak_hint', emptyCmt.streak > 0 ? ('提到连续 ' + emptyCmt.streak + ' 天') : '无历史，不提示');
          T.closeDay();
          T.state.sessions = keep;
          L('34_restore_after_test', 'sessions=' + T.state.sessions.length);

          // 13. 周 / 月小结：切标签、周期切分是否精确、分析和建议有没有出来
          $('#btnDay').click();
          await sleep(200);
          var tabs = Array.prototype.map.call($('#dayTabs').querySelectorAll('button'), function (b) {
            return b.textContent + (b.classList.contains('on') ? '*' : ''); });
          L('35_period_tabs', tabs.join(' | '));

          // 用构造数据验证周期边界：把记录换成本周内 / 上周内 / 本月早段 / 40 天前
          var keep2 = T.state.sessions.slice();
          var WR = T.periodRange('week'), MR = T.periodRange('month');
          function mk(ts, task, min) {
            return { id: 'x' + task, task: task, start: ts, end: ts + min * 60000, ms: min * 60000 };
          }
          T.state.sessions = [
            mk(WR.start + 3600000, '本周内', 60),      // 1 小时，落在本周
            mk(WR.start - 3600000, '上周内', 30),      // 0.5 小时，落在上一周
            mk(MR.start + 7200000, '本月早段', 45),    // 0.75 小时，落在这个月
            mk(Date.now() - 40 * 86400000, '四十天前', 999)  // 不该被本周/本月算进去
          ];
          var wk = T.periodStat('week'), mo = T.periodStat('month');
          function has(st, name) { return st.list.some(function (s) { return s.task === name; }); }
          function ms(st, name) { var t = 0; st.list.forEach(function (s) { if (s.task === name) { t += s.ms; } }); return t / 60000; }
          // 注意：本周边界会落在月内哪一天取决于今天几号，
          // 所以这里不断言绝对值，只断言“谁该进、谁不该进”，数字照打出来供肉眼核对
          L('36_week_split', '本周含本周内=' + has(wk, '本周内') + ' / 不含上周内=' + !has(wk, '上周内') +
            ' / 不含四十天前=' + !has(wk, '四十天前') +
            '  （本周总计 ' + wk.total / 60000 + ' 分钟，上周 ' + wk.prevTotal / 60000 + ' 分钟）');
          L('37_month_excludes', '本月含本月早段=' + has(mo, '本月早段') +
            ' / 不含四十天前=' + !has(mo, '四十天前') +
            '  （本月总计 ' + mo.total / 60000 + ' 分钟，其中本周内 ' + ms(mo, '本周内') +
            ' 分钟、上周内 ' + ms(mo, '上周内') + ' 分钟 —— 这两个是否算进本月取决于今天几号）');

          // 切到本周视图
          $('#dayTabs').querySelector('[data-period="week"]').click();
          await sleep(200);
          L('38_week_view', '标题=' + $('#dayTitle').textContent + ' / 日期=' + $('#dayDate').textContent +
            ' / 总量=' + $('#dayTotal').textContent + ' / 副标=' + $('#daySub').textContent);
          var wadv = $('#dayBody').querySelectorAll('.adv .a');
          L('39_week_advice', wadv.length + ' 张卡片 / 首张=' +
            (wadv[0] ? wadv[0].querySelector('b').textContent + ' → ' + wadv[0].querySelector('p').textContent.slice(0, 60) : '无'));
          L('40_week_bars', $('#dayBody').querySelectorAll('.dm-days i').length + ' 根日柱子 / ' +
            $('#dayBody').querySelectorAll('.dm-tod div').length + ' 个时段格');
          var wcmt = Array.prototype.map.call($('#dayComment').querySelectorAll('p'), function (p) { return p.textContent; });
          L('41_week_comment', wcmt.join(' ').slice(0, 130));
          L('42_week_tone', /大哥哥/.test(wcmt.join('')) ? 'OK 喊了大哥哥' : 'MISSING 没喊大哥哥');
          L('43_week_no_discourage', /不如|才这么|怎么才|太差|不够努力|懒惰/.test(
            wcmt.join('') + Array.prototype.map.call(wadv, function (a) { return a.textContent; }).join('')) ?
            'FOUND 泄气词' : 'OK 没有泄气词');

          // 切到本月视图
          $('#dayTabs').querySelector('[data-period="month"]').click();
          await sleep(200);
          L('44_month_view', '标题=' + $('#dayTitle').textContent + ' / 日期=' + $('#dayDate').textContent +
            ' / 总量=' + $('#dayTotal').textContent);
          L('45_month_advice', $('#dayBody').querySelectorAll('.adv .a').length + ' 张卡片 / 日柱 ' +
            $('#dayBody').querySelectorAll('.dm-days i').length + ' 根');
          L('46_month_comment_tone', /大哥哥/.test(Array.prototype.map.call(
            $('#dayComment').querySelectorAll('p'), function (p) { return p.textContent; }).join('')) ?
            'OK 喊了大哥哥' : 'MISSING');

          // 空数据的周/月也要给台阶
          T.state.sessions = [];
          T.renderDay();
          L('47_empty_week', $('#dayTotal').textContent + ' / ' + $('#dayComment').querySelector('p').textContent);
          T.state.sessions = keep2;
          T.closeDay();
          L('48_restore', 'sessions=' + T.state.sessions.length);

          // 14. 跨日自动收尾：忘了按结束的计时不许把时间带到第二天
          var keep3 = T.state.sessions.slice();
          var yBin = new Date(Date.now() - 86400000); yBin.setHours(20, 0, 0, 0);   // 昨天 20:00
          var yStart = yBin.getTime();

          // (a) 今天还在跑的计时：不许被收掉
          T.state.current = { task: '今天的', startedAt: Date.now() - 600000, accum: 0,
                              resumeAt: Date.now() - 600000, paused: false };
          var a1 = T.autoClose();
          L('49_today_not_closed', '收尾=' + (a1 ? a1.task : 'null') + ' / current=' +
            (T.state.current ? T.state.current.task : 'null'));

          // (b) 昨晚 20:00 开始、一直没结束（还在跑）：应停在昨天 23:59
          T.state.sessions = [];
          T.state.current = { task: '昨晚忘了停', startedAt: yStart, accum: 0, resumeAt: yStart, paused: false };
          var b1 = T.autoClose();
          var rec = T.state.sessions[0];
          L('50_overnight_closed', '收尾=' + (b1 ? b1.task + ' / ' + Math.round(b1.ms / 60000) + ' 分钟' : 'null') +
            ' / current=' + (T.state.current ? 'yes' : 'null'));
          L('51_capped_at_2359', rec
            ? ('记录 ' + Math.round(rec.ms / 60000) + ' 分钟 / auto=' + rec.auto +
               ' / 归属日=' + new Date(rec.start).getDate() + ' 号 / 结束于 ' +
               new Date(rec.end).getHours() + ':' + ('0' + new Date(rec.end).getMinutes()).slice(-2))
            : '无记录');

          // (c) 暂停着过夜：只按已经累计的时间收，不能凭空多算
          T.state.sessions = [];
          T.state.current = { task: '暂停过夜', startedAt: yStart, accum: 45 * 60000, resumeAt: null, paused: true };
          var c1 = T.autoClose();
          L('52_paused_overnight', '收尾=' + (c1 ? Math.round(c1.ms / 60000) + ' 分钟' : 'null') +
            ' / sessions=' + T.state.sessions.length);

          // (d) 收尾掉的这段不能算进「今天」
          T.state.sessions = [rec];
          L('53_not_counted_today', '今日合计=' + Math.round(T.dayStat().total / 60000) + ' 分钟');

          // (e) 关掉开关就该恢复旧行为（不做自动收尾）
          T.state.settings.autoClose = false;
          T.state.current = { task: '关掉开关', startedAt: yStart, accum: 60000, resumeAt: null, paused: true };
          var e1 = T.autoClose();
          L('54_toggle_off', '收尾=' + (e1 ? 'yes' : 'null') + ' / current=' +
            (T.state.current ? T.state.current.task : 'null'));
          T.state.settings.autoClose = true;
          T.state.current = null;

          // (f) 小结里要能看出哪一段是自动收尾的
          //     （(b) 那条落在昨天，本周不一定含昨天，所以另造一条落在本周内的）
          var WR2 = T.periodRange('week');
          T.state.sessions = [{ id: 'auto-w', task: "自动收尾的", start: WR2.start + 3600000,
                                end: WR2.start + 4200000, ms: 600000, auto: 1 }];
          T.openDay(); await sleep(200);
          $('#dayTabs').querySelector('[data-period="week"]').click();
          await sleep(200);
          var note = $('#dayChips').querySelector('.dm-autonote');
          L('55_week_autonote', note ? note.textContent : '无');
          T.state.sessions = [{ id: 'auto-today', task: '今天自动收尾',
                                start: Date.now() - 600000, end: Date.now(), ms: 600000, auto: 1 }];
          T.closeDay();
          T.render();
          await sleep(150);
          var atag = $('#list').querySelector('.tag-auto');
          L('56_detail_autotag', atag ? atag.textContent : '无');

          // (g) 设置里那个开关在不在、默认开不开
          var ck = $('#setAutoClose');
          L('57_autoclose_switch', ck ? ('存在 / 默认勾选=' + ck.checked) : '不存在');

          T.state.sessions = keep3;
          L('58_restore_autoclose', 'sessions=' + T.state.sessions.length);

          // (i) 补记：学之前忘了开计时
          var bfBase = T.state.sessions.slice();
          var bf0 = bfBase.length;
          $('#btnBackfill').click();
          await sleep(150);
          L('60_backfill_open', 'hidden=' + $('#bfModal').hidden + ' / 候选项目=' + $('#bfList').children.length +
            ' / 预填=' + ($('#bfTask').value || '空'));
          $('#bfTask').value = '';
          $('#bfMin').value = '30';
          $('#bfOk').click();
          await sleep(120);
          L('61_backfill_no_task', 'sessions=' + T.state.sessions.length + ' / 弹层还开着=' + !$('#bfModal').hidden);
          $('#bfTask').value = '补记测试';
          $('#bfMin').value = '0';
          $('#bfOk').click();
          await sleep(120);
          L('62_backfill_zero', 'sessions=' + T.state.sessions.length + '（应当没变）');
          $('#bfMin').value = 'abc';
          $('#bfOk').click();
          await sleep(120);
          L('63_backfill_nan', 'sessions=' + T.state.sessions.length + '（应当没变）');

          $('#bfMin').value = '45';
          $('#bfOk').click();
          await sleep(250);
          var bfRec = T.state.sessions[T.state.sessions.length - 1];
          L('64_backfill_ok', 'sessions=' + T.state.sessions.length + '（期望 ' + (bf0 + 1) + '）/ 弹层关了=' + $('#bfModal').hidden);
          var bfD = new Date(bfRec.start), bfN = new Date();
          L('65_backfill_rec', bfRec.task + ' / ' + Math.round(bfRec.ms / 60000) + ' 分钟 / manual=' + bfRec.manual +
            ' / 落在今天=' + (bfD.getDate() === bfN.getDate() && bfD.getMonth() === bfN.getMonth()));

          // 计入项目：合并成一条，不做单独的「补记」分类
          var bfRow = [].slice.call($('#list').querySelectorAll('.row.proj')).filter(function (r) {
            return r.getAttribute('data-resume') === '补记测试';
          })[0];
          L('66_backfill_merged', bfRow
            ? ('项目行=' + bfRow.querySelector('.du').textContent.replace(/\s+/g, ' ').trim() +
               ' / 占比=' + bfRow.querySelector('.nm i').textContent)
            : '没有这一行');
          L('67_backfill_total', '今日合计=' + $('#totalValue').textContent.replace(/\s+/g, ' '));
          var bfSess = [].slice.call($('#list').querySelectorAll('.sess')).filter(function (s) {
            return s.textContent.indexOf('补记测试') >= 0;
          })[0];
          L('68_backfill_plain', bfSess ? ('明细=' + bfSess.textContent.replace(/\s+/g, ' ').trim()) : '没找到明细行');

          // 记到昨天
          $('#btnBackfill').click();
          await sleep(150);
          $('#bfTask').value = '昨天补的';
          $('#bfMin').value = '30';
          $('#bfDay').querySelector('[data-d="1"]').click();
          $('#bfOk').click();
          await sleep(250);
          var bfY = T.state.sessions[T.state.sessions.length - 1];
          var bfYD = new Date(bfY.start), bfYes = new Date(Date.now() - 86400000);
          L('69_backfill_yesterday', bfY.task + ' / 落在昨天=' +
            (bfYD.getDate() === bfYes.getDate() && bfYD.getMonth() === bfYes.getMonth()) +
            ' / ' + Math.round(bfY.ms / 60000) + ' 分钟');

          // 超长补记不该越到前天去（否则会被算进另一天）
          $('#btnBackfill').click();
          await sleep(150);
          $('#bfTask').value = '超长补记';
          $('#bfMin').value = '1440';
          $('#bfDay').querySelector('[data-d="1"]').click();
          $('#bfOk').click();
          await sleep(250);
          var bfL = T.state.sessions[T.state.sessions.length - 1];
          var bfLD = new Date(bfL.start);
          L('70_backfill_clamp', 'start 仍在昨天=' + (bfLD.getDate() === bfYes.getDate()) +
            ' / 时长=' + Math.round(bfL.ms / 60000) + ' 分钟');

          T.state.sessions = bfBase;
          T.render();
          L('71_backfill_restore', 'sessions=' + T.state.sessions.length);

          // (h) 留一个「昨晚忘了停」的计时在存档里，交给第二轮验证开机时会不会自动收尾
          var yBin2 = new Date(Date.now() - 86400000); yBin2.setHours(21, 0, 0, 0);
          T.state.current = { task: '昨晚的过夜计时', startedAt: yBin2.getTime(), accum: 0,
                              resumeAt: yBin2.getTime(), paused: false };
          T.state.lastTask = '病理学 · 炎症';
          T.save();
          L('59_leave_overnight_for_phase2', '已把过夜中的「' + T.state.current.task + '」写进存档');
        } catch (e) { L('!!EXCEPTION', e && e.message); }
        done();
      })();
    } else {
      try {
        L('20_restored_sessions', T.state.sessions.length);
        L('21_restored_total', $('#totalValue').textContent.replace(/\s+/g, ' '));
        L('22_last_task_prefill', $('#taskInput').value);
        L('23_rows', document.querySelectorAll('#list .row').length);
        // 开机时应该已经把「昨晚忘了停」的那段按 23:59 收掉了
        var lastRec = T.state.sessions[T.state.sessions.length - 1];
        L('24_boot_autoclose', 'current=' + (T.state.current ? T.state.current.task : 'null') +
          ' / 末条=' + (lastRec ? (lastRec.task + ' · ' + Math.round(lastRec.ms / 60000) + ' 分钟 · auto=' + lastRec.auto) : '无'));
        L('25_boot_state_text', $('#stateText').textContent + ' / 今日=' + $('#todayText').textContent);
      } catch (e) { L('!!EXCEPTION', e && e.message); }
      done();
    }
  });
})();
</script>
"""


def run(exe, url, profile, budget):
    tmp = tempfile.mkdtemp(prefix='sttest_')
    cmd = [exe, '--headless=new', '--disable-gpu', '--no-first-run',
           '--user-data-dir=' + profile, '--hide-scrollbars',
           '--window-size=500,800',
           '--virtual-time-budget=%d' % budget,
           '--dump-dom', url]
    try:
        out = subprocess.run(cmd, capture_output=True, timeout=180)
        return out.stdout.decode('utf-8', 'ignore')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def extract(dom, raw_name=None):
    # Edge 在 Windows 上 dump 出来的换行是 CRLF，先归一化再匹配
    dom = dom.replace('\r\n', '\n').replace('\r', '\n')
    m = re.search(r'@@@TESTLOG\n(.*?)\n@@@ENDLOG', dom, re.S)
    if not m and raw_name:
        p = os.path.join(os.environ.get('TEMP', '.'), raw_name)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(dom)
        return '(没有拿到测试输出，原始 DOM 已存到 %s，长度 %d)' % (p, len(dom))
    return m.group(1) if m else '(没有拿到测试输出)'


def main():
    exe = sys.argv[1] if len(sys.argv) > 1 else 'msedge.exe'
    with open(HTML, 'r', encoding='utf-8') as f:
        src = f.read()
    if '</body>' not in src:
        sys.exit('构建产物异常')
    page = src.replace('</body>', DRIVER + '</body>')

    tmpdir = tempfile.mkdtemp(prefix='stapp_')
    page_path = os.path.join(tmpdir, 'app.html')
    with open(page_path, 'w', encoding='utf-8') as f:
        f.write(page)
    url = 'file:///' + page_path.replace('\\', '/')

    profile = os.path.join(tmpdir, 'profile')
    report = []
    report.append('=== 第一轮：完整流程 ===')
    report.append(extract(run(exe, url + '#phase1', profile, 40000), 'st_raw1.txt'))
    report.append('')
    report.append('=== 第二轮：关掉重开（同一份存档）===')
    report.append(extract(run(exe, url + '#phase2', profile, 6000), 'st_raw2.txt'))
    text = '\n'.join(report)
    outfile = os.path.join(os.environ.get('TEMP', '.'), 'st_selftest.txt')
    with open(outfile, 'w', encoding='utf-8') as f:
        f.write(text)
    print('结果已写入:', outfile)
    shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == '__main__':
    main()
