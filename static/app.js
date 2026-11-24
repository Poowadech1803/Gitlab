/* Lab 04 UI-only helper: show an in-flight label while the SPICE form
   submits. Validation and rendering stay on the Flask server. */
(function () {
  'use strict';

  var form = document.getElementById('sim-form');
  var button = document.getElementById('sim-run');
  if (!form || !button) return; // Lab 03's /calculate form is left untouched.

  var idleLabel = button.dataset.idleLabel || button.textContent.trim() ||
    'Run SPICE simulation';
  button.dataset.idleLabel = idleLabel;

  function restore() {
    button.textContent = idleLabel;
    button.disabled = false;
  }

  form.addEventListener('submit', function (event) {
    var submitter = event.submitter || document.activeElement;
    // "Change analysis" only reloads the form; it never runs ngspice.
    if (submitter && submitter.getAttribute &&
        submitter.getAttribute('name') === 'action') {
      return;
    }
    button.textContent = 'Running…';
    button.disabled = true;
  });

  document.addEventListener('DOMContentLoaded', restore);
  window.addEventListener('pageshow', restore);
})();
