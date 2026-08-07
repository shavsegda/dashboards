# -*- coding: utf-8 -*-
"""Проверки: месячный замер разъехался по своим ритмам.

Задача (фича 004). В месячном мини-аппе стояли девять инструментов и 81 вопрос.
В месяце остаются два — стресс и сон. Остальные уезжают:

  настроение, тревога, разгон  → условная карточка `state_clinical`
  алкоголь                     → годовой ритм `state_year`
  потребности                  → своя карточка `state_needs`, квартальный ритм
  команда                      → своя карточка `state_team`
  дистанция (децентрация)      → пока негде, см. `check_eq_has_no_home`

Главное, что проверяем: инструмент не просто удалён из месячного, а **приехал**
в свою страницу, с теми же пунктами и теми же ключами полей. Иначе получится не
разъезд, а потеря замера.

Запуск:  python3 checks/state_month_split.py
"""

import lib_path  # noqa: F401
from lib import (bot, block_paths, dig, form_app, form_render, html,
                 inline_script, ok, run)

MONTH = "state-month/app3.html"
CLINICAL = "state-clinical/app.html"
YEAR = "state-year/app.html"
TEAM = "state-team/app.html"
NEEDS = "state-needs/app.html"
QUARTER = "state-quarter/app3.html"

# Куда какой инструмент уехал: ключ теста → (файл, блок базы, сколько пунктов).
# Числа пунктов прибиты руками: при копировании теряется именно пункт, и
# посчитать их из самого файла значит согласиться с потерей.
MOVED = {
    "phq": (CLINICAL, "state_clinical", 9),
    "gad": (CLINICAL, "state_clinical", 7),
    "asrm": (CLINICAL, "state_clinical", 5),
    "audit": (YEAR, "state_year", 3),
    "bpnsfs": (NEEDS, "state_needs", 24),
    "safety": (TEAM, "state_team", 7),
}

# Что остаётся в месячном.
MONTH_KEEP = {"pss": 10, "isi": 7}

# Поля, которые должны остаться теми же после переезда.
FIELDS = {
    "phq": {"total", "item9", "item9_flag", "alert"},
    "gad": {"total", "alert"},
    "asrm": {"total", "alert"},
    "audit": {"total", "alert", "threshold", "sex_asked"},
    "eq": {"mean"},
    "safety": {"mean"},
    "pss": {"total"},
    "isi": {"total", "alert"},
}

# Дословные куски пунктов: их легко потерять при копировании, и потеря меняет
# сам инструмент. Проверяем по одному самому важному на каждый переезд.
QUOTES = {
    CLINICAL: [
        "Вас посещали мысли о том, что Вам лучше было бы умереть",   # PHQ-9, п. 9
        "Вы испытывали страх, словно должно произойти нечто ужасное",  # GAD-7, п. 7
        "Мне не нужно меньше сна, чем обычно.",                        # ASRM
    ],
    YEAR: [
        "Одна стандартная порция — 10 г чистого спирта",   # инструкция AUDIT-C
        "Как часто Вы употребляете алкогольные напитки?",
    ],
    TEAM: [
        "Если в этой команде ты ошибаешься, это часто ставят тебе в вину.",
        "В работе с этой командой мои умения и таланты ценят и используют.",
    ],
    NEEDS: [
        "В последний месяц я чувствовал свободу и возможность выбора в том, за что берусь.",
        "В последний месяц я чувствовал себя неудачником из-за своих ошибок.",
    ],
}

FILL_ALL = "api.TESTS.forEach(t => fill(t.key, null));\nOUT.scores = api.buildScores();"

# Расхождение, которое было до этой работы и остаётся: квартальный мини-апп
# пишет «support.significant_other», а бот читает «support.significant». Линия
# «Поддержка: близкий» в панели из-за этого пустая. Квартальный файл этой
# работой не трогается, расхождение записано в отчёте.
KNOWN_MISMATCH: dict = {}


def check_month_is_short() -> None:
    """1. В месячном остались стресс и сон."""
    app = form_app(MONTH, FILL_ALL)
    assert app["keys"] == list(MONTH_KEEP), \
        f"в месячном не только стресс и сон: {app['keys']}"
    ok("в месячном ровно два теста: напряжение и сон")

    total = sum(app["sizes"])
    assert total == sum(MONTH_KEEP.values()), \
        f"вопросов в месячном {total}, а должно быть {sum(MONTH_KEEP.values())}"
    ok(f"вопросов в месячном {total} вместо 81")

    src = inline_script(MONTH)
    for key in MOVED:
        assert f"key: '{key}'" not in src, f"тест «{key}» всё ещё объявлен в месячном"
    for gone in ("scorePhq", "scoreGad", "scoreAudit", "scoreAsrm",
                 "scoreBpnsfs", "scoreEq", "scoreSafety",
                 "SCALE_PHQ", "SCALE_BPNSFS", "SCALE_SAFETY", "SCALE_EQ"):
        assert gone not in src, f"в месячном остался мёртвый кусок «{gone}»"
    ok("подсчёт и шкалы уехавших инструментов из месячного убраны")

    for word in ("PHQ-9", "GAD-7", "AUDIT", "ASRM", "BPNSFS", "Эдмондсон"):
        assert word not in app["instrument"], \
            f"в подписи инструмента месячного всё ещё «{word}»: {app['instrument']}"
    ok(f"подпись инструмента честная: {app['instrument']}")

    body = html(MONTH)
    for quotes in QUOTES.values():
        for q in quotes:
            assert q not in body, f"в месячном остался уехавший пункт: «{q[:40]}…»"
    ok("ни одного уехавшего пункта в тексте месячной страницы")


def check_month_record() -> None:
    """2. Запись месячного: ровно два инструмента, ключи прежние."""
    b = bot()
    app = form_app(MONTH, FILL_ALL)
    scores = app["scores"]
    assert set(scores) - {"source", "alert"} == set(MONTH_KEEP), \
        f"в записи месячного не только стресс и сон: {sorted(scores)}"
    for key in MONTH_KEEP:
        got = set(scores[key]) - {"band", "nums"}
        assert got == FIELDS[key], f"поля «{key}» поехали: {sorted(got)}"
    ok("в записи месячного только pss и isi, поля прежние")

    for path in block_paths(b, "state_month"):
        assert dig(scores, path) is not None, \
            f"бот читает «{path}» из state_month, а мини-апп его не пишет"
    ok("оба поля, которые бот читает из месяца, мини-апп пишет")

    assert app["block"] == "state_month", f"блок базы поехал: {app['block']}"
    ok("блок базы прежний")


def check_stale_keys_dropped() -> None:
    """3. Уехавший ответ из памяти телефона в месячный больше не уходит.

    У всех, кто проходил месячный раньше, ответы про настроение и алкоголь
    лежат в памяти телефона. Если сборка записи идёт по всему, что накопилось,
    старая цифра уезжает в базу как свежая. Это и есть «догадки не сохраняются
    как данные»: конституция.
    """
    extra = (
        "fill('pss', 2);\n"
        "api.results['phq'] = { nums: [], band: 'старое', c: 'warn',\n"
        "  data: { total: 22, alert: true }, answers: {},\n"
        "  completed_at: '2026-06-01T10:00:00.000Z' };\n"
        "OUT.scores = api.buildScores();\n"
        "OUT.answers = api.buildAnswers();\n"
    )
    app = form_app(MONTH, extra)
    assert "phq" not in app["scores"], "старый ответ про настроение уехал в месячный"
    assert "phq" not in app["answers"], "старые ответы про настроение уехали в базу"
    assert app["scores"].get("alert") is not True, \
        "старый чужой сигнал поднял общий флаг тревоги месячного"
    assert "pss" in app["scores"], "вместе с чужим ключом выкинуло свой"
    ok("чужой ключ отброшен и флаг тревоги не поднимает")


def check_moved_arrived() -> None:
    """4. Каждый уехавший инструмент приехал: страница, блок, пункты, поля."""
    b = bot()
    seen: dict = {}
    for rel in (CLINICAL, YEAR, TEAM, NEEDS):
        app = form_app(rel, FILL_ALL)
        seen[rel] = app

    for key, (rel, block, count) in MOVED.items():
        app = seen[rel]
        assert key in app["keys"], f"«{key}» не приехал в {rel}: {app['keys']}"
        got = app["sizes"][app["keys"].index(key)]
        assert got == count, f"у «{key}» в {rel} стало {got} пунктов вместо {count}"
        assert app["block"] == block, \
            f"{rel} пишет в блок «{app['block']}», а бот ждёт «{block}»"
        if key in FIELDS:
            fields = set(app["scores"][key]) - {"band", "nums"}
            assert fields == FIELDS[key], \
                f"поля «{key}» после переезда поехали: {sorted(fields)}"
    ok(f"все {len(MOVED)} инструментов на месте: пункты и поля прежние")

    # Ключи полей — буквально как в bot.py, по каждому новому блоку.
    for rel, app in seen.items():
        want = block_paths(b, app["block"])
        missing = {p for p in want if dig(app["scores"], p) is None}
        known = KNOWN_MISMATCH.get(app["block"], set())
        assert missing == known, \
            (f"расхождения {rel} с bot.py по блоку {app['block']}: "
             f"{sorted(missing)} вместо {sorted(known)}")
    ok("все поля, которые бот читает из новых блоков, мини-аппы пишут")

    # Дословные пункты не потерялись при копировании.
    for rel, quotes in QUOTES.items():
        body = html(rel)
        for q in quotes:
            assert q in body, f"в {rel} нет пункта «{q[:40]}…»"
    ok("дословные формулировки пунктов на месте")


def check_bpnsfs_structure() -> None:
    """5. Потребности не потеряли подшкалы: по четыре пункта на каждую."""
    extra = ("fill('bpnsfs', 3);\nOUT.scores = api.buildScores();\n"
             "OUT.subs = api.TESTS.find(t => t.key === 'bpnsfs').items"
             ".reduce((a, i) => (a[i.s] = (a[i.s] || 0) + 1, a), {});")
    app = form_app(NEEDS, extra)
    assert app["subs"] == {"as": 4, "af": 4, "cs": 4, "cf": 4, "rs": 4, "rf": 4}, \
        f"подшкалы потребностей поехали: {app['subs']}"
    ok("шесть подшкал по четыре пункта")

    b = app["scores"]["bpnsfs"]
    for field in ("autonomy_satisfaction", "autonomy_frustration",
                  "competence_satisfaction", "competence_frustration",
                  "relatedness_satisfaction", "relatedness_frustration",
                  "satisfaction", "frustration"):
        assert field in b, f"в записи потребностей нет поля «{field}»"
    ok("все восемь полей потребностей на месте")

    # Обратные пункты Эдмондсона: их три, и без них среднее считается наоборот.
    extra2 = ("OUT.rev = api.TESTS.find(t => t.key === 'safety').items"
              ".filter(i => i.rev).length;\nfill('safety', 7);\n"
              "OUT.scores = api.buildScores();")
    team = form_app(TEAM, extra2)
    assert team["rev"] == 3, f"обратных пунктов у команды {team['rev']}, а не три"
    # Все ответы «7»: четыре прямых дают 7, три обратных — по 1. Среднее 4,43.
    assert team["scores"]["safety"]["mean"] == 4.43, \
        f"подсчёт команды поехал: {team['scores']['safety']}"
    ok("у команды три обратных пункта, подсчёт прежний")


def check_quarter_untouched() -> None:
    """6. Квартальный мини-апп этой работой не тронут.

    Его как раз разбирают на отдельные карточки в `bot.py` — потребности,
    смысл, выгорание, поддержку, осознанность. Лезть туда сейчас значит
    столкнуться с чужой работой посреди неё.
    """
    app = form_app(QUARTER, FILL_ALL)
    want = ["swls", "mlq", "ffmq", "rses", "olbi", "support"]
    assert app["keys"] == want, f"состав квартального поехал: {app['keys']}"
    assert app["block"] == "state_quarter", f"блок квартала поехал: {app['block']}"
    ok("в квартале прежние шесть тестов и прежний блок")


def check_eq_has_no_home() -> None:
    """7. Дистанцию (децентрацию) сейчас собирать негде — и это записано.

    В bot.py её новый дом — карточка «Осознанность» (блок `state_mind`): там
    она стоит вместе с осознанностью и открывается только тому, кто практикует.
    Пока такой страницы нет, и вопросы про дистанцию не задаёт никто. Лучше
    пусто, чем писать их в блок, который бот не читает.

    Проверка падает, когда дом появится: это сигнал вернуться и убрать её.
    """
    homes = []
    for rel in (MONTH, CLINICAL, YEAR, TEAM, NEEDS, QUARTER):
        if "eq" in form_app(rel)["keys"]:
            homes.append(rel)
    assert not homes, f"дистанция появилась в {homes} — пора обновить проверку"
    ok("дистанция ни в одном мини-аппе: дом ждёт карточку «Осознанность»")


def check_pages_render() -> None:
    """9. Каждая страница собирается: список тестов виден, пустых полей нет."""
    want = {
        MONTH: ["Напряжение", "Сон"],
        CLINICAL: ["Настроение", "Тревога", "Разгон"],
        YEAR: ["Алкоголь"],
        TEAM: ["Команда"],
        NEEDS: ["Потребности"],
    }
    for rel, titles in want.items():
        h = form_render(rel)
        assert "undefined" not in h and "NaN" not in h, \
            f"в собранной странице {rel} есть undefined или NaN"
        for t in titles:
            assert f">{t}<" in h, f"на странице {rel} нет теста «{t}»"
    ok(f"все {len(want)} страниц собираются и показывают свои тесты")


def check_one_home_per_instrument() -> None:
    """8. Один инструмент — одна дверь. Дважды не спрашиваем."""
    where: dict = {}
    for rel in (MONTH, CLINICAL, YEAR, TEAM, NEEDS, QUARTER, "state-week/app4.html"):
        for key in form_app(rel)["keys"]:
            where.setdefault(key, []).append(rel)
    twice = {k: v for k, v in where.items() if len(v) > 1}
    assert not twice, f"инструмент спрашивают из двух мест: {twice}"
    ok(f"все {len(where)} инструментов живут ровно в одном мини-аппе")

    # Ключи хранения у каждой страницы свои: иначе результаты одной страницы
    # подмешаются в запись другой через память телефона и облако.
    keys: dict = {}
    for rel in (MONTH, CLINICAL, YEAR, TEAM, NEEDS, QUARTER, "state-week/app4.html"):
        for k in form_app(rel)["storeKeys"]:
            keys.setdefault(k, []).append(rel)
    shared = {k: v for k, v in keys.items() if len(v) > 1}
    assert not shared, f"две страницы делят ключ хранения: {shared}"
    ok("ключи хранения у каждой страницы свои")


if __name__ == "__main__":
    raise SystemExit(run([
        check_month_is_short, check_month_record, check_stale_keys_dropped,
        check_moved_arrived, check_bpnsfs_structure, check_quarter_untouched,
        check_eq_has_no_home, check_pages_render,
        check_one_home_per_instrument,
    ]))
