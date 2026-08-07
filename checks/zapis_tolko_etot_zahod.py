# -*- coding: utf-8 -*-
"""Проверки: в базу уходят ТОЛЬКО тесты, отвеченные в этом заходе.

Дефект, который портил данные. Алексей открыл квартальный замер, ответил только
на вопросы про поддержку — а в базу уехала запись, где рядом с новой поддержкой
лежали ВСЕ остальные шкалы квартала со значениями его замера от 3 августа.
Он их в тот день не отвечал.

Причина. Словарь `results` живёт в памяти телефона (`RESULT_KEY`) и поднимается
из облака (`restoreFromCloud`), а сборка записи шла по ВСЕМУ `results`. Значит
один ответ отправлял заодно все прошлые как свежие, и в линии появлялись точки,
которых человек не давал. Тренд рисовался по выдуманным данным — то есть вся
затея с линиями теряла смысл.

Прежняя защита `ownKeys()` отсекала УБРАННЫЕ тесты. Это другой случай: она не
знала, что тест не отвечали сейчас.

Правило: в запись попадают только ключи этого захода (`sessionKeys`). Прошлые
результаты остаются лежать локально — по ним считается строка «с прошлым
разом», — но в базу не уезжают никогда. Ни одного ответа в заходе — записи нет.

Проверки смотрят на ТЕЛО запроса к базе: не «как написан код», а что реально
уходит по сети.

Запуск:  python3 checks/zapis_tolko_etot_zahod.py
"""

import re

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
from lib import app_run, form_app, html, inline_script, ok, run

# Все страницы, которые собирают запись из нескольких тестов.
PAGES = [
    "state-quarter/app3.html",
    "state-month/app3.html",
    "state-week/app4.html",
    "state-clinical/app.html",
    "state-year/app.html",
    "state-team/app.html",
    "state-needs/app.html",
    "selfhood/app.html",
]

# Страницы, где тестов больше одного: только на них видно «один из шести».
MULTI = [p for p in PAGES]

# Так выглядит результат прошлого захода: он лежит в памяти телефона или пришёл
# из облака. В запись он попасть не должен.
OLD = "2026-08-03T10:00:00.000Z"

PRIOR_JS = """
  // Кладём в results прошлые результаты — ровно так они и поднимаются из памяти
  // телефона и из Telegram CloudStorage. Ключ «отвечено сейчас» не ставим.
  TESTS.slice(1).forEach(function (t) {
    results[t.key] = { nums: [11], band: 'старое', c: 'ok',
                       data: { total: 11 }, answers: { 0: 1 },
                       completed_at: '%s' };
  });
  saveResultsLocal();
""" % OLD


def pushed(rel: str, js: str) -> list:
    """Тела запросов, которые страница отправила в базу."""
    got = app_run(rel, js + "\n  OUT.pushed = PUSHED.map(function (p) { return p.body; });")
    return got["pushed"]


# --------------------------------------------------------------------------


def check_one_test_one_record() -> None:
    """1. Ответ на один тест даёт запись ровно с одним тестом."""
    for rel in MULTI:
        keys = form_app(rel)["keys"]
        if len(keys) < 2:
            continue
        rows = pushed(rel, PRIOR_JS + """
  await __pass(TESTS[0].key, null);
""")
        assert len(rows) == 1, f"{rel}: запросов к базе {len(rows)}, а не один"
        scores = rows[0]["scores"]
        answers = rows[0]["answers"]
        got = sorted(k for k in scores if k not in ("source", "alert"))
        assert got == [keys[0]], \
            f"{rel}: в запись уехали тесты {got}, а отвечали только «{keys[0]}»"
        assert sorted(answers) == [keys[0]], \
            f"{rel}: в ответах уехало {sorted(answers)}"
        assert scores.get("source") == "manual", f"{rel}: пропала метка источника"
    ok("ответ на один тест: в записи один тест и его ответы")


def check_memory_and_cloud_never_travel() -> None:
    """2. Поднятое из памяти телефона и из облака в запись не попадает."""
    for rel in MULTI:
        keys = form_app(rel)["keys"]
        if len(keys) < 2:
            continue
        rows = pushed(rel, PRIOR_JS + """
  await __pass(TESTS[0].key, null);
""")
        body = rows[0]
        for key in keys[1:]:
            assert key not in body["scores"], \
                f"{rel}: прошлый результат «{key}» уехал в базу как свежий"
            assert key not in body["answers"], \
                f"{rel}: прошлые ответы «{key}» уехали в базу"
        assert str(body["completed_at"]) != OLD, \
            f"{rel}: у записи чужая дата — {body['completed_at']}"
    ok("прошлые результаты остались лежать локально")

    # То же для облака: восстановление кладёт данные в тот же results, и путь
    # проверяется тем же способом — через настоящий CloudStorage-обработчик.
    rel = "state-quarter/app3.html"
    rows = pushed(rel, """
  // Заглушка облака отдаёт прошлый квартал целиком, как живой Телеграм.
  var cloud = {};
  TESTS.slice(1).forEach(function (t) {
    cloud[t.key] = { nums: [11], band: 'старое', c: 'ok', data: { total: 11 },
                     answers: { 0: 1 }, completed_at: '%s' };
  });
  globalThis.window.Telegram = { WebApp: { CloudStorage: {
    getItem: function (k, cb) { cb(null, JSON.stringify(cloud)); },
    setItem: function (k, v, cb) { cb && cb(null, true); }
  } } };
  await restoreFromCloud();
  await __pass(TESTS[0].key, null);
""" % OLD)
    assert len(rows) == 1, f"{rel}: запросов к базе {len(rows)}"
    got = sorted(k for k in rows[0]["scores"] if k not in ("source", "alert"))
    assert got == [form_app(rel)["keys"][0]], \
        f"{rel}: из облака в базу уехало {got}"
    ok("восстановление из облака в базу не уезжает")


def check_empty_session_no_record() -> None:
    """3. Пустой заход не создаёт записи."""
    for rel in MULTI:
        rows = pushed(rel, PRIOR_JS)
        assert rows == [], \
            f"{rel}: страницу открыли и ничего не ответили, а в базу ушло {len(rows)}"
    ok("открыли и вышли: в базу не ушло ничего")

    # Заслонка внутри store: ключа нет в реестре страницы — писать нечего.
    # На квартальной странице записью занимается сам finish(), функции store нет.
    for rel in MULTI:
        if "async function store(" not in inline_script(rel):
            continue
        rows = pushed(rel, PRIOR_JS + """
  await store('ключа_нет_в_реестре', { nums: [], band: 'x', c: 'ok', data: {} }, {});
""")
        assert rows == [], f"{rel}: запись ушла по ключу, которого нет в реестре"
    ok("ключ вне реестра страницы записи не создаёт")


def check_alert_flag_is_from_this_session() -> None:
    """3a. Флаг тревоги в записи считается по этому заходу, а не по прошлому."""
    for rel in PAGES:
        src = inline_script(rel)
        if "scores.alert" not in src:
            continue
        assert "scores.alert = sessionAlert();" in src, \
            f"{rel}: флаг тревоги в записи считается по всему results"
        i = src.index("function sessionAlert()")
        body = src[i:src.index("\n}", i)]
        assert "sessionKeys()" in body, \
            f"{rel}: sessionAlert ходит не по ключам захода"
    ok("флаг тревоги в записи — только по тестам захода")

    # Живьём: прошлый тест с тревогой лежит в памяти, сегодня отвечен другой —
    # запись не должна поднимать чужой сигнал сегодняшней датой.
    rel = "state-clinical/app.html"
    rows = pushed(rel, """
  results['phq'] = { nums: [20], band: 'старое', c: 'alarm',
                     data: { total: 20, alert: true }, answers: { 0: 3 },
                     completed_at: '%s' };
  saveResultsLocal();
  await __pass('asrm', null);
""" % OLD)
    assert len(rows) == 1, f"{rel}: запросов {len(rows)}"
    assert rows[0]["scores"].get("alert") is False, \
        "тревога из прошлого замера уехала в сегодняшнюю запись"
    assert "phq" not in rows[0]["scores"], "прошлый тест уехал вместе с тревогой"
    ok("тревога прошлого замера не попадает в сегодняшнюю запись")


def check_second_answer_adds_only_itself() -> None:
    """4. Два теста за заход — в записи ровно эти два, не больше."""
    for rel in MULTI:
        keys = form_app(rel)["keys"]
        if len(keys) < 3:
            continue
        rows = pushed(rel, PRIOR_JS + """
  await __pass(TESTS[0].key, null);
  await __pass(TESTS[1].key, null);
""")
        assert len(rows) == 2, f"{rel}: запросов {len(rows)}, а не два"
        first = sorted(k for k in rows[0]["scores"] if k not in ("source", "alert"))
        second = sorted(k for k in rows[1]["scores"] if k not in ("source", "alert"))
        assert first == [keys[0]], f"{rel}: первая запись {first}"
        assert second == sorted(keys[:2]), \
            f"{rel}: вторая запись {second} вместо {sorted(keys[:2])}"
    ok("второй тест добавляет только себя, прошлые не подтягивает")


def check_session_set_is_not_persisted() -> None:
    """5. Набор «отвечено сейчас» нигде не сохраняется."""
    for rel in PAGES:
        src = inline_script(rel)
        assert "const answeredNow = new Set();" in src, \
            f"{rel}: нет набора ключей этого захода"
        assert "function sessionKeys()" in src, f"{rel}: нет sessionKeys"
        assert "answeredNow.add(key)" in src, \
            f"{rel}: ключ не помечается отвеченным при записи"
        # Ни в память телефона, ни в облако он уходить не должен: иначе после
        # перезапуска прошлые тесты снова станут «свежими».
        assert "JSON.stringify(answeredNow" not in src, \
            f"{rel}: набор захода уезжает в хранилище"
        for m in re.finditer(r"setItem\(([^;]*)\)", src):
            assert "answeredNow" not in m.group(1), \
                f"{rel}: набор захода попал в setItem"
    ok("набор захода живёт только в памяти страницы")

    for rel in PAGES:
        src = inline_script(rel)
        # Сборка записи идёт только по ключам захода.
        for fn in ("buildScores", "buildAnswers"):
            i = src.index("function " + fn + "()")
            body = src[i:src.index("\n}", i)]
            assert "sessionKeys()" in body, \
                f"{rel}: {fn} собирает запись не по ключам захода"
            assert "Object.keys(results)" not in body, \
                f"{rel}: {fn} снова ходит по всему results"
    ok("сборка записи во всех восьми страницах идёт по ключам захода")


def check_local_history_still_shown() -> None:
    """6. Прошлые результаты никуда не делись: строка «с прошлым разом» жива."""
    for rel in PAGES:
        src = inline_script(rel)
        assert "prev:" in src, f"{rel}: пропал прошлый результат для сравнения"
        assert "saveResultsLocal" in src, f"{rel}: пропало локальное хранение"
    ok("прошлое по-прежнему хранится локально и показывается человеку")

    # На экране результата сравнение с прошлым разом должно остаться живым.
    rel = "state-quarter/app3.html"
    got = app_run(rel, """
  results[TESTS[0].key] = { nums: [11], band: 'старое', c: 'ok',
                            data: { total: 11 }, answers: { 0: 1 },
                            completed_at: '%s' };
  await __pass(TESTS[0].key, null);
  OUT.screen = app.innerHTML;
""" % OLD)
    assert "undefined" not in got["screen"] and "NaN" not in got["screen"], \
        "экран результата собрался с дырами"
    ok("экран результата после повторного прохождения собирается целиком")


if __name__ == "__main__":
    raise SystemExit(run([
        check_one_test_one_record, check_memory_and_cloud_never_travel,
        check_empty_session_no_record, check_alert_flag_is_from_this_session,
        check_second_answer_adds_only_itself,
        check_session_set_is_not_persisted, check_local_history_still_shown,
    ]))
