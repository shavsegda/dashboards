# -*- coding: utf-8 -*-
"""Проверки трёх новых страниц замера: полгода и год (спека 006 бота).

Что появилось:

- `state-finwell` — спокойствие с деньгами, десять пунктов, раз в полгода;
- `state-health` — здоровье в целом, десять пунктов, раз в полгода;
- `pair-faces` — опросник семьи, сорок два пункта, раз в год.

Почему проверок так много. У этих трёх карточек особые правила спеки, и каждое
из них ломается тихо:

- **деньги:** ни одного оценочного слова в результате, и «тяжело смотреть»
  закрывает карточку без записи и без повторного приглашения;
- **здоровье:** заметное ухудшение направляет к врачу и ничего не толкует;
- **семья:** пока прошёл один — говорим про ЕГО ответы, а не «про вашу семью»;
- у всех трёх русская версия **не подтверждена**: метка «рабочий перевод», ни
  одного слова про нормы.

Как проверяем. Страница исполняется в node целиком: браузер, Телеграм и база
подменены заглушками. Заглушка базы — маленькая таблица с первичным ключом:
повторная запись по занятому номеру отвечает 409, правка по окну возвращает
исправленные строки. Поэтому «одна точка за период» проверяется поведением.

Ключи полей и блоки сверяются с `bot.py` буквально, а не по памяти: разъезд имён
панели не заметят, они просто покажут пустоту.

Чего проверками НЕ берём и смотрим глазами на телефоне: как выглядят экраны, как
ведёт себя настоящая кнопка назад в настоящем клиенте и не стыдно ли читать
результат вслух.

Запуск:  python3 checks/polgoda_god.py
"""

import json
import re
from typing import Dict, List, Optional

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
# `bot_reader` — читающая часть бота: правило «одна точка за период» с
# 10.08.2026 живёт там, а не на странице (спека 023, FR-002).
from lib import (_node, block_paths, bot, bot_reader, bot_urls, dig, html,
                 inline_script, ok, run, visible)

# ---- Три страницы. Ключ — блок в базе, значение — файл ----
PAGES: Dict[str, str] = {
    "state_finwell": "state-finwell/app.html",
    "state_health": "state-health/app.html",
    "pair_faces": "pair-faces/app.html",
}

# Сколько пунктов у каждого замера. Спека называет числа прямо.
COUNT: Dict[str, int] = {"state_finwell": 10, "state_health": 10,
                         "pair_faces": 42}

# Ритм в днях. От него считается «одна точка за период».
PERIOD: Dict[str, int] = {"state_finwell": 180, "state_health": 180,
                          "pair_faces": 365}

# Верхние ключи записи. Прибиты руками: посчитать их из самого файла значит
# согласиться с любым его состоянием, включая «полей не осталось».
TOP_KEYS: Dict[str, List[str]] = {
    "state_finwell": ["finwell", "source"],
    "state_health": ["promis", "source"],
    "pair_faces": ["faces", "source"],
}

# Поля внутри блока инструмента при полном заходе.
INNER_KEYS: Dict[str, Dict[str, List[str]]] = {
    "state_finwell": {"finwell": [
        "shock", "future", "never", "enjoy", "bygetting", "lastlong",
        "gift", "leftover", "behind", "control"]},
    "state_health": {"promis": [
        "health", "qol", "physical", "mental", "social", "roles",
        "activities", "emotional", "fatigue", "pain", "alert"]},
    "pair_faces": {"faces": [
        "cohesion", "flexibility", "disengaged", "enmeshed", "rigid",
        "chaotic"]},
}

# Полный заход: то же, что делает человек, только без тапов. Значения — середина
# шкалы, кроме боли: у неё своя шкала 0–10.
FULL: Dict[str, str] = {
    "state_finwell": ("['shock','future','never','enjoy','bygetting','lastlong',"
                      "'gift','leftover','behind','control']"
                      ".forEach(function (k) { setAnswer(k, 3); });"),
    "state_health": ("['health','qol','physical','mental','social','roles',"
                     "'activities','emotional','fatigue']"
                     ".forEach(function (k) { setAnswer(k, 4); }); "
                     "setAnswer('pain', 2);"),
    "pair_faces": ("for (var i = 1; i <= 42; i++) setAnswer('i' + i, 3);"),
}

# Адрес, с которым страницу открывает каталог.
SEARCH: Dict[str, str] = {
    "state_finwell": "?u=tg_777",
    "state_health": "?u=tg_777",
    "pair_faces": "?u=tg_777",
}

# Слова, которых не может быть в результате: балл, диапазон, норма и оценка.
# Похвала запрещена так же, как порицание (правила мини-аппов, часть 4).
BAD_WORDS = ["балл", "диапазон", "норм", "процентил", "мало", "много",
             "плохо", "хорошо", "низк", "высок", "средн", "запустил",
             "молодец", "в пределах", "у людей", "отличн", "ужасн"]

# Запретные слова для страницы здоровья — список УЖЕ, чем общий, и вот почему.
#
# Подписи вариантов у этой шкалы свои: «отличное», «хорошее», «плохое»,
# «очень сильное». Это слова САМОГО инструмента и ответ САМОГО человека, а
# результат показывает ровно то, что он отметил. Переписать их «поприятнее»
# значит изменить измерение, а вырезать из результата — соврать про его ответ.
#
# Запрещено другое: чтобы страница добавляла оценку ОТ СЕБЯ — балл, сравнение с
# кем-то, «средне», «запустил». Ровно это и проверяется.
# «в среднем» из списка убрано намеренно: это формулировка самих пунктов — «каким
# в среднем было утомление». Запрещено СРАВНЕНИЕ с другими, и оно ловится
# точными оборотами, а не корнем слова.
HEALTH_BAD = ["балл", "диапазон", "норм", "процентил", "в пределах",
              "у людей", "среди людей", "выше средн", "ниже средн",
              "в среднем по", "мало", "много", "запустил", "молодец",
              "популяц"]

# Толкования: их не может быть там, где мы направляем к врачу.
INTERPRET = ["наверное", "скорее всего", "потому что", "это значит",
             "депресс", "тревожное расстройство", "выгорание у тебя"]

LATIN = re.compile(r"[A-Za-z]{2,}")


# ==========================================================================
# Заглушки: браузер, память телефона, живой DOM, таблица базы
# ==========================================================================
TG_STUB = r"""
globalThis.TG = { closing: 0, relaxed: 0, back: 0, shown: 0, closed: 0 };
globalThis.window.Telegram = { WebApp: {
  initData: '',
  initDataUnsafe: {},
  colorScheme: 'light', themeParams: {},
  ready: function () {}, expand: function () {},
  close: function () { globalThis.TG.closed++; },
  setHeaderColor: function () {}, setBackgroundColor: function () {},
  onEvent: function () {},
  enableClosingConfirmation: function () { globalThis.TG.closing++; },
  disableClosingConfirmation: function () { globalThis.TG.relaxed++; },
  BackButton: {
    onClick: function (fn) { globalThis.TG.onBack = fn; globalThis.TG.back++; },
    show: function () { globalThis.TG.shown++; },
    hide: function () {}
  }
}};
"""


def stubs(search: str, telegram: bool = False) -> str:
    """Браузер, память телефона, живой DOM и таблица базы с первичным ключом."""
    return r"""
globalThis.window = { location: { search: %(search)s } };
globalThis.history = { length: 2, back: function () { globalThis.HISTORY_BACK = (globalThis.HISTORY_BACK || 0) + 1; } };
globalThis.localStorage = {
  _s: {},
  getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
  setItem(k, v) { this._s[k] = String(v); },
  removeItem(k) { delete this._s[k]; }
};

// ---- DOM ----
// Заглушка помнит собранную разметку и отдаёт по ней живые элементы: у них есть
// слушатели и значение поля. Иначе «экран собрался, но кнопки мёртвые» проверкой
// не поймать.
function __unesc(s) {
  return String(s).replace(/&quot;/g, '"').replace(/&#39;/g, "'")
                  .replace(/&lt;/g, '<').replace(/&gt;/g, '>')
                  .replace(/&amp;/g, '&');
}

function __mkEl(tag, inner) {
  var attrs = {}, re = /([a-zA-Z_:][-a-zA-Z0-9_:.]*)="([^"]*)"/g, m;
  while ((m = re.exec(tag))) attrs[m[1]] = __unesc(m[2]);
  var handlers = [];
  return {
    tag: tag, attrs: attrs, textContent: '',
    value: attrs.value !== undefined ? attrs.value : (inner === undefined ? '' : __unesc(inner)),
    style: {}, disabled: false,
    getAttribute: function (n) {
      return Object.prototype.hasOwnProperty.call(attrs, n) ? attrs[n] : null;
    },
    setAttribute: function (n, v) { attrs[n] = String(v); },
    addEventListener: function (t, fn) { handlers.push(fn); },
    removeEventListener: function () {},
    classList: { toggle: function () {}, add: function () {}, remove: function () {} },
    handlers: handlers,
    click: function () {
      var ev = { prevented: 0, preventDefault: function () { ev.prevented++; },
                 stopPropagation: function () {} };
      handlers.forEach(function (fn) { fn(ev); });
      return { handlers: handlers.length, prevented: ev.prevented };
    }
  };
}

globalThis.__APP = {
  _html: '', _cache: {},
  get innerHTML() { return this._html; },
  set innerHTML(v) { this._html = String(v); this._cache = {}; },
  querySelectorAll: function (sel) {
    var m = /^\[([-a-zA-Z0-9_]+)\]$/.exec(sel);
    if (!m) return [];
    var attr = m[1], out = [], seen = {};
    var re = new RegExp('<[^>]*\\b' + attr + '="[^"]*"[^>]*>', 'g'), t;
    while ((t = re.exec(this._html))) {
      var tag = t[0];
      seen[tag] = (seen[tag] || 0) + 1;
      var key = seen[tag] + '|' + tag;
      if (!this._cache[key]) this._cache[key] = __mkEl(tag);
      out.push(this._cache[key]);
    }
    return out;
  },
  byId: function (id) {
    var key = 'id:' + id;
    if (this._cache[key]) return this._cache[key];
    var re = new RegExp('<([a-z]+)([^>]*\\bid="' + id + '"[^>]*)>([\\s\\S]*?)</\\1>');
    var m = re.exec(this._html);
    if (!m) {
      var self = new RegExp('<[a-z]+[^>]*\\bid="' + id + '"[^>]*>');
      var s = self.exec(this._html);
      if (!s) return null;
      this._cache[key] = __mkEl(s[0]);
      return this._cache[key];
    }
    this._cache[key] = __mkEl('<' + m[1] + m[2] + '>', m[3]);
    return this._cache[key];
  },
  classList: { toggle: function () {}, add: function () {}, remove: function () {} },
  style: {}
};

globalThis.__HEADER = {};
['progressBar', 'progressFill', 'progressText', 'progressCount'].forEach(function (id) {
  globalThis.__HEADER[id] = { style: {}, textContent: '', classList: { toggle: function () {} } };
});

globalThis.DOC_LISTENERS = [];
globalThis.document = {
  documentElement: { style: { setProperty: function () {} } },
  getElementById: function (id) {
    if (id === 'app') return globalThis.__APP;
    if (globalThis.__HEADER[id]) return globalThis.__HEADER[id];
    return globalThis.__APP.byId(id);
  },
  addEventListener: function (t, fn) { globalThis.DOC_LISTENERS.push([t, fn]); },
  createElement: function () { return { style: {}, setAttribute: function () {}, select: function () {} }; },
  body: { appendChild: function () {}, removeChild: function () {} }
};
globalThis.window.scrollTo = function () {};

// ---- База: маленькая таблица с первичным ключом ----
globalThis.DB = { rows: [] };
globalThis.CALLS = [];

function __resp(status, body) {
  return { ok: status < 300, status: status, json: async function () { return body; } };
}

globalThis.fetch = async function (url, opts) {
  var u = String(url);
  var method = (opts && opts.method) || 'GET';
  var body = (opts && opts.body) ? JSON.parse(opts.body) : null;
  globalThis.CALLS.push({ url: u, method: method, body: body });
  function q(re) { var m = re.exec(u); return m ? decodeURIComponent(m[1]) : null; }
  if (method === 'POST') {
    if (globalThis.DB.rows.some(function (r) { return r.id === body.id; })) return __resp(409, {});
    globalThis.DB.rows.push(Object.assign({}, body));
    return __resp(201, []);
  }
  if (method === 'PATCH') {
    var id = q(/[?&]id=eq\.([^&]+)/);
    var hit;
    if (id) {
      hit = globalThis.DB.rows.filter(function (r) { return r.id === id; });
    } else {
      var uid = q(/[?&]user_id=eq\.([^&]+)/), blk = q(/[?&]block=eq\.([^&]+)/);
      var from = q(/[?&]completed_at=gte\.([^&]+)/), to = q(/[?&]completed_at=lt\.([^&]+)/);
      hit = globalThis.DB.rows.filter(function (r) {
        return String(r.user_id) === uid && r.block === blk &&
               r.completed_at >= from && r.completed_at < to;
      });
    }
    hit.forEach(function (r) { Object.assign(r, body); });
    return __resp(200, hit);
  }
  return __resp(200, []);
};
%(tg)s
""" % {"search": json.dumps(search), "tg": TG_STUB if telegram else ""}


TAIL = r"""
const OUT = {};
function screen() { return globalThis.__APP.innerHTML; }
function tap(attr, needle) {
  var els = globalThis.__APP.querySelectorAll('[' + attr + ']').filter(function (e) {
    return e.tag.indexOf(needle) >= 0;
  });
  if (!els.length) throw new Error('нет элемента [' + attr + '] с «' + needle + '»');
  return els[0];
}
function byId(id) {
  var el = globalThis.document.getElementById(id);
  if (!el) throw new Error('нет элемента #' + id);
  return el;
}
(async function () {
  await new Promise(function (r) { setTimeout(r, 20); });
%(js)s
  OUT.rows = globalThis.DB.rows;
  OUT.calls = globalThis.CALLS.map(function (c) { return { url: c.url, method: c.method }; });
  console.log('RESULT<' + JSON.stringify(OUT) + '>RESULT');
})();
"""


def page(block: str, js: str, search: Optional[str] = None,
         telegram: bool = False) -> Dict:
    """Исполнить страницу целиком и вернуть то, что собрал переданный кусок JS."""
    rel = PAGES[block]
    code = (stubs(search if search is not None else SEARCH[block], telegram)
            + inline_script(rel) + TAIL % {"js": js})
    return _node(code)


def full_run(block: str, extra: str = "", search: Optional[str] = None) -> Dict:
    """Пройти замер целиком тем же путём, каким его проходит человек."""
    return page(block, "  startCard();\n  " + FULL[block] +
                "\n  await finish();\n  OUT.result = screen();\n" + extra,
                search=search)


def seed(a_js: str) -> str:
    """Положить в память телефона замер ПРОШЛОГО периода."""
    return """
  localStorage.setItem(POINTS_KEY, JSON.stringify([{
    completed_at: '2024-06-01T10:00:00.000Z', periodKey: 'прошлый-период',
    a: %s
  }]));
  POINTS = loadPoints();
  prevSaved = prevPoint(POINTS, periodKey(new Date().toISOString()));
""" % a_js


def steps_of(block: str, search: Optional[str] = None) -> List[Dict]:
    """Вопросы страницы в том порядке, в каком их видит человек."""
    got = page(block, """
  OUT.steps = visibleSteps({}, flags).map(function (s) {
    return { key: s.key, kind: s.kind, q: s.q, lo: s.lo, hi: s.hi,
             optional: !!s.optional,
             options: (s.options || []).map(function (o) { return o.l; }),
             values: (s.options || []).map(function (o) { return o.v; }) };
  });
""", search=search)
    return got["steps"]


def all_screens(block: str) -> Dict[str, str]:
    """Все экраны страницы, собранные подряд: вход, первый вопрос, результат."""
    got = page(block, """
  OUT.intro = screen();
  startCard();
  OUT.first = screen();
  """ + FULL[block] + """
  await finish();
  OUT.result = screen();
""")
    return {k: got[k] for k in ("intro", "first", "result")}


# ==========================================================================
# 1. Контракт с ботом: блок, инструмент, ключи полей
# ==========================================================================
def check_block_and_instrument() -> None:
    """1. Блок и подпись инструмента — буквально как у бота."""
    b = bot()
    for block in PAGES:
        got = page(block, "  OUT.b = BLOCK; OUT.i = INSTRUMENT; OUT.p = PERIOD_DAYS;")
        assert got["b"] == block, f"{PAGES[block]}: блок «{got['b']}», ждали «{block}»"
        assert got["i"] == block, \
            f"{PAGES[block]}: подпись инструмента «{got['i']}» разошлась с блоком"
        assert got["p"] == PERIOD[block], \
            f"{PAGES[block]}: ритм {got['p']} дней, ждали {PERIOD[block]}"
        assert block in b["CARD_META"], f"бот не знает блока «{block}»"
        assert b["CARD_META"][block]["block"] == block, \
            f"бот пишет «{block}» в другой блок"
    ok("1. блок, подпись инструмента и ритм совпадают с ботом")


def check_record_keys() -> None:
    """2. Ключи полей записи — те, что читает бот. Разъезд имён = пустые панели."""
    b = bot()
    for block, tops in TOP_KEYS.items():
        got = full_run(block)
        rows = got["rows"]
        assert len(rows) == 1, f"{PAGES[block]}: записей {len(rows)}, ждали одну"
        scores = rows[0]["scores"]
        assert sorted(scores.keys()) == sorted(tops), \
            f"{PAGES[block]}: верхние ключи {sorted(scores.keys())}, ждали {sorted(tops)}"
        for instr, inner in INNER_KEYS[block].items():
            assert sorted(scores[instr].keys()) == sorted(inner), \
                f"{PAGES[block]}, «{instr}»: поля {sorted(scores[instr].keys())}, " \
                f"ждали {sorted(inner)}"
        # Каждый путь, который бот собирается читать, в записи есть.
        for path in block_paths(b, block):
            assert dig(scores, path) is not None, \
                f"{PAGES[block]}: бот читает «{path}», а его в записи нет"
    ok("2. ключи полей и пути линий совпадают с ботом")


def check_no_totals() -> None:
    """3. Конституция IV: ни одного сводного балла в записи."""
    bad = ("total", "sum", "index", "score", "avg", "overall")
    for block in PAGES:
        got = full_run(block)
        scores = got["rows"][0]["scores"]
        for instr, fields in scores.items():
            if not isinstance(fields, dict):
                continue
            for name in fields:
                for w in bad:
                    assert w not in name.lower(), \
                        f"{PAGES[block]}: в записи есть свод «{instr}.{name}»"
    ok("3. ни одного сводного балла в записях трёх блоков")


# ==========================================================================
# 2. Честная длина и один вопрос на экран
# ==========================================================================
def check_item_count() -> None:
    """4. Пунктов ровно столько, сколько обещает спека: 10, 10 и 42."""
    for block, n in COUNT.items():
        steps = steps_of(block)
        assert len(steps) == n, \
            f"{PAGES[block]}: вопросов {len(steps)}, спека называет {n}"
        keys = [s["key"] for s in steps]
        assert len(set(keys)) == len(keys), f"{PAGES[block]}: ключи повторяются"
        for s in steps:
            assert s["q"] and len(s["q"]) > 8, \
                f"{PAGES[block]}: у вопроса «{s['key']}» нет текста"
    ok("4. пунктов ровно 10, 10 и 42")

    # Честная длина названа на входе — до начала, чтобы человек решил про время.
    for block, n in COUNT.items():
        got = page(block, "  OUT.size = CARD_SIZE; OUT.gives = WHAT_IT_GIVES;")
        size = got["size"]
        assert str(n) in size or {10: "десять", 42: "сорок два"}[n] in size.lower(), \
            f"{PAGES[block]}: честной длины нет на входе: {size!r}"
        assert "минут" in size.lower() or "секунд" in size.lower(), \
            f"{PAGES[block]}: не сказано, сколько это займёт: {size!r}"
        assert got["gives"] and len(got["gives"]) > 20, \
            f"{PAGES[block]}: нет строки «что это даст»"
    ok("4. честная длина и «что это даст» — до начала")


def check_one_question_per_screen() -> None:
    """5. Один вопрос на экран, равные интервалы, никаких таблиц-сеток."""
    for block in PAGES:
        got = page(block, """
  startCard();
  OUT.first = screen();
  OUT.qs = STEPS.map(function (s) { return s.q; });
""")
        first = got["first"]
        shown = [q for q in got["qs"] if q and q in first]
        assert len(shown) == 1, \
            f"{PAGES[block]}: на первом экране {len(shown)} вопросов, а не один"
        for bad in ("<table", "<tr", "<td", "grid-template-rows"):
            assert bad not in first.lower(), \
                f"{PAGES[block]}: на экране таблица-сетка («{bad}») — данные портятся"
    ok("5. один вопрос на экран, таблиц-сеток нет")

    # Интервалы шкалы равные: у горизонтального ряда все доли одинаковые.
    for block in PAGES:
        src = html(PAGES[block])
        rows = re.findall(r"grid-template-columns:\s*repeat\((\d+),\s*1fr\)", src)
        cells = re.findall(r"\.q-option\s*\{[^}]*\}", src)
        assert rows or cells, \
            f"{PAGES[block]}: ни ряда равными долями, ни списка одинаковых вариантов"
    ok("5. интервалы шкал равные")

    # Ни у одного пункта не сбит набор вариантов: пять градаций у пятибалльных.
    for block in ("state_finwell", "pair_faces"):
        for s in steps_of(block):
            assert len(s["options"]) == 5, \
                f"{PAGES[block]}, «{s['key']}»: градаций {len(s['options'])}, ждали 5"
            assert sorted(s["values"]) == [1, 2, 3, 4, 5], \
                f"{PAGES[block]}, «{s['key']}»: значения {s['values']}, ждали 1..5"
    ok("5. у пятибалльных пунктов ровно пять равных градаций")


# ==========================================================================
# 3. Деньги: FR-002, FR-003, FR-005
# ==========================================================================
def check_money_asks_calm_not_sums() -> None:
    """6. FR-002: вопросы про спокойствие с деньгами, а не про суммы."""
    steps = steps_of("state_finwell")
    for s in steps:
        assert s["kind"] == "options", \
            f"пункт «{s['key']}» спрашивает {s['kind']} — это ввод числа, " \
            "а суммы собирает месячный замер (FR-002)"
    ok("6. FR-002 ни одного поля для суммы")

    text = " ".join(s["q"] for s in steps).lower()
    for w in ("рубл", "сколько денег", "₽", "зарплат", "выручк", "сумм",
              "накопил", "остаток на счет", "тысяч"):
        assert w not in text, f"вопрос про сумму: «{w}»"
    ok("6. FR-002 в вопросах нет ни одной суммы")

    # И то, ради чего замер: спокойствие. Иначе это просто другой опросник.
    calm = ("спокой", "хватило", "хватит", "выдерж", "по силам", "давит",
            "управляют", "отстаю", "остаются", "позволить", "беспокоит")
    assert any(w in text for w in calm), \
        f"в вопросах нет ничего про спокойствие с деньгами: {text[:200]!r}"
    ok("6. FR-002 вопросы про спокойствие с деньгами")


def check_money_result_has_no_judgement() -> None:
    """7. FR-003: результат по деньгам — без единого оценочного слова."""
    # Три захода: середина, все крайние «совсем не про меня», все крайние «всегда».
    runs = {
        "середина": FULL["state_finwell"],
        "низ": FULL["state_finwell"].replace("setAnswer(k, 3)", "setAnswer(k, 1)"),
        "верх": FULL["state_finwell"].replace("setAnswer(k, 3)", "setAnswer(k, 5)"),
    }
    for name, js in runs.items():
        got = page("state_finwell",
                   "  startCard();\n  " + js + "\n  await finish();\n"
                   "  OUT.result = screen();")
        text = visible(got["result"]).lower()
        for w in BAD_WORDS:
            assert w not in text, \
                f"в результате по деньгам ({name}) оценочное слово «{w}»: " \
                f"{text[:300]!r}"
        assert not LATIN.search(visible(got["result"])), \
            f"в результате по деньгам ({name}) латиница — это название шкалы"
    ok("7. FR-003 ни одного оценочного слова ни при каких ответах")

    # Что человек видит вместо оценки: свои ответы и сдвиг.
    got = page("state_finwell", seed("{shock: 1, leftover: 1}") +
               "  startCard();\n  " + FULL["state_finwell"] +
               "\n  await finish();\n  OUT.result = screen();")
    text = visible(got["result"]).lower()
    assert "прошл" in text, "в результате нет сдвига с прошлым разом"
    ok("7. FR-003 вместо оценки — свои ответы и сдвиг")

    # Первый раз — честно: сравнивать не с чем.
    got = full_run("state_finwell")
    text = visible(got["result"]).lower()
    assert "точка отсчёта" in text or "не с чем" in text, \
        "первый замер не сказал честно, что сравнить не с чем"
    ok("7. первая точка названа честно")


def check_money_hard_to_look() -> None:
    """8. FR-005: «тяжело смотреть» закрывает карточку без записи."""
    got = page("state_finwell", """
  startCard();
  setAnswer('shock', 2);
  OUT.hasOut = screen().indexOf('data-hard') >= 0;
  tap('data-hard', 'data-hard').click();
  OUT.closed = screen();
""")
    assert got["hasOut"], \
        "на экране вопроса нет тихого выхода «тяжело смотреть» (FR-005)"
    assert not got["rows"], \
        f"выход записал точку в базу: {got['rows']}"
    text = visible(got["closed"]).lower()
    assert "закрыл" in text or "не записал" in text or "оставил" in text, \
        f"после выхода человек не понял, что произошло: {text[:200]!r}"
    ok("8. FR-005 выход есть, записи нет")

    # Не настаиваем и не приглашаем второй раз: ни «попробуй», ни «вернись».
    for w in ("попробуй", "вернись", "загляни", "стоит всё-таки", "давай",
              "всё же", "советую"):
        assert w not in text, \
            f"после «тяжело смотреть» страница настаивает: «{w}»"
    ok("8. FR-005 ни настаивания, ни повторного приглашения")

    # И ни одного оценочного слова в самом прощании.
    for w in BAD_WORDS:
        assert w not in text, f"в прощании оценочное слово «{w}»"
    ok("8. FR-005 прощание без оценок")


# ==========================================================================
# 4. Здоровье: FR-009 — screen and refer, never treat
# ==========================================================================
def health_run(js_answers: str, seed_js: str = "") -> Dict:
    return page("state_health", seed_js + "  startCard();\n  " + js_answers +
                "\n  await finish();\n  OUT.result = screen();")


# Пять порогов из плана. Каждый обязан поднимать сигнал сам по себе.
HEALTH_ALERTS = {
    "общее здоровье «плохое»": "setAnswer('health', 1);",
    "душевное состояние «плохое»": "setAnswer('mental', 1);",
    "боль 7 из 10": "setAnswer('pain', 7);",
    "утомление «очень сильное»": "setAnswer('fatigue', 1);",
}

CALM = ("['health','qol','physical','mental','social','roles','activities',"
        "'emotional','fatigue'].forEach(function (k) { setAnswer(k, 4); }); "
        "setAnswer('pain', 2);")


def check_health_alert_fires() -> None:
    """9. FR-009: каждый порог поднимает сигнал, спокойные ответы — нет."""
    got = health_run(CALM)
    assert got["rows"][0]["scores"]["promis"]["alert"] is False, \
        "спокойные ответы подняли сигнал — тогда он ничего не значит"
    text = visible(got["result"]).lower()
    assert "врач" not in text, \
        "при спокойных ответах страница всё равно отправляет к врачу"
    ok("9. спокойные ответы сигнал не поднимают")

    for name, js in HEALTH_ALERTS.items():
        got = health_run(CALM + " " + js)
        assert got["rows"][0]["scores"]["promis"]["alert"] is True, \
            f"порог «{name}» сигнал не поднял"
        text = visible(got["result"]).lower()
        assert "врач" in text, \
            f"порог «{name}»: страница не сказала про врача"
    ok(f"9. FR-009 все {len(HEALTH_ALERTS)} порогов поднимают сигнал и ведут к врачу")

    # Ровно по границе: 6 не срабатывает, 7 срабатывает. Иначе порог можно
    # незаметно увести на 9, и проверка это пропустит.
    got = health_run(CALM + " setAnswer('pain', 6);")
    assert got["rows"][0]["scores"]["promis"]["alert"] is False, \
        "боль 6 из 10 подняла сигнал — порог съехал вниз"
    got = health_run(CALM + " setAnswer('pain', 7);")
    assert got["rows"][0]["scores"]["promis"]["alert"] is True, \
        "боль 7 из 10 не подняла сигнал — порог съехал вверх"
    ok("9. порог боли стоит ровно на 7")

    # Резкое падение общего здоровья против прошлого раза — тоже сигнал.
    got = health_run(CALM + " setAnswer('health', 2);",
                     seed_js=seed("{health: 4, pain: 2}"))
    assert got["rows"][0]["scores"]["promis"]["alert"] is True, \
        "здоровье упало на две ступени, а сигнала нет"
    got = health_run(CALM + " setAnswer('health', 3);",
                     seed_js=seed("{health: 4, pain: 2}"))
    assert got["rows"][0]["scores"]["promis"]["alert"] is False, \
        "здоровье сдвинулось на одну ступень, а сигнал уже поднялся"
    ok("9. падение на две ступени — сигнал, на одну — нет")


def check_health_refers_without_interpreting() -> None:
    """10. FR-009: направляет к врачу и НИЧЕГО не толкует."""
    for name, js in HEALTH_ALERTS.items():
        got = health_run(CALM + " " + js)
        text = visible(got["result"]).lower()
        for w in INTERPRET:
            assert w not in text, \
                f"порог «{name}»: страница толкует, а не направляет — «{w}»"
        assert "не диагноз" in text or "скрин" in text, \
            f"порог «{name}»: не сказано, что это скрин, а не диагноз"
        for w in HEALTH_BAD:
            assert w not in text, \
                f"порог «{name}»: страница добавила оценку от себя — «{w}»"
    ok("10. FR-009 направляет и не толкует: screen and refer, never treat")

    # T-баллов нет ни на одном экране: они считаются по американским нормам.
    for name in ("intro", "first", "result"):
        text = visible(all_screens("state_health")[name])
        assert not LATIN.search(text), \
            f"экран «{name}» здоровья: латиница — это аббревиатура шкалы"
        low = text.lower()
        for w in ("т-балл", "t-балл", "процентил", "норм", "популяц"):
            assert w not in low, f"экран «{name}» здоровья: слово «{w}»"
    ok("10. T-баллов и норм нет ни на одном экране")


# ==========================================================================
# 5. Семья: FR-013
# ==========================================================================
def check_faces_says_not_stage() -> None:
    """11. FR-013: в описании честно сказано, что меряется не стадия."""
    got = page("pair_faces", "  OUT.intro = screen(); OUT.gives = WHAT_IT_GIVES;")
    text = visible(got["intro"]).lower()
    assert "стади" in text, \
        "на входе ни слова про стадию — а человек ждёт от опросника про семью " \
        "именно её (FR-013)"
    assert re.search(r"не\s+стади", text), \
        f"не сказано, что стадию опросник НЕ меряет: {text[:300]!r}"
    assert "справля" in text, \
        "не сказано, что меряется: справляется ли семья с той стадией, где стоит"
    ok("11. FR-013 на входе честно: не стадия, а справляется ли семья")


def check_faces_one_person_is_not_family() -> None:
    """12. FR-013: прошёл один — говорим про ЕГО ответы, не «про вашу семью»."""
    got = full_run("pair_faces")
    text = visible(got["result"]).lower()
    for w in ("ваша семья", "ваша families", "у вас в семье", "вы вместе",
              "профиль семьи", "ваша сплочён"):
        assert w not in text, \
            f"прошёл один, а результат заявляет про семью: «{w}»"
    assert "ты" in text or "твои" in text or "твоих" in text, \
        f"результат не говорит, что это ответы одного человека: {text[:300]!r}"
    ok("12. FR-013 прошёл один — результат про его ответы")

    # Оба прошли — можно говорить про двоих.
    got = full_run("pair_faces", search="?u=tg_777&bo=1")
    text = visible(got["result"]).lower()
    assert "двоих" in text or "оба" in text or "вдвоём" in text, \
        f"оба прошли, а результат этого не заметил: {text[:300]!r}"
    ok("12. FR-013 прошли оба — результат говорит про двоих")

    # Флага нет — молчание, а не «нет»: страница не заявляет «второй не прошёл».
    got = full_run("pair_faces")
    text = visible(got["result"]).lower()
    assert "не прошёл" not in text and "не прошла" not in text, \
        "страница утверждает про второго то, чего не знает"
    ok("12. про второго ничего не утверждается, пока не сказано")


def check_faces_six_scales_apart() -> None:
    """13. Шесть шкал семьи идут по отдельности, без свода."""
    got = full_run("pair_faces")
    faces = got["rows"][0]["scores"]["faces"]
    assert len(faces) == 6, f"шкал в записи {len(faces)}, ждали шесть: {faces}"
    for name, v in faces.items():
        assert 1 <= v <= 5, f"шкала «{name}» вне границ 1..5: {v}"
    ok("13. шесть шкал в записи, каждая в своих границах")

    # Каждая шкала собрана из СВОИХ семи пунктов: 42 = 6 × 7.
    got = page("pair_faces", "  OUT.scales = FACES_SCALES;")
    scales = got["scales"]
    seen = []
    for name, items in scales.items():
        assert len(items) == 7, f"у шкалы «{name}» {len(items)} пунктов, ждали 7"
        seen += items
    assert sorted(seen) == list(range(1, 43)), \
        f"пункты по шкалам разложены неверно: {sorted(seen)}"
    ok("13. 42 пункта разложены по шести шкалам по семь, без пересечений")


# ==========================================================================
# 6. «Рабочий перевод» и ни слова про нормы — у всех трёх
# ==========================================================================
def check_draft_translation_marked() -> None:
    """14. FR-004, FR-008, FR-013: метка «рабочий перевод», норм нет."""
    for block in PAGES:
        screens = all_screens(block)
        intro = visible(screens["intro"]).lower()
        assert "рабочий перевод" in intro, \
            f"{PAGES[block]}: на входе нет метки «рабочий перевод»"
        # Метка стоит в ДВУХ местах, и оба обязательны: рядом с честной длиной —
        # чтобы человек видел её до входа, и в плашке — чтобы понимал, почему
        # норм не будет. Убрать одну молча нельзя.
        got = page(block, "  OUT.size = CARD_SIZE; OUT.weather = WEATHER_TEXT;")
        assert "рабочий перевод" in got["size"].lower(), \
            f"{PAGES[block]}: метки нет рядом с честной длиной: {got['size']!r}"
        assert "рабочий перевод" in got["weather"].lower(), \
            f"{PAGES[block]}: метки нет в плашке: {got['weather']!r}"
        for name, h in screens.items():
            low = visible(h).lower()
            for w in ("норм", "процентил", "т-балл", "t-балл", "популяц",
                      "у людей", "в пределах"):
                assert w not in low, \
                    f"{PAGES[block]}, экран «{name}»: слово про нормы «{w}»"
    ok("14. у всех трёх метка «рабочий перевод», ни слова про нормы")


def check_no_latin_no_authors() -> None:
    """15. Человек не видит ни аббревиатуры, ни фамилии автора."""
    authors = ["Олсон", "Olson", "CFPB", "PROMIS", "FACES", "Ворошилина"]
    for block in PAGES:
        for name, h in all_screens(block).items():
            text = visible(h)
            m = LATIN.search(text)
            assert not m, \
                f"{PAGES[block]}, экран «{name}»: латиница «{m.group(0)}»"
            for a in authors:
                assert a.lower() not in text.lower(), \
                    f"{PAGES[block]}, экран «{name}»: имя инструмента «{a}»"
    ok("15. ни латиницы, ни имён инструментов на экранах")


# ==========================================================================
# 7. Одна точка за период, замок, только этот заход
# ==========================================================================
# ПЕРЕПИСАНО 10.08.2026, спека 023 «Замер сохраняется».
#
# Было: два прохода за период дают ОДНУ строку — повтор правит существующую.
# Отменено. Ключ страниц умеет только вставлять: правка меняла ноль строк, и
# повтор оборачивался красной строкой «Не удалось сохранить». Теперь каждый заход
# кладёт свою строку, а «одна точка за период» держится на чтении: бот берёт из
# периода запись с самым поздним `completed_at`.
def check_one_point_per_period() -> None:
    """16. Повтор за период сохраняется, а в линии остаётся последняя запись."""
    R = bot_reader()
    for block in PAGES:
        got = page(block, "  startCard();\n  " + FULL[block] +
                   "\n  await finish();\n"
                   "  await new Promise(function (r) { setTimeout(r, 5); });\n"
                   "  startCard();\n  " + FULL[block] +
                   "\n  await finish();\n"
                   "  OUT.n = globalThis.DB.rows.length;\n"
                   "  OUT.fail = globalThis.__APP.innerHTML.indexOf('Не удалось') >= 0;")
        assert got["n"] == 2, \
            f"{PAGES[block]}: два прохода дали {got['n']} строк — повтор не записался"
        assert not got["fail"], \
            f"{PAGES[block]}: повтор за период показал «Не удалось сохранить»"

        # Строк две, точка обязана остаться одна — и это ПОСЛЕДНЯЯ.
        rows = got["rows"]
        days = R["CARD_DAYS"].get(block)
        assert days, f"у карточки «{block}» нет срока — период не посчитать"
        keys = {R["period_key"](r["completed_at"], days) for r in rows}
        assert len(keys) == 1, \
            f"{PAGES[block]}: два прохода подряд попали в разные периоды: {keys}"
        best = R["latest_per_period"](rows, days)
        assert len(best) == 1, \
            f"{PAGES[block]}: за период осталось {len(best)} точек, а не одна"
        latest = max(r["completed_at"] for r in rows)
        assert best[0]["completed_at"] == latest, \
            f"{PAGES[block]}: в линии не последняя запись периода"
    ok("16. повтор сохраняется, а в линии за период остаётся последняя запись")

    # Номер записи считается от периода: полгода и год делятся, а не сливаются.
    got = page("state_finwell", """
  OUT.h1 = periodKey('2026-02-10T00:00:00.000Z');
  OUT.h2 = periodKey('2026-08-10T00:00:00.000Z');
  OUT.h3 = periodKey('2026-03-01T00:00:00.000Z');
""")
    assert got["h1"] != got["h2"], \
        f"две половины года попали в один период: {got['h1']} и {got['h2']}"
    assert got["h1"] == got["h3"], \
        f"февраль и март попали в разные полугодия: {got['h1']} и {got['h3']}"
    ok("16. полугодие считается полугодием, а не кварталом")

    got = page("pair_faces", """
  OUT.y1 = periodKey('2026-01-05T00:00:00.000Z');
  OUT.y2 = periodKey('2026-11-05T00:00:00.000Z');
  OUT.y3 = periodKey('2027-01-05T00:00:00.000Z');
""")
    assert got["y1"] == got["y2"], \
        f"январь и ноябрь одного года — разные периоды: {got['y1']}, {got['y2']}"
    assert got["y1"] != got["y3"], \
        f"два разных года слились в один период: {got['y1']}, {got['y3']}"
    ok("16. год считается годом")

    # Номер записи больше не считается ни от кого: каждый заход берёт свежий
    # случайный. Раньше он считался от человека и периода, и на повторе база
    # отвечала «номер занят» — отсюда и брался молчаливый отказ.
    for block in PAGES:
        got = page(block, """
  OUT.a = newRecordId();
  OUT.b = newRecordId();
""")
        assert got["a"] != got["b"], \
            f"{PAGES[block]}: два захода подряд получили один номер записи"
        parts = got["a"].split("-")
        assert [len(x) for x in parts] == [8, 4, 4, 4, 12] and parts[2][0] == "4", \
            f"{PAGES[block]}: номер записи не случайный uuid — «{got['a']}»"
        src = inline_script(PAGES[block])
        back = [n for n in ("recordIdFor", "idKeyString", "fnvBytes", "patchById",
                            "patchWindow", "countRows", "periodWindow",
                            "decideWrite", "postThenPatch") if n in src]
        assert not back, \
            f"{PAGES[block]}: вернулась механика правки по номеру: {back}"
    ok("16. номер записи свежий на каждый заход, механика правки не вернулась")


def check_submit_lock() -> None:
    """17. Замок на отправке: пять нажатий подряд дают одну запись."""
    for block in PAGES:
        got = page(block, "  startCard();\n  " + FULL[block] + """
  var p = [];
  for (var i = 0; i < 5; i++) p.push(finish());
  await Promise.all(p);
  OUT.n = globalThis.DB.rows.length;
  OUT.posts = globalThis.CALLS.filter(function (c) { return c.method === 'POST'; }).length;
""")
        assert got["n"] == 1, \
            f"{PAGES[block]}: пять нажатий дали {got['n']} записей"
        # Одной строки в базе недостаточно: без замка все пять нажатий уходят в
        # сеть, и одну строку спасает только детерминированный номер записи.
        # Замок обязан отбить лишние ДО запроса.
        assert got["posts"] == 1, \
            f"{PAGES[block]}: замок не держит — в сеть ушло {got['posts']} записей"
    ok("17. пять нажатий подряд — одна запись и один запрос")


def check_only_this_session() -> None:
    """18. В базу уходят только ответы ЭТОГО захода (011, FR-004)."""
    for block in PAGES:
        got = page(block, seed("{shock: 5, health: 1, i1: 5}") +
                   "  startCard();\n  " + FULL[block] +
                   "\n  await finish();\n  OUT.answers = globalThis.DB.rows[0].answers;")
        raw = json.dumps(got["answers"], ensure_ascii=False)
        assert "прошлый-период" not in raw, \
            f"{PAGES[block]}: прошлый заход уехал в запись"
    ok("18. прошлое из памяти телефона в запись не уезжает")

    # Пропущенный пункт в запись не попадает вовсе: пустое поле не данные.
    got = page("state_finwell", """
  startCard();
  setAnswer('shock', 3);
  setAnswer('leftover', 2);
  await finish();
  OUT.keys = Object.keys(globalThis.DB.rows[0].scores.finwell);
""")
    assert sorted(got["keys"]) == ["leftover", "shock"], \
        f"в запись попали неотвеченные пункты: {got['keys']}"
    ok("18. неотвеченный пункт в запись не попадает")


def check_nothing_answered_no_record() -> None:
    """19. Ни одного ответа — записи нет вовсе. Пустая точка хуже отсутствия."""
    for block in PAGES:
        got = page(block, "  startCard();\n  await finish();\n  OUT.done = screen();")
        assert not got["rows"], \
            f"{PAGES[block]}: пустой заход создал запись {got['rows']}"
        text = visible(got["done"]).lower()
        assert "нечего" in text or "не записал" in text, \
            f"{PAGES[block]}: пустой заход не сказал, что записывать нечего"
    ok("19. пустой заход записи не создаёт")


# ==========================================================================
# 8. Кнопка назад, подтверждение выхода, «за период уже есть»
# ==========================================================================
def check_back_and_exit() -> None:
    """20. Кнопка назад и подтверждение выхода — как на других страницах."""
    for block in PAGES:
        got = page(block, """
  startCard();
  OUT.first = STEPS[0].key;
  var second = nextKey(state.key, answers, flags);
  state.key = second; renderStep();
  OUT.back = goBackStep();
  OUT.now = state.key;
  OUT.tg = globalThis.TG;
""", telegram=True)
        assert got["back"] is True, f"{PAGES[block]}: назад со второго шага не работает"
        assert got["now"] == got["first"], \
            f"{PAGES[block]}: назад привёл не на первый вопрос: {got['now']}"
        assert got["tg"]["back"] >= 1 and got["tg"]["shown"] >= 1, \
            f"{PAGES[block]}: штатная кнопка назад не подключена"
    ok("20. назад возвращает на прошлый вопрос, кнопка штатная")

    # Подтверждение выхода: встаёт после первого касания, а не при открытии.
    for block in PAGES:
        got = page(block, """
  OUT.before = globalThis.TG.closing;
  globalThis.DOC_LISTENERS.forEach(function (p) { if (p[0] === 'click') p[1](); });
  OUT.after = globalThis.TG.closing;
""", telegram=True)
        assert got["before"] == 0, \
            f"{PAGES[block]}: подтверждение выхода включилось до первого касания"
        assert got["after"] == 1, \
            f"{PAGES[block]}: начал заполнять — подтверждения выхода нет"
    ok("20. подтверждение выхода встаёт после первого касания")

    # Снятие подтверждения на результате живьём не проверить: обёртка ищет
    # функции в `window`, а в node объявления функций туда не попадают. Значит
    # проверяем сам код — так же, как это делает `zamery_v_miniappe.py`.
    def code_only(src: str) -> str:
        src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
        return re.sub(r"(?m)^\s*//.*$", " ", src)

    for block, rel in PAGES.items():
        code = code_only(inline_script(rel))
        assert "disableClosingConfirmation" in code, \
            f"{rel}: подтверждение не снимается после результата"
        assert "renderResult" in code and "renderClosed" in code, \
            f"{rel}: обёртка снятия не знает про экраны результата и выхода"
        assert re.search(r"history\.length\s*>\s*1", code), \
            f"{rel}: кнопка назад показывается без проверки, есть ли куда вернуться"
        body = re.sub(r"<script.*?</script>", " ", html(rel), flags=re.S)
        for bad in ("←", "⬅", "&larr;"):
            assert bad not in body, f"{rel}: своя стрелка назад {bad}"
    ok("20. подтверждение снимается на результате, своей стрелки назад нет")


def check_says_already_filled() -> None:
    """21. «Замер за этот период уже есть» говорится ДО начала."""
    for block in PAGES:
        got = page(block, "  OUT.intro = screen();",
                   search=SEARCH[block] + "&d=1")
        text = visible(got["intro"]).lower()
        assert "уже есть" in text, \
            f"{PAGES[block]}: про пройденный период не сказано до начала"
        # ПЕРЕПИСАНО 10.08.2026 (023, FR-005). Было: «вторая точка не появится».
        # Так и не происходило: повтор просто не записывался. Теперь честно —
        # запишем ещё раз, а в линии останется последняя запись.
        assert "запишем ещё раз" in text or "запишем еще раз" in text, \
            f"{PAGES[block]}: не сказано, что повтор запишется ещё раз"
        assert "последняя запись" in text, \
            f"{PAGES[block]}: не сказано, что в линии останется последняя запись"
        assert "не появится" not in text and "заменят" not in text, \
            f"{PAGES[block]}: обещано то, чего не происходит — замена прежних"
        got = page(block, "  OUT.intro = screen();")
        assert "уже есть" not in visible(got["intro"]).lower(), \
            f"{PAGES[block]}: говорит «уже есть» тому, кто не проходил"
    ok("21. «за этот период уже есть» — до начала и только когда правда")


def check_no_send_data() -> None:
    """22. sendData на страницах с записью не зовётся: он убивает запись."""
    for block, rel in PAGES.items():
        src = inline_script(rel)
        assert ".sendData(" not in src, \
            f"{rel}: зовёт sendData — он закроет мини-апп и оборвёт запись"
    ok("22. ни одна страница не зовёт sendData")


def check_catalog_knows_three_cards() -> None:
    """23. Каталог знает три карточки и ведёт на их страницы."""
    urls = bot_urls()
    src = inline_script("kak-ty/app.html")
    got = _node(stubs("?u=tg_777") + src.split("// ---- Telegram ----")[0] + r"""
const OUT = { reg: REGISTRY.map(function (r) {
  return { key: r.key, section: r.section, area: r.area, days: r.days,
           containers: r.containers, url: r.url || null, size: r.size,
           group: r.group };
}) };
console.log('RESULT<' + JSON.stringify(OUT) + '>RESULT');
""")
    reg = {r["key"]: r for r in got["reg"]}
    want = {"state_finwell": ("rare", "Деньги", 180),
            "state_health": ("rare", "Тело", 180),
            "pair_faces": ("year", "Семья", 365)}
    for key, (section, area, days) in want.items():
        assert key in reg, f"каталог не знает карточки «{key}»"
        r = reg[key]
        assert r["section"] == section, f"«{key}»: раздел {r['section']}"
        assert r["area"] == area, f"«{key}»: область {r['area']}"
        assert r["days"] == days, f"«{key}»: срок {r['days']}"
        assert r["containers"] == [area], f"«{key}»: метки {r['containers']}"
        assert r["url"], f"«{key}» в каталоге без адреса — станет разговором"
        assert r["url"] == urls["CARD_MINI_APP_URL"][key], \
            f"«{key}»: адрес в каталоге и в боте разный"
        n = COUNT[key]
        assert str(n) in r["size"] or {10: "десять", 42: "сорок два"}[n] in r["size"], \
            f"«{key}»: честной длины в каталоге нет: {r['size']!r}"
    assert reg["pair_faces"]["group"] == "Пара", \
        "карточка семьи не в парной группе — она покажется человеку без пары"
    ok("23. каталог знает три карточки, ведёт на их страницы, длина честная")


if __name__ == "__main__":
    raise SystemExit(run([
        check_block_and_instrument,
        check_record_keys,
        check_no_totals,
        check_item_count,
        check_one_question_per_screen,
        check_money_asks_calm_not_sums,
        check_money_result_has_no_judgement,
        check_money_hard_to_look,
        check_health_alert_fires,
        check_health_refers_without_interpreting,
        check_faces_says_not_stage,
        check_faces_one_person_is_not_family,
        check_faces_six_scales_apart,
        check_draft_translation_marked,
        check_no_latin_no_authors,
        check_one_point_per_period,
        check_submit_lock,
        check_only_this_session,
        check_nothing_answered_no_record,
        check_back_and_exit,
        check_says_already_filled,
        check_no_send_data,
        check_catalog_knows_three_cards,
    ]))
