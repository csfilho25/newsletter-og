/**
 * O&G + Mining Intelligence Brief — Audio Player
 * Hybrid: HTML5 Audio (MP3 preferred) + Web Speech API (TTS fallback)
 * MP3 uses Microsoft Francisca Neural — natural Brazilian Portuguese voice
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
  let preferredVoice = null;
  let voiceQuality = 'standard';
  let audioElement = null;
  let useMP3 = false;
  let audioDuration = 0;

  // ── MP3 Detection ──────────────────────────────────────────────

  function getMP3Url() {
    var meta = document.querySelector('meta[name="audio-url"]');
    if (meta && meta.content) return meta.content;
    var container = document.querySelector('.container');
    if (container && container.getAttribute('data-audio')) return container.getAttribute('data-audio');
    // Default: same name as HTML but .mp3
    return window.location.pathname.replace(/\.html$/, '.mp3');
  }

  function tryLoadMP3() {
    var url = getMP3Url();
    // Use HEAD request to check if MP3 exists
    try {
      var xhr = new XMLHttpRequest();
      xhr.open('HEAD', url, false); // synchronous
      xhr.send();
      if (xhr.status === 200) {
        audioElement = new Audio(url);
        audioElement.preload = 'auto';
        useMP3 = true;
        // Get duration when ready
        audioElement.addEventListener('loadedmetadata', function() {
          audioDuration = audioElement.duration;
          console.log('[Audio] MP3 ready:', Math.round(audioDuration) + 's');
        });
        console.log('[Audio] MP3 found:', url);
        return true;
      }
    } catch (e) {
      // Network error, fall through
    }
    console.log('[Audio] No MP3, using TTS fallback');
    return false;
  }

  // ── TTS Voice Selection (fallback) ─────────────────────────────

  function scoreVoice(v) {
    var score = 0;
    var name = v.name.toLowerCase();
    var lang = v.lang || '';
    if (!lang.startsWith('pt')) return -1;
    if (lang === 'pt-BR') score += 50;
    if (name.includes('natural')) score += 200;
    if (name.includes('neural')) score += 180;
    if (name.includes('online')) score += 100;
    if (name.includes('microsoft')) score += 40;
    if (name.includes('google')) score += 30;
    if (name.includes('francisca')) score += 25;
    if (name.includes('thalita')) score += 25;
    if (!v.localService) score += 10;
    return score;
  }

  function loadVoice() {
    if (!synth) return;
    var voices = synth.getVoices();
    if (!voices || voices.length === 0) return;
    var ptVoices = voices
      .map(function(v) { return { voice: v, score: scoreVoice(v) }; })
      .filter(function(v) { return v.score > 0; })
      .sort(function(a, b) { return b.score - a.score; });
    if (ptVoices.length > 0) {
      preferredVoice = ptVoices[0].voice;
      var name = preferredVoice.name.toLowerCase();
      if (name.includes('natural') || name.includes('neural')) voiceQuality = 'natural';
      else if (name.includes('online') || !preferredVoice.localService) voiceQuality = 'enhanced';
      else voiceQuality = 'standard';
    }
    updateVoiceIndicator();
  }

  if (synth && synth.onvoiceschanged !== undefined) {
    synth.onvoiceschanged = loadVoice;
  }
  if (synth) loadVoice();

  // ── Text Extraction (for TTS fallback) ─────────────────────────

  function extractText(el) {
    var clone = el.cloneNode(true);
    clone.querySelectorAll('.source, .calendar-btn, .back-link, script, style, .listen-btn').forEach(function(n) { n.remove(); });
    var text = clone.textContent || '';
    text = text.replace(/\s+/g, ' ').trim();
    text = text.replace(/[⛽⛏️⚡🌍📊📋🎯🧠📈🗂️📚🚨⚔️🔮🇧🇷💡▸▲▼●◆↗️📅🛢️⚠️🏭⚖️📰🔋💰🏗️🔍👔🎓🏢⏰📌]/g, '');
    text = text.replace(/\s+/g, ' ').trim();
    return text;
  }

  function discoverSections() {
    sections = [];
    var container = document.querySelector('.container');
    if (!container) return;

    var dataSections = container.querySelectorAll('[data-section]');
    if (dataSections.length > 0) {
      dataSections.forEach(function(el) {
        var text = extractText(el);
        if (text.length > 20) {
          sections.push({ name: el.getAttribute('data-section') || 'Secao', element: el, text: text });
        }
      });
      if (sections.length > 0) return;
    }

    var dividers = container.querySelectorAll('.section-divider');
    var allElements = Array.from(container.children);
    for (var i = 0; i < allElements.length; i++) {
      var el = allElements[i];
      if (el.classList.contains('section-divider')) break;
      if (el.classList.contains('header') || el.classList.contains('exec-summary') || el.classList.contains('alert-banner')) {
        var text = extractText(el);
        if (text.length > 20) {
          var name = el.classList.contains('header') ? 'Cabecalho' :
                     el.classList.contains('alert-banner') ? 'Alerta' : 'Resumo Executivo';
          sections.push({ name: name, element: el, text: text });
        }
      }
    }

    dividers.forEach(function(divider) {
      var sectionName = divider.textContent.replace(/\s+/g, ' ').trim();
      var content = [];
      var next = divider.nextElementSibling;
      while (next && !next.classList.contains('section-divider')) {
        content.push(next);
        next = next.nextElementSibling;
      }
      if (content.length > 0) {
        var wrapper = document.createElement('div');
        content.forEach(function(c) { wrapper.appendChild(c.cloneNode(true)); });
        var text = extractText(wrapper);
        if (text.length > 20) {
          sections.push({ name: sectionName.substring(0, 40), element: divider, text: text });
        }
      }
    });

    var footer = container.querySelector('.footer');
    if (footer) {
      sections.push({ name: 'Rodape', element: footer, text: 'Fim da edicao.' });
    }
  }

  // ── Player UI ────────────────────────────────────────────────────

  function createPlayer() {
    var header = document.querySelector('.header');
    if (header) {
      var btn = document.createElement('button');
      btn.className = 'listen-btn';
      btn.id = 'listen-btn';
      btn.innerHTML = '<span class="listen-icon">&#9654;</span> Ouvir esta edicao';
      btn.addEventListener('click', togglePlay);
      header.appendChild(btn);
    }

    var player = document.createElement('div');
    player.className = 'audio-player';
    player.id = 'audio-player';
    player.innerHTML =
      '<div class="audio-player-inner">' +
        '<div class="player-controls">' +
          '<button class="player-btn" id="player-prev" title="Voltar 15s">&#9664;</button>' +
          '<button class="player-btn play-btn" id="player-play" title="Play/Pause">&#9654;</button>' +
          '<button class="player-btn" id="player-next" title="Avancar 15s">&#9654;</button>' +
        '</div>' +
        '<div class="player-info">' +
          '<div class="player-section-name" id="player-section-name">Pronto para ouvir</div>' +
          '<div class="player-progress-bar" id="player-progress-bar">' +
            '<div class="player-progress-fill" id="player-progress-fill"></div>' +
          '</div>' +
          '<div class="player-meta">' +
            '<span class="player-time" id="player-time">0:00 / 0:00</span>' +
            '<span class="voice-quality" id="voice-quality"></span>' +
          '</div>' +
        '</div>' +
        '<button class="speed-btn" id="speed-btn" title="Velocidade">1x</button>' +
        '<button class="player-close" id="player-close" title="Fechar">&times;</button>' +
      '</div>';
    document.body.appendChild(player);

    document.getElementById('player-play').addEventListener('click', togglePlay);
    document.getElementById('player-prev').addEventListener('click', skipBack);
    document.getElementById('player-next').addEventListener('click', skipForward);
    document.getElementById('speed-btn').addEventListener('click', cycleSpeed);
    document.getElementById('player-close').addEventListener('click', stopAndClose);
    document.getElementById('player-progress-bar').addEventListener('click', onProgressClick);
  }

  function updateVoiceIndicator() {
    var el = document.getElementById('voice-quality');
    if (!el) return;
    if (useMP3) {
      el.textContent = 'Voz Natural';
      el.className = 'voice-quality vq-natural';
    } else if (voiceQuality === 'natural') {
      el.textContent = 'Voz Natural';
      el.className = 'voice-quality vq-natural';
    } else if (voiceQuality === 'enhanced') {
      el.textContent = 'Online';
      el.className = 'voice-quality vq-enhanced';
    } else {
      el.textContent = 'TTS';
      el.className = 'voice-quality vq-standard';
    }
  }

  function showPlayer() {
    var player = document.getElementById('audio-player');
    if (player) {
      player.classList.add('visible');
      document.body.classList.add('player-active');
    }
    updateVoiceIndicator();
  }

  function hidePlayer() {
    var player = document.getElementById('audio-player');
    if (player) {
      player.classList.remove('visible');
      document.body.classList.remove('player-active');
    }
  }

  function formatTime(s) {
    var m = Math.floor(s / 60);
    var sec = Math.floor(s % 60);
    return m + ':' + (sec < 10 ? '0' : '') + sec;
  }

  function updateUI() {
    var playBtn = document.getElementById('player-play');
    var listenBtn = document.getElementById('listen-btn');
    var sectionName = document.getElementById('player-section-name');

    if (playBtn) {
      playBtn.innerHTML = isPlaying && !isPaused ? '&#10074;&#10074;' : '&#9654;';
    }
    if (listenBtn) {
      listenBtn.classList.toggle('playing', isPlaying);
      listenBtn.innerHTML = isPlaying
        ? '<span class="listen-icon eq-icon"><span></span><span></span><span></span></span> Pausar'
        : '<span class="listen-icon">&#9654;</span> Ouvir esta edicao';
    }

    if (useMP3 && audioElement) {
      // MP3 mode: show time
      var timeDisplay = document.getElementById('player-time');
      var progressFill = document.getElementById('player-progress-fill');
      if (sectionName) sectionName.textContent = 'O&G + Mining Intelligence Brief';
      if (timeDisplay) timeDisplay.textContent = formatTime(audioElement.currentTime) + ' / ' + formatTime(audioDuration);
      if (progressFill && audioDuration > 0) {
        progressFill.style.width = (audioElement.currentTime / audioDuration * 100) + '%';
      }
    } else {
      // TTS mode: show sections
      if (sectionName && sections.length > 0) {
        sectionName.textContent = sections[currentSectionIdx]?.name || '';
      }
      var progressFill = document.getElementById('player-progress-fill');
      var timeDisplay = document.getElementById('player-time');
      if (progressFill && sections.length > 0) {
        progressFill.style.width = ((currentSectionIdx + 1) / sections.length * 100) + '%';
      }
      if (timeDisplay) {
        timeDisplay.textContent = (currentSectionIdx + 1) + ' / ' + sections.length + ' secoes';
      }

      document.querySelectorAll('.reading').forEach(function(el) { el.classList.remove('reading'); });
      if (isPlaying && sections[currentSectionIdx]?.element) {
        sections[currentSectionIdx].element.classList.add('reading');
        sections[currentSectionIdx].element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }

  // ── MP3 Playback ─────────────────────────────────────────────────

  var mp3UpdateInterval = null;

  function startMP3() {
    if (!audioElement) return;
    audioElement.playbackRate = SPEEDS[currentSpeedIdx];

    // Update duration when available
    audioElement.addEventListener('loadedmetadata', function() {
      audioDuration = audioElement.duration;
      updateUI();
    });
    // Also try getting it now
    if (audioElement.duration && isFinite(audioElement.duration)) {
      audioDuration = audioElement.duration;
    }

    audioElement.play().catch(function(e) {
      console.log('[Audio] Play blocked:', e.message);
    });
    isPlaying = true;
    isPaused = false;
    showPlayer();
    updateUI();

    mp3UpdateInterval = setInterval(function() {
      if (isPlaying && !isPaused) {
        if (audioElement.duration && isFinite(audioElement.duration)) {
          audioDuration = audioElement.duration;
        }
        updateUI();
      }
    }, 500);

    audioElement.onended = function() {
      isPlaying = false;
      isPaused = false;
      clearInterval(mp3UpdateInterval);
      updateUI();
    };
  }

  function pauseMP3() {
    if (!audioElement) return;
    audioElement.pause();
    isPaused = true;
    updateUI();
  }

  function resumeMP3() {
    if (!audioElement) return;
    audioElement.play();
    isPaused = false;
    updateUI();
  }

  function stopMP3() {
    if (!audioElement) return;
    audioElement.pause();
    audioElement.currentTime = 0;
    isPlaying = false;
    isPaused = false;
    clearInterval(mp3UpdateInterval);
  }

  // ── TTS Playback (fallback) ──────────────────────────────────────

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
    var text = sections[idx].text;
    var chunks = splitText(text, 250);
    var chunkIdx = 0;

    function speakChunk() {
      if (chunkIdx >= chunks.length || !isPlaying) {
        if (isPlaying && chunkIdx >= chunks.length) speakSection(idx + 1);
        return;
      }
      var utt = new SpeechSynthesisUtterance(chunks[chunkIdx]);
      utt.lang = 'pt-BR';
      utt.rate = SPEEDS[currentSpeedIdx];
      if (preferredVoice) utt.voice = preferredVoice;
      utt.onend = function() { chunkIdx++; speakChunk(); };
      utt.onerror = function(e) { if (e.error !== 'canceled') { chunkIdx++; speakChunk(); } };
      synth.speak(utt);
    }
    updateUI();
    speakChunk();
  }

  function splitText(text, maxLen) {
    var chunks = [];
    var sentences = text.match(/[^.!?]+[.!?]+/g) || [text];
    var current = '';
    for (var i = 0; i < sentences.length; i++) {
      if ((current + sentences[i]).length > maxLen && current.length > 0) {
        chunks.push(current.trim());
        current = sentences[i];
      } else {
        current += sentences[i];
      }
    }
    if (current.trim()) chunks.push(current.trim());
    return chunks;
  }

  // ── Controls ─────────────────────────────────────────────────────

  function togglePlay() {
    if (useMP3) {
      if (!isPlaying) startMP3();
      else if (isPaused) resumeMP3();
      else pauseMP3();
    } else {
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
  }

  function skipForward() {
    if (useMP3 && audioElement) {
      audioElement.currentTime = Math.min(audioElement.currentTime + 15, audioDuration);
      updateUI();
    } else if (currentSectionIdx < sections.length - 1) {
      synth.cancel();
      speakSection(currentSectionIdx + 1);
    }
  }

  function skipBack() {
    if (useMP3 && audioElement) {
      audioElement.currentTime = Math.max(audioElement.currentTime - 15, 0);
      updateUI();
    } else if (currentSectionIdx > 0) {
      synth.cancel();
      speakSection(currentSectionIdx - 1);
    }
  }

  function cycleSpeed() {
    currentSpeedIdx = (currentSpeedIdx + 1) % SPEEDS.length;
    var speedBtn = document.getElementById('speed-btn');
    if (speedBtn) speedBtn.textContent = SPEEDS[currentSpeedIdx] + 'x';

    if (useMP3 && audioElement) {
      audioElement.playbackRate = SPEEDS[currentSpeedIdx];
    } else if (isPlaying && !isPaused) {
      synth.cancel();
      speakSection(currentSectionIdx);
    }
  }

  function stopAndClose() {
    if (useMP3) stopMP3();
    else synth.cancel();
    isPlaying = false;
    isPaused = false;
    currentSectionIdx = 0;
    hidePlayer();
    updateUI();
  }

  function onProgressClick(e) {
    var bar = e.currentTarget;
    var rect = bar.getBoundingClientRect();
    var pct = (e.clientX - rect.left) / rect.width;

    if (useMP3 && audioElement) {
      audioElement.currentTime = pct * audioDuration;
      updateUI();
    } else {
      var targetIdx = Math.floor(pct * sections.length);
      if (targetIdx >= 0 && targetIdx < sections.length) {
        synth.cancel();
        speakSection(targetIdx);
      }
    }
  }

  // ── Keep-alive & Cleanup ─────────────────────────────────────────

  window.addEventListener('beforeunload', function() {
    if (synth) synth.cancel();
    if (audioElement) { audioElement.pause(); }
  });

  var keepAliveInterval;
  function startKeepAlive() {
    keepAliveInterval = setInterval(function() {
      if (!useMP3 && synth && synth.speaking && !synth.paused) {
        synth.pause();
        synth.resume();
      }
    }, 10000);
  }

  // ── Init ─────────────────────────────────────────────────────────

  function init() {
    createPlayer();

    // Try MP3 first (synchronous check)
    tryLoadMP3();

    // TTS fallback keepalive
    if (!useMP3 && 'speechSynthesis' in window) {
      startKeepAlive();
    }

    updateVoiceIndicator();

    if (window.location.hash === '#listen') {
      setTimeout(togglePlay, 1000);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
