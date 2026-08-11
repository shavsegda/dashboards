# -*- coding: utf-8 -*-
"""Проверки: разговорные замеры второй двери открываются одним нажатием.

Спека `025-razgovornye-zamery-vtoroj-dveri` в проекте бота.

Живой дефект владельца 11.08.2026, дословно: «нажал на уровень мышления и просто
минимап закрылся и ничего не произошло». Карточка вела ссылкой в переписку с
ботом, а замер надо было начать вручную, отправив фразу. Человек этого не понял
и не должен был.

Что проверяется — исполнением страницы в node с заглушками вместо браузера, сети
и Телеграма, а не поиском слов в исходнике:

  1. у карточки разговорного замера есть основной путь `sendData` с контрактом,
     который ждёт бот, и запасной путь ссылкой;
  2. нажатие при доступном `sendData` отправляет боту ровно один пакет и не
     открывает переписку;
  3. нажатие при НЕдоступном `sendData` открывает переписку и ничего не шлёт:
     страница различает два случая и не врёт ни в одном;
  4. подсказки переписаны: про копирование фразы говорится только там, где
     копировать действительно надо;
  5. карточка говорит ДО нажатия, что мини-апп закроется, и что будет дальше —
     начнётся замер или покажется записанное;
  6. «Паспорт целиком» устроен так же;
  7. одиннадцать карточек со своей страницей по-прежнему открываются ссылкой и
     боту ничего не шлют;
  8. в подсказках нет ни цифр-баллов, ни названий инструментов.

Плюс мутационная проверка: в страницу вносится одна точная поломка, и нужная
проверка обязана на ней покраснеть. Файл возвращается байт в байт.

Запуск:  python3 checks/razgovornye_zamery.py
Без мутаций:  python3 checks/razgovornye_zamery.py --bez-mutacij
"""

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
from lib import NODE_STUBS, ROOT, _node, inline_script, ok, run, visible

APP = "kak-ustroen/app.html"
CHECKS = Path(__file__).resolve().parent

# Три разговорных блока второй двери: своей страницы у них нет, вход — разговор.
CHAT_KEYS = ["level", "dna", "body_base"]
# Одиннадцать со своей страницей. Их нажатие ссылкой, и его трогать нельзя.
PAGE_KEYS = ["personality", "neurotype", "nervsystem", "values", "motivators",
             "interests", "decisions", "ztpi", "vulnerabilities", "stressrisk",
             "attachment"]

CARD_ACTION = "passport_card"
FULL_ACTION = "passport_full"


# --------------------------------------------------------------------------
# Живой DOM: и свёрнутые уровни `<details>`, и элементы с метками `data-*`
# --------------------------------------------------------------------------
# Разбор текста не видит, ЧТО произойдёт по нажатию, — а сломалось именно это.
# Поэтому страница исполняется целиком, а заглушка умеет отдавать оба вида
# селекторов, которыми пользуется сама страница: `details` и `[data-…]`.
TAP_DOM = r"""
globalThis.TG_CALLS = { sent: [], opened: [], copied: [] };
globalThis.TG_BACK = { shows: 0, hides: 0, bound: 0 };

function __unesc(s) {
  return String(s).replace(/&quot;/g, '"').replace(/&#39;/g, "'")
                  .replace(/&lt;/g, '<').replace(/&gt;/g, '>')
                  .replace(/&amp;/g, '&');
}

function __mkEl(tag) {
  var attrs = {}, re = /([a-zA-Z_:][-a-zA-Z0-9_:.]*)="([^"]*)"/g, m;
  while ((m = re.exec(tag))) attrs[m[1]] = __unesc(m[2]);
  var hs = [];
  return {
    tag: tag, attrs: attrs, open: false, textContent: '',
    getAttribute: function (n) {
      return Object.prototype.hasOwnProperty.call(attrs, n) ? attrs[n] : null;
    },
    setAttribute: function (n, v) { attrs[n] = String(v); },
    addEventListener: function (t, fn) { hs.push({ t: t, fn: fn }); },
    // Нажатие как в браузере: событие можно отменить, и это видно снаружи.
    click: function () {
      var ev = { prevented: 0, stopped: 0,
                 preventDefault: function () { ev.prevented++; },
                 stopPropagation: function () { ev.stopped++; } };
      hs.forEach(function (h) { if (h.t !== 'toggle') h.fn(ev); });
      return { handlers: hs.length, prevented: ev.prevented };
    },
    tap: function (isOpen) {
      this.open = !!isOpen;
      var self = this;
      hs.forEach(function (h) { if (h.t === 'toggle') h.fn({ target: self }); });
    }
  };
}

globalThis.__APP = {
  _html: '', _cache: {},
  get innerHTML() { return this._html; },
  set innerHTML(v) { this._html = String(v); this._cache = {}; },
  _pick: function (re) {
    var out = [], m, seen = {};
    while ((m = re.exec(this._html))) {
      var tag = m[0];
      seen[tag] = (seen[tag] || 0) + 1;
      var key = seen[tag] + '|' + tag;
      if (!this._cache[key]) this._cache[key] = __mkEl(tag);
      out.push(this._cache[key]);
    }
    return out;
  },
  querySelectorAll: function (sel) {
    if (sel === 'details') return this._pick(/<details\b[^>]*>/g);
    var m = /^\[([-a-zA-Z0-9_]+)\]$/.exec(sel);
    if (!m) return [];
    return this._pick(new RegExp('<[^>]*\\b' + m[1] + '="[^"]*"[^>]*>', 'g'));
  },
  querySelector: function (sel) {
    var m = /^#([-a-zA-Z0-9_:.]+)$/.exec(String(sel));
    if (!m) return null;
    var list = this.querySelectorAll('details');
    for (var i = 0; i < list.length; i++) {
      if (list[i].getAttribute('id') === m[1]) return list[i];
    }
    return null;
  },
  classList: { toggle: function () {}, add: function () {}, remove: function () {} },
  style: {}
};
globalThis.document.getElementById = function () { return globalThis.__APP; };
globalThis.window.scrollTo = function () {};
// В node `navigator` уже есть и объявлен только на чтение — присваиванием его
// не подменить. Поэтому переопределяем свойство целиком.
Object.defineProperty(globalThis, 'navigator', {
  configurable: true, writable: true,
  value: { clipboard: { writeText: function (t) {
    globalThis.TG_CALLS.copied.push(String(t));
    return Promise.resolve();
  } } }
});

/** Найти элемент собранной страницы по куску его тега. */
globalThis.tap = function (attr, needle) {
  var els = globalThis.__APP.querySelectorAll('[' + attr + ']').filter(function (e) {
    return e.tag.indexOf(needle) >= 0;
  });
  if (!els.length) throw new Error('нет элемента [' + attr + '] с «' + needle + '»');
  return els[0];
};
"""


def tg_stub(init_data: str) -> str:
    """Заглушка Телеграма. Пустые `initData` — запуск кнопкой клавиатуры, и
    только у него по документации работает `sendData`."""
    return r"""
globalThis.window.Telegram = { WebApp: {
  initData: %s, initDataUnsafe: {}, colorScheme: 'light', themeParams: {},
  viewportStableHeight: 700, version: '7.0',
  ready: function () {}, expand: function () {},
  isVersionAtLeast: function () { return true; },
  onEvent: function () {},
  setHeaderColor: function () {}, setBackgroundColor: function () {},
  sendData: function (d) { globalThis.TG_CALLS.sent.push(String(d)); },
  openTelegramLink: function (u) { globalThis.TG_CALLS.opened.push(String(u)); },
  BackButton: {
    show: function () { globalThis.TG_BACK.shows++; },
    hide: function () { globalThis.TG_BACK.hides++; },
    onClick: function () { globalThis.TG_BACK.bound++; }
  }
}};
""" % json.dumps(init_data)


def taps(search: str, js: str = "", init_data: str = "") -> dict:
    """Собрать каталог с живым DOM и заглушкой Телеграма и понажимать на него."""
    code = (NODE_STUBS.replace("'?u=tg_777'", repr(search).replace('"', "'"))
            + TAP_DOM + tg_stub(init_data) + inline_script(APP)) + r"""
const OUT = {};
setTimeout(function () {
""" + js + r"""
  OUT.calls = globalThis.TG_CALLS;
  OUT.html = globalThis.__APP.innerHTML;
  console.log('RESULT<' + JSON.stringify(OUT) + '>RESULT');
}, 60);
"""
    return _node(code)


# Список открыт: карточки разговорных замеров лежат внутри групп, и без
# разворота их в разметке нет. Открываем всё, как это делает палец.
OPEN_ALL = r"""
  globalThis.__APP.querySelectorAll('details').forEach(function (d) { d.tap(true); });
"""

# Адрес с датами: `level` пройден, `dna` и `body_base` — нет. Ровно случай
# владельца на 11.08.2026.
SEARCH_PASSED = "?u=tg_777&v=17&f=level:2026-08-10&ask=dna"
SEARCH_PLAIN = "?u=tg_777&v=17&ask=level"


def payloads(calls: dict) -> list:
    """Пакеты, ушедшие боту, разобранными."""
    return [json.loads(s) for s in calls["sent"]]


# --------------------------------------------------------------------------


def check_kontrakt_na_kartochke() -> None:
    """1. У разговорной карточки есть контракт для бота и запасная ссылка."""
    h = taps(SEARCH_PLAIN, OPEN_ALL)["html"]
    plain = h.replace("&quot;", '"')
    for key in CHAT_KEYS:
        assert f'"action":"{CARD_ACTION}","key":"{key}"' in plain, \
            f"карточка «{key}» не шлёт боту контракт второй двери"
    ok("1. три разговорные карточки шлют боту действие второй двери")

    # Действие первой двери сюда попасть не должно: это чужое пространство ключей.
    assert '"open_card"' not in plain, \
        "вторая дверь шлёт действие подвижного слоя — это чужая дверь"
    ok("1. действия подвижного слоя на второй двери нет")

    # Запасной путь остаётся в разметке всегда: `sendData` доступен не везде.
    for key in CHAT_KEYS:
        assert 'data-tglink="https://t.me/' in h, \
            f"у «{key}» пропала запасная ссылка в переписку"
    ok("1. запасная ссылка в переписку на месте")

    # «Паспорт целиком» устроен так же. Он появляется, только когда есть что
    # сшивать, — поэтому смотрим на экран человека с пройденным блоком.
    passed = taps(SEARCH_PASSED, OPEN_ALL)["html"].replace("&quot;", '"')
    assert f'"action":"{FULL_ACTION}"' in passed, \
        "«Паспорт целиком» не шлёт боту своё действие"
    ok("1. «Паспорт целиком» шлёт своё действие")


def check_nazhatie_otpravlyaet_botu() -> None:
    """2. Нажатие с доступным `sendData` отправляет боту ровно один пакет."""
    c = taps(SEARCH_PLAIN, OPEN_ALL + r"""
  OUT.tap = tap('data-send', 'level').click();
""")
    sent = payloads(c["calls"])
    assert len(sent) == 1, f"боту ушло пакетов: {len(sent)} вместо одного"
    assert sent[0] == {"action": CARD_ACTION, "key": "level"}, \
        f"боту ушло не то: {sent[0]}"
    assert c["calls"]["opened"] == [], \
        f"вместе с отправкой открылась переписка: {c['calls']['opened']}"
    assert c["tap"]["prevented"] >= 1, \
        "переход по запасной ссылке не отменён — человек уедет в переписку зря"
    ok("2. нажатие «Уровня мышления» отправляет боту один пакет и не открывает чат")

    # Все три и портрет — тем же путём.
    for key in CHAT_KEYS:
        c = taps(SEARCH_PLAIN, OPEN_ALL + f"""
  tap('data-send', '{key}').click();
""")
        got = payloads(c["calls"])
        assert got == [{"action": CARD_ACTION, "key": key}], \
            f"«{key}»: боту ушло {got}"
    ok("2. все три разговорные карточки открываются одним нажатием")

    c = taps(SEARCH_PASSED, f"""
  tap('data-send', '{FULL_ACTION}').click();
""")
    assert payloads(c["calls"]) == [{"action": FULL_ACTION}], \
        f"«Паспорт целиком»: боту ушло {c['calls']['sent']}"
    ok("2. «Паспорт целиком» открывается одним нажатием")


def check_zapasnoj_put_kogda_sendData_net() -> None:
    """3. `sendData` недоступен — открывается переписка, боту ничего не уходит."""
    # Непустые init-данные значат: мини-апп открыли не кнопкой клавиатуры.
    # По документации Телеграма `sendData` там молча ничего не делает.
    c = taps(SEARCH_PLAIN, OPEN_ALL + r"""
  OUT.tap = tap('data-tglink', 'card-open').click();
""", init_data="query_id=AAA&user=%7B%22id%22%3A777%7D")
    assert c["calls"]["sent"] == [], \
        f"страница отправила данные там, где это не работает: {c['calls']['sent']}"
    assert len(c["calls"]["opened"]) == 1, \
        f"переписка не открылась: {c['calls']['opened']}"
    assert c["calls"]["opened"][0].startswith("https://t.me/"), \
        f"ссылка ведёт не в переписку: {c['calls']['opened'][0]}"
    ok("3. без sendData нажатие открывает переписку и молчит боту")

    # И фраза, которую человек отправит руками, на экране есть.
    text = visible(c["html"])
    for phrase in ("🪜 Уровень мышления", "🧬 ДНК", "🩺 Тело: базовое"):
        assert phrase in text, f"без sendData на экране нет фразы «{phrase}»"
    ok("3. фразы для ручной отправки на экране есть")

    # Кнопка «Скопировать фразу» работает, и копируется именно фраза.
    c2 = taps(SEARCH_PASSED, r"""
  tap('data-copy', 'Паспорт').click();
""", init_data="query_id=AAA")
    assert c2["calls"]["copied"] == ["📋 Паспорт целиком"], \
        f"скопировалось не то: {c2['calls']['copied']}"
    ok("3. «Скопировать фразу» копирует фразу целиком")


def check_stranica_razlichaet_dva_sluchaya() -> None:
    """4. Два случая различаются, и страница не врёт ни в одном."""
    with_send = visible(taps(SEARCH_PLAIN, OPEN_ALL)["html"])
    without = visible(taps(SEARCH_PLAIN, OPEN_ALL,
                           init_data="query_id=AAA")["html"])

    old = "Скопируй фразу и отправь её боту"
    assert old not in with_send, \
        "с работающим нажатием страница по-прежнему просит скопировать фразу"
    assert old in without, \
        "без sendData исчезла единственная работающая подсказка"
    ok("4. подсказка про копирование осталась только там, где она правда")

    assert with_send != without, \
        "экран одинаков в обоих случаях — значит одно из двух неправда"
    ok("4. экраны двух случаев различаются")

    # Кнопок с фразой на основном пути нет: два пути к одному замеру — шум.
    assert "Скопировать фразу" not in with_send, \
        "на основном пути осталась кнопка копирования"
    assert "Скопировать фразу" in without, \
        "на запасном пути пропала кнопка копирования"
    ok("4. кнопки фразы только на запасном пути")


def check_kartochka_govorit_chto_budet() -> None:
    """5. Карточка говорит ДО нажатия: экран закроется и что будет дальше."""
    text = visible(taps(SEARCH_PASSED, OPEN_ALL)["html"])
    assert "закроется" in text, \
        "карточка молчит о том, что мини-апп закроется — ровно этим начался дефект"
    ok("5. про закрытие экрана сказано заранее")

    # Непройденный блок: нажатие начнёт замер. Пройденный: покажет записанное.
    assert "начнёт замер" in text or "начнёт" in text, \
        "не сказано, что нажатие начнёт замер"
    assert "покажет" in text, \
        "про пройденный блок не сказано, что бот покажет записанное"
    ok("5. сказано и про начало замера, и про показ записанного")

    # Обещание разное для разных карточек, а не одна фраза на всех.
    h = taps(SEARCH_PASSED, OPEN_ALL)["html"]
    hints = set(re.findall(r'class="chat-line">([^<]+)<', h))
    assert len(hints) >= 2, \
        f"подсказка одна на все карточки — значит одной из них она врёт: {hints}"
    ok("5. пройденный и непройденный блоки обещают разное")


def check_stranicy_ostalis_ssylkami() -> None:
    """6. Одиннадцать карточек со своей страницей открываются ссылкой."""
    h = taps(SEARCH_PASSED, OPEN_ALL)["html"]
    plain = h.replace("&quot;", '"')
    for key in PAGE_KEYS:
        assert f'"key":"{key}"' not in plain, \
            f"«{key}» вдруг стала отправлять данные боту — у неё есть своя страница"
    ok("6. карточки со страницей боту ничего не шлют")

    c = taps(SEARCH_PASSED, OPEN_ALL + r"""
  var els = globalThis.__APP.querySelectorAll('[href]').filter(function (e) {
    return e.tag.indexOf('personality-hexaco') >= 0;
  });
  OUT.found = els.length;
""")
    assert c["found"] >= 1, "ссылка на страницу личности пропала с экрана"
    assert c["calls"]["sent"] == [], "сборка экрана сама что-то отправила боту"
    ok("6. ссылка на страницу блока на месте")


def check_bez_ballov_v_podskazkah() -> None:
    """7. В подсказках нет ни баллов, ни названий инструментов."""
    for search, init in ((SEARCH_PASSED, ""), (SEARCH_PASSED, "query_id=AAA")):
        text = visible(taps(search, OPEN_ALL, init_data=init)["html"])
        # Латиница на экране второй двери — это аббревиатура инструмента.
        latin = re.findall(r"[A-Za-z]{2,}", text)
        assert not latin, f"на экране латиница: {sorted(set(latin))[:5]}"
        for word in ("балл", "шкал", "норм", "процент", "уровень:"):
            assert word not in text.lower(), f"на экране слово «{word}»"
    ok("7. ни латиницы, ни слов про баллы и шкалы")

    assert "undefined" not in text and "NaN" not in text, \
        "на собранном экране есть undefined или NaN"
    ok("7. экран собирается без дыр")


# --------------------------------------------------------------------------
# Мутации
# --------------------------------------------------------------------------
MUTATIONS = [
    ("контракт с ботом разъехался",
     'action: "passport_card"',
     'action: "open_card"',
     "check_kontrakt_na_kartochke"),
    ("нажатие снова только открывает переписку",
     'if (payload && canSendData(tg)) {',
     'if (payload && false) {',
     "check_nazhatie_otpravlyaet_botu"),
    ("страница решила, что sendData есть всегда",
     'return String(tg.initData == null ? "" : tg.initData) === "";',
     'return true;',
     "check_zapasnoj_put_kogda_sendData_net"),
    ("подсказка снова одна на оба случая",
     'return SEND_OK ? chatHintSend(card) : CHAT_HINT_COPY;',
     'return CHAT_HINT_COPY;',
     "check_stranica_razlichaet_dva_sluchaya"),
    ("карточка перестала предупреждать о закрытии экрана",
     'var CHAT_CLOSES = "Мини-апп закроется.";',
     'var CHAT_CLOSES = "";',
     "check_kartochka_govorit_chto_budet"),
]

MUST_MUTATE = {
    "check_kontrakt_na_kartochke",
    "check_nazhatie_otpravlyaet_botu",
    "check_zapasnoj_put_kogda_sendData_net",
    "check_stranica_razlichaet_dva_sluchaya",
    "check_kartochka_govorit_chto_budet",
}


def _one_check(name: str) -> int:
    env = dict(os.environ, ONE_CHECK=name)
    r = subprocess.run([sys.executable, str(Path(__file__)), "--odna", name],
                       capture_output=True, text=True, env=env, timeout=900)
    return r.returncode


def check_u_kazhdogo_trebovaniya_est_mutaciya() -> None:
    """8. У каждого требования есть поломка."""
    used = {m[3] for m in MUTATIONS}
    missing = MUST_MUTATE - used
    assert not missing, "без мутации остались: " + ", ".join(sorted(missing))
    ok(f"8. {len(MUST_MUTATE)} требований закрыты мутациями")


def check_polomki_lovyatsya() -> None:
    """9. Каждая поломка ловится, и страница возвращается байт в байт."""
    path = ROOT / APP
    before = path.read_text(encoding="utf-8")
    digest = hashlib.sha256(before.encode()).digest()

    caught, misses = 0, []
    for what, old, new, check in MUTATIONS:
        n = before.count(old)
        assert n == 1, f"«{what}»: место мутации встречается {n} раз, а не один"
        try:
            path.write_text(before.replace(old, new, 1), encoding="utf-8")
            if _one_check(check) == 0:
                misses.append(f"{what} → {check} осталась зелёной")
            else:
                caught += 1
                print(f"  ловит  {what}  →  {check}")
        finally:
            path.write_text(before, encoding="utf-8")

    got = path.read_text(encoding="utf-8")
    assert hashlib.sha256(got.encode()).digest() == digest, \
        f"{APP} не вернулся к исходному состоянию"
    assert not misses, "не поймано: " + "; ".join(misses)
    ok(f"9. все {caught} поломок из {len(MUTATIONS)} пойманы, страница на месте")


CHECKS_ALL = [
    check_kontrakt_na_kartochke,
    check_nazhatie_otpravlyaet_botu,
    check_zapasnoj_put_kogda_sendData_net,
    check_stranica_razlichaet_dva_sluchaya,
    check_kartochka_govorit_chto_budet,
    check_stranicy_ostalis_ssylkami,
    check_bez_ballov_v_podskazkah,
]

BY_NAME = {f.__name__: f for f in CHECKS_ALL}

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--odna":
        raise SystemExit(run([BY_NAME[args[1]]]))
    if args and args[0] == "--bez-mutacij":
        raise SystemExit(run(CHECKS_ALL))
    raise SystemExit(run(CHECKS_ALL + [check_u_kazhdogo_trebovaniya_est_mutaciya,
                                       check_polomki_lovyatsya]))
