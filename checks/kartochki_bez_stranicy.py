# -*- coding: utf-8 -*-
"""Проверки: карточка без своей страницы честно говорит, что будет при нажатии.

Спека 020, Истории 1 и 2.

Живой дефект, 10.08.2026. Владелец нажал в каталоге «Нагрузка по дому» —
мини-апп закрылся, внизу развернулась клавиатура бота, никакой диагностики он не
получил и не понял, что произошло.

Причина. У семи карточек нет адреса страницы: `pair_state`, `pair_detector`,
`pair_are`, `pair_load`, `pair_context`, `forum_scales`, `labs`. Нажатие
отправляет боту просьбу открыть разговор, а `sendData` закрывает мини-апп — так
устроен Телеграм. Карточка об этом молчала: строка «идёт разговором — нажми, бот
начнёт сам» не говорила ни про закрытие экрана, ни про то, что для парного замера
нужен второй человек.

Плюс `body_form`: у неё нет ни адреса, ни фразы — она запускается сразу после
квартального замера, но в списке стоит рядом с остальными и выглядит кнопкой.

Что проверяется:
  · у каждой карточки без страницы есть строка про переписку с ботом и про то,
    что мини-апп закроется;
  · парные и групповые говорят, что нужен второй человек; анализы — что нужен
    PDF и вопросов нет;
  · у карточек со своей страницей предупреждения нет: там ничего не закрывается;
  · текст короткий, без баллов, без названий шкал и без оценочных слов;
  · `body_form` не притворяется кнопкой: сказано, после какого замера она
    открывается, и по разметке видно, что это не ссылка;
  · запасной путь «скопировать фразу» на месте — его ломать нельзя;
  · поломки ловятся: каждое требование закрыто мутацией.

Проверки исполняют страницу в node с заглушками и смотрят на СОБРАННЫЙ экран, а
не ищут слова в исходнике: ошибку шаблона разбором текста не поймать.

Запуск:  python3 checks/kartochki_bez_stranicy.py
"""

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
from chto_so_mnoy import FRESH, OBS, link, obs, screens
from lib import ROOT, bot, catalog, catalog_render, catalog_taps, ok, run, visible

CHECKS = Path(__file__).resolve().parent
APP = "kak-ty/app.html"

# Семь карточек без своей страницы. Ключи — из CARD_META бота.
NO_PAGE: List[str] = ["pair_state", "pair_detector", "pair_are", "pair_load",
                      "pair_context", "forum_scales", "labs"]

# Что нужно принести. Закрытый список: новое значение обязано появиться и здесь,
# иначе карточка молча останется без строки про второго человека.
NEEDS = {"pair", "group", "labs"}

# Кому какое значение положено. Группа берётся из самого реестра.
NEED_BY_GROUP = {"Пара": "pair", "Группа": "group"}

# Карточка, которая запускается следом за другим замером, а не своей кнопкой.
AFTER_CARD = "body_form"

# Два факта, которые обязаны быть в предупреждении. Первый — где пойдёт замер,
# второй — что случится с экраном. Без второго человек снова не поймёт, что его
# «выбросило»: он и есть тот самый дефект.
MUST_SAY = ["переписке с ботом", "закроется"]

# Слова, которых в предупреждении быть не может. Оценки — правила мини-аппов,
# часть 4; баллы и шкалы — конституция, принципы III и IV.
BAD_WORDS = ["балл", "балла", "баллов", "индекс", "процент", "мало", "много",
             "плохо", "хорошо", "запустил", "должен", "лень", "провалил",
             "забросил", "PHQ", "GAD", "UCLA", "AUDIT", "ASRM"]

# Правила текста: фраза длиннее двенадцати слов режется пополам.
MAX_WORDS = 12


def warns() -> Dict[str, str]:
    """Строка предупреждения по каждой карточке — из чистой логики."""
    c = catalog("""
OUT.warn = {};
OUT.need = {};
REGISTRY.forEach(function (r) {
  OUT.warn[r.key] = chatWarn(r);
  OUT.need[r.key] = r.need || null;
});
OUT.groups = {};
REGISTRY.forEach(function (r) { OUT.groups[r.key] = r.group; });
OUT.urls = {};
REGISTRY.forEach(function (r) { OUT.urls[r.key] = r.url || null; });
OUT.labels = {};
REGISTRY.forEach(function (r) { OUT.labels[r.key] = r.label; });
""")
    return c


def card_markup(rest: str, label: str) -> str:
    """Разметка одной карточки списка целиком, по её названию.

    Границы — от своего тега до начала следующей карточки: внутри карточки
    закрывающих тегов сколько угодно, и по ним резать нельзя.
    """
    i = rest.index('class="card-name">' + label + "</div>")
    start = rest.rindex('<div class="card', 0, i)
    ends = [x for x in (rest.find('<div class="card"', i),
                        rest.find("</details>", i)) if x > 0]
    return rest[start:min(ends)] if ends else rest[start:]


def sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


# --------------------------------------------------------------------------


def check_warning_says_two_facts() -> None:
    """1. Карточка без страницы говорит: замер в переписке, экран закроется."""
    c = warns()
    for key in NO_PAGE:
        w = c["warn"][key]
        assert w, f"у карточки «{key}» нет строки про то, что будет при нажатии"
        for part in MUST_SAY:
            assert part in w, f"у «{key}» в предупреждении нет «{part}»: {w!r}"
    ok(f"все {len(NO_PAGE)} карточки говорят про переписку и про закрытие экрана")

    # То же на собранном экране: человек читает его, а не чистую логику.
    _, rest = screens(link(FRESH))
    text = visible(rest)
    for key in NO_PAGE:
        card = card_markup(rest, c["labels"][key])
        seen = visible(card)
        for part in MUST_SAY:
            assert part in seen, \
                f"на карточке «{c['labels'][key]}» в списке нет «{part}»"
    assert text.count("переписке с ботом") >= len(NO_PAGE), \
        "предупреждение доехало не до всех карточек списка"
    ok("предупреждение видно на каждой карточке в списке")


def check_need_second_person() -> None:
    """2. Парные и групповые говорят про второго человека, анализы — про PDF."""
    c = warns()
    for key in NO_PAGE:
        need = c["need"][key]
        assert need in NEEDS, f"у «{key}» непонятное значение need: {need!r}"
        want = NEED_BY_GROUP.get(c["groups"][key])
        if want:
            assert need == want, \
                f"«{key}» из группы «{c['groups'][key]}», а need у неё «{need}»"
    ok("у всех семи карточек есть признак «что нужно принести»")

    for key in ["pair_state", "pair_detector", "pair_are", "pair_load",
                "pair_context"]:
        w = c["warn"][key]
        assert "второй человек" in w, \
            f"парный замер «{key}» не говорит, что нужен второй человек: {w!r}"
    ok("пять парных замеров говорят: нужен второй человек")

    g = c["warn"]["forum_scales"]
    assert "группа" in g.lower(), f"групповой замер не говорит про группу: {g!r}"
    assert "одиночку" in g or "второй" in g, \
        f"групповой замер не говорит, что в одиночку он не про то: {g!r}"
    ok("групповой замер говорит: нужна группа")

    labs = c["warn"]["labs"]
    assert "PDF" in labs, f"анализы не говорят про PDF: {labs!r}"
    # «Вопросов нет» стоит строкой честной длины, а не повторяется в
    # предупреждении: два раза подряд одно и то же — шум. Требование от этого не
    # слабеет, поэтому смотрим карточку целиком, как её читает человек.
    _, rest = screens(link(FRESH))
    card = visible(card_markup(rest, c["labels"]["labs"]))
    assert "PDF" in card and "вопросов нет" in card, \
        f"на карточке анализов не сказано про PDF и что вопросов нет: {card}"
    ok("анализы говорят: нужен PDF, вопросов нет")

    # Признак стоит только там, где есть чем его показать: у карточки со
    # страницей он был бы мёртвым полем, которое однажды разъедется с текстом.
    for key, need in c["need"].items():
        if need is None:
            continue
        assert key in NO_PAGE, f"признак need у «{key}», а у неё есть своя страница"
    ok("признака need нет ни у одной карточки со страницей")


def check_page_cards_have_no_warning() -> None:
    """3. У карточки со своей страницей предупреждения нет."""
    c = warns()
    for key, url in c["urls"].items():
        if not url:
            continue
        assert c["warn"][key] == "", \
            f"у «{key}» есть страница, а карточка обещает переписку: {c['warn'][key]!r}"
    ok("ни одна карточка со страницей не обещает закрытие экрана")

    _, rest = screens(link(FRESH))
    for key in ["state_day", "state_week", "state_move", "state_domains"]:
        card = card_markup(rest, c["labels"][key])
        assert "переписке с ботом" not in visible(card), \
            f"на карточке «{c['labels'][key]}» появилось предупреждение про чат"
    ok("на карточках со страницами предупреждения нет")


def check_warning_text_is_clean() -> None:
    """4. Текст короткий, без баллов, без шкал и без оценочных слов."""
    c = warns()
    for key in NO_PAGE + [AFTER_CARD]:
        w = c["warn"][key]
        low = w.lower()
        for bad in BAD_WORDS:
            assert bad.lower() not in low, \
                f"в предупреждении «{key}» слово «{bad}»: {w!r}"
        for s in sentences(w):
            n = len(re.findall(r"[0-9A-Za-zА-Яа-яЁё]+", s))
            assert n <= MAX_WORDS, \
                f"фраза в «{key}» из {n} слов — правила требуют резать: {s!r}"
    ok(f"текст без баллов и оценок, фразы короче {MAX_WORDS + 1} слов")

    # Предупреждение — про то, что произойдёт, а не про человека.
    whole = visible(catalog_render(link(FRESH, obs(OBS), "ask=pair_load")))
    assert "undefined" not in whole and "NaN" not in whole, \
        "на собранном экране есть undefined или NaN"
    ok("экран с предупреждением собирается без дыр")


def check_ask_card_keeps_backup_path() -> None:
    """5. На карточке просьбы предупреждение есть, а запасной путь цел."""
    first, _ = screens(link(FRESH, obs(OBS), "ask=pair_load"))
    seen = visible(first)
    for part in MUST_SAY + ["второй человек"]:
        assert part in seen, f"на карточке просьбы нет «{part}»"
    ok("карточка просьбы предупреждает так же, как карточка списка")

    # Запасной путь: фраза, кнопка копирования и подсказка, что делать, если
    # ничего не произошло. Его держит `dialog_cards_send_data.py`, здесь — что он
    # не потерялся вместе с новой строкой.
    assert "⚖️ Нагрузка" in seen, "фраза для чата исчезла с карточки просьбы"
    assert "Скопировать фразу" in seen, "кнопка «Скопировать фразу» исчезла"
    assert "скопируй фразу и отправь её в чат" in seen, \
        "подсказка про запасной путь исчезла"
    ok("фраза, кнопка копирования и подсказка на месте")

    # Подсказка одна: она длинная, и повторять её на каждой карточке — шум.
    whole = visible(catalog_render(link(FRESH, obs(OBS), "ask=pair_load")))
    assert whole.count("скопируй фразу и отправь её в чат") == 1, \
        "подробная подсказка повторяется — в списке должна быть одна строка"
    ok("подробная подсказка только у просьбы")

    # Нажатие по-прежнему открывает разговор, а не тишину.
    c = catalog_taps(link(FRESH, obs(OBS), "ask=pair_load"), """
  var el = tap('data-send', 'pair_load');
  OUT.tap = el.click();
""")
    assert c["calls"]["sent"] == ['{"action":"open_card","card":"pair_load"}'], \
        f"нажатие карточки больше не открывает замер: {c['calls']['sent']}"
    ok("нажатие по-прежнему отправляет боту просьбу открыть замер")


def check_body_form_is_not_a_button() -> None:
    """6. `body_form` не притворяется кнопкой и называет свой замер."""
    c = warns()
    w = c["warn"][AFTER_CARD]
    assert w, "у «Физической формы» нет строки про то, как она открывается"
    assert "после замера" in w, f"не сказано, после чего она открывается: {w!r}"

    # Имя замера берётся из реестра, а не вписывается вторым разом: разъехались
    # бы на первой же правке названия.
    after = catalog("OUT.after = REGISTRY.filter(function (r) { return r.after; })\n"
                    "  .map(function (r) { return { key: r.key, after: r.after }; });\n")
    keys = {x["key"]: x["after"] for x in after["after"]}
    assert keys == {AFTER_CARD: "state_quarter"}, \
        f"поле after поехало: {keys}"
    assert c["labels"]["state_quarter"] in w, \
        f"в строке нет названия квартального замера: {w!r}"
    ok("сказано: открывается сразу после «" + c["labels"]["state_quarter"] + "»")

    _, rest = screens(link(FRESH))
    card = card_markup(rest, c["labels"][AFTER_CARD])
    assert "после замера" in visible(card), \
        "на карточке «Физической формы» в списке нет строки про порядок"
    # Не ссылка и не отправка боту: по разметке, а не только по тексту.
    assert "<a " not in card, "карточка «Физической формы» стала ссылкой"
    assert "data-send" not in card, \
        "карточка «Физической формы» отправляет боту просьбу открыть разговор"
    assert 'class="card-noopen"' in card, \
        "у карточки нет своего класса — она выглядит как обычная кнопка"
    ok("карточка не ссылка, ничего не отправляет и помечена своим классом")


def check_keys_still_match_bot() -> None:
    """7. Ключи карточек по-прежнему сходятся с реестром бота."""
    meta = bot()["CARD_META"]
    c = warns()
    for key in NO_PAGE + [AFTER_CARD]:
        assert key in meta, f"ключа «{key}» нет в CARD_META бота"
    for key in NO_PAGE:
        assert not c["urls"][key], \
            f"«{key}» получила страницу — этой работой её не делали"
    ok("семь карточек без страницы и «Физическая форма» сходятся с ботом")


# --------------------------------------------------------------------------
# Мутации: ломаем правку и смотрим, покраснеет ли проверка
# --------------------------------------------------------------------------
# Конституция, принцип II: проверка обязана падать при сломанной логике.
# (что ломаем · было · стало · какая проверка обязана покраснеть)
MUTATIONS: List[Tuple[str, str, str, str]] = [
    ("предупреждение не говорит, что экран закроется",
     'var CHAT_OPENS = "Замер идёт в переписке с ботом: нажмёшь — мини-апп закроется.";',
     'var CHAT_OPENS = "Замер идёт в переписке с ботом.";',
     "check_warning_says_two_facts"),

    ("строка предупреждения исчезла из списка",
     '  if (chatLink && inList) {\n'
     '    chat = \'<div class="chat-line">\' + esc(chatWarn(card)) + "</div>";',
     '  if (chatLink && inList) {\n    chat = "";',
     "check_warning_says_two_facts"),

    ("парная карточка потеряла признак «нужен второй»",
     '    size: "3 вопроса",\n    need: "pair",',
     '    size: "3 вопроса",',
     "check_need_second_person"),

    ("предупреждение уехало и на карточки со своими страницами",
     '  if (card.url || !card.phrase) return "";',
     '  if (!card.phrase && !card.url) return "";',
     "check_page_cards_have_no_warning"),

    ("в предупреждение попало оценочное слово",
     'labs: "Нужен PDF анализов: пришлёшь файл — бот прочитает его сам."',
     'labs: "Нужен PDF анализов: файла мало, пришли ещё."',
     "check_warning_text_is_clean"),

    ("«Физическая форма» перестала отличаться от обычной кнопки",
     '    openable = \'<div class="card-noopen">\' + head + "</div>";',
     '    openable = "<div>" + head + "</div>";',
     "check_body_form_is_not_a_button"),

    ("название квартального замера вписано руками, а не взято из реестра",
     '"Своей кнопки нет: открывается сразу после замера «" + labelOf(card.after) + "»."',
     '"Своей кнопки нет: открывается сразу после квартального замера."',
     "check_body_form_is_not_a_button"),
]

MUST_COVER = {
    "check_warning_says_two_facts",
    "check_need_second_person",
    "check_page_cards_have_no_warning",
    "check_warning_text_is_clean",
    "check_body_form_is_not_a_button",
}


def _one_check(name: str) -> int:
    """Прогнать одну проверку отдельным процессом: мутация живёт на диске."""
    code = ("import lib_path\n"
            "from lib import run\n"
            "import kartochki_bez_stranicy as C\n"
            "raise SystemExit(run([getattr(C, %r)]))\n" % name)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(CHECKS) + os.pathsep + env.get("PYTHONPATH", "")
    r = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT), env=env,
                       capture_output=True, text=True, timeout=1800)
    return r.returncode


def check_every_requirement_has_a_mutation() -> None:
    """8. У каждого требования приёмки есть хотя бы одна поломка."""
    used = {m[3] for m in MUTATIONS}
    missing = MUST_COVER - used
    assert not missing, "без мутации остались: " + ", ".join(sorted(missing))
    ok(f"{len(MUST_COVER)} требований закрыты мутациями")


def check_mutations_are_caught() -> None:
    """9. Каждая поломка ловится проверкой, и страница возвращается на место."""
    path = ROOT / APP
    src = path.read_text(encoding="utf-8")
    before = hashlib.sha256(src.encode()).digest()

    caught, misses = 0, []
    for what, old, new, name in MUTATIONS:
        n = src.count(old)
        assert n == 1, f"«{what}»: место поломки встречается {n} раз"
        try:
            path.write_text(src.replace(old, new, 1), encoding="utf-8")
            if _one_check(name) == 0:
                misses.append(f"{what} → {name} осталась зелёной")
            else:
                caught += 1
                print(f"  ловит  {what}  →  {name}")
        finally:
            path.write_text(src, encoding="utf-8")

    got = hashlib.sha256(path.read_text(encoding="utf-8").encode()).digest()
    assert got == before, f"{APP} не вернулся к исходному состоянию"
    assert not misses, "не поймано: " + "; ".join(misses)
    ok(f"все {caught} поломок из {len(MUTATIONS)} пойманы, страница на месте")


CHECKS_LIST = [
    check_warning_says_two_facts,
    check_need_second_person,
    check_page_cards_have_no_warning,
    check_warning_text_is_clean,
    check_ask_card_keeps_backup_path,
    check_body_form_is_not_a_button,
    check_keys_still_match_bot,
]

if __name__ == "__main__":
    fns = list(CHECKS_LIST)
    # Под мутацией гоняется одна проверка, сами мутации тогда не нужны.
    if not os.environ.get("BEZ_STRANICY_ONE"):
        fns += [check_every_requirement_has_a_mutation, check_mutations_are_caught]
    raise SystemExit(run(fns))
