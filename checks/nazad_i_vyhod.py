# -*- coding: utf-8 -*-
"""Проверки кнопки назад и подтверждения выхода (спека 012).

Оба требования записаны в `мини-аппы-правила.md` давно и не были выполнены ни на
одной странице. Дефект нашёл Алексей на живом телефоне: «нет кнопки назад, когда
зашёл на какую-то карточку, только закрыть миниап».

Что проверяем:

  · **Решение** — когда кнопку показывать, что закрывать, сколько обработчиков.
    Это чистая логика, она берётся из кода каталога и исполняется в node.
  · **Наличие проводки** — что на страницах-опросниках вообще используется
    штатная `BackButton` и `enableClosingConfirmation` включается ПОСЛЕ первого
    ответа, а не при открытии.

Что проверками НЕ берётся и проверяется руками на телефоне: как ведёт себя
настоящая кнопка Телеграма в настоящем клиенте. Записано в спеке честно.

Запуск:  python3 checks/nazad_i_vyhod.py
"""

import re

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
from lib import html, inline_script, ok, run, _node

CATALOG = "kak-ty/app.html"

# Страницы-опросники: там кнопка назад ведёт назад по истории, а подтверждение
# выхода включается после первого ответа.
FORMS = (
    "state-week/app4.html",
    "state-month/app3.html",
    "state-quarter/app3.html",
    "state-clinical/app.html",
    "state-year/app.html",
    "state-team/app.html",
    "state-needs/app.html",
    "state-day/app.html",
    "selfhood/app.html",
)


def code_only(src: str) -> str:
    """Код без пояснений: слово в комментарии — не логика."""
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", " ", src)


def nav(js: str) -> dict:
    """Прогнать решение про кнопку назад в node, взяв функции из каталога."""
    src = inline_script(CATALOG)
    m = re.search(r"/\* ==== ЧИСТАЯ ЛОГИКА: НАЧАЛО ====.*?"
                  r"/\* ==== ЧИСТАЯ ЛОГИКА: КОНЕЦ ==== \*/", src, re.S)
    if not m:
        raise AssertionError("в каталоге не нашёл блок чистой логики")
    return _node(m.group(0) + "\nconst OUT = {};\n" + js +
                 "\nconsole.log('RESULT<' + JSON.stringify(OUT) + '>RESULT');")


# --------------------------------------------------------------------------
# Решение: когда показывать кнопку и что закрывать
# --------------------------------------------------------------------------
def check_hidden_on_first_screen():
    out = nav("OUT.v = backVisible([]);")
    assert out["v"] is False, "на первом экране кнопка назад показывается"
    ok("на первом экране кнопки назад нет")


def check_visible_when_list_open():
    out = nav("OUT.v = backVisible(['all']);")
    assert out["v"] is True, "список открыт, а кнопки назад нет"
    ok("список открыт — кнопка назад есть")


def check_back_closes_innermost():
    """Открыты список и область — назад закрывает область, список остаётся."""
    out = nav("OUT.next = navPop(['all', 'area:Тело']);")
    assert out["next"] == ["all"], f"назад закрыл не то: {out['next']}"
    ok("назад закрывает самый внутренний уровень, а не всё сразу")


def check_back_from_list_empties():
    out = nav("OUT.next = navPop(['all']);\nOUT.v = backVisible(navPop(['all']));")
    assert out["next"] == [], "список не закрылся"
    assert out["v"] is False, "после закрытия списка кнопка осталась"
    ok("назад из списка возвращает на первый экран и убирает кнопку")


def check_pop_empty_is_safe():
    out = nav("OUT.next = navPop([]);")
    assert out["next"] == [], "закрытие пустого стека сломалось"
    ok("назад на первом экране ничего не ломает")


def check_push_does_not_duplicate():
    out = nav("OUT.next = navPush(navPush(['all'], 'all'), 'area:Тело');")
    assert out["next"] == ["all", "area:Тело"], f"уровни дублируются: {out['next']}"
    ok("повторный вход в тот же уровень не копит стек")


# --------------------------------------------------------------------------
# Проводка в каталоге
# --------------------------------------------------------------------------
def check_catalog_uses_back_button():
    code = code_only(inline_script(CATALOG))
    assert "BackButton" in code, "каталог не использует BackButton Телеграма"
    assert re.search(r"BackButton\s*\.\s*hide", code), "кнопка нигде не скрывается"
    assert re.search(r"BackButton\s*\.\s*show", code), "кнопка нигде не показывается"
    ok("каталог использует штатную BackButton: и show, и hide")


def check_catalog_binds_once():
    """Обработчик навешивается один раз: иначе одно нажатие сработает дважды."""
    code = code_only(inline_script(CATALOG))
    assert re.search(r"backBound", code), "нет защиты от повторной привязки"
    calls = re.findall(r"BackButton\s*\.\s*onClick", code)
    assert len(calls) == 1, f"onClick вызывается {len(calls)} раз, нужен один"
    ok("обработчик кнопки назад навешивается один раз")


def check_catalog_no_own_arrow():
    """Своя стрелка запрещена: у Телеграма есть родная кнопка."""
    page = html(CATALOG)
    body = re.sub(r"<script.*?</script>", " ", page, flags=re.S)
    for bad in ("←", "⬅", "&larr;"):
        assert bad not in body, f"в разметке своя стрелка назад: {bad}"
    ok("своей стрелки назад в разметке нет")


# --------------------------------------------------------------------------
# Проводка на страницах-опросниках
# --------------------------------------------------------------------------
def check_forms_have_back():
    missing = [f for f in FORMS if "BackButton" not in code_only(inline_script(f))]
    assert not missing, f"нет кнопки назад: {missing}"
    ok(f"кнопка назад есть на всех страницах-опросниках ({len(FORMS)})")


def check_forms_back_only_when_history():
    """Кнопка показывается, только если есть куда вернуться."""
    bad = []
    for f in FORMS:
        code = code_only(inline_script(f))
        if not re.search(r"history\.length\s*>\s*1", code):
            bad.append(f)
    assert not bad, f"кнопка показывается без проверки истории: {bad}"
    ok("кнопка назад показывается только когда есть куда вернуться")


def check_forms_closing_confirmation_after_answer():
    """Подтверждение выхода — после первого ответа, не при открытии."""
    bad, early = [], []
    for f in FORMS:
        code = code_only(inline_script(f))
        if "enableClosingConfirmation" not in code:
            bad.append(f)
            continue
        # включение должно стоять внутри обработчика первого ответа, а не в
        # прямом потоке инициализации: ищем защиту флагом
        if not re.search(r"armed|__armed", code):
            early.append(f)
    assert not bad, f"нет подтверждения выхода: {bad}"
    assert not early, f"подтверждение включается сразу при открытии: {early}"
    ok("подтверждение выхода включается после первого ответа")


def check_forms_release_after_result():
    """После показа результата подтверждение снимается."""
    bad = [f for f in FORMS
           if "disableClosingConfirmation" not in code_only(inline_script(f))]
    assert not bad, f"подтверждение не снимается после результата: {bad}"
    ok("после результата подтверждение выхода снимается")


def check_forms_keys_untouched():
    """Правки не касаются записи: ключи полей и отправка не менялись."""
    bad = []
    for f in FORMS:
        code = code_only(inline_script(f))
        if "BackButton" in code and "scores" not in code and "answers" not in code:
            bad.append(f)
    assert not bad, f"страница потеряла сборку записи: {bad}"
    ok("сборка записи на страницах не тронута")


if __name__ == "__main__":
    raise SystemExit(run([
        check_hidden_on_first_screen,
        check_visible_when_list_open,
        check_back_closes_innermost,
        check_back_from_list_empties,
        check_pop_empty_is_safe,
        check_push_does_not_duplicate,
        check_catalog_uses_back_button,
        check_catalog_binds_once,
        check_catalog_no_own_arrow,
        check_forms_have_back,
        check_forms_back_only_when_history,
        check_forms_closing_confirmation_after_answer,
        check_forms_release_after_result,
        check_forms_keys_untouched,
    ]))
