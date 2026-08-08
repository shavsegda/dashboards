# -*- coding: utf-8 -*-
"""Проверки дорожки «пройти несколько за раз» (спека 011, История 3).

Что такое дорожка. Отдельный вход для того, кто пришёл разбираться, а не
ответить на напоминание: замеры идут цепочкой экранов, и после каждого сразу
открывается следующий. Раньше очередь держал бот, и человека на каждом переходе
выбрасывало в чат. Решение Алексея 07.08.2026: дорожка живёт в мини-аппе.

Что проверяется, по требованиям спеки:

  · **до старта** видно число замеров и минуты плюс честная оговорка: широкий
    срез, но не линия;
  · **порядок по вкладу в картину**: первым идёт замер, который закрывает пустую
    область жизни, а не самый просроченный по календарю;
  · **следующий сразу**: замер записан — открывается адрес следующего, без
    возврата в список и без единого выхода в чат;
  · **около двадцати минут** — предложение остановиться с причиной. Предложение,
    не запрет: «Продолжить» работает;
  · **итог один сшитый** — не столбик отдельных результатов;
  · **выход и возврат**: запись дорожки лежит в памяти телефона, каталог
    предлагает продолжить с того места. Ответы внутри замера дорожка не хранит —
    за них отвечает черновик самой страницы, второго механизма нет;
  · **тяжёлый ответ останавливает дорожку** и человека направляют к специалисту.
    Screen and refer, never treat;
  · **записи замеров не изменились**: тот же блок, те же ключи, та же одна точка
    за период — дорожка ничего в запись не дописывает.

Как проверяем. Страницы исполняются в node целиком: браузер, Телеграм, память
телефона и база подменены заглушками. Заглушки и полные заходы берутся у соседних
проверок — `zamery_v_miniappe` и `polgoda_god`, — чтобы «полный заход» был один на
весь репозиторий, а не три разных.

Чего проверками НЕ берём и смотрим глазами на телефоне: как выглядят экраны, как
ведёт себя настоящая кнопка назад в настоящем клиенте и не стыдно ли читать
сшитый итог вслух.

В конце файла — мутационная проверка: каждое требование ломается точной правкой,
и нужная проверка обязана на ней покраснеть (конституция, принцип II).

Запуск:  python3 checks/dorozhka.py
"""

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
import polgoda_god as P
import zamery_v_miniappe as Z
from lib import (NODE_STUBS, ROOT, TAP_DOM, _node, catalog, html,
                 inline_script, ok, run, tg_stub, visible)

CHECKS = Path(__file__).resolve().parent

CATALOG = "kak-ty/app.html"

# Девять страниц, которые умеют дорожку. Ключ — блок в базе.
PAGES: Dict[str, str] = {
    "state_move": "state-move/app.html",
    "state_people": "state-people/app.html",
    "state_facts": "state-facts/app.html",
    "state_note": "state-note/app.html",
    "state_money": "state-money/app.html",
    "state_domains": "state-domains/app.html",
    "state_finwell": "state-finwell/app.html",
    "state_health": "state-health/app.html",
    "pair_faces": "pair-faces/app.html",
}

# Полный заход по каждому замеру — берём у соседних проверок, чтобы он был один.
FULL: Dict[str, str] = dict(Z.FULL)
FULL.update(P.FULL)

SEARCH: Dict[str, str] = dict(Z.SEARCH)
SEARCH.update(P.SEARCH)

# Ячейка памяти телефона под запись дорожки. Одна на все страницы: они на одном
# домене, и это то, что делает выход и возврат безопасными.
TRACK_KEY = "kak_ty_track_v1"

# Границы блока дорожки в исходнике. Блок обязан быть одинаковым везде.
MARK_A = "==== ДОРОЖКА: НАЧАЛО ===="
MARK_B = "==== ДОРОЖКА: КОНЕЦ ===="

SITE = "https://shapovalov-aleksey.ru"
HOME = SITE + "/kak-ty/app.html"

# Даты последних замеров, как их присылает бот параметром `f=`.
#
# Что здесь важно. Тело и Круг известны — по ним точки есть, но срок вышел.
# Про Я сам, Деньги, Семью и Время на себя не известно ничего. Значит дорожка
# обязана начать с пустого места, а не с самого просроченного замера.
FILL = "f=state_move:2026-07-01,state_people:2026-07-01"

NOW = "2026-08-07T10:00:00.000Z"

# Слова, которых в текстах дорожки быть не может.
BAD_WORDS = ["балл", "процент", "индекс", "уровень заполнения", "прогресс",
             "пройдено", "PHQ", "GAD", "UCLA", "PROMIS", "FACES", "PSS"]

DEBT_WORDS = ["нужно", "должен", "должна", "обязан", "пора"]

LETTER = "[0-9A-Za-zА-Яа-яЁё]"


def has_word(text: str, word: str) -> bool:
    return re.search(f"(?<!{LETTER}){re.escape(word)}(?!{LETTER})", text) is not None


# ==========================================================================
# Заглушки: каталог и страницы замера с памятью телефона и переходами
# ==========================================================================

# Переходы. Дорожка не «показывает ссылку», она сама открывает следующий адрес,
# и проверять надо именно это. Заглушка запоминает, куда ушли.
NAV = r"""
globalThis.window.location.pathname = '/kak-ty/app.html';
globalThis.window.location.origin = 'https://shapovalov-aleksey.ru';
globalThis.window.location.replace = function (u) {
  globalThis.window.location.href = String(u);
};
globalThis.history = globalThis.history ||
  { length: 2, back: function () { globalThis.HISTORY_BACK = 1; } };
"""


def rec(queue: List[dict], done: Optional[List[dict]] = None, state: str = "run",
        spent_min: float = 0, offered: int = 0,
        refer: Optional[str] = None) -> dict:
    """Запись дорожки, как она лежит в памяти телефона."""
    out = {"v": 1, "state": state, "startedAt": "__NOW__", "legAt": "__NOW__",
           "spentMs": int(spent_min * 60000), "offeredMin": offered,
           "home": HOME + "?u=tg_777&track=done",
           "queue": list(queue), "done": list(done or [])}
    if refer:
        out["refer"] = refer
    return out


def leg(key: str, label: str, area: str, mins: float = 1,
        page: Optional[str] = None) -> dict:
    """Один шаг очереди: что открывать и каким адресом."""
    return {"key": key, "label": label, "area": area, "mins": mins,
            "url": SITE + "/" + (page or key.replace("_", "-")) +
                   "/app.html?u=tg_777"}


def seed(record: Optional[dict]) -> str:
    """Положить запись дорожки в память телефона ДО запуска страницы."""
    if record is None:
        return ""
    body = json.dumps(record, ensure_ascii=False).replace('"__NOW__"', "Date.now()")
    return "localStorage.setItem(%s, JSON.stringify(%s));\n" % (
        json.dumps(TRACK_KEY), body)


PAGE_TAIL = r"""
const OUT = {};
function screen() { return globalThis.__APP.innerHTML; }
function tap(attr, needle) {
  var els = globalThis.__APP.querySelectorAll('[' + attr + ']').filter(function (e) {
    return e.tag.indexOf(needle) >= 0;
  });
  if (!els.length) throw new Error('нет элемента [' + attr + '] с «' + needle + '»');
  return els[0];
}
function went() { return globalThis.window.location.href || null; }
function record() {
  var raw = localStorage.getItem(%(key)s);
  return raw ? JSON.parse(raw) : null;
}
(async function () {
  await new Promise(function (r) { setTimeout(r, 20); });
%(js)s
  OUT.rows = globalThis.DB.rows;
  console.log('RESULT<' + JSON.stringify(OUT) + '>RESULT');
})();
"""


def page_run(block: str, js: str, record: Optional[dict] = None,
             search: Optional[str] = None) -> Dict:
    """Исполнить страницу замера целиком, с записью дорожки в памяти телефона."""
    rel = PAGES[block]
    code = (Z.stubs(search if search is not None else SEARCH[block], True)
            + NAV + seed(record) + inline_script(rel)
            + PAGE_TAIL % {"js": js, "key": json.dumps(TRACK_KEY)})
    return _node(code)


def pass_in_track(block: str, record: dict, extra: str = "",
                  answers: Optional[str] = None) -> Dict:
    """Пройти замер тем же путём, каким его проходит человек, внутри дорожки."""
    js = ("  startCard();\n  " + (answers or FULL[block]) +
          "\n  await finish();\n"
          "  OUT.went = went();\n  OUT.rec = record();\n"
          "  OUT.screen = screen();\n" + extra)
    return page_run(block, js, record=record)


CAT_TAIL = r"""
const OUT = {};
function screen() { return globalThis.__APP.innerHTML; }
function tap(attr, needle) {
  var els = globalThis.__APP.querySelectorAll('[' + attr + ']').filter(function (e) {
    return e.tag.indexOf(needle) >= 0;
  });
  if (!els.length) throw new Error('нет элемента [' + attr + '] с «' + needle + '»');
  return els[0];
}
function went() { return globalThis.window.location.href || null; }
function record() {
  var raw = localStorage.getItem(%(key)s);
  return raw ? JSON.parse(raw) : null;
}
setTimeout(function () {
%(js)s
  OUT.html = globalThis.__APP.innerHTML;
  OUT.calls = globalThis.TG_CALLS;
  console.log('RESULT<' + JSON.stringify(OUT) + '>RESULT');
}, 50);
"""


def cat_run(search: str, js: str = "", record: Optional[dict] = None,
            telegram: bool = True, init_data: str = "") -> Dict:
    """Собрать каталог с живым DOM и памятью телефона и понажимать на него."""
    stubs = NODE_STUBS.replace("'?u=tg_777'", repr(search).replace('"', "'"))
    code = (stubs + TAP_DOM + NAV + (tg_stub(init_data) if telegram else "")
            + seed(record) + inline_script(CATALOG)
            + CAT_TAIL % {"js": js, "key": json.dumps(TRACK_KEY)})
    return _node(code)


def cards_js(fill: str = FILL) -> str:
    """Карточки каталога, собранные так же, как их собирает экран."""
    dates = "{" + ", ".join(
        '"%s": "%s"' % (k, v) for k, v in
        (p.split(":") for p in fill.replace("f=", "").split(",") if p)) + "}"
    return """
var __cards = buildCards(visibleCards(REGISTRY, {}), %s, "%s", true);
""" % (dates, NOW)


# ==========================================================================
# Проверки
# ==========================================================================


def check_shared_block_is_one() -> None:
    """1. Блок дорожки один на десять страниц — побайтово."""
    blocks = {}
    for rel in [CATALOG] + sorted(PAGES.values()):
        src = html(rel)
        assert MARK_A in src and MARK_B in src, f"в {rel} нет блока дорожки"
        body = src[src.index(MARK_A) + len(MARK_A):src.index(MARK_B)]
        blocks[rel] = body
    first = blocks[CATALOG]
    assert len(first) > 800, f"блок дорожки подозрительно короткий: {len(first)}"
    for rel, body in blocks.items():
        assert body == first, \
            f"блок дорожки в {rel} разошёлся с каталогом на {len(body) - len(first)} символов"
    ok(f"блок дорожки одинаков на всех {len(blocks)} страницах")

    # Дорожка считает время и усталость в одном месте: два разных порога значили
    # бы, что на одной странице она останавливает, а на другой нет.
    for name in ("TRACK_KEY", "TRACK_TIRED_MIN", "trackHead", "trackLegDone",
                 "trackOfferStop", "trackIsHead"):
        assert name in first, f"в общем блоке нет «{name}»"
    ok("ключ памяти, порог усталости и шаги очереди объявлены один раз")


def check_order_by_contribution() -> None:
    """2. Порядок — по вкладу в картину, а не по календарю."""
    c = catalog(cards_js() + """
OUT.queue = trackQueue(__cards, {}).map(function (q) { return q.key; });
OUT.filled = filledAreas(__cards);
OUT.first = trackQueue(__cards, {})[0];
OUT.areas = {};
trackQueue(__cards, {}).forEach(function (q) { OUT.areas[q.key] = q.area; });
OUT.ranks = {};
__cards.forEach(function (x) { OUT.ranks[x.key] = trackRank(x, filledAreas(__cards)); });
""")
    q = c["queue"]
    assert q, "очередь дорожки пуста на живых данных"
    assert set(c["filled"]) == {"Тело", "Круг"}, \
        f"известными признаны области {c['filled']}, а точки есть только по Телу и Кругу"
    ok(f"известные области считаются по точкам: {', '.join(sorted(c['filled']))}")

    empty_first = [k for k in q if c["areas"][k] not in c["filled"]]
    known_after = [k for k in q if c["areas"][k] in c["filled"]]
    assert q[:len(empty_first)] == empty_first, \
        f"замеры из известных областей вклинились в начало: {q}"
    ok(f"сначала пустые области ({len(empty_first)}), потом известные ({len(known_after)})")

    assert q[0] == "state_facts", \
        f"первым идёт «{q[0]}», а не замер, закрывающий больше всего пустого места"
    ok("первый шаг закрывает пустую область и задевает больше всего областей")

    # Просрочка не делает замер важнее пустого места: у Движения срок вышел
    # больше месяца назад, и оно всё равно идёт после.
    assert q.index("state_move") > q.index("state_money"), \
        "самый просроченный замер обогнал пустую область — порядок по календарю"
    ok("календарная просрочка порядок не решает")

    # Один и тот же вход даёт один и тот же порядок: иначе человек, вышедший и
    # вернувшийся, получит другую дорожку.
    again = catalog(cards_js() + """
OUT.queue = trackQueue(__cards, {}).map(function (q) { return q.key; });
""")["queue"]
    assert again == q, "две сборки очереди дали разный порядок"
    ok("порядок устойчивый: две сборки дают одно и то же")


def check_queue_takes_only_what_it_can() -> None:
    """3. В очередь идут только страницы, которые дорожка умеет пройти."""
    c = catalog(cards_js("f=state_note:2026-08-06") + """
OUT.queue = trackQueue(__cards, {}).map(function (q) { return q.key; });
OUT.chat = REGISTRY.filter(function (r) { return r.phrase; }).map(function (r) { return r.key; });
OUT.noTrack = REGISTRY.filter(function (r) { return r.url && r.track !== true; })
                      .map(function (r) { return r.key; });
""")
    q = c["queue"]
    for key in c["chat"]:
        assert key not in q, \
            f"«{key}» идёт разговором, а стоит в дорожке — это выход в чат"
    ok(f"ни одного замера-разговора в очереди ({len(c['chat'])} проверено)")

    for key in c["noTrack"]:
        assert key not in q, \
            f"«{key}» в очереди, но его страница дорожку не умеет — цепочка порвётся"
    ok(f"страницы без дорожки в очередь не берутся ({len(c['noTrack'])} проверено)")

    assert "state_note" not in q, \
        "замер за этот период уже есть, а дорожка всё равно ведёт на него"
    ok("свежий замер в очередь не попадает: шаг был бы пустым")

    assert set(q) <= set(PAGES), f"в очереди чужие ключи: {set(q) - set(PAGES)}"
    ok("все ключи очереди — страницы дорожки")


def check_intro_says_count_and_caveat() -> None:
    """4. До старта: число замеров, минуты и честная оговорка про линию."""
    c = cat_run("?u=tg_777&" + FILL + "&track=1")
    text = visible(c["html"])
    m = re.search(r"(\d+)\s+замер\w*\s*·\s*около\s+(\d+)\s+минут", text)
    assert m, f"на экране до старта нет числа замеров и минут: {text[:300]}"
    assert int(m.group(1)) >= 2, "дорожка обещает меньше двух замеров"
    assert int(m.group(2)) >= 2, "дорожка обещает меньше двух минут на всё"
    ok(f"до старта сказано: {m.group(1)} замеров, около {m.group(2)} минут")

    low = text.lower()
    assert "срез" in low, "нет слова про широкий срез"
    assert "не линию" in low or "не линия" in low, \
        "нет оговорки, что линии за один вечер не будет"
    assert "временем" in low or "время" in low, \
        "не сказано, что линия рождается временем"
    ok("оговорка на месте: широкий срез, но не линия")

    assert "%" not in text, "на экране дорожки появился процент"
    assert not re.search(r"\d+\s*(из|/)\s*\d+", text), \
        "на экране дорожки появился счётчик пройденного"
    for bad in BAD_WORDS:
        assert bad.lower() not in low, f"в текстах дорожки «{bad}»"
    for bad in DEBT_WORDS:
        assert not has_word(low, bad), f"дорожка звучит как долг: «{bad}»"
    ok("ни балла, ни процента, ни счётчика, ни долга")

    # Дорожка начинается с того замера, который стоит в очереди первым, и это
    # видно человеку ДО старта: он идёт разбираться, а не в мешок с сюрпризом.
    assert "Восемь фактов" in text, \
        "не сказано, с какого замера начнётся дорожка"
    ok("сказано, с чего начнём")


def check_entry_stays_in_miniapp() -> None:
    """5. Вход в дорожку не выходит в чат."""
    src = html(CATALOG)
    assert MARK_A in src and MARK_B in src, "в каталоге нет блока дорожки"
    body = src[src.index(MARK_A):src.index(MARK_B)]
    for bad in ("sendData", "openTelegramLink", "t.me"):
        assert bad not in body, f"в блоке дорожки остался выход в чат: «{bad}»"
    ok("в блоке дорожки нет ни sendData, ни ссылки на переписку")

    c = cat_run("?u=tg_777&" + FILL, """
  var el = tap('data-track', 'start');
  OUT.tap = el.click();
  OUT.went = went();
""")
    assert c["calls"]["sent"] == [], \
        f"вход в дорожку отправил боту: {c['calls']['sent']}"
    assert c["calls"]["opened"] == [], \
        f"вход в дорожку открыл переписку: {c['calls']['opened']}"
    ok("нажатие входа не отправляет боту ничего и не открывает чат")

    went = c["went"] or ""
    assert "t.me" not in went, f"вход увёл в Телеграм: {went}"
    assert "track=1" in went, f"вход не открыл экран дорожки: {went}"
    assert "u=tg_777" in went, f"вход потерял человека: {went}"
    ok("вход открывает экран дорожки в том же мини-аппе")

    # Начало дорожки ведёт прямо на страницу первого замера, а не в бота.
    c2 = cat_run("?u=tg_777&" + FILL + "&track=1", """
  var el = tap('data-track', 'go');
  OUT.tap = el.click();
  OUT.went = went();
  OUT.rec = record();
""")
    assert c2["calls"]["sent"] == [] and c2["calls"]["opened"] == [], \
        "старт дорожки полез в чат"
    assert "/state-facts/app.html" in (c2["went"] or ""), \
        f"старт дорожки открыл не первый замер: {c2['went']}"
    assert "u=tg_777" in (c2["went"] or ""), "адрес первого замера без человека"
    ok("«Начать» открывает страницу первого замера")

    r = c2["rec"]
    assert r and r["state"] == "run", "запись дорожки не создана"
    assert [q["key"] for q in r["queue"]][0] == "state_facts", \
        f"в записи другая очередь: {[q['key'] for q in r['queue']]}"
    assert r["done"] == [], "в новой дорожке уже что-то пройдено"
    ok("запись дорожки создана: очередь на месте, пройденного нет")


def check_next_opens_at_once() -> None:
    """6. Замер записан — следующий открывается сразу, без возврата в список."""
    r = rec([leg("state_move", "Движение", "Тело"),
             leg("state_people", "Люди рядом", "Круг")])
    c = pass_in_track("state_move", r)

    assert len(c["rows"]) == 1, f"записей в базе {len(c['rows'])}, а не одна"
    assert c["went"], "дорожка никуда не пошла — человек застрял на результате"
    assert "/state-people/app.html" in c["went"], \
        f"вместо следующего замера открылось: {c['went']}"
    assert "t.me" not in c["went"], "после замера дорожка ушла в чат"
    assert "/kak-ty/" not in c["went"], \
        "после замера дорожка вернула человека в список"
    ok("следующий замер открывается сразу, список не показывается")

    # Пока идёт отправка, страница честно говорит «Секунду» — это её экран, и он
    # остаётся. Чего быть не должно, так это ГОТОВОГО результата замера: слова
    # соберутся в один итог в конце, а не шестью экранами подряд.
    screen = visible(c["screen"])
    assert "Записал" not in screen, \
        "посреди дорожки показан готовый результат замера"
    assert "Секунду" in screen, \
        "страница не сказала человеку, что отправляет замер"
    ok("готового результата посреди дорожки нет, «Секунду» на месте")

    got = c["rec"]
    assert [q["key"] for q in got["queue"]] == ["state_people"], \
        f"очередь не сдвинулась: {[q['key'] for q in got['queue']]}"
    assert [d["key"] for d in got["done"]] == ["state_move"], \
        f"пройденное не запомнилось: {got['done']}"
    assert got["done"][0]["lines"], "слова замера не попали в пройденное"
    ok("очередь сдвинулась, слова замера легли в пройденное")

    # Последний замер очереди уводит на итог, а не в пустоту.
    last = pass_in_track("state_move", rec([leg("state_move", "Движение", "Тело")]))
    assert "track=done" in (last["went"] or ""), \
        f"после последнего замера дорожка ушла не на итог: {last['went']}"
    assert last["rec"]["state"] == "finish", \
        f"дорожка не закрылась: {last['rec']['state']}"
    ok("последний замер уводит на итог")


def check_stop_offer_after_twenty() -> None:
    """7. Около двадцати минут — предложение остановиться, а не запрет."""
    early = pass_in_track("state_move", rec(
        [leg("state_move", "Движение", "Тело"),
         leg("state_people", "Люди рядом", "Круг")], spent_min=5))
    assert "/state-people/" in (early["went"] or ""), \
        "на пятой минуте дорожка уже останавливается"
    ok("до двадцати минут дорожка идёт молча")

    tired = pass_in_track("state_move", rec(
        [leg("state_move", "Движение", "Тело"),
         leg("state_people", "Люди рядом", "Круг")], spent_min=21))
    assert not tired["went"], \
        f"на двадцать первой минуте дорожка ушла дальше сама: {tired['went']}"
    text = visible(tired["screen"])
    assert "остановиться" in text.lower(), "предложения остановиться нет"
    assert "точн" in text.lower(), \
        "не сказана причина: уставшие ответы менее точны"
    ok("предложение остановиться с причиной")

    low = text.lower()
    for bad in ("хватит", "стоп, дальше нельзя", "дальше нельзя", "закрываю"):
        assert bad not in low, f"предложение звучит как запрет: «{bad}»"
    assert "продолжить" in low, "продолжить дорожку нечем — это запрет"
    ok("это предложение: продолжить можно")

    # Замер, который человек только что прошёл, записан и в очередь не вернётся.
    assert len(tired["rows"]) == 1, "на предложении остановиться запись потерялась"
    assert [d["key"] for d in tired["rec"]["done"]] == ["state_move"], \
        "пройденный замер не попал в пройденное"
    ok("на предложении остановиться запись уже в базе")

    go_on = pass_in_track("state_move", rec(
        [leg("state_move", "Движение", "Тело"),
         leg("state_people", "Люди рядом", "Круг")], spent_min=21),
        extra="""
  tap('data-track', 'go').click();
  OUT.after = went();
  OUT.rec2 = record();
""")
    assert "/state-people/" in (go_on["after"] or ""), \
        f"«Продолжить» не открыл следующий замер: {go_on['after']}"
    assert go_on["rec2"]["state"] == "run", "после «Продолжить» дорожка закрылась"
    assert go_on["rec2"]["offeredMin"] >= 20, \
        "предложение не отмечено — оно придёт на каждом замере подряд"
    ok("«Продолжить» ведёт дальше, второй раз подряд не спрашивает")

    stop = pass_in_track("state_move", rec(
        [leg("state_move", "Движение", "Тело"),
         leg("state_people", "Люди рядом", "Круг")], spent_min=21),
        extra="""
  tap('data-track', 'stop').click();
  OUT.after = went();
  OUT.rec2 = record();
""")
    assert "track=done" in (stop["after"] or ""), \
        f"«Остановиться» не показал итог: {stop['after']}"
    assert stop["rec2"]["state"] == "stopped", \
        f"после остановки дорожка осталась в состоянии {stop['rec2']['state']}"
    assert [q["key"] for q in stop["rec2"]["queue"]] == ["state_people"], \
        "остановка выбросила непройденное — вернуться будет некуда"
    ok("«Остановиться» ведёт на итог, непройденное остаётся на месте")


def check_one_stitched_summary() -> None:
    """8. Итог — один сшитый текст, а не столбик результатов."""
    done = [
        {"key": "state_move", "label": "Движение", "area": "Тело",
         "lines": ["3 дн. по 40 мин — 120 минут за неделю.",
                   "Ориентир по здоровью — 150 минут в неделю. До него 30 минут."]},
        {"key": "state_people", "label": "Люди рядом", "area": "Круг",
         "lines": ["Живых встреч на этой неделе не было."]},
        {"key": "state_money", "label": "Деньги за месяц", "area": "Деньги",
         "lines": ["Денег хватило."]},
    ]
    r = rec([], done=done, state="finish")
    c = cat_run("?u=tg_777&" + FILL + "&track=done", record=r)
    body = c["html"]
    text = visible(body)

    holders = re.findall(r'class="stitch"', body)
    assert len(holders) == 1, \
        f"итог собран из {len(holders)} блоков — это столбик результатов"
    ok("итог лежит в одном блоке")

    m = re.search(r'<p class="stitch">(.*?)</p>', body, re.S)
    assert m, "сшитого текста на экране итога нет"
    stitched = visible(m.group(1))
    for d in done:
        for line in d["lines"]:
            assert line.strip(".") in stitched or line in stitched, \
                f"в сшитый текст не попали слова замера «{d['label']}»: {line}"
    ok(f"в одном тексте слова всех {len(done)} пройденных замеров")

    assert len(re.findall(r'class="res-row"', body)) == 0, \
        "на итоге появились отдельные строки-результаты"
    ok("отдельных результатов на экране нет")

    low = text.lower()
    assert "срез" in low, "итог не говорит, что это срез"
    assert "линия" in low or "линии" in low, \
        "итог не говорит, что линия появится позже"
    ok("итог честный: широкий срез, линия появится потом")

    assert "%" not in text, "на итоге появился процент"
    assert not re.search(r"\d+\s*(из|/)\s*\d+", text), \
        "на итоге появился счётчик пройденного"
    for bad in BAD_WORDS:
        assert bad.lower() not in low, f"в итоге «{bad}»"
    ok("ни сводного балла, ни процента, ни счётчика")

    # Итог показан — дорожки больше нет: возвращаться в неё некуда.
    c2 = cat_run("?u=tg_777&" + FILL + "&track=done", """
  tap('data-track', 'close').click();
  OUT.rec = record();
  OUT.went = went();
""", record=r)
    assert c2["rec"] is None, "после итога запись дорожки осталась в памяти"
    ok("после итога дорожка убирается из памяти телефона")

    # Пройдено ноль — сшивать нечего, и врать про итог нельзя.
    empty = cat_run("?u=tg_777&" + FILL + "&track=done",
                    record=rec([], done=[], state="finish"))
    assert 'class="stitch"' not in empty["html"], \
        "итог показан там, где не пройдено ни одного замера"
    ok("пустой дорожке итог не показывается")


def check_progress_survives_exit() -> None:
    """9. Вышел посреди дорожки — вернулся и продолжил с того места."""
    r = rec([leg("state_people", "Люди рядом", "Круг"),
             leg("state_money", "Деньги за месяц", "Деньги")],
            done=[{"key": "state_move", "label": "Движение", "area": "Тело",
                   "lines": ["120 минут за неделю."]}])
    c = cat_run("?u=tg_777&" + FILL, record=r)
    text = visible(c["html"])
    assert "дорожк" in text.lower(), "каталог молчит про начатую дорожку"
    assert "Люди рядом" in text, "не сказано, какой замер следующий"
    ok("каталог говорит, что дорожка на месте, и называет следующий замер")

    c2 = cat_run("?u=tg_777&" + FILL, """
  tap('data-track', 'go').click();
  OUT.went = went();
  OUT.rec = record();
""", record=r)
    assert "/state-people/app.html" in (c2["went"] or ""), \
        f"«Продолжить» открыл не тот замер: {c2['went']}"
    assert [d["key"] for d in c2["rec"]["done"]] == ["state_move"], \
        "продолжение потеряло пройденное"
    ok("«Продолжить» открывает тот замер, на котором человек вышел")

    # Ответы внутри замера дорожка не хранит: за них отвечает черновик страницы.
    keys = set(r) | {"refer"}
    got = set(c2["rec"])
    assert got <= keys, f"в записи дорожки появились лишние поля: {got - keys}"
    for d in c2["rec"]["done"]:
        assert set(d) == {"key", "label", "area", "lines"}, \
            f"в пройденном лежат ответы человека: {set(d)}"
    ok("дорожка держит очередь и слова, а не ответы: черновик у страницы свой")

    # Черновик замера при этом работает как раньше: человек, вышедший посреди
    # замера внутри дорожки, возвращается на свой вопрос.
    half = page_run("state_domains", """
  startCard();
  setAnswer('living', 7);
  var d = loadDraft();
  OUT.draft = d ? Object.keys(d.a) : null;
  renderIntro();
  OUT.intro = screen();
""", record=rec([leg("state_domains", "Области жизни", "Я сам")]))
    assert half["draft"] == ["living"], \
        f"черновик замера внутри дорожки не пишется: {half['draft']}"
    assert "Продолжить" in visible(half["intro"]), \
        "страница внутри дорожки не предлагает продолжить начатый замер"
    ok("черновик замера внутри дорожки — прежний, второго механизма нет")

    # Дорожка кончилась или её нет — страница ведёт себя как обычно.
    alone = pass_in_track("state_move", rec([leg("state_people", "Люди рядом", "Круг")]))
    assert not alone["went"], \
        "страница увела человека дальше, хотя дорожка ждёт другой замер"
    assert "Пройти снова" in visible(alone["screen"]), \
        "вне своей очереди страница не показала обычный результат"
    ok("не свой шаг дорожки — обычный экран результата")


def check_heavy_answer_stops() -> None:
    """10. Тяжёлый ответ останавливает дорожку и ведёт к специалисту."""
    two = [leg("state_note", "Что ещё стоит знать", "Я сам"),
           leg("state_money", "Деньги за месяц", "Деньги")]
    heavy = pass_in_track(
        "state_note", rec(list(two)),
        answers="setAnswer('text', 'не хочу жить, всё это бессмысленно');")
    assert not heavy["went"], \
        f"после тяжёлого ответа дорожка открыла следующий замер: {heavy['went']}"
    ok("тяжёлый ответ дальше не гонит")

    text = visible(heavy["screen"])
    low = text.lower()
    assert "специалист" in low or "врач" in low or "психотерапевт" in low, \
        "человека не направили к специалисту"
    assert "112" in text or "8 800" in text, \
        "не дан живой контакт, куда обратиться сейчас"
    ok("на экране направление к специалисту и живой контакт")

    for bad in ("диагноз", "у тебя депресс", "это депресс", "ты в депресс"):
        assert bad not in low.replace("не диагноз", ""), \
            f"страница взялась толковать: «{bad}»"
    ok("ни диагноза, ни толкования: screen and refer, never treat")

    assert heavy["rec"]["state"] == "stopped", \
        f"дорожка осталась в состоянии {heavy['rec']['state']}"
    assert [q["key"] for q in heavy["rec"]["queue"]] == ["state_money"], \
        "остановка стёрла непройденное"
    assert len(heavy["rows"]) == 1, "ответ человека не записан"
    ok("дорожка остановлена, ответ записан, непройденное на месте")

    calm = pass_in_track("state_note", rec(list(two)))
    assert "/state-money/" in (calm["went"] or ""), \
        f"обычный ответ тоже остановил дорожку: {calm['went']}"
    ok("обычный ответ дорожку не останавливает")

    # Тот же предохранитель на пороге здоровья: у страницы он уже есть, и
    # дорожка обязана его слушаться, а не считать свой.
    alert = pass_in_track(
        "state_health", rec([leg("state_health", "Здоровье в целом", "Тело"),
                             leg("state_money", "Деньги за месяц", "Деньги")]),
        answers=P.FULL["state_health"] + " setAnswer('mental', 1);")
    assert not alert["went"], "порог здоровья дорожку не остановил"
    assert alert["rec"]["state"] == "stopped", "дорожка идёт дальше после порога"
    assert "врач" in visible(alert["screen"]).lower(), \
        "порог здоровья не привёл к врачу"
    ok("порог здоровья останавливает дорожку тем же путём")


def check_records_unchanged() -> None:
    """11. Записи замеров дорожка не меняет."""
    for block in sorted(PAGES):
        plain = Z._node(
            Z.stubs(SEARCH[block], True) + NAV + inline_script(PAGES[block]) +
            PAGE_TAIL % {"key": json.dumps(TRACK_KEY),
                         "js": "  startCard();\n  " + FULL[block] +
                               "\n  await finish();\n"})
        inside = pass_in_track(block, rec([leg(block, "Замер", "Тело")]))
        assert len(plain["rows"]) == 1 and len(inside["rows"]) == 1, \
            f"«{block}»: записей не по одной"
        a, b = plain["rows"][0], inside["rows"][0]
        for field in ("block", "instrument", "scores", "answers", "user_id"):
            assert a[field] == b[field], \
                f"«{block}»: поле {field} в дорожке другое:\n{a[field]}\n{b[field]}"
    ok(f"на всех {len(PAGES)} страницах запись в дорожке та же, что без неё")

    # Одна точка за период: дорожка не создаёт второй записи, даже если человек
    # прошёл замер внутри дорожки после того, как проходил его сам.
    twice = page_run("state_move", """
  startCard();
""" + FULL["state_move"] + """
  await finish();
  startCard();
""" + FULL["state_move"] + """
  await finish();
  OUT.went = went();
""", record=rec([leg("state_move", "Движение", "Тело")]))
    assert len(twice["rows"]) == 1, \
        f"два захода внутри дорожки дали {len(twice['rows'])} точек"
    ok("две отправки внутри дорожки — одна точка за период")

    # Дорожка ничего не дописывает в scores: панели читают те же ключи.
    one = pass_in_track("state_move", rec([leg("state_move", "Движение", "Тело")]))
    scores = one["rows"][0]["scores"]
    assert set(scores) == {"evs", "source"}, \
        f"дорожка дописала в запись свои поля: {set(scores)}"
    ok("в записи только поля замера, метки дорожки нет")


def check_texts_are_clean() -> None:
    """12. Тексты дорожки: без баллов, без долга, без латиницы."""
    screens = []
    screens.append(visible(cat_run("?u=tg_777&" + FILL + "&track=1")["html"]))
    screens.append(visible(cat_run(
        "?u=tg_777&" + FILL + "&track=done",
        record=rec([], done=[{"key": "state_move", "label": "Движение",
                              "area": "Тело", "lines": ["120 минут за неделю."]}],
                   state="finish"))["html"]))
    resume = cat_run("?u=tg_777&" + FILL,
                     record=rec([leg("state_people", "Люди рядом", "Круг")]))["html"]
    m = re.search(r'<div class="track">(.*?)</div>\s*</div>', resume, re.S)
    assert m, "строки про начатую дорожку на экране нет"
    screens.append(visible(m.group(1)))
    tired = pass_in_track("state_move", rec(
        [leg("state_move", "Движение", "Тело"),
         leg("state_people", "Люди рядом", "Круг")], spent_min=21))
    screens.append(visible(tired["screen"]))

    for text in screens:
        low = text.lower()
        for bad in BAD_WORDS:
            assert bad.lower() not in low, f"«{bad}» в тексте: {text[:120]}"
        for bad in DEBT_WORDS:
            assert not has_word(low, bad), f"долг «{bad}» в тексте: {text[:120]}"
        assert "%" not in text, f"процент в тексте: {text[:120]}"
    ok(f"на {len(screens)} экранах дорожки ни балла, ни процента, ни долга")

    for text in screens:
        latin = [w for w in re.findall(r"[A-Za-z]{3,}", text)]
        assert not latin, f"латиница в тексте человеку: {latin[:5]}"
    ok("ни одного латинского слова в видимом тексте")

    for text in screens:
        low = text.lower()
        for bad in ("мало", "плохо", "запустил", "молодец", "отличн"):
            assert bad not in low, f"оценочное слово «{bad}»: {text[:120]}"
    ok("оценочных слов нет: дорожка не судья")


def check_chain_matches_between_screens() -> None:
    """13. Каталог и страница понимают дорожку одинаково.

    Самое хрупкое место цепочки — стык: каталог кладёт в очередь адреса, а
    открывает их другая страница. Разъехались бы ключ или адрес — человек попал
    бы на замер, который не считает себя шагом дорожки, и цепочка встала бы.
    Поэтому здесь очередь берётся ИЗ каталога и скармливается странице как есть.
    """
    c = cat_run("?u=tg_777&v=11&" + FILL + "&track=1", """
  tap('data-track', 'go').click();
  OUT.rec = record();
  OUT.went = went();
""")
    r = c["rec"]
    head = r["queue"][0]
    assert c["went"] == head["url"], \
        f"каталог ушёл не по адресу из очереди: {c['went']} против {head['url']}"
    assert "v=11" in head["url"], \
        f"версия страниц не доехала до дорожки: {head['url']}"
    assert "u=tg_777" in head["url"], "адрес шага дорожки без человека"
    ok("адреса очереди собраны каталогом: человек и версия страниц на месте")

    search = "?" + head["url"].split("?", 1)[1]
    got = page_run(head["key"], """
  OUT.mine = trackMine();
  startCard();
  """ + FULL[head["key"]] + """
  await finish();
  OUT.went = went();
  OUT.rec = record();
""", record=r, search=search)
    assert got["mine"] is True, \
        f"страница «{head['key']}» не узнала себя шагом дорожки"
    assert got["went"] == r["queue"][1]["url"], \
        f"после первого шага открылось: {got['went']}"
    assert len(got["rows"]) == 1, "первый шаг дорожки не записан"
    ok("страница узнала свой шаг и открыла второй адрес из той же очереди")


# ==========================================================================
# Мутации: ломаем и смотрим, покраснеет ли
# ==========================================================================
MUTATIONS: List[Tuple[str, str, str, str, str]] = [
    ("порядок стал календарным",
     CATALOG,
     "    return (a.rank - b.rank) || (b.wide - a.wide) || (a.at - b.at) ||",
     "    return (b.wide - a.wide) || (a.at - b.at) ||",
     "check_order_by_contribution"),

    ("в очередь пошли свежие замеры",
     CATALOG,
     'return c.track === true && c.url && c.state !== "fresh";',
     "return c.track === true && !!c.url;",
     "check_queue_takes_only_what_it_can"),

    ("в очередь пошли страницы без дорожки",
     CATALOG,
     "    return c.track === true && c.url",
     "    return c.url",
     "check_queue_takes_only_what_it_can"),

    ("до старта не сказано, сколько это займёт",
     CATALOG,
     "    '<div class=\"note\">' + esc(trackSizeLine(q)) + \"</div>\" +",
     '    "" +',
     "check_intro_says_count_and_caveat"),

    ("оговорка про срез и линию пропала",
     CATALOG,
     "    '<p class=\"honest\">' + esc(TRACK_HONEST) + \"</p>\" +",
     '    "" +',
     "check_intro_says_count_and_caveat"),

    ("вход в дорожку снова уходит боту",
     CATALOG,
     "  return '<div class=\"runall\"><a href=\"' + esc(href) +\n"
     "    '\" data-track=\"start\">' +",
     "  return '<div class=\"runall\"><a href=\"https://t.me/vslukh_shapovalov_bot?start=run_all\"' +\n"
     "    ' data-track=\"start\">' +",
     "check_entry_stays_in_miniapp"),

    ("дорожка не запоминается — выход её стирает",
     CATALOG,
     '  trackSave(trackNew(q, trackHref(HOME_URL, SEARCH_RAW, "done"), Date.now()));',
     '  TRACK = trackNew(q, trackHref(HOME_URL, SEARCH_RAW, "done"), Date.now());',
     "check_entry_stays_in_miniapp"),

    ("итог собирается столбиком",
     CATALOG,
     "    ? '<p class=\"stitch\">' + esc(text) + \"</p>\"",
     "    ? TRACK.done.map(function (d) {\n"
     "        return '<div class=\"stitch\">' + esc((d.lines || []).join(\" \")) + \"</div>\";\n"
     "      }).join(\"\")",
     "check_one_stitched_summary"),

    ("после замера дорожка возвращает в список",
     "state-move/app.html",
     "  trackGo(next.url);",
     "  trackGo(rec.home);",
     "check_next_opens_at_once"),

    ("слова замера в пройденное не попадают",
     "state-move/app.html",
     "  var said = resultLines(answers, flags, prevSaved) || [];",
     "  var said = [];",
     "check_next_opens_at_once"),

    ("порог усталости отодвинут за горизонт",
     "state-move/app.html",
     "var TRACK_TIRED_MIN = 20;",
     "var TRACK_TIRED_MIN = 2000;",
     "check_stop_offer_after_twenty"),

    ("предложение остановиться стало запретом",
     "state-move/app.html",
     "      '<button data-track=\"go\">Продолжить</button>' +",
     '      "" +',
     "check_stop_offer_after_twenty"),

    ("дорожка дописывает свою метку в запись",
     "state-move/app.html",
     "  var built = buildScores(answers, flags);",
     "  var built = buildScores(answers, flags);\n"
     "  if (built.has) built.scores.track = 1;",
     "check_records_unchanged"),

    ("предохранитель тяжёлого ответа выключен",
     "state-note/app.html",
     "  var heavy = trackHeavy(answers, flags, prevSaved);",
     "  var heavy = null;",
     "check_heavy_answer_stops"),

    ("порог здоровья дорожку не останавливает",
     "state-health/app.html",
     "  return healthAlert(a, prev) ? HEAVY_TEXT : null;",
     "  return null;",
     "check_heavy_answer_stops"),
]


def _one_check(name: str) -> int:
    """Прогнать одну проверку отдельным процессом. Вернуть её код выхода."""
    code = ("import lib_path\n"
            "from lib import run\n"
            "import dorozhka as C\n"
            "raise SystemExit(run([getattr(C, %r)]))\n" % name)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(CHECKS) + os.pathsep + env.get("PYTHONPATH", "")
    r = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT),
                       capture_output=True, text=True, env=env, timeout=3600)
    return r.returncode


def check_every_requirement_has_a_mutation() -> None:
    """14. У каждого требования дорожки есть поломка."""
    used = {m[4] for m in MUTATIONS}
    must = {
        "check_order_by_contribution",          # порядок по вкладу
        "check_queue_takes_only_what_it_can",   # свежие и чужие не берём
        "check_intro_says_count_and_caveat",    # число, минуты, оговорка
        "check_entry_stays_in_miniapp",         # без выходов в чат
        "check_next_opens_at_once",             # следующий сразу
        "check_stop_offer_after_twenty",        # предложение, не запрет
        "check_one_stitched_summary",           # один сшитый итог
        "check_heavy_answer_stops",             # тяжёлый ответ останавливает
        "check_records_unchanged",              # записи не изменились
    }
    missing = must - used
    assert not missing, "без мутации остались: " + ", ".join(sorted(missing))
    ok(f"{len(must)} требований закрыты мутациями")


def check_mutations_are_caught() -> None:
    """15. Каждая поломка ловится проверкой, файлы возвращаются на место."""
    before = {}
    for _, rel, *_ in MUTATIONS:
        before[rel] = (ROOT / rel).read_text(encoding="utf-8")

    caught, misses = 0, []
    for what, rel, old, new, check in MUTATIONS:
        path = ROOT / rel
        src = before[rel]
        n = src.count(old)
        assert n == 1, f"«{what}»: место мутации в {rel} встречается {n} раз"
        try:
            path.write_text(src.replace(old, new, 1), encoding="utf-8")
            rc = _one_check(check)
            if rc == 0:
                misses.append(f"{what} → {check} осталась зелёной")
            else:
                caught += 1
                print(f"  ловит  {what}  →  {check}")
        finally:
            path.write_text(src, encoding="utf-8")

    for rel, src in before.items():
        got = (ROOT / rel).read_text(encoding="utf-8")
        assert hashlib.sha256(got.encode()).digest() == \
            hashlib.sha256(src.encode()).digest(), \
            f"{rel} не вернулся к исходному состоянию"

    assert not misses, "не поймано: " + "; ".join(misses)
    ok(f"все {caught} поломок пойманы, страницы вернулись байт в байт")


if __name__ == "__main__":
    raise SystemExit(run([
        check_shared_block_is_one,
        check_order_by_contribution,
        check_queue_takes_only_what_it_can,
        check_intro_says_count_and_caveat,
        check_entry_stays_in_miniapp,
        check_next_opens_at_once,
        check_stop_offer_after_twenty,
        check_one_stitched_summary,
        check_progress_survives_exit,
        check_heavy_answer_stops,
        check_records_unchanged,
        check_texts_are_clean,
        check_chain_matches_between_screens,
        check_every_requirement_has_a_mutation,
        check_mutations_are_caught,
    ]))
