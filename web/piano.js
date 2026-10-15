/**
 * AI Instrumento - Grand Piano Sound Synthesizer & Visualizer
 * High-fidelity Acoustic Grand Piano Web Audio engine + 88-Key Waterfall Visualizer
 */

class GrandPianoAudio {
  constructor() {
    this.ctx = null;
    this.masterGain = null;
    this.compressor = null;
    this.activeVoices = new Map(); // noteNumber -> array of oscillators & gains
    this.volume = 0.8;
  }

  init() {
    if (this.ctx) return;
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    this.ctx = new AudioCtx();

    // Dynamics compressor to prevent clipping on heavy chords
    this.compressor = this.ctx.createDynamicsCompressor();
    this.compressor.threshold.setValueAtTime(-14, this.ctx.currentTime);
    this.compressor.knee.setValueAtTime(20, this.ctx.currentTime);
    this.compressor.ratio.setValueAtTime(10, this.ctx.currentTime);
    this.compressor.attack.setValueAtTime(0.002, this.ctx.currentTime);
    this.compressor.release.setValueAtTime(0.2, this.ctx.currentTime);

    this.masterGain = this.ctx.createGain();
    this.masterGain.gain.setValueAtTime(this.volume, this.ctx.currentTime);

    this.masterGain.connect(this.compressor);
    this.compressor.connect(this.ctx.destination);
  }

  setVolume(val) {
    this.volume = Math.max(0, Math.min(1, val));
    if (this.masterGain && this.ctx) {
      this.masterGain.gain.setTargetAtTime(this.volume, this.ctx.currentTime, 0.02);
    }
  }

  midiToFreq(midi) {
    return 440 * Math.pow(2, (midi - 69) / 12);
  }

  /**
   * High fidelity physical acoustic grand piano synthesis
   * Includes fundamental, inharmonic steel string harmonics, hammer strike transient thud,
   * and dual-stage decay envelope.
   */
  playNote(midi, velocity = 100, duration = 0.8) {
    if (!this.ctx) this.init();
    if (this.ctx.state === 'suspended') {
      this.ctx.resume();
    }

    const now = this.ctx.currentTime;
    const baseFreq = this.midiToFreq(midi);
    const velFactor = Math.pow(velocity / 127, 1.4); // Natural velocity curve

    // Key group for stopping
    const voiceId = `${midi}_${now}`;
    const voiceNodes = [];

    // 1. Hammer strike percussive noise transient (wood on felt thud)
    const hammerBuffer = this.ctx.createBuffer(1, this.ctx.sampleRate * 0.03, this.ctx.sampleRate);
    const hammerData = hammerBuffer.getChannelData(0);
    for (let i = 0; i < hammerData.length; i++) {
      hammerData[i] = (Math.random() * 2 - 1) * Math.exp(-i / (this.ctx.sampleRate * 0.006));
    }
    const hammerSource = this.ctx.createBufferSource();
    hammerSource.buffer = hammerBuffer;

    const hammerFilter = this.ctx.createBiquadFilter();
    hammerFilter.type = 'bandpass';
    hammerFilter.frequency.setValueAtTime(Math.min(1200, baseFreq * 1.5), now);
    hammerFilter.Q.setValueAtTime(1.5, now);

    const hammerGain = this.ctx.createGain();
    hammerGain.gain.setValueAtTime(velFactor * 0.15, now);
    hammerGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.03);

    hammerSource.connect(hammerFilter);
    hammerFilter.connect(hammerGain);
    hammerGain.connect(this.masterGain);
    hammerSource.start(now);
    voiceNodes.push(hammerSource);

    // 2. Harmonic Partial Synthesis (Fundamental + 6 Overtones)
    // Acoustic piano strings exhibit slight inharmonicity: f_n = n * f0 * sqrt(1 + B * n^2)
    const inharmonicity = 0.0002;
    const partials = [
      { n: 1, gain: 1.0, decayMult: 1.0 },
      { n: 2, gain: 0.65, decayMult: 0.85 },
      { n: 3, gain: 0.35, decayMult: 0.65 },
      { n: 4, gain: 0.18, decayMult: 0.45 },
      { n: 5, gain: 0.09, decayMult: 0.3 },
      { n: 6, gain: 0.04, decayMult: 0.2 },
    ];

    // Piano notes decay slower in lower registers, faster in treble
    const registerDecay = Math.max(0.5, Math.min(4.5, 4.0 - (midi - 21) * 0.035));
    const noteHoldTime = Math.max(0.2, duration);

    partials.forEach(p => {
      const osc = this.ctx.createOscillator();
      const pGain = this.ctx.createGain();

      const freqMultiplier = p.n * Math.sqrt(1 + inharmonicity * p.n * p.n);
      osc.frequency.setValueAtTime(baseFreq * freqMultiplier, now);
      // Triangle wave provides soft natural string timbre for partials
      osc.type = p.n === 1 ? 'sine' : 'triangle';

      const partialAmp = p.gain * velFactor * 0.28;
      pGain.gain.setValueAtTime(0.0001, now);
      // Fast attack
      pGain.gain.exponentialRampToValueAtTime(Math.max(0.0001, partialAmp), now + 0.004);
      
      // Dual stage decay: initial strike decay into sustained ring
      const decayTime = noteHoldTime * registerDecay * p.decayMult;
      const sustainLevel = Math.max(0.0001, partialAmp * 0.4);
      pGain.gain.exponentialRampToValueAtTime(sustainLevel, now + Math.min(0.25, noteHoldTime * 0.5));
      pGain.gain.exponentialRampToValueAtTime(0.00001, now + decayTime);

      osc.connect(pGain);
      pGain.connect(this.masterGain);

      osc.start(now);
      osc.stop(now + decayTime + 0.05);

      voiceNodes.push(osc);
    });

    this.activeVoices.set(voiceId, voiceNodes);
    setTimeout(() => {
      this.activeVoices.delete(voiceId);
    }, (noteHoldTime + 4.0) * 1000);
  }

  stopAll() {
    this.activeVoices.forEach(nodes => {
      nodes.forEach(n => {
        try { n.stop(); } catch (e) {}
      });
    });
    this.activeVoices.clear();
  }
}

/**
 * 88-Key Piano Keyboard Layout & DOM Renderer
 * Range: A0 (MIDI 21) to C8 (MIDI 108) = 88 Keys (52 White, 36 Black)
 */
class PianoKeyboard {
  constructor(containerEl, onKeyClick) {
    this.container = containerEl;
    this.onKeyClick = onKeyClick;
    this.keyElements = new Map(); // midiNumber -> DOM Element
    this.whiteKeyCount = 52;
    this.render();
  }

  render() {
    this.container.innerHTML = '';
    const noteNames = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
    let whiteIndex = 0;

    // First pass: create all white keys
    for (let midi = 21; midi <= 108; midi++) {
      const semitone = midi % 12;
      const isBlack = [1, 3, 6, 8, 10].includes(semitone);
      const octave = Math.floor(midi / 12) - 1;
      const noteName = `${noteNames[semitone]}${octave}`;

      if (!isBlack) {
        const whiteKey = document.createElement('div');
        whiteKey.className = 'key-white';
        whiteKey.dataset.midi = midi;
        whiteKey.dataset.whiteIndex = whiteIndex;
        whiteKey.innerHTML = `<span class="key-label">${noteName}</span>`;

        whiteKey.addEventListener('mousedown', (e) => {
          e.preventDefault();
          this.triggerKey(midi, 110);
        });

        this.container.appendChild(whiteKey);
        this.keyElements.set(midi, whiteKey);
        whiteIndex++;
      }
    }

    // Second pass: position black keys relative to white keys
    whiteIndex = 0;
    for (let midi = 21; midi <= 108; midi++) {
      const semitone = midi % 12;
      const isBlack = [1, 3, 6, 8, 10].includes(semitone);
      const octave = Math.floor(midi / 12) - 1;
      const noteName = `${noteNames[semitone]}${octave}`;

      if (!isBlack) {
        whiteIndex++;
      } else {
        const blackKey = document.createElement('div');
        blackKey.className = 'key-black';
        blackKey.dataset.midi = midi;
        blackKey.innerHTML = `<span class="key-label">${noteNames[semitone]}</span>`;

        // Calculate left percentage based on preceding white key
        // Total 52 white keys => each is (100 / 52)% wide ~ 1.923%
        const whiteWidthPercent = 100 / 52;
        const leftPercent = (whiteIndex * whiteWidthPercent) - (whiteWidthPercent * 0.32);
        blackKey.style.left = `${leftPercent}%`;

        blackKey.addEventListener('mousedown', (e) => {
          e.preventDefault();
          e.stopPropagation();
          this.triggerKey(midi, 110);
        });

        this.container.appendChild(blackKey);
        this.keyElements.set(midi, blackKey);
      }
    }
  }

  triggerKey(midi, vel = 100) {
    this.pressKey(midi);
    if (this.onKeyClick) {
      this.onKeyClick(midi, vel);
    }
    setTimeout(() => this.releaseKey(midi), 250);
  }

  pressKey(midi) {
    const el = this.keyElements.get(midi);
    if (el) el.classList.add('active');
  }

  releaseKey(midi) {
    const el = this.keyElements.get(midi);
    if (el) el.classList.remove('active');
  }

  clearAllKeys() {
    this.keyElements.forEach(el => el.classList.remove('active'));
  }

  toggleLabels(show) {
    this.container.querySelectorAll('.key-label').forEach(lbl => {
      lbl.style.display = show ? 'block' : 'none';
    });
  }

  getKeyXCenterPercent(midi) {
    const el = this.keyElements.get(midi);
    if (!el) return 50;
    const rect = el.getBoundingClientRect();
    const parentRect = this.container.getBoundingClientRect();
    const xCenter = (rect.left + rect.width / 2) - parentRect.left;
    return (xCenter / parentRect.width) * 100;
  }
}

/**
 * Waterfall Canvas Visualizer (Synthesia Style)
 */
class WaterfallVisualizer {
  constructor(canvasEl, keyboard) {
    this.canvas = canvasEl;
    this.ctx = canvasEl.getContext('2d');
    this.keyboard = keyboard;
    this.notes = []; // [{note, start, duration, velocity, channel, is_black}]
    this.lookAheadSec = 3.5; // Seconds of incoming notes visible on canvas
    this.resize();
    window.addEventListener('resize', () => this.resize());
  }

  resize() {
    const rect = this.canvas.parentElement.getBoundingClientRect();
    this.canvas.width = rect.width * window.devicePixelRatio;
    this.canvas.height = rect.height * window.devicePixelRatio;
    this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    this.width = rect.width;
    this.height = rect.height;
  }

  setNotes(notes) {
    this.notes = notes || [];
  }

  render(currentTime) {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.width, this.height);

    // Subtle background guidelines for octaves
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
    ctx.lineWidth = 1;
    for (let cMidi = 24; cMidi <= 108; cMidi += 12) {
      const pct = this.keyboard.getKeyXCenterPercent(cMidi);
      const x = (pct / 100) * this.width;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, this.height);
      ctx.stroke();
    }

    if (!this.notes.length) return;

    const visibleMinTime = currentTime - 0.2;
    const visibleMaxTime = currentTime + this.lookAheadSec;

    // Bottom edge of canvas corresponds to currentTime
    const h = this.height;
    const timeScale = h / this.lookAheadSec;

    // Filter and render visible notes
    for (let i = 0; i < this.notes.length; i++) {
      const n = this.notes[i];
      const noteEnd = n.start + n.duration;

      // Note hasn't appeared yet or has already passed
      if (noteEnd < visibleMinTime || n.start > visibleMaxTime) continue;

      const pct = this.keyboard.getKeyXCenterPercent(n.note);
      const xCenter = (pct / 100) * this.width;
      const keyWidth = (this.width / 52) * (n.is_black ? 0.65 : 0.85);
      const x = xCenter - keyWidth / 2;

      // Y coordinates: notes travel downwards towards y = h
      const yBottom = h - ((n.start - currentTime) * timeScale);
      const yTop = h - ((noteEnd - currentTime) * timeScale);
      const noteHeight = Math.max(6, yBottom - yTop);

      // Gradient color based on pitch & grand piano warmth
      const isCurrentlyPlaying = (currentTime >= n.start && currentTime <= noteEnd);
      
      const grad = ctx.createLinearGradient(x, yTop, x + keyWidth, yBottom);
      if (isCurrentlyPlaying) {
        grad.addColorStop(0, '#fff4cc');
        grad.addColorStop(0.5, '#ffd043');
        grad.addColorStop(1, '#ff9900');
      } else if (n.is_black) {
        grad.addColorStop(0, '#aa841c');
        grad.addColorStop(1, '#664d0a');
      } else {
        grad.addColorStop(0, '#f9dd7b');
        grad.addColorStop(1, '#c29724');
      }

      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.roundRect(x, yTop, keyWidth, noteHeight, 4);
      ctx.fill();

      // Border glow when actively hitting the keyboard
      if (isCurrentlyPlaying) {
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Hit flash at bottom
        ctx.fillStyle = 'rgba(255, 220, 100, 0.4)';
        ctx.fillRect(x - 2, h - 4, keyWidth + 4, 4);
      }
    }
  }
}

/**
 * Main Application Orchestrator
 */
class GrandPianoStudio {
  constructor() {
    this.audio = new GrandPianoAudio();
    this.keyboard = new PianoKeyboard(
      document.getElementById('pianoKeyboard'),
      (midi, vel) => this.audio.playNote(midi, vel, 0.6)
    );
    this.visualizer = new WaterfallVisualizer(
      document.getElementById('waterfallCanvas'),
      this.keyboard
    );

    this.files = [];
    this.currentFile = null;
    this.parsedData = null;
    this.filteredNotes = [];
    this.isPlaying = false;
    this.playbackTime = 0.0;
    this.duration = 0.0;
    this.speed = 1.0;
    this.volume = 0.8;
    this.soundEngine = 'web'; // 'web' or 'native'
    this.lastFrameTime = 0;
    this.noteTriggerIndex = 0;
    this.activeNoteNumbers = new Set();
    this.pianoTracksOnly = false;

    this.initElements();
    this.attachEvents();
    this.loadFileList();
    this.startLoop();
  }

  initElements() {
    this.el = {
      midiSelect: document.getElementById('midiSelect'),
      btnRefresh: document.getElementById('btnRefreshFiles'),
      dropBadge: document.getElementById('dropBadge'),
      songTitle: document.getElementById('songTitle'),
      statDuration: document.getElementById('statDuration'),
      statNotes: document.getElementById('statNotes'),
      statTracks: document.getElementById('statTracks'),
      statActiveNotes: document.getElementById('statActiveNotes'),
      overlay: document.getElementById('visualizerOverlay'),
      overlayPlayBtn: document.getElementById('overlayPlayBtn'),
      btnPlayPause: document.getElementById('btnPlayPause'),
      btnStop: document.getElementById('btnStop'),
      btnPrev: document.getElementById('btnPrev'),
      seekSlider: document.getElementById('seekSlider'),
      seekProgress: document.getElementById('seekProgressFill'),
      currentTime: document.getElementById('currentTimeDisplay'),
      totalTime: document.getElementById('totalTimeDisplay'),
      tempoSlider: document.getElementById('tempoSlider'),
      tempoValue: document.getElementById('tempoValue'),
      volumeSlider: document.getElementById('volumeSlider'),
      volumeValue: document.getElementById('volumeValue'),
      pianoOnlyToggle: document.getElementById('pianoOnlyToggle'),
      keyLabelsToggle: document.getElementById('keyLabelsToggle'),
      engineWeb: document.getElementById('engineWeb'),
      engineNative: document.getElementById('engineNative'),
    };
  }

  attachEvents() {
    // Play / Pause / Stop
    this.el.btnPlayPause.addEventListener('click', () => this.togglePlay());
    this.el.overlayPlayBtn.addEventListener('click', () => this.play());
    this.el.btnStop.addEventListener('click', () => this.stop());
    this.el.btnPrev.addEventListener('click', () => this.restart());

    // File selection
    this.el.midiSelect.addEventListener('change', (e) => {
      const selected = e.target.value;
      if (selected) this.loadFile(selected);
    });

    this.el.btnRefresh.addEventListener('click', () => this.loadFileList());

    // Timeline Scrubbing
    this.el.seekSlider.addEventListener('input', (e) => {
      this.seekTo((parseFloat(e.target.value) / 100) * this.duration);
    });

    // Speed / Tempo
    document.querySelectorAll('.btn-chip[data-speed]').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.btn-chip[data-speed]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const s = parseFloat(btn.dataset.speed);
        this.setSpeed(s);
        this.el.tempoSlider.value = s;
      });
    });

    this.el.tempoSlider.addEventListener('input', (e) => {
      this.setSpeed(parseFloat(e.target.value));
    });

    // Volume
    this.el.volumeSlider.addEventListener('input', (e) => {
      const v = parseFloat(e.target.value);
      this.volume = v;
      this.audio.setVolume(v);
      this.el.volumeValue.textContent = `${Math.round(v * 100)}%`;
    });

    // Toggles
    this.el.keyLabelsToggle.addEventListener('change', (e) => {
      this.keyboard.toggleLabels(e.target.checked);
    });

    this.el.pianoOnlyToggle.addEventListener('change', (e) => {
      this.pianoTracksOnly = e.target.checked;
      this.filterNotes();
    });

    // Sound engine
    this.el.engineWeb.addEventListener('change', () => {
      this.soundEngine = 'web';
    });
    this.el.engineNative.addEventListener('change', () => {
      this.soundEngine = 'native';
    });

    // Drag and drop MIDI file
    window.addEventListener('dragover', (e) => {
      e.preventDefault();
      this.el.dropBadge.classList.add('dragover');
    });

    window.addEventListener('dragleave', () => {
      this.el.dropBadge.classList.remove('dragover');
    });

    window.addEventListener('drop', (e) => {
      e.preventDefault();
      this.el.dropBadge.classList.remove('dragover');
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        this.uploadMidiFile(e.dataTransfer.files[0]);
      }
    });

    // Keyboard Spacebar play/pause
    window.addEventListener('keydown', (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
      if (e.code === 'Space') {
        e.preventDefault();
        this.togglePlay();
      }
    });
  }

  setSpeed(s) {
    this.speed = s;
    this.el.tempoValue.textContent = `${s.toFixed(2)}x`;
  }

  async loadFileList() {
    try {
      const res = await fetch('/api/files');
      const data = await res.json();
      this.files = data.files || [];

      this.el.midiSelect.innerHTML = '';
      if (!this.files.length) {
        this.el.midiSelect.innerHTML = '<option value="">No .mid files found in directory</option>';
        return;
      }

      this.files.forEach(f => {
        const opt = document.createElement('option');
        opt.value = f.name;
        opt.textContent = `${f.name} (${f.total_notes || 0} notes)`;
        this.el.midiSelect.appendChild(opt);
      });

      // Default to jan gan man.mid or first file
      const defaultFile = this.files.find(f => f.name.toLowerCase().includes('jan gan man')) || this.files[0];
      if (defaultFile) {
        this.el.midiSelect.value = defaultFile.name;
        this.loadFile(defaultFile.name);
      }
    } catch (err) {
      console.warn("Could not load /api/files, operating in offline/demo mode:", err);
    }
  }

  async loadFile(fileName) {
    this.stop();
    this.currentFile = fileName;
    this.el.songTitle.textContent = fileName;

    try {
      const res = await fetch(`/api/parse/${encodeURIComponent(fileName)}`);
      this.parsedData = await res.json();
      this.duration = this.parsedData.duration || 10;
      this.el.statDuration.textContent = this.formatTime(this.duration);
      this.el.totalTime.textContent = this.formatTime(this.duration);
      this.el.statNotes.textContent = this.parsedData.total_notes;

      // Extract piano track info
      const pianoTracks = this.parsedData.tracks.filter(t => t.is_piano);
      if (pianoTracks.length) {
        this.el.statTracks.textContent = `${pianoTracks.length} tracks (${pianoTracks[0].name})`;
      } else {
        this.el.statTracks.textContent = "All mapped to Grand Piano";
      }

      this.filterNotes();
      this.seekTo(0);
    } catch (err) {
      console.error("Failed to parse MIDI file:", err);
    }
  }

  filterNotes() {
    if (!this.parsedData) return;
    if (this.pianoTracksOnly) {
      // Find tracks identified as piano
      const pianoTrackNames = this.parsedData.tracks.filter(t => t.is_piano).map(t => t.name.toLowerCase());
      this.filteredNotes = this.parsedData.notes.filter(n => {
        // If track name matches or track id
        return true; // Keep all or isolate
      });
    } else {
      this.filteredNotes = this.parsedData.notes;
    }
    this.visualizer.setNotes(this.filteredNotes);
  }

  async uploadMidiFile(file) {
    if (!file.name.toLowerCase().endsWith('.mid') && !file.name.toLowerCase().endsWith('.midi')) {
      alert("Please upload a .mid or .midi file.");
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      this.el.dropBadge.textContent = "Uploading...";
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      });
      const result = await res.json();
      if (result.success) {
        this.el.dropBadge.textContent = "Drop .mid here";
        await this.loadFileList();
        this.el.midiSelect.value = result.fileName;
        this.loadFile(result.fileName);
      }
    } catch (err) {
      this.el.dropBadge.textContent = "Drop .mid here";
      console.error("Upload error:", err);
    }
  }

  togglePlay() {
    if (this.isPlaying) {
      this.pause();
    } else {
      this.play();
    }
  }

  play() {
    if (this.isPlaying) return;
    this.audio.init();
    this.isPlaying = true;
    this.el.overlay.classList.add('hidden');
    this.el.btnPlayPause.textContent = "⏸";

    if (this.soundEngine === 'native') {
      fetch('/api/play-native', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file: this.currentFile, speed: this.speed })
      }).catch(err => console.warn(err));
    }
  }

  pause() {
    this.isPlaying = false;
    this.el.btnPlayPause.textContent = "▶";
    this.keyboard.clearAllKeys();
    this.activeNoteNumbers.clear();
    this.el.statActiveNotes.textContent = '0';
    if (this.soundEngine === 'native') {
      fetch('/api/pause-native', { method: 'POST' }).catch(() => {});
    }
  }

  stop() {
    this.pause();
    this.playbackTime = 0.0;
    this.noteTriggerIndex = 0;
    this.updateTimelineUI();
    this.visualizer.render(0);
    this.el.overlay.classList.remove('hidden');
    if (this.soundEngine === 'native') {
      fetch('/api/stop-native', { method: 'POST' }).catch(() => {});
    }
  }

  restart() {
    this.seekTo(0);
    this.play();
  }

  seekTo(seconds) {
    this.playbackTime = Math.max(0, Math.min(this.duration, seconds));
    this.audio.stopAll();
    this.keyboard.clearAllKeys();
    this.activeNoteNumbers.clear();

    // Recalculate note trigger index for fast playback search
    this.noteTriggerIndex = 0;
    while (
      this.noteTriggerIndex < this.filteredNotes.length &&
      this.filteredNotes[this.noteTriggerIndex].start < this.playbackTime
    ) {
      this.noteTriggerIndex++;
    }

    this.updateTimelineUI();
    this.visualizer.render(this.playbackTime);
  }

  updateTimelineUI() {
    this.el.currentTime.textContent = this.formatTime(this.playbackTime);
    const percent = this.duration > 0 ? (this.playbackTime / this.duration) * 100 : 0;
    this.el.seekSlider.value = percent;
    this.el.seekProgress.style.width = `${percent}%`;
  }

  formatTime(sec) {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }

  startLoop() {
    const loop = (timestamp) => {
      if (!this.lastFrameTime) this.lastFrameTime = timestamp;
      const dt = (timestamp - this.lastFrameTime) / 1000;
      this.lastFrameTime = timestamp;

      if (this.isPlaying) {
        this.playbackTime += dt * this.speed;

        if (this.playbackTime >= this.duration) {
          this.stop();
        } else {
          this.processActiveNotes();
          this.updateTimelineUI();
        }
      }

      this.visualizer.render(this.playbackTime);
      requestAnimationFrame(loop);
    };

    requestAnimationFrame(loop);
  }

  processActiveNotes() {
    // 1. Trigger newly starting notes
    while (
      this.noteTriggerIndex < this.filteredNotes.length &&
      this.filteredNotes[this.noteTriggerIndex].start <= this.playbackTime
    ) {
      const n = this.filteredNotes[this.noteTriggerIndex];

      // Only trigger if note hasn't already expired
      if (this.playbackTime < n.start + n.duration) {
        if (this.soundEngine === 'web') {
          this.audio.playNote(n.note, n.velocity, n.duration);
        }
        this.keyboard.pressKey(n.note);
        this.activeNoteNumbers.add(n.note);
      }
      this.noteTriggerIndex++;
    }

    // 2. Release keys whose duration has expired
    this.activeNoteNumbers.forEach(noteNum => {
      // Check if any note is still active for this pitch
      const isStillActive = this.filteredNotes.some(
        n => n.note === noteNum &&
             this.playbackTime >= n.start &&
             this.playbackTime <= (n.start + n.duration)
      );
      if (!isStillActive) {
        this.keyboard.releaseKey(noteNum);
        this.activeNoteNumbers.delete(noteNum);
      }
    });

    this.el.statActiveNotes.textContent = this.activeNoteNumbers.size.toString();
  }
}

// Start application when DOM is ready
window.addEventListener('DOMContentLoaded', () => {
  window.studio = new GrandPianoStudio();
});
