# -*- coding: utf-8 -*-
"""Проверки двух дополнений первого экрана «Что со мной?» (спека 008).

Задача. Экран уже открывается наблюдением и одной просьбой (007). Дополняется
двумя вещами из спеки 008:

  · **История 2, слепая зона.** Одна строка про то, чего бот про человека пока
    не видит. Приезжает готовой параметром `bs=` и показывается как есть — под
    наблюдением и выше просьбы. Ни процентов, ни счётчиков «пройдено N из M»,
    ни слова «нужно»: заполнение как долг превращает замеры в обязанность.
    Параметра нет — строки нет вовсе, пустого места не остаётся (FR-007…FR-009).

  · **История 3, вход в дорожку.** Отдельная ссылка ниже одной просьбы и рядом
    с «Посмотреть всё». Ведёт на экран дорожки в ТОМ ЖЕ мини-аппе — свой адрес с
    меткой `track=1` (FR-010).

    ПЕРЕПИСАНО 08.08.2026, спека 011, История 3. Раньше здесь проверялось
    обратное: вход открывает бота старт-параметром `run_all`, а очередь держит
    бот. Решение Алексея после живой пробы отменило этот путь — «путает, когда
    тебя выкидывает в диалог», — и очередь переехала в мини-апп. Сама дорожка
    проверяется в `dorozhka.py`, здесь только её вход на первом экране.

Проверки исполняют страницу в node с заглушками и смотрят на СОБРАННЫЙ экран,
а не ищут слова в исходнике: ошибку шаблона разбором текста не поймать.

Запуск:  python3 checks/glubina_first_screen.py
"""

import re
import urllib.parse

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
from chto_so_mnoy import FRESH, OBS, has_word, link, obs, screens
from lib import catalog, catalog_render, inline_script, ok, run, visible

APP = "kak-ty/app.html"

# Живая строка слепой зоны из спеки. Кириллица едет в адресе urlencoded.
BLIND = "Про твою работу я не знаю ничего — а падение сил чаще всего оттуда."

BOT_NAME = "vslukh_shapovalov_bot"

# Формат из документации Телеграма: t.me/<bot>?start=<до 64 символов base64url>
START_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# Текст ссылки в дорожку. Обещаний «узнай себя полностью» быть не должно: за
# вечер получается широкий срез, а не линия, и говорит об этом бот на входе.
PROMISES = ["полностью", "всё про себя", "узнай себя", "точная картина",
            "полная картина", "всё о себе"]


def code_only(src: str) -> str:
    """Код без пояснений: слово в комментарии — не логика, искать надо в коде."""
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", " ", src)


def blind(text: str) -> str:
    return "bs=" + urllib.parse.quote(text, safe="")


def blind_text(part: str) -> str:
    """Текст слепой зоны ровно как он попал на экран, без обёртки."""
    m = re.search(r'<div class="blind">(.*?)</div>', part, re.S)
    return m.group(1) if m else ""


def runall_text(part: str) -> str:
    """Видимый текст ссылки в дорожку."""
    m = re.search(r'<div class="runall">(.*?)</div>', part, re.S)
    return visible(m.group(1)).strip() if m else ""


# --------------------------------------------------------------------------


def check_blind_pure() -> None:
    """1. Строка слепой зоны разбирается в чистой логике: предел 200, пусто = нет."""
    c = catalog("""
OUT.limit = BLIND_LIMIT;
OUT.blind = {
  empty: parseBlindSpot(""),
  blank: parseBlindSpot("   "),
  nul:   parseBlindSpot(null),
  undef: parseBlindSpot(undefined),
  plain: parseBlindSpot("  про работу я не знаю ничего  "),
  long:  (parseBlindSpot(new Array(400).join("а")) || "").length
};
""")
    assert c["limit"] == 200, f"предел строки слепой зоны {c['limit']}, а не 200"
    assert c["blind"]["long"] == 200, \
        f"строка не обрезана до 200 символов: {c['blind']['long']}"
    ok("предел 200 символов, длинная строка режется")

    b = c["blind"]
    for name in ("empty", "blank", "nul", "undef"):
        assert b[name] is None, \
            f"пустая строка слепой зоны ({name}) не превратилась в «строки нет»"
    ok("пусто, пробелы и отсутствие параметра = строки нет")

    assert b["plain"] == "про работу я не знаю ничего", \
        f"текст слепой зоны поехал: {b['plain']!r}"
    ok("текст не меняется, снимаются только пробелы по краям")


def check_blind_on_screen() -> None:
    """2. Строка стоит под наблюдением и выше просьбы."""
    first, _ = screens(link(FRESH, obs(OBS), blind(BLIND), "ask=state_week"))
    assert BLIND in visible(first), "строка слепой зоны не доехала до экрана"
    i_obs = first.index("Что видно по твоим ответам")
    i_blind = first.index('class="blind"')
    i_ask = first.index('class="card"')
    assert i_obs < i_blind, "слепая зона встала выше наблюдения"
    assert i_blind < i_ask, "слепая зона встала ниже просьбы"
    ok("наблюдение → слепая зона → просьба")

    # Наблюдения ещё нет, а слепая зона уже есть: она всё равно выше просьбы.
    nofacts, _ = screens(link(blind(BLIND), "ask=state_week"))
    assert BLIND in visible(nofacts), "без наблюдения строка слепой зоны пропала"
    assert nofacts.index('class="blind"') < nofacts.index('class="card"'), \
        "без наблюдения слепая зона уехала под просьбу"
    ok("без наблюдения строка остаётся выше просьбы")


def check_blind_absent_no_gap() -> None:
    """3. Параметра нет — строки нет вообще, пустое место не остаётся."""
    for search in (link(FRESH, obs(OBS), "ask=state_week"),
                   link(FRESH, obs(OBS), "bs=", "ask=state_week"),
                   link(FRESH, obs(OBS), "bs=%20%20", "ask=state_week")):
        first, _ = screens(search)
        assert 'class="blind"' not in first, \
            f"без строки слепой зоны на экране осталась пустая рамка: {search}"
    ok("нет bs, пустой и пробельный bs: рамки нет")

    whole = catalog_render(link(FRESH, obs(OBS), "ask=state_week"))
    assert "blind" not in visible(whole), \
        "служебное слово вылезло в текст, который читает человек"
    ok("на экране без слепой зоны про неё нет ни слова")

    # Зазор между наблюдением и строкой меньше, чем до просьбы: они про одно.
    tight, _ = screens(link(FRESH, obs(OBS), blind(BLIND), "ask=state_week"))
    assert "obs-tight" in tight, \
        "наблюдение и слепая зона стоят на прежнем большом зазоре — читаются как разное"
    plain, _ = screens(link(FRESH, obs(OBS), "ask=state_week"))
    assert "obs-tight" not in plain, \
        "зазор под наблюдением поджат и без строки слепой зоны — под ним пустота"
    ok("зазор поджимается только когда строка есть")


def check_blind_verbatim() -> None:
    """4. Строка показана как есть: без своей формулировки и без разметки."""
    first, _ = screens(link(FRESH, obs(OBS), blind(BLIND), "ask=state_week"))
    assert blind_text(first) == BLIND, \
        f"текст слепой зоны изменён: {blind_text(first)!r} вместо {BLIND!r}"
    ok("текст на экране совпадает с текстом бота посимвольно")

    long_text = "Работа " + "а" * 400
    cut, _ = screens(link(blind(long_text), "ask=state_week"))
    assert len(blind_text(cut)) == 200, \
        f"на экране {len(blind_text(cut))} символов вместо 200"
    ok("строка длиннее 200 символов обрезается")

    evil, _ = screens(link(blind("<b>жирная</b> зона"), "ask=state_week"))
    assert "&lt;b&gt;" in blind_text(evil), "разметка из строки не обезврежена"
    assert "<b>" not in blind_text(evil), "тег из строки попал на страницу живым"
    ok("разметка внутри строки не исполняется")


def check_blind_not_a_debt() -> None:
    """5. Ни процентов, ни счётчиков, ни слова «нужно»: это интерес, не долг."""
    first, _ = screens(link(FRESH, obs(OBS), blind(BLIND), "ask=state_week"))
    text = blind_text(first)
    assert "%" not in text, "в строке слепой зоны появился процент заполнения"
    assert not re.search(r"\d+\s*(из|/)\s*\d+", text), \
        "в строке слепой зоны появился счётчик «пройдено N из M»"
    assert not has_word(text.lower(), "нужно"), \
        "в строке слепой зоны появилось слово «нужно» — замер стал долгом"
    ok("в строке ни процента, ни счётчика, ни «нужно»")

    # Ничего похожего на полосу заполнения не появилось и рядом: спека прямо
    # меняет прогресс-бар на названную слепую зону.
    assert "%" not in visible(first), "на первом экране появился процент"
    assert not re.search(r"\d+\s*(из|/)\s*\d+", visible(first)), \
        "на первом экране появился счётчик пройденного"
    src = code_only(inline_script(APP)).lower()
    for gone in ("progress", "percent", "прогресс", "пройдено", "из 13"):
        assert gone not in src, f"в коде появилась логика заполнения: {gone}"
    ok("полосы заполнения и счётчиков нет ни на экране, ни в коде")


def check_run_all_link_pure() -> None:
    """6. Вход в дорожку собирается на СВОЁМ адресе, а не на адресе бота."""
    c = catalog("""
OUT.link = trackHref("/kak-ty/app.html", "?u=tg_777&f=state_day:2026-08-06", "1");
OUT.done = trackHref("/kak-ty/app.html", "?u=tg_777", "done");
OUT.again = trackHref("/kak-ty/app.html", "?u=tg_777&track=done", "1");
OUT.plain = trackHref("/kak-ty/app.html", "?u=tg_777&track=1", "");
OUT.card = botLink("vslukh_shapovalov_bot", "state_move");
""")
    assert c["link"] == "/kak-ty/app.html?u=tg_777&f=state_day:2026-08-06&track=1", \
        f"вход в дорожку: {c['link']}"
    assert "t.me" not in c["link"], "вход в дорожку всё ещё ведёт в переписку"
    assert c["done"].endswith("track=done"), f"адрес итога дорожки: {c['done']}"
    ok("вход ведёт на свой адрес с меткой дорожки")

    assert c["again"] == "/kak-ty/app.html?u=tg_777&track=1", \
        f"метка дорожки удвоилась: {c['again']}"
    assert c["plain"] == "/kak-ty/app.html?u=tg_777", \
        f"без метки адрес не возвращается к списку: {c['plain']}"
    ok("метка не дублируется и снимается")

    assert c["card"] == f"https://t.me/{BOT_NAME}?start=card_state_move", \
        f"ссылки карточек-разговоров сломались: {c['card']}"
    ok("карточки-разговоры открываются по-прежнему")


def check_run_all_on_screen() -> None:
    """7. Вход в дорожку стоит ниже просьбы и рядом с «Посмотреть всё»."""
    search = link(FRESH, obs(OBS), blind(BLIND), "ask=state_week")
    whole = catalog_render(search)
    want = "track=1"
    assert 'class="runall"' in whole, "на экране нет входа в дорожку"
    assert want in whole, "вход в дорожку не ведёт на её экран"
    assert "start=run_all" not in whole, "вход в дорожку всё ещё уходит боту"
    ok("вход в дорожку на экране, ведёт на её экран в мини-аппе")

    i_ask = whole.index('class="card"')
    i_run = whole.index('class="runall"')
    i_all = whole.index('id="all"')
    assert i_ask < i_run, "вход в дорожку встал выше просьбы"
    assert i_run < i_all, "вход в дорожку уехал внутрь полного списка"
    after = whole[whole.index("</div>", i_run) + len("</div>"):]
    assert after.lstrip().startswith("<details"), \
        f"между дорожкой и «Посмотреть всё» что-то вклинилось: {after[:80]!r}"
    ok("ниже просьбы, вплотную к «Посмотреть всё»")

    # Всё, что прислал бот, доезжает до экрана дорожки: иначе она не узнает ни
    # человека, ни даты замеров, и порядок собрать будет нечем.
    m = re.search(r'<div class="runall"><a href="([^"]+)"', whole)
    assert m, "у входа в дорожку нет адреса"
    href = m.group(1)
    for part in ("u=tg_777", "f=state_day", "track=1"):
        assert part in href, f"вход в дорожку потерял «{part}»: {href}"
    ok("вход доносит человека и даты замеров до экрана дорожки")

    # Дорожка — вход, а не просьба: она есть и когда просить нечего.
    quiet = catalog_render(link())
    assert 'class="runall"' in quiet and want in quiet, \
        "без данных вход в дорожку пропал"
    ok("вход в дорожку есть на любом состоянии экрана")


def check_run_all_opens_bot() -> None:
    """8. Дорожка идёт внутри мини-аппа, а не в переписке.

    Сначала тут стояло обратное: дорожку начинает `sendData`, очередь держит бот.
    Живая проба 07.08.2026 это отменила — человека выбрасывало в чат на каждом
    переходе. Сама дорожка проверяется в `dorozhka.py`, здесь только её вход.
    """
    whole = catalog_render(link(FRESH, obs(OBS), "ask=state_week"))
    m = re.search(r'<div class="runall">(.*?)</div>', whole, re.S)
    assert m, "блока с входом в дорожку на экране нет"
    assert 'data-track="start"' in m.group(1), \
        "у входа в дорожку нет метки, по которой он открывается в мини-аппе"
    assert "data-send=" not in m.group(1), \
        "у входа в дорожку остался payload для бота — он снова уйдёт в чат"
    assert "t.me" not in m.group(1), \
        "у входа в дорожку осталась ссылка на переписку"
    ok("вход в дорожку помечен для мини-аппа, путей в чат у него нет")

    src = inline_script(APP)
    assert "runAllPayload" not in src and "RUN_ALL_START" not in src, \
        "в коде остался прежний путь дорожки через бота"
    assert ".sendData(" in src, \
        "sendData вырезан целиком — карточки-разговоры перестанут открываться"
    assert "openTelegramLink" in src, "запасной путь карточек-разговоров вырезан"
    ok("у дорожки путей в бота нет, у карточек-разговоров оба на месте")


def check_main_ask_still_one() -> None:
    """9. Главная просьба осталась одна: дорожка её не подменяет."""
    first, _ = screens(link(FRESH, obs(OBS), blind(BLIND), "ask=state_week"))
    assert len(re.findall(r'class="card"', first)) == 1, \
        "на первом экране больше одной карточки"
    assert first.count("Чтобы сказать точнее, не хватает одного") == 1, \
        "подпись просьбы пропала или удвоилась"
    assert len(re.findall(r'class="runall"', first)) == 1, \
        "вход в дорожку показывается дважды"
    ok("одна просьба, один вход в дорожку")

    # Дорожка не карточка: иначе она встанет в счёт просьб и в полный список.
    m = re.search(r'<div class="runall">(.*?)</div>', first, re.S)
    assert 'class="card' not in m.group(1), \
        "вход в дорожку оформлен карточкой замера — он читается как вторая просьба"
    _, rest = screens(link(FRESH))
    assert 'class="runall"' not in rest, \
        "вход в дорожку продублирован внутри полного списка"
    ok("дорожка не карточка и в списке не дублируется")


def check_run_all_text_honest() -> None:
    """10. Текст ссылки честно говорит, кому она, одной строкой и без обещаний."""
    first, _ = screens(link(FRESH, obs(OBS), "ask=state_week"))
    text = runall_text(first)
    assert text, "у входа в дорожку нет видимого текста"
    assert "<br" not in first[first.index('class="runall"'):][:400], \
        "текст входа в дорожку разбит на две строки"
    assert len(text) <= 90, f"строка входа длиннее одной строки: {len(text)} символов"
    ok(f"одна строка, {len(text)} символов")

    low = text.lower()
    assert "разобра" in low, \
        "текст не говорит, что дорожка для того, кто пришёл разбираться"
    assert "напомина" in low, \
        "текст не отделяет разбор от ответа на напоминание"
    ok("сказано, кому это: разбираться, а не отвечать на напоминание")

    for bad in PROMISES:
        assert bad not in low, f"в тексте обещание «{bad}»"
    for bad in ("нужно", "должен", "надо", "пора"):
        assert not has_word(low, bad), f"вход в дорожку звучит как долг: «{bad}»"
    ok("ни обещаний, ни долга")


if __name__ == "__main__":
    raise SystemExit(run([
        check_blind_pure, check_blind_on_screen, check_blind_absent_no_gap,
        check_blind_verbatim, check_blind_not_a_debt,
        check_run_all_link_pure, check_run_all_on_screen,
        check_run_all_opens_bot, check_main_ask_still_one,
        check_run_all_text_honest,
    ]))
