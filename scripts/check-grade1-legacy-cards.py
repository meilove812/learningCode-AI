#!/usr/bin/env python3
"""Release gate: old grade-1 cards must be completely represented and locally runnable."""
from pathlib import Path
import json,re,sys
R=Path(__file__).resolve().parents[1]; D=json.loads((R/'grade1-down/chinese/data/legacy-grade1-cards.json').read_text()); S=json.loads((R/'grade1-down/chinese/data/stroke-shapes.json').read_text()); errors=[]
tone=re.compile(r'[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]'); neutral={'a','ba','de','guo','la','le','ma','me','men','na','ne','ya','zhe','zi'}
for kind in ('recognition','writing'):
 p=R/f'grade1-down/chinese/{kind}-cards.html'; text=p.read_text(); src=D[kind]['pages']
 cards=re.findall(r'class="legacy-rec-card"[^>]*data-char="([^"]+)"[^>]*data-speak="([^"]+)"',text) if kind=='recognition' else re.findall(r'class="legacy-write-card"[^>]*data-hanzi="([^"]+)"[^>]*data-strokes="([^"]+)"[^>]*data-speak="([^"]+)"',text)
 expected=[r for page in src for r in page['records']]; got=[x[0] for x in cards]
 if got!=[r['char'] for r in expected]: errors.append(f'{kind}: character record/order mismatch')
 if len(cards)!=D[kind]['recordCount']: errors.append(f'{kind}: {len(cards)} records != {D[kind]["recordCount"]}')
 if len(set(got))!=D[kind]['uniqueCount']: errors.append(f'{kind}: unique count mismatch')
 for i,(r,c) in enumerate(zip(expected,cards)):
  speak=c[-1]; parts=speak.split('，')
  if len(parts)<3 or parts[1]!=r['pinyin'] or parts[2]!=r['word']: errors.append(f'{kind}[{i}] {r["char"]}: pinyin/word changed')
  if not tone.search(r['pinyin']) and r['pinyin'] not in neutral: errors.append(f'{kind}[{i}] {r["char"]}: unmarked pinyin {r["pinyin"]}')
  if kind=='writing':
   ch=c[0]; names=c[1].split('、'); data=R/f'grade1-down/chinese/assets/hanzi-data/{ch}.json'
   if not data.exists(): errors.append(f'writing {ch}: local JSON missing'); continue
   count=len(json.loads(data.read_text())['strokes'])
   if count!=len(names) or count!=len(S[ch]): errors.append(f'writing {ch}: JSON={count}, description={len(names)}, source={len(S[ch])}')
 for ui,page in enumerate(src,1):
  for gi,g in enumerate(page['groups'],1):
   if f'id="u{ui}-g{gi}"' not in text: errors.append(f'{kind}: missing group u{ui}-g{gi}')
 print(f'{kind}: records={len(cards)}, unique={len(set(got))}, units={len(src)}, groups={sum(len(x["groups"]) for x in src)}')
js=(R/'grade1-down/chinese/assets/legacy-cards.js').read_text(); css=(R/'grade1-down/chinese/assets/legacy-cards.css').read_text()
for token in ('playAll','playGroup','voiceSelect','voiceschanged','animateHanzi','pauseHanzi','replayHanzi','resetTrace','charDataLoader'):
 if token not in js: errors.append('JS missing '+token)
for token in ('@media print','trace-glyph','print-grid','tian-grid'):
 if token not in css: errors.append('CSS missing '+token)
for p in (R/'grade1-down/chinese').glob('*.html'):
 for link in re.findall(r'(?:href|src)="([^"]+)"',p.read_text()):
  if re.match(r'^(?:https?:|#|data:|mailto:)',link):
   if link.startswith('http'): errors.append(f'{p.name}: remote runtime dependency {link}')
   continue
  q=(p.parent/link.split('#')[0]).resolve()
  if link and not q.exists(): errors.append(f'{p.name}: broken link {link}')
if errors: print('\n'.join('ERROR '+e for e in errors));sys.exit(1)
print('missing=0; extra=0; changed pinyin/word=0; local resources and links passed.')
