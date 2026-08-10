# -*- coding: utf-8 -*-
"""Проверки: карточка «Осознанность» есть в каталоге и открыта всем.

Спека 023 (`specs/023-osoznannost-dlya-vseh/` в репозитории бота), FR-006.

Что было. Замер «Осознанность» показывался только тому, кто прямо сказал боту,
что практикует медитацию или дыхание. В каталоге карточки не было вовсе — ни
условной, ни обычной. Владелец каждый день заполняет в суточном замере поле
«Практика внимания» и до этого замера не добрался ни разу.

Решение владельца 10.08.2026: открыть замер всем. Внутри две шкалы — внимание в
быту и способность отойти от мысли; ни одна не спрашивает про опыт практики, обе
проверялись на людях без неё. Условие было перестраховкой, а не требованием
инструмента.

Что проверяется:
  · карточка есть в реестре, в квартальном ритме, и её данные совпадают с ботом;
  · она видна при любом состоянии признака практики — и «да», и «нет», и молчание;
  · своей страницы у неё нет, поэтому по правилам 020 она честно говорит, что
    замер идёт в переписке с ботом и мини-апп закроется;
  · «что принести» у неё нет: ни второго человека, ни файла;
  · фраза для чата совпадает с надписью кнопки в `bot.py` буква в букву;
  · на собранном экране карточка стоит в разделе «Квартал» и ровно один раз;
  · текст без баллов, без названий шкал, без оценочных слов и без «для тех, кто
    практикует»;
  · нажатие открывает замер: боту уходит просьба `open_card`;
  · поломки ловятся: каждое требование закрыто мутацией.

Проверки исполняют страницу в node с заглушками и смотрят на СОБРАННЫЙ экран, а
не ищут слова в исходнике: ошибку шаблона разбором текста не поймать.

Запуск:  python3 checks/osoznannost_dlya_vseh.py
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
from kartochki_bez_stranicy import MAX_WORDS, MUST_SAY, card_markup, sentences
from lib import BOT, ROOT, bot, catalog, catalog_render, catalog_taps, ok, run, visible

CHECKS = Path(__file__).resolve().parent
APP = "kak-ty/app.html"

KEY = "state_mind"
LABEL = "Осознанность"

# Слова, которых на карточке быть не может. Оценки — «мини-аппы-правила.md»,
# часть 4; баллы и шкалы — конституция, принципы III и IV.
BAD_WORDS = ["балл", "индекс", "процент", "норм", "мало", "много", "плохо",
             "хорошо", "слабо", "низк", "высок", "должен", "лень",
             "FFMQ", "ffmq", "EQ", "Baer", "Голубев"]

# Условие, которого больше нет. Дословно то, что стояло в описании до 10.08.2026.
BAD_CONDITION = ["для тех, кто практикует", "практик", "медитац", "дыхани"]


def registry() -> Dict[str, Dict]:
    return {r["key"]: r for r in catalog()["registry"]}


def card() -> Dict:
    reg = registry()
    assert KEY in reg, \
        f"карточки «{LABEL}» нет в реестре каталога — замер открыть нечем"
    return reg[KEY]


def warn() -> str:
    """Строка предупреждения карточки — из чистой логики каталога."""
    c = catalog("""
OUT.warn = "";
REGISTRY.forEach(function (r) { if (r.key === "state_mind") OUT.warn = chatWarn(r); });
""")
    return c["warn"]


# --------------------------------------------------------------------------


def check_card_is_in_registry() -> None:
    """1. Карточка есть в реестре и стоит в квартальном ритме."""
    c = card()
    assert c["label"] == LABEL, f"название поехало: {c['label']!r}"
    assert c["section"] == "quarter", \
        f"карточка стоит в ритме «{c['section']}», а должна в «quarter»"
    assert c["days"] == 91, f"срок годности поехал: {c['days']}"
    assert c["what"], "у карточки нет строки «что это даст»"
    assert c["size"], "у карточки нет честной длины"
    assert not c["once"], "квартальный замер помечен разовым"
    ok(f"1. карточка «{LABEL}» в реестре, ритм квартальный, срок 91 день")

    # Данные совпадают с ботом: второго списка имён и меток мы не держим.
    meta = bot()["CARD_META"][KEY]
    assert sorted(c["containers"]) == sorted(meta["containers"]), \
        f"метки областей разошлись с ботом: {c['containers']} vs {meta['containers']}"
    assert meta["section"] == c["section"], \
        f"ритм разошёлся с ботом: {c['section']} vs {meta['section']}"
    assert c["area"] in c["containers"], \
        f"главная область «{c['area']}» не из меток карточки"
    ok("1. метки областей и ритм совпадают с CARD_META бота")

    # Название совпадает с реестром бота: одно имя карточки в двух местах,
    # иначе человек не найдёт кнопку по строке и строку по кнопке.
    label_in_bot = {m["key"]: m["label"] for m in bot()["STATE_BLOCKS_META"]}
    assert label_in_bot.get(KEY) == LABEL, \
        f"название в боте другое: {label_in_bot.get(KEY)!r}"
    ok("1. название совпадает с реестром бота")


def check_visible_to_everyone() -> None:
    """2. Карточка видна при любом состоянии признака практики."""
    c = card()
    assert c["cond"] is None, \
        f"у карточки осталось условие показа: {c['cond']!r}"
    ok("2. условия показа у карточки нет")

    js = """
function keys(opts) { return visibleCards(REGISTRY, opts).map(function (c) { return c.key; }); }
OUT.plain = keys({});
OUT.noTeam = keys({ hasTeam: false });
OUT.noPair = keys({ hasPair: false });
OUT.noForum = keys({ hasForum: false });
OUT.clinical = keys({ clinicalFired: true });
"""
    r = catalog(js)
    sets = ("plain", "noTeam", "noPair", "noForum", "clinical")
    for name in sets:
        assert KEY in r[name], f"карточка исчезла в наборе «{name}»"
    ok(f"2. карточка на месте во всех {len(sets)} наборах условий")

    # Флаг практики каталог по-прежнему передаёт странице замера, но видимость
    # карточки от него больше не зависит. Три состояния, как везде.
    src = (ROOT / APP).read_text(encoding="utf-8")
    assert '"md"' in src or "'md'" in src, \
        "флаг практики перестал уезжать на страницы — «Восемь фактов» переспросят"
    for search in ("md=1", "md=0", ""):
        h = catalog_render(link(FRESH, search))
        assert f'class="card-name">{LABEL}</div>' in h, \
            f"при параметрах «{search}» карточки на экране нет"
    ok("2. карточка на экране и при md=1, и при md=0, и без параметра")


def check_card_says_it_goes_to_chat() -> None:
    """3. Своей страницы нет — карточка честно про переписку с ботом."""
    c = card()
    assert not c["url"], \
        "у карточки появился адрес страницы, которой в проекте нет"
    assert c["phrase"], "у карточки нет фразы для чата — открыть её нечем"
    assert not c["after"], \
        "карточка снова открывается следом за другим замером, а не сама"
    ok("3. у карточки нет адреса, есть фраза для чата")

    w = warn()
    assert w, "карточка молчит о том, что будет при нажатии"
    for part in MUST_SAY:
        assert part in w, f"в предупреждении нет «{part}»: {w!r}"
    ok("3. сказано про переписку с ботом и про закрытие экрана")

    # «Что принести» у неё нет: замер про обычный день, ни второго человека, ни
    # файла он не требует. Лишняя строка тут была бы неправдой.
    assert c.get("need") in (None, ""), \
        f"у карточки стоит «что принести», а приносить нечего: {c.get('need')!r}"
    for bad in ("второй человек", "группа", "PDF"):
        assert bad not in w, f"предупреждение требует принести «{bad}»: {w!r}"
    ok("3. приносить для замера нечего, и карточка ничего не требует")

    # То же на собранном экране: человек читает его, а не чистую логику.
    _, rest = screens(link(FRESH))
    seen = visible(card_markup(rest, LABEL))
    for part in MUST_SAY:
        assert part in seen, f"на карточке в списке нет «{part}»"
    ok("3. предупреждение видно на карточке в списке")


def check_phrase_matches_bot() -> None:
    """4. Фраза карточки совпадает с надписью кнопки бота буква в букву."""
    c = card()
    body = BOT.read_text(encoding="utf-8")
    m = re.search(r'MIND_BUTTON\s*=\s*"([^"]+)"', body)
    assert m, "в bot.py нет надписи кнопки MIND_BUTTON — фразе не с чем сверяться"
    assert c["phrase"] == m.group(1), \
        f"фраза каталога «{c['phrase']}» не равна кнопке бота «{m.group(1)}»"
    ok(f"4. фраза совпадает с кнопкой бота: «{c['phrase']}»")

    # Фраза существует в боте маршрутом, а не только строкой реестра: иначе
    # человек отправит её в чат и не получит ничего.
    assert "MIND_BUTTON" in body, "надпись кнопки нигде не используется"
    assert "mind_start" in body, "надпись есть, а замер по ней не открывается"
    ok("4. фраза открывает замер в боте")


def check_one_card_in_quarter() -> None:
    """5. На экране карточка стоит в разделе «Квартал» и ровно один раз."""
    _, rest = screens(link(FRESH))
    n = rest.count(f'class="card-name">{LABEL}</div>')
    assert n == 1, f"карточка нарисована в списке {n} раз, а должна один"
    ok("5. карточка в списке одна")

    # Раздел: режем список по заголовкам ритмов и смотрим, в каком она куске.
    heads = [(m.start(), m.group(1)) for m in
             re.finditer(r'<span class="rhythm-name">([^<]*)</span>', rest)]
    assert heads, "на экране нет заголовков ритмов — резать нечем"
    pos = rest.index(f'class="card-name">{LABEL}</div>')
    mine = ""
    for start, name in heads:
        if start < pos:
            mine = name
    assert mine == "Квартал", f"карточка стоит под заголовком «{mine}»"
    ok("5. карточка стоит в разделе «Квартал»")


def check_text_is_clean() -> None:
    """6. Ни баллов, ни шкал, ни оценок, ни «для тех, кто практикует»."""
    c = card()
    texts = {"что это даст": c["what"], "честная длина": c["size"],
             "предупреждение": warn(), "название": c["label"]}
    for where, text in texts.items():
        low = (text or "").lower().replace("ё", "е")
        for bad in BAD_WORDS:
            assert bad.lower() not in low, \
                f"{where}: запретное слово «{bad}» — {text!r}"
        for bad in BAD_CONDITION:
            assert bad not in low, \
                f"{where}: условие практики вернулось в текст («{bad}») — {text!r}"
    ok("6. в текстах карточки нет баллов, шкал, оценок и условия практики")

    # Правила текста: фраза длиннее двенадцати слов режется пополам.
    for where, text in texts.items():
        for s in sentences(text or ""):
            n = len(re.findall(r"[0-9A-Za-zА-Яа-яЁё]+", s))
            assert n <= MAX_WORDS, \
                f"{where}: фраза из {n} слов — правила требуют резать: {s!r}"
    ok(f"6. все фразы короче {MAX_WORDS + 1} слов")

    # Сказано, что замеряется. Без этого карточка просто занимает место.
    low = c["what"].lower().replace("ё", "е")
    assert "замеча" in low or "внимани" in low, \
        f"не сказано про внимание: {c['what']!r}"
    assert "мысл" in low, f"не сказано про мысль: {c['what']!r}"
    ok("6. строка «что это даст» называет обе половины замера")

    # Экран целиком собирается без дыр.
    whole = visible(catalog_render(link(FRESH, obs(OBS))))
    assert "undefined" not in whole and "NaN" not in whole, \
        "на собранном экране есть undefined или NaN"
    ok("6. экран с новой карточкой собирается без дыр")


def check_tap_opens_the_measure() -> None:
    """7. Нажатие открывает замер: боту уходит просьба открыть карточку."""
    c = catalog_taps(link(FRESH, obs(OBS)), """
  var el = tap('data-send', 'state_mind');
  OUT.tap = el.click();
""")
    assert c["calls"]["sent"] == ['{"action":"open_card","card":"state_mind"}'], \
        f"нажатие карточки не открывает замер: {c['calls']['sent']}"
    ok("7. нажатие отправляет боту просьбу открыть замер")

    # Запасной путь: ссылка на переписку со старт-параметром. Его ломать нельзя.
    assert "?start=card_state_mind" in c["html"], \
        "у карточки нет запасной ссылки на переписку"
    ok("7. запасная ссылка на переписку на месте")


# --------------------------------------------------------------------------
# Мутации: ломаем правку и смотрим, покраснеет ли проверка
# --------------------------------------------------------------------------
# Конституция, принцип II: проверка обязана падать при сломанной логике.
# (что ломаем · было · стало · какая проверка обязана покраснеть)
MUTATIONS: List[Tuple[str, str, str, str]] = [
    ("карточка уехала из квартального ритма в полгода",
     '    key: "state_mind", label: "Осознанность", group: "Состояние",\n'
     '    days: 91, section: "quarter",',
     '    key: "state_mind", label: "Осознанность", group: "Состояние",\n'
     '    days: 91, section: "rare",',
     "check_one_card_in_quarter"),

    ("карточке вернули условие показа",
     '    size: "15 утверждений · 3 минуты",\n    phrase: "🧠 Осознанность"',
     '    size: "15 утверждений · 3 минуты",\n    cond: "team",\n'
     '    phrase: "🧠 Осознанность"',
     "check_visible_to_everyone"),

    ("у карточки исчезла фраза для чата",
     '    size: "15 утверждений · 3 минуты",\n    phrase: "🧠 Осознанность"',
     '    size: "15 утверждений · 3 минуты"',
     "check_card_says_it_goes_to_chat"),

    ("фраза карточки разошлась с кнопкой бота",
     'phrase: "🧠 Осознанность"\n  },\n  {\n    // Первый замер в области «Работа»',
     'phrase: "🧠 Внимание"\n  },\n  {\n    // Первый замер в области «Работа»',
     "check_phrase_matches_bot"),

    ("в описание вернулось условие практики",
     'what: "внимание в быту и умение отойти от мысли",',
     'what: "для тех, кто практикует: внимание и отход от мысли",',
     "check_text_is_clean"),

    ("карточке приписали чужую страницу",
     '    size: "15 утверждений · 3 минуты",\n    phrase: "🧠 Осознанность"',
     '    size: "15 утверждений · 3 минуты",\n'
     '    url: "https://shapovalov-aleksey.ru/state-quarter/app3.html",\n'
     '    phrase: "🧠 Осознанность"',
     "check_card_says_it_goes_to_chat"),

    ("карточке приписали «нужен второй человек»",
     '    size: "15 утверждений · 3 минуты",\n    phrase: "🧠 Осознанность"',
     '    size: "15 утверждений · 3 минуты",\n    need: "pair",\n'
     '    phrase: "🧠 Осознанность"',
     "check_card_says_it_goes_to_chat"),
]

MUST_COVER = {
    "check_one_card_in_quarter",
    "check_visible_to_everyone",
    "check_card_says_it_goes_to_chat",
    "check_phrase_matches_bot",
    "check_text_is_clean",
}


def _one_check(name: str) -> int:
    """Прогнать одну проверку отдельным процессом: мутация живёт на диске."""
    code = ("import lib_path\n"
            "from lib import run\n"
            "import osoznannost_dlya_vseh as C\n"
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
    ok(f"8. {len(MUST_COVER)} требований закрыты мутациями")


def check_mutations_are_caught() -> None:
    """9. Каждая поломка ловится проверкой, и страница возвращается на место."""
    path = ROOT / APP
    src = path.read_text(encoding="utf-8")
    before = hashlib.sha256(src.encode()).hexdigest()

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

    got = hashlib.sha256(path.read_text(encoding="utf-8").encode()).hexdigest()
    assert got == before, f"{APP} не вернулся к исходному состоянию"
    assert not misses, "поломки не поймались:\n  " + "\n  ".join(misses)
    ok(f"9. все {caught} поломок из {len(MUTATIONS)} пойманы, страница на месте")
    ok(f"9. sha256 страницы тот же: {before[:16]}…")


if __name__ == "__main__":
    raise SystemExit(run([
        check_card_is_in_registry,
        check_visible_to_everyone,
        check_card_says_it_goes_to_chat,
        check_phrase_matches_bot,
        check_one_card_in_quarter,
        check_text_is_clean,
        check_tap_opens_the_measure,
        check_every_requirement_has_a_mutation,
        check_mutations_are_caught,
    ]))
