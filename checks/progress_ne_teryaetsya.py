# -*- coding: utf-8 -*-
"""Проверки: начатый замер не пропадает, а провал отправки виден.

Дефект с живого человека, 07.08.2026. Алексей начал «Области жизни» —
шестнадцать вопросов, — ответил на часть, вышел из мини-аппа. Вернулся: страница
встретила его так, будто он не начинал. Ответов нет ни на экране, ни в базе.

Что было не так. Страницы писали в память телефона только прошлые РЕЗУЛЬТАТЫ —
для строки «с прошлым разом». Промежуточные ответы не хранились нигде: у девяти
страниц-карточек хранилища черновика не было вовсе, а у восьми страниц с
несколькими тестами `localStorage.setItem(STORE_KEY, …)` вызывался и не читался
ни одной строкой. Прогресс писался и никогда не восстанавливался.

Второй дефект того же корня. На восьми страницах с несколькими тестами результат
уезжал в память телефона и в облако, а черновик стирался ДО ответа сервера.
Поэтому потерянная запись выглядела сделанной: в списке стояло «последний замер
сегодня», а единственная копия ответов была уже удалена. Правило из
«мини-аппы-правила.md»: отметка «отправлено» — только после ответа сервера.

Что проверяется здесь:

1. Прогресс пишется после КАЖДОГО ответа, а не в конце.
2. При возврате человек видит, что продолжает, и видит, как начать заново.
   Восстановление явное: страница не бросает в середину сама.
3. Открывается первый вопрос, до которого человек не дошёл.
4. Черновик чужого периода не восстанавливается: начал недельный замер на
   прошлой неделе — на этой это новый замер, а не продолжение.
5. Срок жизни черновика считается от периода замера, а не одним числом на всех.
6. После успешной отправки черновик пуст.
7. Провал отправки виден, ответы целы, повтор возможен, и ничего не помечено
   отправленным.
8. Ключи записи и её сборка не изменились ни на одной странице. Проверка
   жёсткая: она защищает данные людей, уже лежащие в базе.
9. Восстановленное из черновика не превращает прошлые замеры в свежие
   (FR-004 спеки 011 остаётся в силе).

Как проверяем. Страница исполняется в node целиком, браузер, Телеграм и база
подменены заглушками — те же, что в `zamery_v_miniappe.py`. Возврат человека
моделируется двумя прогонами: первый оставляет содержимое памяти телефона,
второй стартует с ним. Это ровно то, что происходит на телефоне.

Что проверками НЕ берётся и смотрится глазами на телефоне: как выглядит строка
про продолжение, не читается ли она упрёком и живо ли ведёт себя настоящая
кнопка назад в настоящем клиенте.

Запуск:  python3 checks/progress_ne_teryaetsya.py
"""

import json
import re
from typing import Dict, List, Optional

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
from lib import _node, inline_script, ok, run, visible
from zamery_v_miniappe import TAIL, stubs

# ==========================================================================
# Страницы. Три семейства: у них разное устройство и разный путь человека.
# ==========================================================================

# Девять страниц-карточек: один замер, один вопрос на экран.
SINGLE: Dict[str, str] = {
    "state-move/app.html": "?u=tg_777&k=1&tm=1&md=1",
    "state-people/app.html": "?u=tg_777",
    "state-facts/app.html": "?u=tg_777&p=1",
    "state-note/app.html": "?u=tg_777",
    "state-money/app.html": "?u=tg_777",
    "state-domains/app.html": "?u=tg_777&imp=1",
    "state-finwell/app.html": "?u=tg_777",
    "state-health/app.html": "?u=tg_777",
    "pair-faces/app.html": "?u=tg_777&bo=1",
}

# Восемь страниц с несколькими тестами: список тестов и вход в любой из них.
MULTI: List[str] = [
    "state-week/app4.html",
    "state-month/app3.html",
    "state-quarter/app3.html",
    "state-clinical/app.html",
    "state-year/app.html",
    "state-team/app.html",
    "state-needs/app.html",
    "selfhood/app.html",
]

# Суточная страница: одна форма на один экран, без вопросов по одному.
DAY = "state-day/app.html"

# Свободная строка. Вопрос всего один, и «ответил на часть» тут невозможно:
# любой ответ заканчивает замер. Зато терять есть что — набранный текст. Поэтому
# у неё свои проверки, по набору в поле, а не по переходу между вопросами.
TEXT_ONLY = "state-note/app.html"

ALL_PAGES = list(SINGLE) + MULTI + [DAY]
STEPPED = [p for p in SINGLE if p != TEXT_ONLY]

# Ритм каждой страницы в днях. Прибит здесь руками сознательно: если взять его
# из самой страницы, проверка согласится с любым значением, включая «одно число
# на всех». Источник — реестр каталога `kak-ty/app.html` и `STATE_BLOCKS_META`
# бота.
RHYTHM: Dict[str, int] = {
    "state-day/app.html": 1,
    "state-week/app4.html": 7,
    "state-move/app.html": 7,
    "state-people/app.html": 7,
    "state-facts/app.html": 7,
    "state-note/app.html": 7,
    "state-month/app3.html": 30,
    "state-money/app.html": 30,
    "state-clinical/app.html": 30,
    "state-quarter/app3.html": 91,
    "state-domains/app.html": 91,
    "state-needs/app.html": 91,
    "state-team/app.html": 91,
    "state-finwell/app.html": 180,
    "state-health/app.html": 180,
    "selfhood/app.html": 180,
    "state-year/app.html": 365,
    "pair-faces/app.html": 365,
}

# ==========================================================================
# Заглушки поверх общих: посев памяти телефона, отказ базы, живой ряд шкалы
# ==========================================================================

# База не отвечает. Не «ответила отказом на одну запись», а именно не приняла:
# так выглядит и упавшая сеть, и ошибка сервера.
FAIL_FETCH = r"""
globalThis.__FAIL = true;
/** База ожила. Нужно, чтобы проверить повтор отправки тем же путём, каким его
 *  делает человек: не удалось — нажал ещё раз — записалось. */
globalThis.__ALIVE = function () { globalThis.__FAIL = false; };
(function () {
  var live = globalThis.fetch;
  globalThis.fetch = async function (url, opts) {
    if (!globalThis.__FAIL) return live(url, opts);
    globalThis.CALLS.push({ url: String(url), method: (opts && opts.method) || 'GET',
                            body: opts && opts.body ? JSON.parse(opts.body) : null });
    return { ok: false, status: 500, json: async function () { return []; } };
  };
})();
"""

# У кнопки шкалы должен быть родитель: суточная страница по нему перекрашивает
# соседей в ряду. Без этого страница падает на первом же тапе.
ROW_PARENT = r"""
(function () {
  var orig = globalThis.__APP.querySelectorAll.bind(globalThis.__APP);
  globalThis.__APP.querySelectorAll = function (sel) {
    var out = orig(sel);
    out.forEach(function (el) {
      if (!el.parentNode) el.parentNode = { querySelectorAll: function () { return out; } };
    });
    return out;
  };
})();
"""

# Общий хвост: что забираем с каждого прогона. Память телефона — целиком, чтобы
# видеть и ключи, и содержимое; тела запросов — чтобы смотреть на запись, а не
# на код.
CAPTURE = r"""
  OUT.ls = JSON.parse(JSON.stringify(globalThis.localStorage._s));
  OUT.pushed = globalThis.CALLS.filter(function (c) { return c.method === 'POST'; })
                              .map(function (c) { return c.body; });
  OUT.patched = globalThis.CALLS.filter(function (c) { return c.method === 'PATCH'; })
                                .map(function (c) { return c.body; });
  OUT.screen = globalThis.__APP.innerHTML;
"""

# Помощники, доступные внутри любого прогона.
HELPERS = r"""
/** Значение, которое человек выбрал бы на этом вопросе. Середина шкалы. */
function stepValue(s) {
  if (s.kind === 'scale') return Math.round((s.lo + s.hi) / 2);
  if (s.kind === 'options') return s.options[0].v;
  if (s.kind === 'text') return 'что-то важное';
  return (s.lo === undefined ? 1 : s.lo) + 1;
}

/** Пройти n вопросов страницы-карточки ровно тем путём, каким идёт человек:
 *  ответ — переход — отрисовка. */
async function answerFirstSingle(n) {
  startCard();
  for (var i = 0; i < n; i++) {
    if (state.screen !== 'step') break;
    var s = stepByKey(state.key);
    setAnswer(s.key, stepValue(s));
    advance();
    await new Promise(function (r) { setTimeout(r, 0); });
  }
  await new Promise(function (r) { setTimeout(r, 20); });
}

/** Ответить на часть и остановиться, не дойдя до конца. Сколько именно — зависит
 *  от страницы: у короткой карточки вопросов всего два. */
async function answerPartialSingle() {
  var total = visibleSteps({}, flags).length;
  var n = Math.max(1, Math.min(2, total - 1));
  await answerFirstSingle(n);
  return n;
}

/** Пройти всё до конца, как человек, который дошёл до отправки. */
async function answerAllSingle() { await answerFirstSingle(200); }

/** Набрать текст в поле, но НЕ нажать «Дальше». Ровно так теряется свободная
 *  строка: человек написал и вышел. */
function typeInto(text) {
  var f = globalThis.document.getElementById('field');
  if (!f) throw new Error('нет поля ввода');
  f.value = String(text);
  f.handlers.forEach(function (fn) { fn({}); });
}

/** Часть пунктов первого теста страницы с несколькими тестами. */
async function answerFirstMulti(n) {
  var t = TESTS[0];
  startTest(t.key);
  if (state.screen === 'filter') answerFilter(true);
  for (var i = 0; i < n && i < t.items.length; i++) {
    var sc = t.items[i].scale || t.scale;
    answer(sc[0].v);
    await new Promise(function (r) { setTimeout(r, 0); });
  }
  await new Promise(function (r) { setTimeout(r, 20); });
}

async function answerPartialMulti() {
  var n = Math.max(1, Math.min(3, TESTS[0].items.length - 1));
  await answerFirstMulti(n);
  return n;
}

/** Первый тест целиком — до отправки. */
async function answerAllMulti() {
  await answerFirstMulti(TESTS[0].items.length);
  await new Promise(function (r) { setTimeout(r, 40); });
}

/** Тап по кнопке суточной шкалы. */
function tapScale(name, v) {
  var els = globalThis.__APP.querySelectorAll('[data-scale]').filter(function (e) {
    return e.getAttribute('data-scale') === name && e.getAttribute('data-v') === String(v);
  });
  if (!els.length) throw new Error('нет кнопки шкалы ' + name + '=' + v);
  els[0].click();
}
"""


def page(rel: str, js: str, search: Optional[str] = None,
         ls: Optional[Dict] = None, fail: bool = False) -> Dict:
    """Исполнить страницу целиком и вернуть то, что собрал переданный кусок JS."""
    code = stubs(search if search is not None else SINGLE.get(rel, "?u=tg_777"),
                 True)
    if ls:
        code += "\nObject.assign(globalThis.localStorage._s, %s);\n" % \
            json.dumps({k: str(v) for k, v in ls.items()}, ensure_ascii=False)
    if fail:
        code += FAIL_FETCH
    code += ROW_PARENT + HELPERS + inline_script(rel) + TAIL % {"js": js + CAPTURE}
    return _node(code)


# Один частичный заход. Возвращает и память телефона, и сколько ответов дано.
PARTIAL_SINGLE = "  OUT.n = await answerPartialSingle();\n"
PARTIAL_MULTI = "  OUT.n = await answerPartialMulti();\n"
PARTIAL_DAY = "  tapScale('tonus', 6);\n  OUT.n = 1;\n"
PARTIAL_TEXT = "  startCard();\n  typeInto('спина отвалилась и завал в отчётах');\n  OUT.n = 0;\n"


def partial(rel: str, extra: str = "") -> Dict:
    """Человек ответил на часть и вышел."""
    if rel == DAY:
        js = PARTIAL_DAY
    elif rel == TEXT_ONLY:
        js = PARTIAL_TEXT
    elif rel in SINGLE:
        js = PARTIAL_SINGLE
    else:
        js = PARTIAL_MULTI
    return page(rel, js + extra)


def draft_key_of(rel: str) -> str:
    """Как называется ячейка черновика этой страницы."""
    probe = "  OUT.k = STORE_KEY;" if rel in MULTI else "  OUT.k = DRAFT_KEY;"
    return page(rel, probe)["k"]


# ==========================================================================
# 1. Прогресс пишется после каждого ответа
# ==========================================================================

def check_draft_saved_after_each_answer() -> None:
    """1. Черновик появляется с первого ответа, а не в конце замера."""
    for rel in STEPPED:
        got = page(rel, """
  await answerFirstSingle(1);
  OUT.afterOne = JSON.parse(JSON.stringify(globalThis.localStorage._s));
  OUT.draftKey = DRAFT_KEY;
""")
        raw = got["afterOne"].get(got["draftKey"])
        assert raw, f"{rel}: после первого ответа черновика в памяти телефона нет"
        d = json.loads(raw)
        assert len(d.get("a") or {}) == 1, \
            f"{rel}: в черновике {len(d.get('a') or {})} ответов вместо одного"
    ok("восемь страниц-карточек: черновик встаёт с первого ответа")

    for rel in STEPPED:
        got = partial(rel, "  OUT.draftKey = DRAFT_KEY;")
        d = json.loads(got["ls"][got["draftKey"]])
        assert len(d.get("a") or {}) == got["n"], \
            f"{rel}: ответов {got['n']}, а в черновике {len(d.get('a') or {})}"
        assert got["pushed"] == [], f"{rel}: незаконченный замер уехал в базу"
    ok("черновик растёт с каждым ответом, а в базу до конца ничего не уходит")

    got = partial(TEXT_ONLY, "  OUT.draftKey = DRAFT_KEY;")
    d = json.loads(got["ls"][got["draftKey"]])
    assert "спина отвалилась" in json.dumps(d, ensure_ascii=False), \
        f"{TEXT_ONLY}: набранный текст не попал в черновик"
    assert got["pushed"] == [], f"{TEXT_ONLY}: недописанная строка уехала в базу"
    ok("свободная строка: набранное сохраняется до нажатия «Дальше»")

    for rel in MULTI:
        got = page(rel, """
  await answerFirstMulti(1);
  OUT.one = JSON.parse(JSON.stringify(globalThis.localStorage._s));
  OUT.storeKey = STORE_KEY;
""")
        raw = got["one"].get(got["storeKey"])
        assert raw, f"{rel}: после первого ответа черновика в памяти нет"
        assert len(json.loads(raw).get("answers") or {}) == 1, f"{rel}: черновик не тот"
    ok("восемь страниц с тестами: черновик встаёт с первого ответа")

    got = page(DAY, """
  tapScale('tonus', 6);
  OUT.afterOne = JSON.parse(JSON.stringify(globalThis.localStorage._s));
  tapScale('mood', 7);
  OUT.draftKey = DRAFT_KEY;
""", search="?u=tg_777")
    assert got["afterOne"].get(got["draftKey"]), \
        f"{DAY}: после первого тапа по шкале черновика нет"
    d = json.loads(got["ls"][got["draftKey"]])
    assert (d.get("form") or {}).get("tonus") == 6, f"{DAY}: тонус не попал в черновик"
    assert (d.get("form") or {}).get("mood") == 7, f"{DAY}: настроение не попало"
    ok("суточная страница: черновик встаёт с первого тапа")


# ==========================================================================
# 2 и 3. Возврат: видно, что продолжаешь; открыт первый непройденный вопрос
# ==========================================================================

def check_return_is_visible_and_explicit() -> None:
    """2. Вернулся — видно, что продолжаешь, и видно, как начать заново.

    Требуем три вещи, а не одну. Подписи кнопок недостаточно: человек должен
    прочитать, ЧТО именно продолжает и сколько уже сделал, — иначе середина
    замера выглядит чужими ответами. И «начать заново» должно быть настоящей
    кнопкой, а не словом в тексте.
    """
    for rel in SINGLE:
        first = partial(rel)
        got = page(rel, """
  OUT.screenName = state.screen;
  OUT.firstScreen = globalThis.__APP.innerHTML;
  // Подпись кнопки заглушка кладёт в `value`: у кнопки это её текст.
  OUT.resumeLabel = (globalThis.document.getElementById('resumeBtn') || {}).value || '';
  OUT.startLabel = (globalThis.document.getElementById('startBtn') || {}).value || '';
""", ls=first["ls"])
        text = visible(got["firstScreen"])
        low = text.lower()
        assert re.search(r"\d+\s+из\s+\d+", text), \
            f"{rel}: на первом экране не сказано, сколько уже сделано"
        assert "продолж" in low or "отправ" in low, \
            f"{rel}: не сказано, что можно продолжить"
        assert got["resumeLabel"], f"{rel}: кнопки «Продолжить» нет"
        rl = got["resumeLabel"].lower()
        assert "продолж" in rl or "отправ" in rl, \
            f"{rel}: кнопка продолжения подписана «{got['resumeLabel']}»"
        assert "заново" in got["startLabel"].lower(), \
            f"{rel}: начать заново нечем, кнопка подписана «{got['startLabel']}»"
        # Восстановление явное: сама страница в середину замера не бросает.
        assert got["screenName"] == "intro", \
            f"{rel}: страница открылась сразу на «{got['screenName']}», без согласия человека"
    ok("девять страниц-карточек: возврат объяснён и обе кнопки на месте")

    for rel in MULTI:
        first = partial(rel)
        got = page(rel, """
  OUT.screenName = state.screen;
  OUT.firstScreen = globalThis.__APP.innerHTML;
""", ls=first["ls"])
        html_text = got["firstScreen"]
        text = visible(html_text)
        low = text.lower()
        assert re.search(r"\d+\s+из\s+\d+", text), \
            f"{rel}: в списке не сказано, сколько уже отмечено"
        assert "продолж" in low or "отправ" in low, \
            f"{rel}: в списке не сказано, что можно продолжить"
        for fn, word in (("resumeTest", "продолж|отправ"), ("dropProgress", "заново")):
            m = re.search(r'onclick="%s\(\)"[^>]*>([^<]*)<' % fn, html_text)
            assert m, f"{rel}: в списке нет кнопки {fn}()"
            assert re.search(word, m.group(1).lower()), \
                f"{rel}: кнопка {fn}() подписана «{m.group(1).strip()}»"
        assert got["screenName"] == "hub", \
            f"{rel}: страница открылась сразу на «{got['screenName']}»"
    ok("восемь страниц с тестами: возврат объяснён и обе кнопки на месте")

    # Суточная — одна форма, вопросов по одному нет. «Продолжаешь» там значит
    # «поля уже заполнены»; сказать это и дать сброс всё равно обязаны.
    first = partial(DAY)
    got = page(DAY, """
  OUT.form = { tonus: form.tonus };
  OUT.firstScreen = globalThis.__APP.innerHTML;
  OUT.dropLabel = (globalThis.document.getElementById('dropDraftBtn') || {}).value || '';
""", search="?u=tg_777", ls=first["ls"])
    assert got["form"]["tonus"] == 6, f"{DAY}: черновик не подставился в форму"
    assert "черновик" in visible(got["firstScreen"]).lower(), \
        f"{DAY}: человеку не сказано, что это черновик"
    assert "заново" in got["dropLabel"].lower(), \
        f"{DAY}: начать заново нечем, кнопка подписана «{got['dropLabel']}»"
    ok("суточная страница: черновик подставлен, назван вслух и сбрасывается кнопкой")


def check_return_opens_first_unanswered() -> None:
    """3. Продолжаем с того вопроса, до которого человек не дошёл."""
    for rel in STEPPED:
        first = partial(rel, """
  OUT.order = visibleSteps({}, flags).map(function (s) { return s.key; });
""")
        n, order = first["n"], first["order"]
        got = page(rel, """
  byId('resumeBtn').click();
  await new Promise(function (r) { setTimeout(r, 20); });
  OUT.key = state.key;
  OUT.screenName = state.screen;
  OUT.answers = Object.keys(answers);
""", ls=first["ls"])
        assert len(got["answers"]) == n, \
            f"{rel}: после «Продолжить» ответов {len(got['answers'])}, а было {n}"
        assert got["screenName"] == "step", f"{rel}: «Продолжить» не открыло вопрос"
        assert got["key"] == order[n], \
            f"{rel}: открылся «{got['key']}» вместо первого непройденного «{order[n]}»"
    ok("восемь страниц-карточек: открыт первый непройденный вопрос")

    # Свободная строка: продолжаем на том же вопросе, и набранное уже в поле.
    first = partial(TEXT_ONLY)
    got = page(TEXT_ONLY, """
  byId('resumeBtn').click();
  await new Promise(function (r) { setTimeout(r, 20); });
  OUT.screenName = state.screen;
  OUT.field = (globalThis.document.getElementById('field') || {}).value || '';
""", ls=first["ls"])
    assert got["screenName"] == "step", f"{TEXT_ONLY}: «Продолжить» не открыло вопрос"
    assert "спина отвалилась" in got["field"], \
        f"{TEXT_ONLY}: набранный текст не вернулся в поле"
    ok("свободная строка: набранное возвращается в поле")

    for rel in MULTI:
        first = partial(rel)
        n = first["n"]
        got = page(rel, """
  resumeTest();
  await new Promise(function (r) { setTimeout(r, 20); });
  OUT.idx = state.idx;
  OUT.screenName = state.screen;
  OUT.answers = Object.keys(state.answers);
""", ls=first["ls"])
        assert len(got["answers"]) == n, \
            f"{rel}: после «Продолжить» ответов {len(got['answers'])}, а было {n}"
        assert got["screenName"] == "test", f"{rel}: «Продолжить» не открыло вопрос"
        assert got["idx"] == n, \
            f"{rel}: открылся пункт {got['idx']} вместо первого непройденного {n}"
    ok("восемь страниц с тестами: открыт первый непройденный пункт")


def check_start_over_wipes_draft() -> None:
    """3a. «Начать заново» стирает черновик, а не прячет его."""
    for rel in SINGLE:
        first = partial(rel)
        got = page(rel, """
  byId('startBtn').click();
  await new Promise(function (r) { setTimeout(r, 20); });
  OUT.answers = Object.keys(answers);
  OUT.draftKey = DRAFT_KEY;
""", ls=first["ls"])
        assert got["answers"] == [], \
            f"{rel}: «Начать заново» оставило ответы {got['answers']}"
        assert not got["ls"].get(got["draftKey"]), \
            f"{rel}: «Начать заново» не стёрло черновик"
    for rel in MULTI:
        first = partial(rel)
        got = page(rel, """
  dropProgress();
  await new Promise(function (r) { setTimeout(r, 20); });
  OUT.storeKey = STORE_KEY;
  OUT.screenName = state.screen;
""", ls=first["ls"])
        assert not got["ls"].get(got["storeKey"]), \
            f"{rel}: «Начать заново» не стёрло черновик"
        assert got["screenName"] == "hub", f"{rel}: после сброса человек не в списке"
    first = partial(DAY)
    got = page(DAY, """
  byId('dropDraftBtn').click();
  await new Promise(function (r) { setTimeout(r, 20); });
  OUT.form = { tonus: form.tonus };
  OUT.draftKey = DRAFT_KEY;
""", search="?u=tg_777", ls=first["ls"])
    assert got["form"]["tonus"] is None, f"{DAY}: «Начать заново» оставило тонус"
    assert not got["ls"].get(got["draftKey"]), f"{DAY}: черновик не стёрт"
    ok("«Начать заново» стирает черновик на всех восемнадцати страницах")


# ==========================================================================
# 4 и 5. Черновик принадлежит своему периоду и живёт по сроку этого периода
# ==========================================================================

def _spoil(ls: Dict, key: str, field: str, value: str) -> Dict:
    out = dict(ls)
    d = json.loads(out[key])
    d[field] = value
    out[key] = json.dumps(d, ensure_ascii=False)
    return out


def check_foreign_period_not_restored() -> None:
    """4. Черновик чужого периода не восстанавливается."""
    for rel in SINGLE:
        first = partial(rel, "  OUT.draftKey = DRAFT_KEY;")
        spoiled = _spoil(first["ls"], first["draftKey"], "periodKey", "чужой-период")
        got = page(rel, """
  OUT.firstScreen = globalThis.__APP.innerHTML;
  OUT.hasResume = !!globalThis.document.getElementById('resumeBtn');
  OUT.loaded = loadDraft();
  startCard();
  OUT.answers = Object.keys(answers);
""", ls=spoiled)
        assert got["loaded"] is None, f"{rel}: чужой период признан годным"
        assert not got["hasResume"], \
            f"{rel}: черновик прошлого периода предложен как продолжение"
        assert "продолж" not in visible(got["firstScreen"]).lower(), \
            f"{rel}: страница обещает продолжить чужой период"
        assert got["answers"] == [], f"{rel}: чужой период подтянулся в ответы"
    for rel in MULTI:
        first = partial(rel, "  OUT.storeKey = STORE_KEY;")
        spoiled = _spoil(first["ls"], first["storeKey"], "periodKey", "чужой-период")
        got = page(rel, """
  OUT.firstScreen = globalThis.__APP.innerHTML;
  OUT.loaded = loadProgress();
""", ls=spoiled)
        assert got["loaded"] is None, \
            f"{rel}: черновик прошлого периода признан годным"
        assert "продолж" not in visible(got["firstScreen"]).lower(), \
            f"{rel}: список обещает продолжить чужой период"
    first = partial(DAY, "  OUT.draftKey = DRAFT_KEY;")
    spoiled = _spoil(first["ls"], first["draftKey"], "dayKey", "1999-01-01")
    got = page(DAY, """
  OUT.form = { tonus: form.tonus };
  OUT.firstScreen = globalThis.__APP.innerHTML;
""", search="?u=tg_777", ls=spoiled)
    assert got["form"]["tonus"] is None, f"{DAY}: черновик чужих суток подставился"
    assert "черновик" not in visible(got["firstScreen"]).lower(), \
        f"{DAY}: страница говорит про черновик чужих суток"
    ok("черновик чужого периода не восстанавливается ни на одной странице")


def check_stale_draft_expires() -> None:
    """4a. Просроченный черновик не восстанавливается даже в своём периоде."""
    for rel in list(SINGLE) + MULTI:
        first = partial(rel, "  OUT.k = %s;" %
                        ("STORE_KEY" if rel in MULTI else "DRAFT_KEY"))
        # Тот же период, но черновик пролежал заведомо дольше любого срока.
        spoiled = _spoil(first["ls"], first["k"], "savedAt", "2020-01-01T00:00:00.000Z")
        probe = "  OUT.loaded = loadProgress();" if rel in MULTI \
            else "  OUT.loaded = loadDraft();"
        got = page(rel, probe, ls=spoiled)
        assert got["loaded"] is None, f"{rel}: черновик 2020 года признан годным"
    ok("просроченный черновик не поднимается")


def check_ttl_comes_from_rhythm() -> None:
    """5. Срок жизни черновика считается от ритма замера, а не одним числом."""
    seen = {}
    for rel in ALL_PAGES:
        got = page(rel, "  OUT.ttl = draftTtlDays();\n  OUT.days = PERIOD_DAYS;")
        assert got["days"] == RHYTHM[rel], \
            f"{rel}: ритм страницы {got['days']} дн. вместо {RHYTHM[rel]}"
        assert got["ttl"] >= 1, f"{rel}: срок черновика {got['ttl']}"
        seen[rel] = got["ttl"]
    assert seen[DAY] < seen["state-move/app.html"] < seen["state-money/app.html"] \
        < seen["state-domains/app.html"] < seen["state-finwell/app.html"] \
        < seen["pair-faces/app.html"], \
        f"сроки не растут вместе с периодом: {seen}"
    assert len(set(seen.values())) >= 5, \
        f"сроков всего {len(set(seen.values()))} — похоже на одно число на всех"
    ok("срок черновика растёт вместе с периодом замера")


# ==========================================================================
# 6. После успешной отправки черновик пуст
# ==========================================================================

def check_draft_cleared_after_send() -> None:
    """6. Замер отправлен — черновик пуст, следующий заход с чистого листа."""
    for rel in SINGLE:
        got = page(rel, """
  await answerAllSingle();
  OUT.sync = state.sync;
  OUT.draftKey = DRAFT_KEY;
""")
        assert got["sync"] == "ok", f"{rel}: замер не отправился, sync={got['sync']}"
        assert len(got["pushed"]) == 1, f"{rel}: записей {len(got['pushed'])}"
        assert not got["ls"].get(got["draftKey"]), \
            f"{rel}: после отправки черновик остался в памяти телефона"
    for rel in MULTI:
        got = page(rel, """
  await answerAllMulti();
  OUT.sync = state.sync;
  OUT.storeKey = STORE_KEY;
""")
        assert got["sync"] == "ok", f"{rel}: замер не отправился, sync={got['sync']}"
        assert not got["ls"].get(got["storeKey"]), \
            f"{rel}: после отправки черновик остался в памяти телефона"
    got = page(DAY, """
  tapScale('tonus', 6);
  tapScale('mood', 7);
  await submit();
  await new Promise(function (r) { setTimeout(r, 20); });
  OUT.draftKey = DRAFT_KEY;
""", search="?u=tg_777")
    assert len(got["pushed"]) == 1, f"{DAY}: записей {len(got['pushed'])}"
    assert not got["ls"].get(got["draftKey"]), \
        f"{DAY}: после отправки черновик остался"
    ok("после успешной отправки черновик пуст на всех восемнадцати страницах")

    # И на следующем заходе никто не обещает продолжение.
    for rel in [TEXT_ONLY, "state-domains/app.html", "state-week/app4.html"]:
        js = "  await answerAllMulti();" if rel in MULTI else "  await answerAllSingle();"
        first = page(rel, js)
        got = page(rel, "  OUT.firstScreen = globalThis.__APP.innerHTML;", ls=first["ls"])
        assert "продолж" not in visible(got["firstScreen"]).lower(), \
            f"{rel}: после отправки страница обещает продолжить"
    ok("после отправки следующий заход начинается с чистого листа")


# ==========================================================================
# 7. Провал отправки виден, ответы целы, повтор возможен
# ==========================================================================

# Слова, которыми страница объявляет дело сделанным. До ответа сервера их быть
# не должно ни в заголовке, ни в подзаголовке.
DONE_WORDS = ("записал", "записан", "записано", "сохранил", "сохранено", "готово")


def _head_and_sub(html_text: str) -> str:
    h = re.search(r"<h1>([\s\S]*?)</h1>", html_text)
    s = re.search(r'<div class="sub">([\s\S]*?)</div>', html_text)
    return visible((h.group(1) if h else "") + " " + (s.group(1) if s else "")).lower()


def check_failed_send_is_visible() -> None:
    """7. База не приняла — человек это видит, и ответы целы."""
    for rel in SINGLE:
        got = page(rel, """
  await answerAllSingle();
  OUT.sync = state.sync;
  OUT.answers = Object.keys(answers).length;
  OUT.draftKey = DRAFT_KEY;
  OUT.retry = (globalThis.document.getElementById('retryBtn') || {}).value || '';
""", fail=True)
        assert got["sync"] == "error", f"{rel}: провал записи не отмечен"
        head = _head_and_sub(got["screen"])
        for w in DONE_WORDS:
            assert w not in head, \
                f"{rel}: запись не ушла, а заголовок говорит «{head.strip()}»"
        text = visible(got["screen"]).lower()
        assert "не удалось" in text or "не ушла" in text or "не записал" in text, \
            f"{rel}: на экране нет ни слова о том, что запись не ушла"
        assert got["retry"], f"{rel}: кнопки «Записать ещё раз» нет"
        assert "ещё раз" in got["retry"].lower(), \
            f"{rel}: кнопка повтора подписана «{got['retry']}»"
        assert got["answers"] > 0, f"{rel}: ответы потерялись вместе с записью"
        assert got["ls"].get(got["draftKey"]), \
            f"{rel}: черновик стёрт, хотя запись не ушла"
    ok("девять страниц-карточек: провал записи виден, ответы и черновик целы")

    for rel in MULTI:
        got = page(rel, """
  await answerAllMulti();
  OUT.sync = state.sync;
  OUT.answers = Object.keys(state.answers).length;
  OUT.storeKey = STORE_KEY;
  OUT.resultKey = RESULT_KEY;
""", fail=True)
        assert got["sync"] == "error", f"{rel}: провал записи не отмечен"
        head = _head_and_sub(got["screen"])
        for w in DONE_WORDS:
            assert w not in head, \
                f"{rel}: запись не ушла, а подзаголовок говорит «{head.strip()}»"
        m = re.search(r'onclick="retryStore\(\'[^\']*\'\)"[^>]*>([^<]*)<', got["screen"])
        assert m, f"{rel}: кнопки «Записать ещё раз» на экране нет"
        assert "ещё раз" in m.group(1).lower(), \
            f"{rel}: кнопка повтора подписана «{m.group(1).strip()}»"
        assert got["answers"] > 0, f"{rel}: ответы потерялись"
        assert got["ls"].get(got["storeKey"]), \
            f"{rel}: черновик стёрт, хотя запись не ушла"
        # Главное: в памяти телефона не должно остаться следа «замер сделан».
        assert not got["ls"].get(got["resultKey"]), \
            f"{rel}: потерянная запись помечена сделанной в памяти телефона"
    ok("восемь страниц с тестами: провал записи не выглядит как успех")

    got = page(DAY, """
  tapScale('tonus', 6);
  tapScale('mood', 7);
  await submit();
  await new Promise(function (r) { setTimeout(r, 20); });
  OUT.draftKey = DRAFT_KEY;
  OUT.lsKey = LS_KEY;
  OUT.form = { tonus: form.tonus, mood: form.mood };
  // Строка провала живёт в отдельном элементе, а не в разметке экрана: читаем её
  // там же, где её читает человек.
  OUT.status = (globalThis.document.getElementById('status') || {}).textContent || '';
  OUT.btn = (globalThis.document.getElementById('submitBtn') || {}).disabled;
""", search="?u=tg_777", fail=True)
    assert got["form"]["tonus"] == 6, f"{DAY}: ответы потерялись"
    assert got["ls"].get(got["draftKey"]), f"{DAY}: черновик стёрт, хотя запись не ушла"
    assert not got["ls"].get(got["lsKey"]), \
        f"{DAY}: провал записи помечен как отправленный замер"
    low = got["status"].lower()
    assert "ещё раз" in low or "попробуй" in low, \
        f"{DAY}: человеку не сказано, что делать. Строка: «{got['status']}»"
    assert got["btn"] is not True, f"{DAY}: кнопка осталась заблокированной, повторить нечем"
    assert "записал" not in visible(got["screen"]).lower(), \
        f"{DAY}: запись не ушла, а экран говорит «Записал»"
    ok("суточная страница: провал записи виден, ответы целы")


def check_failure_survives_leaving() -> None:
    """7a. Запись не ушла, человек вышел — вернулся и может отправить."""
    for rel in list(SINGLE) + MULTI:
        js = "  await answerAllMulti();" if rel in MULTI else "  await answerAllSingle();"
        first = page(rel, js, fail=True)
        got = page(rel, """
  OUT.firstScreen = globalThis.__APP.innerHTML;
""", ls=first["ls"])
        text = visible(got["firstScreen"]).lower()
        assert "продолж" in text or "отправ" in text, \
            f"{rel}: вернулся после провала — про ответы ни слова"
        assert "заново" in text, f"{rel}: не видно, как начать заново"
    ok("после провала и выхода ответы всё ещё предлагаются человеку")


def check_retry_after_failure_writes() -> None:
    """7b. Повтор после провала записывает и чистит черновик."""
    for rel in SINGLE:
        got = page(rel, """
  await answerAllSingle();
  OUT.firstSync = state.sync;
  globalThis.__ALIVE();
  byId('retryBtn').click();
  await new Promise(function (r) { setTimeout(r, 40); });
  OUT.sync = state.sync;
  OUT.draftKey = DRAFT_KEY;
""", fail=True)
        assert got["firstSync"] == "error", f"{rel}: первая попытка не провалилась"
        assert got["sync"] == "ok", f"{rel}: повтор не записал, sync={got['sync']}"
        assert not got["ls"].get(got["draftKey"]), \
            f"{rel}: после удачного повтора черновик остался"
    ok("девять страниц-карточек: повтор после провала записывает")

    for rel in MULTI:
        got = page(rel, """
  await answerAllMulti();
  OUT.firstSync = state.sync;
  globalThis.__ALIVE();
  await retryStore(TESTS[0].key);
  await new Promise(function (r) { setTimeout(r, 40); });
  OUT.sync = state.sync;
  OUT.storeKey = STORE_KEY;
  OUT.resultKey = RESULT_KEY;
  OUT.shift = globalThis.__APP.innerHTML;
""", fail=True)
        assert got["firstSync"] == "error", f"{rel}: первая попытка не провалилась"
        assert got["sync"] == "ok", f"{rel}: повтор не записал, sync={got['sync']}"
        assert not got["ls"].get(got["storeKey"]), \
            f"{rel}: после удачного повтора черновик остался"
        assert got["ls"].get(got["resultKey"]), \
            f"{rel}: запись прошла, а в памяти телефона следа нет"
        # Повтор — тот же замер, а не новый: сам с собой он не сравнивается.
        assert "как в прошлый раз" not in visible(got["shift"]), \
            f"{rel}: повтор отправки сравнил замер сам с собой"
    ok("восемь страниц с тестами: повтор записывает и не портит сравнение")
# Слепок записи, снятый ДО правки прогресса. Прибит здесь руками сознательно:
# посчитать его из самой страницы значит согласиться с любым её состоянием,
# включая «полей не осталось». Расхождение имён рвёт линии в панелях и делает
# уже собранные данные людей нечитаемыми.
FROZEN: Dict[str, Dict] = {
    'pair-faces/app.html': {
        "block": 'pair_faces', "instrument": 'pair_faces',
        "scores": ['faces', 'source'],
        "answers": ['raw'],
        "inner": {'faces': ['chaotic', 'cohesion', 'disengaged', 'enmeshed', 'flexibility', 'rigid']},
        "top": ['answers', 'block', 'completed_at', 'id', 'instrument', 'scores', 'user_id']},
    'selfhood/app.html': {
        "block": 'selfhood', "instrument": 'SCCS + Authenticity Scale + DIDS + DSI-R (I-position)',
        "scores": ['authenticity', 'clarity', 'identity', 'iposition', 'source'],
        "answers": ['authenticity', 'clarity', 'identity', 'iposition'],
        "inner": {'clarity': ['band', 'mean', 'nums', 'sum'], 'authenticity': ['authentic_living', 'band', 'external_influence', 'nums', 'self_alienation'], 'identity': ['band', 'commitment', 'exploration_breadth', 'exploration_depth', 'identification', 'nums', 'rumination'], 'iposition': ['band', 'mean', 'nums', 'sum']},
        "top": ['answers', 'block', 'completed_at', 'instrument', 'scores', 'user_id']},
    'state-clinical/app.html': {
        "block": 'state_clinical', "instrument": 'PHQ-9 + GAD-7 + ASRM',
        "scores": ['alert', 'asrm', 'gad', 'phq', 'source'],
        "answers": ['asrm', 'gad', 'phq'],
        "inner": {'phq': ['alert', 'band', 'item9', 'item9_flag', 'nums', 'total'], 'gad': ['alert', 'band', 'nums', 'total'], 'asrm': ['alert', 'band', 'nums', 'total']},
        "top": ['answers', 'block', 'completed_at', 'instrument', 'scores', 'user_id']},
    'state-day/app.html': {
        "block": 'state_day', "instrument": 'суточный мини-апп',
        "scores": ['mood', 'source', 'tonus'],
        "answers": ['raw'],
        "inner": {},
        "top": ['answers', 'block', 'completed_at', 'id', 'instrument', 'scores', 'user_id']},
    'state-domains/app.html': {
        "block": 'state_domains', "instrument": 'state_domains',
        "scores": ['pwi', 'source'],
        "answers": ['raw'],
        "inner": {'pwi': ['achieve', 'community', 'future', 'health', 'imp_achieve', 'imp_community', 'imp_future', 'imp_health', 'imp_living', 'imp_meaning', 'imp_relations', 'imp_safety', 'living', 'meaning', 'relations', 'safety', 'thin']},
        "top": ['answers', 'block', 'completed_at', 'id', 'instrument', 'scores', 'user_id']},
    'state-facts/app.html': {
        "block": 'state_facts', "instrument": 'state_facts',
        "scores": ['facts', 'signs', 'source'],
        "answers": ['raw'],
        "inner": {'facts': ['containers', 'marked', 'shown', 'work_evenings'], 'signs': ['kids', 'meditates', 'team']},
        "top": ['answers', 'block', 'completed_at', 'id', 'instrument', 'scores', 'user_id']},
    'state-finwell/app.html': {
        "block": 'state_finwell', "instrument": 'state_finwell',
        "scores": ['finwell', 'source'],
        "answers": ['raw'],
        "inner": {'finwell': ['behind', 'bygetting', 'control', 'enjoy', 'future', 'gift', 'lastlong', 'leftover', 'never', 'shock']},
        "top": ['answers', 'block', 'completed_at', 'id', 'instrument', 'scores', 'user_id']},
    'state-health/app.html': {
        "block": 'state_health', "instrument": 'state_health',
        "scores": ['promis', 'source'],
        "answers": ['raw'],
        "inner": {'promis': ['activities', 'alert', 'emotional', 'fatigue', 'health', 'mental', 'pain', 'physical', 'qol', 'roles', 'social']},
        "top": ['answers', 'block', 'completed_at', 'id', 'instrument', 'scores', 'user_id']},
    'state-money/app.html': {
        "block": 'state_money', "instrument": 'state_money',
        "scores": ['money', 'source'],
        "answers": ['raw'],
        "inner": {'money': ['cushion_n', 'debts_n', 'enough', 'enough_word', 'gap_n', 'shock_text']},
        "top": ['answers', 'block', 'completed_at', 'id', 'instrument', 'scores', 'user_id']},
    'state-month/app3.html': {
        "block": 'state_month', "instrument": 'PSS-10 + ISI',
        "scores": ['alert', 'isi', 'pss', 'source'],
        "answers": ['isi', 'pss'],
        "inner": {'pss': ['band', 'nums', 'total'], 'isi': ['alert', 'band', 'nums', 'total']},
        "top": ['answers', 'block', 'completed_at', 'instrument', 'scores', 'user_id']},
    'state-move/app.html': {
        "block": 'state_move', "instrument": 'state_move',
        "scores": ['evs', 'source'],
        "answers": ['raw'],
        "inner": {'evs': ['days', 'min_day', 'min_week']},
        "top": ['answers', 'block', 'completed_at', 'id', 'instrument', 'scores', 'user_id']},
    'state-needs/app.html': {
        "block": 'state_needs', "instrument": 'BPNSFS',
        "scores": ['alert', 'bpnsfs', 'source'],
        "answers": ['bpnsfs'],
        "inner": {'bpnsfs': ['autonomy_frustration', 'autonomy_satisfaction', 'band', 'competence_frustration', 'competence_satisfaction', 'frustration', 'nums', 'relatedness_frustration', 'relatedness_satisfaction', 'satisfaction']},
        "top": ['answers', 'block', 'completed_at', 'instrument', 'scores', 'user_id']},
    'state-note/app.html': {
        "block": 'state_note', "instrument": 'state_note',
        "scores": ['note', 'source'],
        "answers": ['raw'],
        "inner": {'note': ['text']},
        "top": ['answers', 'block', 'completed_at', 'id', 'instrument', 'scores', 'user_id']},
    'state-people/app.html': {
        "block": 'state_people', "instrument": 'state_people',
        "scores": ['lonely', 'source'],
        "answers": ['raw'],
        "inner": {'lonely': ['items', 'met', 'total']},
        "top": ['answers', 'block', 'completed_at', 'id', 'instrument', 'scores', 'user_id']},
    'state-quarter/app3.html': {
        "block": 'state_quarter', "instrument": 'SWLS + MLQ + FFMQ-15 + RSES + OLBI + MSPSS',
        "scores": ['ffmq', 'mlq', 'olbi', 'rses', 'source', 'support', 'swls'],
        "answers": ['ffmq', 'mlq', 'olbi', 'rses', 'support', 'swls'],
        "inner": {'swls': ['band', 'nums', 'sum'], 'mlq': ['band', 'nums', 'presence', 'search'], 'ffmq': ['act_aware', 'band', 'describe', 'mean', 'nonjudge', 'nonreact', 'nums', 'observe'], 'rses': ['band', 'nums', 'sum'], 'olbi': ['band', 'disengagement', 'disengagement_sum', 'exhaustion', 'exhaustion_sum', 'nums'], 'support': ['band', 'family', 'friends', 'nums', 'significant_other']},
        "top": ['answers', 'block', 'completed_at', 'instrument', 'scores', 'user_id']},
    'state-team/app.html': {
        "block": 'state_team', "instrument": 'Шкала психологической безопасности команды (Edmondson, 1999)',
        "scores": ['alert', 'safety', 'source'],
        "answers": ['safety'],
        "inner": {'safety': ['band', 'mean', 'nums']},
        "top": ['answers', 'block', 'completed_at', 'instrument', 'scores', 'user_id']},
    'state-week/app4.html': {
        "block": 'state_week', "instrument": 'PANAS-SF + Vitality + PHQ-2/GAD-2 + поток + KMS-3',
        "scores": ['couple', 'flow', 'gate', 'panas', 'source', 'vitality'],
        "answers": ['couple', 'flow', 'gate', 'panas', 'vitality'],
        "inner": {'panas': ['band', 'na', 'nums', 'pa'], 'vitality': ['band', 'mean', 'nums'], 'gate': ['alert', 'band', 'gad', 'nums', 'phq'], 'flow': ['band', 'nums', 'value'], 'couple': ['band', 'nums', 'sum']},
        "top": ['answers', 'block', 'completed_at', 'instrument', 'scores', 'user_id']},
    'state-year/app.html': {
        "block": 'state_year', "instrument": 'AUDIT-C',
        "scores": ['alert', 'audit', 'source'],
        "answers": ['audit'],
        "inner": {'audit': ['alert', 'band', 'nums', 'sex_asked', 'threshold', 'total']},
        "top": ['answers', 'block', 'completed_at', 'instrument', 'scores', 'user_id']},
}


# ==========================================================================
# 8. Ключи записи и сборка не изменились
# ==========================================================================

MULTI_ALL_JS = r"""
  for (var n = 0; n < TESTS.length; n++) {
    var t = TESTS[n];
    var ans = {};
    t.items.forEach(function (it, i) { var sc = it.scale || t.scale; ans[i] = sc[0].v; });
    state.key = t.key; state.idx = 0; state.answers = ans;
    if (typeof store === 'function') await store(t.key, SCORERS[t.key](ans), Object.assign({}, ans));
    else await finish();
    await new Promise(function (r) { setTimeout(r, 10); });
  }
"""

DAY_ALL_JS = r"""
  tapScale('tonus', 6);
  tapScale('mood', 7);
  await submit();
  await new Promise(function (r) { setTimeout(r, 20); });
"""


def _last_record(rel: str) -> Dict:
    if rel in SINGLE:
        got = page(rel, "  await answerAllSingle();")
    elif rel in MULTI:
        got = page(rel, MULTI_ALL_JS)
    else:
        got = page(rel, DAY_ALL_JS, search="?u=tg_777")
    assert got["pushed"], f"{rel}: в базу не ушло ничего"
    return got["pushed"][-1]


def check_record_shape_frozen() -> None:
    """8. Блок, подпись инструмента и все ключи записи — те же, что были."""
    for rel in ALL_PAGES:
        rec = _last_record(rel)
        want = FROZEN[rel]
        assert rec["block"] == want["block"], \
            f"{rel}: блок стал «{rec['block']}» вместо «{want['block']}»"
        assert rec["instrument"] == want["instrument"], \
            f"{rel}: подпись инструмента стала «{rec['instrument']}»"
        assert sorted(rec["scores"]) == want["scores"], \
            f"{rel}: верхние ключи записи стали {sorted(rec['scores'])}"
        assert sorted(rec["answers"]) == want["answers"], \
            f"{rel}: ключи ответов стали {sorted(rec['answers'])}"
        for block, keys in want["inner"].items():
            got = sorted(rec["scores"][block].keys())
            assert got == keys, f"{rel}: поля «{block}» стали {got}"
        assert sorted(rec.keys()) == want["top"], \
            f"{rel}: верхние поля записи стали {sorted(rec.keys())}"
    ok("восемнадцать страниц: ключи записи и её сборка не изменились")


def check_storage_keys_frozen() -> None:
    """8a. Имена ячеек памяти телефона не разъехались.

    Переименовать ячейку — значит потерять и черновики, и прошлые результаты у
    всех, кто уже пользуется страницей.
    """
    for rel in MULTI:
        got = page(rel, """
  OUT.store = STORE_KEY; OUT.result = RESULT_KEY; OUT.cloud = CLOUD_KEY;
""")
        block = FROZEN[rel]["block"]
        assert got["store"] == block + "_tg_777", f"{rel}: черновик лежит в «{got['store']}»"
        assert got["result"] == block + "_result_tg_777", \
            f"{rel}: результаты лежат в «{got['result']}»"
        assert got["cloud"] == "res_" + block, f"{rel}: облако «{got['cloud']}»"
    for rel in SINGLE:
        got = page(rel, "  OUT.draft = DRAFT_KEY; OUT.points = POINTS_KEY;")
        block = FROZEN[rel]["block"]
        assert got["points"] == block + "_points_777", \
            f"{rel}: прошлые точки лежат в «{got['points']}»"
        assert got["draft"] == block + "_draft_777", \
            f"{rel}: черновик лежит в «{got['draft']}» — ждали «{block}_draft_777»"
        assert got["draft"] != got["points"], f"{rel}: черновик и точки в одной ячейке"
    got = page(DAY, "  OUT.draft = DRAFT_KEY; OUT.sent = LS_KEY;", search="?u=tg_777")
    assert got["sent"] == "sutki_v1_777", f"{DAY}: отправленное лежит в «{got['sent']}»"
    assert got["draft"] == "sutki_draft_777", f"{DAY}: черновик в «{got['draft']}»"
    ok("имена ячеек памяти телефона на месте, черновик лежит отдельно")


def check_draft_not_persisted_into_record() -> None:
    """9. Восстановленное не превращает прошлые замеры в свежие."""
    OLD = "2026-06-01T10:00:00.000Z"
    for rel in MULTI:
        first = page(rel, """
  OUT.n = await answerPartialMulti();
  TESTS.slice(1).forEach(function (t) {
    results[t.key] = { nums: [11], band: 'старое', c: 'ok', data: { total: 11 },
                       answers: { 0: 1 }, completed_at: '%s' };
  });
  saveResultsLocal();
""" % OLD)
        got = page(rel, """
  resumeTest();
  await new Promise(function (r) { setTimeout(r, 10); });
  var t = getTest(state.key);
  for (var i = state.idx; i < t.items.length; i++) {
    var sc = t.items[i].scale || t.scale;
    answer(sc[0].v);
    await new Promise(function (r) { setTimeout(r, 0); });
  }
  await new Promise(function (r) { setTimeout(r, 40); });
  OUT.keys = TESTS.map(function (x) { return x.key; });
  OUT.sync = state.sync;
""", ls=first["ls"])
        assert got["sync"] == "ok", f"{rel}: дописанный черновик не отправился"
        assert len(got["pushed"]) == 1, f"{rel}: записей {len(got['pushed'])}"
        rec = got["pushed"][0]
        own = sorted(k for k in rec["scores"] if k not in ("source", "alert"))
        assert own == [got["keys"][0]], \
            f"{rel}: вместе с дописанным тестом в базу уехало {own}"
        assert sorted(rec["answers"]) == [got["keys"][0]], \
            f"{rel}: в ответах уехало {sorted(rec['answers'])}"
        assert rec["completed_at"] != OLD, f"{rel}: у записи чужая дата"
    ok("дописанный черновик не тянет в базу прошлые замеры")

    for rel in SINGLE:
        first = partial(rel)
        got = page(rel, """
  byId('resumeBtn').click();
  await new Promise(function (r) { setTimeout(r, 10); });
  for (var i = 0; i < 200; i++) {
    if (state.screen !== 'step') break;
    var s = stepByKey(state.key);
    setAnswer(s.key, stepValue(s));
    advance();
    await new Promise(function (r) { setTimeout(r, 0); });
  }
  await new Promise(function (r) { setTimeout(r, 40); });
  OUT.sync = state.sync;
""", ls=first["ls"])
        assert got["sync"] == "ok", f"{rel}: дописанный черновик не отправился"
        assert len(got["pushed"]) == 1, f"{rel}: записей {len(got['pushed'])}"
        rec = got["pushed"][0]
        assert rec["scores"].get("source") == "manual", f"{rel}: пропала метка источника"
        assert rec["completed_at"][:4] == "2026", f"{rel}: у записи чужая дата"
        want = FROZEN[rel]
        assert sorted(rec["scores"]) == want["scores"], \
            f"{rel}: дописанный черновик собрал другую запись: {sorted(rec['scores'])}"
    ok("дописанный черновик уходит в базу как один сегодняшний замер")


def check_draft_never_leaves_the_phone() -> None:
    """9a. Черновик не уходит ни в базу, ни в облако."""
    for rel in list(SINGLE) + MULTI + [DAY]:
        got = partial(rel)
        assert got["pushed"] == [] and got["patched"] == [], \
            f"{rel}: незаконченный замер уехал в базу"
    for rel in ALL_PAGES:
        src = inline_script(rel)
        name = "function saveProgress()" if rel in MULTI else "function saveDraft()"
        assert name in src, f"{rel}: нет функции сохранения черновика"
        i = src.index(name)
        body = src[i:src.index("\n}", i)]
        for bad in ("CloudStorage", "fetch(", "sendData"):
            assert bad not in body, f"{rel}: черновик уходит дальше телефона ({bad})"
    ok("черновик остаётся на телефоне: ни базы, ни облака")


# ==========================================================================
# 10. Ни одного балла и ни одного названия шкалы в новых текстах
# ==========================================================================

SCALE_NAMES = ("PHQ", "GAD", "PSS", "ISI", "AUDIT", "ASRM", "SWLS", "MLQ",
               "FFMQ", "RSES", "OLBI", "MSPSS", "PANAS", "BPNSFS", "SCCS",
               "DIDS", "PWI", "PROMIS", "FACES", "KMS", "UCLA")

# Слова-упрёки. Замер не судья: человек пришёл перестать себя винить.
BLAME_WORDS = ("бросил", "не довёл", "провалил", "поленился", "забросил",
               "опять", "снова не")


def check_resume_text_is_clean() -> None:
    """10. Строка про продолжение — без баллов, без аббревиатур, без упрёка."""
    for rel in ALL_PAGES:
        first = partial(rel)
        got = page(rel, "  OUT.firstScreen = globalThis.__APP.innerHTML;",
                   ls=first["ls"])
        text = visible(got["firstScreen"])
        for name in SCALE_NAMES:
            assert name not in text, f"{rel}: на первом экране название шкалы «{name}»"
        assert not re.search(r"\b\d+\s*балл", text), f"{rel}: на первом экране баллы"
        low = text.lower()
        for w in BLAME_WORDS:
            assert w not in low, f"{rel}: в строке про продолжение упрёк «{w}»"
    ok("строка про продолжение без баллов, аббревиатур и упрёков")


if __name__ == "__main__":
    raise SystemExit(run([
        check_draft_saved_after_each_answer,
        check_return_is_visible_and_explicit,
        check_return_opens_first_unanswered,
        check_start_over_wipes_draft,
        check_foreign_period_not_restored,
        check_stale_draft_expires,
        check_ttl_comes_from_rhythm,
        check_draft_cleared_after_send,
        check_failed_send_is_visible,
        check_failure_survives_leaving,
        check_retry_after_failure_writes,
        check_record_shape_frozen,
        check_storage_keys_frozen,
        check_draft_not_persisted_into_record,
        check_draft_never_leaves_the_phone,
        check_resume_text_is_clean,
    ]))
