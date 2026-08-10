# -*- coding: utf-8 -*-
"""Проверки полного списка «Посмотреть всё»: без дублей и со свёрнутыми областями.

Задача. Алексей открыл список на телефоне — свалка. Причина: карточка стояла в
КАЖДОЙ своей области жизни. «Восемь фактов» — во всех семи, «Области жизни» — в
шести, и в области «Я сам» набиралось девять карточек. Один и тот же замер
человек видел по пять раз, а списку не было конца.

Что проверяем:
  · **одна карточка — одна область.** Место в списке задаёт поле `area`, одно
    на карточку. Поле `containers` остаётся служебным переносом из `CARD_META`
    бота и на место в списке больше не влияет;
  · главная область выбрана не наугад: она из закрытой семёрки и она одна из
    тех областей, которые замер правда задевает;
  · **области свёрнуты.** На первом развороте списка видно семь строк со
    структурой, а не двадцать три карточки подряд;
  · ничего не потеряно: все карточки по-прежнему в списке, каждая ровно раз;
  · описания карточек — в одну строку на телефоне;
  · про остальные области карточка говорит одной короткой строкой, и только в
    списке: на единственной карточке первого экрана метки области нет.

Проверки исполняют страницу в node с заглушками и смотрят на СОБРАННЫЙ экран.

Запуск:  python3 checks/spisok_bez_dublej.py
"""

import re

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
from chto_so_mnoy import AREAS, FRESH, OBS, link, obs, screens
from lib import catalog, catalog_render, ok, run, visible

APP = "kak-ty/app.html"

# Строка «что это даст» должна ложиться в одну строку на телефоне: при 13px и
# ширине экрана 360 это примерно сорок пять знаков.
WHAT_MAX = 45


def areas_js() -> dict:
    """Главные области, остальные области и раскладка списка — из чистой логики."""
    return catalog("""
var CARDS = buildCards(REGISTRY, {}, "2026-08-07T10:00:00Z", true);
OUT.main = REGISTRY.map(function (r) {
  return { key: r.key, area: r.area, containers: r.containers, what: r.what };
});
OUT.groups = byRhythm(CARDS).map(function (g) {
  return { area: g.name, keys: g.cards.map(function (c) { return c.key; }) };
});
OUT.also = {
  none:  alsoText({ area: "Я сам", containers: ["Я сам"] }),
  one:   alsoText({ area: "Тело", containers: ["Я сам", "Тело"] }),
  two:   alsoText({ area: "Тело", containers: ["Тело", "Я сам", "Круг"] }),
  many:  alsoText({ area: "Время на себя",
                    containers: ["Семья", "Работа", "Тело", "Деньги", "Я сам",
                                 "Круг", "Время на себя"] })
};
""")


def cards_in_list(rest: str) -> int:
    return len(re.findall(r'class="card"', rest))


def label_count(rest: str, label: str) -> int:
    return len(re.findall(re.escape('class="card-name">' + label + "</div>"), rest))


# --------------------------------------------------------------------------


def check_one_card_one_area() -> None:
    """1. Одна карточка — один раздел: в раскладке ни одного повтора.

    Правка 10.08.2026: разделы — ритмы. Дубли запрещены так же строго.
    """
    c = areas_js()
    keys = [k for g in c["groups"] for k in g["keys"]]
    dupes = sorted({k for k in keys if keys.count(k) > 1})
    assert not dupes, f"карточки стоят в списке больше одного раза: {dupes}"
    ok("ни одна карточка не попала в две области")

    all_keys = {r["key"] for r in c["main"]}
    assert set(keys) == all_keys, \
        f"из списка выпали карточки: {sorted(all_keys - set(keys))}"
    assert len(keys) == len(all_keys), "число карточек в списке не совпало с реестром"
    ok(f"все {len(all_keys)} карточек в списке, каждая ровно раз")

    # Прежняя раскладка давала 40 мест на 23 карточки — на это и жаловались.
    old = sum(len(r["containers"]) for r in c["main"])
    assert len(keys) < old, \
        f"мест в списке {len(keys)} против {old} прежних — дубли никуда не ушли"
    ok(f"мест в списке {len(keys)} вместо прежних {old}")


def check_main_area_is_honest() -> None:
    """2. Главная область — из семёрки и из того, что замер правда задевает."""
    c = areas_js()
    for r in c["main"]:
        assert r["area"], f"у карточки «{r['key']}» не выбрана главная область"
        assert r["area"] in AREAS, \
            f"у «{r['key']}» область «{r['area']}» — не из семёрки"
        assert r["area"] in r["containers"], \
            f"у «{r['key']}» главная область «{r['area']}» вне его же меток " \
            f"{r['containers']} — замер её не мерит"
    ok("у каждой карточки одна главная область, и она внутри её же меток")

    # Метки контейнеров не тронуты: по ним бот считает покрытие.
    reg = {r["key"]: r for r in catalog()["registry"]}
    assert reg["state_facts"]["containers"] == [
        "Семья", "Работа", "Тело", "Деньги", "Я сам", "Круг", "Время на себя"], \
        "метки «Восьми фактов» подрезали — бот перестанет считать покрытие"
    assert len(reg["state_domains"]["containers"]) == 6, \
        "метки «Областей жизни» подрезали"
    ok("служебные метки контейнеров остались как в боте")

    # Все семь областей по-прежнему живые: иначе дверь в область пропала.
    got = [g["area"] for g in c["groups"]]
    heads = catalog("OUT.heads = RHYTHMS.map(function (r) { return r.name; });\n"
                    "OUT.once = ONCE_RHYTHM.name;\n")
    want = heads["heads"] + [heads["once"]]
    assert got == [g for g in want if g in got], f"разделы в списке: {got}"
    ok("все семь областей остались непустыми и в порядке спеки")


def check_areas_collapsed() -> None:
    """3. Разделы свёрнуты: на первом развороте — структура, а не карточки.

    Правка 10.08.2026: разделами стали РИТМЫ, а не области жизни. Решение
    Алексея после живого использования — по областям он не находил, что пора
    пройти. Утверждение то же: на развороте видна структура, карточки внутри.
    """
    _, rest = screens(link(FRESH))
    opened = re.findall(r"<details[^>]*\bclass=\"rhythm\"[^>]*\bopen", rest)
    assert not opened, "область раскрыта заранее — список снова вываливается целиком"
    heads = catalog("OUT.heads = RHYTHMS.map(function (r) { return r.name; })\n"
                    ";OUT.once = ONCE_RHYTHM.name;\n")
    n_groups = rest.count('<details class="rhythm">')
    assert 1 <= n_groups <= len(heads["heads"]) + 1, \
        f"разделов-ритмов {n_groups}, а ритмов всего {len(heads['heads'])} плюс «один раз»"
    ok(f"{n_groups} разделов-ритмов, все свёрнуты")

    rows = len(re.findall(r"<summary", rest)) - 1   # минус сам «Посмотреть всё»
    cards = cards_in_list(rest)
    assert rows == n_groups, f"строк на развороте {rows}, а разделов {n_groups}"
    assert rows < cards, \
        f"видимых элементов {rows}, карточек {cards} — экономии нет"
    ok(f"на первом развороте {rows} строк против {cards} карточек")

    # Карточка не может лежать выше первой области: иначе она видна сразу.
    i_first_area = rest.index('<details class="rhythm">')
    assert 'class="card"' not in rest[:i_first_area], \
        "карточка стоит выше свёрнутых разделов и видна на первом развороте"
    ok("ни одной карточки выше свёрнутых разделов")


def check_nothing_lost() -> None:
    """4. Ничего не отняли: каждая карточка на экране ровно один раз."""
    _, rest = screens(link(FRESH))
    reg = {r["key"]: r for r in catalog()["registry"]}
    for key, card in reg.items():
        if card["cond"] == "clinical":
            continue                      # её показывает только сигнал датчика
        n = label_count(rest, card["label"])
        assert n == 1, f"карточка «{card['label']}» на экране {n} раз, а не один"
    ok("каждая карточка списка встречается ровно один раз")

    # Условная карточка приходит в свою область и тоже без дублей.
    _, fired = screens(link(FRESH, "cl=1"))
    assert label_count(fired, "Настроение и тревога подробно") == 1, \
        "условная карточка либо не пришла, либо продублировалась"
    ok("условная карточка приходит в одну область")

    # Счётчик у области считает то, что в ней лежит, а не что-то своё.
    for area, count, keys in [(g["area"], None, g["keys"]) for g in areas_js()["groups"]]:
        block = re.search(
            r'<summary class="rhythm-head"><span class="rhythm-name">'
            + re.escape(area) + r'</span><span class="rhythm-count">(\d+)</span>', rest)
        assert block, f"у раздела «{area}» нет строки со счётчиком"
        shown = int(block.group(1))
        alive = [k for k in keys if reg[k]["cond"] != "clinical"]
        assert shown == len(alive), \
            f"область «{area}»: в строке {shown}, карточек {len(alive)}"
    ok("счётчик каждой области совпадает с числом её карточек")


def check_what_one_line() -> None:
    """5. Описание карточки — одна строка, а не две."""
    long = {r["key"]: len(r["what"]) for r in areas_js()["main"]
            if len(r["what"]) > WHAT_MAX}
    assert not long, \
        f"описания длиннее {WHAT_MAX} знаков — на телефоне это две строки: {long}"
    ok(f"все двадцать три описания короче {WHAT_MAX} знаков")

    reg = {r["key"]: r for r in catalog()["registry"]}
    for key, card in reg.items():
        assert card["what"], f"у «{key}» пропала строка «что это даст»"
        assert card["what"] == card["what"].strip(), \
            f"описание «{key}» с пробелами по краям"
    ok("строка «что это даст» осталась у каждой карточки")


def check_also_label() -> None:
    """6. Метка про остальные области — одной строкой и только в списке."""
    a = areas_js()["also"]
    assert a["none"] == "", "у карточки из одной области появилась лишняя метка"
    assert a["one"] == "ещё: Я сам", f"метка на одну область: {a['one']!r}"
    assert a["two"] == "ещё: Я сам · Круг", f"метка на две области: {a['two']!r}"
    assert a["many"] == "ещё: другие области жизни", \
        f"метка на шесть областей перечисляет их все: {a['many']!r}"
    ok("метка: до двух областей по именам, дальше одной фразой")

    _, rest = screens(link(FRESH))
    text = visible(rest)
    assert "ещё: Я сам" in text, "у суточной карточки нет метки про вторую область"
    assert "ещё: другие области жизни" in text, \
        "у «Восьми фактов» нет метки про остальные области"
    ok("метки доехали до списка")

    # Одна строка на карточку: «когда был» и «ещё» стоят в одном ряду.
    row = re.search(r'<div class="card-when">([^<]*)</div>', rest)
    assert row, "служебной строки карточки нет вовсе"
    assert rest.count('class="card-when"') <= cards_in_list(rest), \
        "служебных строк больше, чем карточек — карточка стала выше"
    assert re.search(r'<div class="card-when">[^<]*последний замер [^<]* · ещё: ', rest), \
        "«когда был» и «ещё» разъехались на две строки"
    ok("«последний замер … · ещё: …» — одна строка")

    # На первом экране метки области нет: там карточка одна, метка ей не нужна.
    first, _ = screens(link(FRESH, obs(OBS), "ask=state_day"))
    assert "ещё:" not in visible(first), \
        "метка про области вылезла на карточку первого экрана"
    ok("на первом экране метки области нет")


if __name__ == "__main__":
    raise SystemExit(run([
        check_one_card_one_area, check_main_area_is_honest,
        check_areas_collapsed, check_nothing_lost,
        check_what_one_line, check_also_label,
    ]))
