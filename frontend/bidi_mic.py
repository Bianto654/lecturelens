from __future__ import annotations

from typing import Any, Optional
import streamlit as st

_HOST_MIC_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&family=JetBrains+Mono:wght@600;700&display=swap');
:host, * {
  box-sizing: border-box;
  font-family: 'Poppins', system-ui, -apple-system, sans-serif;
}
.ll-mic-window {
  background: #ffffff;
  border: 1.5px solid #ffe4d2;
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 14px 36px rgba(51, 51, 51, 0.07);
}
.ll-win-bar {
  background: #fff1e8;
  border-bottom: 1px solid #ffe0cc;
  padding: 12px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.ll-win-dots {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.ll-win-badge-icon {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #ffd9c6;
  color: #f77e23;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
}
.ll-win-title {
  color: #333333;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: -0.01em;
}
.ll-win-sub {
  color: #f77e23;
  font-size: 11.5px;
  font-weight: 600;
}
.ll-mic-card {
  position: relative;
  background: #ffffff;
  padding: 22px 22px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}
.ll-top-row {
  position: relative;
  z-index: 1;
  width: 100%;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.ll-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.ll-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}
.ll-pill-idle { background: #fff1e8; color: #b45309; border: 1px solid #ffd9c6; }
.ll-pill-live { background: #f77e23; color: #ffffff; box-shadow: 0 4px 12px rgba(247, 126, 35, 0.3); }
.ll-pill-warn { background: #fef3c7; color: #92400e; }
.ll-pill-err  { background: #fee2e2; color: #991b1b; }
.ll-pill-blue { background: #fff7f2; color: #333333; border: 1px solid #ffe0cc; }

.ll-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}
.ll-dot-pulse {
  animation: llBlink 1.05s ease-in-out infinite;
}
@keyframes llBlink {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.35; transform: scale(0.78); }
}

.ll-lang-toggle {
  display: inline-flex;
  background: #fff1e8;
  border: 1px solid #ffd9c6;
  padding: 3px;
  border-radius: 999px;
  gap: 3px;
}
.ll-lang-btn {
  border: none;
  background: transparent;
  color: #555555;
  font-size: 12px;
  font-weight: 600;
  padding: 6px 14px;
  min-height: 34px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.ll-lang-btn.active {
  background: #f77e23;
  color: #ffffff;
  box-shadow: 0 4px 10px rgba(247, 126, 35, 0.28);
}

/* Huge tactile 104x104px Figma-styled Studio Microphone Button with dashed peach orbit */
.ll-hero-zone {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 10px 0 4px;
  width: 100%;
}
.ll-mic-ring {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 136px;
  height: 136px;
  border-radius: 50%;
  border: 2px dashed #f5b793;
  background: #fff9f5;
}
.ll-mic-ring::before,
.ll-mic-ring::after {
  content: '';
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  opacity: 0;
  pointer-events: none;
}
.ll-mic-ring.listening::before {
  border: 3px solid rgba(247, 126, 35, 0.52);
  animation: llRipple 1.65s cubic-bezier(0.2, 0.7, 0.4, 1) infinite;
}
.ll-mic-ring.listening::after {
  border: 3px solid rgba(239, 68, 68, 0.35);
  animation: llRipple 1.65s cubic-bezier(0.2, 0.7, 0.4, 1) 0.82s infinite;
}
@keyframes llRipple {
  0% { transform: scale(0.84); opacity: 0.95; }
  100% { transform: scale(1.26); opacity: 0; }
}

.ll-mic-btn {
  position: relative;
  z-index: 2;
  width: 104px;
  height: 104px;
  border-radius: 50%;
  border: 4px solid #ffffff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  background: linear-gradient(135deg, #ff9642 0%, #f77e23 100%);
  box-shadow: 0 12px 28px rgba(247, 126, 35, 0.36);
  transition: transform 0.14s ease, box-shadow 0.16s ease, background 0.16s ease;
  -webkit-tap-highlight-color: transparent;
}
.ll-mic-btn:hover { transform: scale(1.04); box-shadow: 0 16px 34px rgba(247, 126, 35, 0.44); }
.ll-mic-btn:active { transform: scale(0.95); }
.ll-mic-btn.listening {
  background: linear-gradient(135deg, #ef4444 0%, #f77e23 100%);
  box-shadow: 0 14px 32px rgba(239, 68, 68, 0.38);
}
.ll-mic-btn svg {
  width: 44px;
  height: 44px;
}

.ll-hero-label {
  font-size: 17px;
  font-weight: 700;
  color: #333333;
  text-align: center;
}
.ll-hero-sub {
  font-size: 13px;
  font-weight: 400;
  color: #666666;
  text-align: center;
  max-width: 460px;
  line-height: 1.55;
}

.ll-wave {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 28px;
}
.ll-bar {
  width: 5px;
  height: 7px;
  border-radius: 999px;
  background: #ffd9c6;
  transition: height 0.12s ease, background 0.2s ease;
}
.ll-wave.active .ll-bar {
  background: linear-gradient(180deg, #f77e23, #ef4444);
  animation: llWave 0.85s ease-in-out infinite alternate;
}
.ll-wave.active .ll-bar:nth-child(2) { animation-delay: 0.15s; }
.ll-wave.active .ll-bar:nth-child(3) { animation-delay: 0.30s; }
.ll-wave.active .ll-bar:nth-child(4) { animation-delay: 0.10s; }
.ll-wave.active .ll-bar:nth-child(5) { animation-delay: 0.25s; }
.ll-wave.active .ll-bar:nth-child(6) { animation-delay: 0.40s; }
.ll-wave.active .ll-bar:nth-child(7) { animation-delay: 0.05s; }
@keyframes llWave {
  0% { height: 7px; }
  100% { height: 26px; }
}

.ll-interim {
  position: relative;
  z-index: 1;
  width: 100%;
  min-height: 58px;
  border-radius: 14px;
  border: 1.5px dashed #f5b793;
  background: #fff9f5;
  padding: 13px 16px;
  font-size: 14.5px;
  font-weight: 500;
  line-height: 1.55;
  color: #666666;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
}
.ll-interim.has-text {
  border-style: solid;
  border-color: #f77e23;
  background: #fff4ec;
  color: #333333;
  font-weight: 600;
  justify-content: flex-start;
  text-align: left;
}

.ll-error {
  position: relative;
  z-index: 1;
  width: 100%;
  display: none;
  padding: 12px 14px;
  border-radius: 14px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.5;
}
.ll-error.show { display: block; }

.ll-controls {
  position: relative;
  z-index: 1;
  width: 100%;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  padding-top: 4px;
}
.ll-action-btn {
  min-height: 44px;
  padding: 10px 20px;
  border-radius: 10px;
  border: 1px solid #ffd9c6;
  background: #fff7f2;
  color: #d9620f;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  transition: transform 0.12s ease, background 0.15s ease, box-shadow 0.15s ease;
}
.ll-action-btn:hover { background: #ffe8d9; transform: translateY(-1px); }
.ll-action-danger {
  background: #333333;
  border-color: #333333;
  color: #ffffff;
  box-shadow: 0 6px 16px rgba(51, 51, 51, 0.18);
}
.ll-action-danger:hover { background: #1e1e1e; }
"""

_HOST_MIC_HTML = """
<div class="ll-mic-window">
  <div class="ll-win-bar">
    <span class="ll-win-dots">
      <span class="ll-win-badge-icon" aria-hidden="true">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
          <line x1="12" x2="12" y1="19" y2="22"/>
        </svg>
      </span>
      <span class="ll-win-title">Live Classroom Audio Studio</span>
    </span>
    <span class="ll-win-sub">Real-time Captioning</span>
  </div>
  <div class="ll-mic-card">
    <div class="ll-top-row">
      <div class="ll-pills">
        <span id="statePill" class="ll-pill ll-pill-idle">
          <span class="ll-dot"></span>
          <span id="stateText">Siap</span>
        </span>
      </div>
      <div class="ll-lang-toggle" role="group" aria-label="Speech language">
        <button id="langId" class="ll-lang-btn active" type="button">ID</button>
        <button id="langEn" class="ll-lang-btn" type="button">EN</button>
      </div>
    </div>

    <div class="ll-hero-zone">
      <div id="micRing" class="ll-mic-ring">
        <button id="micBtn" class="ll-mic-btn" type="button" aria-label="Toggle microphone">
          <svg id="micIcon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
            <line x1="12" x2="12" y1="19" y2="22"/>
          </svg>
        </button>
      </div>
      <div id="heroLabel" class="ll-hero-label">Tap Mikrofon untuk Mulai Bicara</div>
      <div id="heroSub" class="ll-hero-sub">Suara dosen langsung ditranskripsi real-time dengan pencocokan glosarium &amp; rumus KaTeX.</div>
      <div id="wave" class="ll-wave" aria-hidden="true">
        <div class="ll-bar"></div><div class="ll-bar"></div><div class="ll-bar"></div>
        <div class="ll-bar"></div><div class="ll-bar"></div><div class="ll-bar"></div>
        <div class="ll-bar"></div>
      </div>
    </div>

    <div id="interimBox" class="ll-interim">Teks sementara akan muncul di sini saat Anda mulai berbicara...</div>
    <div id="errBox" class="ll-error" role="alert"></div>

    <div class="ll-controls">
      <button id="btnDemo" class="ll-action-btn" type="button">Kirim 1 Baris Demo</button>
      <button id="btnEnd" class="ll-action-btn ll-action-danger" type="button">Akhiri Sesi</button>
    </div>
  </div>
</div>
"""

_HOST_MIC_JS = """
export default function(component) {
  const { parentElement, data, setTriggerValue } = component;
  const cfg = data || {};
  const isId = cfg.ui_lang !== 'en';
  const sessionId = cfg.session_id || 'default';

  const q = (id) => parentElement.querySelector('#' + id);
  const statePill = q('statePill');
  const langIdBtn = q('langId');
  const langEnBtn = q('langEn');
  const micRing   = q('micRing');
  const micBtn    = q('micBtn');
  const heroLabel = q('heroLabel');
  const heroSub   = q('heroSub');
  const waveEl    = q('wave');
  const interimEl = q('interimBox');
  const errBox    = q('errBox');
  const btnDemo   = q('btnDemo');
  const btnEnd    = q('btnEnd');

  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const isMobile = /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent);

  // Persist SpeechRecognition controller across Streamlit reruns so mic NEVER drops!
  if (!window.__LL_MIC || window.__LL_MIC.sessionId !== sessionId) {
    if (window.__LL_MIC && window.__LL_MIC.stopAll) {
      try { window.__LL_MIC.stopAll(); } catch (e) {}
    }
    window.__LL_MIC = {
      sessionId,
      lang: cfg.speech_lang || 'id-ID',
      active: false,
      rec: null,
      restartTimer: null,
      pendingInterim: '',
      lastError: '',
      failCount: 0,
      emit: null,
      syncUi: null,
      stopAll() {
        this.active = false;
        if (this.restartTimer) { clearTimeout(this.restartTimer); this.restartTimer = null; }
        if (this.rec) {
          try { this.rec.onend = null; this.rec.onerror = null; this.rec.abort(); } catch (e) {}
          this.rec = null;
        }
      }
    };
  }
  const ctrl = window.__LL_MIC;

  // Always point ctrl.emit to the latest mounted Streamlit setTriggerValue
  ctrl.emit = (name, payload) => {
    try { setTriggerValue(name, payload); } catch (e) {}
  };

  function renderUi() {
    langIdBtn.classList.toggle('active', ctrl.lang === 'id-ID');
    langEnBtn.classList.toggle('active', ctrl.lang === 'en-US');

    btnDemo.textContent = isId ? 'Kirim 1 Baris Demo' : 'Send 1 Demo Line';
    btnEnd.textContent  = isId ? 'Akhiri Sesi' : 'End Session';

    if (ctrl.active) {
      micRing.classList.add('listening');
      micBtn.classList.add('listening');
      waveEl.classList.add('active');
      statePill.className = 'll-pill ll-pill-live';
      statePill.innerHTML = '<span class="ll-dot ll-dot-pulse"></span><span>' + (isId ? 'MENDENGARKAN' : 'LISTENING') + '</span>';
      heroLabel.textContent = isId ? 'Sedang Mendengarkan... (Tap untuk Jeda)' : 'Listening... (Tap to Pause)';
      heroSub.textContent = isId
        ? 'Berbicaralah dengan jelas. Setiap kalimat otomatis diproses glosarium & rumus lalu dikirim ke mahasiswa.'
        : 'Speak clearly. Each sentence is automatically processed with glossary & formulas and sent live.';
    } else {
      micRing.classList.remove('listening');
      micBtn.classList.remove('listening');
      waveEl.classList.remove('active');
      statePill.className = 'll-pill ll-pill-idle';
      statePill.innerHTML = '<span class="ll-dot"></span><span>' + (isId ? 'SIAP / DIJEDA' : 'READY / PAUSED') + '</span>';
      heroLabel.textContent = isId ? 'Tap Mikrofon untuk Mulai Bicara' : 'Tap Microphone to Start Speaking';
      heroSub.textContent = isId
        ? 'Ketuk tombol bulat di atas untuk mulai transkripsi langsung (Chrome / Edge / Safari).'
        : 'Tap the large round button above to start live speech captioning (Chrome / Edge / Safari).';
    }

    if (ctrl.pendingInterim) {
      interimEl.classList.add('has-text');
      interimEl.textContent = ctrl.pendingInterim;
    } else {
      interimEl.classList.remove('has-text');
      interimEl.textContent = ctrl.active
        ? (isId ? 'Menunggu suara Anda...' : 'Waiting for speech...')
        : (isId ? 'Teks sementara akan muncul di sini saat Anda mulai berbicara...' : 'Live interim words will appear here as you speak...');
    }

    if (ctrl.lastError) {
      errBox.textContent = ctrl.lastError;
      errBox.classList.add('show');
    } else {
      errBox.classList.remove('show');
    }
  }
  ctrl.syncUi = renderUi;

  function commitFinal(text, confidence) {
    const clean = (text || '').trim();
    if (!clean) return;
    ctrl.pendingInterim = '';
    if (ctrl.syncUi) ctrl.syncUi();
    ctrl.emit('utterance', {
      id: Date.now() + '-' + Math.random().toString(36).slice(2, 7),
      text: clean,
      confidence: typeof confidence === 'number' && confidence > 0 ? confidence : 0.92,
      lang: ctrl.lang
    });
  }

  function launchRecognition() {
    if (!ctrl.active) return;
    if (!SR) {
      ctrl.active = false;
      ctrl.lastError = isId
        ? 'Browser ini belum mendukung Web Speech API (gunakan Google Chrome, Edge, atau Safari — jangan lewat browser bawaan WhatsApp/IG). Anda masih bisa memakai tombol Demo atau ketik/upload audio di bawah.'
        : 'This browser does not support Web Speech API. Please open in Chrome, Edge, or Safari (not inside WhatsApp/Instagram in-app browser).';
      if (ctrl.syncUi) ctrl.syncUi();
      return;
    }

    if (ctrl.rec) {
      try { ctrl.rec.onend = null; ctrl.rec.abort(); } catch (e) {}
      ctrl.rec = null;
    }

    const rec = new SR();
    rec.lang = ctrl.lang;
    // Mobile Chrome & iOS Safari work much more reliably with non-continuous + fast auto-restart
    rec.continuous = !isMobile;
    rec.interimResults = true;
    rec.maxAlternatives = 1;

    rec.onstart = () => {
      ctrl.failCount = 0;
      ctrl.lastError = '';
      if (ctrl.syncUi) ctrl.syncUi();
    };

    rec.onresult = (ev) => {
      let interim = '';
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        const res = ev.results[i];
        const alt = res[0];
        if (!alt) continue;
        if (res.isFinal) {
          commitFinal(alt.transcript, alt.confidence);
        } else {
          interim += alt.transcript;
        }
      }
      ctrl.pendingInterim = interim.trim();
      if (ctrl.syncUi) ctrl.syncUi();
    };

    rec.onerror = (ev) => {
      const code = ev.error;
      if (code === 'no-speech') return;
      if (code === 'not-allowed' || code === 'service-not-allowed') {
        ctrl.active = false;
        ctrl.lastError = isId
          ? 'Izin mikrofon ditolak oleh browser. Klik ikon gembok/mikrofon di address bar lalu izinkan akses mikrofon.'
          : 'Microphone permission denied. Allow microphone access in your browser address bar.';
        if (ctrl.syncUi) ctrl.syncUi();
        return;
      }
      if (code === 'audio-capture') {
        ctrl.active = false;
        ctrl.lastError = isId
          ? 'Mikrofon tidak ditemukan atau sedang dipakai aplikasi lain.'
          : 'No microphone detected or it is busy in another app.';
        if (ctrl.syncUi) ctrl.syncUi();
        return;
      }
      if (code === 'network') {
        ctrl.failCount += 1;
        if (ctrl.failCount >= 2) {
          ctrl.active = false;
          ctrl.lastError = isId
            ? 'Browser ini (mis. Brave/Firefox) memblokir layanan Web Speech. Buka link ini di Google Chrome atau Safari untuk transkripsi suara langsung.'
            : 'This browser blocked Web Speech network access (common in Brave). Open in Google Chrome or Safari for live voice transcription.';
          if (ctrl.syncUi) ctrl.syncUi();
          return;
        }
      }
      ctrl.failCount += 1;
    };

    rec.onend = () => {
      ctrl.rec = null;
      // Commit any spoken interim text that mobile Safari/Chrome didn't finalize before ending
      if (ctrl.pendingInterim) {
        commitFinal(ctrl.pendingInterim, 0.86);
      }
      if (ctrl.active) {
        const delay = isMobile ? 180 : Math.min(2500, 300 * Math.pow(1.5, ctrl.failCount));
        ctrl.restartTimer = setTimeout(launchRecognition, delay);
      } else if (ctrl.syncUi) {
        ctrl.syncUi();
      }
    };

    ctrl.rec = rec;
    try {
      rec.start();
    } catch (err) {
      ctrl.failCount += 1;
      ctrl.restartTimer = setTimeout(launchRecognition, 450);
    }
  }

  micBtn.onclick = () => {
    if (ctrl.active) {
      if (ctrl.pendingInterim) commitFinal(ctrl.pendingInterim, 0.86);
      ctrl.stopAll();
      ctrl.emit('action', { type: 'pause', ts: Date.now() });
      renderUi();
    } else {
      ctrl.lastError = '';
      ctrl.active = true;
      ctrl.failCount = 0;
      ctrl.emit('action', { type: 'resume', ts: Date.now() });
      renderUi();
      launchRecognition();
    }
  };

  langIdBtn.onclick = () => {
    if (ctrl.lang === 'id-ID') return;
    ctrl.lang = 'id-ID';
    ctrl.emit('action', { type: 'language', language: 'id-ID', ts: Date.now() });
    if (ctrl.active) launchRecognition();
    renderUi();
  };

  langEnBtn.onclick = () => {
    if (ctrl.lang === 'en-US') return;
    ctrl.lang = 'en-US';
    ctrl.emit('action', { type: 'language', language: 'en-US', ts: Date.now() });
    if (ctrl.active) launchRecognition();
    renderUi();
  };

  btnDemo.onclick = () => {
    ctrl.emit('action', { type: 'demo_one', ts: Date.now() });
  };

  btnEnd.onclick = () => {
    if (!window.confirm(isId ? 'Akhiri sesi kuliah ini sekarang?' : 'End this lecture session now?')) return;
    ctrl.stopAll();
    ctrl.emit('action', { type: 'end', ts: Date.now() });
    renderUi();
  };

  renderUi();
}
"""

_QR_CARD_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&family=JetBrains+Mono:wght@600;700&display=swap');
:host, * {
  box-sizing: border-box;
  font-family: 'Poppins', system-ui, -apple-system, sans-serif;
}
.qr-window {
  background: #ffffff;
  border: 1.5px solid #ffe4d2;
  border-radius: 22px;
  overflow: hidden;
  box-shadow: 0 12px 32px rgba(51, 51, 51, 0.06);
}
.qr-bar {
  background: #fff1e8;
  border-bottom: 1px solid #ffe0cc;
  padding: 11px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.qr-bar-left {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #333333;
  font-size: 13px;
  font-weight: 700;
}
.qr-bar-lbl {
  color: #f77e23;
  font-size: 11.5px;
  font-weight: 600;
}
.qr-shell {
  background: #ffffff;
  padding: 20px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 22px;
}
.qr-img-box {
  background: #fff7f2;
  border: 2px dashed #f5b793;
  border-radius: 18px;
  padding: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto;
}
.qr-img-box img {
  width: 196px;
  height: 196px;
  display: block;
  border-radius: 10px;
}
.qr-info {
  flex: 1;
  min-width: 230px;
  display: flex;
  flex-direction: column;
  gap: 11px;
}
.qr-code-badge {
  display: inline-block;
  align-self: flex-start;
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-size: 21px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: #f77e23;
  background: #fff1e8;
  border: 1.5px solid #ffd9c6;
  padding: 6px 18px;
  border-radius: 12px;
}
.qr-url-row {
  display: flex;
  gap: 8px;
  align-items: stretch;
}
.qr-url-input {
  flex: 1;
  min-height: 44px;
  padding: 8px 14px;
  border-radius: 10px;
  border: 1px solid #e5e7eb;
  background: #fafafa;
  color: #333333;
  font-size: 12.5px;
  font-family: 'JetBrains Mono', ui-monospace, monospace;
}
.qr-copy-btn {
  min-height: 44px;
  padding: 0 20px;
  border-radius: 10px;
  border: none;
  background: #f77e23;
  color: #ffffff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  box-shadow: 0 6px 16px rgba(247, 126, 35, 0.28);
}
.qr-copy-btn:hover { background: #e36a12; }
.qr-copy-btn.copied { background: #16a34a; box-shadow: 0 6px 16px rgba(22, 163, 74, 0.28); }
.qr-hint {
  font-size: 13px;
  font-weight: 400;
  color: #666666;
  line-height: 1.55;
}
"""

_QR_CARD_HTML = """
<div class="qr-window">
  <div class="qr-bar">
    <span class="qr-bar-left">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f77e23" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
        <rect x="3" y="14" width="7" height="7"/><path d="M14 14h3v3h-3zM18 18h3v3h-3z"/>
      </svg>
      <span>Room Access QR</span>
    </span>
    <span class="qr-bar-lbl">Scan langsung masuk kelas</span>
  </div>
  <div class="qr-shell">
    <div class="qr-img-box">
      <img id="qrImg" alt="Room QR Code" />
    </div>
    <div class="qr-info">
      <div id="roomCode" class="qr-code-badge"></div>
      <div id="qrHint" class="qr-hint"></div>
      <div class="qr-url-row">
        <input id="qrUrl" class="qr-url-input" type="text" readonly />
        <button id="copyBtn" class="qr-copy-btn" type="button">Salin</button>
      </div>
    </div>
  </div>
</div>
"""

_QR_CARD_JS = """
export default function(component) {
  const { parentElement, data } = component;
  const cfg = data || {};
  const sessionId = cfg.session_id || '';
  const isId = cfg.ui_lang !== 'en';

  // Always derive the REAL live browser URL (works on Streamlit Cloud, custom domains, & localhost!)
  const origin = (window.location.origin && !window.location.origin.includes('null'))
    ? window.location.origin
    : (cfg.fallback_origin || 'http://localhost:8501');
  const joinUrl = origin.replace(/\\/+$/, '') + '/?page=join&session=' + encodeURIComponent(sessionId);

  const q       = (id) => parentElement.querySelector('#' + id);
  const imgEl   = q('qrImg');
  const codeEl  = q('roomCode');
  const hintEl  = q('qrHint');
  const urlEl   = q('qrUrl');
  const copyBtn = q('copyBtn');

  codeEl.textContent = sessionId;
  urlEl.value = joinUrl;
  hintEl.textContent = isId
    ? 'Pindai QR ini dari kamera HP mahasiswa — langsung masuk ke ruang teks sesi ini.'
    : 'Scan this QR from any student phone camera — opens directly inside this live caption room.';
  copyBtn.textContent = isId ? 'Salin Link' : 'Copy Link';

  // Generate crisp QR image matching the EXACT browser origin URL
  if (cfg.qr_data_url && cfg.server_join_url === joinUrl) {
    imgEl.src = cfg.qr_data_url;
  } else {
    imgEl.src = 'https://api.qrserver.com/v1/create-qr-code/?size=240x240&margin=6&data=' + encodeURIComponent(joinUrl);
  }

  copyBtn.onclick = async () => {
    try {
      await navigator.clipboard.writeText(joinUrl);
      copyBtn.classList.add('copied');
      copyBtn.textContent = isId ? 'Tersalin!' : 'Copied!';
      setTimeout(() => {
        copyBtn.classList.remove('copied');
        copyBtn.textContent = isId ? 'Salin Link' : 'Copy Link';
      }, 2000);
    } catch (e) {
      urlEl.select();
      document.execCommand('copy');
    }
  };
}
"""

# Register bidirectional components ONCE at module import
_host_mic_component = st.components.v2.component(
    "lecturelens_host_mic_v2",
    html=_HOST_MIC_HTML,
    css=_HOST_MIC_CSS,
    js=_HOST_MIC_JS,
    isolate_styles=True,
)

_qr_card_component = st.components.v2.component(
    "lecturelens_qr_card_v2",
    html=_QR_CARD_HTML,
    css=_QR_CARD_CSS,
    js=_QR_CARD_JS,
    isolate_styles=True,
)


def mount_host_mic_console(
    session_id: str,
    speech_lang: str,
    ui_lang: str = "id",
) -> tuple[Optional[dict[str, Any]], Optional[dict[str, Any]]]:
    """
    Mounts the huge tactile bidirectional Host Microphone console.
    Returns `(utterance_payload, action_payload)` triggered from browser JS.
    """
    res = _host_mic_component(
        key=f"ll_host_mic_{session_id}",
        data={
            "session_id": session_id,
            "speech_lang": speech_lang,
            "ui_lang": ui_lang,
        },
        on_utterance_change=lambda: None,
        on_action_change=lambda: None,
    )
    utterance = getattr(res, "utterance", None)
    action = getattr(res, "action", None)
    return utterance, action


def mount_room_qr_card(
    session_id: str,
    fallback_origin: str,
    server_join_url: str,
    qr_data_url: str,
    ui_lang: str = "id",
) -> None:
    """
    Mounts a crisp Shareable QR card that always resolves to `window.location.origin`
    so scanning from a phone opens directly into `?page=join&session=<ROOM_ID>`.
    """
    _qr_card_component(
        key=f"ll_qr_card_{session_id}",
        data={
            "session_id": session_id,
            "fallback_origin": fallback_origin,
            "server_join_url": server_join_url,
            "qr_data_url": qr_data_url,
            "ui_lang": ui_lang,
        },
    )
