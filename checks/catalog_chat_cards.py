# -*- coding: utf-8 -*-
"""Проверки: диалоговые карточки каталога открывают бота.

Задача. Часть замеров идёт разговором с ботом, а не страницей: Движение, Люди
рядом, Восемь фактов, Что ещё стоит знать, Деньги за месяц, Области жизни. Из
каталога их было не открыть — человек видел карточку и фразу, которую надо
скопировать руками.

Что проверяем:
  · у всех шести карточек есть ссылка на бота со старт-параметром
    «card_<ключ карточки>», ключи — буквально из CARD_META в `bot.py`;
  · старт-параметр по формату Телеграма: до 64 символов base64url;
  · открывает переписку `openTelegramLink`, а `sendData` не зовётся нигде —
    он закрывает мини-апп и убивает запись;
  · имя бота приезжает параметром, а на случай его отсутствия есть запасное;
  · карточка «Области жизни» в каталоге вообще есть — раньше её не было.

Запуск:  python3 checks/catalog_chat_cards.py
"""

import re

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
from lib import bot, catalog, catalog_render, inline_script, ok, run, visible

APP = "kak-ty/app.html"

# Карточки, которые проходятся разговором. Ключи — из CARD_META бота, порядок
# как в задаче Алексея.
CHAT_CARDS = ["state_move", "state_people", "state_facts", "state_note",
              "state_money", "state_domains"]

BOT_NAME = "vslukh_shapovalov_bot"

# Формат из документации Телеграма: t.me/<bot>?start=<до 64 символов base64url>
START_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def check_keys_from_bot() -> None:
    """1. Ключи карточек — буквально из CARD_META в bot.py."""
    meta = bot()["CARD_META"]
    for key in CHAT_CARDS:
        assert key in meta, f"в CARD_META бота нет карточки «{key}»"
    ok("все шесть ключей есть в реестре бота")

    reg = {r["key"]: r for r in catalog()["registry"]}
    for key in CHAT_CARDS:
        assert key in reg, f"в каталоге нет карточки «{key}»"
        assert not reg[key]["url"], \
            f"карточка «{key}» проходится страницей, а не разговором"
        assert reg[key]["phrase"], f"у карточки «{key}» нет фразы для чата"
    ok("все шесть карточек в каталоге и все шесть — диалоговые")


def check_domains_card_added() -> None:
    """2. Карточка «Области жизни» в каталоге есть, и её данные как у бота."""
    reg = {r["key"]: r for r in catalog()["registry"]}
    card = reg["state_domains"]
    b = bot()
    meta = b["CARD_META"]["state_domains"]
    assert card["label"] == "Области жизни", f"название поехало: {card['label']}"
    assert card["days"] == 91, f"срок годности поехал: {card['days']}"
    assert card["section"] == "quarter", f"раздел поехал: {card['section']}"
    assert sorted(card["containers"]) == sorted(meta["containers"]), \
        f"метки контейнеров разошлись с ботом: {card['containers']}"
    ok("«Области жизни» на месте: срок, раздел и метки как у бота")


def check_link_built_right() -> None:
    """3. Ссылка собирается по документированному формату Телеграма."""
    got = catalog("""
  OUT.links = {};
  CHAT.forEach(function (k) { OUT.links[k] = botLink('vslukh_shapovalov_bot', k); });
  OUT.fallback = botLink('', 'state_move');
  OUT.dirty = botLink('злой ввод; rm -rf', 'state_move');
  OUT.params = CHAT.map(function (k) { return cardStartParam(k); });
""".replace("CHAT", repr(CHAT_CARDS).replace("'", '"')))

    for key in CHAT_CARDS:
        want = f"https://t.me/{BOT_NAME}?start=card_{key}"
        assert got["links"][key] == want, \
            f"ссылка карточки «{key}»: {got['links'][key]}"
    ok("ссылки ровно вида t.me/<бот>?start=card_<ключ>")

    for p in got["params"]:
        assert START_RE.match(p), f"старт-параметр не по формату: «{p}»"
    ok("старт-параметры по формату Телеграма: base64url, до 64 символов")

    assert got["fallback"] == f"https://t.me/{BOT_NAME}?start=card_state_move", \
        f"без имени бота ссылка неверная: {got['fallback']}"
    assert " " not in got["dirty"] and ";" not in got["dirty"], \
        f"мусор в имени бота попал в ссылку: {got['dirty']}"
    ok("имя бота чистится, запасное имя работает")


def check_links_on_screen() -> None:
    """4. Ссылка доезжает до карточки на собранном экране."""
    h = catalog_render("?u=tg_777")
    for key in CHAT_CARDS:
        want = f"https://t.me/{BOT_NAME}?start=card_{key}"
        assert want in h, f"на экране нет ссылки карточки «{key}»"
    ok("все шесть ссылок стоят на карточках")

    other = catalog_render("?u=tg_777&b=other_test_bot")
    assert "https://t.me/other_test_bot?start=card_state_move" in other, \
        "имя бота из адреса каталога не подхватывается"
    assert f"t.me/{BOT_NAME}?start=card_state_move" not in other, \
        "рядом с именем из адреса осталось запасное"
    ok("имя бота берётся из адреса, который даёт бот")

    text = visible(h)
    assert "undefined" not in text and "NaN" not in text, \
        "на собранном экране есть undefined или NaN"
    ok("экран собирается без дыр")


def check_open_path() -> None:
    """5. Основной путь — sendData, openTelegramLink остался запасным.

    Раньше здесь проверялось обратное: «sendData не зовётся». На живом телефоне
    выяснилось, что ссылка со старт-параметром не работает — payload теряется,
    если чат с ботом уже существует, и до бота `/start` не доходит. Замеры-
    разговоры были недостижимы. Поэтому правило перевернулось, а подробные
    проверки нажатия лежат в `dialog_cards_send_data.py`.

    Запрет `sendData` из правил мини-аппов в силе — но он про страницы, которые
    пишут результат в базу: там он обрывает незавершённую запись. Каталог не
    пишет ничего.
    """
    src = inline_script(APP)
    assert ".sendData(" in src, \
        "каталог не зовёт sendData — замеры-разговоры снова недостижимы"
    assert "openTelegramLink" in src, \
        "запасной путь вырезан: вне кнопки клавиатуры нажать будет нечем"
    ok("sendData основной путь, openTelegramLink запасной")


if __name__ == "__main__":
    raise SystemExit(run([
        check_keys_from_bot, check_domains_card_added, check_link_built_right,
        check_links_on_screen, check_open_path,
    ]))
