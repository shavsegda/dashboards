# -*- coding: utf-8 -*-
"""Проверки шести замеров, переехавших из разговора в мини-апп (спека 011).

Что переехало: Движение · Люди рядом · Восемь фактов · Что ещё стоит знать ·
Деньги за месяц · Области жизни.

Почему проверок так много. Переезд не должен порвать линию: старые записи,
собранные разговором, и новые, собранные экраном, обязаны читаться как одна
история. Значит блок, подпись инструмента и каждый ключ поля сверяются с
`bot.py` буквально, а не по памяти — расхождение имён панели не заметят, они
просто покажут пустоту.

Как проверяем. Страница исполняется в node целиком: браузер, Телеграм и база
подменены заглушками. Заглушка базы — не «принимает всё», а маленькая таблица с
первичным ключом: повторная запись по занятому номеру отвечает 409, правка по
окну возвращает исправленные строки. Поэтому «одна точка за период» проверяется
поведением, а не чтением кода.

Что проверками НЕ берётся и смотрится глазами на телефоне: как выглядят экраны,
как ведёт себя настоящая кнопка назад в настоящем клиенте и не стыдно ли читать
результат вслух.

Запуск:  python3 checks/zamery_v_miniappe.py
"""

import ast
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
# `bot_reader` — читающая часть бота: правило «одна точка за период» с
# 10.08.2026 живёт там, а не на странице (спека 023, FR-002).
from lib import (BOT, _node, block_paths, bot, bot_reader, dig, html,
                 inline_script, ok, run, visible)

# ---- Шесть страниц. Ключ — блок в базе, значение — файл ----
PAGES: Dict[str, str] = {
    "state_move": "state-move/app.html",
    "state_people": "state-people/app.html",
    "state_facts": "state-facts/app.html",
    "state_note": "state-note/app.html",
    "state_money": "state-money/app.html",
    "state_domains": "state-domains/app.html",
}

# Верхние ключи записи. Прибиты руками: посчитать их из самого файла значит
# согласиться с любым его состоянием, включая «полей не осталось».
TOP_KEYS: Dict[str, List[str]] = {
    "state_move": ["evs", "source"],
    "state_people": ["lonely", "source"],
    "state_facts": ["facts", "signs", "source"],
    "state_note": ["note", "source"],
    "state_money": ["money", "source"],
    "state_domains": ["pwi", "source"],
}

# Поля внутри блока инструмента при полном заходе.
INNER_KEYS: Dict[str, Dict[str, List[str]]] = {
    "state_move": {"evs": ["days", "min_day", "min_week"]},
    "state_people": {"lonely": ["items", "total", "met"]},
    "state_facts": {"facts": ["marked", "shown", "work_evenings", "containers"]},
    "state_note": {"note": ["text", "containers"]},
    "state_money": {"money": ["enough", "enough_word", "gap_n", "cushion_n",
                              "debts_n", "shock_text"]},
    "state_domains": {"pwi": [
        "living", "health", "achieve", "relations", "safety", "community",
        "future", "meaning",
        "imp_living", "imp_health", "imp_achieve", "imp_relations",
        "imp_safety", "imp_community", "imp_future", "imp_meaning", "thin"]},
}

# Полный заход: то же, что делает человек, только без тапов. Значения выбраны
# так, чтобы включились и условные вопросы.
FULL: Dict[str, str] = {
    "state_move": "setAnswer('days', 3); setAnswer('min_day', 40);",
    "state_people": ("setAnswer('company', 2); setAnswer('left_out', 1); "
                     "setAnswer('isolated', 3); setAnswer('met', true);"),
    "state_facts": (
        "['warm','tension','kids','work_evenings','met','own_time',"
        "'money_worry','flow'].forEach(function (k) { setAnswer(k, true); });"
        "setAnswer('work_evenings_n', 4);"
        "setAnswer('sign_kids', true); setAnswer('sign_team', true);"
        "setAnswer('sign_meditates', false);"),
    "state_note": "setAnswer('text', 'спина отвалилась и завал в отчётах');",
    "state_money": ("setAnswer('enough', 'yes'); setAnswer('gap', 15000); "
                    "setAnswer('cushion', 3); setAnswer('debts', 0); "
                    "setAnswer('shock', 'полетел холодильник на 40к');"),
    "state_domains": (
        "[['living',7],['health',4],['achieve',8],['relations',9],"
        "['safety',6],['community',5],['future',3],['meaning',7]]"
        ".forEach(function (p) { setAnswer(p[0], p[1]); });"
        "PWI_DOMAINS.forEach(function (d) { setAnswer('imp_' + d.key, 9); });"),
}

# Адрес открытия. У фактов и областей приезжают признаки от бота: без них
# условные вопросы не показываются, и полный заход был бы неполным.
SEARCH: Dict[str, str] = {
    "state_move": "?u=tg_777",
    "state_people": "?u=tg_777",
    "state_facts": "?u=tg_777&p=1",
    "state_note": "?u=tg_777",
    "state_money": "?u=tg_777",
    # Параметра `imp` больше нет (023, FR-007): страница всегда спрашивает и
    # про «устраивает», и про «важно».
    "state_domains": "?u=tg_777",
}


# ==========================================================================
# Заглушки: браузер, Телеграм и база
# ==========================================================================
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
// не поймать — а это ровно тот дефект, из-за которого писалась спека.
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

// Шапка с полосой прогресса лежит вне блока, который пересобирается.
globalThis.__HEADER = {};
var HEADER_IDS = ['progressBar', 'progressFill', 'progressText', 'progressCount'];
HEADER_IDS.forEach(function (id) {
  globalThis.__HEADER[id] = { style: {}, textContent: '', classList: { toggle: function () {} } };
});

globalThis.DOC_LISTENERS = [];
globalThis.document = {
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
// Заглушка не «принимает всё»: занятый номер даёт 409, правка возвращает
// исправленные строки. Только так «одна точка за период» проверяется поведением.
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


TG_STUB = r"""
globalThis.TG = { closing: 0, relaxed: 0, back: 0, shown: 0, closed: 0 };
globalThis.window.Telegram = { WebApp: {
  initData: '',
  initDataUnsafe: {},
  ready: function () {}, expand: function () {},
  close: function () { globalThis.TG.closed++; },
  enableClosingConfirmation: function () { globalThis.TG.closing++; },
  disableClosingConfirmation: function () { globalThis.TG.relaxed++; },
  BackButton: {
    onClick: function (fn) { globalThis.TG.onBack = fn; globalThis.TG.back++; },
    show: function () { globalThis.TG.shown++; },
    hide: function () {}
  }
}};
"""

TAIL = r"""
const OUT = {};
/** Собранная разметка экрана. Человек читает именно её. */
function screen() { return globalThis.__APP.innerHTML; }
/** Нажать элемент собранной разметки по куску его тега. */
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


def seed(a_js: str, marked_js: str = "undefined") -> str:
    """Положить в память телефона замер ПРОШЛОГО периода.

    Ровно так он и поднимается на живом телефоне. Проверки на этом смотрят две
    вещи: что сравнение с прошлым разом работает и что в базу прошлое не уезжает.
    """
    return """
  localStorage.setItem(POINTS_KEY, JSON.stringify([{
    completed_at: '2026-06-01T10:00:00.000Z', periodKey: 'прошлый-период',
    a: %s, marked: %s
  }]));
  POINTS = loadPoints();
  prevSaved = prevPoint(POINTS, periodKey(new Date().toISOString()));
""" % (a_js, marked_js)


# ==========================================================================
# Литералы бота: читаем разбором AST. Импортировать бота нельзя — он тянет сеть.
# ==========================================================================
_WANTED = {
    "MOVE_Q", "MOVE_NORM_MIN", "LONELY_SCALE", "LONELY_ITEMS", "LONELY_MET_Q",
    "FACTS_ITEMS", "FACTS_STREAK_MIN", "SIGN_Q", "NOTE_Q", "MONEY_Q",
    "MONEY_CLOSE_TEXT", "PWI_DOMAINS", "PWI_SAT_Q", "PWI_IMP_Q",
    "LIFE_CONTAINERS",
}


def bot_texts() -> Dict:
    """Вопросы, шкалы и списки бота. Сверяем по ним, а не по памяти."""
    tree = ast.parse(BOT.read_text(encoding="utf-8"))
    picked, found = [], set()
    for node in tree.body:
        name = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
        if name in _WANTED:
            picked.append(node)
            found.add(name)
    missing = _WANTED - found
    assert not missing, f"в bot.py не нашёл: {', '.join(sorted(missing))}"
    ns: Dict = {"Dict": Dict, "List": List, "Optional": Optional,
                "Set": Set, "Tuple": Tuple}
    exec(compile(ast.Module(body=picked, type_ignores=[]), "<bot>", "exec"), ns)
    return ns


def steps_of(block: str, search: Optional[str] = None) -> List[Dict]:
    """Вопросы страницы в том порядке, в каком их видит человек."""
    got = page(block, """
  OUT.steps = visibleSteps({}, flags).map(function (s) {
    return { key: s.key, kind: s.kind, q: s.q, lo: s.lo, hi: s.hi,
             optional: !!s.optional,
             options: (s.options || []).map(function (o) { return o.l; }) };
  });
  OUT.all = STEPS.map(function (s) { return { key: s.key, q: s.q, kind: s.kind }; });
""", search=search)
    return got["steps"]


def all_steps(block: str) -> List[Dict]:
    got = page(block, """
  OUT.all = STEPS.map(function (s) { return { key: s.key, q: s.q, kind: s.kind }; });
""")
    return got["all"]


# ==========================================================================
# 1. Контракт с ботом: блок, подпись инструмента, ключи полей
# ==========================================================================
def check_block_and_instrument() -> None:
    """1. Блок и подпись инструмента — буквально как у бота."""
    meta = bot()["CARD_META"]
    for block in PAGES:
        assert block in meta, f"в CARD_META бота нет карточки «{block}»"
        assert meta[block]["block"] == block, \
            f"«{block}»: у бота карточка пишет в «{meta[block]['block']}»"
        got = page(block, "  OUT.block = BLOCK; OUT.instrument = INSTRUMENT;")
        assert got["block"] == block, f"{PAGES[block]}: блок стал «{got['block']}»"
        # Бот кладёт в instrument сам ключ блока для всего, кроме суточной строки.
        assert got["instrument"] == block, \
            f"{PAGES[block]}: подпись инструмента «{got['instrument']}» вместо «{block}»"
    ok("шесть страниц: блок и подпись инструмента совпадают с ботом")


def check_record_keys() -> None:
    """2. Ключи полей записи — те же, что писал разговор."""
    b = bot()
    for block in PAGES:
        got = full_run(block)
        rows = got["rows"]
        assert len(rows) == 1, f"{PAGES[block]}: строк в базе {len(rows)}"
        row = rows[0]
        assert row["block"] == block, f"{PAGES[block]}: блок записи «{row['block']}»"
        assert row["instrument"] == block, \
            f"{PAGES[block]}: подпись инструмента записи «{row['instrument']}»"
        scores = row["scores"]
        assert sorted(scores) == sorted(TOP_KEYS[block]), \
            f"{PAGES[block]}: верхние ключи записи {sorted(scores)}"
        assert scores.get("source") == "manual", \
            f"{PAGES[block]}: пропала метка источника"
        for inst, fields in INNER_KEYS[block].items():
            assert sorted(scores[inst]) == sorted(fields), \
                f"{PAGES[block]}, «{inst}»: поля стали {sorted(scores[inst])}"
        # Ответы человека читаемой строкой, как у бота: answers.raw.
        assert list(row["answers"]) == ["raw"], \
            f"{PAGES[block]}: в answers лежит {list(row['answers'])}, а не raw"
    ok("шесть страниц: верхние ключи, поля инструмента и answers.raw как у бота")

    # Пути, по которым бот рисует линии, обязаны находиться в записи.
    for block in PAGES:
        want = block_paths(b, block)
        if not want:
            continue
        scores = full_run(block)["rows"][0]["scores"]
        missing = sorted(p for p in want if dig(scores, p) is None)
        assert not missing, f"{PAGES[block]}: бот читает, а записи нет: {missing}"
    ok("все пути линий из bot.py находятся в записи страницы")


def check_questions_from_bot() -> None:
    """3. Вопросы, шкалы и области — буквально из bot.py."""
    t = bot_texts()

    # Движение: два вопроса, и каждый начинается словами бота. Хвост про формат
    # ответа («одна цифра от 0 до 7») на экране не нужен: границы видны глазом.
    st = {s["key"]: s for s in steps_of("state_move")}
    for key, bot_q in t["MOVE_Q"]:
        assert key in st, f"движение: пропал вопрос «{key}»"
        assert bot_q.startswith(st[key]["q"]), \
            f"движение, «{key}»: вопрос разошёлся с ботом:\n  экран: {st[key]['q']}\n  бот:   {bot_q}"
    assert [s["key"] for s in steps_of("state_move")] == [k for k, _q in t["MOVE_Q"]], \
        "движение: порядок вопросов не как у бота"
    ok("движение: оба вопроса и их порядок из MOVE_Q")

    # Люди рядом: три пункта, шкала частоты и факт про живую встречу.
    got = page("state_people", "  OUT.scale = LONELY_SCALE;\n"
                               "  OUT.items = LONELY_ITEMS.map(function (i) { return [i.key, i.q]; });")
    assert got["scale"] == t["LONELY_SCALE"], f"люди рядом: шкала {got['scale']}"
    want = [[k, q] for k, q, _s in t["LONELY_ITEMS"]]
    assert got["items"] == want, f"люди рядом: пункты разошлись: {got['items']}"
    met = {s["key"]: s for s in steps_of("state_people")}["met"]
    assert t["LONELY_MET_Q"].startswith(met["q"]), \
        f"люди рядом: вопрос про живую встречу разошёлся: {met['q']}"
    assert len(met["options"]) == 2, "люди рядом: у факта не два варианта"
    ok("люди рядом: три пункта, шкала частоты и вопрос про живую встречу из бота")

    # Восемь фактов: тексты и ключи один в один, плюс условный вопрос и признаки.
    got = page("state_facts", """
  OUT.items = FACTS_ITEMS.map(function (i) { return [i.key, i.t, i.c, i.cond, i.side]; });
  OUT.streak = FACTS_STREAK_MIN;
  OUT.signs = SIGN_STEPS.map(function (s) { return [s.sign, s.q]; });
""")
    want = [[k, txt, cont, cond, side] for k, txt, cont, cond, side, _tpl in t["FACTS_ITEMS"]]
    assert got["items"] == want, f"восемь фактов: список разошёлся с ботом"
    assert got["streak"] == t["FACTS_STREAK_MIN"], "восемь фактов: порог серии другой"
    for (name, bot_q), (got_name, got_q) in zip(t["SIGN_Q"], got["signs"]):
        assert name == got_name, f"признаки: порядок другой — {got['signs']}"
        assert bot_q.startswith(got_q), \
            f"признак «{name}»: вопрос разошёлся:\n  экран: {got_q}\n  бот:   {bot_q}"
    ok("восемь фактов: пункты, порог серии и три признака из бота")

    # Свободная строка.
    note = steps_of("state_note")[0]
    assert t["NOTE_Q"].startswith(note["q"]), \
        f"свободная строка: вопрос разошёлся: {note['q']}"
    assert note["optional"], "свободную строку нельзя пропустить"
    ok("свободная строка: вопрос из NOTE_Q, пропуск законный")

    # Деньги: пять вопросов, их ключи и порядок.
    st = steps_of("state_money")
    assert [s["key"] for s in st] == [k for k, _q in t["MONEY_Q"]], \
        f"деньги: ключи или порядок разошлись: {[s['key'] for s in st]}"
    for (key, bot_q), s in zip(t["MONEY_Q"], st):
        assert bot_q.startswith(s["q"]), \
            f"деньги, «{key}»: вопрос разошёлся:\n  экран: {s['q']}\n  бот:   {bot_q}"
    got = page("state_money", "  OUT.close = MONEY_CLOSE_TEXT;")
    assert got["close"] == t["MONEY_CLOSE_TEXT"], \
        f"деньги: текст закрытия разошёлся: {got['close']}"
    ok("деньги: пять вопросов, порядок и текст закрытия из бота")

    # Области жизни: шестнадцать вопросов, ключи и порядок из бота.
    #
    # ПЕРЕПИСАНО 10.08.2026. Раньше требовалось, чтобы вопрос страницы буквально
    # совпадал с шаблоном бота `PWI_SAT_Q`. Требование снято решением по ходу
    # 023: шаблон «Насколько тебя устраивает {название}?» ломал согласование на
    # двух областях из восьми — «устраивает дела и достижения», «устраивает
    # близкие отношения». Кривая фраза стоит дороже, чем кажется: человек
    # спотыкается о язык и отвечает про своё, а цифра идёт в расчёт направления.
    # Поэтому вопрос на странице пишется целиком.
    #
    # Что осталось привязанным к боту и проверяется по-прежнему: ключи областей,
    # их порядок, шкала и то, что в каждом заходе спрашивают оба блока. Название
    # области — тоже из бота: переименуешь — потеряешь сопоставимость.
    st = steps_of("state_domains")
    keys = [k for k, _n, _c in t["PWI_DOMAINS"]]
    assert [s["key"] for s in st][:8] == keys, \
        f"области: ключи или порядок разошлись: {[s['key'] for s in st][:8]}"
    assert [s["key"] for s in st][8:] == [f"imp_{k}" for k in keys], \
        f"области: важность спрашивается не про те области: {[s['key'] for s in st][8:]}"
    assert len(st) == 16, \
        f"области: вопросов {len(st)}, а должно быть шестнадцать — 023, FR-006"
    got = page("state_domains", "  OUT.d = PWI_DOMAINS.map(function (d) {"
                                " return [d.key, d.name, d.sat, d.imp]; });")
    for (key, name, _c), (gk, gname, sat, imp) in zip(t["PWI_DOMAINS"], got["d"]):
        assert gk == key and gname == name, \
            f"области: название «{gname}» разошлось с ботом «{name}»"
        # Вопрос свой, но про эту область и про то самое: «устраивает» и «важно».
        assert sat.strip().endswith("?") and imp.strip().endswith("?"), \
            f"области, «{key}»: вопрос не вопрос: {sat} / {imp}"
        assert "важ" in imp.lower(), \
            f"области, «{key}»: второй вопрос не про важность: {imp}"
        assert sat != imp, f"области, «{key}»: оба вопроса одинаковые"
    assert all(s["lo"] == 0 and s["hi"] == 10 for s in st), \
        "области: шкала не от 0 до 10"
    ok("области жизни: 16 вопросов, ключи и названия из бота, шкала 0–10")

    # Метки контейнеров жизни там, где страница их ставит.
    for block in ("state_facts", "state_note"):
        got = page(block, "  OUT.c = LIFE_CONTAINERS;")
        assert got["c"] == list(t["LIFE_CONTAINERS"]), \
            f"{PAGES[block]}: список областей жизни разошёлся с ботом"
    ok("список областей жизни совпадает с ботом на обеих страницах, где он нужен")


# ==========================================================================
# 2. Запись: один замер, только этот заход, одна точка за период
# ==========================================================================
def check_one_card_one_record() -> None:
    """4. Ответ на один замер даёт запись ровно с одним замером."""
    for block in PAGES:
        got = full_run(block)
        rows = got["rows"]
        assert len(rows) == 1, f"{PAGES[block]}: строк {len(rows)}, а не одна"
        posts = [c for c in got["calls"] if c["method"] == "POST"]
        assert len(posts) == 1, f"{PAGES[block]}: запросов на вставку {len(posts)}"
        instruments = [k for k in rows[0]["scores"] if k not in ("source", "signs")]
        assert len(instruments) == 1, \
            f"{PAGES[block]}: в записи замеров {instruments}, а отвечали один"
    ok("шесть страниц: один заход — одна запись с одним замером")


def _setitem_calls(src: str):
    """Все вызовы `localStorage.setItem` с ключом и целым аргументом.

    Разбираем по скобкам, а не построчно: вызов бывает на пять строк, и наивная
    регулярка обрывает его на середине — то есть перестаёт видеть, что пишется.
    """
    out = []
    for m in re.finditer(r"localStorage\.setItem\(", src):
        i = m.end() - 1
        depth, j = 0, i
        while j < len(src):
            if src[j] == "(":
                depth += 1
            elif src[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        arg = src[i + 1:j]
        out.append((arg.split(",")[0].strip(), arg))
    return out


def check_only_this_session() -> None:
    """5. В базу уходит только то, что человек ответил в этом заходе."""
    cases = {
        # Отвечаем ЧАСТЬ вопросов, в памяти лежит полный прошлый заход.
        "state_people": ("{ company: 3, left_out: 3, isolated: 3, met: true }",
                         "setAnswer('company', 1); setAnswer('left_out', 1); "
                         "setAnswer('isolated', 1);",
                         {"lonely": {"items": {"company": 1, "left_out": 1,
                                               "isolated": 1}, "total": 3}}),
        "state_money": ("{ enough: 'no', gap: 99999, cushion: 12, debts: 500000, shock: 'машина' }",
                        "setAnswer('enough', 'yes'); setAnswer('cushion', 2);",
                        {"money": {"enough": True, "enough_word": "хватило",
                                   "cushion_n": 2}}),
        "state_domains": ("{ living: 1, health: 1, achieve: 1, relations: 1, "
                          "safety: 1, community: 1, future: 1, meaning: 1, imp_living: 10 }",
                          "setAnswer('living', 8); setAnswer('health', 5);",
                          {"pwi": {"living": 8, "health": 5, "thin": "health"}}),
    }
    for block, (prior_js, part, want) in cases.items():
        got = page(block, seed(prior_js, "['warm', 'tension', 'kids']") +
                   "  startCard();\n  " + part + "\n  await finish();")
        rows = got["rows"]
        assert len(rows) == 1, f"{PAGES[block]}: строк {len(rows)}"
        scores = rows[0]["scores"]
        for inst, fields in want.items():
            assert scores[inst] == fields, \
                (f"{PAGES[block]}: в запись уехало {scores[inst]},\n"
                 f"    а отвечали только {fields}")
    ok("прошлый заход из памяти телефона в запись не попадает")

    # Признаки тоже только этого захода: не спросили — не пишем.
    got = page("state_facts", """
  startCard();
  setAnswer('met', true);
  await finish();
""", search="?u=tg_777&k=1&tm=1&md=1&p=1")
    scores = got["rows"][0]["scores"]
    assert "signs" not in scores, \
        f"признаки уехали в запись, хотя их не спрашивали: {scores.get('signs')}"
    assert scores["facts"]["marked"] == ["met"], \
        f"в записи отмечено {scores['facts']['marked']}"
    assert scores["facts"]["shown"] == ["met"], \
        f"в записи показано {scores['facts']['shown']}, а отвечали один пункт"
    ok("восемь фактов: в записи только отвеченные пункты и ни одного лишнего признака")

    # Ответы этого захода лежат в СВОЕЙ ячейке-черновике и только там.
    #
    # Правило переписано 07.08.2026, и вот почему. Раньше проверка требовала,
    # чтобы ответы захода не попадали в память телефона ВОВСЕ. Смысл был верный —
    # прошлое не должно уезжать в базу как свежее, — но средство слишком грубое:
    # оно же запрещало сохранять начатый замер. Живой человек ответил на часть
    # вопросов, вышел и потерял всю работу.
    #
    # Теперь запрет точный. В память телефона ответы кладёт только черновик и
    # только в ячейку `DRAFT_KEY`, помеченную своим периодом. Ячейка прошлых
    # точек ответов захода не касается, сборка записи в память телефона не
    # заглядывает совсем — ни в точки, ни в черновик.
    for block in PAGES:
        src = inline_script(PAGES[block])
        assert "var answers = {};" in src, \
            f"{PAGES[block]}: нет отдельного набора ответов этого захода"
        assert "function saveDraft()" in src, \
            f"{PAGES[block]}: начатый замер негде сохранить"
        for key, arg in _setitem_calls(src):
            if "answers" not in arg:
                continue
            assert key == "DRAFT_KEY", \
                f"{PAGES[block]}: ответы захода уезжают в ячейку {key}, а не в черновик"
        i = src.index("function saveDraft()")
        draft = src[i:src.index("\n}", i)]
        assert "POINTS" not in draft, \
            f"{PAGES[block]}: черновик пишется в ячейку прошлых точек"
        i = src.index("function buildScores(")
        body = src[i:src.index("\n}", i)]
        for bad in ("prevSaved", "loadPoints", "POINTS", "loadDraft", "DRAFT_KEY"):
            assert bad not in body, \
                f"{PAGES[block]}: сборка записи заглядывает в память телефона ({bad})"
    ok("ответы захода живут только в черновике, сборка записи их оттуда не берёт")


def check_skip_makes_no_record() -> None:
    """6. Пропуск и отказ не создают записи."""
    # Открыли и вышли, ничего не ответив.
    for block in PAGES:
        got = page(block, "  startCard();\n  await finish();\n  OUT.screen = screen();")
        assert got["rows"] == [], \
            f"{PAGES[block]}: ничего не ответили, а в базу ушла запись"
    ok("шесть страниц: пустой заход не создаёт записи")

    # Свободная строка: «Нечего добавить» — ЭТО ОТВЕТ, и он записывается.
    #
    # Правило перевернули 10.08.2026 (спека 020). До этого пропуск не писал
    # ничего, и живой человек попал в дыру: прошёл недельный замер, нажал
    # «Нечего добавить», а карточка осталась непройденной и ритм дёргал заново.
    # Старое правило «пустая точка хуже отсутствия» верно для линии графика и
    # неверно для факта прохождения. Поэтому строка есть, а цифры в ней нет.
    #
    # Ожидание записи обязательно: без него проверка снимала базу до отправки и
    # проходила по гонке — «записи нет» означало «ещё не успела».
    got = page("state_note", """
  startCard();
  byId('skipStep').click();
  await new Promise(function (r) { setTimeout(r, 20); });
  OUT.screen = screen();
""")
    rows = got["rows"]
    assert len(rows) == 1, \
        f"«Нечего добавить» — ответ, а записи нет или их больше одной: {rows}"
    scores = rows[0].get("scores") or {}
    assert scores.get("nothing_to_add") is True, \
        f"в записи нет признака «нечего добавить»: {scores}"
    # Ни одного числа: рисовать точку в линии нечем, и это главное требование.
    for key, val in scores.items():
        assert not isinstance(val, (int, float)) or isinstance(val, bool), \
            f"в записи «нечего добавить» появилось число ({key}={val}) — оно нарисует точку"
    text = visible(got["screen"])
    assert "записан" in text.lower(), \
        f"экран не сказал, что отметка записана: {text[:200]}"
    assert "Пропустил" not in text, \
        f"экран всё ещё говорит про пропуск, хотя запись есть: {text[:200]}"
    ok("свободная строка: «нечего добавить» записывается без числа и говорит об этом")

    # Деньги: оба тихих выхода закрывают замер и ничего не пишут.
    t = bot_texts()
    for out_id in ("outSkip", "outHard"):
        got = page("state_money", """
  startCard();
  setAnswer('enough', 'no');
  byId('%s').click();
  OUT.screen = screen();
""" % out_id)
        assert got["rows"] == [], f"деньги, «{out_id}»: в базу ушла запись"
        text = visible(got["screen"])
        assert t["MONEY_CLOSE_TEXT"] in text, \
            f"деньги, «{out_id}»: нет текста закрытия из бота"
        # Ни одного повторного приглашения: ни «пройти снова», ни «вернись».
        for bad in ("Пройти снова", "Начать", "Попробуй"):
            assert bad not in text, \
                f"деньги, «{out_id}»: экран снова зовёт проходить — «{bad}»"
    ok("деньги: пропуск и «тяжело смотреть» закрывают замер без записи и без приглашения")

    # Пропущенная область не превращается в ноль: поля просто нет.
    got = page("state_domains", """
  startCard();
  setAnswer('living', 6);
  advance();
  byId('skipStep').click();          // здоровье пропускаем
  setAnswer('achieve', 4);
  await finish();
""")
    pwi = got["rows"][0]["scores"]["pwi"]
    assert "health" not in pwi, f"пропущенная область попала в запись: {pwi}"
    assert pwi["living"] == 6 and pwi["achieve"] == 4, f"в записи {pwi}"
    ok("области жизни: пропущенная область в запись не попадает")


# ПЕРЕПИСАНО 10.08.2026, спека 023 «Замер сохраняется».
#
# Было: вторая отправка за период правит ту же строку — номер записи считался от
# человека, блока и периода. Отменено. Ключ страниц умеет только вставлять:
# правка меняла ноль строк, и человек на повторе видел «Не удалось сохранить», а
# ответы не уходили никуда.
#
# Стало: каждый заход кладёт свою строку со случайным номером, а «одна точка за
# период» держится на ЧТЕНИИ — бот берёт из периода запись с самым поздним
# `completed_at`. Проверка смотрит на оба конца: что записала страница и что из
# этого прочитает бот.
def check_one_point_per_period() -> None:
    """7. Повтор за период сохраняется, а в линии остаётся последняя запись."""
    R = bot_reader()
    for block in PAGES:
        # Второй раз в том же заходе: страница уже знает, что точка есть.
        got = full_run(block, extra="""
  await new Promise(function (r) { setTimeout(r, 5); });
  startCard();
  """ + FULL[block] + """
  await finish();
  OUT.ids = globalThis.DB.rows.map(function (r) { return r.id; });
  OUT.fail = globalThis.__APP.innerHTML.indexOf('Не удалось') >= 0;
""")
        assert len(got["rows"]) == 2, \
            f"{PAGES[block]}: после второй отправки строк {len(got['rows'])}, а не две"
        assert not got["fail"], \
            f"{PAGES[block]}: повтор за период показал «Не удалось сохранить»"
        assert len(set(got["ids"])) == 2, \
            f"{PAGES[block]}: две строки ушли под одним номером: {got['ids']}"
        assert not [c for c in got["calls"] if c["method"] != "POST"], \
            f"{PAGES[block]}: страница ходит в базу не только вставкой"

        # Обе строки в одном периоде, а точка из них одна — последняя.
        days = R["CARD_DAYS"].get(block)
        assert days, f"у карточки «{block}» нет срока — период не посчитать"
        best = R["latest_per_period"](got["rows"], days)
        assert len(best) == 1, \
            f"{PAGES[block]}: за период осталось {len(best)} точек, а не одна"
        latest = max(r["completed_at"] for r in got["rows"])
        assert best[0]["completed_at"] == latest, \
            f"{PAGES[block]}: в линии не последняя запись периода"
    ok("шесть страниц: повтор сохраняется, а в линии остаётся последняя запись")

    # Новый заход после перезагрузки страницы: номер свежий, отказа нет.
    for block in PAGES:
        got = page(block, """
  startCard();
  """ + FULL[block] + """
  await finish();
  await new Promise(function (r) { setTimeout(r, 5); });
  // Забываем всё, что знали: как будто страницу открыли заново.
  knownExisting = false;
  startCard();
  """ + FULL[block] + """
  await finish();
  OUT.ids = globalThis.DB.rows.map(function (r) { return r.id; });
  OUT.posts = globalThis.CALLS.filter(function (c) { return c.method === 'POST'; }).length;
  OUT.bad = globalThis.CALLS.filter(function (c) { return c.method !== 'POST'; }).length;
""")
        assert len(got["rows"]) == 2, \
            f"{PAGES[block]}: новый заход не записался ({len(got['rows'])} строк)"
        assert len(set(got["ids"])) == 2, \
            f"{PAGES[block]}: номер записи повторился: {got['ids']}"
        assert got["posts"] == 2 and got["bad"] == 0, \
            f"{PAGES[block]}: в базу ушло {got['posts']} вставок и {got['bad']} прочих"
    ok("шесть страниц: номер записи свежий на каждый заход, отказа нет")

    # Точку, записанную разговором с ботом, страница не трогает: она чужая.
    for block in PAGES:
        got = page(block, """
  globalThis.DB.rows.push({
    id: 'чужой-номер-от-бота', user_id: 777, block: BLOCK, instrument: BLOCK,
    scores: { source: 'manual' }, answers: { raw: 'из разговора' },
    completed_at: new Date().toISOString()
  });
  startCard();
  """ + FULL[block] + """
  await finish();
""", search=SEARCH[block] + "&d=1")
        old = [r for r in got["rows"] if r["id"] == "чужой-номер-от-бота"]
        assert len(old) == 1, \
            f"{PAGES[block]}: точка из разговора пропала или размножилась"
        assert old[0]["answers"] == {"raw": "из разговора"}, \
            f"{PAGES[block]}: точку из разговора переписали замером"
        assert len(got["rows"]) == 2, \
            f"{PAGES[block]}: рядом с точкой из разговора не появилось новой строки"
    ok("шесть страниц: точка из разговора цела, замер лёг рядом новой строкой")


def check_submit_lock() -> None:
    """8. Пять нажатий подряд дают одну запись."""
    for block in PAGES:
        got = page(block, """
  startCard();
  """ + FULL[block] + """
  await Promise.all([finish(), finish(), finish(), finish(), finish()]);
""")
        posts = [c for c in got["calls"] if c["method"] == "POST"]
        assert len(posts) == 1, f"{PAGES[block]}: вставок {len(posts)}, а не одна"
        assert len(got["rows"]) == 1, f"{PAGES[block]}: строк {len(got['rows'])}"
    ok("шесть страниц: замок держит — пять отправок дают одну запись")


# ==========================================================================
# 3. Текст: ни баллов, ни названий шкал, ни оценок
# ==========================================================================
LATIN = re.compile(r"[A-Za-z]{2,}")

# Фамилии и сокращения, которые нельзя показывать человеку.
AUTHORS = ["ШПАНА", "ШВС", "Осин", "Абабков", "Минздрав", "Леонтьев", "Углановой",
           "Хьюз", "Эдмондсон", "Качиоппо", "ВОЗ", "клинрекоменд"]
AUTHOR_RE = [(a, re.compile(r"(?<![A-Za-zА-Яа-яЁё])" + a + r"(?![A-Za-zА-Яа-яЁё])", re.I))
             for a in AUTHORS]

# Оценочные слова и всё, что говорит про балл и норму. «Много» и «мало» стоят
# рядом с «молодец» не случайно: приятный ярлык запрещён так же, как неприятный.
BAD_WORDS = ["балл", "диапазон", "норм", "мало", "много", "немного", "плохо",
             "низк", "высок", "средн", "запустил", "молодец",
             "в пределах", "у людей", "индекс", "уровень", "сумма", "итого"]

# Две оговорки. Это слова самого бота, перенесённые буквально по FR-002, и ни
# одно из них не оценка: «в среднем» — часть вопроса про минуты, «уровень
# жизни» — название области. Вычитаем их до проверки, чтобы запрет остался
# запретом, а не превратился в исключение на всякий случай.
EXCUSED = ["в среднем", "уровень жизни"]


def scan_text(h: str) -> str:
    """Видимый текст без двух оговорок — то, по чему ищем баллы и оценки."""
    text = visible(h)
    for phrase in EXCUSED:
        text = text.replace(phrase, " ")
    return text


def all_screens(block: str) -> Dict[str, str]:
    """Все экраны страницы: вход, каждый вопрос, результат, пустой заход."""
    got = page(block, """
  OUT.s = {};
  OUT.s['вход'] = screen();
  startCard();
  var guard = 0;
  while (state.screen === 'step' && guard++ < 40) {
    OUT.s['вопрос ' + state.key] = screen();
    var s = stepByKey(state.key);
    if (s.kind === 'scale') setAnswer(s.key, Math.round((s.lo + s.hi) / 2));
    else if (s.kind === 'options') setAnswer(s.key, s.options[0].v);
    else if (s.kind === 'text') setAnswer(s.key, 'спина отвалилась');
    else setAnswer(s.key, 5);
    advance();
  }
  OUT.s['результат'] = screen();
  // Даём отправке дойти до конца: иначе замок ещё занят и пустой заход не
  // дорисуется, а именно его текст нам и нужен.
  await new Promise(function (r) { setTimeout(r, 15); });
  startCard();
  await finish();
  OUT.s['пустой заход'] = screen();
""")
    return got["s"]


def extreme_results(block: str) -> Dict[str, str]:
    """Экран результата на крайних ответах.

    Формулировок у результата несколько, и плохая может лежать в редкой ветке:
    «он пройден» видно только тому, кто много двигался. Поэтому обходим низ и
    верх каждой шкалы, а не только середину.
    """
    got = page(block, """
  OUT.s = {};
  for (const side of ['низ', 'верх']) {
    startCard();
    var guard = 0;
    while (state.screen === 'step' && guard++ < 40) {
      var s = stepByKey(state.key);
      if (s.kind === 'options') {
        setAnswer(s.key, side === 'низ' ? s.options[0].v : s.options[s.options.length - 1].v);
      } else if (s.kind === 'text') {
        setAnswer(s.key, side === 'низ' ? 'нет' : 'полетел холодильник и заболела спина');
      } else {
        setAnswer(s.key, side === 'низ' ? s.lo : s.hi);
      }
      advance();
    }
    await new Promise(function (r) { setTimeout(r, 5); });
    OUT.s['результат, ' + side + ' шкалы'] = screen();
  }
""")
    return got["s"]


def check_no_latin_no_scores() -> None:
    """9. Ни латиницы, ни фамилий, ни баллов, ни оценочных слов на экранах."""
    for block in PAGES:
        parts = dict(all_screens(block))
        parts.update(extreme_results(block))
        for name, h in parts.items():
            text = scan_text(h)
            found = sorted(set(LATIN.findall(text)))
            assert not found, f"{PAGES[block]}, экран «{name}»: латиница {found}"
            hits = [a for a, rx in AUTHOR_RE if rx.search(text)]
            assert not hits, f"{PAGES[block]}, экран «{name}»: фамилии {hits}"
            low = text.lower()
            bad = [w for w in BAD_WORDS if w in low]
            assert not bad, f"{PAGES[block]}, экран «{name}»: {bad} в тексте"
            assert "undefined" not in text and "NaN" not in text, \
                f"{PAGES[block]}, экран «{name}»: экран собрался с дырами"
    ok("шесть страниц: на всех экранах ни латиницы, ни фамилий, ни баллов, ни оценок")

    # Отдельно — экран закрытия по отказу: его в общий обход не заносит.
    got = page("state_money", """
  startCard();
  byId('outHard').click();
  OUT.screen = screen();
""")
    text = scan_text(got["screen"])
    bad = [w for w in BAD_WORDS if w in text.lower()]
    assert not bad, f"деньги, экран закрытия: {bad}"
    ok("деньги: на экране закрытия ни одного оценочного слова")


def check_result_in_words() -> None:
    """10. Результат — слова про его ответы плюс сравнение с прошлым разом."""
    # Первый раз: честная точка отсчёта, без упрёка и без обещаний.
    for block in PAGES:
        text = visible(full_run(block)["result"])
        assert "точка отсчёта" in text, \
            f"{PAGES[block]}: на первом замере нет честной точки отсчёта"
        assert "прошлым разом" in text, \
            f"{PAGES[block]}: на экране результата нет строки «с прошлым разом»"
    ok("шесть страниц: первый замер честно назван точкой отсчёта")

    # Второй раз: сравнение с прошлым разом, и «точки отсчёта» больше нет.
    # Прошлый раз кладём в память как замер прошлого периода — так он и приходит.
    second = {
        "state_move": ("{ days: 3, min_day: 40 }", "undefined",
                       "setAnswer('days', 5); setAnswer('min_day', 40);",
                       "В прошлый раз было 120 минут"),
        "state_people": ("{ company: 1, left_out: 1, isolated: 1, met: true }", "undefined",
                         "setAnswer('company', 3); setAnswer('left_out', 1); "
                         "setAnswer('isolated', 1); setAnswer('met', true);",
                         "общения не хватает — чаще, чем в прошлый раз"),
        "state_money": ("{ enough: 'yes', cushion: 2 }", "undefined",
                        "setAnswer('enough', 'yes'); setAnswer('cushion', 5);",
                        "запас был 2 мес."),
        "state_domains": ("{ living: 4 }", "undefined", "setAnswer('living', 7);",
                          "в прошлый раз 4, сдвиг +3"),
        "state_note": ("{ text: 'спина отвалилась' }", "undefined",
                       "setAnswer('text', 'завал в отчётах');",
                       "спина отвалилась"),
        "state_facts": ("{ met: true, flow: true }", "['met', 'flow']",
                        "setAnswer('met', true); setAnswer('flow', false);",
                        "в этот раз не было"),
    }
    for block, (prior_js, marked_js, again, want) in second.items():
        got = page(block, seed(prior_js, marked_js) + """
  startCard();
  """ + again + """
  await finish();
  OUT.result = screen();
""")
        text = visible(got["result"])
        assert want.lower() in text.lower(), \
            f"{PAGES[block]}: нет сравнения с прошлым разом «{want}».\n  экран: {text[:400]}"
        assert "точка отсчёта" not in text, \
            f"{PAGES[block]}: второй замер всё ещё зовётся точкой отсчёта"
    ok("шесть страниц: на втором замере видно, что сдвинулось")

    # Свои ответы человек видит словами, а не цифрой-суммой.
    text = visible(full_run("state_people")["result"])
    assert "общения не хватает — иногда" in text, \
        f"люди рядом: своего ответа словами не видно: {text[:300]}"
    assert "Живая встреча на этой неделе была" in text, \
        "люди рядом: факт про живую встречу не пересказан"
    text = visible(full_run("state_facts")["result"])
    assert "Отмечено:" in text, "восемь фактов: отмеченное не пересказано"
    ok("свои ответы человек читает словами")


def check_what_it_gives() -> None:
    """11. До входа: что это даст и сколько это займёт."""
    for block in PAGES:
        text = visible(page(block, "  OUT.screen = screen();")["screen"])
        # Честная длина — вопросы или минуты, до начала.
        assert re.search(r"\d+\s*(вопрос|минут|област|цифр|строк)", text) or "строка" in text, \
            f"{PAGES[block]}: на входе не сказано, сколько это займёт: {text[:200]}"
        assert "Покажет" in text or "ляжет рядом" in text, \
            f"{PAGES[block]}: на входе нет строки «что это даст»: {text[:200]}"
    ok("шесть страниц: до входа сказано, что это даст и сколько займёт")

    # Замер за этот период уже есть — говорим это ДО начала, а не после отправки.
    for block in PAGES:
        text = visible(page(block, "  OUT.screen = screen();",
                            search=SEARCH[block] + "&d=1")["screen"])
        assert "уже есть" in text, \
            f"{PAGES[block]}: про уже пройденный замер сказано не на входе"
        # ПЕРЕПИСАНО 10.08.2026 (023, FR-005). Было: «вторая точка не появится».
        # Так и не происходило — повтор просто не записывался. Теперь честно:
        # запишем ещё раз, а в линии останется последняя запись.
        assert "запишем ещё раз" in text, \
            f"{PAGES[block]}: не сказано, что повтор запишется ещё раз"
        assert "в линии останется последняя запись" in text, \
            f"{PAGES[block]}: не сказано, что в линии останется последняя запись"
        assert "не появится" not in text and "заменят" not in text, \
            f"{PAGES[block]}: обещана замена прежних ответов, а её не происходит"
    ok("шесть страниц: про уже пройденный замер сказано до начала")


# ==========================================================================
# 4. Устройство: один вопрос на экран, равные интервалы, условные вопросы
# ==========================================================================
def check_one_question_per_screen() -> None:
    """12. Один вопрос на экран, равные интервалы, ни одной таблицы-сетки."""
    for block in PAGES:
        for name, h in all_screens(block).items():
            if not name.startswith("вопрос"):
                continue
            assert h.count('class="q-text"') == 1, \
                f'{PAGES[block]}, «{name}»: на экране {h.count("q-text")} вопросов'
            assert "<table" not in h, f"{PAGES[block]}, «{name}»: таблица-сетка"
    ok("шесть страниц: на каждом экране один вопрос и ни одной таблицы")

    # Интервалы шкалы равные: ряд делится на равные доли, и делений столько же,
    # сколько значений. Неровный ряд смещает середину, а с ней и ответы.
    got = page("state_domains", """
  OUT.scales = [];
  startCard();
  var guard = 0;
  while (state.screen === 'step' && guard++ < 20) {
    var s = stepByKey(state.key);
    if (s.kind === 'scale') {
      var h = screen();
      var m = /grid-template-columns: repeat\\((\\d+), 1fr\\)/.exec(h);
      OUT.scales.push({ key: s.key, cols: m ? Number(m[1]) : null,
                        cells: (h.match(/class="scale-btn/g) || []).length,
                        want: s.hi - s.lo + 1 });
    }
    setAnswer(s.key, s.lo);
    advance();
  }
""")
    assert got["scales"], "области жизни: ни одной шкалы на экранах"
    for r in got["scales"]:
        assert r["cols"] == r["want"], \
            f"области, «{r['key']}»: ряд поделён на {r['cols']} долей вместо {r['want']}"
        assert r["cells"] == r["want"], \
            f"области, «{r['key']}»: делений {r['cells']} вместо {r['want']}"
    ok("области жизни: интервалы шкалы равные на каждом экране")

    # Горизонтальный ряд там, где пунктов больше семи; варианты словами —
    # вертикально, потому что иначе они не влезают.
    for block in ("state_move", "state_facts", "state_domains"):
        src = inline_script(PAGES[block])
        assert "grid-template-columns: repeat(" in src, \
            f"{PAGES[block]}: шкала перестала быть рядом равных долей"
    ok("шкалы остались горизонтальным рядом равных долей")


def check_conditional_questions() -> None:
    """13. Условный вопрос показывается только тому, кому он адресован."""
    # Детей нет — пункт про детей не показывается. Не спрашивали — показывается:
    # «не спрашивали» ≠ «нет», иначе данные теряются молча.
    keys = lambda s: [x["key"] for x in steps_of("state_facts", search=s)]
    assert "kids" not in keys("?u=tg_777&k=0&p=1"), \
        "детей нет, а пункт про детей показывается"
    assert "kids" in keys("?u=tg_777&k=1&p=1"), "дети есть, а пункта про детей нет"
    assert "kids" in keys("?u=tg_777&p=1"), \
        "про детей не спрашивали, а пункт уже спрятан"
    ok("восемь фактов: пункт про детей по условию, «не спрашивали» показываем")

    # Парная работа: спрятано, только когда бот прямо сказал, что пары нет.
    assert "warm" not in keys("?u=tg_777&p=0"), "пары нет, а пункт про пару показывается"
    assert "tension" not in keys("?u=tg_777&p=0"), "пары нет, а напряжение спрашиваем"
    assert "warm" in keys("?u=tg_777&p=1"), "пара есть, а пункта про пару нет"
    ok("восемь фактов: пункты про пару по условию")

    # Признаки: спрашиваем только те, которых бот ещё не знает.
    assert keys("?u=tg_777&k=1&tm=1&md=1&p=1").count("sign_kids") == 0, \
        "признак спрашивается заново, хотя бот его уже знает"
    st = keys("?u=tg_777&k=1&p=1")
    assert "sign_kids" not in st and "sign_team" in st and "sign_meditates" in st, \
        f"спрашиваются не те признаки: {st}"
    ok("восемь фактов: спрашиваются только неизвестные признаки")

    # Число вечеров — только тому, кто отметил, что работа их забирала.
    got = page("state_facts", """
  OUT.without = visibleSteps({ work_evenings: false }, flags).map(function (s) { return s.key; });
  OUT.with_ = visibleSteps({ work_evenings: true }, flags).map(function (s) { return s.key; });
  OUT.unasked = visibleSteps({}, flags).map(function (s) { return s.key; });
""", search="?u=tg_777&p=1")
    assert "work_evenings_n" not in got["without"], \
        "вечера не забирала работа, а число вечеров всё равно спрашиваем"
    assert "work_evenings_n" not in got["unasked"], \
        "число вечеров спрашиваем до ответа про сам факт"
    assert "work_evenings_n" in got["with_"], \
        "работа забирала вечера, а число вечеров не спросили"
    ok("восемь фактов: число вечеров только тому, кто отметил сам факт")

    # И это доезжает до записи: цифра стоит рядом с отмеченным фактом, не иначе.
    got = page("state_facts", """
  startCard();
  setAnswer('work_evenings', false);
  setAnswer('work_evenings_n', 5);
  await finish();
""", search="?u=tg_777&p=1")
    facts = got["rows"][0]["scores"]["facts"]
    assert "work_evenings" not in facts, \
        f"число вечеров уехало в запись без самого факта: {facts}"
    ok("восемь фактов: число вечеров без отмеченного факта в запись не уходит")

    # ПЕРЕПИСАНО 10.08.2026, спека 023 (FR-006, FR-007). Было: «важность — раз в
    # год, и решает это бот». Отменено. 10.08.2026 решение бота и вопрос человеку
    # разошлись: страница не спросила ни одной важности, а в запись уехали восемь
    # десяток. По разрыву «важно минус устраивает» выбирается область работы —
    # значит выбор шёл по цифрам, которых человек не называл.
    #
    # Стало: шестнадцать вопросов всегда, без вариантов и без флага в адресе.
    imp = [s for s in steps_of("state_domains", search="?u=tg_777")
           if s["key"].startswith("imp_")]
    assert len(imp) == 8, \
        f"важность спрашивается не всегда: вопросов про неё {len(imp)}"
    # Флаг в адресе ничего не меняет: параметра больше нет, и подсунуть его
    # снаружи нельзя — иначе вернулась бы вторая копия правила.
    with_flag = [s for s in steps_of("state_domains", search="?u=tg_777&imp=0")
                 if s["key"].startswith("imp_")]
    assert len(with_flag) == 8, \
        f"флаг в адресе всё ещё убирает вопросы про важность: {len(with_flag)}"
    assert "imp" not in inline_script("state-domains/app.html").split("flags")[0] \
        or "flags.imp" not in inline_script("state-domains/app.html"), \
        "страница снова читает флаг важности из адреса"
    ok("области жизни: важность спрашивается всегда, флаг в адресе не действует")

    # Честная длина одна и та же всегда: шестнадцать вопросов, четыре минуты.
    for search in ("?u=tg_777", "?u=tg_777&imp=0", "?u=tg_777&imp=1"):
        text = visible(page("state_domains", "  OUT.screen = screen();",
                            search=search)["screen"])
        assert "16 вопросов" in text, \
            f"области, адрес «{search}»: обещано не шестнадцать вопросов: {text[:160]}"
        assert "8 вопросов" not in text, \
            f"области, адрес «{search}»: длина всё ещё зависит от флага"
    ok("области жизни: обещанная длина одна и та же — 16 вопросов")


def check_signs_reach_record() -> None:
    """14. Признаки собираются экраном и уезжают полем signs внутри scores."""
    got = page("state_facts", """
  startCard();
  setAnswer('met', true);
  setAnswer('sign_kids', true);
  setAnswer('sign_team', false);
  await finish();
""", search="?u=tg_777&p=1")
    scores = got["rows"][0]["scores"]
    assert "signs" in scores, "признаки не уехали в запись — условные пункты исчезнут"
    assert scores["signs"] == {"kids": True, "team": False}, \
        f"в признаках лежит {scores['signs']}"
    assert "meditates" not in scores["signs"], \
        "признак, которого не спрашивали, уехал в запись"
    ok("восемь фактов: признаки уезжают полем signs, и только отвеченные")

    # Имена признаков — те же, что у бота: иначе он их не прочитает.
    t = bot_texts()
    got = page("state_facts", "  OUT.names = SIGN_STEPS.map(function (s) { return s.sign; });")
    assert got["names"] == [n for n, _q in t["SIGN_Q"]], \
        f"имена признаков разошлись с ботом: {got['names']}"
    ok("имена признаков совпадают с SIGN_Q в bot.py")


def check_back_and_exit() -> None:
    """15. Кнопка назад и подтверждение выхода."""
    def code_only(src: str) -> str:
        src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
        return re.sub(r"(?m)^\s*//.*$", " ", src)

    for block in PAGES:
        code = code_only(inline_script(PAGES[block]))
        assert "BackButton" in code, f"{PAGES[block]}: нет штатной кнопки назад"
        assert re.search(r"history\.length\s*>\s*1", code), \
            f"{PAGES[block]}: кнопка показывается без проверки, есть ли куда вернуться"
        assert "enableClosingConfirmation" in code, \
            f"{PAGES[block]}: нет подтверждения выхода"
        assert "disableClosingConfirmation" in code, \
            f"{PAGES[block]}: подтверждение не снимается после результата"
        assert re.search(r"armed", code), \
            f"{PAGES[block]}: подтверждение включается сразу при открытии"
        body = re.sub(r"<script.*?</script>", " ", html(PAGES[block]), flags=re.S)
        for bad in ("←", "⬅", "&larr;"):
            assert bad not in body, f"{PAGES[block]}: своя стрелка назад {bad}"
    ok("шесть страниц: штатная кнопка назад, своей стрелки нет")

    # Живьём: кнопка привязана, подтверждение выхода включается после первого
    # касания, а не при открытии.
    for block in PAGES:
        got = page(block, """
  OUT.beforeTouch = globalThis.TG.closing;
  OUT.bound = globalThis.TG.back;
  OUT.shown = globalThis.TG.shown;
  globalThis.DOC_LISTENERS.forEach(function (p) { if (p[0] === 'click') p[1](); });
  OUT.afterTouch = globalThis.TG.closing;
""", telegram=True)
        assert got["bound"] == 1 and got["shown"] == 1, \
            f"{PAGES[block]}: кнопка назад привязана {got['bound']} раз, показана {got['shown']}"
        assert got["beforeTouch"] == 0, \
            f"{PAGES[block]}: подтверждение выхода включилось до первого касания"
        assert got["afterTouch"] == 1, \
            f"{PAGES[block]}: после первого касания подтверждения выхода нет"
    ok("шесть страниц: подтверждение выхода включается после первого касания")

    # Внутри замера кнопка назад возвращает на прошлый вопрос, а не закрывает
    # мини-апп: дефект с живого телефона был именно в этом.
    for block in PAGES:
        got = page(block, """
  startCard();
  var first = state.key;
  var s = stepByKey(state.key);
  setAnswer(s.key, s.kind === 'options' ? s.options[0].v : (s.lo === undefined ? 'текст' : s.lo));
  advance();
  OUT.second = state.key;
  globalThis.TG.onBack();
  OUT.afterBack = state.key;
  OUT.first = first;
  OUT.histBack = globalThis.HISTORY_BACK || 0;
""", telegram=True)
        if got["second"] == got["first"]:
            continue                      # у страницы всего один вопрос
        assert got["afterBack"] == got["first"], \
            f"{PAGES[block]}: назад не вернул на прошлый вопрос ({got['afterBack']})"
        assert got["histBack"] == 0, \
            f"{PAGES[block]}: назад посреди замера ушёл из мини-аппа"
    ok("шесть страниц: внутри замера назад возвращает на прошлый вопрос")

    # На первом вопросе — назад в список, а не в пустоту.
    got = page("state_move", """
  startCard();
  globalThis.TG.onBack();
  OUT.histBack = globalThis.HISTORY_BACK || 0;
""", telegram=True)
    assert got["histBack"] == 1, "с первого вопроса назад не ведёт в список"
    ok("с первого вопроса кнопка назад возвращает в список")


def check_taps_work() -> None:
    """16. Экраны живые: замер проходится нажатиями, а не только из кода."""
    got = page("state_move", """
  byId('startBtn').click();
  OUT.q1 = state.key;
  globalThis.__APP.querySelectorAll('[data-v]')[3].click();   // три дня
  OUT.q2 = state.key;
  byId('field').value = '40';
  byId('goStep').click();
  await new Promise(function (r) { setTimeout(r, 10); });
  OUT.screen = screen();
""")
    assert got["q1"] == "days" and got["q2"] == "min_day", \
        f"нажатия не перевели по вопросам: {got['q1']} → {got['q2']}"
    assert len(got["rows"]) == 1, f"после нажатий строк {len(got['rows'])}"
    assert got["rows"][0]["scores"]["evs"] == {"days": 3, "min_day": 40, "min_week": 120}, \
        f"нажатия собрали не то: {got['rows'][0]['scores']['evs']}"
    ok("движение: замер проходится нажатиями и пишет верную запись")

    got = page("state_people", """
  byId('startBtn').click();
  for (var i = 0; i < 4; i++) {
    globalThis.__APP.querySelectorAll('[data-v]')[0].click();
  }
  await new Promise(function (r) { setTimeout(r, 10); });
  OUT.screen = screen();
""")
    assert len(got["rows"]) == 1, f"люди рядом: после нажатий строк {len(got['rows'])}"
    lonely = got["rows"][0]["scores"]["lonely"]
    assert lonely["items"] == {"company": 1, "left_out": 1, "isolated": 1}, \
        f"люди рядом: нажатия собрали {lonely['items']}"
    assert lonely["met"] is True, f"люди рядом: факт про встречу {lonely.get('met')}"
    ok("люди рядом: замер проходится нажатиями и пишет верную запись")


def check_no_send_data() -> None:
    """17. sendData со страниц-замеров не зовётся: он обрывает запись."""
    for block in PAGES:
        src = inline_script(PAGES[block])
        assert ".sendData(" not in src, \
            f"{PAGES[block]}: зовёт sendData — запись в базу не дойдёт"
    ok("шесть страниц: sendData не зовётся ни на одной")


if __name__ == "__main__":
    raise SystemExit(run([
        check_block_and_instrument, check_record_keys, check_questions_from_bot,
        check_one_card_one_record, check_only_this_session,
        check_skip_makes_no_record, check_one_point_per_period,
        check_submit_lock,
        check_no_latin_no_scores, check_result_in_words, check_what_it_gives,
        check_one_question_per_screen, check_conditional_questions,
        check_signs_reach_record, check_back_and_exit, check_taps_work,
        check_no_send_data,
    ]))
