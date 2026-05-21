/*
  Command Center Radio - JavaScript
  Paste into the Business Text panel "JavaScript Code" -> "After Content Ready" hook.
  The plugin invokes this with a `context` object that exposes `context.element` -
  the panel's root DOM node. All wiring is scoped to that node.

  Why this design:
    - One persistent <audio id="cc-audio"> element. We never replace it; we only
      swap audio.src. This eliminates the popup-window / "new player every click"
      behavior caused by anchor tags or per-button <audio> elements.
    - All click handlers are attached here (not inline) so Grafana's CSP can't
      strip them, and so we control event.preventDefault().
    - Idempotent: a marker on the root element prevents double-binding if the
      panel re-runs this hook on a refresh.
    - Visualizer is opt-in. createMediaElementSource() requires CORS-clean audio,
      so we only enable it on user request and gracefully fall back if blocked.
*/

(function initCommandCenterRadio() {
  const root = context.element.querySelector('#cc-radio');
  if (!root) return;
  if (root._ccInit) return;          // already wired in this DOM
  root._ccInit = true;

  const audio        = root.querySelector('#cc-audio');
  const nowPlaying   = root.querySelector('#cc-now-playing');
  const nowUrl       = root.querySelector('#cc-now-url');
  const statusLight  = root.querySelector('#cc-status-light');
  const statusText   = root.querySelector('#cc-status-text');
  const playPauseBtn = root.querySelector('#cc-play-pause');
  const stopBtn      = root.querySelector('#cc-stop');
  const volumeInput  = root.querySelector('#cc-volume');
  const volumeRead   = root.querySelector('#cc-volume-readout');
  const vizToggle    = root.querySelector('#cc-viz-toggle');
  const vizState     = root.querySelector('#cc-viz-state');
  const canvas       = root.querySelector('#cc-visualizer');
  const stationBtns  = Array.from(root.querySelectorAll('.cc-station'));

  // ---- State persisted on the DOM node so re-renders without a full reload
  //      can find the last selection. (Audio element is recreated on full
  //      content re-render either way - disable panel auto-refresh.)
  const state = root._ccState = root._ccState || {
    currentUrl:  null,
    currentName: null,
    vizEnabled:  false,
  };

  // ---- Status helpers
  function setStatus(text, mode) {
    statusText.textContent = text;
    statusLight.classList.remove('cc-status-standby', 'cc-status-live', 'cc-status-error');
    statusLight.classList.add('cc-status-' + (mode || 'standby'));
  }

  function setPlayPauseLabel(playing) {
    const icon  = playPauseBtn.querySelector('.cc-btn-icon');
    const label = playPauseBtn.querySelector('.cc-btn-label');
    icon.innerHTML  = playing ? '&#10074;&#10074;' : '&#9658;';
    label.textContent = playing ? 'PAUSE' : 'PLAY';
  }

  function markActive(url) {
    stationBtns.forEach(b => {
      b.classList.toggle('cc-active', b.dataset.stationUrl === url);
    });
  }

  // ---- Station switching
  function selectStation(url, name) {
    state.currentUrl  = url;
    state.currentName = name;
    nowPlaying.textContent = name;
    nowUrl.textContent     = url;
    markActive(url);

    // Setting src + load() is the safe way to retarget a live stream.
    audio.src = url;
    audio.load();
    setStatus('ACQUIRING SIGNAL...', 'standby');
    const p = audio.play();
    if (p && typeof p.catch === 'function') {
      p.catch(err => {
        setStatus('FAULT: ' + (err && err.message ? err.message : 'play blocked'), 'error');
      });
    }
  }

  stationBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const url  = btn.dataset.stationUrl;
      const name = btn.dataset.stationName || 'UNKNOWN';
      if (!url) return;
      selectStation(url, name);
    });
  });

  // ---- Transport controls
  playPauseBtn.addEventListener('click', (e) => {
    e.preventDefault();
    if (!state.currentUrl) {
      // Nothing selected yet - default to first station.
      const first = stationBtns[0];
      if (first) {
        selectStation(first.dataset.stationUrl, first.dataset.stationName);
      }
      return;
    }
    if (audio.paused) {
      audio.play().catch(err => setStatus('FAULT: ' + err.message, 'error'));
    } else {
      audio.pause();
    }
  });

  stopBtn.addEventListener('click', (e) => {
    e.preventDefault();
    audio.pause();
    // Fully detach the stream so we don't keep buffering in the background.
    audio.removeAttribute('src');
    audio.load();
    state.currentUrl = null;
    nowPlaying.textContent = '--- NO SIGNAL ---';
    nowUrl.textContent     = 'awaiting selection';
    markActive(null);
    setStatus('STANDBY', 'standby');
    setPlayPauseLabel(false);
  });

  // ---- Volume
  function applyVolume(v) {
    audio.volume = v;
    volumeRead.textContent = String(Math.round(v * 100));
  }
  volumeInput.addEventListener('input', (e) => applyVolume(parseFloat(e.target.value)));
  applyVolume(parseFloat(volumeInput.value));

  // ---- Audio element events drive the UI
  audio.addEventListener('playing', () => { setPlayPauseLabel(true);  setStatus('TRANSMITTING', 'live'); });
  audio.addEventListener('pause',   () => { setPlayPauseLabel(false); if (state.currentUrl) setStatus('PAUSED', 'standby'); });
  audio.addEventListener('waiting', () => { setStatus('BUFFERING...', 'standby'); });
  audio.addEventListener('stalled', () => { setStatus('STALLED', 'error'); });
  audio.addEventListener('error',   () => { setStatus('SIGNAL LOST', 'error'); setPlayPauseLabel(false); });

  // ---- Visualizer (opt-in, CORS-aware)
  const ctx2d = canvas.getContext('2d');
  let audioCtx = null;
  let analyser = null;
  let dataArray = null;
  let rafId = null;

  function resizeCanvas() {
    const rect = canvas.getBoundingClientRect();
    // Account for devicePixelRatio for crisp bars on retina / Pi touchscreens.
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width  = Math.max(1, Math.floor(rect.width  * dpr));
    canvas.height = Math.max(1, Math.floor(rect.height * dpr));
    ctx2d.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  resizeCanvas();
  if (typeof ResizeObserver !== 'undefined') {
    new ResizeObserver(resizeCanvas).observe(canvas);
  }

  function drawIdle() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    ctx2d.clearRect(0, 0, w, h);
    // Faint center-line "no signal" sweep
    ctx2d.strokeStyle = 'rgba(255,176,0,0.25)';
    ctx2d.lineWidth = 1;
    ctx2d.beginPath();
    ctx2d.moveTo(0, h / 2);
    ctx2d.lineTo(w, h / 2);
    ctx2d.stroke();
  }
  drawIdle();

  function drawBars() {
    rafId = requestAnimationFrame(drawBars);
    if (!analyser || !dataArray) return;
    analyser.getByteFrequencyData(dataArray);
    const w = canvas.clientWidth, h = canvas.clientHeight;
    ctx2d.clearRect(0, 0, w, h);

    const bars = dataArray.length;
    const barW = w / bars;
    for (let i = 0; i < bars; i++) {
      const v = dataArray[i] / 255;
      const barH = Math.max(1, v * h);
      // Amber → green gradient as energy rises. Pure terminal vibes.
      const hue = 40 - (v * 40);
      ctx2d.fillStyle = `hsl(${hue}, 100%, ${35 + v * 25}%)`;
      ctx2d.fillRect(i * barW + 0.5, h - barH, Math.max(1, barW - 1), barH);
    }
  }

  function enableVisualizer() {
    if (audioCtx) return true;
    try {
      // CORS: required for AnalyserNode to actually receive sample data
      // from a cross-origin <audio>. SomaFM serves CORS headers; if a stream
      // does not, the audio will be silenced and we'll auto-disable below.
      audio.crossOrigin = 'anonymous';
      // Re-load current src under the new CORS mode if one is playing
      if (state.currentUrl) {
        const wasPlaying = !audio.paused;
        audio.src = state.currentUrl;
        audio.load();
        if (wasPlaying) audio.play().catch(() => {});
      }

      const AC = window.AudioContext || window.webkitAudioContext;
      audioCtx  = new AC();
      const src = audioCtx.createMediaElementSource(audio);
      analyser  = audioCtx.createAnalyser();
      analyser.fftSize = 128;
      src.connect(analyser);
      analyser.connect(audioCtx.destination);
      dataArray = new Uint8Array(analyser.frequencyBinCount);
      drawBars();
      return true;
    } catch (err) {
      audioCtx = null; analyser = null; dataArray = null;
      return false;
    }
  }

  function disableVisualizer() {
    if (rafId) cancelAnimationFrame(rafId);
    rafId = null;
    if (audioCtx) {
      try { audioCtx.close(); } catch (_) {}
    }
    audioCtx = null; analyser = null; dataArray = null;
    audio.removeAttribute('crossorigin');
    if (state.currentUrl) {
      const wasPlaying = !audio.paused;
      audio.src = state.currentUrl;
      audio.load();
      if (wasPlaying) audio.play().catch(() => {});
    }
    drawIdle();
  }

  vizToggle.addEventListener('click', (e) => {
    e.preventDefault();
    if (state.vizEnabled) {
      state.vizEnabled = false;
      vizState.textContent = 'OFF';
      disableVisualizer();
    } else {
      const ok = enableVisualizer();
      state.vizEnabled = ok;
      vizState.textContent = ok ? 'ON' : 'BLOCKED';
    }
  });
})();
