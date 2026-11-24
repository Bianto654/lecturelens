from __future__ import annotations

import json
import streamlit.components.v1 as components

KATEX_HEAD = """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.21/dist/katex.min.css" crossorigin="anonymous">
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.21/dist/katex.min.js" crossorigin="anonymous"></script>
"""

SHARED_STYLES = """
<style>
  :root {
    --bg: #ffffff;
    --panel: #f8fafc;
    --border: #e2e8f0;
    --text: #0f172a;
    --muted: #475569;
    --brand: #1549c7;
    --brand-soft: #e0ecff;
    --formula-bg: #f0fdfa;
    --formula-border: #14b8a6;
    --unclear-bg: #fef3c7;
    --unclear-text: #92400e;
  }
  body.dark {
    --bg: #020617;
    --panel: #0f172a;
    --border: #1e293b;
    --text: #f8fafc;
    --muted: #94a3b8;
    --brand: #60a5fa;
    --brand-soft: #1e3a8a;
    --formula-bg: #042f2e;
    --formula-border: #2dd4bf;
    --unclear-bg: #451a03;
    --unclear-text: #fde68a;
  }
  * { box-sizing: border-box; font-family: Inter, system-ui, -apple-system, sans-serif; }
  body { margin: 0; background: var(--bg); color: var(--text); }
  .card {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 18px;
    overflow: hidden;
  }
  .toolbar {
    display: flex; flex-wrap: wrap; gap: 8px; align-items: center; justify-content: space-between;
    padding: 12px 14px; background: var(--panel); border-bottom: 1px solid var(--border);
  }
  .badge {
    display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px;
    border-radius: 999px; font-size: 12px; font-weight: 700;
  }
  .badge-ok { background: #dcfce7; color: #14532d; }
  .badge-warn { background: #fef3c7; color: #78350f; }
  .badge-err { background: #ffe4e6; color: #881337; }
  .badge-brand { background: var(--brand-soft); color: var(--brand); }
  .btn {
    min-height: 44px; min-width: 44px; padding: 8px 14px; border-radius: 12px;
    border: 1px solid var(--border); background: var(--bg); color: var(--text);
    font-size: 13px; font-weight: 700; cursor: pointer; display: inline-flex;
    align-items: center; justify-content: center; gap: 6px;
  }
  .btn:hover { opacity: 0.92; }
  .btn-primary { background: #1549c7; color: #fff; border-color: #1549c7; }
  .btn-green { background: #047857; color: #fff; border-color: #047857; }
  .btn-amber { background: #d97706; color: #fff; border-color: #d97706; }
  .btn-red { background: #be123c; color: #fff; border-color: #be123c; }
  .stream {
    height: 410px; overflow-y: auto; padding: 18px; display: flex; flex-direction: column;
    gap: 14px; scroll-behavior: smooth;
  }
  .cap-item {
    padding: 12px 14px; border-radius: 14px; background: var(--panel);
    border: 1px solid var(--border); line-height: 1.65;
  }
  .cap-meta {
    display: flex; justify-content: space-between; align-items: center;
    font-size: 11px; color: var(--muted); margin-bottom: 4px; font-family: monospace;
  }
  .glossary-chip {
    display: inline; padding: 2px 6px; border-radius: 6px;
    background: var(--brand-soft); border-bottom: 2px solid var(--brand); font-weight: 600;
  }
  .formula-chip {
    display: inline-flex; flex-wrap: wrap; align-items: center; gap: 6px;
    padding: 3px 9px; margin: 2px 4px; border-radius: 10px;
    background: var(--formula-bg); border: 1px solid var(--formula-border);
    vertical-align: middle;
  }
  .formula-orig { font-size: 0.78em; font-style: italic; color: var(--muted); }
  .auto-tag {
    font-size: 0.65em; font-weight: 800; text-transform: uppercase;
    padding: 2px 7px; border-radius: 999px; background: #0f766e; color: #fff;
  }
  .unclear-tag {
    display: inline-block; padding: 2px 7px; border-radius: 6px;
    background: var(--unclear-bg); color: var(--unclear-text); font-weight: 700; font-size: 0.85em;
  }
  .meter-wrap {
    height: 12px; border-radius: 999px; background: var(--border); overflow: hidden; margin-top: 6px;
  }
  .meter-fill { height: 100%; width: 0%; background: linear-gradient(90deg, #10b981, #f59e0b, #ef4444); transition: width 80ms; }
  .interim-box {
    padding: 10px 14px; border-radius: 12px; border: 2px dashed var(--brand);
    font-style: italic; color: var(--muted);
  }
  select, input[type="text"] {
    min-height: 44px; padding: 8px 12px; border-radius: 12px;
    border: 1px solid var(--border); background: var(--bg); color: var(--text); font-size: 14px;
  }
  .bk-btn {
    border: 1px solid var(--border); background: transparent; color: var(--muted);
    border-radius: 8px; padding: 3px 8px; font-size: 12px; cursor: pointer; font-weight: 700;
  }
  .bk-btn.saved { background: #fef08a; color: #713f12; border-color: #eab308; }
</style>
"""

SHARED_RENDER_JS = """
function escHtml(s) {
  return String(s || '').replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

function renderLatex(latex) {
  try {
    if (window.katex) {
      return window.katex.renderToString(latex, { throwOnError: false, strict: 'ignore' });
    }
  } catch (e) {}
  return '<code>' + escHtml(latex) + '</code>';
}

function renderSegmentsHtml(cap, autoLabel) {
  const segs = Array.isArray(cap.segments) && cap.segments.length
    ? cap.segments
    : [{ type: 'text', text: cap.processed_text || cap.raw_text || '' }];
  return segs.map(seg => {
    if (seg.type === 'text') return escHtml(seg.text);
    if (seg.type === 'glossary') {
      const tip = seg.was_corrected ? ' title="Matched from: ' + escHtml(seg.original) + '"' : '';
      return '<span class="glossary-chip"' + tip + '>' + escHtml(seg.matched_term || seg.text) + '</span>';
    }
    if (seg.type === 'unclear') {
      return '<span class="unclear-tag">[unclear]</span>';
    }
    if (seg.type === 'formula') {
      return '<span class="formula-chip">'
        + '<span class="formula-orig">&ldquo;' + escHtml(seg.original_text) + '&rdquo;</span>'
        + '<span>&rarr;</span>'
        + '<span>' + renderLatex(seg.latex) + '</span>'
        + '<span class="auto-tag">' + escHtml(autoLabel) + '</span>'
        + '</span>';
    }
    return escHtml(seg.text || '');
  }).join('');
}

function fmtTime(tsMs) {
  try {
    return new Date(tsMs).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch (e) { return ''; }
}
"""


def render_host_live_console(
    session: dict,
    ws_base_url: str,
    http_base_url: str,
    ui_lang: str = "id",
) -> None:
    """
    Mobile-first live Host console embedded in Streamlit.
    Streams either:
      - 16kHz PCM16 audio frames over WebSockets to FastAPI -> Faster-Whisper + Silero VAD
      - Fast browser Web Speech text frames -> FastAPI -> Gemini Flash + Math Engine
      - Built-in Mock Lecture Simulator or manual test input
    """
    is_id = ui_lang == "id"
    cfg = {
        "sessionId": session["id"],
        "language": session["language"],
        "wsUrl": f"{ws_base_url}/ws/host/{session['id']}",
        "httpUrl": http_base_url,
        "autoLabel": "otomatis" if is_id else "automatic",
        "isId": is_id,
    }

    html = f"""<!doctype html>
<html><head><meta charset="utf-8">{KATEX_HEAD}{SHARED_STYLES}</head>
<body>
<div class="card">
  <div class="toolbar">
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
      <span id="connBadge" class="badge badge-warn">Menghubungkan...</span>
      <span id="stuBadge" class="badge badge-brand">0 {'mahasiswa' if is_id else 'students'}</span>
      <span id="statusBadge" class="badge badge-ok">{session['status'].upper()}</span>
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;">
      <select id="engineSelect" aria-label="STT Engine">
        <option value="whisper_ws">{'Faster-Whisper + Silero VAD (Backend WS)' if is_id else 'Faster-Whisper + Silero VAD (Backend WS)'}</option>
        <option value="webspeech">{'Web Speech Cepat -> Gemini Backend' if is_id else 'Fast Web Speech -> Gemini Backend'}</option>
        <option value="mock">{'Simulasi Kuliah (Mock)' if is_id else 'Lecture Simulator (Mock)'}</option>
      </select>
      <select id="micSelect" aria-label="Microphone">
        <option value="">{'Mikrofon Bawaan' if is_id else 'Default Microphone'}</option>
      </select>
    </div>
  </div>

  <div style="padding:12px 14px;border-bottom:1px solid var(--border);background:var(--panel);">
    <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;">
      <button id="btnStart" class="btn btn-green" type="button">▶ {'Mulai Transkripsi' if is_id else 'Start Captioning'}</button>
      <button id="btnPause" class="btn btn-amber" type="button" style="display:none;">⏸ {'Jeda' if is_id else 'Pause'}</button>
      <button id="btnResume" class="btn btn-green" type="button" style="display:none;">▶ {'Lanjutkan' if is_id else 'Resume'}</button>
      <button id="btnDemoOne" class="btn" type="button">✨ {'Kirim 1 Baris Demo' if is_id else 'Send 1 Demo Line'}</button>
      <button id="btnEnd" class="btn btn-red" type="button">■ {'Akhiri Sesi' if is_id else 'End Session'}</button>
    </div>
    <div style="margin-top:10px;display:flex;align-items:center;gap:10px;font-size:12px;color:var(--muted);">
      <span>🎤 {'Level Input Suara' if is_id else 'Input Level'}</span>
      <span id="levelPct" style="font-family:monospace;">0%</span>
    </div>
    <div class="meter-wrap"><div id="meterFill" class="meter-fill"></div></div>
    <div id="errBox" style="display:none;margin-top:8px;padding:8px 12px;border-radius:10px;background:#ffe4e6;color:#881337;font-size:12px;font-weight:700;"></div>
  </div>

  <div id="stream" class="stream" aria-live="polite">
    <div id="emptyMsg" style="margin:auto;color:var(--muted);text-align:center;font-size:14px;">
      {'Tekan Mulai Transkripsi, kirim 1 baris demo, atau ketik kalimat uji di bawah.' if is_id else 'Press Start Captioning, send a demo line, or type a test utterance below.'}
    </div>
  </div>

  <form id="manualForm" style="display:flex;gap:8px;padding:12px 14px;border-top:1px solid var(--border);background:var(--panel);">
    <input id="manualInput" type="text" style="flex:1;"
      placeholder="{'Ketik kalimat uji (mis: integral dari nol sampai satu x kuadrat dx)...' if is_id else 'Type a test sentence (e.g. integral from zero to one of x squared dx)...'}" />
    <button class="btn btn-primary" type="submit">{'Kirim Uji' if is_id else 'Send Test'}</button>
  </form>
</div>

<script>
{SHARED_RENDER_JS}
const CFG = {json.dumps(cfg)};
const DEMO_LINES = CFG.isId ? [
  "Selamat pagi, hari ini kita bahas Integral Riemann dan Konvergensi deret.",
  "Perhatikan fungsi sederhana x kuadrat dan hitung integral dari nol sampai satu x kuadrat dx.",
  "Pada metode eiginvalue kita menjumpai akar dari x tambah satu sebelum Transformasi Fourier.",
  "Cek bagian papan sebelah kiri [unclear] lalu evaluasi limit x menuju nol dari sin x per x."
] : [
  "Good morning everyone, today we study Riemann Integral and Convergence.",
  "Consider x squared and evaluate the integral from zero to one of x squared dx.",
  "In eiginvalue decomposition we encounter square root of x plus one before Fourier Transform.",
  "Check the corner of the board [unclear] then compute limit as x approaches zero of sin x over x."
];

let ws = null;
let demoIdx = 0;
let captions = [];
let interimText = '';
let running = false;
let paused = false;
let mediaStream = null;
let audioCtx = null;
let procNode = null;
let recognition = null;
let mockTimer = null;

const connBadge = document.getElementById('connBadge');
const stuBadge = document.getElementById('stuBadge');
const statusBadge = document.getElementById('statusBadge');
const streamEl = document.getElementById('stream');
const meterFill = document.getElementById('meterFill');
const levelPct = document.getElementById('levelPct');
const errBox = document.getElementById('errBox');
const micSelect = document.getElementById('micSelect');
const engineSelect = document.getElementById('engineSelect');

function showError(msg) {{
  if (!msg) {{ errBox.style.display = 'none'; return; }}
  errBox.textContent = msg;
  errBox.style.display = 'block';
}}

function setMeter(pct) {{
  const v = Math.max(0, Math.min(100, Math.round(pct)));
  meterFill.style.width = v + '%';
  levelPct.textContent = v + '%';
}}

async function refreshMics() {{
  if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
  try {{
    const devs = await navigator.mediaDevices.enumerateDevices();
    const inputs = devs.filter(d => d.kind === 'audioinput');
    const prev = micSelect.value;
    micSelect.innerHTML = '<option value="">' + (CFG.isId ? 'Mikrofon Bawaan' : 'Default Microphone') + '</option>';
    inputs.forEach((d, idx) => {{
      const opt = document.createElement('option');
      opt.value = d.deviceId;
      opt.textContent = d.label || ('Microphone ' + (idx + 1));
      micSelect.appendChild(opt);
    }});
    if (prev) micSelect.value = prev;
  }} catch (e) {{}}
}}
refreshMics();

function renderStream() {{
  if (!captions.length && !interimText) {{
    streamEl.innerHTML = '<div style="margin:auto;color:var(--muted);text-align:center;font-size:14px;">'
      + (CFG.isId ? 'Belum ada transkrip. Mulai berbicara atau kirim baris uji.' : 'No captions yet. Start speaking or send a test line.')
      + '</div>';
    return;
  }}
  let html = captions.map(cap =>
    '<div class="cap-item">'
    + '<div class="cap-meta"><span>#' + cap.seq + ' &middot; ' + escHtml(cap.refined_by || 'rules') + '</span><span>' + fmtTime(cap.timestamp_ms) + '</span></div>'
    + '<div>' + renderSegmentsHtml(cap, CFG.autoLabel) + '</div>'
    + '</div>'
  ).join('');
  if (interimText) {{
    html += '<div class="interim-box">' + escHtml(interimText) + '</div>';
  }}
  streamEl.innerHTML = html;
  streamEl.scrollTop = streamEl.scrollHeight;
}}

function connectWs() {{
  ws = new WebSocket(CFG.wsUrl);
  ws.onopen = () => {{
    connBadge.className = 'badge badge-ok';
    connBadge.textContent = CFG.isId ? 'WebSocket Terhubung' : 'WebSocket Connected';
  }};
  ws.onmessage = (ev) => {{
    if (ev.data === 'pong') return;
    try {{
      const msg = JSON.parse(ev.data);
      if (msg.type === 'snapshot') {{
        captions = msg.captions || [];
        stuBadge.textContent = (msg.student_count || 0) + (CFG.isId ? ' mahasiswa' : ' students');
        if (msg.session) statusBadge.textContent = (msg.session.status || 'live').toUpperCase();
        renderStream();
      }} else if (msg.type === 'caption' && msg.caption) {{
        const idx = captions.findIndex(c => c.seq === msg.caption.seq);
        if (idx >= 0) captions[idx] = msg.caption; else captions.push(msg.caption);
        interimText = '';
        renderStream();
      }} else if (msg.type === 'interim') {{
        interimText = msg.text || '';
        renderStream();
      }} else if (msg.type === 'student_count') {{
        stuBadge.textContent = (msg.count || 0) + (CFG.isId ? ' mahasiswa' : ' students');
      }} else if (msg.type === 'session_update' && msg.session) {{
        statusBadge.textContent = (msg.session.status || 'live').toUpperCase();
      }} else if (msg.type === 'stt_error') {{
        showError('Faster-Whisper: ' + msg.message);
      }}
    }} catch (e) {{}}
  }};
  ws.onclose = () => {{
    connBadge.className = 'badge badge-warn';
    connBadge.textContent = CFG.isId ? 'Menghubungkan ulang...' : 'Reconnecting...';
    setTimeout(connectWs, 2000);
  }};
}}
connectWs();
setInterval(() => {{ if (ws && ws.readyState === 1) ws.send('ping'); }}, 18000);

function downsampleToInt16(floatArr, inRate) {{
  const ratio = inRate / 16000;
  const outLen = Math.max(1, Math.round(floatArr.length / ratio));
  const out = new Int16Array(outLen);
  for (let i = 0; i < outLen; i++) {{
    const s = Math.max(-1, Math.min(1, floatArr[Math.min(floatArr.length - 1, Math.round(i * ratio))]));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }}
  return out;
}}

function stopCapture() {{
  running = false;
  if (mockTimer) {{ clearInterval(mockTimer); mockTimer = null; }}
  if (recognition) {{ try {{ recognition.onend = null; recognition.abort(); }} catch (e) {{}} recognition = null; }}
  if (procNode) {{ procNode.disconnect(); procNode = null; }}
  if (audioCtx) {{ audioCtx.close().catch(() => {{}}); audioCtx = null; }}
  if (mediaStream) {{ mediaStream.getTracks().forEach(t => t.stop()); mediaStream = null; }}
  setMeter(0);
}}

async function startWhisperWsMic() {{
  showError('');
  const devId = micSelect.value;
  mediaStream = await navigator.mediaDevices.getUserMedia({{
    audio: devId ? {{ deviceId: {{ exact: devId }} }} : true, video: false
  }});
  await refreshMics();
  const AC = window.AudioContext || window.webkitAudioContext;
  audioCtx = new AC();
  const src = audioCtx.createMediaStreamSource(mediaStream);
  procNode = audioCtx.createScriptProcessor(4096, 1, 1);
  let chunks = [];
  let collected = 0;
  let peakRms = 0;
  const targetSamples = Math.round(audioCtx.sampleRate * 4.5);

  procNode.onaudioprocess = (ev) => {{
    if (!running || paused) return;
    const data = ev.inputBuffer.getChannelData(0);
    let sq = 0;
    for (let i = 0; i < data.length; i++) sq += data[i] * data[i];
    const rms = Math.sqrt(sq / data.length);
    if (rms > peakRms) peakRms = rms;
    setMeter(rms * 280);
    chunks.push(new Float32Array(data));
    collected += data.length;
    if (collected >= targetSamples) {{
      const merged = new Float32Array(collected);
      let off = 0;
      for (const c of chunks) {{ merged.set(c, off); off += c.length; }}
      chunks = []; collected = 0;
      const hadVoice = peakRms >= 0.012;
      peakRms = 0;
      if (hadVoice && ws && ws.readyState === 1) {{
        const pcm16 = downsampleToInt16(merged, audioCtx.sampleRate);
        ws.send(pcm16.buffer);
      }}
    }}
  }};
  src.connect(procNode);
  procNode.connect(audioCtx.destination);
}}

function startWebSpeech() {{
  showError('');
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {{
    showError(CFG.isId ? 'Web Speech tidak didukung browser ini. Pilih Faster-Whisper atau Mock.' : 'Web Speech unsupported here. Switch to Faster-Whisper or Mock.');
    return;
  }}
  const isMobile = /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent);
  let pendingInterim = '';
  const launch = () => {{
    if (!running || paused) return;
    const rec = new SR();
    rec.lang = CFG.language;
    rec.continuous = !isMobile;
    rec.interimResults = true;
    rec.onresult = (ev) => {{
      let inter = '';
      for (let i = ev.resultIndex; i < ev.results.length; i++) {{
        const r = ev.results[i];
        const alt = r[0];
        if (!alt) continue;
        if (r.isFinal) {{
          pendingInterim = '';
          const txt = alt.transcript.trim();
          if (txt && ws && ws.readyState === 1) {{
            setMeter(70);
            ws.send(JSON.stringify({{ type: 'final', text: txt, confidence: alt.confidence || 0.92 }}));
            setTimeout(() => setMeter(18), 400);
          }}
        }} else {{
          inter += alt.transcript;
        }}
      }}
      if (inter.trim()) {{
        pendingInterim = inter.trim();
        setMeter(45);
        if (ws && ws.readyState === 1) ws.send(JSON.stringify({{ type: 'interim', text: pendingInterim }}));
      }}
    }};
    rec.onerror = (ev) => {{
      if (ev.error !== 'no-speech') showError('Web Speech (' + ev.error + ')');
    }};
    rec.onend = () => {{
      if (pendingInterim && ws && ws.readyState === 1) {{
        ws.send(JSON.stringify({{ type: 'final', text: pendingInterim, confidence: 0.85 }}));
        pendingInterim = '';
      }}
      if (running && !paused) setTimeout(launch, 250);
    }};
    recognition = rec;
    try {{ rec.start(); }} catch (e) {{}}
  }};
  launch();
}}

function startMock() {{
  showError('');
  const emit = () => {{
    if (!running || paused || !ws || ws.readyState !== 1) return;
    const line = DEMO_LINES[demoIdx % DEMO_LINES.length];
    demoIdx++;
    setMeter(58);
    ws.send(JSON.stringify({{ type: 'final', text: line, confidence: 0.94 }}));
    setTimeout(() => setMeter(15), 600);
  }};
  emit();
  mockTimer = setInterval(emit, 3500);
}}

const btnStart = document.getElementById('btnStart');
const btnPause = document.getElementById('btnPause');
const btnResume = document.getElementById('btnResume');

btnStart.onclick = async () => {{
  stopCapture();
  running = true; paused = false;
  btnStart.style.display = 'none';
  btnPause.style.display = 'inline-flex';
  btnResume.style.display = 'none';
  if (ws && ws.readyState === 1) ws.send(JSON.stringify({{ type: 'status', status: 'live' }}));
  const mode = engineSelect.value;
  try {{
    if (mode === 'whisper_ws') await startWhisperWsMic();
    else if (mode === 'webspeech') startWebSpeech();
    else startMock();
  }} catch (err) {{
    showError(String(err));
    stopCapture();
    btnStart.style.display = 'inline-flex';
    btnPause.style.display = 'none';
  }}
}};

btnPause.onclick = () => {{
  paused = true;
  btnPause.style.display = 'none';
  btnResume.style.display = 'inline-flex';
  if (recognition) {{ try {{ recognition.abort(); }} catch (e) {{}} }}
  setMeter(0);
  if (ws && ws.readyState === 1) ws.send(JSON.stringify({{ type: 'status', status: 'paused' }}));
}};

btnResume.onclick = () => {{
  paused = false;
  btnResume.style.display = 'none';
  btnPause.style.display = 'inline-flex';
  if (ws && ws.readyState === 1) ws.send(JSON.stringify({{ type: 'status', status: 'live' }}));
  if (engineSelect.value === 'webspeech') startWebSpeech();
}};

document.getElementById('btnDemoOne').onclick = () => {{
  const line = DEMO_LINES[demoIdx % DEMO_LINES.length];
  demoIdx++;
  if (ws && ws.readyState === 1) {{
    ws.send(JSON.stringify({{ type: 'final', text: line, confidence: 0.94 }}));
  }}
}};

document.getElementById('btnEnd').onclick = () => {{
  if (!confirm(CFG.isId ? 'Akhiri sesi kuliah ini?' : 'End this lecture session?')) return;
  stopCapture();
  btnStart.style.display = 'inline-flex';
  btnPause.style.display = 'none';
  btnResume.style.display = 'none';
  if (ws && ws.readyState === 1) ws.send(JSON.stringify({{ type: 'status', status: 'ended' }}));
}};

document.getElementById('manualForm').onsubmit = (e) => {{
  e.preventDefault();
  const inp = document.getElementById('manualInput');
  const txt = inp.value.trim();
  if (!txt || !ws || ws.readyState !== 1) return;
  ws.send(JSON.stringify({{ type: 'final', text: txt, confidence: 0.96 }}));
  inp.value = '';
}};
</script>
</body></html>
"""
    components.html(html, height=670, scrolling=False)


def render_student_live_console(
    session: dict,
    ws_base_url: str,
    http_base_url: str,
    student_id: str,
    ui_lang: str = "id",
) -> None:
    """
    High-contrast, zero-flicker mobile-first Student Caption Screen powered by
    FastAPI WebSockets + KaTeX + Private Bookmarks (Supabase PostgreSQL).
    """
    is_id = ui_lang == "id"
    cfg = {
        "sessionId": session["id"],
        "studentId": student_id,
        "wsUrl": f"{ws_base_url}/ws/student/{session['id']}?client_id={student_id}",
        "bookmarksApi": f"{http_base_url}/api/sessions/{session['id']}/bookmarks",
        "autoLabel": "otomatis" if is_id else "automatic",
        "isId": is_id,
        "courseTitle": session["course_title"],
        "topic": session["topic"],
    }

    html = f"""<!doctype html>
<html><head><meta charset="utf-8">{KATEX_HEAD}{SHARED_STYLES}</head>
<body>
<div class="card">
  <div class="toolbar">
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
      <span id="liveBadge" class="badge badge-err">● LIVE</span>
      <span id="connBadge" class="badge badge-warn">{'Menghubungkan...' if is_id else 'Connecting...'}</span>
    </div>
    <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;">
      <button id="btnFontDec" class="btn" type="button" aria-label="Decrease font">A-</button>
      <span id="fontLabel" style="font-size:12px;font-weight:800;min-width:26px;text-align:center;">M</span>
      <button id="btnFontInc" class="btn" type="button" aria-label="Increase font">A+</button>
      <button id="btnScroll" class="btn" type="button">⏸ {'Jeda Gulir' if is_id else 'Pause Scroll'}</button>
      <button id="btnTheme" class="btn" type="button">🌙</button>
    </div>
  </div>

  <div id="lostBanner" style="display:none;padding:10px 14px;background:#ffe4e6;color:#881337;font-size:13px;font-weight:700;align-items:center;justify-content:space-between;gap:8px;">
    <span>{'Koneksi terputus — mencoba menghubungkan ulang...' if is_id else 'Connection lost — attempting to reconnect...'}</span>
    <button id="btnRetry" class="btn btn-red" type="button">{'Coba Lagi' if is_id else 'Retry'}</button>
  </div>

  <div id="endedPanel" style="display:none;padding:48px 24px;text-align:center;">
    <div style="font-size:40px;">✅</div>
    <h2 style="margin:10px 0 6px;">{'Sesi Telah Berakhir' if is_id else 'Session Ended'}</h2>
    <p style="color:var(--muted);max-width:460px;margin:0 auto;font-size:14px;">
      {'Dosen telah mengakhiri sesi kuliah langsung ini. Buka tab Transkrip & Ringkasan di atas untuk melihat ringkasan Gemini dan ekspor .docx / .pdf.' if is_id else 'The lecturer ended this live session. Switch to the Transcript & Summary tab above to generate a Gemini summary and export .docx / .pdf.'}
    </p>
  </div>

  <div style="position:relative;">
    <div id="stream" class="stream" style="height:460px;font-size:21px;" role="log" aria-live="polite"></div>
    <button id="jumpBtn" class="btn btn-primary" type="button"
      style="display:none;position:absolute;right:16px;bottom:16px;border-radius:999px;box-shadow:0 6px 18px rgba(0,0,0,0.2);">
      {'Ke teks terbaru ↓' if is_id else 'Jump to latest ↓'}
    </button>
  </div>
</div>

<script>
{SHARED_RENDER_JS}
const CFG = {json.dumps(cfg)};
const SIZES = [
  {{ label: 'S', px: 17 }},
  {{ label: 'M', px: 21 }},
  {{ label: 'L', px: 26 }},
  {{ label: 'XL', px: 32 }}
];

let fontIdx = Number(localStorage.getItem('ll_py_font') || 1);
if (isNaN(fontIdx) || fontIdx < 0 || fontIdx >= SIZES.length) fontIdx = 1;
let dark = localStorage.getItem('ll_py_dark') === '1';
let autoScroll = true;
let captions = [];
let interimText = '';
let bookmarkedSeqs = new Set();
let ws = null;

const streamEl = document.getElementById('stream');
const connBadge = document.getElementById('connBadge');
const liveBadge = document.getElementById('liveBadge');
const lostBanner = document.getElementById('lostBanner');
const endedPanel = document.getElementById('endedPanel');
const jumpBtn = document.getElementById('jumpBtn');
const btnScroll = document.getElementById('btnScroll');
const btnTheme = document.getElementById('btnTheme');
const fontLabel = document.getElementById('fontLabel');

function applyPrefs() {{
  document.body.classList.toggle('dark', dark);
  btnTheme.textContent = dark ? '☀️' : '🌙';
  streamEl.style.fontSize = SIZES[fontIdx].px + 'px';
  fontLabel.textContent = SIZES[fontIdx].label;
  localStorage.setItem('ll_py_font', String(fontIdx));
  localStorage.setItem('ll_py_dark', dark ? '1' : '0');
}}
applyPrefs();

document.getElementById('btnFontDec').onclick = () => {{ if (fontIdx > 0) {{ fontIdx--; applyPrefs(); }} }};
document.getElementById('btnFontInc').onclick = () => {{ if (fontIdx < SIZES.length - 1) {{ fontIdx++; applyPrefs(); }} }};
btnTheme.onclick = () => {{ dark = !dark; applyPrefs(); }};

function updateScrollUi() {{
  btnScroll.textContent = autoScroll
    ? ('⏸ ' + (CFG.isId ? 'Jeda Gulir' : 'Pause Scroll'))
    : ('▶ ' + (CFG.isId ? 'Lanjut Gulir' : 'Resume Scroll'));
  jumpBtn.style.display = autoScroll ? 'none' : 'inline-flex';
}}

btnScroll.onclick = () => {{
  autoScroll = !autoScroll;
  updateScrollUi();
  if (autoScroll) streamEl.scrollTop = streamEl.scrollHeight;
}};
jumpBtn.onclick = () => {{
  autoScroll = true;
  updateScrollUi();
  streamEl.scrollTop = streamEl.scrollHeight;
}};
streamEl.addEventListener('scroll', () => {{
  const dist = streamEl.scrollHeight - streamEl.scrollTop - streamEl.clientHeight;
  if (dist > 80 && autoScroll) {{ autoScroll = false; updateScrollUi(); }}
}});

async function loadBookmarks() {{
  try {{
    const r = await fetch(CFG.bookmarksApi + '?student_id=' + encodeURIComponent(CFG.studentId));
    if (r.ok) {{
      const list = await r.json();
      bookmarkedSeqs = new Set(list.map(b => b.transcript_seq));
      renderStream();
    }}
  }} catch (e) {{}}
}}
loadBookmarks();

window.toggleBookmark = async function(seq) {{
  const has = bookmarkedSeqs.has(seq);
  try {{
    if (has) {{
      await fetch(CFG.bookmarksApi + '/' + seq + '?student_id=' + encodeURIComponent(CFG.studentId), {{ method: 'DELETE' }});
      bookmarkedSeqs.delete(seq);
    }} else {{
      await fetch(CFG.bookmarksApi, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ transcript_seq: seq, student_id: CFG.studentId, note: '' }})
      }});
      bookmarkedSeqs.add(seq);
    }}
    renderStream();
  }} catch (e) {{}}
}};

function renderStream() {{
  if (!captions.length && !interimText) {{
    streamEl.innerHTML = '<div style="margin:auto;color:var(--muted);text-align:center;font-size:16px;">'
      + (CFG.isId ? 'Terhubung! Menunggu dosen mulai berbicara...' : 'Connected! Waiting for the lecturer to begin...')
      + '</div>';
    return;
  }}
  let html = '<div style="margin-top:auto;display:flex;flex-direction:column;gap:14px;">';
  html += captions.map(cap => {{
    const saved = bookmarkedSeqs.has(cap.seq);
    return '<div class="cap-item">'
      + '<div class="cap-meta">'
      + '<span>#' + cap.seq + ' &middot; ' + fmtTime(cap.timestamp_ms) + '</span>'
      + '<button class="bk-btn ' + (saved ? 'saved' : '') + '" onclick="toggleBookmark(' + cap.seq + ')">'
      + (saved ? '★ ' + (CFG.isId ? 'Tersimpan' : 'Bookmarked') : '☆ Bookmark')
      + '</button>'
      + '</div>'
      + '<div>' + renderSegmentsHtml(cap, CFG.autoLabel) + '</div>'
      + '</div>';
  }}).join('');
  if (interimText) {{
    html += '<div class="interim-box">' + escHtml(interimText) + '</div>';
  }}
  html += '</div>';
  streamEl.innerHTML = html;
  if (autoScroll) streamEl.scrollTop = streamEl.scrollHeight;
}}

function applySessionStatus(st) {{
  if (st === 'ended') {{
    liveBadge.className = 'badge badge-ok';
    liveBadge.textContent = CFG.isId ? 'SELESAI' : 'ENDED';
    streamEl.style.display = 'none';
    endedPanel.style.display = 'block';
  }} else if (st === 'paused') {{
    liveBadge.className = 'badge badge-warn';
    liveBadge.textContent = CFG.isId ? 'DIJEDA' : 'PAUSED';
    streamEl.style.display = 'flex';
    endedPanel.style.display = 'none';
  }} else {{
    liveBadge.className = 'badge badge-err';
    liveBadge.textContent = CFG.isId ? '● LANGSUNG' : '● LIVE';
    streamEl.style.display = 'flex';
    endedPanel.style.display = 'none';
  }}
}}

function connectWs() {{
  if (ws) {{ try {{ ws.close(); }} catch (e) {{}} }}
  ws = new WebSocket(CFG.wsUrl);
  ws.onopen = () => {{
    connBadge.className = 'badge badge-ok';
    connBadge.textContent = CFG.isId ? 'Terhubung' : 'Connected';
    lostBanner.style.display = 'none';
  }};
  ws.onmessage = (ev) => {{
    if (ev.data === 'pong') return;
    try {{
      const msg = JSON.parse(ev.data);
      if (msg.type === 'snapshot') {{
        captions = msg.captions || [];
        if (msg.session) applySessionStatus(msg.session.status);
        renderStream();
      }} else if (msg.type === 'caption' && msg.caption) {{
        const idx = captions.findIndex(c => c.seq === msg.caption.seq);
        if (idx >= 0) captions[idx] = msg.caption; else captions.push(msg.caption);
        interimText = '';
        renderStream();
      }} else if (msg.type === 'interim') {{
        interimText = msg.text || '';
        renderStream();
      }} else if (msg.type === 'session_update' && msg.session) {{
        applySessionStatus(msg.session.status);
      }}
    }} catch (e) {{}}
  }};
  ws.onclose = () => {{
    connBadge.className = 'badge badge-err';
    connBadge.textContent = CFG.isId ? 'Terputus' : 'Disconnected';
    lostBanner.style.display = 'flex';
    setTimeout(connectWs, 2500);
  }};
}}
document.getElementById('btnRetry').onclick = connectWs;
connectWs();
setInterval(() => {{ if (ws && ws.readyState === 1) ws.send('ping'); }}, 18000);
</script>
</body></html>
"""
    components.html(html, height=575, scrolling=False)


def render_katex_transcript_list(
    captions: list[dict],
    bookmarked_seqs: set[int],
    ui_lang: str = "id",
) -> None:
    """Renders searchable transcript rows with full KaTeX formulas & glossary highlights."""
    auto_label = "otomatis" if ui_lang == "id" else "automatic"
    payload = {
        "captions": captions,
        "bookmarks": list(bookmarked_seqs),
        "autoLabel": auto_label,
    }
    est_height = max(240, min(720, 95 * max(1, len(captions))))
    html = f"""<!doctype html>
<html><head><meta charset="utf-8">{KATEX_HEAD}{SHARED_STYLES}</head>
<body>
<div id="list" style="display:flex;flex-direction:column;gap:10px;padding:4px;"></div>
<script>
{SHARED_RENDER_JS}
const DATA = {json.dumps(payload)};
const bset = new Set(DATA.bookmarks || []);
const root = document.getElementById('list');
root.innerHTML = DATA.captions.map(cap => {{
  const star = bset.has(cap.seq) ? ' <span class="badge badge-warn">★ Bookmark</span>' : '';
  return '<div class="cap-item">'
    + '<div class="cap-meta"><span>#' + cap.seq + ' &middot; ' + fmtTime(cap.timestamp_ms) + star + '</span><span>' + escHtml(cap.refined_by || 'rules') + '</span></div>'
    + '<div style="font-size:16px;">' + renderSegmentsHtml(cap, DATA.autoLabel) + '</div>'
    + '</div>';
}}).join('');
</script>
</body></html>
"""
    components.html(html, height=est_height, scrolling=True)
