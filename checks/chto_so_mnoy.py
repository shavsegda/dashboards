# -*- coding: utf-8 -*-
"""Проверки первого экрана «Что со мной?» (спека 007).

Задача. Раньше экран открывался каталогом из тринадцати замеров — то есть
списком долгов. Теперь он открывается тем, что бот уже про человека видит, и
ровно одной просьбой. Список остаётся, но за одним нажатием и сгруппирован по
областям жизни, а не по срокам.

Контракт с ботом (соблюдается буквально):
  · `o=`   — текст наблюдения, urlencoded, до 400 символов. Показывается как
             есть; мини-апп своих толкований не добавляет;
  · `ask=` — ключ одной предложенной карточки;
  · нет `o`   → честное «пока ничего не знаю»;
  · нет `ask` → просьбы нет, сказано когда заглянуть.

Четыре состояния экрана — это две пары «есть/нет» на два параметра:
  observation_ask · observation_only · first_step · quiet.

Проверки исполняют страницу в node с заглушками и смотрят на СОБРАННЫЙ экран,
а не ищут слова в исходнике: ошибку шаблона разбором текста не поймать.

Запуск:  python3 checks/chto_so_mnoy.py
"""

import re
import urllib.parse

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
from lib import bot, catalog, catalog_render, html, inline_script, ok, run, visible

APP = "kak-ty/app.html"

# Живой пример наблюдения из спеки. Без апострофов: строка едет в node через repr.
OBS = "Силы падают третью неделю подряд. Сон при этом не изменился."

# Даты последних замеров — как их присылает бот параметром f=.
FRESH = "f=state_day:2026-08-06,state_week:2026-08-05,state_month:2026-06-01"

# Области жизни в порядке спеки (FR-010).
AREAS = ["Я сам", "Тело", "Семья", "Круг", "Работа", "Деньги", "Время на себя"]

# Названия разделов по сроку. На экране их быть не должно нигде: человек не
# приходит с периодом.
BY_PERIOD_HEADS = ["каждый день", "раз в неделю", "раз в месяц", "раз в квартал",
                   "раз в полгода"]

# Слова-шум, которые убираются целиком (раздел «Что убирается как шум»).
NOISE_WORDS = ["не проходил", "неизвестно", "свежее", "просрочено", "Пусто:"]

# Слово ищем как слово, а не как кусок другого: «пора» живёт внутри «опоры»,
# и без границ проверка падала бы на честном тексте.
LETTER = "[0-9A-Za-zА-Яа-яЁё]"


def has_word(text: str, word: str) -> bool:
    return re.search(f"(?<!{LETTER}){re.escape(word)}(?!{LETTER})", text) is not None


def link(*parts: str) -> str:
    """Адрес каталога с параметрами, как его собирает бот."""
    return "?u=tg_777&" + "&".join(p for p in parts if p)


def obs(text: str) -> str:
    return "o=" + urllib.parse.quote(text, safe="")


def screens(search: str):
    """Собранный экран, разрезанный на первый экран и список за ссылкой.

    Резать надо: «наблюдение выше карточек» проверяется по первому экрану, а
    полный список живёт ниже и на порядок чтения не влияет.
    """
    h = catalog_render(search)
    assert 'id="all"' in h, "на странице нет блока полного списка (id=all)"
    i = h.index('id="all"')
    return h[:i], h[i:]


def cards_in(part: str) -> int:
    return len(re.findall(r'class="card"', part))


def obs_text(part: str) -> str:
    """Текст наблюдения ровно как он попал на экран, без обёртки."""
    m = re.search(r'<div class="obs-text">(.*?)</div>', part, re.S)
    return m.group(1) if m else ""


# --------------------------------------------------------------------------


def check_button_name() -> None:
    """1. Экран называется «Что со мной?» — так, как человек спрашивает сам."""
    src = html(APP)
    assert "<title>Что со мной?</title>" in src, "заголовок вкладки не переименован"
    first, _ = screens(link())
    assert "Что со мной?" in visible(first), "на экране нет заголовка «Что со мной?»"
    assert "Как ты?" not in visible(first), \
        "старое название «Как ты?» осталось на экране"
    ok("заголовок «Что со мной?», старого названия на экране нет")


def check_four_states_pure() -> None:
    """2. Четыре состояния экрана считаются в чистой логике."""
    c = catalog("""
OUT.states = {
  observation_ask:  screenState("текст", { key: "state_week" }),
  observation_only: screenState("текст", null),
  first_step:       screenState(null, { key: "state_week" }),
  quiet:            screenState(null, null)
};
OUT.parse = {
  empty: parseObservation(""),
  blank: parseObservation("   "),
  nul:   parseObservation(null),
  plain: parseObservation("  два пробела по краям  "),
  long:  (parseObservation(new Array(600).join("а")) || "").length
};
OUT.pick = {
  found:   (pickAsk([{ key: "state_week" }], "state_week") || {}).key || null,
  missing: pickAsk([{ key: "state_week" }], "state_nope"),
  empty:   pickAsk([{ key: "state_week" }], ""),
  nul:     pickAsk([{ key: "state_week" }], null)
};
""")
    for want, got in c["states"].items():
        assert got == want, f"состояние «{want}» посчиталось как «{got}»"
    ok("observation_ask · observation_only · first_step · quiet")

    p = c["parse"]
    assert p["empty"] is None and p["blank"] is None and p["nul"] is None, \
        "пустое наблюдение не превратилось в «ничего не знаю»"
    assert p["plain"] == "два пробела по краям", f"текст поехал: {p['plain']!r}"
    assert p["long"] == 400, f"наблюдение не обрезано до 400 символов: {p['long']}"
    ok("пустое наблюдение = нет наблюдения, длинное режется на 400")

    k = c["pick"]
    assert k["found"] == "state_week", "просьба не находит свою карточку по ключу"
    assert k["missing"] is None and k["empty"] is None and k["nul"] is None, \
        "неизвестный ключ просьбы даёт карточку — на экране будет пустая рамка"
    ok("ключ просьбы: своя карточка или ничего, без выдумок")


def check_four_states_on_screen() -> None:
    """3. Четыре состояния собираются на экране, каждое со своим текстом."""
    a, _ = screens(link(FRESH, obs(OBS), "ask=state_week"))
    ta = visible(a)
    assert OBS in ta, "наблюдение не доехало до экрана"
    assert "Чтобы сказать точнее, не хватает одного" in ta, \
        "есть наблюдение и просьба, а просьба не подписана"
    assert cards_in(a) == 1, f"карточек на экране {cards_in(a)}, а не одна"
    ok("наблюдение + просьба: текст, подпись и одна карточка")

    b, _ = screens(link(FRESH, obs(OBS)))
    tb = visible(b)
    assert OBS in tb, "наблюдение пропало, когда просьбы нет"
    assert cards_in(b) == 0, "просьбы нет, а карточка на экране осталась"
    assert "Загляни через неделю" in tb, "не сказано, когда заглянуть"
    ok("наблюдение без просьбы: сказано, когда заглянуть, карточки нет")

    c, _ = screens(link("ask=state_week"))
    tc = visible(c)
    assert "пока ничего не знаю" in tc, \
        "данных нет, а честного «пока ничего не знаю» на экране нет"
    assert "Начни с этого" in tc, "первый шаг не назван первым шагом"
    assert cards_in(c) == 1, f"на первом шаге карточек {cards_in(c)}, а не одна"
    ok("данных нет: честное «пока ничего не знаю» и один первый шаг")

    d, _ = screens(link())
    td = visible(d)
    assert "пока ничего не знаю" in td, "нет ни наблюдения, ни честной строки"
    assert cards_in(d) == 0, "ни наблюдения, ни просьбы, а карточка есть"
    assert "Загляни через неделю" in td, "не сказано, когда заглянуть"
    ok("ни наблюдения, ни просьбы: честно и без просьбы")


def check_observation_above_cards() -> None:
    """4. Наблюдение стоит выше карточек: отдали раньше, чем попросили."""
    first, _ = screens(link(FRESH, obs(OBS), "ask=state_week"))
    i_obs = first.index("Что видно по твоим ответам")
    i_card = first.index('class="card"')
    assert i_obs < i_card, "карточка стоит выше наблюдения — снова просим первыми"
    ok("наблюдение выше карточки")

    whole = catalog_render(link(FRESH, obs(OBS), "ask=state_week"))
    assert whole.index("Что видно по твоим ответам") < whole.index('id="all"'), \
        "наблюдение уехало ниже полного списка"
    ok("наблюдение выше полного списка")


def check_observation_verbatim() -> None:
    """5. Наблюдение показано как есть: без своих толкований и без разметки."""
    first, _ = screens(link(FRESH, obs(OBS), "ask=state_week"))
    assert obs_text(first) == OBS, \
        f"текст наблюдения изменён: {obs_text(first)!r} вместо {OBS!r}"
    ok("текст наблюдения на экране совпадает с текстом бота посимвольно")

    long_text = "Сон " + "а" * 500
    cut, _ = screens(link(obs(long_text), "ask=state_week"))
    assert len(obs_text(cut)) == 400, \
        f"на экране {len(obs_text(cut))} символов наблюдения вместо 400"
    ok("наблюдение длиннее 400 символов обрезается")

    evil, _ = screens(link(obs("<b>жирный</b> текст"), "ask=state_week"))
    assert "&lt;b&gt;" in obs_text(evil), "разметка из наблюдения не обезврежена"
    assert "<b>" not in obs_text(evil), "тег из наблюдения попал на страницу живым"
    ok("разметка внутри наблюдения не исполняется")


def check_exactly_one_ask() -> None:
    """6. Просьба ровно одна, и она та, которую назвал бот."""
    reg = {r["key"]: r for r in catalog()["registry"]}
    for key in ("state_week", "state_move", "state_needs", "labs"):
        first, _ = screens(link(FRESH, obs(OBS), "ask=" + key))
        assert cards_in(first) == 1, \
            f"просьба «{key}»: карточек {cards_in(first)}, а не одна"
        assert reg[key]["label"] in visible(first), \
            f"попросили «{key}», а на экране другая карточка"
        assert reg[key]["what"] in visible(first), \
            f"у просьбы «{key}» нет строки «что это даст»"
        assert reg[key]["size"] in visible(first), \
            f"у просьбы «{key}» не написано, сколько это займёт"
    ok("одна карточка, та самая, со строкой «что это даст» и честной длиной")

    # Ключ, которого нет, и карточка, спрятанная условием: просьбы быть не должно,
    # а не пустой рамки. Догадок мини-апп не строит.
    nope, _ = screens(link(FRESH, obs(OBS), "ask=state_nope"))
    assert cards_in(nope) == 0, "неизвестный ключ просьбы нарисовал карточку"
    assert "Загляни через неделю" in visible(nope), \
        "неизвестный ключ: просьбы нет, а строки «когда заглянуть» тоже нет"
    hidden, _ = screens(link(FRESH, obs(OBS), "ask=state_clinical"))
    assert cards_in(hidden) == 0, \
        "спрятанная условием карточка вылезла как просьба"
    ok("неизвестный и спрятанный ключ просьбы не рисуют карточку")


def check_ask_link_intact() -> None:
    """7. Адреса и ключи не поломаны: просьба открывается с тем же человеком."""
    # ПРАВКА 07.08.2026, спека 011: версия страницы больше не прибита единицей.
    # Пока в адресе жёстко стояло `v=1`, версия из каталога не поднималась
    # никогда, и Телеграм отдавал человеку старый экран из кэша (FR-014). Теперь
    # версию присылает бот, и каталог передаёт её дальше.
    first, _ = screens(link(FRESH, obs(OBS), "ask=state_week", "v=9"))
    reg = {r["key"]: r for r in catalog()["registry"]}
    want = reg["state_week"]["url"] + "?v=9&u=tg_777"
    # В разметке амперсанд экранирован — сравниваем с обратно раскодированной.
    assert want in first.replace("&amp;", "&"), f"адрес просьбы поехал, нет «{want}»"
    ok("страничная просьба открывается своим адресом с человеком в ссылке")

    # Замер, который правда идёт разговором. Шесть прежних диалоговых замеров
    # переехали на страницы (011), и переписку для них открывать больше нечем.
    chat, _ = screens(link(FRESH, obs(OBS), "ask=pair_state"))
    assert "https://t.me/vslukh_shapovalov_bot?start=card_pair_state" in chat, \
        "диалоговая просьба не открывает переписку с ботом"
    ok("диалоговая просьба открывает переписку со старт-параметром")

    meta = bot()["CARD_META"]
    for key in reg:
        assert key in meta, f"ключа «{key}» нет в CARD_META бота"
    ok("все ключи карточек по-прежнему сходятся с реестром бота")


def check_list_by_life_areas() -> None:
    """8. Полный список сгруппирован по областям жизни, а не по срокам."""
    _, rest = screens(link(FRESH))
    text = visible(rest)
    seen = [(text.index(a), a) for a in AREAS if a in text]
    assert len(seen) == len(AREAS), \
        f"в списке нет областей: {sorted(set(AREAS) - {a for _i, a in seen})}"
    assert [a for _i, a in sorted(seen)] == AREAS, \
        f"области идут не в том порядке: {[a for _i, a in sorted(seen)]}"
    ok("семь областей жизни, в порядке спеки")

    for head in BY_PERIOD_HEADS:
        assert head not in text, f"в списке остался раздел по сроку: «{head}»"
    ok("ни одного раздела по сроку")

    c = catalog("""
OUT.areaOrder = AREA_ORDER;
OUT.groups = byArea(buildCards(REGISTRY, {}, "2026-08-07T10:00:00Z", true))
  .map(function (g) { return { area: g.area, n: g.cards.length }; });
""")
    assert c["areaOrder"] == AREAS, f"порядок областей в коде: {c['areaOrder']}"
    assert sorted(c["areaOrder"]) == sorted(c["containers"]), \
        "список областей разошёлся с переносом LIFE_CONTAINERS из бота"
    for g in c["groups"]:
        assert g["n"] > 0, f"область «{g['area']}» попала в список пустой"
    ok("порядок областей задан явно и сходится с переносом из бота")


def check_fresh_visible_not_a_task() -> None:
    """9. Свежие замеры в списке видны, но не подаются как дела (FR-012)."""
    _, rest = screens(link(FRESH))
    text = visible(rest)
    reg = {r["key"]: r for r in catalog()["registry"]}
    # state_day заполнен вчера — карточка обязана остаться видимой.
    assert reg["state_day"]["label"] in text, "свежий замер исчез из списка"
    ok("свежий замер видно в списке")

    for word in NOISE_WORDS:
        assert not has_word(text, word), f"в списке слово-шум: «{word}»"
    ok("в списке нет «пора», «свежее», «не проходил», «неизвестно»")

    assert "последний замер" in text, \
        "про свежий замер не сказано даже когда он был — экран стал беднее"
    ok("у свежего замера видно, когда он был, и это не задача")

    # Диалоговая карточка стоит сразу в нескольких областях жизни. Подробная
    # подсказка на каждой её копии — пять строк, повторённых семь раз: шум.
    whole = visible(catalog_render(link(FRESH, obs(OBS), "ask=pair_state")))
    assert whole.count("Этот замер идёт разговором, не формой") == 1, \
        "подробная подсказка про разговор повторяется — в списке нужна одна строка"
    assert "идёт разговором — нажми, бот начнёт сам" in visible(rest), \
        "в списке не видно, что замер идёт разговором"
    ok("подробная подсказка только у просьбы, в списке одна строка")


def check_noise_gone() -> None:
    """10. Шум убран: чипов-фильтров нет, метки на первой карточке нет."""
    whole = catalog_render(link(FRESH, obs(OBS), "ask=state_week"))
    text = visible(whole)
    for word in NOISE_WORDS + ["пора"]:
        assert not has_word(text, word), f"на странице слово-шум: «{word}»"
    ok("на всей странице нет меток свежести и строки «Пусто»")

    src = inline_script(APP)
    for gone in ("filterHtml", "containerCounts", "emptyContainers",
                 "activeContainer", "needsAttention", "bySection"):
        assert gone not in src, f"осталась логика фильтра или разделов: {gone}"
    ok("логика чипов-фильтров и разделов по срокам удалена")

    first, _ = screens(link(FRESH, obs(OBS), "ask=state_week"))
    reg = {r["key"]: r for r in catalog()["registry"]}
    for area in reg["state_week"]["containers"]:
        assert area not in visible(first), \
            f"на карточке первого экрана осталась метка контейнера: «{area}»"
    assert 'class="tag' not in first, "на первом экране остались кнопки-метки"
    ok("метки контейнера на карточке первого экрана нет")


def check_no_scores_no_scales() -> None:
    """11. Ни балла, ни названия шкалы, ни оценочного слова на экране."""
    whole = catalog_render(link(FRESH, obs(OBS), "ask=state_week"))
    text = visible(whole)
    for bad in ("PHQ", "GAD", "UCLA", "AUDIT", "ASRM", "PSS", "ISI", "BPNSFS",
                "SWLS", "MLQ", "FFMQ", "OLBI", "RSES", "Эдмондсон", "EVS", "KMS",
                "балл", "балла", "баллов", "индекс", "процент"):
        assert not has_word(text, bad), f"на экране название шкалы или балл: «{bad}»"
    ok("ни аббревиатур, ни баллов, ни индексов")

    for bad in ("мало", "плохо", "запустил", "должен", "надо было", "лень",
                "провалил", "забросил"):
        assert not has_word(text.lower(), bad), f"оценочное или винящее слово: «{bad}»"
    ok("ни одного слова, которое добавляет вины")

    assert "undefined" not in text and "NaN" not in text, \
        "на собранном экране есть undefined или NaN"
    ok("экран собирается без дыр")


if __name__ == "__main__":
    raise SystemExit(run([
        check_button_name, check_four_states_pure, check_four_states_on_screen,
        check_observation_above_cards, check_observation_verbatim,
        check_exactly_one_ask, check_ask_link_intact, check_list_by_life_areas,
        check_fresh_visible_not_a_task, check_noise_gone,
        check_no_scores_no_scales,
    ]))
