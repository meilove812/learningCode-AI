#!/usr/bin/env python3
from pathlib import Path
import json,html
R=Path(__file__).resolve().parents[1]
D=json.loads((R/'data/chinese-lesson-character-map.json').read_text())
modal='''<div class="hz-modal" id="hzModal" hidden><div class="hz-panel"><div class="hz-head"><h2 id="hzTitle"></h2><button onclick="closeHanzi()">×</button></div><div class="hz-grids"><section class="hz-box"><h3>看真实笔顺</h3><div class="tian-grid" id="hzWriter"></div><div class="hz-actions"><button class="primary" onclick="animateHanzi()">▶ 播放</button><button id="hzPause" onclick="pauseHanzi()">⏸ 暂停</button><button onclick="replayHanzi()">↻ 重播</button></div><p id="hzStrokeNames" class="stroke-names"></p></section><section class="hz-box"><h3>逐画描红</h3><div id="traceProgress"></div><div class="tian-grid" id="traceWriter"></div><div id="traceFeedback"></div><button onclick="resetTrace()">↻ 重来</button></section></div><section class="print-practice"><h3>打印练习</h3><div class="print-grids"><div class="print-grid trace-glyph" id="printGlyph"></div><div class="print-grid print-blank"></div><div class="print-grid print-blank"></div></div></section><p id="hzStatus"></p></div></div>'''
def rec(x):
 c,p,w=x; s=f'{c}，{p}，{w}'
 return f'<button class="recognition-card" data-recognition="{c}" data-speak="{s}"><span class="hanzi-main">{c}</span><span class="pinyin">{p}</span><span class="example">{w}</span><span>🔊</span></button>'
def write(x):
 c,p,w,st=x;s=f'{c}，{p}，{w}'
 return f'<article class="writing-card" data-hanzi="{c}" data-strokes="{st}" data-speak="{s}"><button class="writing-head"><span class="hanzi-main">{c}</span><span><b class="pinyin">{p}</b><br><span class="example">{w}</span> 🔊</span></button><p class="stroke-names"><strong>笔顺：</strong>{st}</p><div class="practice"><div class="print-grid trace-glyph">{c}</div><div class="print-grid"></div><div class="print-grid"></div></div></article>'
def page(course,key,info,prev,nxt):
 root=R/('grade2-up/chinese/unit1' if course=='grade2-up' else 'grade1-down/chinese/lessons')
 base='../../../assets/site.css' if course=='grade2-up' else '../../../assets/site.css'
 assets='assets' if course=='grade2-up' else '../assets'
 title=html.escape(info['title']); confirmed=bool(info['recognition'] or info['writing'])
 nav=(f'<a href="{prev}.html">← 上一课</a>' if prev else '<a href="index.html">← 目录</a>')+f'<strong>{title} · 认字与写字</strong>'+(f'<a href="{nxt}.html">下一课 →</a>' if nxt else '<a href="index.html">目录 →</a>')
 if confirmed:
  writing_section=(f'''<section class="card literacy-section writing-section"><h2>B 写字（要求会写） · {len(info['writing'])}字</h2><p>每个字都有真实笔顺动画、播放/暂停/重播、逐画描红、笔顺说明和可打印田字格。</p><div class="writing-grid">{''.join(map(write,info['writing']))}</div></section>''' if info['writing'] else '''<section class="card literacy-section writing-section"><h2>B 写字（要求会写） · 0字</h2><p>旧站没有提供这节课的会写字集合、笔顺或描红数据。为避免把生活常用字误作课文写字表，本区暂不补字；待有可靠的原课次资料后再原样迁移。</p></section>''')
  body=f'''<section class="card literacy-section recognition-section"><h2>A 认字（要求会认） · {len(info['recognition'])}字</h2><p>读准字音、联系词语观察字形；这些字不标作本课必写字。</p><div class="recognition-grid">{''.join(map(rec,info['recognition']))}</div><button class="primary group-speak" onclick="playRecognition()">🔊 整组朗读认字</button></section>{writing_section}'''
 else:
  body='''<section class="card literacy-section"><h2>逐课结构已建立</h2><p>这节课的认字表与写字表尚未从可靠的原课次资料确认，因此暂不展示字表，也不会用单元总字表代替或猜测。</p></section>'''
 out=f'''<!doctype html><html lang="zh-CN" data-hanzi-root="{assets}/hanzi-data"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} · 认字与写字</title><link rel="stylesheet" href="{base}"><link rel="stylesheet" href="{assets}/lesson.css"></head><body><nav class="course-nav">{nav}</nav><main class="wrap"><section class="hero"><h1>{title} · 认字与写字</h1><p>认字与写字分开学习：会认字重在读音、词语和字形；会写字逐字练真实笔顺与描红。</p><div class="toolbar"><button class="primary" onclick="playAll()">🔊 连续朗读</button><button id="pauseBtn" onclick="pauseSpeak()">⏸ 暂停</button><button onclick="stopSpeak()">⏹ 停止</button><label>语音 <select id="voiceSelect"></select></label><label>语速 <select id="rate"><option value=".75">慢</option><option value=".9" selected>适中</option><option value="1.05">稍快</option></select></label><button onclick="window.print()">🖨️ 打印写字练习</button></div></section>{body}</main>{modal if confirmed else ''}<script src="{assets}/hanzi-writer.min.js"></script><script src="{assets}/lesson.js"></script></body></html>'''
 (root/f'{key}.html').write_text(out)
for course,c in D['courses'].items():
 keys=list(c['lessons'])
 for i,k in enumerate(keys): page(course,k,c['lessons'][k],keys[i-1] if i else None,keys[i+1] if i+1<len(keys) else None)
