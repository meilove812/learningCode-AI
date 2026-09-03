#!/usr/bin/env python3
"""Static release gate for grade 1/2 Chinese writing cards."""
from pathlib import Path
import json,re,sys
ROOT=Path(__file__).resolve().parents[1]
PAGES=[ROOT/'grade1-down/chinese/writing-cards.html',*sorted((ROOT/'grade2-up/chinese/unit1').glob('lesson[123].html'))]
errors=[];cards=0
for p in PAGES:
 text=p.read_text(); tags=re.findall(r'<(?:button|article)[^>]*class="[^"]*(?:write-card|writing-card|hanzi-card)[^"]*"[^>]*>',text)
 if not tags: errors.append(f'{p.relative_to(ROOT)}: no writing cards')
 root=re.search(r'data-hanzi-root="([^"]+)"',text)
 data_root=(p.parent/(root.group(1) if root else 'assets/hanzi-data')).resolve()
 for tag in tags:
  cards+=1; cm=re.search(r'data-hanzi="([^"]+)"',tag); sm=re.search(r'data-strokes="([^"]+)"',tag); speak=re.search(r'data-speak="([^"]+)"',tag)
  if not cm or not sm or not speak: errors.append(f'{p.relative_to(ROOT)}: card missing data-hanzi/data-strokes/data-speak');continue
  ch=cm.group(1); names=[x for x in re.split('[、,，]',sm.group(1)) if x.strip()]; data=data_root/(ch+'.json')
  if not data.exists(): errors.append(f'{p.relative_to(ROOT)}: {ch} missing local JSON');continue
  try: count=len(json.loads(data.read_text())['strokes'])
  except Exception as e: errors.append(f'{p.relative_to(ROOT)}: {ch} invalid JSON: {e}');continue
  if count!=len(names): errors.append(f'{p.relative_to(ROOT)}: {ch} JSON {count} strokes != names {len(names)}')
  parts=speak.group(1).split('，'); py=parts[1] if len(parts)>1 else ''; neutral={'me','de','men','zhe','le','ma','ne','ba','a','la','ya','na','zi'}
  if not re.search(r'[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]',py) and py not in neutral: errors.append(f'{p.relative_to(ROOT)}: {ch} lacks tone-marked or standard-neutral pinyin in speech text')
 scripts='\n'.join((p.parent/src).resolve().read_text() for src in re.findall(r'<script src="([^"]+\.js)"',text) if (p.parent/src).resolve().exists())
 css='\n'.join((p.parent/src).resolve().read_text() for src in re.findall(r'<link[^>]+href="([^"]+\.css)"',text) if (p.parent/src).resolve().exists())
 for token in ('animateHanzi','pauseHanzi','replayHanzi','resetTrace','speechSynthesis','voiceschanged'):
  if token not in text+scripts: errors.append(f'{p.relative_to(ROOT)}: missing {token}')
 if not re.search(r'print-practice|class="practice"',text): errors.append(f'{p.relative_to(ROOT)}: missing printable practice')
 if '@media print' not in text+css: errors.append(f'{p.relative_to(ROOT)}: missing print CSS')
print(f'writing cards checked: {cards}; pages: {len(PAGES)}')
if errors: print('\n'.join('ERROR '+x for x in errors));sys.exit(1)
