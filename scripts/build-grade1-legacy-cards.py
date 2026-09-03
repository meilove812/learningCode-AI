#!/usr/bin/env python3
from pathlib import Path
import json, html
R=Path(__file__).resolve().parents[1]
D=json.loads((R/'grade1-down/chinese/data/legacy-grade1-cards.json').read_text())
S=json.loads((R/'grade1-down/chinese/data/stroke-shapes.json').read_text())
A='grade1-down/chinese'

def esc(s): return html.escape(str(s),quote=True)
def group_id(unit,idx): return f'u{unit}-g{idx+1}'
def rec_card(r):
    speak=f"{r['char']}，{r['pinyin']}，{r['word']}"
    return f'''<button class="legacy-rec-card" data-char="{esc(r['char'])}" data-speak="{esc(speak)}"><span class="legacy-char">{esc(r['char'])}</span><span class="pinyin">{esc(r['pinyin'])}</span><span class="example">{esc(r['word'])}</span><span aria-hidden="true">🔊</span></button>'''
def write_card(r):
    ch=r['char']; strokes='、'.join(S[ch]); speak=f"{ch}，{r['pinyin']}，{r['word']}"
    return f'''<article class="legacy-write-card" data-hanzi="{esc(ch)}" data-strokes="{esc(strokes)}" data-speak="{esc(speak)}"><button class="legacy-write-head" type="button"><span class="legacy-char">{esc(ch)}</span><span><b class="pinyin">{esc(r['pinyin'])}</b><br><span class="example">{esc(r['word'])}</span> 🔊</span></button><p class="stroke-names"><strong>笔顺：</strong>{esc(strokes)}</p><div class="practice" aria-label="{esc(ch)}的淡色字模和空白田字格"><div class="print-grid trace-glyph">{esc(ch)}</div><div class="print-grid print-blank"></div><div class="print-grid print-blank"></div></div></article>'''
def toolbar(print_button=False):
    p='<button onclick="window.print()">🖨️ 打印写字练习</button>' if print_button else ''
    return f'''<div class="toolbar"><button class="primary" onclick="playAll()">🔊 连续播放</button><button id="speechPause" onclick="pauseSpeak()">⏸ 暂停/继续</button><button onclick="stopSpeak()">⏹ 停止</button><label>语音 <select id="voiceSelect"></select></label><label>语速 <select id="rate"><option value=".65">慢</option><option value=".85" selected>适中</option><option value="1.05">稍快</option></select></label>{p}</div>'''
def page(kind):
    title='完整认字卡' if kind=='recognition' else '完整写字卡'
    data=D[kind]; count=data['recordCount']; uniq=data['uniqueCount']
    nav=''.join(f'<a class="unit-jump" href="#unit-{i+1}">第{i+1}单元</a>' for i in range(8))
    units=[]
    for ui,p in enumerate(data['pages'],1):
      groups=[]
      for gi,g in enumerate(p['groups']):
        rs=[r for r in p['records'] if r['group']==g['name']]
        cards=''.join((rec_card if kind=='recognition' else write_card)(r) for r in rs)
        groups.append(f'''<section class="legacy-group" id="{group_id(ui,gi)}"><div class="group-title"><h3>{esc(g['name'])} · {len(rs)}字</h3><button onclick="playGroup(this)">🔊 本组朗读</button></div><div class="{'legacy-rec-grid' if kind=='recognition' else 'legacy-write-grid'}">{cards}</div></section>''')
      units.append(f'''<section class="card legacy-unit" id="unit-{ui}"><h2>第{ui}单元 · {p['count']}字</h2>{''.join(groups)}</section>''')
    modal='''<div class="hz-modal" id="hzModal" hidden><div class="hz-panel"><div class="hz-head"><h2 id="hzTitle"></h2><button onclick="closeHanzi()">×</button></div><div class="hz-grids"><section class="hz-box"><h3>真实逐画笔顺</h3><div class="tian-grid" id="hzWriter"></div><div class="hz-actions"><button class="primary" onclick="animateHanzi()">▶ 播放</button><button id="hzPause" onclick="pauseHanzi()">⏸ 暂停</button><button onclick="replayHanzi()">↻ 重播</button></div><p id="hzStrokeNames" class="stroke-names"></p></section><section class="hz-box"><h3>逐画描红</h3><div id="traceProgress"></div><div class="tian-grid" id="traceWriter"></div><div id="traceFeedback"></div><button onclick="resetTrace()">↻ 重来</button></section></div><section class="print-practice"><h3>打印练习</h3><div class="practice"><div class="print-grid trace-glyph" id="printGlyph"></div><div class="print-grid print-blank"></div><div class="print-grid print-blank"></div></div></section><p id="hzStatus"></p></div></div>''' if kind=='writing' else ''
    scripts='<script src="assets/hanzi-writer.min.js"></script>' if kind=='writing' else ''
    out=f'''<!doctype html><html lang="zh-CN" data-kind="{kind}" data-hanzi-root="assets/hanzi-data"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>一年级下 · {title}</title><link rel="stylesheet" href="../../assets/site.css"><link rel="stylesheet" href="assets/lesson.css"><link rel="stylesheet" href="assets/legacy-cards.css"></head><body><header class="topbar"><div class="wrap"><a class="brand" href="index.html">← 汉字乐园</a></div></header><main class="wrap"><nav class="crumb"><a href="../../index.html">首页</a> → <a href="../index.html">一年级下</a> → <a href="index.html">汉字乐园</a> → {title}</nav><section class="hero"><span class="badge">旧版完整复用 · 8单元</span><h1>{'👀' if kind=='recognition' else '✏️'} 一年级下 · {title}</h1><p>完整保留旧版字表、拼音、词语、单元与课次分组：共 <strong>{count}</strong> 条，<strong>{uniq}</strong> 个不同汉字。</p>{toolbar(kind=='writing')}<nav class="unit-nav">{nav}</nav></section>{''.join(units)}</main>{modal}{scripts}<script src="assets/legacy-cards.js"></script></body></html>'''
    (R/A/f'{kind}-cards.html').write_text(out)
for k in ('recognition','writing'):page(k)
print('built recognition',D['recognition']['recordCount'],'writing',D['writing']['recordCount'])
