/* Учёт библиотеки: только просмотр страницы и два явно заданных действия. */
(function () {
  'use strict';
  if (window.__libraryTrackingReady || window.location.hostname !== 'shapovalov-aleksey.ru') return;
  var config = document.querySelector('script[data-library-counter]');
  if (!config) return;
  var counter = Number(config.dataset.libraryCounter);
  var book = config.dataset.libraryBook;
  if (!counter || !/^[a-z0-9-]+$/.test(book)) return;
  window.__libraryTrackingReady = true;

  window.ym = window.ym || function () { (window.ym.a = window.ym.a || []).push(arguments); };
  window.ym.l = window.ym.l || Date.now();
  var library = document.createElement('script');
  library.async = true;
  library.src = 'https://mc.yandex.ru/metrika/tag.js?id=' + counter;
  library.referrerPolicy = 'origin';
  document.head.appendChild(library);

  // Автопросмотр отключён: адрес и источник передаём без поисковых параметров.
  window.ym(counter, 'init', {
    defer: true,
    webvisor: false,
    clickmap: false,
    trackLinks: false,
    trackHash: false,
    ecommerce: false,
    disableYtm: true,
    accurateTrackBounce: true
  });
  var referer = '';
  try {
    var source = new URL(document.referrer);
    referer = source.origin;
    if (source.hostname === window.location.hostname) referer += source.pathname;
  } catch (_) { /* Прямой заход не содержит источника. */ }
  window.ym(counter, 'hit', window.location.origin + window.location.pathname, {
    title: document.title,
    referer: referer,
    params: { library_book: book }
  });

  document.addEventListener('submit', function (event) {
    var form = event.target;
    if (!form.matches('.author-connect__form') || !form.checkValidity()) return;
    // Событие означает попытку подписки. Подтверждение проверяется в DashaMail.
    window.ym(counter, 'reachGoal', 'library_subscribe_submit', { library_book: book });
  });
  document.addEventListener('click', function (event) {
    var target = event.target instanceof Element ? event.target.closest('a[data-library-action="telegram"]') : null;
    if (!target) return;
    // Переход в Telegram ещё не означает отправленное сообщение.
    window.ym(counter, 'reachGoal', 'library_telegram_click', { library_book: book });
  });
}());
