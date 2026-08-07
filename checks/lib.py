# -*- coding: utf-8 -*-
"""Общие помощники для проверок мини-аппов.

Зачем это есть. Мини-аппы — это HTML со скриптом внутри, и проверить их
разбором текста можно только поверхностно: «слово есть, слова нет». Настоящие
ошибки — в логике: тест остался в списке, ключ поля переехал, старый результат
из памяти телефона снова уехал в базу. Поэтому проверки делают две вещи:

1. **Вырезают скрипт из HTML и исполняют его в node** с заглушками вместо
   браузера и Телеграма. После этого можно звать те же функции, что зовёт
   человек, и смотреть, что уходит в базу.
2. **Читают `bot.py` разбором AST** — как проверки в `specs/00*/checks.py`.
   Импортировать бота нельзя: при импорте он тянет токены и сеть.

Правило конституции, принцип II: проверка обязана падать при сломанной логике.
Поэтому сравниваем не «есть ли слово», а конкретные ключи и значения.
"""

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]           # локальный клон dashboards
BOT = Path(os.environ.get("BOT_PY") or (
    Path.home() / "Desktop" / "Файлы для работы на воркшопах" /
    "Рабочие вопросы" / "vslukh-bot" / "bot.py"))

PASSED = 0
FAILED: List[str] = []


def ok(name: str) -> None:
    global PASSED
    PASSED += 1
    print(f"  ok   {name}")


def report(title: str) -> int:
    """Итог прогона. Возвращает код выхода: 0 — всё зелёное."""
    if FAILED:
        print(f"\n{title}: провалено {len(FAILED)} из {len(FAILED) + PASSED}")
        for f in FAILED:
            print(f"  ПАДАЕТ  {f}")
        return 1
    print(f"\n{title}: всё зелёное, {PASSED} проверок.")
    return 0


def run(fns) -> int:
    """Прогнать проверки по очереди. Упавшая не останавливает остальные:
    иначе после первой ошибки не видно всей картины."""
    for fn in fns:
        print(f"{(fn.__doc__ or fn.__name__).splitlines()[0]}")
        try:
            fn()
        except KeyError as e:
            FAILED.append(f"{fn.__name__}: нет карточки или ключа {e}")
            print(f"  ПАДАЕТ нет карточки или ключа {e}")
        except AssertionError as e:
            FAILED.append(f"{fn.__name__}: {e}")
            print(f"  ПАДАЕТ {e}")
    return report(sys.argv[0].rsplit("/", 1)[-1])


# --------------------------------------------------------------------------
# HTML мини-аппа
# --------------------------------------------------------------------------
def html(rel: str) -> str:
    p = ROOT / rel
    assert p.exists(), f"нет файла {p}"
    return p.read_text(encoding="utf-8")


def inline_script(rel: str) -> str:
    """Свой скрипт мини-аппа: тег `<script>` без `src`. Их всегда один."""
    src = html(rel)
    found = [m.group(1) for m in
             re.finditer(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", src, re.S)]
    assert len(found) == 1, f"в {rel} не один свой скрипт, а {len(found)}"
    return found[0]


def pure_block(rel: str) -> str:
    """Блок «ЧИСТАЯ ЛОГИКА» — часть скрипта, которая не трогает DOM и сеть."""
    s = inline_script(rel)
    m = re.search(r"ЧИСТАЯ ЛОГИКА: НАЧАЛО(.*?)ЧИСТАЯ ЛОГИКА: КОНЕЦ", s, re.S)
    assert m, f"в {rel} нет границ блока чистой логики"
    body = m.group(1)
    # Отрезаем хвост комментария-заголовка и начало комментария-подвала: сами
    # маркеры лежат внутри /* … */, и без этого в node уедет мусор.
    body = body[body.index("*/") + 2:]
    return body[:body.rindex("/*")]


NODE_STUBS = r"""
// Заглушки вместо браузера и Телеграма. Всё, что уходит в сеть и в DOM,
// подменяется; логика замера, подсчёта и сборки записи остаётся боевой.
globalThis.window = { location: { search: '?u=tg_777' } };
globalThis.localStorage = {
  _s: {},
  getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
  setItem(k, v) { this._s[k] = String(v); },
  removeItem(k) { delete this._s[k]; }
};
globalThis.document = {
  getElementById() { return { style: {}, innerHTML: '', textContent: '' }; },
  createElement() { return { style: {}, setAttribute() {}, select() {} }; },
  body: { appendChild() {}, removeChild() {} },
  execCommand() { return true; }
};
globalThis.PUSHED = [];
globalThis.fetch = async function (url, opts) {
  globalThis.PUSHED.push({ url: String(url), body: opts && opts.body ? JSON.parse(opts.body) : null });
  return { ok: true, status: 201, json: async () => [] };
};
"""


def _node(js: str) -> Dict:
    """Выполнить JS в node и забрать то, что он напечатал через RESULT<json>."""
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False,
                                     encoding="utf-8") as f:
        f.write(js)
        path = f.name
    try:
        r = subprocess.run(["node", path], capture_output=True, text=True,
                           timeout=60)
    finally:
        os.unlink(path)
    assert r.returncode == 0, f"node упал: {r.stderr.strip()[:2000]}"
    m = re.search(r"RESULT<(.*)>RESULT", r.stdout, re.S)
    assert m, f"скрипт ничего не вернул. stdout: {r.stdout[:500]}"
    return json.loads(m.group(1))


def form_app(rel: str, extra_js: str = "") -> Dict:
    """Прогнать мини-апп-опросник: заполнить все его тесты и посмотреть запись.

    Скрипт берётся до метки «=== Старт ===»: дальше идёт запуск отрисовки,
    который в проверке ни к чему. Всё до неё — объявления, шкалы, подсчёт и
    сборка записи, то есть ровно то, что надо проверить.
    """
    s = inline_script(rel)
    mark = "// === Старт ==="
    assert mark in s, f"в {rel} нет метки «{mark}» — не знаю, где кончаются объявления"
    body = s.split(mark)[0]
    js = NODE_STUBS + body + r"""
globalThis.__api = { TESTS, SCORERS, BLOCK, INSTRUMENT, buildScores, buildAnswers,
                     results, STORE_KEY, RESULT_KEY, CLOUD_KEY, UID,
                     // Набор «отвечено в этом заходе». Есть только у страниц с
                     // несколькими тестами; у односоставных его нет и не нужно.
                     answeredNow: (typeof answeredNow === 'undefined' ? null : answeredNow) };
const api = globalThis.__api;

/** Пройти один тест, отвечая одним и тем же значением. Как живой человек,
 *  только без тапов: state здесь не нужен, считает та же функция.
 *  Ключ помечается как отвеченный сейчас — ровно это делает живой ответ. */
function fill(key, value) {
  const t = api.TESTS.find(x => x.key === key);
  if (!t) throw new Error('нет теста ' + key);
  const ans = {};
  t.items.forEach((it, i) => {
    const scale = it.scale || t.scale;
    const v = (value === null) ? scale[0].v : value;
    ans[i] = v;
  });
  const s = api.SCORERS[key](ans);
  api.results[key] = { nums: s.nums, band: s.band, c: s.c, data: s.data,
                       answers: ans, completed_at: new Date().toISOString() };
  if (api.answeredNow) api.answeredNow.add(key);
  return s;
}

/** Положить результат ПРОШЛОГО захода: так он приходит из памяти телефона или
 *  из облака. Ключ намеренно НЕ помечается отвеченным — в базу он попасть не
 *  должен, и проверка на это и смотрит. */
function fillFromMemory(key, value) {
  const marked = api.answeredNow && api.answeredNow.has(key);
  fill(key, value);
  if (api.answeredNow && !marked) api.answeredNow.delete(key);
  api.results[key].completed_at = '2026-08-03T10:00:00.000Z';
  return api.results[key];
}
const OUT = {
  block: api.BLOCK, instrument: api.INSTRUMENT,
  keys: api.TESTS.map(t => t.key),
  titles: api.TESTS.map(t => t.title),
  sizes: api.TESTS.map(t => t.items.length),
  scorers: Object.keys(api.SCORERS),
  storeKeys: [api.STORE_KEY, api.RESULT_KEY, api.CLOUD_KEY]
};
""" + extra_js + r"""
console.log('RESULT<' + JSON.stringify(OUT) + '>RESULT');
"""
    return _node(js)


DOM_STUB = r"""
globalThis.document.getElementById = function () {
  return { style: {}, innerHTML: '', textContent: '',
           querySelectorAll: function () { return []; },
           classList: { toggle() {} } };
};
globalThis.window.scrollTo = function () {};
"""


def form_render(rel: str) -> str:
    """Собрать экран списка мини-аппа целиком и отдать готовый HTML.

    Ошибку шаблона разбором текста не поймать: страница просто останется пустой.
    Поэтому скрипт исполняется весь, с заглушками вместо браузера и сети.
    """
    js = NODE_STUBS + DOM_STUB + inline_script(rel) + r"""
setTimeout(function () {
  console.log('RESULT<' + JSON.stringify({ html: app.innerHTML }) + '>RESULT');
}, 50);
"""
    return _node(js)["html"]


RICH_DOM = r"""
// Заглушка живого элемента: у формы есть слушатели, ползунки и поля ввода.
// Без них суточная страница падает уже на отрисовке.
globalThis.document.getElementById = function () {
  return { style: {}, innerHTML: '', textContent: '', value: '', disabled: false,
           addEventListener() {}, removeEventListener() {},
           setAttribute() {}, getAttribute() { return null; },
           querySelectorAll() { return []; },
           classList: { toggle() {}, add() {}, remove() {} } };
};
globalThis.window.scrollTo = function () {};
"""


def app_run(rel: str, js: str) -> Dict:
    """Исполнить мини-апп целиком и вернуть то, что собрал переданный кусок JS.

    Нужно, чтобы смотреть на ЭКРАНЫ, а не на исходник: человек читает
    собранный HTML. Скрипт исполняется весь, заглушки подменяют браузер, сеть и
    Телеграм. Переданный `js` кладёт что хочет в объект `OUT`, он и возвращается.

    Внутри `js` доступно всё, что объявил сам мини-апп: TESTS, SCORERS, results,
    state, app, store или finish. Ответы сервера подменены, поэтому запись
    доходит до конца и виден настоящий экран результата, а не «Сохраняю…».
    """
    code = NODE_STUBS + RICH_DOM + inline_script(rel) + r"""
const OUT = {};
/** Пройти тест целиком, отвечая одним значением на каждый пункт. Значения нет
 *  в шкале пункта — берём первое, как сделал бы человек. */
function __answers(key, value) {
  const t = TESTS.find(x => x.key === key);
  if (!t) throw new Error('нет теста ' + key);
  const ans = {};
  t.items.forEach((it, i) => {
    const scale = it.scale || t.scale;
    const opt = scale.find(s => s.v === value) || scale[0];
    ans[i] = opt.v;
  });
  return ans;
}
/** Отправить замер тем же путём, каким его отправляет человек. */
async function __pass(key, value) {
  const ans = __answers(key, value);
  state.key = key;
  state.idx = 0;
  state.answers = ans;
  if (typeof store === 'function') {
    await store(key, SCORERS[key](ans), Object.assign({}, ans));
  } else {
    await finish();
  }
  return app.innerHTML;
}
(async function () {
  await new Promise(r => setTimeout(r, 30));
""" + js + r"""
  console.log('RESULT<' + JSON.stringify(OUT) + '>RESULT');
})();
"""
    return _node(code)


TAG_RE = re.compile(r"<[^>]*>")
ENTITIES = {"&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"',
            "&#39;": "'", "&nbsp;": " "}


def visible(html_text: str) -> str:
    """Текст, который человек реально читает: без тегов и без мнемоник.

    Имена классов и обработчики живут внутри тегов и человеку не видны —
    поэтому проверять надо именно этот текст, а не исходник страницы.
    """
    out = TAG_RE.sub(" ", html_text)
    for k, v in ENTITIES.items():
        out = out.replace(k, v)
    return re.sub(r"\s+", " ", out)


def catalog_render(search: str) -> str:
    """Собрать каталог целиком, как в телефоне, и отдать готовый HTML.

    Скрипт исполняется весь, включая отрисовку: заглушки подменяют только
    браузер и сеть. Так ловятся ошибки шаблона, которых разбор текста не видит.
    """
    js = (NODE_STUBS.replace("'?u=tg_777'", repr(search).replace('"', "'"))
          + DOM_STUB + inline_script("kak-ty/app.html")) + r"""
setTimeout(function () {
  console.log('RESULT<' + JSON.stringify({ html: app.innerHTML }) + '>RESULT');
}, 50);
"""
    return _node(js)["html"]


TAP_DOM = r"""
// Живой DOM ради одного: проверить НАЖАТИЕ. Разбор текста не видит, что
// произойдёт по клику, а именно там ломался вход в замеры-разговоры.
//
// Что умеет заглушка: помнит собранную разметку, отдаёт по селектору «[атрибут]»
// элементы с их настоящими атрибутами и хранит слушателей. Дальше проверка жмёт
// элемент и смотрит, что ушло в Телеграм.
globalThis.TG_CALLS = { sent: [], opened: [], bound: 0 };

function __unesc(s) {
  return String(s).replace(/&quot;/g, '"').replace(/&#39;/g, "'")
                  .replace(/&lt;/g, '<').replace(/&gt;/g, '>')
                  .replace(/&amp;/g, '&');
}

function __mkEl(tag) {
  var attrs = {}, re = /([a-zA-Z_:][-a-zA-Z0-9_:.]*)="([^"]*)"/g, m;
  while ((m = re.exec(tag))) attrs[m[1]] = __unesc(m[2]);
  var handlers = [];
  return {
    tag: tag,
    attrs: attrs,
    textContent: '',
    getAttribute: function (n) {
      return Object.prototype.hasOwnProperty.call(attrs, n) ? attrs[n] : null;
    },
    setAttribute: function (n, v) { attrs[n] = String(v); },
    addEventListener: function (t, fn) { handlers.push(fn); globalThis.TG_CALLS.bound++; },
    handlers: handlers,
    // Нажатие как в браузере: событие можно отменить, и это видно снаружи.
    click: function () {
      var ev = { prevented: 0, stopped: 0,
                 preventDefault: function () { ev.prevented++; },
                 stopPropagation: function () { ev.stopped++; } };
      handlers.forEach(function (fn) { fn(ev); });
      return { handlers: handlers.length, prevented: ev.prevented };
    }
  };
}

globalThis.__APP = {
  _html: '',
  // Один и тот же элемент разметки должен отдаваться одним и тем же объектом:
  // иначе слушатель уходит в пустоту и нажатие ничего не проверяет. Новая
  // разметка — новые объекты, как в браузере.
  _cache: {},
  get innerHTML() { return this._html; },
  set innerHTML(v) { this._html = String(v); this._cache = {}; },
  querySelectorAll: function (sel) {
    var m = /^\[([-a-zA-Z0-9_]+)\]$/.exec(sel);
    if (!m) return [];
    var attr = m[1], out = [], seen = {};
    var re = new RegExp('<[^>]*\\b' + attr + '="[^"]*"[^>]*>', 'g'), t;
    while ((t = re.exec(this._html))) {
      // Ключ — сам тег и номер его повтора, БЕЗ имени атрибута: у одного тега
      // их несколько, и по каждому селектору должен приходить один объект.
      var tag = t[0];
      seen[tag] = (seen[tag] || 0) + 1;
      var key = seen[tag] + '|' + tag;
      if (!this._cache[key]) this._cache[key] = __mkEl(tag);
      out.push(this._cache[key]);
    }
    return out;
  },
  classList: { toggle: function () {}, add: function () {}, remove: function () {} },
  style: {}
};
globalThis.document.getElementById = function () { return globalThis.__APP; };
globalThis.window.scrollTo = function () {};

/** Найти элемент собранной страницы по куску его тега. */
globalThis.tap = function (attr, needle) {
  var els = globalThis.__APP.querySelectorAll('[' + attr + ']').filter(function (e) {
    return e.tag.indexOf(needle) >= 0;
  });
  if (!els.length) throw new Error('нет элемента [' + attr + '] с «' + needle + '»');
  return els[0];
};
"""


def tg_stub(init_data: str = "", methods: str = "") -> str:
    """Заглушка Телеграма. `init_data` пустой — запуск кнопкой клавиатуры, и
    только у него по документации работает `sendData`."""
    return r"""
globalThis.window.Telegram = { WebApp: {
  initData: %s,
  initDataUnsafe: {},
  version: '7.0',
  ready: function () {}, expand: function () {},
  isVersionAtLeast: function () { return true; },
  sendData: function (d) { globalThis.TG_CALLS.sent.push(String(d)); },
  openTelegramLink: function (u) { globalThis.TG_CALLS.opened.push(String(u)); }
  %s
}};
""" % (json.dumps(init_data), ("," + methods) if methods else "")


def catalog_taps(search: str, js: str, init_data: str = "",
                 telegram: bool = True, extra_tg: str = "") -> Dict:
    """Собрать каталог с живым DOM и заглушкой Телеграма и понажимать на него.

    `js` кладёт что хочет в объект `OUT`: внутри доступны `tap('data-send', …)`,
    `TG_CALLS` и всё, что объявил сам мини-апп.
    """
    stubs = NODE_STUBS.replace("'?u=tg_777'", repr(search).replace('"', "'"))
    code = stubs + TAP_DOM + (tg_stub(init_data, extra_tg) if telegram else "") \
        + inline_script("kak-ty/app.html") + r"""
const OUT = {};
setTimeout(function () {
""" + js + r"""
  OUT.calls = globalThis.TG_CALLS;
  OUT.html = globalThis.__APP.innerHTML;
  console.log('RESULT<' + JSON.stringify(OUT) + '>RESULT');
}, 50);
"""
    return _node(code)


def catalog(extra_js: str = "") -> Dict:
    """Прогнать чистую логику каталога «Как ты?»."""
    js = pure_block("kak-ty/app.html") + r"""
const OUT = {
  containers: LIFE_CONTAINERS,
  rhythms: RHYTHMS.map(r => r.id),
  registry: REGISTRY.map(r => ({
    key: r.key, label: r.label, days: r.days, section: r.section,
    containers: r.containers, group: r.group, what: r.what, size: r.size,
    url: r.url || null, phrase: r.phrase || null, cond: r.cond || null,
    once: !!r.once, after: r.after || null
  }))
};
""" + extra_js + r"""
console.log('RESULT<' + JSON.stringify(OUT) + '>RESULT');
"""
    return _node(js)


# --------------------------------------------------------------------------
# bot.py — только чтение, разбором AST
# --------------------------------------------------------------------------
_BOT_WANTED = {
    "LIFE_CONTAINERS", "CARD_META", "COVERAGE_MAP", "STATE_BLOCK_LINES",
    "INSTRUMENT_PAST_BLOCKS", "KAK_TY_KEYS", "STATE_BLOCKS_META",
    "INSTRUMENT_VALID", "VALID_RU", "VALID_DRAFT", "VALID_NONE",
}


def bot() -> Dict:
    """Реестры бота. Ключи полей сверяем по ним, а не по памяти."""
    src = BOT.read_text(encoding="utf-8")
    tree = ast.parse(src)
    picked = []
    found: Set[str] = set()
    for node in tree.body:
        name = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
        if name in _BOT_WANTED:
            picked.append(node)
            found.add(name)
    missing = _BOT_WANTED - found
    assert not missing, f"в bot.py не нашёл: {', '.join(sorted(missing))}"
    ns: Dict = {"Dict": Dict, "List": List, "Optional": Optional,
                "Set": Set, "Tuple": Tuple}
    exec(compile(ast.Module(body=picked, type_ignores=[]), "<bot>", "exec"), ns)
    return ns


# Адреса страниц замеров. Отдельно от `bot()`: их сборка требует `os.getenv`, а
# реестры полей — нет, и мешать одно с другим значит тащить окружение в проверку
# ключей. Нужно с 07.08.2026 (спека 011): каталог ведёт на страницы, и адрес в
# каталоге обязан совпадать с адресом в боте — иначе человек уедет на страницу,
# которой бот не знает, и запись ляжет мимо.
_BOT_URL_WANTED = {
    "STATE_DAY_MINI_APP_URL", "STATE_WEEK_MINI_APP_URL",
    "STATE_MONTH_MINI_APP_URL", "STATE_QUARTER_MINI_APP_URL",
    "STATE_CLINICAL_MINI_APP_URL", "SELFHOOD_MINI_APP_URL",
    "STATE_MEANING_MINI_APP_URL", "STATE_BURNOUT_MINI_APP_URL",
    "STATE_SUPPORT_MINI_APP_URL", "STATE_NEEDS_MINI_APP_URL",
    "STATE_MIND_MINI_APP_URL", "SELFESTEEM_MINI_APP_URL",
    "STATE_MOVE_MINI_APP_URL", "STATE_PEOPLE_MINI_APP_URL",
    "STATE_FACTS_MINI_APP_URL", "STATE_NOTE_MINI_APP_URL",
    "STATE_MONEY_MINI_APP_URL", "STATE_DOMAINS_MINI_APP_URL",
    "CARD_MINI_APP_URL", "CARDS_MOVED_TO_PAGE", "MINI_APP_V",
}


def bot_urls() -> Dict:
    """Адреса страниц замеров и версия из `bot.py`. Только чтение."""
    tree = ast.parse(BOT.read_text(encoding="utf-8"))
    picked, found = [], set()
    for node in tree.body:
        name = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
        if name in _BOT_URL_WANTED:
            picked.append(node)
            found.add(name)
    missing = _BOT_URL_WANTED - found
    assert not missing, f"в bot.py не нашёл адресов: {', '.join(sorted(missing))}"
    ns: Dict = {"os": os, "Dict": Dict, "List": List, "Optional": Optional,
                "Set": Set, "Tuple": Tuple}
    exec(compile(ast.Module(body=picked, type_ignores=[]), "<bot-urls>", "exec"), ns)
    return ns


def block_paths(b: Dict, block: str) -> Set[str]:
    """Пути, которые бот читает из блока: «pss.total» → берём как есть."""
    return {p for p, *_rest in b["STATE_BLOCK_LINES"].get(block, [])}


def dig(scores: Dict, path: str):
    """Достать значение по пути «инструмент.поле». Нет — None, не догадка."""
    cur = scores
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur
