/**
 * AI Instrumento - Smart Grand Piano Sound Synthesizer & Visualizer
 * High-fidelity Acoustic Grand Piano Web Audio engine + 88-Key Waterfall Visualizer
 * with Smart Track Identification and Solo Piano Lead Focus.
 */

class GrandPianoAudio {
  constructor() {
    this.ctx = null;
    this.masterGain = null;
    this.compressor = null;
    this.activeVoices = new Map();
    this.volume = 0.8;
  }

  init() {
    if (this.ctx) return;
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    this.ctx = new AudioCtx();

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

  playNote(midi, velocity = 100, duration = 0.8) {
    if (!this.ctx) this.init();
    if (this.ctx.state === 'suspended') {
      this.ctx.resume();
    }

    const now = this.ctx.currentTime;
    const baseFreq = this.midiToFreq(midi);
    const velFactor = Math.pow(velocity / 127, 1.4);

    const voiceId = `${midi}_${now}`;
    const voiceNodes = [];

    // 1. Hammer strike percussive noise transient
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

    // 2. Harmonic Partial Synthesis
    const inharmonicity = 0.0002;
    const partials = [
      { n: 1, gain: 1.0, decayMult: 1.0 },
      { n: 2, gain: 0.65, decayMult: 0.85 },
      { n: 3, gain: 0.35, decayMult: 0.65 },
      { n: 4, gain: 0.18, decayMult: 0.45 },
      { n: 5, gain: 0.09, decayMult: 0.3 },
      { n: 6, gain: 0.04, decayMult: 0.2 },
    ];

    const registerDecay = Math.max(0.5, Math.min(4.5, 4.0 - (midi - 21) * 0.035));
    const noteHoldTime = Math.max(0.2, duration);

    partials.forEach(p => {
      const osc = this.ctx.createOscillator();
      const pGain = this.ctx.createGain();

      const freqMultiplier = p.n * Math.sqrt(1 + inharmonicity * p.n * p.n);
      osc.frequency.setValueAtTime(baseFreq * freqMultiplier, now);
      osc.type = p.n === 1 ? 'sine' : 'triangle';

      const partialAmp = p.gain * velFactor * 0.28;
      pGain.gain.setValueAtTime(0.0001, now);
      pGain.gain.exponentialRampToValueAtTime(Math.max(0.0001, partialAmp), now + 0.004);
      
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

class PianoKeyboard {
  constructor(containerEl, onKeyClick) {
    this.container = containerEl;
    this.onKeyClick = onKeyClick;
    this.keyElements = new Map();
    this.whiteKeyCount = 52;
    this.render();
  }

  render() {
    this.container.innerHTML = '';
    const noteNames = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
    let whiteIndex = 0;

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

    whiteIndex = 0;
    for (let midi = 21; midi <= 108; midi++) {
      const semitone = midi % 12;
      const isBlack = [1, 3, 6, 8, 10].includes(semitone);
      const noteNames = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

      if (!isBlack) {
        whiteIndex++;
      } else {
        const blackKey = document.createElement('div');
        blackKey.className = 'key-black';
        blackKey.dataset.midi = midi;
        blackKey.innerHTML = `<span class="key-label">${noteNames[semitone]}</span>`;

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

class WaterfallVisualizer {
  constructor(canvasEl, keyboard) {
    this.canvas = canvasEl;
    this.ctx = canvasEl.getContext('2d');
    this.keyboard = keyboard;
    this.notes = [];
    this.lookAheadSec = 3.5;
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
    const h = this.height;
    const timeScale = h / this.lookAheadSec;

    for (let i = 0; i < this.notes.length; i++) {
      const n = this.notes[i];
      const noteEnd = n.start + n.duration;

      if (noteEnd < visibleMinTime || n.start > visibleMaxTime) continue;

      const pct = this.keyboard.getKeyXCenterPercent(n.note);
      const xCenter = (pct / 100) * this.width;
      const keyWidth = (this.width / 52) * (n.is_black ? 0.65 : 0.85);
      const x = xCenter - keyWidth / 2;

      const yBottom = h - ((n.start - currentTime) * timeScale);
      const yTop = h - ((noteEnd - currentTime) * timeScale);
      const noteHeight = Math.max(6, yBottom - yTop);

      const isCurrentlyPlaying = (currentTime >= n.start && currentTime <= noteEnd);
      
      const grad = ctx.createLinearGradient(x, yTop, x + keyWidth, yBottom);
      if (isCurrentlyPlaying) {
        grad.addColorStop(0, '#ffffff');
        grad.addColorStop(0.4, '#ffd043');
        grad.addColorStop(1, '#ff8800');
      } else if (n.is_piano_lead) {
        // High visibility radiant gold for piano lead
        grad.addColorStop(0, '#ffea9f');
        grad.addColorStop(0.6, '#d4af37');
        grad.addColorStop(1, '#8a6a12');
      } else if (n.is_black) {
        grad.addColorStop(0, '#785b1a');
        grad.addColorStop(1, '#44330d');
      } else {
        grad.addColorStop(0, '#93a1b8');
        grad.addColorStop(1, '#4b5563');
      }

      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.roundRect(x, yTop, keyWidth, noteHeight, 4);
      ctx.fill();

      if (isCurrentlyPlaying) {
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.8;
        ctx.stroke();

        ctx.fillStyle = 'rgba(255, 230, 120, 0.5)';
        ctx.fillRect(x - 3, h - 5, keyWidth + 6, 5);
      }
    }
  }
}

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
    this.playMode = 'lead'; // 'lead', 'track', 'all'
    this.selectedTrackId = null;

    this.isPlaying = false;
    this.playbackTime = 0.0;
    this.duration = 0.0;
    this.speed = 1.0;
    this.volume = 0.8;
    this.soundEngine = 'web';
    this.lastFrameTime = 0;
    this.noteTriggerIndex = 0;
    this.activeNoteNumbers = new Set();

    this.initElements();
    this.attachEvents();
    this.loadFileList();
    this.startLoop();
  }

  initElements() {
    this.el = {
      midiSelect: document.getElementById('midiSelect'),
      btnRefresh: document.getElementById('btnRefreshFiles'),
      btnExportLead: document.getElementById('btnExportLead'),
      btnInspectTracks: document.getElementById('btnInspectTracks'),
      trackCountBadge: document.getElementById('trackCountBadge'),
      dropBadge: document.getElementById('dropBadge'),
      
      tabLead: document.getElementById('tabLead'),
      tabTrack: document.getElementById('tabTrack'),
      tabAll: document.getElementById('tabAll'),
      trackSelectWrapper: document.getElementById('trackSelectWrapper'),
      trackSelect: document.getElementById('trackSelect'),
      leadStatusText: document.getElementById('leadStatusText'),

      songTitle: document.getElementById('songTitle'),
      statDuration: document.getElementById('statDuration'),
      statNotes: document.getElementById('statNotes'),
      statLeadNotes: document.getElementById('statLeadNotes'),
      statActiveNotes: document.getElementById('statActiveNotes'),
      
      overlay: document.getElementById('visualizerOverlay'),
      overlayPlayBtn: document.getElementById('overlayPlayBtn'),
      overlayBtnText: document.getElementById('overlayBtnText'),
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
      keyLabelsToggle: document.getElementById('keyLabelsToggle'),
      engineWeb: document.getElementById('engineWeb'),
      engineNative: document.getElementById('engineNative'),

      trackModal: document.getElementById('trackModal'),
      modalSongName: document.getElementById('modalSongName'),
      modalCloseBtn: document.getElementById('modalCloseBtn'),
      modalCloseBtn2: document.getElementById('modalCloseBtn2'),
      modalExportBtn: document.getElementById('modalExportBtn'),
      trackTableBody: document.getElementById('trackTableBody'),
    };
  }

  attachEvents() {
    this.el.btnPlayPause.addEventListener('click', () => this.togglePlay());
    this.el.overlayPlayBtn.addEventListener('click', () => this.play());
    this.el.btnStop.addEventListener('click', () => this.stop());
    this.el.btnPrev.addEventListener('click', () => this.restart());

    this.el.midiSelect.addEventListener('change', (e) => {
      if (e.target.value) this.loadFile(e.target.value);
    });

    this.el.btnRefresh.addEventListener('click', () => this.loadFileList());

    // Smart Mode Tabs
    this.el.tabLead.addEventListener('click', () => this.setMode('lead'));
    this.el.tabTrack.addEventListener('click', () => this.setMode('track'));
    this.el.tabAll.addEventListener('click', () => this.setMode('all'));

    // Track Selector
    this.el.trackSelect.addEventListener('change', (e) => {
      this.selectedTrackId = parseInt(e.target.value);
      this.filterNotes();
      this.seekTo(0);
    });

    // Modal
    this.el.btnInspectTracks.addEventListener('click', () => this.openTrackModal());
    this.el.modalCloseBtn.addEventListener('click', () => this.closeTrackModal());
    this.el.modalCloseBtn2.addEventListener('click', () => this.closeTrackModal());
    this.el.trackModal.addEventListener('click', (e) => {
      if (e.target === this.el.trackModal) this.closeTrackModal();
    });

    // Export Lead
    this.el.btnExportLead.addEventListener('click', () => this.exportLeadMidi());
    this.el.modalExportBtn.addEventListener('click', () => this.exportLeadMidi());

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

    this.el.volumeSlider.addEventListener('input', (e) => {
      const v = parseFloat(e.target.value);
      this.volume = v;
      this.audio.setVolume(v);
      this.el.volumeValue.textContent = `${Math.round(v * 100)}%`;
    });

    this.el.keyLabelsToggle.addEventListener('change', (e) => {
      this.keyboard.toggleLabels(e.target.checked);
    });

    this.el.engineWeb.addEventListener('change', () => {
      this.soundEngine = 'web';
    });
    this.el.engineNative.addEventListener('change', () => {
      this.soundEngine = 'native';
    });

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

    window.addEventListener('keydown', (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
      if (e.code === 'Space') {
        e.preventDefault();
        this.togglePlay();
      }
    });
  }

  setMode(mode) {
    this.playMode = mode;
    this.el.tabLead.classList.toggle('active', mode === 'lead');
    this.el.tabTrack.classList.toggle('active', mode === 'track');
    this.el.tabAll.classList.toggle('active', mode === 'all');

    this.el.trackSelectWrapper.style.display = (mode === 'track') ? 'flex' : 'none';

    this.filterNotes();
    this.seekTo(0);
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
        const tag = f.is_lead_file ? ' [SOLO LEAD]' : '';
        opt.textContent = `${f.name}${tag} (${f.total_notes || 0} notes)`;
        this.el.midiSelect.appendChild(opt);
      });

      // Default to jan gan man.mid or first file
      const defaultFile = this.files.find(f => f.name.toLowerCase().includes('jan gan man') && !f.is_lead_file) || this.files[0];
      if (defaultFile) {
        this.el.midiSelect.value = defaultFile.name;
        this.loadFile(defaultFile.name);
      }
    } catch (err) {
      console.warn("Could not load /api/files:", err);
    }
  }

  async loadFile(fileName) {
    this.stop();
    this.currentFile = fileName;
    this.el.songTitle.textContent = fileName;
    this.el.modalSongName.textContent = fileName;

    try {
      const res = await fetch(`/api/parse/${encodeURIComponent(fileName)}`);
      this.parsedData = await res.json();
      this.duration = this.parsedData.duration || 10;
      this.el.statDuration.textContent = this.formatTime(this.duration);
      this.el.totalTime.textContent = this.formatTime(this.duration);
      this.el.statLeadNotes.textContent = `${this.parsedData.lead_notes_count} notes`;
      this.el.trackCountBadge.textContent = this.parsedData.tracks.length;

      // Populate track selector
      this.el.trackSelect.innerHTML = '';
      this.parsedData.tracks.forEach(t => {
        const opt = document.createElement('option');
        opt.value = t.id;
        const leadStar = t.is_piano_lead ? '★ ' : '';
        opt.textContent = `${leadStar}Track ${t.id}: ${t.name} (${t.notes_count} notes)`;
        this.el.trackSelect.appendChild(opt);
      });

      if (this.parsedData.lead_track_ids && this.parsedData.lead_track_ids.length > 0) {
        this.selectedTrackId = this.parsedData.lead_track_ids[0];
        this.el.trackSelect.value = this.selectedTrackId;
      } else if (this.parsedData.tracks.length > 0) {
        this.selectedTrackId = this.parsedData.tracks[0].id;
      }

      this.filterNotes();
      this.seekTo(0);
    } catch (err) {
      console.error("Failed to parse MIDI file:", err);
    }
  }

  filterNotes() {
    if (!this.parsedData) return;

    if (this.playMode === 'lead') {
      this.filteredNotes = this.parsedData.lead_notes || [];
      this.el.overlayBtnText.textContent = "PLAY MAIN PIANO LEAD";
      this.el.leadStatusText.textContent = `Smart Classifier: Main Piano Lead (${this.filteredNotes.length} notes across ${this.parsedData.lead_track_ids.length} phrases)`;
    } else if (this.playMode === 'track') {
      this.filteredNotes = this.parsedData.notes.filter(n => n.track_id === this.selectedTrackId);
      const trk = this.parsedData.tracks.find(t => t.id === this.selectedTrackId);
      const name = trk ? trk.name : `Track ${this.selectedTrackId}`;
      this.el.overlayBtnText.textContent = `PLAY "${name.toUpperCase()}" SOLO`;
      this.el.leadStatusText.textContent = `Soloing Track ${this.selectedTrackId}: ${name} (${this.filteredNotes.length} notes)`;
    } else {
      this.filteredNotes = this.parsedData.notes || [];
      this.el.overlayBtnText.textContent = "PLAY ALL TRACKS ON GRAND PIANO";
      this.el.leadStatusText.textContent = `Full Arrangement Mode: ${this.filteredNotes.length} total notes`;
    }

    this.el.statNotes.textContent = this.filteredNotes.length;
    this.visualizer.setNotes(this.filteredNotes);
  }

  openTrackModal() {
    if (!this.parsedData) return;
    const tbody = this.el.trackTableBody;
    tbody.innerHTML = '';

    const noteNames = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
    const pToName = (p) => `${noteNames[p % 12]}${Math.floor(p / 12) - 1}`;

    this.parsedData.tracks.forEach(t => {
      const tr = document.createElement('tr');
      if (t.is_piano_lead) tr.className = 'is-lead-row';

      const badgeClass = t.is_piano_lead ? 'badge-lead' : 'badge-other';
      const rangeStr = `${pToName(t.pitch_min)} - ${pToName(t.pitch_max)} (avg ${t.pitch_avg})`;

      tr.innerHTML = `
        <td><strong>#${t.id}</strong></td>
        <td>${t.name}</td>
        <td><span class="${badgeClass}">${t.badge}</span></td>
        <td><strong>${t.notes_count}</strong></td>
        <td>${rangeStr}</td>
        <td>
          <button class="btn-table-solo" data-track-id="${t.id}">Solo on Piano</button>
        </td>
      `;

      tr.querySelector('.btn-table-solo').addEventListener('click', () => {
        this.soloTrack(t.id);
      });

      tbody.appendChild(tr);
    });

    this.el.trackModal.style.display = 'flex';
  }

  closeTrackModal() {
    this.el.trackModal.style.display = 'none';
  }

  soloTrack(trackId) {
    this.closeTrackModal();
    this.selectedTrackId = trackId;
    this.el.trackSelect.value = trackId;
    this.setMode('track');
    this.play();
  }

  async exportLeadMidi() {
    if (!this.currentFile) return;
    try {
      const res = await fetch('/api/export-lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file: this.currentFile })
      });
      const data = await res.json();
      if (data.success) {
        alert(`Main Piano Lead exported successfully!\n\nSaved as: ${data.lead_file}`);
        await this.loadFileList();
        this.el.midiSelect.value = data.lead_file;
        this.loadFile(data.lead_file);
      } else {
        alert("Export failed: " + (data.error || "Unknown error"));
      }
    } catch (err) {
      alert("Export request failed: " + err.message);
    }
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
        body: JSON.stringify({
          file: this.currentFile,
          speed: this.speed,
          solo_lead: (this.playMode === 'lead'),
          selected_track_ids: (this.playMode === 'track' ? [this.selectedTrackId] : null)
        })
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
    while (
      this.noteTriggerIndex < this.filteredNotes.length &&
      this.filteredNotes[this.noteTriggerIndex].start <= this.playbackTime
    ) {
      const n = this.filteredNotes[this.noteTriggerIndex];

      if (this.playbackTime < n.start + n.duration) {
        if (this.soundEngine === 'web') {
          this.audio.playNote(n.note, n.velocity, n.duration);
        }
        this.keyboard.pressKey(n.note);
        this.activeNoteNumbers.add(n.note);
      }
      this.noteTriggerIndex++;
    }

    this.activeNoteNumbers.forEach(noteNum => {
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

window.addEventListener('DOMContentLoaded', () => {
  window.studio = new GrandPianoStudio();
});
