# -*- coding: utf-8 -*-
"""Проверки: замеры, которые правда идут разговором, открываются через sendData.

ПЕРЕПИСАНО 07.08.2026, спека 011 «все замеры в мини-аппе».

Что было в этом файле раньше. Через `sendData` открывались шесть замеров —
Движение, Люди рядом, Восемь фактов, Что ещё стоит знать, Деньги за месяц,
Области жизни. Это и был мост «мини-апп открывает разговор с ботом».

Почему утверждение отменено, а не ослаблено. Спека 011 отменяет сам мост как
основной путь к замеру: шесть замеров стали страницами. Решение Алексея после
живой пробы: «путает, когда тебя выкидывает в диалог». Ссылка со старт-параметром
до бота вообще не доходила, если чат с ботом уже есть, — это и был дефект 008,
который `sendData` закрывал.

Что осталось. Разговором по-прежнему идут карточки, где нужен живой отклик и
согласование двух людей: «Как я в наших отношениях», «Детектор взрыва», «Про
нас», «Надёжна ли связь», «Нагрузка», «Цифры группы», «Анализы». Им `sendData`
нужен, и весь его контракт проверяется здесь.

Дорожки «несколько за раз» в этом списке больше нет: 08.08.2026 она переехала
внутрь мини-аппа цепочкой экранов (спека 011, История 3). Её payload удалён, и
здесь проверяется обратное — что вход в дорожку боту НИЧЕГО не отправляет.
Сама дорожка проверяется в `dorozhka.py`.

Запрет `sendData` из правил мини-аппов не нарушается: он про страницы-опросники,
которые пишут результат в базу и обрываются на полуслове. Каталог не пишет
ничего.

Что проверяется:
  · payload буквально по контракту: `{"action":"open_card","card":"<ключ>"}`;
  · нажатие разговорной карточки правда зовёт `sendData`;
  · шесть переехавших замеров `sendData` больше НЕ зовут — они ссылки;
  · `sendData` недоступен или бросил ошибку — человек видит запасной путь
    (переписка и фраза, которую можно скопировать), а не тишину;
  · слушатель на элементе один, сколько бы раз экран ни пересобирался.

Запуск:  python3 checks/dialog_cards_send_data.py
"""

import json
import re

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
from chto_so_mnoy import FRESH, OBS, link, obs
from lib import catalog, catalog_taps, inline_script, ok, run, visible

APP = "kak-ty/app.html"

# Карточки, которые идут разговором. Ключи — из CARD_META бота.
CHAT_CARDS = ["pair_state", "pair_detector", "pair_context", "pair_are",
              "pair_load", "forum_scales", "labs"]

# Шесть переехавших: их в разговор больше не открывают.
MOVED = ["state_move", "state_people", "state_facts", "state_note",
         "state_money", "state_domains"]

BOT_NAME = "vslukh_shapovalov_bot"


# Контракт с ботом, буквально. Порядок полей тоже: сравниваем строку, а не dict.
def card_payload(key: str) -> str:
    return '{"action":"open_card","card":"%s"}' % key



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
OUT.dirty = cardPayload(null);
""".replace("CHAT", json.dumps(CHAT_CARDS)))

    for key, got in zip(CHAT_CARDS, c["cards"]):
        assert got == card_payload(key), \
            f"payload карточки «{key}»: {got} вместо {card_payload(key)}"
    ok("1. карточка-разговор: {\"action\":\"open_card\",\"card\":\"<ключ>\"}")

    # У дорожки payload нет вовсе: она идёт внутри мини-аппа (спека 011).
    src = inline_script(APP)
    assert "runAllPayload" not in src, \
        "у дорожки снова есть payload для бота — она опять уйдёт в чат"
    ok("1. у дорожки payload нет: она не разговор")

    # Порядок полей и разбор: бот читает JSON, и он обязан быть валидным.
    for got in c["cards"]:
        parsed = json.loads(got)
        assert set(parsed) <= {"action", "card"}, f"лишние поля в payload: {got}"
    assert json.loads(c["dirty"])["card"] == "", \
        "пустой ключ превратился в null — бот получит мусор"
    ok("1. payload разбирается как JSON, лишних полей нет")


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
    ok("2. пустые init-данные = кнопка клавиатуры = sendData можно")

    src = inline_script(APP)
    assert "initData" in src and "canSendData" in src, \
        "признак запуска не читается — доступность определяется наугад"
    ok("2. признак берётся из initData, а не из версии клиента наугад")


def check_tap_sends_data() -> None:
    """3. Нажатие разговорной карточки зовёт sendData с точным payload."""
    c = catalog_taps(base("ask=pair_state"), """
  var el = tap('data-send', 'card_pair_state');
  OUT.tap = el.click();
""")
    assert c["calls"]["sent"] == [card_payload("pair_state")], \
        f"в Телеграм ушло: {c['calls']['sent']}"
    assert c["calls"]["opened"] == [], \
        "рядом с sendData ещё и переписка открылась — человек получит два действия"
    assert c["tap"]["prevented"] >= 1, \
        "переход по ссылке не отменён — Телеграм уйдёт по href мимо sendData"
    ok("3. карточка первого экрана: один sendData, ссылка не срабатывает")

    # То же из полного списка: там карточка — сама ссылка.
    c2 = catalog_taps(base("ask=state_week"), """
  var el = tap('data-send', 'card_pair_detector');
  OUT.tap = el.click();
""")
    assert c2["calls"]["sent"] == [card_payload("pair_detector")], \
        f"из списка ушло: {c2['calls']['sent']}"
    ok("3. карточка списка: тот же sendData")

    # Все разговорные карточки несут свой payload в разметке.
    html = catalog_taps(base(), "")["html"]
    for key in CHAT_CARDS:
        want = 'data-send="' + card_payload(key).replace('"', "&quot;") + '"'
        assert want in html, f"у карточки «{key}» нет payload в разметке"
    ok(f"3. все {len(CHAT_CARDS)} разговорные карточки несут свой payload")


def check_moved_do_not_send() -> None:
    """4. Шесть переехавших замеров боту ничего не отправляют (спека 011)."""
    html = catalog_taps(base(), "")["html"]
    for key in MOVED:
        want = 'data-send="' + card_payload(key).replace('"', "&quot;") + '"'
        assert want not in html, \
            f"«{key}» переехал на страницу, а каталог всё ещё зовёт разговор"
    ok("4. ни один из шести не несёт payload разговора")

    c = catalog_taps(base("ask=state_move"), """
  var els = document.getElementById('app').querySelectorAll('[href]')
    .filter(function (e) { return e.tag.indexOf('state-move') >= 0; });
  OUT.found = els.length;
  OUT.tap = els.length ? els[0].click() : null;
""")
    assert c["found"] >= 1, "карточка «Движение» не стала ссылкой на страницу"
    assert c["calls"]["sent"] == [], \
        f"нажатие «Движения» отправило боту: {c['calls']['sent']}"
    assert c["calls"]["opened"] == [], \
        f"нажатие «Движения» открыло переписку: {c['calls']['opened']}"
    ok("4. нажатие «Движения» открывает страницу и ничего не отправляет")


def check_run_all_sends_data() -> None:
    """5. Вход в дорожку боту ничего не отправляет (спека 011, История 3)."""
    c = catalog_taps(base("ask=state_week"), """
  var el = tap('data-track', 'start');
  OUT.tap = el.click();
  OUT.href = el.getAttribute('href');
""")
    assert c["calls"]["sent"] == [], \
        f"вход в дорожку отправил боту: {c['calls']['sent']}"
    assert c["calls"]["opened"] == [], \
        f"вход в дорожку открыл переписку: {c['calls']['opened']}"
    assert "track=1" in (c["href"] or ""), \
        f"вход в дорожку ведёт не на её экран: {c['href']}"
    ok("5. дорожка идёт в мини-аппе: боту ни payload, ни переписки")


def check_fallback_when_unavailable() -> None:
    """6. sendData недоступен — человек видит запасной путь, а не тишину."""
    c = catalog_taps(base("ask=pair_state"), """
  var el = tap('data-send', 'card_pair_state');
  OUT.tap = el.click();
""", init_data=NOT_KEYBOARD)
    assert c["calls"]["sent"] == [], \
        "sendData позвали там, где он не работает — человек получит тишину"
    assert c["calls"]["opened"] == \
        ["https://t.me/%s?start=card_pair_state" % BOT_NAME], \
        f"запасной путь не сработал: {c['calls']['opened']}"
    ok("6. не кнопка клавиатуры: открывается переписка, прежний путь")

    text = visible(c["html"])
    assert "🫂 Как я в наших отношениях" in text, "фразы для чата на экране нет"
    assert "Скопировать фразу" in text, "кнопки «Скопировать фразу» нет"
    assert "скопируй фразу и отправь её в чат" in text, \
        "не сказано, что делать, если ничего не произошло"
    ok("6. на экране остались фраза и «Скопировать фразу»")

    # Телеграма нет вовсе — браузер: ссылка обязана остаться живой.
    c2 = catalog_taps(base("ask=pair_state"), """
  var el = tap('data-send', 'card_pair_state');
  OUT.tap = el.click();
  OUT.href = el.getAttribute('href');
""", telegram=False)
    assert c2["tap"]["prevented"] == 0, \
        "вне Телеграма переход отменён, а замена ему не работает"
    assert c2["href"] == "https://t.me/%s?start=card_pair_state" % BOT_NAME, \
        f"у карточки нет живой ссылки: {c2['href']}"
    ok("6. вне Телеграма работает обычная ссылка")


def check_fallback_when_throws() -> None:
    """7. sendData бросил ошибку — уходим в запасной путь, а не падаем."""
    c = catalog_taps(base("ask=pair_state"), """
  var el = tap('data-send', 'card_pair_state');
  OUT.tap = el.click();
""", extra_tg="sendData: function () { throw new Error('нельзя'); }")
    assert c["calls"]["opened"] == \
        ["https://t.me/%s?start=card_pair_state" % BOT_NAME], \
        f"после ошибки sendData запасной путь не сработал: {c['calls']['opened']}"
    ok("7. ошибка sendData не оставляет человека без действия")


def check_handler_bound_once() -> None:
    """8. Слушатель один, сколько бы раз экран ни пересобирался."""
    c = catalog_taps(base("ask=pair_state"), """
  render(); render();                       // пересобрали экран ещё дважды
  var el = tap('data-send', 'card_pair_state');
  OUT.tap = el.click();
""")
    assert c["tap"]["handlers"] == 1, \
        f"на элементе {c['tap']['handlers']} слушателя — нажатие сработает дважды"
    assert c["calls"]["sent"] == [card_payload("pair_state")], \
        f"после пересборки экрана ушло: {c['calls']['sent']}"
    ok("8. один слушатель, один sendData после трёх сборок экрана")


def check_old_path_left_as_backup() -> None:
    """9. Прежний путь остался в разметке запасным, а не удалён."""
    html = catalog_taps(base("ask=pair_state"), "")["html"]
    assert 'data-tglink="https://t.me/' in html, \
        "ссылка на переписку удалена — вне Телеграма нажать будет нечем"
    for key in CHAT_CARDS:
        assert "?start=card_" + key in html, f"у «{key}» нет запасной ссылки"
    ok("9. у каждой разговорной карточки рядом с payload лежит запасная ссылка")

    src = inline_script(APP)
    assert "openTelegramLink" in src, "запасной путь вырезан из кода"
    assert re.search(r"\.sendData\(", src), "основной путь не вызывается"
    ok("9. в коде оба пути: sendData основной, openTelegramLink запасной")


if __name__ == "__main__":
    raise SystemExit(run([
        check_payload_contract, check_availability_rule, check_tap_sends_data,
        check_moved_do_not_send, check_run_all_sends_data,
        check_fallback_when_unavailable, check_fallback_when_throws,
        check_handler_bound_once, check_old_path_left_as_backup,
    ]))
