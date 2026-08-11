# -*- coding: utf-8 -*-
"""Проверки первого экрана второй двери «Как я устроен» (спека 021).

Запрос владельца 10.08.2026: на первом экране должен быть разбор из того, что
человек прошёл, — примерно как раньше делала кнопка «Паспорт целиком».

Первый экран обязан состоять из трёх вещей, строго в этом порядке:

  1. **факт** — сколько блоков пройдено из скольких и какие области видно.
     Только факты: ни оценки, ни «осталось пройти». Числа — СЛОВАМИ: «пройдено 9
     из 14» это счётчик заполнения, запрещённый в этой двери 07.08.2026, а
     «пройдено девять блоков из четырнадцати» — предложение на русском языке;
  2. **одно наблюдение** — текст приезжает от бота параметром `o=`, страница его
     не сочиняет и не толкует, показывает как есть и кончает вопросом. Не
     приехало — блока нет ВОВСЕ, и заглушки на его месте нет;
  3. **чего не хватает** — ровно один блок, без упрёка и без списка из пяти.

Полный разбор — ссылкой ниже, отдельным действием: сшивает блоки бот, у страницы
этих данных нет. Не разворот на первом экране.

Что проверяется — исполнением страницы в node с заглушками вместо браузера, сети
и Телеграма, а не поиском слов в исходнике:

  1. порядок трёх блоков: факт выше наблюдения, наблюдение выше просьбы;
  2. факт считает ровно пройденное и называет области ровно пройденных групп;
  3. в строке факта нет ни одной цифры, ни слова про прогресс — на всех
     возможных значениях от нуля до всех блоков;
  4. `o=` не приехал — блока наблюдения нет и заглушки нет;
  5. наблюдение кончается вопросом, и вопрос ровно один;
  6. ни баллов, ни названий инструментов, ни оценочных слов, ни ярлыков;
  7. даты не приехали — сказано честно, без выдуманных чисел;
  8. полный разбор — ссылка и фраза, существующая в `bot.py` буквально; не
     `<details>` и не разворот.

Плюс мутационная проверка: в страницу вносится одна точная поломка, и нужная
проверка обязана на ней покраснеть. Файл возвращается байт в байт.

Запуск:  python3 checks/pervyj_ekran_ustroen.py
"""

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import quote

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
import kak_ustroen_catalog as K
from lib import BOT, ROOT, ok, run

APP = K.APP
CHECKS = Path(__file__).resolve().parent

# Фраза полного разбора. Она же кнопка бота: человек отправляет её в чат, и бот
# собирает портрет. Проверка сверяет её с `bot.py` буквально.
FULL_PHRASE = "📋 Паспорт целиком"

# Заглушки, которых на месте отсутствующего наблюдения быть не должно. Пустая
# рамка с подписью «пока нечего сказать» хуже отсутствия блока: она сообщает
# человеку, что про него нечего сказать.
STUB_WORDS = [
    "нечего сказать", "пока ничего не заметил", "наблюдений нет",
    "наблюдения нет", "пока без наблюдений", "нет наблюдения",
]

# Слова, которыми экран не имеет права требовать догнать.
DEBT_WORDS = [
    "осталось", "должен", "надо пройти", "не хватает данных", "прогресс",
    "заполнено на", "доля",
]


def pure(extra_js: str = "") -> Dict:
    """Чистая логика страницы с добавкой под этот файл проверок."""
    return K.pure(extra_js)


PURE_JS = r"""
var NOW = "2026-08-10T00:00:00.000Z";

/** Карточки на выдуманных датах. `known === false` — даты не приехали вовсе. */
function mk(dates, known) {
  return buildCards(REGISTRY, dates || {}, NOW, known !== false);
}

OUT.total = REGISTRY.length;
OUT.seenNames = GROUP_ORDER.map(function (g) {
  return { id: g.id, seen: (g.seen === undefined ? null : g.seen) };
});
OUT.phrase = FULL_PHRASE;

// Четыре пройденных блока в трёх группах: склад, что ведёт, как решаешь.
var FOUR = { personality: "2026-06-01", values: "2026-05-01",
             motivators: "2026-05-01", ztpi: "2026-07-01" };
OUT.countFour = countPassed(mk(FOUR));
OUT.areasFour = areasSeen(mk(FOUR));
OUT.factFour = factLine(mk(FOUR), false);

// Просроченный замер — тоже пройденный: срок вышел, но человек его проходил.
OUT.countDue = countPassed(mk({ personality: "2019-01-01" }));

// Каждое возможное число пройденных: от нуля до всех.
OUT.ladder = [];
var KEYS = REGISTRY.map(function (r) { return r.key; });
for (var n = 0; n <= KEYS.length; n++) {
  var d = {};
  for (var i = 0; i < n; i++) d[KEYS[i]] = "2026-06-01";
  OUT.ladder.push({ n: n, count: countPassed(mk(d)), fact: factLine(mk(d), false) });
}

// Даты не приехали. С наблюдением и без него текст обязан быть РАЗНЫМ: сказать
// «ничего не знаю» рядом с наблюдением от бота значит соврать в минус.
OUT.unknownNoObs = factLine(mk({}, false), false);
OUT.unknownObs = factLine(mk({}, false), true);

// Вопрос в конце наблюдения.
OUT.q = {
  plain: obsQuestion("Ты уже рассказал про склад"),
  asked: obsQuestion("а насколько это про тебя?"),
  empty: obsQuestion("")
};

// Ссылка на полный разбор: сшивать нечего — ссылки нет.
OUT.full = {
  nothing: showFullReport(mk({}, false), null),
  obsOnly: showFullReport(mk({}, false), "текст от бота"),
  passed: showFullReport(mk(FOUR), null)
};
"""


def logic() -> Dict:
    return pure(PURE_JS)


OBS = "Ты уже рассказал про склад и про то, что тебя ведёт"


def rich(obs: str = OBS, ask: str = "motivators",
         f: str = "personality:2026-06-01,values:2026-05-01") -> str:
    """Адрес живого случая: даты приехали, наблюдение приехало, просьба есть."""
    q = "?u=tg_777"
    if f:
        q += "&f=" + f
    if ask:
        q += "&ask=" + ask
    if obs:
        q += "&o=" + quote(obs)
    return q


# --------------------------------------------------------------------------
# Проверки
# --------------------------------------------------------------------------
def check_poryadok_treh_blokov() -> None:
    """1. Три блока в жёстком порядке: факт → наблюдение → чего не хватает."""
    text = K.seen(rich())

    fact = "Пройдено два блока из четырнадцати"
    i_fact = text.find(fact)
    assert i_fact >= 0, f"первый экран не говорит факт «{fact}»"
    i_obs = text.find(OBS)
    assert i_obs >= 0, "наблюдение от бота не показано вовсе"
    i_ask = text.find("не хватает одного")
    assert i_ask >= 0, "просьбы нет, хотя ключ приехал параметром"

    assert i_fact < i_obs, "наблюдение стоит выше факта: экран говорит про меня " \
        "раньше, чем говорит, что вообще знает"
    assert i_obs < i_ask, "просьба стоит выше наблюдения: сначала просим, потом даём"
    ok("факт выше наблюдения, наблюдение выше просьбы")

    # Полный разбор — ниже трёх блоков и отдельным действием.
    i_full = text.find("Полный разбор")
    assert i_full > i_ask, "полный разбор стоит выше просьбы"
    i_all = text.find("Посмотреть всё")
    assert 0 < i_full < i_all, "полный разбор стоит ниже полного списка"
    ok("полный разбор ниже трёх блоков и выше списка")

    # Факт стоит первым на экране: между заголовком и фактом ничего нет.
    head = text.find("Как я устроен")
    assert 0 <= head < i_fact, "заголовок не на месте"
    between = text[head + len("Как я устроен"):i_fact].strip()
    assert len(between) < 40, \
        f"между заголовком и фактом влез посторонний текст: «{between[:80]}»"
    ok("факт — первое, что человек читает")


def check_fakt_schitaet_prohozhdennoe() -> None:
    """2. Факт считает ровно пройденное и называет ровно пройденные области."""
    c = logic()

    assert c["countFour"] == 4, \
        f"пройдено четыре блока, а посчитано {c['countFour']}"
    assert c["countDue"] == 1, \
        "просроченный замер не считается пройденным, хотя человек его проходил"
    ok("пройденное считается по датам, просроченное тоже пройдено")

    for g in c["seenNames"]:
        assert g["seen"], f"у группы «{g['id']}» нет названия области для строки факта"
    ok(f"у всех {len(c['seenNames'])} групп есть название области")

    want = [g["seen"] for g in c["seenNames"]
            if g["id"] in ("sklad", "vedet", "reshaesh")]
    assert c["areasFour"] == want, \
        f"области: {c['areasFour']} вместо {want}"
    ok("названы области ровно тех групп, где есть пройденный блок")

    fact = c["factFour"]
    assert "четыре блока" in fact["main"], \
        f"строка факта не называет число пройденных: «{fact['main']}»"
    assert "из четырнадцати" in fact["main"], \
        f"строка факта не называет общее число: «{fact['main']}»"
    assert fact["extra"] and "Видно" in fact["extra"], \
        f"строка факта не называет области: «{fact['extra']}»"
    ok("факт называет число пройденных, общее число и области")

    # Сверка ДОСЛОВНАЯ, а не «начинается с»: «Пройден один блоков» тоже
    # начинается с «Пройден один блок», и такая проверка пропустила бы поломку.
    forms = {r["n"]: r["fact"]["main"] for r in c["ladder"]}
    assert "ни одного блока" in forms[0], \
        f"нуль пройденных сказан не фактом: «{forms[0]}»"
    want = {
        1: "Пройден один блок из четырнадцати.",
        2: "Пройдено два блока из четырнадцати.",
        5: "Пройдено пять блоков из четырнадцати.",
        11: "Пройдено одиннадцать блоков из четырнадцати.",
        14: "Пройдено четырнадцать блоков из четырнадцати.",
    }
    for n, phrase in want.items():
        assert forms[n] == phrase, \
            f"согласование при {n}: «{forms[n]}» вместо «{phrase}»"
    ok("согласование числительных верное на 0, 1, 2, 5, 11 и 14")

    for r in c["ladder"]:
        assert r["count"] == r["n"], \
            f"пройдено {r['n']}, а посчитано {r['count']}"
    ok(f"счёт сходится на всех значениях от 0 до {c['total']}")

    # На экране то же число, что в логике.
    text = K.seen("?u=tg_777&f=personality:2026-06-01,values:2026-05-01")
    assert "Пройдено два блока из четырнадцати" in text, \
        "на экране не то число пройденных, что в логике"
    ok("на экране то же, что в логике")


def check_fakt_slovami_bez_cifr() -> None:
    """3. В строке факта нет ни одной цифры и ни слова про долг."""
    c = logic()
    for r in c["ladder"]:
        for part in (r["fact"]["main"], r["fact"]["extra"] or ""):
            assert not re.search(r"\d", part), \
                f"при {r['n']} пройденных в строке факта цифра: «{part}»"
            low = part.lower()
            for bad in DEBT_WORDS:
                assert bad not in low, \
                    f"при {r['n']} пройденных в строке факта долг «{bad}»: «{part}»"
    ok(f"на всех {len(c['ladder'])} значениях — слова, а не цифры, и ни слова о долге")

    for part in (c["unknownNoObs"], c["unknownObs"]):
        assert not re.search(r"\d", part["main"]), \
            f"когда дат нет, в строке факта цифра: «{part['main']}»"
    ok("при пустых датах цифр тоже нет")

    text = K.seen(rich())
    assert not re.search(r"\d+\s*(из|/)\s*\d+", text), \
        "на экране счётчик вида «N из M» цифрами"
    low = text.lower()
    for bad in ("осталось пройти", "прогресс", "заполнено на", "очк"):
        assert bad not in low, f"на экране геймификация: «{bad}»"
    ok("на экране ни дроби, ни прогресса")


def check_net_nablyudeniya_net_bloka() -> None:
    """4. `o=` не приехал — блока наблюдения нет, и заглушки нет."""
    c = logic()
    question = c["q"]["plain"]
    assert question, "у страницы нет вопроса, которым кончается наблюдение"

    with_obs = K.seen(rich())
    assert OBS in with_obs, "наблюдение не показано, хотя приехало"
    head = "Одно наблюдение"
    assert head in with_obs, f"у блока наблюдения нет подписи «{head}»"
    ok("наблюдение приехало — блок есть")

    for search in ("?u=tg_777&f=personality:2026-06-01&ask=values",
                   "?u=tg_777&o=" + quote("   ") + "&ask=values",
                   "?u=tg_777"):
        text = K.seen(search)
        assert head not in text, \
            f"наблюдения нет, а подпись блока есть: {search}"
        assert question not in text, \
            f"наблюдения нет, а вопрос страницы есть: {search}"
        low = text.lower()
        for bad in STUB_WORDS:
            assert bad not in low, f"на месте наблюдения заглушка «{bad}»: {search}"
    ok("нет наблюдения — нет ни блока, ни заглушки, ни вопроса")


def check_nablyudenie_konchaetsya_voprosom() -> None:
    """5. Наблюдение кончается вопросом, и вопрос ровно один."""
    c = logic()
    q = c["q"]
    assert q["plain"], "к наблюдению без вопроса свой вопрос не добавлен"
    assert q["plain"].strip().endswith("?"), \
        f"вопрос страницы не вопрос: «{q['plain']}»"
    assert q["asked"] is None, \
        "текст бота уже кончался вопросом, а страница добавила второй"
    assert q["empty"] is None, "вопрос предложен к пустому наблюдению"
    ok("вопрос добавляется только там, где его нет")

    text = K.seen(rich())
    i_obs = text.find(OBS)
    i_q = text.find(q["plain"])
    assert i_q > i_obs >= 0, "вопрос стоит не после наблюдения"
    ok("на экране вопрос стоит сразу после наблюдения")

    asked = "Похоже, тут связь между складом и давлением — насколько это про тебя?"
    text2 = K.seen(rich(obs=asked))
    assert asked in text2, "наблюдение с вопросом не показано"
    assert q["plain"] not in text2, \
        "у наблюдения, которое само кончалось вопросом, появился второй вопрос"
    ok("двух вопросов подряд не бывает")


def check_bez_ballov_i_ocenok() -> None:
    """6. Ни баллов, ни названий инструментов, ни оценок, ни ярлыков."""
    text = K.seen(rich())
    low = text.lower()

    latin = sorted(set(K.LATIN.findall(text)))
    assert not latin, f"в видимом тексте латиница: {latin[:8]}"
    for bad in K.AUTHORS:
        assert bad.lower() not in low, f"на экране фамилия автора: «{bad}»"
    for bad in K.SCORE_WORDS:
        assert bad.lower() not in low, f"на экране слово про балл или шкалу: «{bad}»"
    for bad in K.LABEL_WORDS:
        assert bad.lower() not in low, f"на экране ярлык о характере: «{bad}»"
    for bad in K.GAME_WORDS:
        assert bad.lower() not in low, f"на экране геймификация: «{bad}»"
    ok("на первом экране ни балла, ни шкалы, ни ярлыка")

    assert "undefined" not in text and "NaN" not in text, \
        "в собранной странице есть undefined или NaN — где-то пустое поле"
    ok("пустых полей нет")

    # Оценочных слов нет и в строках факта — на всех значениях сразу.
    c = logic()
    bad_words = ["мало", "плохо", "хорошо", "слабо", "высок", "низк", "молодец"]
    for r in c["ladder"]:
        joined = (r["fact"]["main"] + " " + (r["fact"]["extra"] or "")).lower()
        for bad in bad_words:
            assert bad not in joined, \
                f"при {r['n']} пройденных оценка «{bad}»: «{joined}»"
    ok("в строке факта нет оценочных слов ни на одном значении")


def check_chestno_pri_pustyh_datah() -> None:
    """7. Даты не приехали — сказано честно, без выдуманных чисел."""
    c = logic()
    honest = "Про то, как ты устроен, я пока ничего не знаю."
    assert c["unknownNoObs"]["main"] == honest, \
        f"без дат и без наблюдения сказано не честно: «{c['unknownNoObs']['main']}»"
    reason = c["unknownObs"]["main"]
    assert reason != honest, \
        "рядом с наблюдением экран говорит «ничего не знаю» — это вранье в минус"
    assert "даты" in reason.lower(), \
        f"причина не названа: «{reason}»"
    ok("два разных честных текста: с наблюдением и без")

    text = K.seen("?u=tg_777")
    assert honest in text, "экран молчит вместо честной строки про то, что данных нет"
    for bad in ("Пройдено ", "Пройден ", "ни одного блока"):
        assert bad not in text, \
            f"дат нет, а экран называет число пройденных: «{bad}»"
    ok("без дат числа не выдумываются")

    with_obs = K.seen("?u=tg_777&o=" + quote(OBS))
    assert honest not in with_obs, \
        "рядом с наблюдением на экране «ничего не знаю»"
    assert reason in with_obs, f"на экране нет причины: «{reason}»"
    ok("с наблюдением экран называет причину, а не молчание")


def check_polnyj_razbor_ssylkoj() -> None:
    """8. Полный разбор — ссылка и фраза боту, а не разворот на экране."""
    c = logic()
    assert c["phrase"] == FULL_PHRASE, \
        f"фраза полного разбора: «{c['phrase']}» вместо «{FULL_PHRASE}»"
    bot_text = BOT.read_text(encoding="utf-8")
    assert f'"{c["phrase"]}"' in bot_text, \
        f"фразы «{c['phrase']}» нет в bot.py — человек отправит её зря"
    ok("фраза полного разбора существует в боте буквально")

    assert c["full"]["passed"] is True, \
        "блоки пройдены, а ссылки на полный разбор нет"
    assert c["full"]["obsOnly"] is True, \
        "наблюдение приехало, значит боту есть что сшить, а ссылки нет"
    assert c["full"]["nothing"] is False, \
        "сшивать нечего, а полный разбор всё равно предложен"
    ok("ссылка появляется только там, где есть что сшивать")

    raw = K.render(rich())
    i_full = raw.find("Полный разбор")
    i_det = raw.find("<details")
    assert i_full >= 0, "на экране нет полного разбора"
    assert 0 <= i_full < i_det, \
        "полный разбор оказался внутри разворота: на первом экране он ссылка"
    assert FULL_PHRASE in raw, "фразы полного разбора нет на экране"
    assert 'data-tglink="https://t.me/' in raw, \
        "полный разбор не ведёт в переписку с ботом"
    ok("полный разбор — ссылка и фраза, не разворот")

    empty = K.seen("?u=tg_777")
    assert "Полный разбор" not in empty, \
        "ничего не известно, а полный разбор предложен"
    ok("нечего сшивать — ссылки нет")


# --------------------------------------------------------------------------
# Мутации: ломаем страницу и смотрим, покраснеет ли нужная проверка
# --------------------------------------------------------------------------
# (что ломаем · было · стало · какая проверка обязана покраснеть)
MUTATIONS: List[Tuple[str, str, str, str]] = [
    ("наблюдение встало выше факта",
     "  give += factHtml(cards, !!obs);\n  if (obs) give += obsHtml(obs);",
     "  if (obs) give += obsHtml(obs);\n  give += factHtml(cards, !!obs);",
     "check_poryadok_treh_blokov"),

    ("счёт пройденных врёт",
     "(cards || []).forEach(function (c) { if (isPassed(c)) n += 1; });",
     "(cards || []).forEach(function (c) { n += 1; });",
     "check_fakt_schitaet_prohozhdennoe"),

    ("названы области, которых человек не проходил",
     "      if (isPassed(c) && c.group === g.id) any = true;",
     "      if (c.group === g.id) any = true;",
     "check_fakt_schitaet_prohozhdennoe"),

    ("согласование числительных сломано",
     '  if (d10 === 1 && d100 !== 11) return "блок";',
     '  if (false) return "блок";',
     "check_fakt_schitaet_prohozhdennoe"),

    ("в строке факта вместо слов цифры",
     '  return (typeof n === "number" && n >= 0 && n < list.length) ? list[n] : null;',
     "  return String(n);",
     "check_fakt_slovami_bez_cifr"),

    ("на месте отсутствующего наблюдения появилась заглушка",
     "  if (obs) give += obsHtml(obs);",
     "  give += obs ? obsHtml(obs) : '<div class=\"obs\">"
     "<div class=\"obs-head\">Одно наблюдение</div>"
     "<div class=\"obs-text\">Пока нечего сказать.</div></div>';",
     "check_net_nablyudeniya_net_bloka"),

    ("наблюдение перестало кончаться вопросом",
     "  if (endsWithQuestion(s)) return null;\n  return OBS_QUESTION;",
     "  return null;",
     "check_nablyudenie_konchaetsya_voprosom"),

    ("к вопросу бота приклеился второй вопрос",
     'function endsWithQuestion(s) {\n  return /\\?[»"\')\\s]*$/'
     '.test(String(s == null ? "" : s));',
     "function endsWithQuestion(s) {\n  return false;",
     "check_nablyudenie_konchaetsya_voprosom"),

    ("рядом с наблюдением экран говорит «ничего не знаю»",
     "    return { known: false, main: hasObs ? HONEST_NO_DATES : HONEST_UNKNOWN,",
     "    return { known: false, main: HONEST_UNKNOWN,",
     "check_chestno_pri_pustyh_datah"),

    ("дат нет, а экран называет число пройденных",
     "  if (!datesKnown(list)) {",
     "  if (false) {",
     "check_chestno_pri_pustyh_datah"),

    # Место мутации пересняли 11.08.2026: спека 025 добавила отправку одним
    # нажатием, и сборка блока переехала из `return` в переменную `head`.
    # Утверждение не изменилось: полный разбор остаётся отдельным шагом-ссылкой,
    # а не разворотом прямо на первом экране.
    ("полный разбор стал разворотом на первом экране",
     "  var head = '<div class=\"full\">' +",
     "  var head = '<details class=\"full\"><summary>Полный разбор</summary>' +",
     "check_polnyj_razbor_ssylkoj"),

    ("фраза полного разбора разошлась с ботом",
     'var FULL_PHRASE = "📋 Паспорт целиком";',
     'var FULL_PHRASE = "📋 Паспорт полностью";',
     "check_polnyj_razbor_ssylkoj"),

    ("полный разбор предложен, когда сшивать нечего",
     "function showFullReport(cards, obs) {\n  if (obs) return true;\n"
     "  return countPassed(cards) > 0;",
     "function showFullReport(cards, obs) {\n  return true;",
     "check_polnyj_razbor_ssylkoj"),

    ("на первый экран вернулось название инструмента",
     'var OBS_QUESTION = "Насколько это про тебя?";',
     'var OBS_QUESTION = "Насколько это похоже на твой профиль по шкале ECR-R?";',
     "check_bez_ballov_i_ocenok"),

    ("в строке факта появилась оценка",
     '    main = "Пока не пройдено ни одного блока из " + totalWord + ".";',
     '    main = "Пока пройдено мало: ни одного блока из " + totalWord + ".";',
     "check_bez_ballov_i_ocenok"),
]

# У каждой проверки — своя поломка. Без этого список мутаций незаметно съезжает
# в «поломали то, что легче ломается».
MUST_MUTATE = {
    "check_poryadok_treh_blokov",
    "check_fakt_schitaet_prohozhdennoe",
    "check_fakt_slovami_bez_cifr",
    "check_net_nablyudeniya_net_bloka",
    "check_nablyudenie_konchaetsya_voprosom",
    "check_bez_ballov_i_ocenok",
    "check_chestno_pri_pustyh_datah",
    "check_polnyj_razbor_ssylkoj",
}


def _one_check(name: str) -> int:
    """Прогнать одну проверку отдельным процессом. Вернуть её код выхода."""
    code = (
        "import lib_path\n"
        "from lib import run\n"
        "import pervyj_ekran_ustroen as C\n"
        "raise SystemExit(run([getattr(C, %r)]))\n" % name
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(CHECKS) + os.pathsep + env.get("PYTHONPATH", "")
    r = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT),
                       capture_output=True, text=True, env=env, timeout=1800)
    return r.returncode


def check_u_kazhdoj_proverki_est_mutaciya() -> None:
    """9. У каждой проверки есть поломка, на которой она краснеет."""
    used = {m[3] for m in MUTATIONS}
    missing = MUST_MUTATE - used
    assert not missing, "без мутации остались: " + ", ".join(sorted(missing))
    ok(f"{len(MUST_MUTATE)} проверок закрыты мутациями")


def check_polomki_lovyatsya() -> None:
    """10. Каждая поломка ловится, и страница возвращается байт в байт."""
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
    ok(f"все {caught} поломок из {len(MUTATIONS)} пойманы, страница на месте")


CHECKS_ALL = [
    check_poryadok_treh_blokov,
    check_fakt_schitaet_prohozhdennoe,
    check_fakt_slovami_bez_cifr,
    check_net_nablyudeniya_net_bloka,
    check_nablyudenie_konchaetsya_voprosom,
    check_bez_ballov_i_ocenok,
    check_chestno_pri_pustyh_datah,
    check_polnyj_razbor_ssylkoj,
]

if __name__ == "__main__":
    only = sys.argv[1:] and sys.argv[1] == "--bez-mutacij"
    fns = CHECKS_ALL if only else CHECKS_ALL + [
        check_u_kazhdoj_proverki_est_mutaciya,
        check_polomki_lovyatsya,
    ]
    raise SystemExit(run(fns))
