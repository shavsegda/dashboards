# -*- coding: utf-8 -*-
"""Проверки каталога второй двери «Как я устроен» (`kak-ustroen/app.html`).

Зачем страница. Вторая дверь была кучей кнопок в клавиатуре бота: четырнадцать
надписей подряд, без порядка и без «зачем это мне». Человек нажимал кнопку и
получал список дел вместо ответа. Теперь дверь открывает один экран — как это
уже сделано для подвижного слоя в `kak-ty/app.html`.

Отличие от подвижного слоя, и оно главное: здесь замеры РАЗОВЫЕ или очень
редкие. Личность, нейротип, интересы, ДНК меняются годами или не меняются
вовсе. Поэтому список сгруппирован по смыслу, а не по ритмам.

Что проверяется — исполнением страницы в node с заглушками вместо браузера,
сети и Телеграма, а не поиском слов в исходнике:

  1. состав каталога сверяется с реестрами `bot.py` разбором AST: ни один блок
     не потерян, ни один не придуман, названия и сроки годности взяты буквально;
  2. каждая ссылка ведёт на существующий файл в этом клоне, и адрес совпадает с
     адресом в боте; фраза-подсказка существует в боте буквально;
  3. честная длина сверяется с САМИМИ опросниками: числа в строке длины — это
     настоящее число пунктов на странице, а не прикидка;
  4. ни одной карточки дважды: одна карточка — одна группа, группы полные;
  5. две двери не пересекаются: подвижный слой сюда не пролезает, а «уровень
     мышления», «ощущение времени» и «стресс и риск» здесь есть;
  6. в видимом тексте нет ни латиницы (это и есть аббревиатуры инструментов),
     ни фамилий авторов, ни слов про балл, шкалу и норму;
  7. первый экран отдаёт раньше, чем просит: наблюдение выше просьбы;
  8. без параметров экран говорит честно, а не пусто;
  9. у блоков со сроком годности видно «пора пересдать», у разовых — никогда;
 10. кнопка назад Телеграма закрывает самый внутренний уровень, а не всё сразу;
 11. ни одного счётчика «пройдено N из M» и никакой геймификации.

Плюс мутационная проверка: в страницу вносится одна точная поломка, и нужная
проверка обязана на ней покраснеть. Файл возвращается байт в байт.

Запуск:  python3 checks/kak_ustroen_catalog.py
"""

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
from lib import (BOT, DOM_STUB, NODE_STUBS, RICH_DOM, ROOT, _node, html,
                 inline_script, ok, pure_block, run, visible)

APP = "kak-ustroen/app.html"
KAK_TY = "kak-ty/app.html"          # соседняя дверь, только на чтение
CHECKS = Path(__file__).resolve().parent

# --------------------------------------------------------------------------
# Реестры бота. Только чтение, разбором AST: импортировать бота нельзя —
# он тянет токены и сеть.
# --------------------------------------------------------------------------
# Реестр устойчивого слоя и его соседи. `PASSPORT_BLOCKS_META` — главный: ключ,
# подпись человеку, срок годности в МЕСЯЦАХ. `COVERAGE_MAP` добавляет срок в
# днях и строку «на какой вопрос отвечает». `LEVEL_STEMS` и `BODY_BASE_Q` —
# настоящая длина двух замеров, которые идут разговором.
_WANTED = {"PASSPORT_BLOCKS_META", "COVERAGE_MAP", "LEVEL_STEMS", "BODY_BASE_Q"}

# Адреса страниц блоков. Отдельно: их сборка требует `os.getenv`.
_WANTED_URLS = {
    "PERSONALITY_MINI_APP_URL", "NEUROTYPE_MINI_APP_URL",
    "NERVSYSTEM_MINI_APP_URL", "INTERESTS_MINI_APP_URL",
    "VALUES_MINI_APP_URL", "MOTIVATORS_MINI_APP_URL",
    "ATTACHMENT_MINI_APP_URL", "DECISIONS_MINI_APP_URL",
    "VULNERABILITIES_MINI_APP_URL", "STRESSRISK_MINI_APP_URL",
    "ZTPI_MINI_APP_URL", "MINI_APP_V",
}

# Ключ блока → имя переменной с адресом в боте. Адрес в каталоге обязан
# совпадать с адресом в боте: иначе человек уедет на страницу, которой бот не
# знает, и запись ляжет мимо.
URL_VAR = {
    "personality": "PERSONALITY_MINI_APP_URL",
    "neurotype": "NEUROTYPE_MINI_APP_URL",
    "nervsystem": "NERVSYSTEM_MINI_APP_URL",
    "interests": "INTERESTS_MINI_APP_URL",
    "values": "VALUES_MINI_APP_URL",
    "motivators": "MOTIVATORS_MINI_APP_URL",
    "attachment": "ATTACHMENT_MINI_APP_URL",
    "decisions": "DECISIONS_MINI_APP_URL",
    "vulnerabilities": "VULNERABILITIES_MINI_APP_URL",
    "stressrisk": "STRESSRISK_MINI_APP_URL",
    "ztpi": "ZTPI_MINI_APP_URL",
}


def _bot_pick(names: Set[str], with_os: bool = False) -> Dict:
    """Взять из `bot.py` только названные присваивания верхнего уровня."""
    tree = ast.parse(BOT.read_text(encoding="utf-8"))
    picked, found = [], set()
    for node in tree.body:
        name = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
        if name in names:
            picked.append(node)
            found.add(name)
    missing = names - found
    assert not missing, f"в bot.py не нашёл: {', '.join(sorted(missing))}"
    ns: Dict = {"Dict": Dict, "List": List, "Optional": Optional,
                "Set": Set, "Tuple": Tuple}
    if with_os:
        ns["os"] = os
    exec(compile(ast.Module(body=picked, type_ignores=[]), "<bot>", "exec"), ns)
    return ns


def bot_meta() -> Dict:
    return _bot_pick(_WANTED)


def bot_urls() -> Dict:
    return _bot_pick(_WANTED_URLS, with_os=True)


# --------------------------------------------------------------------------
# Страница: чистая логика, отрисовка, нажатия
# --------------------------------------------------------------------------
def pure(extra_js: str = "") -> Dict:
    """Прогнать чистую логику каталога: без DOM и без сети."""
    js = pure_block(APP) + r"""
const OUT = {
  groups: GROUP_ORDER.map(g => ({ id: g.id, name: g.name, lead: g.lead })),
  registry: REGISTRY.map(r => ({
    key: r.key, label: r.label, what: r.what, size: r.size,
    items: r.items || [], group: r.group,
    shelfMonths: (r.shelfMonths === undefined ? null : r.shelfMonths),
    url: r.url || null, phrase: r.phrase || null
  }))
};
""" + extra_js + r"""
console.log('RESULT<' + JSON.stringify(OUT) + '>RESULT');
"""
    return _node(js)


def registry() -> Dict[str, Dict]:
    return {r["key"]: r for r in pure()["registry"]}


def render(search: str) -> str:
    """Собрать экран целиком, как в телефоне, и отдать готовый HTML."""
    js = (NODE_STUBS.replace("'?u=tg_777'", repr(search).replace('"', "'"))
          + DOM_STUB + inline_script(APP)) + r"""
setTimeout(function () {
  console.log('RESULT<' + JSON.stringify({ html: app.innerHTML }) + '>RESULT');
}, 50);
"""
    return _node(js)["html"]


def seen(search: str) -> str:
    """Текст, который человек реально читает: без тегов и без мнемоник."""
    return visible(render(search))


# Живой DOM ради двух вещей: свёрнутых уровней `<details>` и кнопки назад.
# Разбор текста не видит, что произойдёт по нажатию, а именно там дверь ломалась
# на телефоне: зашёл в список — выйти нечем, кроме закрытия мини-аппа.
LEVELS_DOM = r"""
globalThis.TG_BACK = { shows: 0, hides: 0, bound: 0, visible: false };

function __unesc(s) {
  return String(s).replace(/&quot;/g, '"').replace(/&#39;/g, "'")
                  .replace(/&lt;/g, '<').replace(/&gt;/g, '>')
                  .replace(/&amp;/g, '&');
}

/** Заглушка `<details>`: помнит свои атрибуты, открытость и слушателей. */
function __mkDetails(tag) {
  var attrs = {}, re = /([a-zA-Z_:][-a-zA-Z0-9_:.]*)="([^"]*)"/g, m;
  while ((m = re.exec(tag))) attrs[m[1]] = __unesc(m[2]);
  var hs = [];
  return {
    tag: tag, attrs: attrs, open: false,
    getAttribute: function (n) {
      return Object.prototype.hasOwnProperty.call(attrs, n) ? attrs[n] : null;
    },
    setAttribute: function (n, v) { attrs[n] = String(v); },
    addEventListener: function (t, fn) { hs.push({ t: t, fn: fn }); },
    // Открыть/закрыть как пальцем: меняем `open` и пускаем событие toggle,
    // ровно как это делает браузер.
    tap: function (isOpen) {
      this.open = !!isOpen;
      var self = this;
      hs.forEach(function (h) { if (h.t === 'toggle') h.fn({ target: self }); });
    }
  };
}

globalThis.__APP = {
  _html: '', _cache: null,
  get innerHTML() { return this._html; },
  set innerHTML(v) { this._html = String(v); this._cache = null; },
  _all: function () {
    if (this._cache) return this._cache;
    var out = [], re = /<details\b[^>]*>/g, m;
    while ((m = re.exec(this._html))) out.push(__mkDetails(m[0]));
    this._cache = out;
    return out;
  },
  querySelectorAll: function (sel) {
    if (sel === 'details') return this._all();
    return [];
  },
  querySelector: function (sel) {
    var m = /^#([-a-zA-Z0-9_:.]+)$/.exec(String(sel));
    if (!m) return null;
    var id = m[1], list = this._all();
    for (var i = 0; i < list.length; i++) {
      if (list[i].getAttribute('id') === id) return list[i];
    }
    return null;
  },
  classList: { toggle: function () {}, add: function () {}, remove: function () {} },
  style: {}
};
globalThis.document.getElementById = function () { return globalThis.__APP; };
globalThis.window.scrollTo = function () {};

globalThis.window.Telegram = { WebApp: {
  initData: '', initDataUnsafe: {}, colorScheme: 'light', themeParams: {},
  viewportStableHeight: 700,
  ready: function () {}, expand: function () {},
  isVersionAtLeast: function () { return true; },
  onEvent: function () {},
  setHeaderColor: function () {}, setBackgroundColor: function () {},
  BackButton: {
    show: function () { globalThis.TG_BACK.shows++; globalThis.TG_BACK.visible = true; },
    hide: function () { globalThis.TG_BACK.hides++; globalThis.TG_BACK.visible = false; },
    onClick: function () { globalThis.TG_BACK.bound++; }
  }
}};

/** Уровень по номеру среди `<details>` собранной страницы. */
globalThis.level = function (n) { return globalThis.__APP._all()[n]; };
globalThis.byId = function (id) { return globalThis.__APP.querySelector('#' + id); };
"""


def taps(search: str, js: str) -> Dict:
    """Собрать каталог с живым DOM и понажимать на него."""
    code = (NODE_STUBS.replace("'?u=tg_777'", repr(search).replace('"', "'"))
            + LEVELS_DOM + inline_script(APP)) + r"""
const OUT = {};
setTimeout(function () {
""" + js + r"""
  OUT.back = globalThis.TG_BACK;
  OUT.html = globalThis.__APP.innerHTML;
  console.log('RESULT<' + JSON.stringify(OUT) + '>RESULT');
}, 50);
"""
    return _node(code)


# --------------------------------------------------------------------------
# Настоящая длина опросников. Берётся с самих страниц, а не из головы.
# --------------------------------------------------------------------------
# Девять страниц одного устройства: список тестов → вопросы → результат.
TPL = {
    "neurotype": "neurotype/app11.html",
    "nervsystem": "nervsystem/app2.html",
    "interests": "interests/app.html",
    "values": "values/app8.html",
    "motivators": "motivators/app10.html",
    "attachment": "attachment/app2.html",
    "decisions": "decisions/app2.html",
    "vulnerabilities": "vulnerabilities/app2.html",
    "stressrisk": "stressrisk/app2.html",
}


def tpl_sizes(rel: str) -> List[int]:
    """Число пунктов каждой части страницы-опросника."""
    js = NODE_STUBS + RICH_DOM + inline_script(rel) + r"""
console.log('RESULT<' + JSON.stringify({ n: TESTS.map(t => t.items.length) }) + '>RESULT');
"""
    return _node(js)["n"]


def hexaco_size() -> List[int]:
    """Личность: пункты лежат отдельным файлом, страница берёт их оттуда."""
    js = NODE_STUBS + "globalThis.window = globalThis.window || {};\n" \
        + html("personality-hexaco/items.js") + r"""
console.log('RESULT<' + JSON.stringify({ n: (window.HEXACO_ITEMS || []).length }) + '>RESULT');
"""
    return [_node(js)["n"]]


def ztpi_size() -> List[int]:
    """Ощущение времени: страница поднимает базу, поэтому берём только список."""
    src = inline_script("ztpi/index.html")
    m = re.search(r"const QUESTIONS\s*=", src)
    assert m, "в ztpi/index.html не нашёл список вопросов"
    body = src[m.start():].split("\n];")[0] + "\n];"
    js = body + r"""
console.log('RESULT<' + JSON.stringify({ n: QUESTIONS.length }) + '>RESULT');
"""
    return [_node(js)["n"]]


# --------------------------------------------------------------------------
# Запрещённые слова в видимом тексте
# --------------------------------------------------------------------------
# Латиница на этих экранах — это и есть аббревиатуры инструментов. Человек не
# должен видеть ни одной.
LATIN = re.compile(r"[A-Za-z]{2,}")

# Фамилии авторов и школ: ярлык от фамилии человек принимает как приговор.
AUTHORS = [
    "Фрейли", "Уоллер", "Бреннан", "Пачини", "Эпстайн", "Барон", "Де Дрё",
    "Дрё", "Хиггинс", "Деси", "Райан", "Стреляу", "Шмелёв", "Барон-Коэн",
    "Арон", "Хорн-Остберг", "Карвер", "Вебер", "Карлтон", "Полхус", "Фрост",
    "Хайдт", "Грэм", "Носек", "Шварц", "Голланд", "Лёвинджер", "Кук-Гройтер",
    "Зимбардо", "Кегана", "Киган",
]

# Балл, шкала, норма, сводное число. Ни одного из этих слов человек читать не
# должен: они превращают замер в оценку (конституция, принципы IV и V).
SCORE_WORDS = [
    "балл", "шкала", "шкале", "шкал", "диапазон", "порог", "в норме",
    "выше нормы", "ниже нормы", "суммарн", "индекс", "процент", "%",
]

# Ярлыки о характере — и неприятные, и приятные. Приятный примут не проверяя.
LABEL_WORDS = [
    "ты мало", "ты много", "плохо", "низк", "высок", "средн", "слаб",
    "сильн", "молодец", "отличн", "выражен", "перевес", "ведущ",
    "запустил", "диагноз ", "приговор",
]

# Геймификация и долг. Счётчик заполнения превращает замеры в обязанность.
#
# Граница, уточнённая 10.08.2026 (спека 021). Запрещено то, ради чего запрет и
# вводился: дробь ЦИФРАМИ, прогресс, «осталось пройти», «заполнено на». Факт
# предложением на русском языке — «Пройдено девять блоков из четырнадцати» —
# разрешён решением владельца: это ответ на вопрос «что ты про меня уже знаешь»,
# а не оценка. Проверка на цифры ниже остаётся и продолжает держать границу;
# строку факта на всех значениях гоняет `checks/pervyj_ekran_ustroen.py`.
GAME_WORDS = [
    "пройдено 0 из", "пройдено 1 из", "пройдено 2 из", "пройдено 3 из",
    "прогресс", "осталось пройти", "очк", "достижени", "уровень заполн",
    "заполнено на",
]


# --------------------------------------------------------------------------
# Проверки
# --------------------------------------------------------------------------
def check_sostav_iz_reestra() -> None:
    """1. Состав каталога — из реестров бота, не из головы."""
    b = bot_meta()
    meta = {m["key"]: m for m in b["PASSPORT_BLOCKS_META"]}
    cov = {k: (label, group, days, what)
           for k, label, group, days, what in b["COVERAGE_MAP"]}
    reg = registry()

    for key in meta:
        assert key in reg, f"блок «{key}» есть в реестре бота, а карточки нет"
    ok(f"все {len(meta)} блоков устойчивого слоя на месте")

    for key in reg:
        assert key in meta or key in cov, \
            f"карточка «{key}» придумана: её нет ни в одном реестре бота"
    ok(f"ни одной придуманной карточки, всего {len(reg)}")

    for key, card in reg.items():
        want = meta[key]["label"] if key in meta else cov[key][0]
        assert card["label"] == want, \
            f"название «{key}»: «{card['label']}» против «{want}» в боте"
    ok("названия взяты из реестров бота буквально")

    for key, card in reg.items():
        if key in meta:
            want = meta[key]["shelf"]
        else:
            days = cov[key][2]
            want = None if days is None else round(days / 30.44)
        assert card["shelfMonths"] == want, \
            f"срок «{key}»: {card['shelfMonths']} мес против {want} в боте"
    ok("сроки годности совпадают с реестрами бота")

    for key, card in reg.items():
        assert card["what"], f"у «{key}» нет строки «что это даст»"
        assert card["size"], f"у «{key}» не написано, сколько это займёт"
        assert card["url"] or card["phrase"], f"карточка «{key}» никуда не ведёт"
    ok("у каждой карточки есть «что это даст», длина и дверь")


def check_ssylki_zhivut() -> None:
    """2. Каждая ссылка ведёт на существующий файл и совпадает с адресом бота."""
    u = bot_urls()
    reg = registry()

    for key, var in URL_VAR.items():
        assert key in reg, f"блока «{key}» нет в каталоге"
        assert reg[key]["url"] == u[var], \
            f"адрес «{key}»: {reg[key]['url']} против {u[var]} в боте"
    ok(f"все {len(URL_VAR)} адресов совпадают с адресами в боте")

    for key, card in reg.items():
        if not card["url"]:
            continue
        m = re.match(r"https://shapovalov-aleksey\.ru/(.+)$", card["url"])
        assert m, f"адрес «{key}» не с нашего домена: {card['url']}"
        p = ROOT / m.group(1)
        assert p.exists(), f"«{key}» ведёт на несуществующий путь: {p}"
        if p.is_dir():
            assert (p / "index.html").exists(), \
                f"«{key}» ведёт в папку без index.html: {p}"
    ok("все адреса ведут на существующие страницы")

    bot_text = BOT.read_text(encoding="utf-8")
    phrases = {k: c["phrase"] for k, c in reg.items() if c["phrase"]}
    assert phrases, "ни одной карточки-разговора: три блока идут в чате"
    for key, phrase in phrases.items():
        assert f'"{phrase}"' in bot_text, \
            f"фразы «{phrase}» нет в bot.py — человек отправит её зря"
    ok(f"все {len(phrases)} фраз-подсказок существуют в боте буквально")

    # Два пути к одному замеру на экране — это вопрос «а чем правильно».
    for key, card in reg.items():
        assert not (card["url"] and card["phrase"]), \
            f"у «{key}» и страница, и фраза — два пути к одному замеру"
    ok("у каждой карточки ровно одна дверь")


def check_chestnaya_dlina() -> None:
    """3. Честная длина — из самих опросников, а не прикидка."""
    b = bot_meta()
    reg = registry()

    real: Dict[str, List[int]] = {}
    for key, rel in TPL.items():
        real[key] = tpl_sizes(rel)
    real["personality"] = hexaco_size()
    real["ztpi"] = ztpi_size()
    real["level"] = [len(b["LEVEL_STEMS"])]
    real["body_base"] = [len(b["BODY_BASE_Q"])]

    for key, want in real.items():
        got = reg[key]["items"]
        assert sorted(got) == sorted(want), \
            f"длина «{key}»: в каталоге {sorted(got)}, на самом деле {sorted(want)}"
    ok(f"число пунктов у {len(real)} замеров сходится с самими замерами")

    for key, card in reg.items():
        items = card["items"]
        if not items:
            continue
        size = card["size"]
        for n in (min(items), max(items)):
            assert str(n) in size, \
                f"в длине «{key}» нет числа {n}: «{size}»"
    ok("строка длины называет настоящие числа")

    # У ДНК вопросов нет вовсе, и обещать их нельзя.
    assert reg["dna"]["items"] == [], "у ДНК появились вопросы, которых нет"
    ok("ДНК честно без вопросов")


def check_odna_kartochka_odna_gruppa() -> None:
    """4. Ни одной карточки дважды: одна карточка — одна группа."""
    c = pure(r"""
OUT.grouped = byGroup(buildCards(REGISTRY, {}, NOW_FAKE, false))
  .map(g => ({ id: g.id, keys: g.cards.map(x => x.key) }));
""".replace("NOW_FAKE", '"2026-08-10T00:00:00.000Z"'))

    reg = {r["key"]: r for r in c["registry"]}
    assert len(reg) == len(c["registry"]), "в реестре каталога есть ключ-двойник"
    ok("ни одного ключа-двойника в реестре")

    ids = [g["id"] for g in c["groups"]]
    assert len(ids) == len(set(ids)), "две группы с одним именем"
    for key, card in reg.items():
        assert card["group"] in ids, \
            f"«{key}» лежит в группе «{card['group']}», которой нет в списке"
    ok(f"все карточки разложены по {len(ids)} группам из списка")

    flat = [k for g in c["grouped"] for k in g["keys"]]
    assert len(flat) == len(set(flat)), \
        "карточка встречается в списке дважды: " + \
        ", ".join(sorted({k for k in flat if flat.count(k) > 1}))
    assert set(flat) == set(reg), \
        f"в список попало {len(set(flat))} карточек из {len(reg)}"
    ok("каждая карточка стоит в списке ровно один раз")

    for g in c["grouped"]:
        assert g["keys"], f"группа «{g['id']}» пустая"
    for g in c["groups"]:
        assert g["name"] and g["lead"], f"у группы «{g['id']}» нет имени или строки"
    ok("все группы полные и подписаны")

    # Группы по смыслу, а не по ритму: имя группы не должно быть периодом.
    by_period = {"день", "неделя", "месяц", "квартал", "год", "полгода",
                 "раз в год", "реже"}
    for g in c["groups"]:
        assert g["name"].strip().lower() not in by_period, \
            f"группа названа сроком: «{g['name']}» — здесь замеры разовые"
    ok("ни одна группа не названа сроком")


def check_dve_dveri_ne_peresekayutsya() -> None:
    """5. Две двери не пересекаются: один замер не бывает за двумя."""
    js = pure_block(KAK_TY) + r"""
console.log('RESULT<' + JSON.stringify({
  keys: REGISTRY.map(r => r.key), notHere: NOT_HERE
}) + '>RESULT');
"""
    other = _node(js)
    reg = registry()

    both = sorted(set(reg) & set(other["keys"]))
    assert not both, f"замер стоит за двумя дверями сразу: {both}"
    ok("пересечения с подвижным слоем нет")

    for key in other["notHere"]:
        assert key in reg, \
            f"«{key}» помечен в подвижном слое как «живёт здесь», а карточки нет"
    ok(f"все {len(other['notHere'])} замера структуры добрались до своей двери")


def check_bez_ballov_familij_i_abbreviatur() -> None:
    """6. В видимом тексте нет баллов, аббревиатур и фамилий."""
    text = seen("?u=tg_777&o=" + "%D0%A2%D0%B5%D1%81%D1%82"
                + "&f=personality:2019-01-01,dna:2026-06-01&ask=values")
    low = text.lower()

    latin = sorted(set(LATIN.findall(text)))
    assert not latin, f"в видимом тексте латиница: {latin[:8]}"
    ok("ни одного латинского слова на экране")

    for bad in AUTHORS:
        assert bad.lower() not in low, f"на экране фамилия автора: «{bad}»"
    ok("ни одной фамилии автора")

    for bad in SCORE_WORDS:
        assert bad.lower() not in low, f"на экране слово про балл или шкалу: «{bad}»"
    ok("ни балла, ни шкалы, ни нормы")

    for bad in LABEL_WORDS:
        assert bad.lower() not in low, f"на экране ярлык о характере: «{bad}»"
    ok("ни одного ярлыка о характере")

    assert "undefined" not in text and "NaN" not in text, \
        "в собранной странице есть undefined или NaN — где-то пустое поле"
    ok("пустых полей на странице нет")


def check_snachala_otdaet_potom_prosit() -> None:
    """7. Первый экран отдаёт раньше, чем просит."""
    obs = "Ты уже рассказал про склад и про то, что тебя ведёт"
    q = "?u=tg_777&ask=values&o=" + obs.replace(" ", "%20")
    text = seen(q)

    i_obs = text.find(obs)
    assert i_obs >= 0, "наблюдение от бота не показано вовсе"
    i_ask = text.find("не хватает одного")
    assert i_ask >= 0, "просьбы нет, хотя ключ приехал параметром"
    assert i_obs < i_ask, "просьба стоит выше наблюдения: сначала просим, потом даём"
    ok("наблюдение выше просьбы")

    reg = registry()
    i_all = text.find("Посмотреть всё")
    assert i_all > i_ask, "полный список стоит выше просьбы"
    assert text.count(reg["values"]["label"]) >= 1, "карточки просьбы на экране нет"
    ok("список за ссылкой, ниже просьбы")

    # Просьба ровно одна: два приглашения на первом экране — это уже список дел.
    for head in ("не хватает одного", "Начни с этого"):
        assert text.count(head) <= 1, f"заголовок просьбы повторяется: «{head}»"
    only_obs = seen("?u=tg_777&o=" + obs.replace(" ", "%20"))
    assert "не хватает одного" not in only_obs and "Начни с этого" not in only_obs, \
        "ключа просьбы нет, а просьба на экране есть"
    ok("нет ключа — нет и просьбы")

    first_step = seen("?u=tg_777&ask=values")
    assert "Начни с этого" in first_step, \
        "наблюдения нет, а первый шаг не предложен"
    ok("без наблюдения экран предлагает первый шаг")


def check_bez_parametrov_chestno() -> None:
    """8. Без параметров экран говорит честно, а не пусто."""
    text = seen("?u=tg_777")
    assert "Про то, как ты устроен, я пока ничего не знаю" in text, \
        "экран молчит вместо честной строки про то, что данных нет"
    ok("честная строка на месте")

    assert "Посмотреть всё" in text, "без параметров список недоступен вовсе"
    assert "не хватает одного" not in text, "просьба выдумана без ключа"
    ok("список открыт, просьба не выдумана")

    # Открыт не из бота — экран объясняет, почему он пуст, а не молчит.
    no_user = render("?")
    assert "открывается из бота" in visible(no_user), \
        "без человека экран пустой и ничего не объясняет"
    ok("без человека экран объясняет, откуда его открывать")


def check_srok_godnosti_i_razovye() -> None:
    """9. Со сроком — «пора пересдать». У разовых — никогда."""
    c = pure(r"""
var NOW = "2026-08-10T00:00:00.000Z";
OUT.old   = freshness("2019-01-01", 60, NOW, true);
OUT.fresh = freshness("2026-06-01", 60, NOW, true);
OUT.once  = freshness("2019-01-01", null, NOW, true);
OUT.never = freshness(null, 60, NOW, true);
OUT.due = buildCards(REGISTRY,
  { personality: "2019-01-01", dna: "2019-01-01", body_base: "2019-01-01",
    values: "2026-07-01" }, NOW, true)
  .filter(x => x.state === "due").map(x => x.key);
""")
    assert c["old"]["state"] == "due", "срок вышел, а замер считается свежим"
    assert c["fresh"]["state"] == "fresh", "свежий замер помечен просроченным"
    assert c["once"]["state"] == "fresh", \
        "разовый замер через семь лет просит пересдачи"
    assert c["never"]["state"] == "never", "непройденный замер не отличается от пройденного"
    ok("свежесть считается как в боте: месяцы, граница «месяцев >= срока»")

    assert "dna" not in c["due"] and "body_base" not in c["due"], \
        f"разовый замер попал в «пора пересдать»: {c['due']}"
    assert "personality" in c["due"], "просроченный замер не помечен"
    assert "values" not in c["due"], "свежий замер помечен просроченным"
    ok("разовые никогда не «пора», у остальных срок работает")

    text = seen("?u=tg_777&f=personality:2019-01-01,dna:2019-01-01,"
                "body_base:2019-01-01,values:2026-07-01")
    assert text.count("пора пересдать") == len(c["due"]), \
        f"на экране «пора пересдать» {text.count('пора пересдать')} раз, " \
        f"а просрочено {len(c['due'])}"
    ok("на экране «пора пересдать» ровно у просроченных")

    assert "пройдено" in text.lower(), \
        "экран не говорит, что замер пройден и когда"
    never = seen("?u=tg_777")
    assert "пора пересдать" not in never, \
        "непройденные замеры уже требуют пересдачи"
    ok("непройденное ни о чём не упрекает")


def check_knopka_nazad() -> None:
    """10. Кнопка назад закрывает самый внутренний уровень, а не всё сразу."""
    r = taps("?u=tg_777", r"""
  OUT.bound = globalThis.TG_BACK.bound;
  OUT.start = globalThis.TG_BACK.visible;
  var all = globalThis.byId('lvl-all');
  OUT.hasAll = !!all;
  all.tap(true);
  OUT.afterAll = globalThis.TG_BACK.visible;
  var groups = globalThis.__APP.querySelectorAll('details').filter(function (d) {
    return String(d.getAttribute('id') || '').indexOf('lvl-g-') === 0;
  });
  OUT.groups = groups.length;
  groups[0].tap(true);
  OUT.afterGroup = globalThis.TG_BACK.visible;
  onBack();
  OUT.groupOpenAfterBack = groups[0].open;
  OUT.allOpenAfterBack = all.open;
  OUT.afterBack1 = globalThis.TG_BACK.visible;
  onBack();
  OUT.allOpenAfterBack2 = all.open;
  OUT.afterBack2 = globalThis.TG_BACK.visible;
""")
    assert r["bound"] >= 1, "обработчик кнопки назад не привязан ни разу"
    assert r["bound"] == 1, \
        f"обработчик кнопки назад привязан {r['bound']} раз — назад пойдёт на два шага"
    ok("обработчик кнопки назад привязан ровно один раз")

    assert r["hasAll"], "на странице нет уровня со списком"
    assert r["groups"] >= 2, f"групп-уровней всего {r['groups']}"
    assert r["start"] is False, "кнопка назад видна на первом экране, откуда некуда"
    assert r["afterAll"] is True, "список открыт, а кнопки назад нет"
    assert r["afterGroup"] is True, "группа открыта, а кнопки назад нет"
    ok("кнопка появляется там, откуда есть куда вернуться")

    assert r["groupOpenAfterBack"] is False, "назад не закрыл открытую группу"
    assert r["allOpenAfterBack"] is True, \
        "назад закрыл всё сразу: человек хотел выйти из группы, а не потерять список"
    assert r["afterBack1"] is True, "кнопка назад исчезла, хотя список ещё открыт"
    ok("назад закрывает самый внутренний уровень")

    assert r["allOpenAfterBack2"] is False, "второй назад не закрыл список"
    assert r["afterBack2"] is False, "кнопка назад осталась на первом экране"
    ok("второй назад возвращает на первый экран и убирает кнопку")


def check_bez_geymifikacii() -> None:
    """11. Ни счётчиков «пройдено N из M», ни баллов прогресса."""
    text = seen("?u=tg_777&f=personality:2026-06-01,values:2026-07-01")
    low = text.lower()
    for bad in GAME_WORDS:
        assert bad.lower() not in low, f"на экране геймификация: «{bad}»"
    ok("ни счётчика, ни прогресса, ни очков")

    assert not re.search(r"\d+\s*(из|/)\s*\d+", text), \
        "на экране счётчик вида «N из M»"
    ok("счётчика «N из M» нет")

    assert "Одного числа на всё нет" in text, \
        "пропала оговорка про то, что сводного числа не будет"
    ok("оговорка про отсутствие сводного числа на месте")


# --------------------------------------------------------------------------
# Мутации: ломаем страницу и смотрим, покраснеет ли нужная проверка
# --------------------------------------------------------------------------
# (что ломаем · было · стало · какая проверка обязана покраснеть)
MUTATIONS: List[Tuple[str, str, str, str]] = [
    ("блок выпал из каталога",
     'key: "interests", label: "Интересы"',
     'key: "interests_x", label: "Интересы"',
     "check_sostav_iz_reestra"),

    ("название разошлось с реестром бота",
     'key: "values", label: "Ценности"',
     'key: "values", label: "Ценности и мораль"',
     "check_sostav_iz_reestra"),

    ("срок годности разошёлся с ботом",
     'key: "attachment", label: "Привязанность", group: "davlenie", shelfMonths: 24',
     'key: "attachment", label: "Привязанность", group: "davlenie", shelfMonths: 12',
     "check_sostav_iz_reestra"),

    ("ссылка ведёт на несуществующую страницу",
     "https://shapovalov-aleksey.ru/nervsystem/app2.html",
     "https://shapovalov-aleksey.ru/nervsystem/app9.html",
     "check_ssylki_zhivut"),

    ("длина обещает не те вопросы",
     'items: [134], size: "134 вопроса"',
     'items: [134], size: "40 вопросов"',
     "check_chestnaya_dlina"),

    ("карточка попала во все группы сразу",
     "return c.group === g.id;",
     "return true;",
     "check_odna_kartochka_odna_gruppa"),

    ("замер стоит за двумя дверями",
     'key: "ztpi", label: "Ощущение времени"',
     'key: "state_day", label: "Ощущение времени"',
     "check_dve_dveri_ne_peresekayutsya"),

    ("на экран вернулось название шкалы",
     'what: "как ты в близких отношениях: тянешься или закрываешься"',
     'what: "близость и дистанция по шкале ECR-R"',
     "check_bez_ballov_familij_i_abbreviatur"),

    ("сначала просим, потом отдаём",
     "return give + askBlock;",
     "return askBlock + give;",
     "check_snachala_otdaet_potom_prosit"),

    ("без данных экран молчит вместо честной строки",
     "Про то, как ты устроен, я пока ничего не знаю.",
     "&nbsp;",
     "check_bez_parametrov_chestno"),

    ("разовый замер просит пересдачи",
     "if (shelfMonths === null || shelfMonths === undefined) {\n    return { state: \"fresh\"",
     "if (false) {\n    return { state: \"fresh\"",
     "check_srok_godnosti_i_razovye"),

    ("кнопка назад не показывается никогда",
     "if (backVisible(NAV)) tg.BackButton.show();",
     "if (false) tg.BackButton.show();",
     "check_knopka_nazad"),

    ("назад закрывает всё сразу",
     "NAV = navPop(NAV);",
     "NAV = [];",
     "check_knopka_nazad"),

    ("на экране появился счётчик заполнения",
     '<p class="all-lead">',
     '<p class="all-lead">Пройдено 3 из 14. ',
     "check_bez_geymifikacii"),
]

# У каждого требования задания — своя мутация. Без этого список мутаций
# незаметно съезжает в «поломали то, что легче ломается».
MUST_MUTATE = {
    "check_sostav_iz_reestra",
    "check_ssylki_zhivut",
    "check_chestnaya_dlina",
    "check_odna_kartochka_odna_gruppa",
    "check_dve_dveri_ne_peresekayutsya",
    "check_bez_ballov_familij_i_abbreviatur",
    "check_snachala_otdaet_potom_prosit",
    "check_bez_parametrov_chestno",
    "check_srok_godnosti_i_razovye",
    "check_knopka_nazad",
    "check_bez_geymifikacii",
}


def _one_check(name: str) -> int:
    """Прогнать одну проверку отдельным процессом. Вернуть её код выхода."""
    code = (
        "import lib_path\n"
        "from lib import run\n"
        "import kak_ustroen_catalog as C\n"
        "raise SystemExit(run([getattr(C, %r)]))\n" % name
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(CHECKS) + os.pathsep + env.get("PYTHONPATH", "")
    r = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT),
                       capture_output=True, text=True, env=env, timeout=1800)
    return r.returncode


def check_u_kazhdogo_trebovaniya_est_mutaciya() -> None:
    """12. У каждого требования задания есть поломка."""
    used = {m[3] for m in MUTATIONS}
    missing = MUST_MUTATE - used
    assert not missing, "без мутации остались: " + ", ".join(sorted(missing))
    ok(f"{len(MUST_MUTATE)} требований закрыты мутациями")


def check_polomki_lovyatsya() -> None:
    """13. Каждая поломка ловится, и страница возвращается байт в байт."""
    path = ROOT / APP
    before = path.read_text(encoding="utf-8")
    digest = hashlib.sha256(before.encode()).digest()

    caught, misses = 0, []
    for what, old, new, check in MUTATIONS:
        n = before.count(old)
        assert n == 1, f"«{what}»: место мутации встречается {n} раз, а не один"
        try:
            path.write_text(before.replace(old, new, 1), encoding="utf-8")
            if _one_check(check) == 0:
                misses.append(f"{what} → {check} осталась зелёной")
            else:
                caught += 1
                print(f"  ловит  {what}  →  {check}")
        finally:
            path.write_text(before, encoding="utf-8")

    got = path.read_text(encoding="utf-8")
    assert hashlib.sha256(got.encode()).digest() == digest, \
        f"{APP} не вернулся к исходному состоянию"
    assert not misses, "не поймано: " + "; ".join(misses)
    ok(f"все {caught} поломок из {len(MUTATIONS)} пойманы, страница на месте")


CHECKS_ALL = [
    check_sostav_iz_reestra,
    check_ssylki_zhivut,
    check_chestnaya_dlina,
    check_odna_kartochka_odna_gruppa,
    check_dve_dveri_ne_peresekayutsya,
    check_bez_ballov_familij_i_abbreviatur,
    check_snachala_otdaet_potom_prosit,
    check_bez_parametrov_chestno,
    check_srok_godnosti_i_razovye,
    check_knopka_nazad,
    check_bez_geymifikacii,
]

if __name__ == "__main__":
    only = sys.argv[1:] and sys.argv[1] == "--bez-mutacij"
    fns = CHECKS_ALL if only else CHECKS_ALL + [
        check_u_kazhdogo_trebovaniya_est_mutaciya,
        check_polomki_lovyatsya,
    ]
    raise SystemExit(run(fns))
