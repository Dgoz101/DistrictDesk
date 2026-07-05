/**
 * Insert canned response snippets into the ticket comment textarea.
 */
(function () {
  'use strict';

  var dataEl = document.getElementById('canned-responses-data');
  var picker = document.getElementById('canned-response-picker');
  var insertBtn = document.getElementById('canned-response-insert');
  var textarea = document.getElementById('ticket-comment-body');

  if (!dataEl || !picker || !insertBtn || !textarea) {
    return;
  }

  var snippets;
  try {
    snippets = JSON.parse(dataEl.textContent);
  } catch (e) {
    return;
  }

  var byId = {};
  snippets.forEach(function (s) {
    byId[String(s.id)] = s.body;
  });

  function insertText(text) {
    if (!text) return;
    var existing = textarea.value;
    if (existing.trim()) {
      textarea.value = existing.replace(/\s+$/, '') + '\n\n' + text;
    } else {
      textarea.value = text;
    }
    textarea.focus();
  }

  insertBtn.addEventListener('click', function () {
    var id = picker.value;
    if (!id) return;
    insertText(byId[id] || '');
  });

  picker.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      insertBtn.click();
    }
  });
})();
