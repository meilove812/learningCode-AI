
'use strict';
(function () {
  function normalize(value) {
    return String(value).normalize('NFKC').toLowerCase().replace(/[’‘ʼ]/g, "'")
      .replace(/[‐‑–—−]/g, '-').trim().replace(/\s+/g, ' ').replace(/\s*-\s*/g, '-');
  }
  function judge(item, values) {
    if (!Array.isArray(values) || values.length !== item.answers.length) return false;
    return item.answers.every((accepted, i) => accepted.some(v => normalize(v) === normalize(values[i])));
  }
  function fresh(ids) { return {round:1, ids:[...ids], entries:{}, history:[], finished:false}; }
  function entry(state, id) {
    return state.entries[id] || (state.entries[id] = {values:[], result:null, hard:false, shown:false});
  }
  function advance(state, items) {
    if (state.finished) return state;
    const byId = new Map(items.map(i => [i.id, i]));
    const ids = state.ids.filter(id => {
      const e = state.entries[id];
      return !e || e.result !== true || !judge(byId.get(id), e.values) || e.hard;
    });
    const history = [...state.history, {round:state.round, ids:[...state.ids], entries:JSON.parse(JSON.stringify(state.entries))}];
    if (state.round >= 4 || ids.length === 0) return {...state, history, finished:true};
    const entries = {};
    for (const id of ids) entries[id] = {values:[], result:null, hard:!!state.entries[id]?.hard, shown:false};
    return {round:state.round+1, ids, entries, history, finished:false};
  }
  const core = {normalize, judge, fresh, entry, advance};
  if (typeof module !== 'undefined' && module.exports) module.exports = core;
  if (typeof document === 'undefined') return;
  const payload = document.getElementById('data');
  if (!payload) return;
  const data = JSON.parse(payload.textContent), items = data.items;
  const ids = items.map(i => i.id), map = new Map(items.map(i => [i.id, i]));
  const key = 'pu3-dictation-draft-v1-' + data.unit + '-' + data.version;
  const $ = id => document.getElementById(id);
  const storageNotice = $('storage');
  let state = fresh(ids);
  function validState(s) {
    return s && Number.isInteger(s.round) && s.round >= 1 && s.round <= 4 &&
      Array.isArray(s.ids) && new Set(s.ids).size === s.ids.length && s.ids.every(id => map.has(id)) &&
      s.entries && typeof s.entries === 'object' && Array.isArray(s.history) &&
      typeof s.finished === 'boolean' && Object.values(s.entries).every(e =>
        e && Array.isArray(e.values) && e.values.every(v => typeof v === 'string') &&
        [true,false,null].includes(e.result) && typeof e.hard === 'boolean' && typeof e.shown === 'boolean');
  }
  try {
    const saved = localStorage.getItem(key);
    if (saved) {
      const parsed = JSON.parse(saved);
      if (!validState(parsed)) throw new Error('invalid progress');
      state = parsed;
    }
  } catch (_) { storageNotice.textContent = '保存记录不可读取或已损坏。本次从第1轮开始；浏览器可能禁止本地存储。'; }
  function save() {
    try { localStorage.setItem(key, JSON.stringify(state)); }
    catch (_) { storageNotice.textContent = '本地保存失败（隐私模式、存储权限或容量限制）。当前可练习，但刷新后进度可能丢失。'; }
  }
  function el(tag, text, className) {
    const n = document.createElement(tag);
    if (text !== undefined) n.textContent = text;
    if (className) n.className = className;
    return n;
  }
  function button(text, fn) { const b = el('button', text); b.type = 'button'; b.addEventListener('click', fn); return b; }
  const speechAvailable = 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window;
  const synth = speechAvailable ? window.speechSynthesis : null;
  let voices = [], speechSerial = 0, speechTimer = null;
  function refreshVoices() {
    const previous = $('voice').value;
    voices = synth ? synth.getVoices().filter(v => /^en(?:-|_)/i.test(v.lang)) : [];
    $('voice').replaceChildren();
    voices.forEach((v,i) => { const o = el('option', v.name + ' · ' + v.lang); o.value = String(i); $('voice').append(o); });
    if (!voices.length) {
      const o = el('option', '无可用英文语音'); o.value = ''; $('voice').append(o);
      $('speech-status').textContent = speechAvailable ? '语音 API 存在，但没有可用英文声音。请安装英文语音或换支持语音的浏览器；可继续文字练习。' : '此浏览器不支持 Web Speech 朗读；可继续文字练习。';
    } else {
      const preferred = voices.findIndex(v => /Microsoft/i.test(v.name) && /Online.*Natural/i.test(v.name));
      $('voice').value = previous !== '' && voices[Number(previous)] ? previous : String(preferred < 0 ? 0 : preferred);
      $('speech-status').textContent = '检测到 ' + voices.length + ' 个英文声音；点击朗读后由设备播放（未保证离线可用）。';
    }
    $('voice').disabled = !voices.length;
    document.querySelectorAll('.speak').forEach(b => { b.disabled = !voices.length; });
  }
  function stopSpeech() { speechSerial++; clearTimeout(speechTimer); if (synth) synth.cancel(); }
  function speak(item) {
    if (!synth || !voices.length) { refreshVoices(); return; }
    stopSpeech(); const serial = speechSerial;
    const u = new SpeechSynthesisUtterance(item.answers.map(a => a[0]).join('. '));
    u.voice = voices[Number($('voice').value)] || voices[0]; u.lang = u.voice.lang; u.rate = Number($('rate').value);
    let started = false;
    u.addEventListener('start', () => { if(serial !== speechSerial) return; started = true; clearTimeout(speechTimer); $('speech-status').textContent = '正在请求设备朗读；是否有声请以实际听音为准。'; });
    u.addEventListener('end', () => { if(serial !== speechSerial) return; clearTimeout(speechTimer); $('speech-status').textContent = '设备报告朗读结束。'; });
    u.addEventListener('error', e => { if(serial !== speechSerial) return; clearTimeout(speechTimer); $('speech-status').textContent = '朗读失败：' + e.error + '。请换声音或检查系统语音设置。'; });
    $('speech-status').textContent = '等待语音服务…';
    speechTimer = setTimeout(() => { if(serial === speechSerial && !started) { stopSpeech(); $('speech-status').textContent = '语音服务未启动，不能确认可播放。请换声音或浏览器。'; } }, 8000);
    try { synth.speak(u); } catch (e) { stopSpeech(); $('speech-status').textContent = '朗读调用失败：' + e.message; }
  }
  function summary() {
    let correct = 0, wrong = 0, undone = 0, hard = 0;
    state.ids.forEach(id => { const e = entry(state,id); if(e.result === true) correct++; else if(e.result === false) wrong++; else undone++; if(e.hard) hard++; });
    $('summary').textContent = `第 ${state.round}/4 轮 · 本轮 ${state.ids.length} 题 · 正确 ${correct} · 错误 ${wrong} · 未做 ${undone} · 困难 ${hard}` + (state.finished ? ' · 本组练习已结束' : '');
    $('next').disabled = state.finished;
    $('submit-all').disabled = state.finished;
    $('next').textContent = state.round === 4 ? '结束第4轮' : '进入下一轮';
    $('round-log').textContent = state.history.map(h => `第${h.round}轮：${h.ids.length}题，判对${h.ids.filter(id => h.entries[id]?.result === true).length}题`).join('；');
  }
  function render() {
    $('cards').replaceChildren();
    for (const id of state.ids) {
      const item = map.get(id), e = entry(state,id), card = el('section', undefined, 'card' + (e.hard ? ' hard' : ''));
      card.append(el('div', `默写材料第 ${item.dictation_page} 页 · 第 ${item.row} 行 · 清单序号 ${item.order}`, 'meta'));
      card.append(el('h2', item.cn, 'prompt'));
      card.append(el('small', item.answers.length === 2 ? '动词变化题：分别写完整原形和过去式（短语也写完整）。' : '写完整英文词或短语；英美变体任选一种。'));
      const inputs = el('div', undefined, 'inputs'), fields = [];
      const status = el('p'); status.setAttribute('role','status');
      function updateStatus() { status.textContent = e.result === true ? '✓ 正确' : e.result === false ? '再试一次（可显答核对）' : '未提交'; status.className = e.result === true ? 'good' : 'bad'; }
      const answer = el('div', undefined, 'answer');
      answer.textContent = '参考答案：' + item.answers.map(a => a.join(' / ')).join(' → ') + '\n清单原词串：' + item.word + (item.ipa ? '\n音标：' + item.ipa : '');
      answer.hidden = !e.shown;
      item.answers.forEach((_,index) => {
        const label = el('label', item.answers.length === 2 ? (index === 0 ? '原形 / 完整短语' : '过去式 / 完整短语') : '英文答案');
        const input = el('input'); input.type = 'text'; input.autocomplete = 'off'; input.spellcheck = false;
        input.setAttribute('autocapitalize','none'); input.setAttribute('autocorrect','off'); input.value = e.values[index] || ''; input.disabled = state.finished;
        input.addEventListener('input', () => { e.values = fields.map(f => f.value); e.result = null; e.shown = false; answer.hidden = true; save(); updateStatus(); summary(); });
        input.addEventListener('keydown', event => { if(event.key === 'Enter' && !event.isComposing) { event.preventDefault(); submit(); } });
        label.append(input); inputs.append(label); fields.push(input);
      });
      function submit() { if(state.finished) return; e.values = fields.map(f => f.value); e.result = e.values.every(v => normalize(v)) ? judge(item,e.values) : null; save(); updateStatus(); summary(); }
      const actions = el('div', undefined, 'actions');
      const submitButton = button('提交本题',submit); submitButton.disabled = state.finished;
      const reveal = button(e.shown ? '隐藏答案' : '显示答案', () => { e.shown = !e.shown; answer.hidden = !e.shown; reveal.textContent = e.shown ? '隐藏答案' : '显示答案'; save(); });
      const difficult = button(e.hard ? '取消困难' : '标记困难', () => { if(state.finished) return; e.hard = !e.hard; difficult.textContent = e.hard ? '取消困难' : '标记困难'; difficult.setAttribute('aria-pressed', String(e.hard)); card.classList.toggle('hard',e.hard); save(); summary(); });
      difficult.setAttribute('aria-pressed', String(e.hard)); difficult.disabled = state.finished;
      const audio = button('朗读英文', () => speak(item)); audio.className = 'speak'; audio.disabled = !voices.length;
      actions.append(submitButton,reveal,difficult,audio);
      card.append(inputs,actions,status,answer); updateStatus(); $('cards').append(card);
    }
    summary();
  }
  $('submit-all').addEventListener('click', () => {
    state.ids.forEach(id => { const e = entry(state,id); e.result = e.values.length === map.get(id).answers.length && e.values.every(v => normalize(v)) ? judge(map.get(id),e.values) : null; });
    save(); render();
  });
  $('next').addEventListener('click', () => {
    if(state.finished) return;
    if(!window.confirm(state.round === 4 ? '结束第4轮？未做和错误将保留在本轮记录。' : '进入下一轮？仅保留错题、未提交题和困难题，旧输入与答案将隐藏。')) return;
    stopSpeech(); state = advance(state,items); save(); render(); window.scrollTo({top:0,behavior:'smooth'});
  });
  $('clear').addEventListener('click', () => {
    if(!window.confirm('确定清空本单元全部4轮答题记录和困难标记？其他单元不受影响。')) return;
    stopSpeech();
    try { localStorage.removeItem(key); } catch (_) { storageNotice.textContent = '无法删除本地保存记录；请在浏览器设置中清除本站数据。'; }
    state = fresh(ids); save(); render();
  });
  $('stop').addEventListener('click', () => { stopSpeech(); $('speech-status').textContent = '已停止朗读。'; });
  $('rate').addEventListener('input', () => { $('rate-value').textContent = $('rate').value + '×'; });
  $('voice').addEventListener('change', stopSpeech);
  window.addEventListener('pagehide', stopSpeech);
  if (synth) synth.addEventListener('voiceschanged', refreshVoices);
  refreshVoices(); render();
})();
