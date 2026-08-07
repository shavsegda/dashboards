# -*- coding: utf-8 -*-
"""Проверки каталога «Как ты?»: новые карточки и названия по содержанию.

Задачи:
  · в каталоге появляются карточки, которые бот уже умеет: движение, люди
    рядом, восемь фактов, свободная строка, деньги, потребности, раз в год,
    плюс условные — полная версия клинических шкал и команда;
  · четыре карточки называются по содержанию, а не по сроку (007, FR-011):
    Сутки → Тонус и сон · Неделя → Самочувствие · Месяц → Стресс и сон ·
    Квартал → Удовлетворённость и смысл;
  · условия видимости приходят параметрами ссылки: `cl=1` открывает полную
    версию, `tm=0` прячет команду.

Ключи, названия и сроки сверяются с реестрами `bot.py`, а не с памятью.

Запуск:  python3 checks/kak_ty_catalog.py
"""

import re

import lib_path  # noqa: F401
from lib import BOT, ROOT, bot, catalog, catalog_render, html, ok, run

APP = "kak-ty/app.html"

# Названия по содержанию (007, FR-011). В bot.py эти карточки по-прежнему
# называются по сроку — там переименование делает другой агент, и расхождение
# должно быть видно именно здесь.
RENAMED = {
    "state_day": "Тонус и сон",
    "state_week": "Самочувствие",
    "state_month": "Стресс и сон",
    "state_quarter": "Удовлетворённость и смысл",
}

# Карточки, которых в каталоге не было. Ключ → (раздел, условие показа).
NEW_CARDS = {
    "state_move": ("week", None),
    "state_people": ("week", None),
    "state_facts": ("week", None),
    "state_note": ("week", None),
    "state_money": ("month", None),
    "state_needs": ("quarter", None),
    "state_clinical": ("month", "clinical"),
    "state_team": ("quarter", "team"),
    "state_year": ("year", None),
}

# Точные тексты кнопок бота: карточка-разговор подсказывает человеку фразу, и
# фраза с опечаткой просто не сработает.
PHRASES = {
    "state_move": "🏃 Движение",
    "state_people": "🫂 Люди рядом",
    "state_facts": "✅ Восемь фактов",
    "state_note": "✍️ Что ещё стоит знать",
    "state_money": "💵 Деньги за месяц",
}


def registry() -> dict:
    return {r["key"]: r for r in catalog()["registry"]}


def check_new_cards_present() -> None:
    """1. Новые карточки в каталоге, каждая в своём разделе."""
    reg = registry()
    for key, (section, cond) in NEW_CARDS.items():
        assert key in reg, f"карточки «{key}» нет в каталоге"
        assert reg[key]["section"] == section, \
            f"«{key}» стоит в разделе «{reg[key]['section']}», а не «{section}»"
        assert reg[key]["cond"] == cond, \
            f"условие показа «{key}»: {reg[key]['cond']} вместо {cond}"
    ok(f"все {len(NEW_CARDS)} новых карточек на месте, разделы и условия те же")

    sections = set(catalog()["rhythms"]) | {"once"}
    for key, card in reg.items():
        assert card["section"] in sections, \
            f"у «{key}» раздел «{card['section']}», которого нет в списке ритмов"
    ok("у каждой карточки есть свой раздел")


def check_renamed() -> None:
    """2. Четыре карточки названы по содержанию, а не по сроку."""
    reg = registry()
    for key, label in RENAMED.items():
        assert reg[key]["label"] == label, \
            f"«{key}» называется «{reg[key]['label']}», а не «{label}»"
    ok("Тонус и сон · Самочувствие · Стресс и сон · Удовлетворённость и смысл")

    # Названия по сроку не должны остаться ни у одной карточки: человек не
    # приходит с периодом, он приходит с вопросом про себя.
    by_period = {"Сутки", "Неделя", "Месяц", "Квартал"}
    left = {k: c["label"] for k, c in reg.items() if c["label"] in by_period}
    assert not left, f"названия по сроку остались: {left}"
    ok("ни одной карточки, названной сроком")


def check_matches_bot() -> None:
    """3. Ключи, сроки и метки контейнеров — как в реестрах bot.py."""
    b = bot()
    reg = registry()
    cov = {k: (label, days) for k, label, _g, days, _q in b["COVERAGE_MAP"]}

    for key, card in reg.items():
        assert key in b["CARD_META"], f"карточки «{key}» нет в CARD_META бота"
        meta = b["CARD_META"][key]
        assert (meta.get("door") or "state") == "state", \
            f"«{key}» живёт за кнопкой «Как я устроен», а стоит в «Как ты?»"
        assert card["containers"] == meta["containers"], \
            f"метка «{key}»: {card['containers']} против {meta['containers']} в боте"
        assert card["section"] == meta["section"], \
            f"раздел «{key}»: {card['section']} против {meta['section']} в боте"
        assert key in cov, f"«{key}» нет в COVERAGE_MAP — не будет свежести"
        label, days = cov[key]
        assert card["days"] == days, \
            f"срок «{key}»: {card['days']} дней против {days} в боте"
        if key not in RENAMED:
            assert card["label"] == label, \
                f"название «{key}»: «{card['label']}» против «{label}» в боте"
    ok(f"все {len(reg)} карточек сходятся с CARD_META и COVERAGE_MAP")

    keys = set(b["KAK_TY_KEYS"])
    for key in reg:
        assert key in keys, \
            f"«{key}» не едет в каталог параметром f= — карточка будет без свежести"
    ok("свежесть приезжает по всем карточкам каталога")

    # Замеры структуры в каталоге состояния не появляются (003, FR-002f).
    for key in ("level", "ztpi", "stressrisk", "personality", "values"):
        assert key not in reg, f"замер структуры «{key}» пролез в «Как ты?»"
    ok("ни одного замера структуры в каталоге состояния")


def check_every_card_has_door() -> None:
    """4. У каждой карточки есть дверь: страница, фраза или «идёт следом»."""
    reg = registry()
    for key, card in reg.items():
        assert card["url"] or card["phrase"] or card["after"], \
            f"карточка «{key}» никуда не ведёт"
    ok("каждая карточка открывается")

    bot_text = BOT.read_text(encoding="utf-8")
    for key, phrase in PHRASES.items():
        assert reg[key]["phrase"] == phrase, \
            f"фраза «{key}»: «{reg[key]['phrase']}» вместо «{phrase}»"
    for key, card in reg.items():
        if card["phrase"]:
            assert f'"{card["phrase"]}"' in bot_text, \
                f"фразы «{card['phrase']}» нет в bot.py — человек отправит её зря"
    ok("все фразы-подсказки существуют в боте буквально")

    # Страница, на которую ведёт карточка, должна существовать в этом клоне:
    # кнопка на 404 хуже отсутствия кнопки.
    for key, card in reg.items():
        if not card["url"]:
            continue
        m = re.match(r"https://shapovalov-aleksey\.ru/(.+)$", card["url"])
        assert m, f"адрес «{key}» не с нашего домена: {card['url']}"
        p = ROOT / m.group(1)
        assert p.exists(), f"карточка «{key}» ведёт на несуществующий файл: {p}"
    ok("все адреса карточек ведут на существующие страницы")


def check_conditional_visibility() -> None:
    """5. Условные карточки: `cl=1` открывает полную версию, `tm=0` прячет команду."""
    js = """
function keys(opts) { return visibleCards(REGISTRY, opts).map(function (c) { return c.key; }); }
OUT.plain = keys({});
OUT.clinical = keys({ clinicalFired: true });
OUT.noTeam = keys({ hasTeam: false });
OUT.noPair = keys({ hasPair: false });
OUT.noForum = keys({ hasForum: false });
"""
    c = catalog(js)
    assert "state_clinical" not in c["plain"], \
        "полная версия клинических шкал показывается без сигнала датчика"
    assert "state_clinical" in c["clinical"], \
        "датчик сработал (cl=1), а карточки полной версии нет"
    ok("полной версии нет, пока не сработал датчик")

    assert "state_team" in c["plain"], \
        "признак не спрашивали, а карточка команды уже спрятана — «не знаю» ≠ «нет»"
    assert "state_team" not in c["noTeam"], \
        "человек сказал «команды нет» (tm=0), а карточка команды осталась"
    ok("команду прячет только прямое «нет»")

    assert not [k for k in c["noPair"] if k.startswith("pair_")], \
        "парные карточки остались у человека без пары"
    assert "forum_scales" not in c["noForum"], "карточка группы осталась без группы"
    assert "state_facts" in c["noPair"] and "state_move" in c["noPair"], \
        "вместе с парными спрятало новые карточки"
    ok("парные и групповые прячутся как раньше, новые не задеты")

    # Разбор параметров ссылки: он делается в той же логике, что и у бота.
    src = html(APP)
    assert 'params.get("cl") === "1"' in src, \
        "параметр cl не читается — условие приходит от бота, а не выдумывается"
    assert 'params.get("tm") === "0"' in src, "параметр tm не читается"
    assert "clinicalFired" in src and "hasTeam" in src, \
        "флаги не передаются в отбор карточек"
    ok("cl и tm читаются из ссылки и уходят в отбор карточек")


def check_honest_size() -> None:
    """6. Честная длина: месяц больше не обещает 81 вопрос."""
    reg = registry()
    assert "81" not in reg["state_month"]["size"], \
        f"месяц всё ещё обещает 81 вопрос: {reg['state_month']['size']}"
    assert "28" not in reg["state_week"]["size"], \
        f"неделя обещает прежние 28 вопросов: {reg['state_week']['size']}"
    for key, card in reg.items():
        assert card["size"], f"у «{key}» не написано, сколько это займёт"
        assert card["what"], f"у «{key}» нет строки «что это даст»"
    ok("у каждой карточки есть и «что это даст», и честная длина")


def check_no_scale_names() -> None:
    """7. Ни одного названия шкалы и ни одного балла в текстах каталога."""
    body = html(APP)
    # Берём только то, что человек видит: строки в кавычках внутри REGISTRY.
    reg = registry()
    seen = " ".join(str(c["label"]) + " " + str(c["what"]) + " " + str(c["size"])
                    for c in reg.values())
    for bad in ("PHQ", "GAD", "UCLA", "AUDIT", "ASRM", "PSS", "ISI", "BPNSFS",
                "SWLS", "MLQ", "FFMQ", "OLBI", "RSES", "балл", "Эдмондсон",
                "EVS", "KMS"):
        assert bad not in seen, f"в тексте карточек название шкалы или балл: «{bad}»"
    ok("в карточках нет ни аббревиатур, ни баллов")

    for bad in ("мало", "плохо", "запустил"):
        assert bad not in seen.lower(), f"оценочное слово в тексте карточек: «{bad}»"
    ok("в карточках нет оценочных слов")

    assert "Один балл" not in body or "не будет" in body, \
        "пропала оговорка про то, что сводного балла не будет"
    ok("оговорка про отсутствие сводного балла на месте")


def check_renders() -> None:
    """8. Каталог собирается целиком — на выдуманных данных, как в телефоне.

    Разбор текста не видит ошибок шаблона: их видно только на отрисовке. Здесь
    скрипт исполняется весь, с заглушками вместо браузера и сети.
    """
    base = "?u=tg_777&f=state_day:2026-08-06,state_week:2026-07-01"
    plain = catalog_render(base)
    assert "undefined" not in plain and "NaN" not in plain,         "в собранной странице есть undefined или NaN — где-то пустое поле"
    for name in ("Тонус и сон", "Самочувствие", "Стресс и сон",
                 "Удовлетворённость и смысл", "Движение", "Люди рядом",
                 "Восемь фактов", "Что ещё стоит знать", "Деньги за месяц",
                 "Потребности", "Раз в год"):
        assert name in plain, f"карточки «{name}» нет на собранной странице"
    ok("страница собирается, все карточки видны, пустых полей нет")

    assert "Настроение и тревога подробно" not in plain,         "полная версия видна на странице без сигнала"
    fired = catalog_render(base + "&cl=1")
    assert "Настроение и тревога подробно" in fired,         "cl=1 не открыл полную версию на собранной странице"
    ok("cl=1 добавляет карточку на страницу, без него её нет")

    assert "Психобезопасность команды" in plain, "карточка команды пропала"
    no_team = catalog_render(base + "&tm=0")
    assert "Психобезопасность команды" not in no_team,         "tm=0 не спрятал карточку команды на собранной странице"
    ok("tm=0 убирает карточку команды со страницы")

    # Строка «Пусто: …» была честной, пока замеров про работу и деньги не было.
    # Теперь они есть, и строка должна исчезнуть сама, а не остаться врать.
    assert "Пусто:" not in plain,         "страница всё ещё говорит, что областей жизни без замеров нет вовсе"
    ok("строка про пустые области жизни ушла: замеры появились")


if __name__ == "__main__":
    raise SystemExit(run([
        check_new_cards_present, check_renamed, check_matches_bot,
        check_every_card_has_door, check_conditional_visibility,
        check_honest_size, check_no_scale_names, check_renders,
    ]))
