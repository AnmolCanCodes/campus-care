(function () {
  'use strict';

  // Character counters: <textarea data-counter="id-of-span">
  document.querySelectorAll('textarea[data-counter]').forEach(function (area) {
    var out = document.getElementById(area.dataset.counter);
    if (!out) return;
    var max = area.getAttribute('maxlength');
    function update() { out.textContent = area.value.length + (max ? ' / ' + max : ''); }
    area.addEventListener('input', update);
    update();
  });

  // Loading state for forms that call the AI
  var STEPS = ['Reading your description...', 'Structuring the issue...', 'Writing the formal complaint...'];
  var timers = [];

  function resetForm(form) {
    timers.forEach(clearTimeout); timers = [];
    form.removeAttribute('aria-busy');
    var status = form.querySelector('[data-status]');
    var actions = form.querySelector('[data-actions]');
    if (status) status.hidden = true;
    if (actions) actions.hidden = false;
    form.querySelectorAll('button[type="submit"]').forEach(function (b) { b.disabled = false; });
  }

  document.querySelectorAll('form[data-loading-form]').forEach(function (form) {
    form.addEventListener('submit', function (event) {
      // Native checks first (the form has novalidate so the server can explain errors),
      // but make sure required fields are not obviously empty before showing the loader.
      var firstInvalid = Array.prototype.find.call(form.querySelectorAll('[required]'), function (el) { return !el.value.trim(); });
      if (firstInvalid) { return; } // let the server return a clear message

      var status = form.querySelector('[data-status]');
      var list = form.querySelector('[data-status-lines]');
      var actions = form.querySelector('[data-actions]');
      form.setAttribute('aria-busy', 'true');
      if (status && list) {
        list.innerHTML = '';
        status.hidden = false;
        if (actions) actions.hidden = true;
        STEPS.forEach(function (text, i) {
          timers.push(setTimeout(function () {
            var li = document.createElement('li');
            li.textContent = text;
            list.appendChild(li);
          }, i * 2200));
        });
      } else {
        var btn = form.querySelector('button[type="submit"]');
        if (btn) { btn.textContent = 'Regenerating...'; }
      }
      // Disable after the browser has collected the form data
      setTimeout(function () {
        form.querySelectorAll('button[type="submit"]').forEach(function (b) { b.disabled = true; });
      }, 0);
    });
  });

  // Back/forward cache: never show a stuck loader
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) document.querySelectorAll('form[data-loading-form]').forEach(resetForm);
  });

  // Copy button: <button data-copy="id-of-hidden-textarea">
  document.querySelectorAll('[data-copy]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var source = document.getElementById(btn.dataset.copy);
      var note = document.querySelector('[data-copy-status]');
      if (!source) return;
      var text = source.value;

      function done(ok) {
        var original = btn.textContent;
        btn.textContent = ok ? 'Copied' : 'Copy failed';
        if (note && !ok) note.textContent = 'Your browser blocked copying. Select the text and copy it manually.';
        setTimeout(function () { btn.textContent = original; }, 2000);
      }

      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(function () { done(true); }, function () { done(false); });
      } else {
        var tmp = document.createElement('textarea');
        tmp.value = text; tmp.style.position = 'fixed'; tmp.style.opacity = '0';
        document.body.appendChild(tmp); tmp.select();
        var ok = false;
        try { ok = document.execCommand('copy'); } catch (err) { ok = false; }
        document.body.removeChild(tmp);
        done(ok);
      }
    });
  });
})();

(function () {
  'use strict';
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Home hint: types the secret path once, after the page has settled
  document.querySelectorAll('[data-typed]').forEach(function (el) {
    var full = el.textContent.trim();
    if (reduce) return;
    el.textContent = '';
    var i = 0;
    function tick() {
      if (i < full.length) { i += 1; el.textContent = full.slice(0, i); setTimeout(tick, 90); }
    }
    setTimeout(tick, 1900);
  });

  // Rant box: rotate the placeholder while it is empty
  document.querySelectorAll('textarea[data-placeholders]').forEach(function (area) {
    var list;
    try { list = JSON.parse(area.dataset.placeholders); } catch (e) { return; }
    if (!list || list.length < 2) return;
    var n = 0;
    setInterval(function () {
      if (area.value !== '') return;
      n = (n + 1) % list.length;
      area.placeholder = list[n];
    }, 3500);
  });
})();