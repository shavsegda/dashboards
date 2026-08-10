# -*- coding: utf-8 -*-
"""Проверки: на первом экране виден замер, на который бот не приглашает.

Спека 020, История 4.

Дефект, 10.08.2026. Владелец не нашёл «Спокойствие с деньгами». Бот про деньги не
спрашивает сам — это записано в нём списком `OBS_ASK_SKIP` и сделано сознательно:
деньги чувствительная тема. Следствие вышло обратное задуманному: до таких
замеров невозможно дойти. Просьба на экране одна, и она никогда не про них, а в
списке карточка лежит в разделе «Полгода», куда владелец не добрался.

Что проверяется:
  · на первом экране есть блок с ОДНИМ таким замером;
  · список ключей — перенос из `OBS_ASK_SKIP` бота, а не своя выдумка;
  · берётся только тот замер, до которого человек может дойти сам: со своей
    страницей и без второго человека;
  · пройденный не показывается: сказать про него нечего;
  · текст не задание и не долг: ни «пора», ни «нужно», ни «должен», ни счётчика;
  · просьба на экране по-прежнему одна: блок не становится второй просьбой;
  · порядок экрана не поехал: вход в дорожку и «Посмотреть всё» на месте;
  · поломки ловятся: каждое требование закрыто мутацией.

Запуск:  python3 checks/zamer_bez_priglasheniya.py
"""

import ast
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
from chto_so_mnoy import FRESH, OBS, has_word, link, obs, screens
from lib import BOT, ROOT, catalog, catalog_render, ok, run, visible

CHECKS = Path(__file__).resolve().parent
APP = "kak-ty/app.html"

# Замер, который сейчас попадает в блок. Один: у остальных из списка бота либо нет
# своей страницы, либо нужен второй человек.
CARD = "state_finwell"
LABEL = "Спокойствие с деньгами"

# Слова, которые превращают строку в задание или в долг.
DUTY_WORDS = ["пора", "нужно", "должен", "обязательно", "не проходил",
              "осталось", "из семи", "пройдено"]


def obs_ask_skip() -> List[str]:
    """`OBS_ASK_SKIP` из bot.py. Только чтение, разбором AST: импортировать бота
    нельзя — при импорте он тянет токены и сеть."""
    tree = ast.parse(BOT.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name) \
                and node.targets[0].id == "OBS_ASK_SKIP":
            return list(ast.literal_eval(node.value))
    raise AssertionError("в bot.py нет OBS_ASK_SKIP")


def block(search: str) -> str:
    """Разметка блока про замер без приглашения. Нет блока — пустая строка."""
    h = catalog_render(search)
    if 'class="mine"' not in h:
        return ""
    i = h.index('<div class="mine">')
    return h[i:h.index('<div class="runall"', i)] if '<div class="runall"' in h[i:] \
        else h[i:h.index("<details", i)]


def cards_on_first(search: str) -> int:
    first, _ = screens(search)
    return len(re.findall(r'class="card"', first))


# --------------------------------------------------------------------------


def check_block_shows_one_measure() -> None:
    """1. На первом экране есть блок с одним таким замером."""
    b = block(link(FRESH, obs(OBS), "ask=state_week"))
    assert b, "на первом экране нет блока про замер, на который не приглашают"
    text = visible(b)
    assert LABEL in text, f"в блоке не тот замер: {text}"
    reg = {r["key"]: r for r in catalog()["registry"]}
    assert reg[CARD]["what"] in text, "у замера в блоке нет строки «что это даст»"
    assert reg[CARD]["size"] in text, "у замера в блоке не написано, сколько это"
    ok(f"блок на экране, в нём «{LABEL}» со строкой «что это даст» и длиной")

    # Ровно один: два замера подряд — это уже список дел.
    assert len(re.findall(r'class="mine-name"', b)) == 1, \
        f"в блоке больше одного замера: {text}"
    ok("в блоке ровно один замер")

    # Замер открывается своим адресом, с человеком внутри.
    m = re.search(r'class="mine-open" href="([^"]+)"', b)
    assert m, "замер в блоке не открывается — это просто текст"
    href = m.group(1).replace("&amp;", "&")
    assert reg[CARD]["url"] in href, f"адрес замера поехал: {href}"
    assert "u=tg_777" in href, f"в адресе нет человека: {href}"
    ok("замер открывается своей страницей, человек в адресе")


def check_keys_come_from_bot() -> None:
    """2. Список ключей — перенос из `OBS_ASK_SKIP` бота."""
    c = catalog("OUT.keys = NO_INVITE;\n")
    assert c["keys"] == obs_ask_skip(), \
        f"список разошёлся с ботом: {c['keys']} против {obs_ask_skip()}"
    ok("ключи один в один из OBS_ASK_SKIP бота")

    # Берём только то, до чего человек дойдёт сам: своя страница и без второго
    # человека. Иначе блок предложил бы парный замер, который в одиночку не про то.
    c2 = catalog("""
var CARDS = buildCards(REGISTRY, {}, "2026-08-10T10:00:00Z", true);
OUT.pick = (pickNoInvite(CARDS) || {}).key || null;
OUT.chat = (pickNoInvite(CARDS.filter(function (c) {
  return c.key === "forum_scales"; })) || {}).key || null;
""")
    assert c2["pick"] == CARD, f"блок выбрал не тот замер: {c2['pick']}"
    assert c2["chat"] is None, \
        "блок предложил замер, который идёт разговором и требует второго человека"
    ok("выбирается замер со своей страницей, разговорный не берётся")


def check_done_measure_is_not_shown() -> None:
    """3. Пройденный замер не показывается: сказать про него нечего."""
    fresh = "f=" + CARD + ":2026-08-09"
    assert block(link(fresh, obs(OBS), "ask=state_week")) == "", \
        "замер пройден вчера, а блок всё равно его показывает"
    ok("свежий замер в блоке не появляется")

    # Срок вышел — снова показываем: за полгода ответы могли измениться.
    old = "f=" + CARD + ":2025-01-01"
    assert block(link(old, obs(OBS), "ask=state_week")), \
        "срок замера вышел, а блока нет"
    ok("вышел срок — замер снова виден")

    c = catalog("""
OUT.none = pickNoInvite([]);
OUT.nul = pickNoInvite(null);
""")
    assert c["none"] is None and c["nul"] is None, \
        "на пустом списке блок что-то придумал"
    ok("нет кандидата — нет блока, пустой рамки не остаётся")


def check_text_is_not_a_task() -> None:
    """4. Текст не задание и не долг."""
    b = visible(block(link(FRESH, obs(OBS), "ask=state_week")))
    for bad in DUTY_WORDS:
        assert not has_word(b.lower(), bad), f"в блоке слово-долг «{bad}»: {b}"
    ok("ни «пора», ни «нужно», ни «должен», ни счётчика")

    # Сказано, почему этого замера не было: бот про это не спрашивает сам.
    assert "не спрашиваю" in b or "не приглашаю" in b, \
        f"не сказано, почему замера не было: {b}"
    assert "ещё не было" in b, \
        f"не сказано, что этого замера у человека ещё не было: {b}"
    ok("сказано: этого ещё не было, и я про это не спрашиваю сам")

    # Ни одного балла и ни одной оценки.
    for bad in ["балл", "мало", "много", "плохо", "хорошо", "индекс", "процент"]:
        assert not has_word(b.lower(), bad), f"в блоке оценка или балл «{bad}»: {b}"
    assert "undefined" not in b and "NaN" not in b, "в блоке есть undefined или NaN"
    ok("ни балла, ни оценки, дыр нет")


def check_ask_is_still_one() -> None:
    """5. Просьба на экране по-прежнему одна."""
    assert cards_on_first(link(FRESH, obs(OBS), "ask=state_week")) == 1, \
        "карточек просьбы стало больше одной"
    assert cards_on_first(link(FRESH, obs(OBS))) == 0, \
        "просьбы нет, а карточка на экране появилась"
    ok("с просьбой одна карточка, без просьбы ни одной")

    # Блок стоит НИЖЕ просьбы: сначала то, о чём просили, потом остальное.
    whole = catalog_render(link(FRESH, obs(OBS), "ask=state_week"))
    assert whole.index('class="card"') < whole.index('class="mine"'), \
        "блок встал выше просьбы — теперь на экране две просьбы"
    ok("блок ниже просьбы")


def check_screen_order_intact() -> None:
    """6. Порядок экрана не поехал: дорожка и «Посмотреть всё» на месте."""
    whole = catalog_render(link(FRESH, obs(OBS), "ask=state_week"))
    i_mine = whole.index('class="mine"')
    i_run = whole.index('class="runall"')
    i_all = whole.index('id="all"')
    assert i_mine < i_run < i_all, \
        f"порядок экрана поехал: блок {i_mine}, дорожка {i_run}, список {i_all}"
    ok("блок · вход в дорожку · «Посмотреть всё»")

    # Между дорожкой и списком по-прежнему ничего не вклинивается: это держит
    # `glubina_first_screen.py`, здесь сторожим то же со своей стороны.
    after = whole[whole.index("</div>", i_run) + len("</div>"):]
    assert after.lstrip().startswith("<details"), \
        f"между дорожкой и «Посмотреть всё» что-то вклинилось: {after[:80]!r}"
    ok("вход в дорожку по-прежнему вплотную к списку")


# --------------------------------------------------------------------------
# Мутации: ломаем правку и смотрим, покраснеет ли проверка
# --------------------------------------------------------------------------
MUTATIONS: List[Tuple[str, str, str, str]] = [
    ("блок пропал с первого экрана",
     "    noInviteHtml(pickNoInvite(cards)) +",
     "    \"\" +",
     "check_block_shows_one_measure"),

    ("список ключей стал своей выдумкой",
     'var NO_INVITE = ["forum_scales", "state_finwell"];',
     'var NO_INVITE = ["state_finwell", "state_health"];',
     "check_keys_come_from_bot"),

    ("в блок пошёл замер, который идёт разговором",
     "    if (!c.url || c.need) continue;",
     "    if (c.need && false) continue;",
     "check_keys_come_from_bot"),

    ("блок показывает уже пройденный замер",
     '    if (c.state === "fresh") continue;',
     '    if (false) continue;',
     "check_done_measure_is_not_shown"),

    ("в текст блока вернулся долг",
     'var NO_INVITE_WHY = "Этого замера у тебя ещё не было. '
     'Сам про это не спрашиваю — тема твоя.";',
     'var NO_INVITE_WHY = "Пора пройти: этого замера у тебя ещё не было.";',
     "check_text_is_not_a_task"),

    ("блок встал выше просьбы и стал второй просьбой",
     "    firstScreenHtml(OBSERVATION, ask, BLIND_SPOT) +\n"
     "    noInviteHtml(pickNoInvite(cards)) +",
     "    noInviteHtml(pickNoInvite(cards)) +\n"
     "    firstScreenHtml(OBSERVATION, ask, BLIND_SPOT) +",
     "check_ask_is_still_one"),
]

MUST_COVER = {
    "check_block_shows_one_measure",
    "check_keys_come_from_bot",
    "check_done_measure_is_not_shown",
    "check_text_is_not_a_task",
    "check_ask_is_still_one",
}


def _one_check(name: str) -> int:
    """Прогнать одну проверку отдельным процессом: мутация живёт на диске."""
    code = ("import lib_path\n"
            "from lib import run\n"
            "import zamer_bez_priglasheniya as C\n"
            "raise SystemExit(run([getattr(C, %r)]))\n" % name)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(CHECKS) + os.pathsep + env.get("PYTHONPATH", "")
    r = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT), env=env,
                       capture_output=True, text=True, timeout=1800)
    return r.returncode


def check_every_requirement_has_a_mutation() -> None:
    """7. У каждого требования приёмки есть хотя бы одна поломка."""
    used = {m[3] for m in MUTATIONS}
    missing = MUST_COVER - used
    assert not missing, "без мутации остались: " + ", ".join(sorted(missing))
    ok(f"{len(MUST_COVER)} требований закрыты мутациями")


def check_mutations_are_caught() -> None:
    """8. Каждая поломка ловится проверкой, и страница возвращается на место."""
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
    check_block_shows_one_measure,
    check_keys_come_from_bot,
    check_done_measure_is_not_shown,
    check_text_is_not_a_task,
    check_ask_is_still_one,
    check_screen_order_intact,
]

if __name__ == "__main__":
    fns = list(CHECKS_LIST)
    if not os.environ.get("BEZ_PRIGLASHENIYA_ONE"):
        fns += [check_every_requirement_has_a_mutation, check_mutations_are_caught]
    raise SystemExit(run(fns))
