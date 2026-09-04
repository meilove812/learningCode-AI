#!/usr/bin/env python3
import argparse, html, json, re, subprocess, datetime, urllib.request, urllib.error
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);ap.add_argument('--html',required=True)
ap.add_argument('--skip-net',action='store_true',help='跳过来源链接联网核验（仅离线自检，发布前不要用）')
a=ap.parse_args()
d=json.loads(Path(a.config).read_text(encoding='utf-8'));h=Path(a.html).read_text(encoding='utf-8')
errors=[]; slides=d.get('slides',[]); tts=''.join(x.get('tts','') for x in slides)
# 敏感/厂商扫描只针对会上屏的 slides；sources/thesis/derivation/taken_away 是溯源元数据，不渲染进页面
text=json.dumps(slides,ensure_ascii=False)
# 8 页：行动（怎么解决）与落款分离 —— 行动是观众唯一要带走的东西，不该和免责署名挤一屏。
if len(slides)!=8: errors.append(f'需要8页，当前{len(slides)}页')
if not 260<=len(tts)<=340: errors.append(f'旁白应为260-340字，当前{len(tts)}字')
for term in ['反制中国','中美博弈','脱钩','被入侵','被攻击','国家安全','军事情报','建议布局','目标价','\u6f9c\u7199','学校','班级','政治','政策','规划','法规','总统','部长']:
    if term in text: errors.append('敏感或隐私词：'+term)
for vendor in ['Gemini','Google','OpenAI','Anthropic','Claude','Amazon','NVIDIA','CrowdStrike','HiddenLayer','Wonderful','微软','谷歌','苹果','Meta']:
    if vendor.lower() in text.lower(): errors.append('出现厂商或产品名：'+vendor)

# ---- 演化链留痕：核心判断必须由某条来源的事实推出 ----
# 背景：技能第 2 步原先写「先定核心判断，再围绕它组织事实」，顺序是反的。
# 倒着做时，从通用原理推出的归因可能与实测数据相反，而成品页面看不出任何异常。
# thesis 写一句本期核心判断；derivation 写它由第几条来源的哪个事实推出。
thesis=(d.get('thesis') or '').strip()
deriv=(d.get('derivation') or '').strip()
if not thesis: errors.append('缺少 thesis：需写明本期唯一核心判断')
if not deriv: errors.append('缺少 derivation：需写明核心判断由第几条来源的哪个事实推出')

# ---- 首屏带入感：不许把结论直接砸给还不知道在说什么的观众 ----
# 背景：9/4 首版封面写「它不是不会 / 是不查」——「它」是谁、在干什么、跟观众什么关系，
# 首屏一字未交代，等于把内部黑话当标题。「开头3秒给结论」的前提是结论落在观众认得出的处境上；
# 否则那 3 秒观众只看到看不懂的字，反而划得更快。封面须四层递进：
# eyebrow=观众处境，title=问句式主标题，accent=核心判断，note=观众能带走什么。
cover=next((x for x in slides if x.get('kind')=='cover'),None)
if cover is None:
    errors.append('缺少 cover 页')
else:
    for f,desc in [('eyebrow','观众处境铺垫'),('title','问句式主标题'),('accent','核心判断'),('note','观众能带走什么')]:
        if not (cover.get(f) or '').strip(): errors.append(f'封面缺 {f}：需写{desc}')
    ct=(cover.get('title') or '').strip()
    for bad in ['它','这个','这','其','他','她','该']:
        if ct.startswith(bad): errors.append(f'封面标题以「{bad}」开头、无主语交代：'+ct); break

# ---- 反谄媚：每期必须点名一个确实被拿走的动作 ----
# 背景：选题链条落在「AI 和我有什么关系、该怎么做」，其最大失效模式是每期都得出
# 「人还是不可替代」——那是安慰剂，不是分析。点不出损失的一期即为奉承，应当重写。
# taken_away 写本期点名被拿走的具体动作：单位是动作，不是职业（没有职业被整体替代）。
taken=(d.get('taken_away') or '').strip()
if not taken:
    errors.append('缺少 taken_away：需点名本期「确实被拿走」的具体动作')
elif len(taken)<8:
    errors.append('taken_away 过短，需写清是哪个动作：'+taken)
else:
    for evade in ['无','没有','不存在','暂无','没什么','都没','不会被','取代不了','无法替代','不可替代']:
        if taken.startswith(evade) or taken.rstrip('。').endswith(evade):
            errors.append('taken_away 回避了损失（谄媚化），需点名具体被拿走的动作：'+taken); break
    for job in ['职业','岗位','工作岗位','程序员','老师','医生','律师','设计师']:
        if job in taken:
            errors.append(f'taken_away 的单位应是动作而非职业（出现「{job}」）：'+taken); break
    # 这一拍必须真的到达观众：9/4 首版 taken_away 只躺在元数据里，观众既看不到也听不到，
    # 关卡打了 PASS 但四拍在成品上是缺的。写了不等于给了，故校验它是否出现在上屏文字或旁白中。
    core=re.split(r'[——；;，,]', taken)[0].strip()
    core=re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]','',core)
    if core:
        # 负向测试发现的漏洞：只写「没被拿走的是…」也能命中「拿走」两字而通过，
        # 而那正是谄媚的那半边。先把否定式整体剔掉，再要求剩下的正面损失表述存在。
        aud=text
        for neg in ['没被拿走','没有被拿走','不被拿走','未被拿走','没拿走','不会被拿走','拿不走',
                    '没被接手','没被替掉','没被省掉','没被代劳','不被接手','不被替掉']:
            aud=aud.replace(neg,'')
        if not any(k in aud for k in ['拿走','接手','替掉','省掉','代劳']):
            errors.append('taken_away 未上屏：页面与旁白只说了「没被拿走」，缺正面点名损失的表述')
        bi={core[i:i+2] for i in range(len(core)-1)} or {core}
        hit={b for b in bi if b in text}
        if len(hit)<2 and core not in text:
            errors.append(f'taken_away 未上屏：核心词「{core}」在上屏文字与旁白中几乎不出现（命中 {len(hit)} 段）')

# ---- 结尾必须给「拿去就能用的一条」，且带刻度 ----
# 背景：04 页原先只给方法的形状（要设检查点），没给刻度（设多密），观众看完带不走确切动作。
# 行动页 action 写今天就能照做的事，必须含具体数字或一句观众能直接说出口的话（「」），否则等于口号。
act_pg=slides[6] if len(slides)==8 else {}
end=slides[7] if len(slides)==8 else {}
if act_pg.get('kind')!='action': errors.append(f"第7页应为独立行动页（kind=action），当前 {act_pg.get('kind')}")
if end.get('kind')!='ending': errors.append(f"第8页应为落款页（kind=ending），当前 {end.get('kind')}")
# 升级背景：原先 action 只是一句话（「把超过 10 步的活分成 3 段」），舵手指出「似乎不具体」——
# 一句话只能交代方法的形状，观众真去做会卡在「怎么数步／在哪切／每段交什么」。
# 现在要求：① 至少 3 步，逐步可执行；② 必须给一句观众能直接说出口的原话（action_script），
# 观众能复制粘贴的东西才叫拿得走。上屏措辞写观众要做的动作，不写作者的编辑用语——
# 「照抄」是命令观众抄，语气硬；「参考」是作者视角的编辑用语，观众不会说「我参考一下这句」。写成「你可以这么说」，观众一眼知道自己要做什么。
_raw=act_pg.get('action')
acts=[str(x).strip() for x in _raw if str(x).strip()] if isinstance(_raw,list) else (
    [_raw.strip()] if isinstance(_raw,str) and _raw.strip() else [])
if len(acts)<3:
    errors.append(f'action 需拆成至少 3 个可执行步骤（当前 {len(acts)} 步）：一句话只是方法的形状，不是能照做的动作')
for i,x in enumerate(acts,1):
    if len(x)<8:
        errors.append(f'action 步骤[{i}] 过短，写不出具体做法：'+x)
script=(act_pg.get('action_script') or '').strip()
if not script:
    errors.append('缺 action_script：需给一句观众能直接说出口的原话（用「」括起）')
elif not ('「' in script and '」' in script):
    errors.append('action_script 必须把那句原话用「」括起，观众才知道用哪一段：'+script)
elif len(re.search(r'「(.*?)」',script).group(1))<12:
    errors.append('action_script 里「」中的话太短，照着说也不管用：'+script)
act=' '.join(acts)
if not act:
    errors.append('落版页缺 action：需给一条今天就能照做的具体动作')
# 负向测试发现的漏洞：把中文数字算作刻度时，「多核对一下」的「一」也会命中而放行。
# 中文数字大量出现在「一下／一些／一点／十分」这类虚词里，不能作为刻度证据。
# 只认阿拉伯数字或可直接说出口的句式；顺带逼出更适合上屏扫读的写法。
elif not (re.search(r'[0-9０-９]', act) or ('「' in act and '」' in act)):
    errors.append('action 缺刻度：需含具体数字，或给出一句观众能直接说出口的话（用「」括起）：'+act)
else:
    for vague in ['注意','重视','关注一下','保持','养成习惯','多加','适当']:
        if act.startswith(vague):
            errors.append(f'action 是口号不是动作（以「{vague}」开头）：'+act); break

# ---- 来源硬约束：没有已核验的外部依据就不许发 ----
# 背景：2026-08-31 起 web_search 长期不可用，9/1 之后连续多期在零外部事实下凭原理成稿，
# 而当时的校验器只查敏感词和 HTML，每次都打印 PASS。这一段是唯一拦得住该情况的关卡。
# 不要为了让 build 通过而放宽阈值或加 --skip-net，宁可当天不发。
sources=d.get('sources')
if not isinstance(sources,list) or len(sources)<1:
    errors.append('缺少 sources 字段：每期至少 1 条已核验外部来源')
else:
    m=re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', d.get('date',''))
    ep_date=datetime.date(int(m.group(1)),int(m.group(2)),int(m.group(3))) if m else None
    for i,s in enumerate(sources,1):
        if not isinstance(s,dict): errors.append(f'sources[{i}] 不是对象'); continue
        title=(s.get('title') or '').strip(); url=(s.get('url') or '').strip(); sdate=(s.get('date') or '').strip()
        if not title: errors.append(f'sources[{i}] 缺 title')
        for p in ['\u6f9c\u7199','学校','班级']:
            if p in title: errors.append(f'sources[{i}] 标题含隐私词：'+p)
        if not url.startswith('https://'): errors.append(f'sources[{i}] url 必须为 https：'+(url or '(空)'))
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', sdate):
            errors.append(f'sources[{i}] date 必须是 YYYY-MM-DD：'+(sdate or '(空)'))
        elif ep_date:
            gap=(ep_date-datetime.date(*map(int,sdate.split('-')))).days
            if gap<0: errors.append(f'sources[{i}] 来源日期晚于本期日期')
            elif gap>30: errors.append(f'sources[{i}] 来源过时：距本期 {gap} 天，上限 30')
        if url.startswith('https://') and not a.skip_net:
            try:
                req=urllib.request.Request(url,method='HEAD',headers={'User-Agent':'ai-insight-checker'})
                code=urllib.request.urlopen(req,timeout=15).status
            except urllib.error.HTTPError as e: code=e.code
            except Exception as e: code='ERR '+type(e).__name__
            if code!=200: errors.append(f'sources[{i}] 链接不可达（{code}）：'+url)
    # derivation 必须指向真实存在的来源编号，不能空口说「据某研究」
    if deriv and not any(1<=n<=len(sources) for n in (int(x) for x in re.findall(r'\d+',deriv))):
        errors.append(f'derivation 未引用有效来源编号（当前 {len(sources)} 条来源）')

# ---- 上屏数字必须能追到原文引文，引文必须逐字存在于线上页面 ----
# 背景：原有关卡只验来源「存在且可达」，不验「我写的数字是否与原文一致」。
# 来源真、链接通、日期对，但数字写错或断章取义，17 道关卡会全部放行 —— 这是内容错误里最致命的一类。
# 设计：每条 sources 带 quotes（原文片段），校验 quote 逐字出现在抓取页面；
# 上屏的小数／百分数／区间必须能在 quotes 里找到。跨语言表述做归一化：
# 原文 "every 30 to 75 turns" 与上屏「30–75 回合」等价，故 to／–／—／- 统一成 -。
def _norm(t):
    t=re.sub(r'\s+to\s+','-',t)
    t=re.sub(r'[–—~]','-',t)
    return re.sub(r'\s+','',t)

allq=[]
for i,s in enumerate(d.get('sources') or [],1):
    qs=[q for q in (s.get('quotes') or []) if isinstance(q,str) and q.strip()]
    if not qs:
        errors.append(f'sources[{i}] 缺 quotes：需摘原文片段，否则数字无从核对'); continue
    for j,q in enumerate(qs,1):
        if len(q.strip())<30:
            errors.append(f'sources[{i}].quotes[{j}] 过短（<30 字符），不足以定位原文：'+q.strip())
        allq.append(q)
    if not a.skip_net:
        try:
            rq=urllib.request.Request(s['url'],headers={'User-Agent':'Mozilla/5.0'})
            raw=urllib.request.urlopen(rq,timeout=25).read().decode('utf-8','ignore')
            page=_norm(html.unescape(re.sub(r'<[^>]+>',' ',raw)))
        except Exception as e:
            errors.append(f'sources[{i}] 抓取失败，无法核对引文：{e}'); page=None
        if page:
            for j,q in enumerate(qs,1):
                if _norm(q) not in page:
                    errors.append(f'sources[{i}].quotes[{j}] 在线上页面中查不到（引文与原文不符）：'+q.strip()[:60])

# 上屏精确数字必须有引文支撑（只查小数／百分数／区间：这类几乎只来自研究；
# 整数常是本期自拟的建议刻度，如「每 10 回合」，不在此列）
qn=_norm(' '.join(allq))
onscreen=json.dumps(slides[1:7],ensure_ascii=False) if len(slides)==8 else ''
for n in sorted(set(re.findall(r'\d+\.\d+%?|\d+%|\d+\s*[–—-]\s*\d+', onscreen))):
    if _norm(n) not in qn:
        errors.append(f'上屏数字「{n}」在 quotes 中找不到出处（可能写错或断章取义）')

# ---- 这期值不值得讲：观众必须能拿它改一个决定 ----
# 背景：56 条关卡全在管形式（页数、时长、措辞、来源、数字溯源），没有一条管价值。
# 一期同义反复、无关痛痒的片子可以全绿 PASS。选题价值本身机器判不了，
# 但「有没有想清楚给观众换掉哪个决定」可以判：逼一句 decision 出来，写不出就是没想清楚。
# 判据：观众看完会改一个决定，而不是多懂一个概念。学到概念不算，行为要变。
dec=(d.get('decision') or '').strip()
if not dec:
    errors.append('缺少 decision：一句话写明观众看完会改哪个决定（不是学到什么概念）')
elif not (12 <= len(dec) <= 44):
    errors.append(f'decision 长度 {len(dec)} 字，需 12–44 字：太短说不清，太长说明没想清楚：'+dec)
else:
    for vague in ['认知','理解','意识到','了解','学会','掌握','思考','视野','格局','启发']:
        if vague in dec:
            errors.append(f'decision 落在「{vague}」上——那是多懂一个概念，不是改一个决定：'+dec); break
    else:
        # 与 taken_away 同理：写了不等于给了。这个决定的核心词必须真的到达观众。
        import re as _re
        cand=[w for w in _re.split(r'[，。、：；「」,\s]+', dec) if len(w)>=2]
        reach=' '.join((x.get('title') or '')+' '+str(x.get('body') or '')+' '+(x.get('tts') or '') for x in slides)
        if not any(w in reach for w in cand):
            errors.append('decision 只躺在元数据里：这个决定的说法在上屏文字与旁白中都找不到：'+dec)

# ---- 上屏措辞必须是观众要做的动作，不是作者的编辑用语 ----
# 背景：行动页引导语先写「照抄这句」（命令观众抄，语气硬），改成「参考这么说」仍然不对——
# 「参考」是作者处理素材时的词（参考资料、仅供参考），观众不会说「我参考一下这句」，
# 他要知道的是自己该怎么说。终稿写成「你可以这么说」，主语是观众，动词是他真会做的动作。
# 自检法：把这句话放进观众嘴里念一遍，念不顺就是作者视角残留。
# 只扫封面到行动页（slides[0:7]）：落款页的「仅供参考」是法律套话，属正当例外。
EDITORIAL = ['参考', '详见', '如下', '本期', '敬请', '如上', '请见', '综上所述', '建议']
_screen_keys = ('eyebrow','title','accent','note','body','metric','result','action_script','label','value','name')
def _screen_text(o):
    out=[]
    if isinstance(o,dict):
        for k,v in o.items():
            if k in ('tts','quotes','url','date'): continue
            if k in _screen_keys or isinstance(v,(dict,list)): out.append(_screen_text(v))
    elif isinstance(o,list):
        for v in o: out.append(_screen_text(v))
    elif isinstance(o,str): out.append(o)
    return ' '.join(x for x in out if x)
if len(slides)==8:
    for i,s_ in enumerate(slides[:7]):
        txt=_screen_text(s_)
        for w in EDITORIAL:
            if w in txt:
                errors.append(f'上屏[{i}] 用了作者的编辑用语「{w}」，观众念不出这句话：改写成他要做的动作（如「你可以这么说」）')
                break

# ---- 观众看到的来源必须就是被核验过的那一条 ----
# 背景：9/3 顶层 sources 已核验 HTTP 200，但落版页 sources 是空的，观众看不到任何出处；
# 9/4 展示了却与顶层各写一套，两边可以静默漂移。核验的和展示的必须是同一条。
disp=(slides[7].get('sources') if len(slides)==8 else None) or []
vurls={(x.get('url') or '').strip() for x in (d.get('sources') or []) if isinstance(x,dict)}
if not disp:
    errors.append('落版页未展示来源：观众看不到出处')
for i,x in enumerate(disp,1):
    if not isinstance(x,dict): errors.append(f'落版页来源[{i}] 不是对象'); continue
    u=(x.get('url') or '').strip(); n=(x.get('name') or '').strip()
    if u not in vurls:
        errors.append(f'落版页来源[{i}] 不在已核验 sources 中（展示与核验漂移）：'+(u or '(空)'))
    if len(n)<6:
        errors.append(f'落版页来源[{i}] 名称太短，观众看不出那是什么：'+(n or '(空)'))

for forbidden in ['http://','https://fonts.','<script src=','localStorage','sessionStorage','document.cookie','fetch(']:
    if forbidden in h: errors.append('禁用远程依赖/存储：'+forbidden)
for marker in ['speechSynthesis','onvoiceschanged','data-start','id="rate"','id="replay"','class="track"']:
    if marker not in h: errors.append('缺少功能：'+marker)
if h.count('<section class="slide ')!=8: errors.append('HTML slide数量不为8')
if not h.rstrip().endswith('</html>'): errors.append('HTML结尾不完整')
scripts=re.findall(r'<script>(.*?)</script>',h,re.S)
for i,s in enumerate(scripts):
    p=Path('/tmp')/f'check-video-{i}.js';p.write_text(s,encoding='utf-8')
    r=subprocess.run(['node','--check',str(p)],capture_output=True,text=True)
    if r.returncode: errors.append('JavaScript语法错误：'+r.stderr.strip())
# 除来源外，只应围绕同一事件
joined=' '.join(x.get('title','')+' '+x.get('body','')+' '+x.get('tts','') for x in slides)
for off_topic in ['融资','估值','漏洞','涨价','风险']:
    if off_topic in joined: errors.append('出现离题或易误解表达：'+off_topic)
# ---- 旁白必须是说给观众听的，不是念给页面看的 ----
# 背景：9/4 趋势版首版七段旁白里，五段没有第二人称，三段在念页面标签（「趋势是这样」「今日判断：」
# 「本期依据……」）。观众听到的是结构说明，不是对他说的话。视频号是听觉先行的场子，
# 上屏文字可以是标签，旁白不行。三条硬约束：不念标签、观众必须在场、不写念不出来的字形。
for i,s in enumerate(slides):
    t=(s.get('tts') or '')
    for w in ['趋势是这样','今日判断','本期依据','怎么拆分','这一页','如下','以下几','第一部分','小结','综上','接下来我们']:
        if w in t:
            errors.append(f'旁白[{i}] 在念页面标签「{w}」，观众不需要听结构：'+t[:22]); break
# 观众必须在场。负向测试证明「用户／大家／我们」都能绕过这条——那是在谈论观众，不是在对他说话，
# 所以只认第二人称「你」，且至少 3 段命中，避免只在某一页贴一个「你」就放行。
you_hits=[i for i,s in enumerate(slides) if '你' in (s.get('tts') or '')]
if len(you_hits)<3:
    errors.append(f'旁白没在跟观众说话：仅 {len(you_hits)} 段出现第二人称「你」，至少 3 段')
# ---- 旁白主语：观众得知道「它」是谁 ----
# 背景：2026-09-04 舵手反馈 9/5 期「没有带入感，直接就说 AI，观众要能很明白」。
# 当期旁白 8 段 14 处「它」，从第一句「让它把活复查一遍」起全篇没有先行词。
# 既有关卡只拦封面标题以「它」开头（9/4 教训），旁白正文无人管。
# 上屏可以直接写「AI」（落版就叫「今日AI洞察」）；旁白受拉丁字母关卡约束，
# 故要求旁白用中文具名（人工智能／模型／工具／助手），具名之后代词才成立。
_NAMES = ('AI', '人工智能', '模型', '工具', '助手')
_t0 = (slides[0].get('tts') or '') if slides else ''
if not any(n in _t0 for n in _NAMES):
    errors.append('旁白[0] 没具名交代主语，观众不知道在说谁：第一句就点名「AI」：' + _t0[:22])
# 2026-09-05 舵手第二次反馈：解说词里还有「它」，观众听不懂 —— 听觉媒介没法回头看，
# 首句点名不够，每处都要点名。故旁白一处「它」都不许有，一律写 AI。
# 只禁「它」：「他」「其」会落在「其他」「其实」里误报，反而逼出更差的改写。
for _i, _s in enumerate(slides):
    _t = (_s.get('tts') or '')
    if '它' in _t:
        errors.append(f'旁白[{_i}] 用了代词「它」×{_t.count("它")}，听众分不清指谁，改成 AI：' + _t[:22])

# 念不出来的字形：参数量后缀、英文词、括号注释、超长不换气句，朗读出来全是噪音。
for i,s in enumerate(slides):
    t=(s.get('tts') or '')
    # 负向测试教训：原先分两条查「阿拉伯数字+B/M/K」和「≥2 个连续英文字母」，
    # 反例「六百七十一B」用中文数字前缀 + 单个字母，两条都绕过去了。
    # 2026-09-05 舵手：「AI 名词讲解也用 AI」——口播就念 AI，观众最熟这两个字母。
    # 原先全拦造成的后果：写稿只能退回「它」，9/5 期旁白 14 处代词全篇无先行词。
    # 所以白名单只放 AI 一个词；剔除后仍有拉丁字母照拦（型号 GPT、参数后缀 671B、编号 v2）。
    _t_res = t.replace('AI', '')
    if re.search(r'[A-Za-z]', _t_res):
        errors.append(f'旁白[{i}] 含 AI 之外的拉丁字母（型号／参数后缀／编号），朗读念不出来，改中文说法：'+t[:22])
    if '（' in t or '(' in t:
        errors.append(f'旁白[{i}] 含括号注释，朗读读不出层次：'+t[:22])
    longest=max((len(x) for x in re.split(r'[，。：；？！、]', t)), default=0)
    if longest>26:
        errors.append(f'旁白[{i}] 有 {longest} 字长句不换气，听不动：'+t[:22])

if errors:
    print('\n'.join('FAIL: '+x for x in errors));raise SystemExit(1)
sec=len(tts)/4.2
nsrc=len(d.get('sources') or [])
print(f'PASS: slides=8; tts_chars={len(tts)}; estimated={sec:.0f}s; single-topic; sources={nsrc} ({"skipped" if a.skip_net else "HTTP200"}); cover 4-layer; taken_away named; thesis+derivation traced; sensitive/privacy/dependency/HTML/JS checks passed')
