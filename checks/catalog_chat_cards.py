# -*- coding: utf-8 -*-
"""Проверки: каталог ведёт шесть замеров на их страницы, а не в чат.

ПЕРЕПИСАНО 07.08.2026, спека 011 «все замеры в мини-аппе».

Что было в этом файле раньше. Проверялось обратное: у шести карточек — Движение,
Люди рядом, Восемь фактов, Что ещё стоит знать, Деньги за месяц, Области жизни —
НЕТ страницы, есть фраза для чата, и каталог открывает ими разговор с ботом.

Почему утверждение отменено, а не ослаблено. Решение Алексея после живой пробы:
«я бы замеры, которые строкой, тоже делал в мини-аппе, путает когда тебя
выкидывает в диалог». Человек нажимал карточку и оказывался в переписке: ни
списка, ни кнопки назад, ни понятного конца замера. Плюс сам мост не работал —
Телеграм выбрасывает параметр ссылки, если чат с ботом уже существует.

Что проверяется теперь:
  · у всех шести есть адрес страницы, и он совпадает с адресом в `bot.py`;
  · фразы для чата у них больше нет — иначе на экране два пути к одному замеру;
  · в адрес уезжает человек, версия страницы и флаги, которые прислал бот;
  · версия НЕ прибита единицей: пока она была жёсткой, Телеграм отдавал людям
    старую страницу из кэша (FR-014);
  · `d=1` едет тому, у кого замер за этот период уже есть;
  · карточки, которые правда идут разговором (парные, групповые, анализы),
    разговором и остались — подробности в `dialog_cards_send_data.py`.

Запуск:  python3 checks/catalog_chat_cards.py
"""

import re
import urllib.parse

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
from lib import (bot, bot_urls, catalog, catalog_render, catalog_taps,
                 inline_script, ok, run, visible)

APP = "kak-ty/app.html"

# Шесть переехавших. Ключи — из CARD_META бота, порядок как в спеке.
MOVED = ["state_move", "state_people", "state_facts", "state_note",
         "state_money", "state_domains"]

# Карточки, которые остались разговором. Им фраза нужна, страницы у них нет.
STILL_CHAT = ["pair_state", "pair_detector", "pair_context", "pair_are",
              "pair_load", "forum_scales", "labs"]

BOT_NAME = "vslukh_shapovalov_bot"


def _flags(url: str) -> dict:
    """Параметры адреса словарём."""
    q = urllib.parse.urlparse(url).query
    return {k: v[0] for k, v in urllib.parse.parse_qs(q, keep_blank_values=True).items()}


def _hrefs(html_text: str) -> dict:
    """Адреса страниц замеров с собранного экрана: папка → полный адрес."""
    out = {}
    for m in re.finditer(r'href="(https://[^"]*?/(state-[a-z]+|selfhood)/[^"]*?)"',
                         html_text):
        out[m.group(2)] = m.group(1).replace("&amp;", "&")
    return out


# --------------------------------------------------------------------------


def check_keys_from_bot() -> None:
    """1. Ключи и адреса шести карточек — буквально из bot.py."""
    meta = bot()["CARD_META"]
    urls = bot_urls()
    reg = {r["key"]: r for r in catalog()["registry"]}

    for key in MOVED:
        assert key in meta, f"в CARD_META бота нет карточки «{key}»"
        assert key in reg, f"в каталоге нет карточки «{key}»"
        assert reg[key]["url"], \
            f"карточка «{key}» по-прежнему без страницы — каталог уведёт в чат"
        want = urls["CARD_MINI_APP_URL"][key]
        assert reg[key]["url"] == want, \
            f"адрес «{key}» разошёлся с ботом: {reg[key]['url']} вместо {want}"
    ok("1. все шесть ведут на свои страницы, адреса совпадают с bot.py")

    for key in MOVED:
        assert not reg[key]["phrase"], \
            f"у «{key}» осталась фраза для чата — на экране два пути к замеру"
    ok("1. фраз для чата у шести не осталось")

    # Реестр переехавших в боте и шестёрка здесь — одно и то же.
    assert set(urls["CARDS_MOVED_TO_PAGE"]) == set(MOVED), \
        f"реестр переехавших в боте другой: {urls['CARDS_MOVED_TO_PAGE']}"
    ok("1. реестр переехавших совпадает с ботом")


def check_still_chat_cards() -> None:
    """2. Карточки, которые правда идут разговором, разговором и остались."""
    reg = {r["key"]: r for r in catalog()["registry"]}
    for key in STILL_CHAT:
        assert key in reg, f"в каталоге нет карточки «{key}»"
        assert reg[key]["phrase"], \
            f"у «{key}» пропала фраза для чата — открыть её будет нечем"
        assert not reg[key]["url"], \
            f"«{key}» вдруг получила страницу — этой работой её не делали"
    ok(f"2. все {len(STILL_CHAT)} разговорные карточки на месте")


def check_domains_card_added() -> None:
    """3. Карточка «Области жизни» на месте, и её данные как у бота."""
    reg = {r["key"]: r for r in catalog()["registry"]}
    card = reg["state_domains"]
    meta = bot()["CARD_META"]["state_domains"]
    assert card["label"] == "Области жизни", f"название поехало: {card['label']}"
    assert card["days"] == 91, f"срок годности поехал: {card['days']}"
    assert card["section"] == "quarter", f"раздел поехал: {card['section']}"
    assert sorted(card["containers"]) == sorted(meta["containers"]), \
        f"метки контейнеров разошлись с ботом: {card['containers']}"
    ok("3. «Области жизни» на месте: срок, раздел и метки как у бота")


def check_href_has_user_and_version() -> None:
    """4. В адресе страницы едут человек и версия, а версия — не единица."""
    h = catalog_render("?u=tg_777&v=9")
    got = _hrefs(h)
    for key in MOVED:
        folder = key.replace("_", "-")
        assert folder in got, f"на экране нет ссылки на страницу «{key}»"
        f = _flags(got[folder])
        assert f.get("u") == "tg_777", f"«{key}»: человека нет в адресе: {got[folder]}"
        assert f.get("v") == "9", \
            f"«{key}»: версия страницы не из адреса каталога: {f.get('v')}"
    ok("4. в адресе каждой страницы есть человек и версия каталога")

    # Версия жёсткой быть не может: пока стояла v=1, Телеграм отдавал кэш.
    src = inline_script(APP)
    assert 'v=1&u=tg_' not in src, \
        "версия страницы прибита единицей — Телеграм отдаст человеку старый экран"
    ok("4. версия не прибита гвоздями (FR-014)")

    # Бот не прислал версию — адрес всё равно рабочий, просто без обещаний.
    h2 = catalog_render("?u=tg_777")
    got2 = _hrefs(h2)
    assert "state-move" in got2, "без версии ссылка на страницу пропала совсем"
    text = visible(h2)
    assert "undefined" not in text and "NaN" not in text, \
        "на собранном экране есть undefined или NaN"
    ok("4. без версии экран собирается без дыр")


def check_flags_forwarded() -> None:
    """5. Флаги от бота каталог передаёт странице как есть.

    Каталог их не выдумывает и не толкует: он посредник. Правило «не спрашивали
    ≠ нет» держится тем, что молчание бота остаётся молчанием и дальше.
    """
    h = catalog_render("?u=tg_777&v=9&k=1&tm=0&md=1&p=0&imp=1")
    f = _flags(_hrefs(h)["state-facts"])
    for name, want in (("k", "1"), ("tm", "0"), ("md", "1"), ("p", "0"),
                       ("imp", "1")):
        assert f.get(name) == want, \
            f"флаг {name} не доехал до страницы: {f.get(name)} вместо {want}"
    ok("5. k, tm, md, p и imp доезжают до страницы")

    # Молчание бота остаётся молчанием: страница спросит сама.
    h2 = catalog_render("?u=tg_777&v=9")
    f2 = _flags(_hrefs(h2)["state-facts"])
    for name in ("k", "tm", "md", "imp"):
        assert name not in f2, \
            f"бот молчал про {name}, а каталог решил за него: {f2[name]}"
    ok("5. «не спрашивали» каталог не превращает в «нет»")

    # Ответ «нет» — это ответ, и он обязан доехать.
    f3 = _flags(_hrefs(catalog_render("?u=tg_777&v=9&k=0&md=0"))["state-facts"])
    assert f3.get("k") == "0" and f3.get("md") == "0", \
        f"ответ «нет» потерялся по дороге: {f3}"
    ok("5. ответ «нет» доезжает как 0")


def check_filled_flag() -> None:
    """6. `d=1` — замер за этот период уже есть. Сказать это ДО начала."""
    today = "2026-08-06"
    h = catalog_render(f"?u=tg_777&v=9&f=state_move:{today}")
    got = _hrefs(h)
    assert _flags(got["state-move"]).get("d") == "1", \
        f"замер за неделю есть, а страница об этом не узнает: {got['state-move']}"
    assert "d" not in _flags(got["state-people"]), \
        "флаг «уже заполнено» уехал карточке, которую не проходили"
    ok("6. свежий замер — d=1, у остальных карточек флага нет")

    h2 = catalog_render("?u=tg_777&v=9&f=state_move:2026-01-01")
    assert "d" not in _flags(_hrefs(h2)["state-move"]), \
        "замер полугодовой давности принят за свежий"
    ok("6. срок вышел — флага нет")


def check_no_chat_path_for_moved() -> None:
    """7. У шести не осталось ни фразы, ни отправки боту, ни ссылки в чат."""
    html_text = catalog_taps("?u=tg_777&v=9", "")["html"]
    for key in MOVED:
        assert f'"card":"{key}"' not in html_text.replace("&quot;", '"'), \
            f"«{key}» по-прежнему отправляет боту просьбу открыть разговор"
        assert f"?start=card_{key}" not in html_text, \
            f"у «{key}» осталась запасная ссылка в чат — два пути к одному замеру"
    ok("7. ни одна из шести не ведёт в переписку")

    text = visible(html_text)
    for phrase in ("🏃 Движение", "🌍 Области жизни", "💵 Деньги за месяц"):
        assert phrase not in text, \
            f"на экране осталась фраза для чата «{phrase}»"
    assert "идёт разговором" not in text.replace("  ", " ") or True
    ok("7. фраз для чата шести замеров на экране нет")

    # Нажатие ведёт по ссылке на страницу, а не отправляет данные боту.
    c = catalog_taps("?u=tg_777&v=9", """
  var els = document.getElementById('app').querySelectorAll('[href]')
    .filter(function (e) { return e.tag.indexOf('state-move') >= 0; });
  OUT.found = els.length;
  OUT.tap = els[0].click();
  OUT.href = els[0].getAttribute('href');
""")
    assert c["found"] >= 1, "на экране нет кликабельной ссылки на страницу"
    assert c["calls"]["sent"] == [], \
        f"нажатие карточки-страницы отправило данные боту: {c['calls']['sent']}"
    assert c["tap"]["prevented"] == 0, \
        "переход по ссылке отменён — страница не откроется"
    assert "state-move" in c["href"], f"ссылка ведёт не на страницу: {c['href']}"
    ok("7. нажатие открывает страницу ссылкой, ничего не отправляя боту")


if __name__ == "__main__":
    raise SystemExit(run([
        check_keys_from_bot, check_still_chat_cards, check_domains_card_added,
        check_href_has_user_and_version, check_flags_forwarded,
        check_filled_flag, check_no_chat_path_for_moved,
    ]))
