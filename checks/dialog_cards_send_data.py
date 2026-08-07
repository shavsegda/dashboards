# -*- coding: utf-8 -*-
"""Проверки: замеры-разговоры и дорожка открываются через sendData.

Дефект с живого телефона. Алексей нажал «Восемь фактов» — мини-апп закрылся, в
чате ничего не произошло. По логам бота видно причину: `/start` со
старт-параметром до него не доходит вообще. `openTelegramLink` открывает
переписку, но payload теряется, если чат с ботом уже существует. Это поведение
Телеграма, и половина замеров была недостижима.

Правильный путь — `sendData`: боту приходит апдейт `web_app_data`, обработчик у
него уже есть. По документации Телеграма метод доступен ТОЛЬКО мини-аппам,
открытым кнопкой обычной клавиатуры, а у такого запуска init-данные пустые —
это и есть признак доступности. Каталог открывается именно кнопкой клавиатуры.

Запрет `sendData` из правил здесь не нарушается: он про страницы-опросники,
которые пишут результат в базу и обрываются на полуслове. Каталог не пишет
ничего.

Что проверяем:
  · payload буквально по контракту: `{"action":"open_card","card":"<ключ>"}` и
    `{"action":"run_all"}`;
  · нажатие карточки-разговора и входа в дорожку правда зовёт `sendData`;
  · `sendData` недоступен или бросил ошибку — человек видит запасной путь
    (переписка и фраза, которую можно скопировать), а не тишину;
  · слушатель на элементе один, сколько бы раз экран ни пересобирался.

Проверки исполняют страницу в node, жмут элементы собранной разметки и смотрят,
что ушло в Телеграм.

Запуск:  python3 checks/dialog_cards_send_data.py
"""

import json
import re

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
from chto_so_mnoy import FRESH, OBS, link, obs
from lib import catalog, catalog_taps, inline_script, ok, run, visible

APP = "kak-ty/app.html"

# Карточки, которые проходятся разговором. Ключи — из CARD_META бота.
CHAT_CARDS = ["state_move", "state_people", "state_facts", "state_note",
              "state_money", "state_domains"]

BOT_NAME = "vslukh_shapovalov_bot"

# Контракт с ботом, буквально. Порядок полей тоже: сравниваем строку, а не dict.
def card_payload(key: str) -> str:
    return '{"action":"open_card","card":"%s"}' % key


RUN_ALL_PAYLOAD = '{"action":"run_all"}'

# Init-данные непустые — значит мини-апп открыли НЕ кнопкой клавиатуры, и
# sendData там молча ничего не сделает.
NOT_KEYBOARD = "user=%7B%22id%22%3A777%7D&auth_date=1&hash=abc"


def base(*parts: str) -> str:
    return link(FRESH, obs(OBS), *parts)


# --------------------------------------------------------------------------


def check_payload_contract() -> None:
    """1. Payload собирается буквально по контракту с ботом."""
    c = catalog("""
OUT.cards = CHAT.map(function (k) { return cardPayload(k); });
OUT.runAll = runAllPayload();
OUT.dirty = cardPayload(null);
""".replace("CHAT", json.dumps(CHAT_CARDS)))

    for key, got in zip(CHAT_CARDS, c["cards"]):
        assert got == card_payload(key), \
            f"payload карточки «{key}»: {got} вместо {card_payload(key)}"
    ok("карточка-разговор: {\"action\":\"open_card\",\"card\":\"<ключ>\"}")

    assert c["runAll"] == RUN_ALL_PAYLOAD, f"payload дорожки: {c['runAll']}"
    ok('дорожка: {"action":"run_all"}')

    # Порядок полей и разбор: бот читает JSON, и он обязан быть валидным.
    for got in c["cards"] + [c["runAll"]]:
        parsed = json.loads(got)
        assert set(parsed) <= {"action", "card"}, f"лишние поля в payload: {got}"
    assert json.loads(c["dirty"])["card"] == "", \
        "пустой ключ превратился в null — бот получит мусор"
    ok("payload разбирается как JSON, лишних полей нет")


def check_availability_rule() -> None:
    """2. Доступность sendData считается по документированному признаку."""
    c = catalog("""
OUT.avail = {
  none:      canSendData(null),
  noMethod:  canSendData({ initData: "" }),
  keyboard:  canSendData({ initData: "", sendData: function () {} }),
  nullInit:  canSendData({ initData: null, sendData: function () {} }),
  menu:      canSendData({ initData: "user=%7B%22id%22%3A1%7D", sendData: function () {} })
};
""")
    a = c["avail"]
    assert a["none"] is False, "без Телеграма sendData считается доступным"
    assert a["noMethod"] is False, "метода нет, а мы собираемся его звать"
    assert a["keyboard"] is True, \
        "запуск кнопкой клавиатуры (пустые init-данные) не признан доступным"
    assert a["nullInit"] is True, "отсутствие init-данных — тот же запуск"
    assert a["menu"] is False, \
        "мини-апп открыт не кнопкой клавиатуры, а sendData считается рабочим"
    ok("пустые init-данные = кнопка клавиатуры = sendData можно")

    src = inline_script(APP)
    assert "initData" in src and "canSendData" in src, \
        "признак запуска не читается — доступность определяется наугад"
    ok("признак берётся из initData, а не из версии клиента наугад")


def check_tap_sends_data() -> None:
    """3. Нажатие карточки-разговора зовёт sendData с точным payload."""
    c = catalog_taps(base("ask=state_move"), """
  var el = tap('data-send', 'card_state_move');
  OUT.tap = el.click();
""")
    assert c["calls"]["sent"] == [card_payload("state_move")], \
        f"в Телеграм ушло: {c['calls']['sent']}"
    assert c["calls"]["opened"] == [], \
        "рядом с sendData ещё и переписка открылась — человек получит два действия"
    assert c["tap"]["prevented"] >= 1, \
        "переход по ссылке не отменён — Телеграм уйдёт по href мимо sendData"
    ok("карточка первого экрана: один sendData, ссылка не срабатывает")

    # То же из полного списка: там карточка — сама ссылка.
    c2 = catalog_taps(base("ask=state_week"), """
  var el = tap('data-send', 'card_state_facts');
  OUT.tap = el.click();
""")
    assert c2["calls"]["sent"] == [card_payload("state_facts")], \
        f"из списка ушло: {c2['calls']['sent']}"
    ok("карточка списка: тот же sendData")

    # Все шесть диалоговых карточек несут свой payload в разметке.
    html = catalog_taps(base(), "")["html"]
    for key in CHAT_CARDS:
        want = 'data-send="' + card_payload(key).replace('"', "&quot;") + '"'
        assert want in html, f"у карточки «{key}» нет payload в разметке"
    ok("все шесть карточек-разговоров несут свой payload")


def check_run_all_sends_data() -> None:
    """4. Вход в дорожку зовёт свой payload."""
    c = catalog_taps(base("ask=state_week"), """
  var el = tap('data-send', 'run_all');
  OUT.tap = el.click();
""")
    assert c["calls"]["sent"] == [RUN_ALL_PAYLOAD], \
        f"дорожка отправила: {c['calls']['sent']}"
    assert c["calls"]["opened"] == [], "дорожка вдобавок открыла переписку"
    ok("дорожка: один sendData с {\"action\":\"run_all\"}")


def check_fallback_when_unavailable() -> None:
    """5. sendData недоступен — человек видит запасной путь, а не тишину."""
    c = catalog_taps(base("ask=state_move"), """
  var el = tap('data-send', 'card_state_move');
  OUT.tap = el.click();
""", init_data=NOT_KEYBOARD)
    assert c["calls"]["sent"] == [], \
        "sendData позвали там, где он не работает — человек получит тишину"
    assert c["calls"]["opened"] == \
        ["https://t.me/%s?start=card_state_move" % BOT_NAME], \
        f"запасной путь не сработал: {c['calls']['opened']}"
    ok("не кнопка клавиатуры: открывается переписка, прежний путь")

    text = visible(c["html"])
    assert "🏃 Движение" in text, "фразы для чата на экране нет"
    assert "Скопировать фразу" in text, "кнопки «Скопировать фразу» нет"
    assert "скопируй фразу и отправь её в чат" in text, \
        "не сказано, что делать, если ничего не произошло"
    ok("на экране остались фраза и «Скопировать фразу»")

    # Телеграма нет вовсе — браузер: ссылка обязана остаться живой.
    c2 = catalog_taps(base("ask=state_move"), """
  var el = tap('data-send', 'card_state_move');
  OUT.tap = el.click();
  OUT.href = el.getAttribute('href');
""", telegram=False)
    assert c2["tap"]["prevented"] == 0, \
        "вне Телеграма переход отменён, а замена ему не работает"
    assert c2["href"] == "https://t.me/%s?start=card_state_move" % BOT_NAME, \
        f"у карточки нет живой ссылки: {c2['href']}"
    ok("вне Телеграма работает обычная ссылка")


def check_fallback_when_throws() -> None:
    """6. sendData бросил ошибку — уходим в запасной путь, а не падаем."""
    c = catalog_taps(base("ask=state_move"), """
  var el = tap('data-send', 'card_state_move');
  OUT.tap = el.click();
""", extra_tg="sendData: function () { throw new Error('нельзя'); }")
    assert c["calls"]["opened"] == \
        ["https://t.me/%s?start=card_state_move" % BOT_NAME], \
        f"после ошибки sendData запасной путь не сработал: {c['calls']['opened']}"
    ok("ошибка sendData не оставляет человека без действия")


def check_handler_bound_once() -> None:
    """7. Слушатель один, сколько бы раз экран ни пересобирался."""
    c = catalog_taps(base("ask=state_move"), """
  render(); render();                       // пересобрали экран ещё дважды
  var el = tap('data-send', 'card_state_move');
  OUT.tap = el.click();
""")
    assert c["tap"]["handlers"] == 1, \
        f"на элементе {c['tap']['handlers']} слушателя — нажатие сработает дважды"
    assert c["calls"]["sent"] == [card_payload("state_move")], \
        f"после пересборки экрана ушло: {c['calls']['sent']}"
    ok("один слушатель, один sendData после трёх сборок экрана")


def check_old_path_left_as_backup() -> None:
    """8. Прежний путь остался в разметке запасным, а не удалён."""
    html = catalog_taps(base("ask=state_move"), "")["html"]
    assert 'data-tglink="https://t.me/' in html, \
        "ссылка на переписку удалена — вне Телеграма нажать будет нечем"
    for key in CHAT_CARDS:
        assert "?start=card_" + key in html, f"у «{key}» нет запасной ссылки"
    ok("у каждой карточки рядом с payload лежит запасная ссылка")

    src = inline_script(APP)
    assert "openTelegramLink" in src, "запасной путь вырезан из кода"
    assert re.search(r"\.sendData\(", src), "основной путь не вызывается"
    ok("в коде оба пути: sendData основной, openTelegramLink запасной")


if __name__ == "__main__":
    raise SystemExit(run([
        check_payload_contract, check_availability_rule, check_tap_sends_data,
        check_run_all_sends_data, check_fallback_when_unavailable,
        check_fallback_when_throws, check_handler_bound_once,
        check_old_path_left_as_backup,
    ]))
