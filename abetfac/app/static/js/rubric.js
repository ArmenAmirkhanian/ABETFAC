// Rubric score button interaction — handles highlight, hidden input, keyboard nav
(function () {
  'use strict';

  function initRubricGroup(group) {
    const field = group.dataset.field;
    const hidden = document.getElementById('hidden_' + field);
    const buttons = group.querySelectorAll('.score-btn');

    function selectScore(btn) {
      buttons.forEach(b => b.classList.remove('selected', 'active'));
      btn.classList.add('selected', 'active');
      hidden.value = btn.dataset.score;
      // Trigger autosave
      document.dispatchEvent(new Event('rubric-changed'));
    }

    buttons.forEach(btn => {
      btn.addEventListener('click', () => selectScore(btn));
    });

    // Highlight pre-selected value on page load
    const preSelected = group.querySelector(`.score-btn[data-score="${hidden.value}"]`);
    if (preSelected) preSelected.classList.add('selected', 'active');

    // Keyboard shortcut: number keys 1-4 when any button in group is focused
    group.addEventListener('keydown', e => {
      if (['1', '2', '3', '4'].includes(e.key)) {
        const target = group.querySelector(`.score-btn[data-score="${e.key}"]`);
        if (target) { selectScore(target); e.preventDefault(); }
      }
    });
  }

  document.querySelectorAll('.score-btn-group').forEach(initRubricGroup);

  // Autosave draft via HTMX every 30s and on any score change
  const form = document.getElementById('rubric-form');
  if (!form) return;

  const statusEl = document.getElementById('autosave-status');
  let saveTimer = null;

  function scheduleSave() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(saveDraft, 30000);
  }

  function saveDraft() {
    const data = new FormData(form);
    const batchId = form.dataset.batchId;
    fetch(`/batches/${batchId}/assess/draft`, {
      method: 'POST',
      body: data,
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    }).then(r => {
      if (r.ok && statusEl) {
        statusEl.textContent = 'Draft saved';
        setTimeout(() => { statusEl.textContent = ''; }, 3000);
      }
    }).catch(() => {});
  }

  document.addEventListener('rubric-changed', scheduleSave);
  scheduleSave();
})();
