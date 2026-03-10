/**
 * O&G + Mining Intelligence Brief — Audio Player
 * Text-to-Speech using Web Speech API (pt-BR)
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

  // Find best pt-BR voice
  function loadVoice() {
    const voices = synth.getVoices();
    // Prefer Google or Microsoft pt-BR voices
    preferredVoice = voices.find(v => v.lang === 'pt-BR' && v.name.includes('Google')) ||
                     voices.find(v => v.lang === 'pt-BR' && v.name.includes('Microsoft')) ||
                     voices.find(v => v.lang === 'pt-BR') ||
                     voices.find(v => v.lang.startsWith('pt')) ||
                     null;
  }

  // Load voices (async on some browsers)
  if (synth.onvoiceschanged !== undefined) {
    synth.onvoiceschanged = loadVoice;
  }
  loadVoice();

  // Extract readable text from an element, skipping source links
  function extractText(el) {
    const clone = el.cloneNode(true);
    // Remove source paragraphs and calendar buttons
    clone.querySelectorAll('.source, .calendar-btn, .back-link, script, style').forEach(n => n.remove());
    let text = clone.textContent || '';
    // Clean up whitespace
    text = text.replace(/\s+/g, ' ').trim();
    // Clean common symbols that sound bad in TTS
    text = text.replace(/[⛽⛏️⚡🌍📊📋🎯🧠📈🗂️📚🚨⚔️🔮🇧🇷💡▸▲▼●◆↗️]/g, '');
    text = text.replace(/\s+/g, ' ').trim();
    return text;
  }

  // Discover sections from the page
  function discoverSections() {
    sections = [];
    const container = document.querySelector('.container');
    if (!container) return;

    // Try data-section attributes first
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
      return;
    }

    // Fallback: use section dividers to split content
    const dividers = container.querySelectorAll('.section-divider');
    const allElements = Array.from(container.children);

    // First: everything before the first divider (exec summary, alert, header)
    let preContent = [];
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

    // Then: each section divider groups the content until the next divider
    dividers.forEach((divider, i) => {
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

    // Footer
    const footer = container.querySelector('.footer');
    if (footer) {
      sections.push({
        name: 'Rodape',
        element: footer,
        text: 'Fim da edicao. Obrigado por ouvir o O and G plus Mining Intelligence Brief.'
      });
    }
  }

  // Create the player UI
  function createPlayer() {
    // Listen button (inserted after the header)
    const header = document.querySelector('.header');
    if (header) {
      const btn = document.createElement('button');
      btn.className = 'listen-btn';
      btn.id = 'listen-btn';
      btn.innerHTML = '<span class="listen-icon">&#9654;</span> Ouvir esta edicao';
      btn.addEventListener('click', togglePlay);
      header.appendChild(btn);
    }

    // Floating player bar
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
          <div class="player-time" id="player-time">0 / 0 secoes</div>
        </div>
        <button class="speed-btn" id="speed-btn" title="Velocidade">1x</button>
        <button class="player-close" id="player-close" title="Fechar">&times;</button>
      </div>
    `;
    document.body.appendChild(player);

    // Event listeners
    document.getElementById('player-play').addEventListener('click', togglePlay);
    document.getElementById('player-prev').addEventListener('click', prevSection);
    document.getElementById('player-next').addEventListener('click', nextSection);
    document.getElementById('speed-btn').addEventListener('click', cycleSpeed);
    document.getElementById('player-close').addEventListener('click', stopAndClose);
    document.getElementById('player-progress-bar').addEventListener('click', onProgressClick);
  }

  function showPlayer() {
    const player = document.getElementById('audio-player');
    if (player) {
      player.classList.add('visible');
      document.body.classList.add('player-active');
    }
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
        ? '<span class="listen-icon">&#10074;&#10074;</span> Pausar'
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

    // Highlight current section
    document.querySelectorAll('.reading').forEach(el => el.classList.remove('reading'));
    if (isPlaying && sections[currentSectionIdx]?.element) {
      sections[currentSectionIdx].element.classList.add('reading');
      // Scroll into view smoothly
      sections[currentSectionIdx].element.scrollIntoView({
        behavior: 'smooth',
        block: 'center'
      });
    }
  }

  function speakSection(idx) {
    if (idx >= sections.length) {
      // Done
      isPlaying = false;
      isPaused = false;
      currentSectionIdx = 0;
      updateUI();
      return;
    }

    synth.cancel();
    currentSectionIdx = idx;

    const text = sections[idx].text;
    // Split long texts into chunks (speechSynthesis has ~300 char limit on some browsers)
    const chunks = splitText(text, 200);
    let chunkIdx = 0;

    function speakChunk() {
      if (chunkIdx >= chunks.length || !isPlaying) {
        if (isPlaying && chunkIdx >= chunks.length) {
          // Move to next section
          speakSection(idx + 1);
        }
        return;
      }

      const utt = new SpeechSynthesisUtterance(chunks[chunkIdx]);
      utt.lang = 'pt-BR';
      utt.rate = SPEEDS[currentSpeedIdx];
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

  function togglePlay() {
    if (!isPlaying) {
      // Start
      discoverSections();
      if (sections.length === 0) return;
      isPlaying = true;
      isPaused = false;
      showPlayer();
      speakSection(currentSectionIdx);
    } else if (isPaused) {
      // Resume
      isPaused = false;
      synth.resume();
      updateUI();
    } else {
      // Pause
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

    // If currently speaking, restart current section with new speed
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

  // Cleanup on page unload
  window.addEventListener('beforeunload', function() {
    synth.cancel();
  });

  // Chrome bug workaround: speech synthesis stops after ~15s if not "poked"
  // This interval keeps it alive
  let keepAliveInterval;
  function startKeepAlive() {
    keepAliveInterval = setInterval(function() {
      if (synth.speaking && !synth.paused) {
        synth.pause();
        synth.resume();
      }
    }, 10000);
  }

  function stopKeepAlive() {
    clearInterval(keepAliveInterval);
  }

  // Override togglePlay to manage keepalive
  const origToggle = togglePlay;

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  function init() {
    // Check for Web Speech API support
    if (!('speechSynthesis' in window)) {
      console.warn('Web Speech API not supported in this browser.');
      return;
    }
    createPlayer();
    startKeepAlive();
  }
})();
