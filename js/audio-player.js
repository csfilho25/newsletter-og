/**
 * O&G + Mining Intelligence Brief — Audio Player
 * Hybrid: HTML5 Audio (MP3) + Web Speech API (TTS) with natural voice priority
 * Works on GitHub Pages — no server needed
 */

(function() {
  'use strict';

  const SPEEDS = [0.75, 1, 1.25, 1.5, 2];
  let currentSpeedIdx = 1;
  let sections = [];
  let currentSectionIdx = 0;
  let isPlaying = false;
  let isPaused = false;
  let synth = window.speechSynthesis;
  let currentUtterance = null;
  let preferredVoice = null;
  let voiceQuality = 'standard'; // 'natural', 'enhanced', 'standard'
  let audioElement = null; // For MP3 playback
  let useMP3 = false;

  // ── Voice Selection ──────────────────────────────────────────────

  function scoreVoice(v) {
    let score = 0;
    const name = v.name.toLowerCase();
    const lang = v.lang || '';

    // Must be Portuguese
    if (!lang.startsWith('pt')) return -1;
    if (lang === 'pt-BR') score += 50;

    // Strongly prefer Natural/Neural voices (highest quality)
    if (name.includes('natural')) score += 200;
    if (name.includes('neural')) score += 180;
    if (name.includes('online')) score += 100;

    // Prefer known high-quality providers
    if (name.includes('microsoft')) score += 40;
    if (name.includes('google')) score += 30;

    // Prefer female voices (generally better TTS quality for pt-BR)
    if (name.includes('francisca')) score += 25;
    if (name.includes('thalita')) score += 25;
    if (name.includes('elza')) score += 20;
    if (name.includes('fernanda')) score += 20;
    if (name.includes('leila')) score += 15;

    // Male natural voices also good
    if (name.includes('antonio')) score += 15;
    if (name.includes('valerio')) score += 15;

    // Remote/cloud voices tend to be better
    if (!v.localService) score += 10;

    return score;
  }

  function loadVoice() {
    const voices = synth.getVoices();
    if (!voices || voices.length === 0) return;

    // Score and sort all Portuguese voices
    const ptVoices = voices
      .map(v => ({ voice: v, score: scoreVoice(v) }))
      .filter(v => v.score > 0)
      .sort((a, b) => b.score - a.score);

    if (ptVoices.length > 0) {
      preferredVoice = ptVoices[0].voice;
      const name = preferredVoice.name.toLowerCase();

      if (name.includes('natural') || name.includes('neural')) {
        voiceQuality = 'natural';
      } else if (name.includes('online') || !preferredVoice.localService) {
        voiceQuality = 'enhanced';
      } else {
        voiceQuality = 'standard';
      }

      console.log('[Audio] Selected voice:', preferredVoice.name, '| Quality:', voiceQuality);
    }

    updateVoiceIndicator();
  }

  if (synth && synth.onvoiceschanged !== undefined) {
    synth.onvoiceschanged = loadVoice;
  }
  if (synth) loadVoice();

  // ── MP3 Audio Support ────────────────────────────────────────────

  function checkMP3() {
    const container = document.querySelector('.container');
    if (!container) return false;

    const audioUrl = container.getAttribute('data-audio') ||
                     document.querySelector('meta[name="audio-url"]')?.content;

    if (audioUrl) {
      audioElement = new Audio(audioUrl);
      audioElement.preload = 'metadata';
      return true;
    }
    return false;
  }

  // ── Text Extraction ──────────────────────────────────────────────

  function extractText(el) {
    const clone = el.cloneNode(true);
    clone.querySelectorAll('.source, .calendar-btn, .back-link, script, style, .listen-btn').forEach(n => n.remove());
    let text = clone.textContent || '';
    text = text.replace(/\s+/g, ' ').trim();
    text = text.replace(/[⛽⛏️⚡🌍📊📋🎯🧠📈🗂️📚🚨⚔️🔮🇧🇷💡▸▲▼●◆↗️📅🛢️⚠️🏭⚖️📰🔋💰🏗️🔍👔🎓🏢⏰📌]/g, '');
    text = text.replace(/\s+/g, ' ').trim();
    return text;
  }

  // ── Section Discovery ────────────────────────────────────────────

  function discoverSections() {
    sections = [];
    const container = document.querySelector('.container');
    if (!container) return;

    const dataSections = container.querySelectorAll('[data-section]');
    if (dataSections.length > 0) {
      dataSections.forEach(el => {
        const text = extractText(el);
        if (text.length > 20) {
          sections.push({
            name: el.getAttribute('data-section') || 'Secao',
            element: el,
            text: text
          });
        }
      });
      if (sections.length > 0) return;
    }

    const dividers = container.querySelectorAll('.section-divider');
    const allElements = Array.from(container.children);

    for (let el of allElements) {
      if (el.classList.contains('section-divider')) break;
      if (el.classList.contains('header') || el.classList.contains('exec-summary') || el.classList.contains('alert-banner')) {
        const text = extractText(el);
        if (text.length > 20) {
          const name = el.classList.contains('header') ? 'Cabecalho' :
                       el.classList.contains('alert-banner') ? 'Alerta' : 'Resumo Executivo';
          sections.push({ name, element: el, text });
        }
      }
    }

    dividers.forEach((divider) => {
      const sectionName = divider.textContent.replace(/\s+/g, ' ').trim();
      let content = [];
      let next = divider.nextElementSibling;
      while (next && !next.classList.contains('section-divider')) {
        content.push(next);
        next = next.nextElementSibling;
      }
      if (content.length > 0) {
        const wrapper = document.createElement('div');
        content.forEach(c => wrapper.appendChild(c.cloneNode(true)));
        const text = extractText(wrapper);
        if (text.length > 20) {
          sections.push({
            name: sectionName.substring(0, 40),
            element: divider,
            text: text
          });
        }
      }
    });

    const footer = container.querySelector('.footer');
    if (footer) {
      sections.push({
        name: 'Rodape',
        element: footer,
        text: 'Fim da edicao. Obrigado por ouvir o O and G plus Mining Intelligence Brief.'
      });
    }
  }

  // ── Player UI ────────────────────────────────────────────────────

  function createPlayer() {
    const header = document.querySelector('.header');
    if (header) {
      const btn = document.createElement('button');
      btn.className = 'listen-btn';
      btn.id = 'listen-btn';
      btn.innerHTML = '<span class="listen-icon">&#9654;</span> Ouvir esta edicao';
      btn.addEventListener('click', togglePlay);
      header.appendChild(btn);
    }

    const player = document.createElement('div');
    player.className = 'audio-player';
    player.id = 'audio-player';
    player.innerHTML = `
      <div class="audio-player-inner">
        <div class="player-controls">
          <button class="player-btn" id="player-prev" title="Secao anterior">&#9664;</button>
          <button class="player-btn play-btn" id="player-play" title="Play/Pause">&#9654;</button>
          <button class="player-btn" id="player-next" title="Proxima secao">&#9654;</button>
        </div>
        <div class="player-info">
          <div class="player-section-name" id="player-section-name">Pronto para ouvir</div>
          <div class="player-progress-bar" id="player-progress-bar">
            <div class="player-progress-fill" id="player-progress-fill"></div>
          </div>
          <div class="player-meta">
            <span class="player-time" id="player-time">0 / 0 secoes</span>
            <span class="voice-quality" id="voice-quality"></span>
          </div>
        </div>
        <button class="speed-btn" id="speed-btn" title="Velocidade">1x</button>
        <button class="player-close" id="player-close" title="Fechar">&times;</button>
      </div>
    `;
    document.body.appendChild(player);

    document.getElementById('player-play').addEventListener('click', togglePlay);
    document.getElementById('player-prev').addEventListener('click', prevSection);
    document.getElementById('player-next').addEventListener('click', nextSection);
    document.getElementById('speed-btn').addEventListener('click', cycleSpeed);
    document.getElementById('player-close').addEventListener('click', stopAndClose);
    document.getElementById('player-progress-bar').addEventListener('click', onProgressClick);
  }

  function updateVoiceIndicator() {
    const el = document.getElementById('voice-quality');
    if (!el) return;

    if (useMP3) {
      el.textContent = 'MP3';
      el.className = 'voice-quality vq-natural';
    } else if (voiceQuality === 'natural') {
      el.textContent = 'Voz Natural';
      el.className = 'voice-quality vq-natural';
    } else if (voiceQuality === 'enhanced') {
      el.textContent = 'Voz Online';
      el.className = 'voice-quality vq-enhanced';
    } else {
      el.textContent = 'TTS';
      el.className = 'voice-quality vq-standard';
    }
  }

  function showPlayer() {
    const player = document.getElementById('audio-player');
    if (player) {
      player.classList.add('visible');
      document.body.classList.add('player-active');
    }
    updateVoiceIndicator();
  }

  function hidePlayer() {
    const player = document.getElementById('audio-player');
    if (player) {
      player.classList.remove('visible');
      document.body.classList.remove('player-active');
    }
  }

  function updateUI() {
    const playBtn = document.getElementById('player-play');
    const listenBtn = document.getElementById('listen-btn');
    const sectionName = document.getElementById('player-section-name');
    const progressFill = document.getElementById('player-progress-fill');
    const timeDisplay = document.getElementById('player-time');

    if (playBtn) {
      playBtn.innerHTML = isPlaying && !isPaused ? '&#10074;&#10074;' : '&#9654;';
    }
    if (listenBtn) {
      listenBtn.classList.toggle('playing', isPlaying);
      listenBtn.innerHTML = isPlaying
        ? '<span class="listen-icon eq-icon"><span></span><span></span><span></span></span> Pausar'
        : '<span class="listen-icon">&#9654;</span> Ouvir esta edicao';
    }
    if (sectionName && sections.length > 0) {
      sectionName.textContent = sections[currentSectionIdx]?.name || '';
    }
    if (progressFill && sections.length > 0) {
      const pct = ((currentSectionIdx + 1) / sections.length) * 100;
      progressFill.style.width = pct + '%';
    }
    if (timeDisplay) {
      timeDisplay.textContent = `${currentSectionIdx + 1} / ${sections.length} secoes`;
    }

    document.querySelectorAll('.reading').forEach(el => el.classList.remove('reading'));
    if (isPlaying && sections[currentSectionIdx]?.element) {
      sections[currentSectionIdx].element.classList.add('reading');
      sections[currentSectionIdx].element.scrollIntoView({
        behavior: 'smooth',
        block: 'center'
      });
    }
  }

  // ── TTS Playback ─────────────────────────────────────────────────

  function speakSection(idx) {
    if (idx >= sections.length) {
      isPlaying = false;
      isPaused = false;
      currentSectionIdx = 0;
      updateUI();
      return;
    }

    synth.cancel();
    currentSectionIdx = idx;

    const text = sections[idx].text;
    const chunks = splitText(text, 250);
    let chunkIdx = 0;

    function speakChunk() {
      if (chunkIdx >= chunks.length || !isPlaying) {
        if (isPlaying && chunkIdx >= chunks.length) {
          speakSection(idx + 1);
        }
        return;
      }

      const utt = new SpeechSynthesisUtterance(chunks[chunkIdx]);
      utt.lang = 'pt-BR';
      utt.rate = SPEEDS[currentSpeedIdx];
      utt.pitch = 1.0;
      if (preferredVoice) utt.voice = preferredVoice;

      utt.onend = function() {
        chunkIdx++;
        speakChunk();
      };

      utt.onerror = function(e) {
        if (e.error !== 'canceled') {
          chunkIdx++;
          speakChunk();
        }
      };

      currentUtterance = utt;
      synth.speak(utt);
    }

    updateUI();
    speakChunk();
  }

  function splitText(text, maxLen) {
    const chunks = [];
    const sentences = text.match(/[^.!?]+[.!?]+/g) || [text];
    let current = '';

    for (const sentence of sentences) {
      if ((current + sentence).length > maxLen && current.length > 0) {
        chunks.push(current.trim());
        current = sentence;
      } else {
        current += sentence;
      }
    }
    if (current.trim()) chunks.push(current.trim());
    return chunks;
  }

  // ── Controls ─────────────────────────────────────────────────────

  function togglePlay() {
    if (!isPlaying) {
      discoverSections();
      if (sections.length === 0) return;
      isPlaying = true;
      isPaused = false;
      showPlayer();
      speakSection(currentSectionIdx);
    } else if (isPaused) {
      isPaused = false;
      synth.resume();
      updateUI();
    } else {
      isPaused = true;
      synth.pause();
      updateUI();
    }
  }

  function nextSection() {
    if (currentSectionIdx < sections.length - 1) {
      synth.cancel();
      speakSection(currentSectionIdx + 1);
    }
  }

  function prevSection() {
    if (currentSectionIdx > 0) {
      synth.cancel();
      speakSection(currentSectionIdx - 1);
    }
  }

  function cycleSpeed() {
    currentSpeedIdx = (currentSpeedIdx + 1) % SPEEDS.length;
    const speedBtn = document.getElementById('speed-btn');
    if (speedBtn) speedBtn.textContent = SPEEDS[currentSpeedIdx] + 'x';

    if (isPlaying && !isPaused) {
      synth.cancel();
      speakSection(currentSectionIdx);
    }
  }

  function stopAndClose() {
    synth.cancel();
    isPlaying = false;
    isPaused = false;
    currentSectionIdx = 0;
    hidePlayer();
    updateUI();
  }

  function onProgressClick(e) {
    const bar = e.currentTarget;
    const rect = bar.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    const targetIdx = Math.floor(pct * sections.length);
    if (targetIdx >= 0 && targetIdx < sections.length) {
      synth.cancel();
      speakSection(targetIdx);
    }
  }

  // ── Keep-alive & Cleanup ─────────────────────────────────────────

  window.addEventListener('beforeunload', function() {
    if (synth) synth.cancel();
  });

  let keepAliveInterval;
  function startKeepAlive() {
    keepAliveInterval = setInterval(function() {
      if (synth && synth.speaking && !synth.paused) {
        synth.pause();
        synth.resume();
      }
    }, 10000);
  }

  // ── Init ─────────────────────────────────────────────────────────

  function init() {
    if (!('speechSynthesis' in window)) {
      console.warn('[Audio] Web Speech API not supported.');
      return;
    }

    useMP3 = checkMP3();
    createPlayer();
    startKeepAlive();

    // Auto-start if URL has #listen
    if (window.location.hash === '#listen') {
      setTimeout(function() {
        togglePlay();
      }, 1000);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
