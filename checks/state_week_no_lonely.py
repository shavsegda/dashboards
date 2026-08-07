# -*- coding: utf-8 -*-
"""Проверки: одиночество спрашивают один раз.

Задача. В недельном мини-аппе стояли три пункта про одиночество (UCLA-3). То же
самое теперь спрашивает карточка бота «🫂 Люди рядом». Человек отвечал дважды —
и обе записи ложились в базу как разные точки одной линии.

Что проверяем:
  · в недельном мини-аппе про одиночество больше не спрашивают;
  · остальные пять тестов на месте, их ключи и число пунктов не поехали;
  · старый ответ, оставшийся в памяти телефона, в базу больше не уходит;
  · линия одиночества не рвётся: бот читает её из двух блоков.

Запуск:  python3 checks/state_week_no_lonely.py
"""

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
from lib import (bot, block_paths, dig, form_app, form_render, html,
                 inline_script, ok, run)

APP = "state-week/app4.html"

# Что должно остаться в недельном мини-аппе. Ключ → сколько пунктов.
# Числа прибиты руками: посчитать их из самого файла значит согласиться с любым
# его состоянием, включая «пунктов не осталось».
EXPECTED = {
    "panas": 10,      # I-PANAS-SF, десять прилагательных
    "vitality": 7,    # субъективная витальность
    "gate": 4,        # PHQ-2 плюс GAD-2
    "flow": 1,        # свой пункт про поток
    "couple": 3,      # KMS-3, три вопроса про связь
}


def check_lonely_gone() -> None:
    """1. Про одиночество в недельном мини-аппе больше не спрашивают."""
    app = form_app(APP)
    assert "lonely" not in app["keys"], \
        f"тест про одиночество всё ещё в списке недельного: {app['keys']}"
    assert "lonely" not in app["scorers"], \
        "подсчёт одиночества остался в недельном — значит остался и путь к нему"
    ok("одиночества нет ни в списке тестов, ни в подсчёте")

    src = inline_script(APP)
    for word in ("UCLA", "SCALE_UCLA", "scoreLonely"):
        assert word not in src, f"в скрипте остался кусок одиночества: «{word}»"
    ok("в скрипте не осталось ни шкалы, ни функции подсчёта одиночества")

    body = html(APP)
    for word in ("не хватает дружеского общения", "чувствуешь себя лишним",
                 "изолированным от других"):
        assert word not in body, f"пункт про одиночество остался в тексте: «{word}»"
    ok("три пункта про одиночество убраны из текста страницы")

    assert "UCLA-3" not in app["instrument"], \
        f"в подписи инструмента всё ещё UCLA-3: {app['instrument']}"
    ok(f"подпись инструмента честная: {app['instrument']}")


def check_rest_untouched() -> None:
    """2. Остальные пять тестов и их ключи не поехали."""
    app = form_app(APP)
    assert app["keys"] == list(EXPECTED), \
        f"состав тестов недельного изменился: {app['keys']}"
    ok("остались ровно пять тестов, порядок прежний")

    for key, count in EXPECTED.items():
        got = app["sizes"][app["keys"].index(key)]
        assert got == count, f"у теста «{key}» стало {got} пунктов вместо {count}"
    ok("число пунктов у каждого теста прежнее")

    assert app["block"] == "state_week", f"блок базы поехал: {app['block']}"
    assert app["storeKeys"] == ["state_week_tg_777", "state_week_result_tg_777",
                                "res_state_week"], \
        f"ключи хранения поехали: {app['storeKeys']}"
    ok("блок базы и ключи хранения прежние")


# Поля, которые каждый оставшийся тест кладёт в запись. Это и есть «ключи не
# поехали»: сравниваем с тем, что было до правки, а не с тем, что удобно.
EXPECTED_FIELDS = {
    "panas": {"pa", "na"},
    "vitality": {"mean"},
    "gate": {"phq", "gad", "alert"},
    "flow": {"value"},
    "couple": {"sum"},
}

# Расхождение, которое было до этой работы и остаётся: бот читает из недели
# «couple.total», а мини-апп пишет «couple.sum». Линия «Близкая связь» в панели
# из-за этого пустая. Здесь оно ЗАПИСАНО, чтобы проверка падала, если список
# расхождений изменится в любую сторону — почините или добавите новое.
KNOWN_MISMATCH = {"couple.total"}


def check_fields_match_bot() -> None:
    """3. Ключи полей — буквально как в bot.py."""
    b = bot()
    want = block_paths(b, "state_week")
    fill = "\n".join(f"fill('{k}', 2);" for k in EXPECTED)
    app = form_app(APP, fill + "\nOUT.scores = api.buildScores();")
    scores = app["scores"]

    for key, fields in EXPECTED_FIELDS.items():
        got = set(scores.get(key) or {}) - {"band", "nums"}
        assert got == fields, f"поля теста «{key}» поехали: {sorted(got)}"
    ok("поля всех пяти тестов прежние")

    missing = {p for p in want if dig(scores, p) is None}
    assert missing == KNOWN_MISMATCH, \
        ("список расхождений с bot.py изменился: "
         f"{sorted(missing)} вместо {sorted(KNOWN_MISMATCH)}")
    ok(f"из {len(want)} полей бота мини-апп пишет все, кроме известного "
       f"{sorted(KNOWN_MISMATCH)}")

    assert dig(scores, "lonely.total") is None and "lonely" not in scores, \
        f"одиночество всё ещё уходит в запись недели: {sorted(scores)}"
    ok("в записи недели одиночества нет")

    # Метка источника нужна панели: она отличает мини-апп от разговора.
    assert scores.get("source") == "manual", "пропала метка источника записи"
    ok("метка источника на месте")


def check_stale_answer_not_resent() -> None:
    """4. Старый ответ из памяти телефона в базу не уходит.

    Самое дорогое место. У людей, кто проходил неделю раньше, ответ про
    одиночество лежит в памяти телефона. Сборка записи шла по всему, что
    накопилось, — и старая цифра уезжала бы в базу каждую неделю как свежая.
    Догадки не сохраняются как данные: конституция.
    """
    extra = (
        "fill('panas', 2);\n"
        # Так выглядит запись, оставшаяся от прежней версии мини-аппа.
        "api.results['lonely'] = { nums: [], band: 'старое', c: 'ok',\n"
        "  data: { sum: 9 }, answers: { 0: 3, 1: 3, 2: 3 },\n"
        "  completed_at: '2026-07-01T10:00:00.000Z' };\n"
        "OUT.scores = api.buildScores();\n"
        "OUT.answers = api.buildAnswers();\n"
    )
    app = form_app(APP, extra)
    assert "lonely" not in app["scores"], \
        "старый ответ про одиночество снова уехал в базу"
    assert "lonely" not in app["answers"], \
        "старые ответы про одиночество снова уехали в базу"
    assert "panas" in app["scores"], "вместе с чужим ключом выкинуло свой"
    ok("старый ключ отброшен, свои остались")


def check_history_kept() -> None:
    """5. История одиночества не рвётся: бот читает её из двух блоков.

    Оговорка, которую надо знать: прежний недельный мини-апп писал одиночество
    полем «lonely.sum», а бот читает «lonely.total». Значит прошлые точки в
    панели и так не читались — переносить нечего. Указатель прошлого блока
    всё равно должен стоять: он про правило, а не про эти данные.
    """
    b = bot()
    past = b["INSTRUMENT_PAST_BLOCKS"].get("lonely")
    assert past and "state_week" in past, \
        f"бот не помнит, что одиночество жило в недельном: {past}"
    assert "lonely.total" in block_paths(b, "state_people"), \
        "бот не читает одиночество из новой карточки «Люди рядом»"
    ok("прошлые точки читаются: state_week плюс state_people")


def check_page_renders() -> None:
    """6. Страница собирается: пять тестов видно, одиночества нет."""
    h = form_render(APP)
    assert "undefined" not in h and "NaN" not in h, \
        "в собранной странице есть undefined или NaN"
    for t in ("Аффект", "Витальность", "Датчик", "Поток", "Близкая связь"):
        assert f">{t}<" in h, f"на собранной странице нет теста «{t}»"
    assert "Одиночество" not in h, "одиночество всё ещё на собранной странице"
    ok("страница собирается: пять тестов, одиночества нет")


if __name__ == "__main__":
    raise SystemExit(run([
        check_lonely_gone, check_rest_untouched, check_fields_match_bot,
        check_stale_answer_not_resent, check_history_kept, check_page_renders,
    ]))
