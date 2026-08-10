# -*- coding: utf-8 -*-
"""Проверки: «Нечего добавить» — это ответ, а не отсутствие ответа.

Спека 020, История 3. Страница `state-note/app.html` («Что ещё стоит знать»).

Живой дефект, 10.08.2026. Владелец прошёл недельный замер и нажал «Нечего
добавить». В базе строки нет, карточка в каталоге не подсветилась как пройденная,
недельный ритм позовёт снова.

Причина. Пустой текст давал `built.has = false`, и страница не писала НИЧЕГО.
Правило «пустая точка хуже отсутствия» верное для линии графика и неверное для
факта прохождения: человек работу сделал, а система считает, что он не приходил.

Что проверяется:
  · нажал «Нечего добавить» — уходит одна строка с признаком `nothing_to_add`;
  · в строке нет ни числа, ни текста, ни имени шкалы: точку в линии рисовать
    нечем физически, а не по обещанию в тексте;
  · открыл и ушёл, ничего не нажав — записи нет. Отличие «нажал» от «ушёл»
    держится на том, что у ушедшего в ответах пусто;
  · написал текст — прежняя запись, признака «нечего добавить» в ней нет;
  · экран результата говорит, что отметка записана и точки в истории не будет;
  · карточка после такой строки считается пройденной: срок годности читается
    ровно так же, как у любой другой записи;
  · пять нажатий подряд дают одну строку — замок и одна точка за период целы;
  · поломки ловятся: каждое требование закрыто мутацией.

Проверки исполняют страницу целиком в node: заглушки подменяют браузер, Телеграм
и базу. База в заглушке с первичным ключом — занятый номер отвечает 409, поэтому
«одна точка за период» проверяется поведением, а не словами.

Запуск:  python3 checks/nechego_dobavit.py
"""

import hashlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
from lib import ROOT, bot_reader, catalog, ok, run, visible
from zamery_v_miniappe import page

CHECKS = Path(__file__).resolve().parent
APP = "state-note/app.html"
BLOCK = "state_note"

# Имя поля. Честное: «добавить было нечего». Ни числа, ни шкалы рядом с ним.
FIELD = "nothing_to_add"

# Что человек читает после того, как нажал «Нечего добавить». Два обязательных
# факта: отметка записана и точки в истории не будет.
MUST_SAY = ["записана", "точки"]

# Слова, которых на этом экране быть не может: человек ответил, а не сбежал.
BAD_WORDS = ["Пропустил", "пропустил", "не записал", "мало", "плохо", "лень",
             "забросил", "должен", "балл"]

# Ждём, пока отправка дойдёт до конца: нажатие зовёт `finish()` и не ждёт его.
WAIT = "  await new Promise(function (r) { setTimeout(r, 30); });\n"

SKIP = "  startCard();\n  byId('skipStep').click();\n" + WAIT


def rows_of(got: Dict) -> List[Dict]:
    return got["rows"]


def only_row(got: Dict) -> Dict:
    rows = rows_of(got)
    assert len(rows) == 1, f"строк в базе {len(rows)}, а не одна: {rows}"
    return rows[0]


def numbers_in(value, path: str = "scores") -> List[str]:
    """Все числа внутри записи, с путями. Число значит точку в линии."""
    out: List[str] = []
    if isinstance(value, bool):
        return out
    if isinstance(value, (int, float)):
        return [path]
    if isinstance(value, dict):
        for k, v in value.items():
            out += numbers_in(v, f"{path}.{k}")
    if isinstance(value, list):
        for i, v in enumerate(value):
            out += numbers_in(v, f"{path}[{i}]")
    return out


# --------------------------------------------------------------------------


def check_skip_writes_a_row() -> None:
    """1. «Нечего добавить» пишет одну строку с честным признаком."""
    got = page(BLOCK, SKIP + "  OUT.screen = screen();")
    row = only_row(got)
    assert row["block"] == BLOCK, f"строка ушла в чужой блок: {row['block']}"
    assert row["instrument"] == BLOCK, f"подпись инструмента: {row['instrument']}"
    assert row["scores"].get(FIELD) is True, \
        f"в строке нет признака «{FIELD}»: {row['scores']}"
    assert row["completed_at"], "у строки нет времени — карточка не станет пройденной"
    ok(f"нажал «Нечего добавить» — одна строка с {FIELD}")

    assert set(row["scores"]) == {FIELD, "source"}, \
        f"в записи лишние поля: {sorted(row['scores'])}"
    assert row["scores"]["source"] == "manual", \
        f"источник записи поехал: {row['scores']['source']}"
    assert row["answers"] == {}, f"в ответах что-то есть: {row['answers']}"
    ok("в записи только признак и источник, ответы пустые")


def check_row_draws_no_point() -> None:
    """2. Такая строка не рисует точку и не превращается в число."""
    row = only_row(page(BLOCK, SKIP))
    nums = numbers_in(row["scores"])
    assert not nums, f"в записи есть числа — из них соберётся точка: {nums}"
    assert "note" not in row["scores"], \
        "рядом с признаком лежит заметка — панель нарисует пустую цитату"
    ok("в записи нет ни одного числа и ни одной заметки")

    # Пустой текст догадкой не сохраняется: конституция, «догадки не сохраняются
    # как данные». Сказать было нечего — значит нечего и класть.
    assert '""' not in str(row["scores"]), f"в записи пустая строка: {row['scores']}"
    ok("пустого текста в записи нет")


def check_leaving_writes_nothing() -> None:
    """3. Открыл и ушёл, ничего не нажав — записи нет."""
    got = page(BLOCK, "  startCard();\n" + WAIT)
    assert rows_of(got) == [], \
        f"человек ничего не нажал, а в базу ушла запись: {rows_of(got)}"
    ok("открыл замер и ушёл — записи нет")

    # И даже если отправка случилась сама: без нажатия отметки писать нечего.
    got2 = page(BLOCK, "  startCard();\n  await finish();\n  OUT.screen = screen();")
    assert rows_of(got2) == [], \
        f"пустая отправка создала запись: {rows_of(got2)}"
    ok("пустая отправка по-прежнему ничего не пишет")

    # Отличие явное: у нажавшего в ответах этого захода стоит отметка.
    got3 = page(BLOCK, SKIP + "  OUT.answers = answers;")
    assert got3["answers"], \
        "после нажатия в ответах захода пусто — «нажал» не отличить от «ушёл»"
    ok("«нажал» и «ушёл» различаются по ответам захода")


def check_text_row_unchanged() -> None:
    """4. Написал текст — запись прежняя, признака в ней нет."""
    got = page(BLOCK, """
  startCard();
  setAnswer('text', 'спина отвалилась и завал в отчётах');
  await finish();
""")
    row = only_row(got)
    assert row["scores"]["note"]["text"] == "спина отвалилась и завал в отчётах", \
        f"текст в записи поехал: {row['scores']}"
    assert FIELD not in row["scores"], \
        f"человек написал текст, а в записи признак «нечего добавить»: {row['scores']}"
    assert row["answers"]["raw"], "сырой ответ пропал из записи"
    ok("текстовая запись прежняя, признака в ней нет")


def check_result_screen_is_honest() -> None:
    """5. Экран результата говорит: отметка записана, точки не будет."""
    got = page(BLOCK, SKIP + "  OUT.screen = screen();")
    text = visible(got["screen"])
    for part in MUST_SAY:
        assert part in text, f"на экране результата нет «{part}»: {text[:220]}"
    ok("сказано: отметка записана и точки в истории не будет")

    for bad in BAD_WORDS:
        assert bad not in text, f"на экране слово «{bad}»: {text[:220]}"
    ok("ни «Пропустил», ни оценок, ни вины")

    assert "undefined" not in text and "NaN" not in text, \
        "на экране результата есть undefined или NaN"
    ok("экран собирается без дыр")


def check_card_counts_as_done() -> None:
    """6. Карточка после такой строки считается пройденной."""
    c = catalog("""
OUT.fresh = freshness("2026-08-10T09:00:00Z", 7, "2026-08-10T21:00:00Z", true);
OUT.week  = freshness("2026-08-01T09:00:00Z", 7, "2026-08-10T21:00:00Z", true);
OUT.never = freshness(null, 7, "2026-08-10T21:00:00Z", true);
""")
    assert c["fresh"]["state"] == "fresh", \
        f"свежая запись не считается пройденной: {c['fresh']}"
    assert c["never"]["state"] == "never", \
        f"отсутствие записи перестало отличаться от записи: {c['never']}"
    assert c["week"]["state"] == "due", \
        f"через девять дней срок обязан выйти: {c['week']}"
    ok("запись за эту неделю — пройдено, ритм позовёт только через неделю")

    # Строка отдаёт дату тем же полем, по которому каталог считает свежесть.
    row = only_row(page(BLOCK, SKIP))
    assert row["completed_at"].startswith("20") and "T" in row["completed_at"], \
        f"время записи не в том виде, по которому считается свежесть: {row['completed_at']}"
    ok("время записи в том же виде, что у остальных замеров")


def check_one_row_on_five_taps() -> None:
    """7. Пять отправок подряд добавляют одну строку: замок держит.

    ПЕРЕПИСАНО 10.08.2026, спека 023. Раньше одну строку спасал не замок, а
    номер записи: у всех пяти отправок он был один, и база отбивала лишние
    ответом 409. Теперь номер у каждой отправки свой, и держать нажатия обязан
    именно замок — без него пять тапов дадут пять строк.
    """
    got = page(BLOCK, SKIP + """
  var before = globalThis.DB.rows.length;
  await Promise.all([finish(), finish(), finish(), finish(), finish()]);
  OUT.before = before;
  OUT.posts = globalThis.CALLS.filter(function (c) { return c.method === 'POST'; }).length;
""")
    assert got["before"] == 1, \
        f"до пяти нажатий строк {got['before']}, а должна быть одна — от «нечего добавить»"
    added = len(rows_of(got)) - got["before"]
    assert added == 1, f"пять нажатий добавили {added} строк, а не одну"
    assert got["posts"] == 2, \
        f"в сеть ушло {got['posts']} вставок вместо двух — замок не держит"
    ok("пять нажатий подряд добавляют одну строку, лишние отбиты до запроса")

    # ПЕРЕПИСАНО 10.08.2026, спека 023. Было: второй заход в том же периоде
    # правит ту же строку. Отменено — ключ страниц умеет только вставлять, и
    # правка оборачивалась молчаливым отказом «Не удалось сохранить».
    #
    # Стало: второй заход кладёт свою строку, а «одна точка за период» держится
    # на чтении. Замок на пяти нажатиях от этого никуда не делся: он про одно
    # нажатие, а не про повтор через день.
    got2 = page(BLOCK, SKIP + """
  await new Promise(function (r) { setTimeout(r, 5); });
  knownExisting = false;
""" + SKIP + """
  OUT.ids = globalThis.DB.rows.map(function (r) { return r.id; });
  OUT.other = globalThis.CALLS.filter(function (c) { return c.method !== 'POST'; }).length;
""")
    assert len(rows_of(got2)) == 2, \
        f"второй заход не записался: строк {len(rows_of(got2))}, ids {got2['ids']}"
    assert len(set(got2["ids"])) == 2, \
        f"две строки ушли под одним номером: {got2['ids']}"
    assert got2["other"] == 0, \
        f"страница ходит в базу не только вставкой: {got2['other']} прочих запросов"
    R = bot_reader()
    best = R["latest_per_period"](rows_of(got2), R["CARD_DAYS"].get(BLOCK))
    assert len(best) == 1, f"за период осталось {len(best)} точек, а не одна"
    assert best[0]["completed_at"] == max(r["completed_at"] for r in rows_of(got2)), \
        "в линии не последняя запись периода"
    ok("второй заход в том же периоде пишет свою строку, а в линии одна точка")


# --------------------------------------------------------------------------
# Мутации: ломаем правку и смотрим, покраснеет ли проверка
# --------------------------------------------------------------------------
# Конституция, принцип II: проверка обязана падать при сломанной логике.
MUTATIONS: List[Tuple[str, str, str, str]] = [
    ("«Нечего добавить» снова ничего не пишет",
     '  if (!body) {\n    return a.nothing === true\n'
     '      ? { scores: { nothing_to_add: true, source: "manual" }, has: true, nothing: true }\n'
     '      : { scores: {}, has: false };\n  }',
     '  if (!body) return { scores: {}, has: false };',
     "check_skip_writes_a_row"),

    ("кнопка перестала помечать «нечего добавить»",
     '    if (s.skipMeans) answers[s.skipMeans] = true;',
     '    if (false) answers[s.skipMeans] = true;',
     "check_skip_writes_a_row"),

    ("отметка превратилась в число",
     'scores: { nothing_to_add: true, source: "manual" }, has: true, nothing: true }',
     'scores: { nothing_to_add: 0, source: "manual" }, has: true, nothing: true }',
     "check_row_draws_no_point"),

    ("рядом с отметкой поехал пустой текст",
     '      ? { scores: { nothing_to_add: true, source: "manual" }, has: true, nothing: true }',
     '      ? { scores: { nothing_to_add: true, note: { text: "" }, source: "manual" },'
     ' has: true, nothing: true }',
     "check_row_draws_no_point"),

    ("запись уходит и от того, кто просто ушёл",
     '    return a.nothing === true\n',
     '    return true\n',
     "check_leaving_writes_nothing"),

    ("экран результата больше не говорит, что записал и что точки не будет",
     '  "Отметка записана. В истории точки за эту неделю не будет: '
     'цифры в этом ответе нет."];',
     '  "Готово."];',
     "check_result_screen_is_honest"),
]

MUST_COVER = {
    "check_skip_writes_a_row",
    "check_row_draws_no_point",
    "check_leaving_writes_nothing",
    "check_result_screen_is_honest",
}


def _one_check(name: str) -> int:
    """Прогнать одну проверку отдельным процессом: мутация живёт на диске."""
    code = ("import lib_path\n"
            "from lib import run\n"
            "import nechego_dobavit as C\n"
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
    check_skip_writes_a_row,
    check_row_draws_no_point,
    check_leaving_writes_nothing,
    check_text_row_unchanged,
    check_result_screen_is_honest,
    check_card_counts_as_done,
    check_one_row_on_five_taps,
]

if __name__ == "__main__":
    fns = list(CHECKS_LIST)
    if not os.environ.get("NECHEGO_ONE"):
        fns += [check_every_requirement_has_a_mutation, check_mutations_are_caught]
    raise SystemExit(run(fns))
