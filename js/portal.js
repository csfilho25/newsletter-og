/**
 * O&G + Mining Intelligence Brief — Portal Logic
 * Loads editions from index.json and renders hero + archive
 */

(function() {
  'use strict';

  const MONTHS_PT = {
    '01': 'Janeiro', '02': 'Fevereiro', '03': 'Marco',
    '04': 'Abril', '05': 'Maio', '06': 'Junho',
    '07': 'Julho', '08': 'Agosto', '09': 'Setembro',
    '10': 'Outubro', '11': 'Novembro', '12': 'Dezembro'
  };

  const WEEKDAYS_PT = ['Domingo', 'Segunda-feira', 'Terca-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sabado'];

  function formatDate(dateStr) {
    const parts = dateStr.split('-');
    const day = parseInt(parts[2]);
    const month = MONTHS_PT[parts[1]] || parts[1];
    const year = parts[0];
    const d = new Date(dateStr + 'T12:00:00');
    const weekday = WEEKDAYS_PT[d.getDay()];
    return `${weekday}, ${day} de ${month} de ${year}`;
  }

  function formatDateShort(dateStr) {
    const parts = dateStr.split('-');
    const day = parts[2];
    const month = MONTHS_PT[parts[1]] || parts[1];
    return `${day} ${month.substring(0, 3)} ${parts[0]}`;
  }

  function renderHero(edition) {
    const badge = document.getElementById('hero-badge');
    const title = document.getElementById('hero-title');
    const highlights = document.getElementById('hero-highlights');
    const readBtn = document.getElementById('hero-read-btn');
    const listenBtn = document.getElementById('hero-listen-btn');

    if (!edition) {
      badge.textContent = 'Nenhuma edicao disponivel';
      return;
    }

    badge.textContent = `Ed. #${edition.number} — ${formatDate(edition.date)}`;
    title.textContent = edition.title;

    highlights.innerHTML = '';
    if (edition.highlights) {
      edition.highlights.forEach(function(h) {
        const li = document.createElement('li');
        li.textContent = h;
        highlights.appendChild(li);
      });
    }

    const editionUrl = 'editions/' + edition.file;
    readBtn.href = editionUrl;
    listenBtn.href = editionUrl + '#listen';
  }

  function renderArchive(editions) {
    const grid = document.getElementById('archive-grid');
    grid.innerHTML = '';

    if (!editions || editions.length === 0) {
      grid.innerHTML = '<div class="archive-empty">Nenhuma edicao anterior disponivel ainda.</div>';
      return;
    }

    editions.forEach(function(edition) {
      const card = document.createElement('a');
      card.className = 'archive-card';
      card.href = 'editions/' + edition.file;

      let highlightsHtml = '';
      if (edition.highlights) {
        highlightsHtml = '<ul class="archive-card-highlights">' +
          edition.highlights.map(function(h) { return '<li>' + h + '</li>'; }).join('') +
        '</ul>';
      }

      card.innerHTML =
        '<div class="archive-card-date">' + formatDate(edition.date) + '</div>' +
        '<span class="archive-card-edition">Ed. #' + edition.number + '</span>' +
        '<h3>' + edition.title + '</h3>' +
        highlightsHtml;

      grid.appendChild(card);
    });
  }

  function loadEditions() {
    fetch('editions/index.json')
      .then(function(res) {
        if (!res.ok) throw new Error('Failed to load editions');
        return res.json();
      })
      .then(function(data) {
        if (data.editions && data.editions.length > 0) {
          renderHero(data.editions[0]);
          renderArchive(data.editions.slice(1));
        } else {
          renderHero(null);
          renderArchive([]);
        }
      })
      .catch(function(err) {
        console.error('Error loading editions:', err);
        document.getElementById('hero-badge').textContent = 'Erro ao carregar edicoes';
        document.getElementById('archive-grid').innerHTML =
          '<div class="archive-empty">Erro ao carregar arquivo. Tente novamente.</div>';
      });
  }

  // Init
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadEditions);
  } else {
    loadEditions();
  }
})();
