# -*- coding: utf-8 -*-
"""Проверки темы Телеграма, безопасных зон и стабильной высоты (спека 013).

Дефект. Единственный пункт `мини-аппы-правила.md`, красный сразу на всех
страницах-замерах: цвета были прибиты гвоздями (paper/graphite/terracotta), тема
клиента не читалась и `themeChanged` никто не слушал. У человека с тёмной темой
страница светила белым листом. Отступы на девяти страницах шли обычными
пикселями — на телефоне с вырезом верх уезжал под вырез, низ под панель. Высота
считалась от `100vh`, а не от стабильной высоты окна: во время жестов низ
страницы прыгал под пальцем.

Как устроено решение — и что из этого проверяется здесь:

  · **Цвет** — в CSS каждый цвет объявлен как `var(--tg-theme-*, запасной)`.
    Запасное значение — палитра Алексея, поэтому без Телеграма (браузер,
    проверки) страница выглядит как раньше. Полупрозрачные оттенки собираются из
    триплетов `--ink-rgb` и `--alert-rgb`: добавить альфу к чужому цвету
    средствами CSS нельзя, поэтому триплеты считает скрипт.
  · **Перерисовка** — скрипт слушает `themeChanged` и пересчитывает переменные.
    Проверяется поведением: тема переключается прямо в прогоне, и переменные
    обязаны поменяться.
  · **Читаемость акцента** — терракота остаётся своим цветом (в теме Телеграма
    аналога нет), но на тёмном фоне обычная терракота не читается, поэтому для
    тёмной темы задан свой более светлый оттенок. Контраст считается формулой
    WCAG, а не на глаз.
  · **Безопасные зоны** — отступы через `var(--tg-safe-area-inset-*)` и
    `var(--tg-content-safe-area-inset-*)`.
  · **Высота** — `viewportStableHeight`, а не `viewportHeight`.
  · **Данные не тронуты** — отдельный жёсткий блок: блок базы, подпись
    инструмента, число пунктов и все ключи записи сверяются со снимком, снятым
    ДО правки оформления. Работа была только про вид; расхождение здесь значит,
    что оформление залезло в данные.

Заглушка базы для шести замеров-разговоров берётся из `zamery_v_miniappe.py`:
второй такой же копией стало бы легко разойтись, а расхождение заглушек — это
проверки, которые проверяют разное и обе зелёные.

Что проверками НЕ берётся и смотрится глазами на телефоне: как настоящий клиент
Телеграма отдаёт свою тему, не режет ли глаз конкретный оттенок и не поехала ли
вёрстка на телефоне с вырезом. Записано честно.

Запуск:  python3 checks/tema_i_bezopasnye_zony.py
"""

import json
import re
from typing import Dict, List, Tuple

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
import zamery_v_miniappe as zm
from lib import _node, form_app, html, inline_script, ok, pure_block, run

# --------------------------------------------------------------------------
# Пятнадцать страниц-замеров
# --------------------------------------------------------------------------
DAY = "state-day/app.html"

# Страницы-опросники со сборкой через TESTS/SCORERS.
FORMS: Tuple[str, ...] = (
    "state-week/app4.html",
    "state-month/app3.html",
    "state-quarter/app3.html",
    "state-clinical/app.html",
    "state-year/app.html",
    "state-team/app.html",
    "state-needs/app.html",
    "selfhood/app.html",
)

# Шесть замеров-разговоров: их запись проверяется прогоном страницы целиком.
NEW: Tuple[str, ...] = tuple(zm.PAGES[b] for b in zm.PAGES)

PAGES: Tuple[str, ...] = (DAY,) + FORMS + NEW

# --------------------------------------------------------------------------
# Две палитры. Светлая — как было, тёмная — запасная под тёмную тему.
# Одни и те же значения обязаны стоять и в CSS, и в скрипте страницы.
# --------------------------------------------------------------------------
LIGHT = {"paper": "#F4F2EC", "stone": "#E8E5DC", "ink": "#1A1A1A",
         "ink_rgb": "26,26,26", "alert": "#B91C1C", "alert_rgb": "185,28,28",
         "accent": "#B85C38", "accent_rgb": "184,92,56"}
DARK = {"paper": "#17171A", "stone": "#202024", "ink": "#F0EEE8",
        "ink_rgb": "240,238,232", "alert": "#F27A7A", "alert_rgb": "242,122,122",
        "accent": "#E08A63", "accent_rgb": "224,138,99"}

# Цвет → переменная темы Телеграма. Своё значение остаётся запасным.
THEME_VARS: Dict[str, Tuple[str, str, str]] = {
    "--paper": ("--tg-theme-bg_color", LIGHT["paper"], DARK["paper"]),
    "--stone": ("--tg-theme-secondary_bg_color", LIGHT["stone"], DARK["stone"]),
    "--graphite": ("--tg-theme-text_color", LIGHT["ink"], DARK["ink"]),
    "--alert": ("--tg-theme-destructive_text_color", LIGHT["alert"], DARK["alert"]),
}

# Полупрозрачные оттенки: та же альфа, что была, но триплет теперь общий.
ALPHA: Dict[str, Tuple[str, str]] = {
    "--graphite-90": ("--ink-rgb", "0.9"),
    "--graphite-75": ("--ink-rgb", "0.75"),
    "--graphite-65": ("--ink-rgb", "0.65"),
    "--graphite-50": ("--ink-rgb", "0.5"),
    "--graphite-30": ("--ink-rgb", "0.3"),
    "--graphite-15": ("--ink-rgb", "0.15"),
    "--graphite-08": ("--ink-rgb", "0.08"),
    "--terracotta-tint": ("--accent-rgb", "0.08"),
    "--alert-tint": ("--alert-rgb", "0.06"),
}

# Переменные, которые считает скрипт: цветной литерал у них законный.
DERIVED = {"--ink-rgb", "--accent-rgb", "--alert-rgb", "--terracotta"}


# ==========================================================================
# Чтение страницы
# ==========================================================================
def style(rel: str) -> str:
    """Таблица стилей без пояснений: слово в комментарии — не правило."""
    src = html(rel)
    m = re.search(r"<style>(.*?)</style>", src, re.S)
    assert m, f"в {rel} нет таблицы стилей"
    return re.sub(r"/\*.*?\*/", " ", m.group(1), flags=re.S)


def code(rel: str) -> str:
    """Скрипт страницы без пояснений."""
    src = re.sub(r"/\*.*?\*/", " ", inline_script(rel), flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", " ", src)


def decls(css: str) -> List[Tuple[str, str]]:
    """Все объявления «имя: значение» таблицы стилей, по порядку."""
    out = []
    for m in re.finditer(r"([-a-zA-Z][-a-zA-Z0-9_]*)\s*:\s*([^;{}]+)[;}]", css):
        out.append((m.group(1), m.group(2).strip()))
    return out


def rule(css: str, selector: str) -> str:
    """Тело правила по селектору. Нужен блок, а не поиск по всему файлу.

    Селектор ищется с начала строки: иначе «body» находится внутри
    «html, body», и проверка смотрит не то правило.
    """
    m = re.search(r"(?m)^\s*" + re.escape(selector) + r"\s*\{(.*?)\}", css, re.S)
    assert m, f"нет правила «{selector}»"
    return m.group(1)


def root_vars(rel: str, dark: bool = False) -> Dict[str, str]:
    """Переменные из `:root`. `dark=True` — из блока про тёмную систему."""
    css = style(rel)
    if dark:
        m = re.search(r"@media\s*\(prefers-color-scheme:\s*dark\)\s*\{(.*?\})\s*\}",
                      css, re.S)
        assert m, f"в {rel} нет блока про тёмную тему системы"
        css = m.group(1)
    return dict(decls(rule(css, ":root")))


# ==========================================================================
# Прогон страницы с заглушкой темы
# ==========================================================================
START = re.compile(r"(?m)^//\s*[-=]{2,}\s*Старт")

STUBS = r"""
globalThis.window = { location: { search: '?u=tg_777' }, scrollTo: function () {} };
globalThis.history = { length: 2, back: function () {} };
globalThis.localStorage = {
  _s: {},
  getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
  setItem(k, v) { this._s[k] = String(v); },
  removeItem(k) { delete this._s[k]; }
};
// Что страница записала в переменные `:root`. Ровно это видит человек глазами.
globalThis.VARS = {};
function __el() {
  return { style: {}, innerHTML: '', textContent: '', value: '', disabled: false,
           addEventListener() {}, removeEventListener() {},
           setAttribute() {}, getAttribute() { return null; },
           querySelectorAll() { return []; },
           classList: { toggle() {}, add() {}, remove() {} } };
}
globalThis.document = {
  documentElement: { style: {
    setProperty: function (k, v) { globalThis.VARS[k] = String(v); },
    getPropertyValue: function (k) { return globalThis.VARS[k] || ''; },
    removeProperty: function (k) { delete globalThis.VARS[k]; }
  } },
  getElementById: __el, createElement: __el,
  addEventListener: function () {},
  body: { appendChild() {}, removeChild() {} },
  execCommand() { return true; }
};
globalThis.fetch = async function () {
  return { ok: true, status: 201, json: async function () { return []; } };
};
globalThis.HANDLERS = {};
globalThis.TGCALLS = { header: [], background: [] };
globalThis.THEME = %(theme)s;
globalThis.SCHEME = %(scheme)s;
"""

TG = r"""
globalThis.window.Telegram = { WebApp: {
  initData: '', initDataUnsafe: {},
  version: '8.0',
  // Тема и схема читаются каждый раз заново: клиент их меняет на ходу.
  get themeParams() { return globalThis.THEME; },
  get colorScheme() { return globalThis.SCHEME; },
  viewportStableHeight: 612,
  viewportHeight: 700,
  ready: function () {}, expand: function () {},
  isVersionAtLeast: function () { return true; },
  onEvent: function (n, f) { (globalThis.HANDLERS[n] = globalThis.HANDLERS[n] || []).push(f); },
  setHeaderColor: function (c) { globalThis.TGCALLS.header.push(String(c)); },
  setBackgroundColor: function (c) { globalThis.TGCALLS.background.push(String(c)); },
  enableClosingConfirmation: function () {}, disableClosingConfirmation: function () {},
  BackButton: { onClick: function () {}, show: function () {}, hide: function () {} }
}};
"""

TAIL = r"""
const OUT = { first: Object.assign({}, globalThis.VARS),
              events: Object.keys(globalThis.HANDLERS),
              calls: globalThis.TGCALLS };
// Человек переключил тему в клиенте. Страница обязана переключиться за ним.
globalThis.THEME = %(theme2)s;
globalThis.SCHEME = %(scheme2)s;
(globalThis.HANDLERS['themeChanged'] || []).forEach(function (f) { f(); });
OUT.after = Object.assign({}, globalThis.VARS);
console.log('RESULT<' + JSON.stringify(OUT) + '>RESULT');
"""

DARK_THEME = {"bg_color": "#17212B", "secondary_bg_color": "#232E3C",
              "text_color": "#FFFFFF", "hint_color": "#708499",
              "destructive_text_color": "#EC3942"}
LIGHT_THEME = {"bg_color": "#FFFFFF", "secondary_bg_color": "#F0F0F0",
               "text_color": "#000000", "hint_color": "#999999",
               "destructive_text_color": "#CC2929"}


def before_start(rel: str) -> str:
    """Скрипт до метки старта: объявления и настройка, без отрисовки."""
    s = inline_script(rel)
    m = START.search(s)
    assert m, f"в {rel} нет метки старта — не знаю, где кончается настройка"
    return s[:m.start()]


def theme_run(rel: str, telegram: bool = True) -> Dict:
    """Открыть страницу в тёмной теме, потом переключить клиент на светлую."""
    js = (STUBS % {"theme": json.dumps(DARK_THEME), "scheme": '"dark"'}
          + (TG if telegram else "")
          + before_start(rel)
          + TAIL % {"theme2": json.dumps(LIGHT_THEME), "scheme2": '"light"'})
    return _node(js)


RUNS: Dict[str, Dict] = {}


def run_of(rel: str) -> Dict:
    """Прогон кешируется: страниц пятнадцать, node запускать по разу."""
    if rel not in RUNS:
        RUNS[rel] = theme_run(rel)
    return RUNS[rel]


# ==========================================================================
# Контраст: формула WCAG, а не «на глаз»
# ==========================================================================
def rgb(hex_color: str) -> Tuple[float, float, float]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def luminance(hex_color: str) -> float:
    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb(hex_color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# ==========================================================================
# 1. Цвета из темы, палитра Алексея — запасная
# ==========================================================================
def check_theme_vars_with_fallback() -> None:
    """1. В светлой теме — своя палитра, в тёмной — тема Телеграма.

    Правка от 07.08.2026, решение Алексея. Изначально проверка требовала цвет из
    темы Телеграма с запасом на свою палитру — то есть в светлой теме страница
    брала белый фон клиента вместо тёплого #F4F2EC. Алексей посмотрел и сказал:
    «мне жалко оттенок». Бумажный тон — часть его дизайн-системы, узнаваемая
    вещь, и терять её ради буквы правила незачем.

    Что осталось от правила: **тёмная тема обязана работать**. Светлый лист в
    тёмном окне — настоящая поломка, а тёплый фон вместо белого — нет. Поэтому в
    тёмном блоке цвета по-прежнему берутся из темы с запасом.
    """
    # Своими остаются три базовых: фон, второй фон и текст — из них и состоит
    # узнаваемый бумажный вид. Цвет тревоги (`--alert`) по-прежнему берём из
    # темы: у клиента он свой не ради красоты, а чтобы «опасное» выглядело
    # опасным привычным для человека образом.
    own = ("--paper", "--stone", "--graphite")
    bad = []
    for rel in PAGES:
        got = root_vars(rel)
        for name, (tg_var, fallback, _dark) in THEME_VARS.items():
            value = got.get(name, "").replace(" ", "")
            if name in own:
                if value != fallback.replace(" ", ""):
                    bad.append(f"{rel}: {name} = {got.get(name)!r}, нужно {fallback!r}")
            else:
                want = f"var({tg_var}, {fallback})".replace(" ", "")
                if value != want:
                    bad.append(f"{rel}: {name} = {got.get(name)!r}, нужно из темы")
    assert not bad, "; ".join(bad[:6])
    ok(f"в светлой теме свой бумажный оттенок, тревога из темы ({len(PAGES)} страниц)")


def check_alpha_shades_follow_ink() -> None:
    """2. Полупрозрачные оттенки собираются из триплета, а не из своего цвета."""
    bad = []
    for rel in PAGES:
        got = root_vars(rel)
        for name, (src, alpha) in ALPHA.items():
            if name not in got:
                continue                       # такого оттенка на странице нет
            want = f"rgba(var({src}),{alpha})"
            if got[name].replace(" ", "") != want:
                bad.append(f"{rel}: {name} = {got[name]!r}, нужно {want!r}")
    assert not bad, "; ".join(bad[:6])
    ok("полупрозрачные оттенки идут за цветом текста темы")


def check_alpha_values_unchanged() -> None:
    """3. Альфы не поехали: вид страницы в светлой теме остаётся прежним."""
    bad = []
    for rel in PAGES:
        got = root_vars(rel)
        for name, (_src, alpha) in ALPHA.items():
            if name in got and alpha not in got[name]:
                bad.append(f"{rel}: {name} потерял альфу {alpha}")
    assert not bad, "; ".join(bad[:6])
    ok("прозрачность оттенков та же, что была")


def check_no_stray_color_literals() -> None:
    """4. Цвет задаётся только в корне, а не рассыпан по правилам.

    Правка от 07.08.2026 вместе с проверкой №1. Прежняя версия запрещала любой
    свой цвет в стилях — под решение Алексея («жалко оттенок») три базовых цвета
    в светлом блоке снова свои. Смысл проверки при этом не пропал, он сместился:
    цвет живёт **в одном месте**, в переменных корня. Тогда тёмная тема
    переключает всё разом, и ни одно правило не держит свой цвет мимо неё.
    """
    lit = re.compile(r"#[0-9A-Fa-f]{3,8}\b|rgba?\(\s*\d")
    base = set(THEME_VARS)                     # три базовых цвета — свои, решение
    bad = []
    for rel in PAGES:
        for name, value in decls(style(rel)):
            if name in DERIVED or name in base:
                continue                       # считает скрипт либо базовый цвет
            clean = re.sub(r"var\(\s*--tg-[^,()]+,[^()]*\)", " ", value)
            clean = re.sub(r"rgba?\(\s*var\([^)]*\)[^)]*\)", " ", clean)
            if lit.search(clean):
                bad.append(f"{rel}: {name}: {value}")
    assert not bad, "; ".join(bad[:6])
    ok("цвет живёт только в переменных корня, по правилам не рассыпан")


def check_dark_palette_block() -> None:
    """5. Телеграма нет, а система тёмная — страница тёмная целиком."""
    bad = []
    for rel in PAGES:
        got = root_vars(rel, dark=True)
        for name, (tg_var, _light, dark) in THEME_VARS.items():
            want = f"var({tg_var}, {dark})"
            if got.get(name, "").replace(" ", "") != want.replace(" ", ""):
                bad.append(f"{rel}: тёмная тема, {name} = {got.get(name)!r}")
        if got.get("--ink-rgb", "").replace(" ", "") != DARK["ink_rgb"]:
            bad.append(f"{rel}: тёмная тема, чернила {got.get('--ink-rgb')!r}")
        if got.get("--terracotta", "").strip() != DARK["accent"]:
            bad.append(f"{rel}: тёмная тема, акцент {got.get('--terracotta')!r}")
    assert not bad, "; ".join(bad[:6])
    ok("для тёмной темы системы задана своя полная палитра")


def check_dark_accent_readable() -> None:
    """6. Акцент в тёмной теме читается не хуже, чем в светлой."""
    было = contrast(LIGHT["accent"], LIGHT["paper"])
    стало = contrast(DARK["accent"], DARK["paper"])
    assert стало >= 3.0, f"тёмный акцент почти не виден: контраст {стало:.2f}"
    assert было >= 3.0, f"светлый акцент почти не виден: контраст {было:.2f}"
    assert стало >= было, f"в тёмной теме акцент хуже: {стало:.2f} против {было:.2f}"
    # Акцент бывает фоном кнопки, а текст на нём — цвета страницы.
    on_btn = contrast(DARK["accent"], DARK["paper"])
    assert on_btn >= 3.0, f"текст на кнопке в тёмной теме не читается: {on_btn:.2f}"
    ok(f"акцент читается в обеих темах: светлая {было:.2f}, тёмная {стало:.2f}")


def check_palette_same_in_css_and_script() -> None:
    """7. Запасная палитра в стилях и в скрипте одна и та же."""
    bad = []
    for rel in PAGES:
        src = code(rel)
        for pal in (LIGHT, DARK):
            for key in ("paper", "stone", "ink", "ink_rgb", "alert", "alert_rgb",
                        "accent", "accent_rgb"):
                if pal[key] not in src:
                    bad.append(f"{rel}: в скрипте нет {pal[key]}")
    assert not bad, "; ".join(bad[:6])
    ok("палитра в стилях и в скрипте совпадает")


# ==========================================================================
# 2. themeChanged: страница переключается за человеком
# ==========================================================================
def check_theme_changed_listened() -> None:
    """8. Событие themeChanged слушается на всех страницах."""
    bad = [rel for rel in PAGES
           if not re.search(r'onEvent\(\s*["\']themeChanged["\']', code(rel))]
    assert not bad, f"themeChanged не слушается: {bad}"
    ok(f"themeChanged слушается на всех страницах ({len(PAGES)})")


def check_theme_paints_on_open() -> None:
    """9. При открытии переменные ставятся из темы клиента, а не из своих."""
    bad = []
    for rel in PAGES:
        v = run_of(rel)["first"]
        if v.get("--graphite") != DARK_THEME["text_color"]:
            bad.append(f"{rel}: цвет текста {v.get('--graphite')!r}")
        if v.get("--paper") != DARK_THEME["bg_color"]:
            bad.append(f"{rel}: фон {v.get('--paper')!r}")
        if v.get("--ink-rgb") != "255,255,255":
            bad.append(f"{rel}: чернила {v.get('--ink-rgb')!r}")
    assert not bad, "; ".join(bad[:6])
    ok("при открытии страница берёт цвета у клиента")


def check_theme_repaints_on_change() -> None:
    """10. Человек переключил тему — переменные пересчитались."""
    bad = []
    for rel in PAGES:
        r = run_of(rel)
        before, after = r["first"], r["after"]
        if after.get("--paper") != LIGHT_THEME["bg_color"]:
            bad.append(f"{rel}: фон не переключился ({after.get('--paper')!r})")
        if after.get("--ink-rgb") != "0,0,0":
            bad.append(f"{rel}: чернила не переключились ({after.get('--ink-rgb')!r})")
        if before.get("--ink-rgb") == after.get("--ink-rgb"):
            bad.append(f"{rel}: переменные не меняются вообще")
    assert not bad, "; ".join(bad[:6])
    ok("переключение темы перерисовывает переменные")


def check_accent_switches_with_scheme() -> None:
    """11. В тёмной теме акцент светлее, в светлой — обычный."""
    bad = []
    for rel in PAGES:
        r = run_of(rel)
        if r["first"].get("--terracotta") != DARK["accent"]:
            bad.append(f"{rel}: в тёмной теме акцент {r['first'].get('--terracotta')!r}")
        if r["after"].get("--terracotta") != LIGHT["accent"]:
            bad.append(f"{rel}: в светлой теме акцент {r['after'].get('--terracotta')!r}")
        if r["first"].get("--accent-rgb") != DARK["accent_rgb"]:
            bad.append(f"{rel}: тёмный триплет акцента {r['first'].get('--accent-rgb')!r}")
    assert not bad, "; ".join(bad[:6])
    ok("акцент меняет оттенок вместе с темой")


def check_header_follows_theme() -> None:
    """12. Шапка и фон окна того же цвета, что страница: без чужого канта."""
    bad = []
    for rel in PAGES:
        calls = run_of(rel)["calls"]
        if not calls["header"]:
            bad.append(f"{rel}: цвет шапки не задан")
        if not calls["background"]:
            bad.append(f"{rel}: цвет фона окна не задан")
    assert not bad, "; ".join(bad[:6])
    ok("шапка и фон окна идут за темой")


def check_no_telegram_no_paint() -> None:
    """13. Без Телеграма страница не падает и остаётся на своей палитре."""
    bad = []
    for rel in PAGES:
        v = theme_run(rel, telegram=False)["first"]
        if v:
            bad.append(f"{rel}: без Телеграма переопределил {sorted(v)}")
    assert not bad, "; ".join(bad[:6])
    ok("без Телеграма страница живая и цвета свои")


# ==========================================================================
# 3. Безопасные зоны
# ==========================================================================
def check_safe_area_top() -> None:
    """14. Верх — через содержательную безопасную зону: не под вырез."""
    bad = [rel for rel in PAGES
           if "--tg-content-safe-area-inset-top" not in style(rel)]
    assert not bad, f"верх без безопасной зоны: {bad}"
    ok(f"верх страниц за безопасной зоной ({len(PAGES)})")


def check_safe_area_sides_and_bottom() -> None:
    """15. Низ и края — через безопасные зоны: не под панель и не под скругление."""
    bad = []
    for rel in PAGES:
        body = rule(style(rel), "main")
        for side in ("bottom", "left", "right"):
            if f"--tg-safe-area-inset-{side}" not in body:
                bad.append(f"{rel}: у main нет зоны {side}")
    assert not bad, "; ".join(bad[:6])
    ok("низ и края страниц за безопасными зонами")


def check_main_padding_not_flat() -> None:
    """16. Короткого `padding: 40px 24px 80px` у main не осталось."""
    bad = []
    for rel in PAGES:
        for name, value in decls(rule(style(rel), "main")):
            if name == "padding" and "safe-area" not in value:
                bad.append(f"{rel}: main padding: {value}")
    assert not bad, "; ".join(bad[:6])
    ok("отступы main расписаны по сторонам, а не одной строкой")


# ==========================================================================
# 4. Высота: стабильная, а не дёргающаяся
# ==========================================================================
def check_stable_height_read() -> None:
    """17. Высоту берём из viewportStableHeight."""
    bad = [rel for rel in PAGES if "viewportStableHeight" not in code(rel)]
    assert not bad, f"стабильная высота не читается: {bad}"
    ok(f"высота берётся из viewportStableHeight ({len(PAGES)})")


def check_no_viewport_height() -> None:
    """18. viewportHeight не читается: он дёргается во время жестов."""
    bad = []
    for rel in PAGES:
        src = code(rel)
        if re.search(r"viewportHeight", src):
            bad.append(rel)
    assert not bad, f"читают дёргающуюся высоту: {bad}"
    ok("дёргающаяся viewportHeight не используется")


def check_body_height_from_stable() -> None:
    """19. Высота страницы — от стабильной высоты окна, а не от 100vh."""
    bad = []
    for rel in PAGES:
        body = rule(style(rel), "body")
        got = dict(decls(body)).get("min-height", "")
        if "--tg-vh" not in got:
            bad.append(f"{rel}: min-height: {got!r}")
    assert not bad, "; ".join(bad[:6])
    ok("высота страницы считается от стабильной высоты окна")


def check_stable_height_measured() -> None:
    """20. Переменная высоты действительно равна стабильной высоте окна."""
    bad = []
    for rel in PAGES:
        v = run_of(rel)["first"]
        if v.get("--tg-vh") != "612px":
            bad.append(f"{rel}: --tg-vh = {v.get('--tg-vh')!r}, ждали 612px")
    assert not bad, "; ".join(bad[:6])
    ok("высота окна замеряется по стабильной высоте")


def check_viewport_changed_listened() -> None:
    """21. Окно изменилось — высота пересчитывается."""
    bad = [rel for rel in PAGES
           if "viewportChanged" not in " ".join(run_of(rel)["events"])]
    assert not bad, f"viewportChanged не слушается: {bad}"
    ok("изменение окна пересчитывает высоту")


def check_bottom_pinned_uses_stable() -> None:
    """22. Элемент, прижатый к низу, опирается на стабильную высоту или зону."""
    bad = []
    for rel in PAGES:
        for m in re.finditer(r"\{[^{}]*position:\s*(fixed|sticky)[^{}]*\}", style(rel)):
            block = m.group(0)
            # «border-bottom» не считается: речь о прижатии к низу окна
            if re.search(r"(?<![-a-z])bottom\s*:", block) and \
                    "--tg-vh" not in block and "safe-area-inset-bottom" not in block:
                bad.append(f"{rel}: {block.strip()[:80]}")
    assert not bad, "; ".join(bad[:4])
    ok("прижатые к низу элементы держатся за стабильную высоту")


# ==========================================================================
# 5. Данные: жёсткий блок. Оформление не имеет права лезть в запись
# ==========================================================================
# Снимок снят ДО правки оформления. Прибит руками: посчитать ключи из самого
# файла значит согласиться с любым его состоянием, включая «полей не осталось».
FORM_RECORD: Dict[str, Dict] = {
    "state-week/app4.html": {
        "block": "state_week",
        "instrument": "PANAS-SF + Vitality + PHQ-2/GAD-2 + поток + KMS-3",
        "tests": ["panas", "vitality", "gate", "flow", "couple"],
        "sizes": [10, 7, 4, 1, 3],
        "scores": {
            "panas": ["band", "na", "nums", "pa"],
            "vitality": ["band", "mean", "nums"],
            "gate": ["alert", "band", "gad", "nums", "phq"],
            "flow": ["band", "nums", "value"],
            "couple": ["band", "nums", "sum"],
        },
        "top": ["couple", "flow", "gate", "panas", "source", "vitality"],
        "answers": ["couple", "flow", "gate", "panas", "vitality"],
    },
    "state-month/app3.html": {
        "block": "state_month", "instrument": "PSS-10 + ISI",
        "tests": ["pss", "isi"], "sizes": [10, 7],
        "scores": {"pss": ["band", "nums", "total"],
                   "isi": ["alert", "band", "nums", "total"]},
        "top": ["alert", "isi", "pss", "source"],
        "answers": ["isi", "pss"],
    },
    "state-quarter/app3.html": {
        "block": "state_quarter",
        "instrument": "SWLS + MLQ + FFMQ-15 + RSES + OLBI + MSPSS",
        "tests": ["swls", "mlq", "ffmq", "rses", "olbi", "support"],
        "sizes": [5, 10, 15, 10, 16, 12],
        "scores": {
            "swls": ["band", "nums", "sum"],
            "mlq": ["band", "nums", "presence", "search"],
            "ffmq": ["act_aware", "band", "describe", "mean", "nonjudge",
                     "nonreact", "nums", "observe"],
            "rses": ["band", "nums", "sum"],
            "olbi": ["band", "disengagement", "disengagement_sum", "exhaustion",
                     "exhaustion_sum", "nums"],
            "support": ["band", "family", "friends", "nums", "significant_other"],
        },
        "top": ["ffmq", "mlq", "olbi", "rses", "source", "support", "swls"],
        "answers": ["ffmq", "mlq", "olbi", "rses", "support", "swls"],
    },
    "state-clinical/app.html": {
        "block": "state_clinical", "instrument": "PHQ-9 + GAD-7 + ASRM",
        "tests": ["phq", "gad", "asrm"], "sizes": [9, 7, 5],
        "scores": {
            "phq": ["alert", "band", "item9", "item9_flag", "nums", "total"],
            "gad": ["alert", "band", "nums", "total"],
            "asrm": ["alert", "band", "nums", "total"],
        },
        "top": ["alert", "asrm", "gad", "phq", "source"],
        "answers": ["asrm", "gad", "phq"],
    },
    "state-year/app.html": {
        "block": "state_year", "instrument": "AUDIT-C",
        "tests": ["audit"], "sizes": [3],
        "scores": {"audit": ["alert", "band", "nums", "sex_asked", "threshold",
                             "total"]},
        "top": ["alert", "audit", "source"],
        "answers": ["audit"],
    },
    "state-team/app.html": {
        "block": "state_team",
        "instrument": "Шкала психологической безопасности команды (Edmondson, 1999)",
        "tests": ["safety"], "sizes": [7],
        "scores": {"safety": ["band", "mean", "nums"]},
        "top": ["alert", "safety", "source"],
        "answers": ["safety"],
    },
    "state-needs/app.html": {
        "block": "state_needs", "instrument": "BPNSFS",
        "tests": ["bpnsfs"], "sizes": [24],
        "scores": {"bpnsfs": [
            "autonomy_frustration", "autonomy_satisfaction", "band",
            "competence_frustration", "competence_satisfaction", "frustration",
            "nums", "relatedness_frustration", "relatedness_satisfaction",
            "satisfaction"]},
        "top": ["alert", "bpnsfs", "source"],
        "answers": ["bpnsfs"],
    },
    "selfhood/app.html": {
        "block": "selfhood",
        "instrument": "SCCS + Authenticity Scale + DIDS + DSI-R (I-position)",
        "tests": ["clarity", "authenticity", "identity", "iposition"],
        "sizes": [12, 11, 25, 11],
        "scores": {
            "clarity": ["band", "mean", "nums", "sum"],
            "authenticity": ["authentic_living", "band", "external_influence",
                             "nums", "self_alienation"],
            "identity": ["band", "commitment", "exploration_breadth",
                         "exploration_depth", "identification", "nums",
                         "rumination"],
            "iposition": ["band", "mean", "nums", "sum"],
        },
        "top": ["authenticity", "clarity", "identity", "iposition", "source"],
        "answers": ["authenticity", "clarity", "identity", "iposition"],
    },
}

# Сутки: ключи scores при полном заполнении.
DAY_SCORES = ["awakenings", "battery", "bed", "containers", "hrv", "mood",
              "practice_kind", "practice_min", "resting_hr", "sleep_hours",
              "sleep_latency", "sleep_quality", "source", "tonus", "wake"]

# Шесть замеров-разговоров: строка базы и ключи внутри.
NEW_RECORD: Dict[str, Dict] = {
    "state-move/app.html": {
        "block": "state_move", "instrument": "state_move",
        "scores": {"evs": ["days", "min_day", "min_week"]}, "top": ["evs", "source"]},
    "state-people/app.html": {
        "block": "state_people", "instrument": "state_people",
        "scores": {"lonely": ["items", "met", "total"]}, "top": ["lonely", "source"]},
    "state-facts/app.html": {
        "block": "state_facts", "instrument": "state_facts",
        "scores": {"facts": ["containers", "marked", "shown", "work_evenings"],
                   "signs": ["kids", "meditates", "team"]},
        "top": ["facts", "signs", "source"]},
    "state-note/app.html": {
        "block": "state_note", "instrument": "state_note",
        "scores": {"note": ["containers", "text"]}, "top": ["note", "source"]},
    "state-money/app.html": {
        "block": "state_money", "instrument": "state_money",
        "scores": {"money": ["cushion_n", "debts_n", "enough", "enough_word",
                             "gap_n", "shock_text"]},
        "top": ["money", "source"]},
    "state-domains/app.html": {
        "block": "state_domains", "instrument": "state_domains",
        "scores": {"pwi": [
            "achieve", "community", "future", "health", "imp_achieve",
            "imp_community", "imp_future", "imp_health", "imp_living",
            "imp_meaning", "imp_relations", "imp_safety", "living", "meaning",
            "relations", "safety", "thin"]},
        "top": ["pwi", "source"]},
}

ROW_KEYS = ["answers", "block", "completed_at", "id", "instrument", "scores",
            "user_id"]

FILL_ALL = ("api.TESTS.forEach(t => fill(t.key, null));\n"
            "OUT.scores = api.buildScores();\nOUT.answers = api.buildAnswers();")


def check_forms_record_untouched() -> None:
    """23. Восемь опросников: блок, инструмент и все ключи записи те же."""
    bad = []
    for rel, want in FORM_RECORD.items():
        got = form_app(rel, FILL_ALL)
        if got["block"] != want["block"]:
            bad.append(f"{rel}: блок {got['block']!r}")
        if got["instrument"] != want["instrument"]:
            bad.append(f"{rel}: инструмент {got['instrument']!r}")
        if got["keys"] != want["tests"]:
            bad.append(f"{rel}: тесты {got['keys']}")
        if got["sizes"] != want["sizes"]:
            bad.append(f"{rel}: пунктов {got['sizes']}, было {want['sizes']}")
        scores = got["scores"]
        if sorted(scores) != sorted(want["top"]):
            bad.append(f"{rel}: верхние ключи {sorted(scores)}")
        for inst, fields in want["scores"].items():
            if sorted(scores.get(inst, {})) != fields:
                bad.append(f"{rel}: {inst} → {sorted(scores.get(inst, {}))}")
        if sorted(got["answers"]) != want["answers"]:
            bad.append(f"{rel}: ответы {sorted(got['answers'])}")
    assert not bad, "; ".join(bad[:6])
    ok("восемь опросников: запись и число пунктов не тронуты")


def check_day_record_untouched() -> None:
    """24. Сутки: ключи записи те же."""
    js = r"""
globalThis.window = { location: { search: '?u=tg_777' } };
""" + pure_block(DAY) + r"""
const built = buildScores({ bed: '23:30', wake: '07:00', sleepQuality: 7, tonus: 6,
  mood: 5, sleepLatency: 20, awakenings: 1, restingHr: 52, battery: 70, hrv: 60,
  practiceMin: 15, practiceKind: 'медитация',
  eventText: 'завал в отчётах и жена устала' });
const OUT = { scores: Object.keys(built.scores).sort(), has: built.hasMeasurement };
console.log('RESULT<' + JSON.stringify(OUT) + '>RESULT');
"""
    got = _node(js)
    assert got["has"] is True, "сутки: полный заход перестал считаться замером"
    assert got["scores"] == DAY_SCORES, f"сутки: ключи {got['scores']}"
    ok("сутки: ключи записи не тронуты")


def check_new_pages_record_untouched() -> None:
    """25. Шесть замеров-разговоров: строка базы и ключи внутри те же."""
    bad = []
    for block, rel in zm.PAGES.items():
        rows = zm.full_run(block)["rows"]
        if len(rows) != 1:
            bad.append(f"{rel}: строк в базе {len(rows)}")
            continue
        row, want = rows[0], NEW_RECORD[rel]
        if sorted(row) != ROW_KEYS:
            bad.append(f"{rel}: поля строки {sorted(row)}")
        if row["block"] != want["block"] or row["instrument"] != want["instrument"]:
            bad.append(f"{rel}: блок/инструмент {row['block']!r}/{row['instrument']!r}")
        if sorted(row["scores"]) != sorted(want["top"]):
            bad.append(f"{rel}: верхние ключи {sorted(row['scores'])}")
        for inst, fields in want["scores"].items():
            if sorted(row["scores"].get(inst, {})) != fields:
                bad.append(f"{rel}: {inst} → {sorted(row['scores'].get(inst, {}))}")
        if sorted(row["answers"]) != ["raw"]:
            bad.append(f"{rel}: ответы {sorted(row['answers'])}")
    assert not bad, "; ".join(bad[:6])
    ok("шесть замеров-разговоров: запись не тронута")


def check_main_button_untouched() -> None:
    """26. MainButton не появился: перенос отправки — отдельная работа."""
    bad = [rel for rel in PAGES if "MainButton" in code(rel)]
    assert not bad, f"отправка переехала на главную кнопку без спеки: {bad}"
    ok("главную кнопку не трогали")


if __name__ == "__main__":
    raise SystemExit(run([
        check_theme_vars_with_fallback,
        check_alpha_shades_follow_ink,
        check_alpha_values_unchanged,
        check_no_stray_color_literals,
        check_dark_palette_block,
        check_dark_accent_readable,
        check_palette_same_in_css_and_script,
        check_theme_changed_listened,
        check_theme_paints_on_open,
        check_theme_repaints_on_change,
        check_accent_switches_with_scheme,
        check_header_follows_theme,
        check_no_telegram_no_paint,
        check_safe_area_top,
        check_safe_area_sides_and_bottom,
        check_main_padding_not_flat,
        check_stable_height_read,
        check_no_viewport_height,
        check_body_height_from_stable,
        check_stable_height_measured,
        check_viewport_changed_listened,
        check_bottom_pinned_uses_stable,
        check_forms_record_untouched,
        check_day_record_untouched,
        check_new_pages_record_untouched,
        check_main_button_untouched,
    ]))
