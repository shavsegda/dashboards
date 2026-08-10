# -*- coding: utf-8 -*-
"""Проверки: список «Посмотреть всё» идёт РИТМАМИ, первый экран не тронут.

Дефект нашёл Алексей, пользуясь кнопкой сам, 10.08.2026. Дословно:

    «мне неудобно сейчас пользоваться этой кнопкой, мне бы было удобно поделить
    замеры на: ежедневно, еженедельно, ежемесячно, квартально, полгода, год»

Подтвердил: **шесть ритмов, для всех пользователей одинаково.**

Почему дефект появился. Спека 007 (FR-010) велела группировать список по
областям жизни — под работу нового человека «что со мной вообще». У
вернувшегося работа другая: «что мне пора пройти», и по областям он этого не
находит. Убрав ритмы, 007 закрыла первую работу и убила вторую.

Что проверяем:
  · **шесть ритмов в порядке от частого к редкому:** сутки · неделя · месяц ·
    квартал · полгода · год. Порядок именно такой, и он одинаков для всех;
  · разовый замер — не ритм: он идёт последним отдельным блоком и не приписан к
    сроку, которого у него нет;
  · **ритм карточки — её собственный, из `CARD_META` бота** (поле `section`).
    Не наша выдумка и не пересчёт из дней;
  · **ни одна карточка не встречается дважды.** Раньше карточка попадала в
    каждую свою область жизни, и «Восемь фактов» стояли во всех семи;
  · **область жизни видна меткой на карточке** — обе работы закрыты разом:
    видно, что пора, и видно, чего это касается;
  · **первый экран не изменился ни на байт.** Наблюдение, одна просьба, слепая
    зона, вход в дорожку — всё как было. Проверка жёсткая: собранный первый
    экран сверяется с хешем по пяти состояниям сразу;
  · поломки ловятся: каждое требование закрыто мутацией.

Проверки исполняют страницу в node с заглушками и смотрят на СОБРАННЫЙ экран,
а не ищут слова в исходнике: ошибку шаблона разбором текста не поймать.

Запуск:  python3 checks/spisok_ritmami.py
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
from lib import ROOT, bot, catalog, catalog_render, ok, run, visible

CHECKS = Path(__file__).resolve().parent
APP = "kak-ty/app.html"

# Шесть ритмов, в порядке решения Алексея: от частого к редкому.
RHYTHM_HEADS: List[str] = ["Сутки", "Неделя", "Месяц", "Квартал", "Полгода", "Год"]

# Разовый замер идёт последним и назван по-честному: ритма у него нет.
ONCE_HEAD = "Один раз"

# Идентификаторы ритмов — те же, что поле `section` в CARD_META бота.
RHYTHM_IDS: List[str] = ["day", "week", "month", "quarter", "rare", "year"]

# Строка про слепую зону: она едет от бота и стоит на первом экране.
BLIND = "Про работу и деньги пока ничего не известно."


def blind(text: str) -> str:
    import urllib.parse
    return "bs=" + urllib.parse.quote(text, safe="")


# Первый экран в пяти состояниях. Хеши снятЫ 10.08.2026 ДО правки списка и с тех
# пор не менялись: правка касается только того, что ниже «Посмотреть всё».
#
# Зачем хеш, а не набор слов. «Не изменился» — это утверждение про весь экран
# целиком, вместе с порядком блоков, разметкой и адресами. Набор слов пропустит
# и переставленные блоки, и уехавшую метку, и лишнюю строку.
FIRST_SCREEN_SHA: Dict[str, str] = {
    "quiet":
        "91726c7f93ca7968002839c7713371f0a7b24a9cde1a934f14ac8b8c81133da1",
    "obs_ask":
        "de2ff61a68eecc9f76a544be12ddb4274750f940053003d0957c21fef6d590c7",
    "obs_only":
        "79371da35e588e282988cc4b91e1a7d1847269ac630b51ca2f4ff69146b7d7de",
    "first_step":
        "e0a71fedf26db5595c36aaa710deddb46fdd2123b56b8bdc510f5bfbbe3e1fbb",
    "with_blind":
        "3618fdce7e377bc487f02a374edb862c7a103c535b610499f5555b470f3b2bbb",
}

FIRST_SCREEN_CASES: Dict[str, str] = {
    "quiet": link(),
    "obs_ask": link(FRESH, obs(OBS), "ask=state_week"),
    "obs_only": link(FRESH, obs(OBS)),
    "first_step": link("ask=state_week"),
    "with_blind": link(FRESH, obs(OBS), "ask=state_week", blind(BLIND)),
}


# --------------------------------------------------------------------------
# Разбор собранного списка
# --------------------------------------------------------------------------
def group_names(rest: str) -> List[str]:
    """Заголовки групп списка, в порядке экрана."""
    return re.findall(r'<span class="rhythm-name">([^<]*)</span>', rest)


def group_counts(rest: str) -> List[Tuple[str, int]]:
    """Заголовок группы и число в её строке — как их видит человек."""
    return [(m.group(1), int(m.group(2))) for m in re.finditer(
        r'<span class="rhythm-name">([^<]*)</span>'
        r'<span class="rhythm-count">(\d+)</span>', rest)]


def group_blocks(rest: str) -> List[Tuple[str, str]]:
    """Каждая группа целиком: её имя и её разметка."""
    out = []
    parts = rest.split('<details class="rhythm">')
    for p in parts[1:]:
        m = re.search(r'<span class="rhythm-name">([^<]*)</span>', p)
        assert m, "у группы списка нет заголовка"
        out.append((m.group(1), p.split("</details>")[0]))
    return out


def cards_of(block: str) -> List[str]:
    """Карточки внутри группы: каждая своей разметкой."""
    return ['<div class="card">' + c for c in block.split('<div class="card">')[1:]]


def card_label(card: str) -> str:
    m = re.search(r'<div class="card-name">([^<]*)</div>', card)
    return m.group(1) if m else ""


def registry() -> Dict[str, Dict]:
    return {r["key"]: r for r in catalog()["registry"]}


def visible_registry() -> Dict[str, Dict]:
    """Карточки, которые человек видит по умолчанию: без условной клинической."""
    return {k: c for k, c in registry().items() if c["cond"] != "clinical"}


def first_screen(search: str) -> str:
    """Первый экран целиком: всё, что стоит ВЫШЕ «Посмотреть всё»."""
    h = catalog_render(search)
    i = h.index('id="all"')
    return h[:h.rindex("<details", 0, i)]


# --------------------------------------------------------------------------


def check_six_rhythms_in_order() -> None:
    """1. Шесть ритмов, в порядке от частого к редкому."""
    _, rest = screens(link(FRESH))
    names = group_names(rest)
    assert names[:6] == RHYTHM_HEADS, f"ритмы идут так: {names[:6]}"
    ok("сутки · неделя · месяц · квартал · полгода · год")

    text = visible(rest)
    for head in RHYTHM_HEADS:
        assert head in text, f"ритма «{head}» на экране нет"
    ok("все шесть ритмов человек видит")

    # Порядок задан явно в коде, а не получается случайно из порядка реестра.
    c = catalog("OUT.order = RHYTHMS.map(function (r) { return r.id; });\n"
                "OUT.heads = RHYTHMS.map(function (r) { return r.name; });\n"
                "OUT.once = ONCE_RHYTHM;\n")
    assert c["order"] == RHYTHM_IDS, f"порядок ритмов в коде: {c['order']}"
    assert c["heads"] == RHYTHM_HEADS, f"названия ритмов в коде: {c['heads']}"
    assert c["once"]["id"] == "once", "разовый замер потерял свою метку"
    ok("порядок и названия ритмов заданы явно")


def check_once_is_not_a_rhythm() -> None:
    """2. Разовый замер — последним блоком и не приписан к сроку."""
    _, rest = screens(link(FRESH))
    names = group_names(rest)
    assert names[-1] == ONCE_HEAD, f"последняя группа списка: «{names[-1]}»"
    assert names.count(ONCE_HEAD) == 1, "разовых блоков больше одного"
    assert len(names) == len(RHYTHM_HEADS) + 1, \
        f"групп в списке {len(names)}, а не шесть ритмов плюс разовое"
    ok("разовое идёт последним, отдельным блоком")

    reg = registry()
    once = [(name, block) for name, block in group_blocks(rest) if name == ONCE_HEAD]
    labels = [card_label(c) for c in cards_of(once[0][1])]
    want = [c["label"] for c in reg.values() if c["section"] == "once"]
    assert sorted(labels) == sorted(want), \
        f"в разовом блоке {labels}, а разовые замеры — {want}"
    ok("в разовом блоке только разовые замеры")

    # И наоборот: разовая карточка не попала ни в один ритм.
    for name, block in group_blocks(rest):
        if name == ONCE_HEAD:
            continue
        for card in cards_of(block):
            assert card_label(card) not in want, \
                f"разовый замер «{card_label(card)}» приписан ритму «{name}»"
    ok("ни один разовый замер не приписан сроку")


def check_rhythm_comes_from_bot() -> None:
    """3. Ритм карточки — её собственный, из CARD_META бота."""
    meta = bot()["CARD_META"]
    reg = registry()
    for key, card in reg.items():
        assert key in meta, f"карточки «{key}» нет в CARD_META бота"
        assert card["section"] == meta[key]["section"], \
            f"ритм «{key}»: «{card['section']}» против «{meta[key]['section']}» в боте"
    ok(f"ритм всех {len(reg)} карточек сходится с CARD_META")

    c = catalog("""
var CARDS = buildCards(REGISTRY, {}, "2026-08-10T10:00:00Z", true);
OUT.groups = byRhythm(CARDS).map(function (g) {
  return { id: g.id, name: g.name,
           keys: g.cards.map(function (x) { return x.key; }) };
});
OUT.sections = REGISTRY.map(function (r) { return { key: r.key, s: r.section }; });
""")
    sect = {x["key"]: x["s"] for x in c["sections"]}
    for g in c["groups"]:
        for key in g["keys"]:
            assert sect[key] == g["id"], \
                f"карточка «{key}» с ритмом «{sect[key]}» стоит в группе «{g['id']}»"
        assert g["keys"], f"группа «{g['id']}» попала в список пустой"
    ok("раскладка идёт по полю section, пустых групп нет")


def check_no_card_twice() -> None:
    """4. Ни одна карточка не встречается в списке дважды."""
    c = catalog("""
OUT.groups = byRhythm(buildCards(REGISTRY, {}, "2026-08-10T10:00:00Z", true))
  .map(function (g) { return g.cards.map(function (x) { return x.key; }); });
OUT.all = REGISTRY.map(function (r) { return r.key; });
OUT.places = REGISTRY.reduce(function (n, r) {
  return n + (r.containers || []).length;
}, 0);
""")
    keys = [k for g in c["groups"] for k in g]
    dupes = sorted({k for k in keys if keys.count(k) > 1})
    assert not dupes, f"карточки стоят в списке больше одного раза: {dupes}"
    assert set(keys) == set(c["all"]), \
        f"из списка выпали карточки: {sorted(set(c['all']) - set(keys))}"
    assert len(keys) == len(c["all"]), "число мест в списке не равно числу карточек"
    assert len(keys) < c["places"], \
        f"мест в списке {len(keys)} против {c['places']} прежних — дубли вернулись"
    ok(f"все {len(keys)} карточек, каждая ровно раз (было {c['places']} мест)")

    # То же на собранном экране: карточка не может встретиться дважды.
    _, rest = screens(link(FRESH))
    for key, card in visible_registry().items():
        n = len(re.findall(
            re.escape('<div class="card-name">' + card["label"] + "</div>"), rest))
        assert n == 1, f"карточка «{card['label']}» на экране {n} раз, а не один"
    ok("на собранном экране каждая карточка ровно один раз")

    # Число в строке группы совпадает с тем, что в ней лежит.
    for name, block in group_blocks(rest):
        want = len(cards_of(block))
        got = dict(group_counts(rest))[name]
        assert got == want, f"группа «{name}»: в строке {got}, карточек {want}"
    ok("число в строке каждой группы совпадает с её карточками")


def check_area_is_a_label_on_the_card() -> None:
    """5. Область жизни видна меткой на карточке, а не заголовком раздела."""
    _, rest = screens(link(FRESH))
    reg = visible_registry()
    for name, block in group_blocks(rest):
        for card in cards_of(block):
            label = card_label(card)
            key = [k for k, v in reg.items() if v["label"] == label]
            assert key, f"на экране карточка «{label}», которой нет в реестре"
            area = next(r["area"] for r in catalog()["registry"]
                        if r["key"] == key[0])
            m = re.search(r'<div class="card-when">([^<]*)</div>', card)
            assert m, f"у карточки «{label}» нет служебной строки с меткой области"
            assert m.group(1).split(" · ")[0] == area, \
                f"у «{label}» метка области «{m.group(1)}», а область — «{area}»"
    ok("у каждой карточки списка первой стоит метка её области")

    # Метка стоит в ОДНОЙ строке с остальным: карточка не стала выше.
    assert re.search(r'<div class="card-when">Тело · последний замер [^<]* · ещё: ',
                     rest), "метка области, «когда был» и «ещё» разъехались на строки"
    assert rest.count('class="card-when"') <= len(re.findall(r'class="card"', rest)), \
        "служебных строк больше, чем карточек"
    ok("метка области, «когда был» и «ещё» — одна строка")

    # Заголовками разделов области больше не работают.
    text = visible(rest)
    heads = group_names(rest)
    for area in ["Я сам", "Тело", "Семья", "Круг", "Работа", "Деньги",
                 "Время на себя"]:
        assert area not in heads, f"область «{area}» осталась заголовком раздела"
        assert area in text, f"область «{area}» пропала из списка вовсе"
    ok("области жизни видны, но не как разделы")


def check_first_screen_untouched() -> None:
    """6. Первый экран не изменился ни на байт — по всем пяти состояниям."""
    for name, search in FIRST_SCREEN_CASES.items():
        got = first_screen(search)
        sha = hashlib.sha256(got.encode()).hexdigest()
        assert sha == FIRST_SCREEN_SHA[name], (
            f"первый экран «{name}» изменился: {sha[:12]} вместо "
            f"{FIRST_SCREEN_SHA[name][:12]}")
    ok("пять состояний первого экрана совпадают с хешами до правки")

    # Отдельно словами — чтобы при падении было видно, ЧТО именно ушло.
    ask = visible(first_screen(FIRST_SCREEN_CASES["with_blind"]))
    for part in ("Что со мной?", "Что видно по твоим ответам", OBS, BLIND,
                 "Чтобы сказать точнее, не хватает одного",
                 "пройти несколько за раз"):
        assert part in ask, f"с первого экрана пропало: «{part}»"
    ok("наблюдение, слепая зона, одна просьба и вход в дорожку на месте")

    # Ритмов на первом экране нет: они живут внутри списка.
    for head in RHYTHM_HEADS + [ONCE_HEAD]:
        assert head not in group_names(first_screen(FIRST_SCREEN_CASES["obs_ask"])), \
            f"заголовок ритма «{head}» вылез на первый экран"
    assert "card-when" not in first_screen(FIRST_SCREEN_CASES["obs_ask"]), \
        "на карточке первого экрана появилась служебная строка с меткой области"
    ok("на первом экране ни ритмов, ни метки области")


# --------------------------------------------------------------------------
# Мутации: ломаем правку и смотрим, покраснеет ли проверка
# --------------------------------------------------------------------------
# Конституция, принцип II: проверка обязана падать при сломанной логике.
# (что ломаем · было · стало · какая проверка обязана покраснеть)
MUTATIONS: List[Tuple[str, str, str, str]] = [
    ("список снова группируется по областям жизни",
     'cards: (cards || []).filter(function (c) { return c.section === r.id; })',
     'cards: (cards || []).filter(function (c) { return c.area === r.name; })',
     "check_six_rhythms_in_order"),

    ("ритмы идут от редкого к частому",
     'var RHYTHMS = [\n  { id: "day",     name: "Сутки" },',
     'var RHYTHMS = [\n  { id: "year",    name: "Год" },\n'
     '  { id: "day",     name: "Сутки" },',
     "check_six_rhythms_in_order"),

    ("разовый замер приписан к году",
     'return RHYTHMS.concat([ONCE_RHYTHM]).map(function (r) {',
     'return RHYTHMS.map(function (r) {\n'
     '    if (r.id === "year") return { id: r.id, name: r.name,\n'
     '      cards: (cards || []).filter(function (c) {\n'
     '        return c.section === "year" || c.section === "once"; }) };\n'
     '    return null;\n'
     '  }).filter(function (g) { return g; }).map(function (r) {',
     "check_once_is_not_a_rhythm"),

    ("карточка снова встаёт в каждую свою область",
     "  return RHYTHMS.concat([ONCE_RHYTHM]).map(function (r) {",
     "  return AREA_ORDER.map(function (a) { return { id: a, name: a,\n"
     "    cards: (cards || []).filter(function (c) {\n"
     "      return (c.containers || []).indexOf(a) >= 0; }) }; })\n"
     "    .filter(function (g) { return g.cards.length > 0; })\n"
     "    .concat([]).map(function (r) { return r; });\n"
     "  return RHYTHMS.concat([ONCE_RHYTHM]).map(function (r) {",
     "check_no_card_twice"),

    ("метка области ушла с карточки",
     "  if (card.area) parts.push(card.area);",
     "  if (false) parts.push(card.area);",
     "check_area_is_a_label_on_the_card"),

    ("метка области вылезла на карточку первого экрана",
     "      cardHtml(ask, false) + \"</div>\";\n  } else if (state === \"first_step\")",
     "      cardHtml(ask, true) + \"</div>\";\n  } else if (state === \"first_step\")",
     "check_first_screen_untouched"),

    ("ритм карточки считается не из реестра бота",
     'key: "state_move", label: "Движение", group: "Состояние", days: 7, section: "week"',
     'key: "state_move", label: "Движение", group: "Состояние", days: 7, section: "month"',
     "check_rhythm_comes_from_bot"),
]

MUST_COVER = {
    "check_six_rhythms_in_order",
    "check_once_is_not_a_rhythm",
    "check_rhythm_comes_from_bot",
    "check_no_card_twice",
    "check_area_is_a_label_on_the_card",
    "check_first_screen_untouched",
}


def _one_check(name: str) -> int:
    """Прогнать одну проверку отдельным процессом: мутация живёт на диске."""
    code = ("import lib_path\n"
            "from lib import run\n"
            "import spisok_ritmami as C\n"
            "raise SystemExit(run([getattr(C, %r)]))\n" % name)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(CHECKS) + os.pathsep + env.get("PYTHONPATH", "")
    r = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT),
                       capture_output=True, text=True, timeout=1800)
    return r.returncode


def check_every_requirement_has_a_mutation() -> None:
    """7. У каждого требования приёмки есть хотя бы одна поломка."""
    used = {m[3] for m in MUTATIONS}
    missing = MUST_COVER - used
    assert not missing, "без мутации остались: " + ", ".join(sorted(missing))
    ok(f"{len(MUST_COVER)} требований закрыты мутациями")


def check_mutations_are_caught() -> None:
    """8. Каждая поломка ловится проверкой, и страница возвращается по хешу."""
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
    check_six_rhythms_in_order,
    check_once_is_not_a_rhythm,
    check_rhythm_comes_from_bot,
    check_no_card_twice,
    check_area_is_a_label_on_the_card,
    check_first_screen_untouched,
]

if __name__ == "__main__":
    fns = list(CHECKS_LIST)
    # Под мутацией гоняется одна проверка, сами мутации тогда не нужны.
    if not os.environ.get("RITMAMI_ONE"):
        fns += [check_every_requirement_has_a_mutation, check_mutations_are_caught]
    raise SystemExit(run(fns))
