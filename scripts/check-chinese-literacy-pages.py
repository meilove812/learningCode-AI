#!/usr/bin/env python3
from pathlib import Path
import json,re,sys
R=Path(__file__).resolve().parents[1]; M=json.loads((R/'data/chinese-lesson-character-map.json').read_text()); errors=[]
tone=re.compile(r'[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]')
for course,cdata in M['courses'].items():
 base=R/('grade2-up/chinese/unit1' if course=='grade2-up' else 'grade1-down/chinese/lessons')
 for key,info in cdata['lessons'].items():
  p=base/(key+'.html'); text=p.read_text() if p.exists() else ''
  rec=re.findall(r'<button class="recognition-card"[^>]*data-recognition="([^"]+)"[^>]*data-speak="([^"]+)"',text)
  wr=re.findall(r'<article class="writing-card"[^>]*data-hanzi="([^"]+)"[^>]*data-strokes="([^"]+)"[^>]*data-speak="([^"]+)"',text)
  er=[x[0] for x in info['recognition']]; ew=[x[0] for x in info['writing']]
  if [x[0] for x in rec]!=er: errors.append(f'{p}: recognition set/order mismatch')
  if [x[0] for x in wr]!=ew: errors.append(f'{p}: writing set/order mismatch')
  if len(rec)!=len(er) or len(wr)!=len(ew): errors.append(f'{p}: count mismatch')
  neutral={'me','de','le','ma','ne','ba','a','zhe','guo'}
  for ch,s in rec:
   parts=s.split('，'); py=parts[1] if len(parts)>1 else ''
   if (not tone.search(py) and py not in neutral) or len(parts)<3 or not parts[2]: errors.append(f'{p}: recognition {ch} lacks tone-marked/standard-neutral pinyin or word')
  if rec and ('playRecognition' not in text or '连续朗读' not in text): errors.append(f'{p}: recognition group speech missing')
  scripts=''.join((p.parent/src).read_text() for src in re.findall(r'<script src="([^"]+\.js)"',text) if (p.parent/src).exists())
  for ch,st,s in wr:
   data=p.parent/'assets/hanzi-data'/f'{ch}.json'
   if not data.exists(): errors.append(f'{p}: {ch} local stroke JSON missing'); continue
   n=len(json.loads(data.read_text())['strokes']); names=[x for x in st.split('、') if x]
   if n!=len(names): errors.append(f'{p}: {ch} stroke count {n}!={len(names)}')
   if not tone.search(s) or s.count('，')<2: errors.append(f'{p}: writing {ch} lacks tone pinyin/word')
  for token in ('animateHanzi','pauseHanzi','replayHanzi','resetTrace','speechSynthesis','voiceschanged'):
   if wr and token not in text+scripts: errors.append(f'{p}: missing {token}')
  for token in ('print-practice','practice','笔顺：','window.print'):
   if wr and token not in text: errors.append(f'{p}: missing {token}')
  if set(er)&set(ew): pass # overlap can legitimately be both required sets
  print(f'{course}/{key}: recognition={len(rec)} writing={len(wr)}')
if errors: print('\n'.join('ERROR '+x for x in errors));sys.exit(1)
print('Chinese lesson literacy checks passed.')
