# -*- coding: utf-8 -*-
"""Проверки: историю замера привозит бот, а не память телефона.

Дефект живого человека 10.08.2026, дословно: «я открыл сутки и кажется, что
сегодня проходил уже и раньше проходил, а историю не вижу».

Данные были целы — четыре точки в базе. Страница их не видела, потому что
«прошлый раз» знала только из памяти телефона (`localStorage`), а Телеграм-кэш
человек почистил. Читать базу страница не может: у публичного ключа есть право
только на вставку, и открывать чтение нельзя ни в каком виде. Значит историю
обязан передавать бот — параметром `h=`.

Что проверяем — на собранных ЭКРАНАХ и на СЕТИ, а не в исходнике:
  · ЖЁСТКО: ни одна страница замера не ходит в `passport` за чтением;
  · ключи линий страницы совпадают с `HIST_LINES` в `bot.py`;
  · история из адреса показана, и памяти телефона для этого не нужно;
  · параметра нет — работает запасной путь через память телефона;
  · адрес и память расходятся — берётся адрес;
  · нет ни того, ни другого — блока истории нет вовсе;
  · график: одна линия на показатель, на оси ни одной цифры, подписи словами;
  · пропуск в серии рвёт линию;
  · поле практики объясняет себя до ввода;
  · сигнал боту уходит ПОСЛЕ ответа сервера, ровно один раз;
  · сигнал послать нельзя — человек видит результат на странице;
  · восстановленное из адреса в запись не уходит;
  · каталог передаёт странице только её запись истории.

Запуск:  python3 checks/istoriya_ot_bota.py
"""

import ast
import json
import re
import urllib.parse
from datetime import datetime, timezone

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
from lib import (BOT, ROOT, catalog_render, html, inline_script, ok,
                 pure_block, run, visible)

DAY = "state-day/app.html"
CATALOG = "kak-ty/app.html"

# Все страницы замеров подвижного слоя. Список прибит руками нарочно: посчитать
# его из папок значит согласиться с любым их состоянием, включая «страниц не
# осталось».
MEASURE_PAGES = [
    "state-day/app.html", "state-week/app4.html", "state-month/app3.html",
    "state-quarter/app3.html", "state-clinical/app.html", "state-year/app.html",
    "state-team/app.html", "state-needs/app.html", "state-move/app.html",
    "state-people/app.html", "state-facts/app.html", "state-note/app.html",
    "state-money/app.html", "state-domains/app.html", "state-finwell/app.html",
    "state-health/app.html", "pair-faces/app.html", "selfhood/app.html",
]

# Где публичный ключ вообще ПРОБУЕТ читать базу: два каталога, «Что со мной?» и
# «Как я устроен». Запрос там лежит с пометкой «работает, только если у ключа есть
# право читать; сейчас его нет, база отдаёт пустой список» и служит ДОПОЛНЕНИЕМ к
# параметру `f=` от бота, а не заменой ему.
#
# Список явный и закрытый: появится третье такое место — проверка упадёт. Именно
# поэтому история едет параметром от бота, а не запросом со страницы: право читать
# `passport` означало бы право читать чужие замеры, и выдавать его нельзя.
READ_ALLOWED = {CATALOG, "kak-ustroen/app.html"}

# История, как её присылает бот. Строка собрана по контракту из `bot.py` и
# проверяется там же обратным разбором (`specs/019-istoriya-ot-bota/checks.py`).
HIST = ("state_day!tonus,mood,sleep_quality,sleep_hours,practice_min"
        "!260804:5,6,7,7.5,0!260807:7,8,6,8,10!260808:6,7,,8.5,0"
        "!260809:4,9,5,6,15")

# Дата берётся живой, а не прибитой строкой. Прибитая «2026-08-10» пережила
# ровно один день: 11.08.2026 проверка покраснела на ровном месте — точка,
# которую она считала сегодняшней, стала вчерашней и законно превратилась в
# историю. Страница при этом была исправна. День страница считает по UTC
# (`utcDayKey`), поэтому и здесь UTC, иначе вечером сойдёмся на разных сутках.
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")


# --------------------------------------------------------------------------
# Стенд: суточная страница с подставленным адресом, памятью и Телеграмом
# --------------------------------------------------------------------------
STUBS = r"""
globalThis.LOG = [];
globalThis.window = { location: { search: %(search)s } };
globalThis.localStorage = {
  _s: %(ls)s,
  getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
  setItem(k, v) { this._s[k] = String(v); globalThis.LOG.push('ls:' + k); },
  removeItem(k) { delete this._s[k]; globalThis.LOG.push('rm:' + k); }
};
globalThis.PUSHED = [];
globalThis.fetch = async function (url, opts) {
  globalThis.PUSHED.push({ url: String(url), method: (opts && opts.method) || 'GET',
                           body: opts && opts.body ? JSON.parse(opts.body) : null });
  globalThis.LOG.push('fetch:' + ((opts && opts.method) || 'GET'));
  return { ok: true, status: 201, json: async () => [] };
};
globalThis.TG_SENT = [];
globalThis.document = {
  documentElement: { style: { setProperty() {} } },
  getElementById() { return __el(); },
  createElement() { return __el(); },
  addEventListener() {},
  body: { appendChild() {}, removeChild() {} },
  execCommand() { return true; }
};
function __el() {
  return { style: {}, innerHTML: '', textContent: '', value: '', disabled: false,
           addEventListener() {}, removeEventListener() {},
           setAttribute() {}, getAttribute() { return null; },
           querySelectorAll() { return []; },
           classList: { toggle() {}, add() {}, remove() {} } };
}
globalThis.history = { length: 1, back() {} };
// `window.crypto` в заглушке нет вовсе — страница уходит на запасной хеш, как на
// старом телефоне. Номер записи от этого не меняет смысла: он всё равно
// детерминированный, и «одна точка за сутки» держится.
%(tg)s
"""

TG_ON = r"""
globalThis.window.Telegram = { WebApp: {
  initData: %(init)s,
  initDataUnsafe: {},
  colorScheme: 'light', themeParams: {},
  viewportStableHeight: 600,
  ready() {}, expand() {}, close() { globalThis.LOG.push('close'); },
  isVersionAtLeast() { return true; },
  onEvent() {}, setHeaderColor() {}, setBackgroundColor() {},
  enableClosingConfirmation() { globalThis.LOG.push('arm'); },
  disableClosingConfirmation() { globalThis.LOG.push('relax'); },
  BackButton: { onClick() {}, show() {} },
  sendData(d) { globalThis.TG_SENT.push(String(d)); globalThis.LOG.push('sendData'); }
}};
"""


def day_run(js: str, search: str = "?u=tg_777", ls: dict = None,
            telegram: bool = True, init: str = "",
            no_send: bool = False) -> dict:
    """Собрать суточную страницу целиком и выполнить переданный кусок JS.

    Страница исполняется вся, с заглушками вместо браузера, сети и Телеграма.
    Так проверяется ЭКРАН и ПОРЯДОК ДЕЙСТВИЙ, а не текст исходника.
    """
    tg = ""
    if telegram:
        tg = TG_ON % {"init": json.dumps(init)}
        if no_send:
            tg = tg.replace("sendData(d) { globalThis.TG_SENT.push(String(d));"
                            " globalThis.LOG.push('sendData'); }",
                            "sendDataMissing: 1")
    stubs = STUBS % {"search": json.dumps(search),
                     "ls": json.dumps(ls or {}), "tg": tg}
    code = stubs + inline_script(DAY) + r"""
const OUT = {};
(async function () {
  await new Promise(r => setTimeout(r, 20));
""" + js + r"""
  OUT.log = globalThis.LOG;
  OUT.sent = globalThis.TG_SENT;
  OUT.pushed = globalThis.PUSHED;
  console.log('RESULT<' + JSON.stringify(OUT) + '>RESULT');
})();
"""
    return _node(code)


def _node(js: str) -> dict:
    import os
    import subprocess
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False,
                                     encoding="utf-8") as f:
        f.write(js)
        path = f.name
    try:
        r = subprocess.run(["node", path], capture_output=True, text=True,
                           timeout=60)
    finally:
        os.unlink(path)
    assert r.returncode == 0, f"node упал: {r.stderr.strip()[:2000]}"
    m = re.search(r"RESULT<(.*)>RESULT", r.stdout, re.S)
    assert m, f"скрипт ничего не вернул. stdout: {r.stdout[:600]}"
    return json.loads(m.group(1))


def pure_run(js: str) -> dict:
    """Прогнать только чистую логику страницы: без DOM и без сети."""
    code = pure_block(DAY) + r"""
const OUT = {};
""" + js + r"""
console.log('RESULT<' + JSON.stringify(OUT) + '>RESULT');
"""
    return _node(code)


def bot_hist_lines() -> dict:
    """`HIST_LINES` из `bot.py`. Только чтение, разбором AST."""
    tree = ast.parse(BOT.read_text(encoding="utf-8"))
    for node in tree.body:
        name = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
        if name == "HIST_LINES":
            ns: dict = {"Dict": dict, "Tuple": tuple}
            exec(compile(ast.Module(body=[node], type_ignores=[]), "<bot>",
                         "exec"), ns)
            return ns["HIST_LINES"]
    raise AssertionError("в bot.py нет HIST_LINES — историю передавать нечем")


# ---------------------------------------------------------------- 1
def check_no_read_with_public_key() -> None:
    """1. ЖЁСТКО: страницы замеров не читают базу публичным ключом."""
    for rel in MEASURE_PAGES:
        body = html(rel)
        assert "rest/v1/passport?" not in body, \
            (f"{rel}: появился запрос к таблице замеров. У публичного ключа есть "
             "право только на вставку, и открывать чтение нельзя: адрес страницы "
             "не секрет")
        assert 'method: "GET"' not in body and "method: 'GET'" not in body, \
            f"{rel}: появился явный GET"
        assert "select=" not in body, \
            f"{rel}: появился выбор полей — это чтение базы"
    ok(f"1. ни одна из {len(MEASURE_PAGES)} страниц замеров базу не читает")

    # Ни одного нового места, где публичный ключ пробует читать.
    found = set()
    for p in sorted(ROOT.glob("*/app*.html")):
        rel = f"{p.parent.name}/{p.name}"
        if "rest/v1/passport?" in p.read_text(encoding="utf-8"):
            found.add(rel)
    assert found <= READ_ALLOWED, \
        f"публичный ключ пробует читать базу в новых местах: {sorted(found - READ_ALLOWED)}"
    ok("1. новых мест чтения базы публичным ключом не появилось")

    # Историю привозит бот: страница обязана разбирать параметр.
    src = inline_script(DAY)
    assert 'params.get("h")' in src, \
        "страница не читает параметр истории — дефект вернулся"
    ok("1. историю страница берёт из адреса")


# ---------------------------------------------------------------- 2
def check_keys_match_bot() -> None:
    """2. Ключи линий страницы совпадают с `HIST_LINES` в `bot.py`."""
    got = pure_run("OUT.meta = HIST_META.map(m => m.key); OUT.card = HIST_CARD;")
    want = list(bot_hist_lines()[got["card"]])
    assert got["meta"] == want, \
        (f"ключи разъехались: страница читает {got['meta']}, бот присылает {want}. "
         "Страница будет показывать пустоту")
    ok("2. ключи линий страницы и бота совпадают буквально")

    # Разбор контракта: те же точки, что положил бот.
    got = pure_run("OUT.rec = parseHist(%s).state_day;" % json.dumps(HIST))
    pts = got["rec"]["points"]
    assert [p["day"] for p in pts] == ["260804", "260807", "260808", "260809"], \
        f"даты разобрались не те: {[p['day'] for p in pts]}"
    assert pts[0]["vals"]["sleep_hours"] == 7.5, "дробное значение потерялось"
    assert pts[0]["vals"]["practice_min"] == 0, "нуль прочитан как отсутствие"
    assert "sleep_quality" not in pts[2]["vals"], \
        "пустое место прочитано как значение — три состояния сломаны"
    ok("2. контракт разбирается: дробное, нуль и «не отмечено» различимы")

    # Мусор отбрасывается молча, а не превращается в данные.
    bad = pure_run("""
OUT.junk = [
  Object.keys(parseHist('state_day!tonus')).length,
  Object.keys(parseHist('')).length,
  Object.keys(parseHist('state_day!tonus!нетдаты:5')).length,
  Object.keys(parseHist('~~~')).length
];
""")
    assert bad["junk"] == [0, 0, 0, 0], f"мусор стал данными: {bad['junk']}"
    ok("2. обломок и мусор данными не становятся")


# ---------------------------------------------------------------- 3
def check_history_from_url() -> None:
    """3. История из адреса показана, память телефона для этого не нужна."""
    got = day_run("OUT.html = app.innerHTML;",
                  search=f"?u=tg_777&h={HIST}")
    text = visible(got["html"])
    assert "Что было раньше" in text, f"блока истории нет: {text[:300]}"
    assert "В прошлый раз" in text, "строки «в прошлый раз» нет"
    assert "тонус 4" in text, f"своих цифр прошлой отметки не видно: {text[:400]}"
    assert "настроение 9" in text, "не все линии прошлой отметки названы"
    ok("3. память телефона пуста, а история есть — дефект закрыт")

    # Сегодняшняя точка историей не считается: это «как есть», а не «как было».
    got = day_run("OUT.html = app.innerHTML;",
                  search=f"?u=tg_777&h=state_day!tonus!{TODAY[2:].replace('-','')}:8")
    assert "Что было раньше" not in visible(got["html"]), \
        "сегодняшняя точка показана как история прошлых заходов"
    ok("3. сегодняшняя точка историей не считается")


# ---------------------------------------------------------------- 4
def check_fallback_and_priority() -> None:
    """4. Параметра нет — работает память; есть — она сильнее памяти."""
    ls = {"sutki_v1_777": json.dumps({
        "dayKey": "2026-08-01", "savedAt": "2026-08-01T10:00:00.000Z",
        "form": {"tonus": 2, "mood": 3, "sleepHours": 6}})}

    got = day_run("OUT.html = app.innerHTML;", search="?u=tg_777", ls=ls)
    text = visible(got["html"])
    assert "В прошлый раз" in text, "запасной путь через память телефона не работает"
    assert "тонус 2" in text, f"значения из памяти не подставились: {text[:300]}"
    ok("4. параметра нет — работает память телефона")

    got = day_run("OUT.html = app.innerHTML;",
                  search=f"?u=tg_777&h={HIST}", ls=ls)
    text = visible(got["html"])
    assert "тонус 4" in text, "адрес не победил память телефона"
    assert "тонус 2" not in text, \
        ("память телефона победила адрес — после чистки кэша человек снова "
         "увидит пустоту")
    ok("4. адрес и память расходятся — берётся адрес")

    got = day_run("OUT.html = app.innerHTML;", search="?u=tg_777")
    assert "Что было раньше" not in visible(got["html"]), \
        "истории нет, а блок показан — пустое место читается как факт про себя"
    ok("4. ни адреса, ни памяти — блока нет вовсе")


# ---------------------------------------------------------------- 5
def check_chart() -> None:
    """5. График: линия на показатель, на оси ни одной цифры, подписи словами."""
    got = day_run("OUT.html = app.innerHTML;", search=f"?u=tg_777&h={HIST}")
    page = got["html"]
    svgs = re.findall(r"<svg class=\"spark\".*?</svg>", page, re.S)
    assert len(svgs) >= 4, f"линий меньше, чем показателей с данными: {len(svgs)}"
    ok(f"5. одна линия на показатель, всего {len(svgs)}")

    for s in svgs:
        assert "<text" not in s, "на графике появился текст — это цифры на оси"
        assert visible(s).strip() == "", f"внутри графика читаемый текст: {visible(s)}"
    ok("5. на оси ни одной цифры")

    text = visible(page)
    for word in ("больше сил", "меньше сил", "легче", "тяжелее",
                 "спал дольше", "спал меньше"):
        assert word in text, f"подписи словами «{word}» нет"
    for bad in ("мало", "много", "плохо", "низк", "высок", "средн", "балл",
                "норм"):
        assert bad not in text.lower(), f"на экране оценочное слово «{bad}»"
    ok("5. подписи словами, оценочных слов нет")

    # Пропуск рвёт линию, а не сглаживается через день, которого не было.
    got = pure_run("""
OUT.whole = sparkSegments([1, 2, 3, 4], 0, 10, 100, 40).length;
OUT.gap = sparkSegments([1, 2, null, 4, 5], 0, 10, 100, 40).length;
OUT.one = sparkSegments([5], 0, 10, 100, 40).length;
OUT.empty = sparkSegments([], 0, 10, 100, 40).length;
""")
    assert got["whole"] == 1, "целая серия разорвалась"
    assert got["gap"] == 2, f"пропуск не разорвал линию: отрезков {got['gap']}"
    assert got["one"] == 0 and got["empty"] == 0, \
        "линия нарисовалась из одной точки — это выдуманная линия"
    ok("5. пропуск рвёт линию, из одной точки линии не бывает")

    # По одной прошлой точке графика нет: линии из одной точки не бывает.
    got = day_run("OUT.html = app.innerHTML;",
                  search="?u=tg_777&h=state_day!tonus!260801:5")
    assert "В прошлый раз" in visible(got["html"]), "строка «в прошлый раз» пропала"
    assert 'class="spark"' not in got["html"], \
        "по одной точке нарисован график"
    ok("5. одна прошлая точка — строка есть, графика нет")


# ---------------------------------------------------------------- 6
def check_practice_field() -> None:
    """6. Поле практики объясняет себя ДО ввода."""
    got = day_run("OUT.html = app.innerHTML;", search="?u=tg_777")
    text = visible(got["html"])
    assert "Практика внимания" in text, \
        "поле по-прежнему называется просто «Практика» — непонятно, что считать"
    for word in ("Медитация", "дыхание", "сканирование тела"):
        assert word in text, f"примеров практики нет: «{word}»"
    assert "Бег и зал" in text, "не сказано, что НЕ считается практикой"
    assert "это тоже ответ" in text, "нуль не назван нормальным ответом"
    ok("6. сказано что считается, что нет и что нуль — ответ")

    # Всё это стоит ДО ввода: подсказка вида появлялась только после выбора минут.
    i_name = text.index("Практика внимания")
    i_hint = text.index("Медитация")
    i_chips = text.index("Что сегодня было")
    assert i_name < i_hint < i_chips, \
        f"подсказка стоит не до ввода: {i_name}, {i_hint}, {i_chips}"
    ok("6. подсказка стоит до ввода, а не после выбора минут")

    for bad in ("хотя бы", "всего", "мало", "лень"):
        assert bad not in text.lower(), f"в поле практики оценка «{bad}»"
    ok("6. оценочных слов в поле практики нет")


# ---------------------------------------------------------------- 7
def check_signal_to_bot() -> None:
    """7. Сигнал боту — после ответа сервера, ровно один раз."""
    js = r"""
  form.tonus = 5; form.mood = 7; form.sleepHours = 7;
  await submit();
  OUT.html = app.innerHTML;
"""
    got = day_run(js, search="?u=tg_777&h=" + HIST)
    assert got["sent"] == ['{"action":"state_saved","block":"state_day"}'], \
        f"сигнал ушёл не тот или не один: {got['sent']}"
    ok("7. один сигнал с точным содержимым")

    log = got["log"]
    assert "sendData" in log, "сигнал не ушёл вовсе"
    assert log.index("fetch:POST") < log.index("sendData"), \
        ("сигнал ушёл до ответа сервера — sendData закрывает мини-апп и "
         "обрывает запись")
    assert log.index("rm:sutki_draft_777") < log.index("sendData"), \
        "черновик к моменту сигнала ещё не стёрт — потеряется"
    assert log.index("ls:sutki_v1_777") < log.index("sendData"), \
        "отметка «отправлено» ставится после сигнала — мини-апп уже закроется"
    ok("7. порядок: запись → черновик стёрт → сигнал")

    # Повторные нажатия не рождают второй сигнал и второе сообщение бота.
    twice = day_run(r"""
  form.tonus = 5; form.mood = 7;
  await submit();
  SIGNAL_SENT = SIGNAL_SENT;   // ничего не сбрасываем, как в жизни
  await submit();
  OUT.n = globalThis.TG_SENT.length;
""", search="?u=tg_777")
    assert twice["n"] == 1, f"сигналов {twice['n']} вместо одного"
    ok("7. вторая отправка второго сигнала не рождает")

    # Сигнал послать нельзя — человек видит результат на странице, а не тишину.
    for label, kw in (("мини-апп открыт не кнопкой клавиатуры",
                       {"init": "user=%7B%22id%22%3A1%7D"}),
                      ("метода sendData нет вовсе", {"no_send": True}),
                      ("Телеграма нет", {"telegram": False})):
        got = day_run(js, search="?u=tg_777&h=" + HIST, **kw)
        text = visible(got["html"])
        assert not got["sent"], f"{label}: сигнал всё равно позвали"
        assert "Записал" in text, f"{label}: человек остался без результата"
        assert "Тонус" in text, f"{label}: своих цифр в результате нет"
    ok("7. сигнал недоступен — результат показывает страница")


# ---------------------------------------------------------------- 8
def check_history_never_written() -> None:
    """8. Восстановленное из адреса в запись не уходит."""
    got = day_run(r"""
  form.tonus = 5;
  await submit();
  OUT.scores = globalThis.PUSHED[0].body.scores;
  OUT.raw = globalThis.PUSHED[0].body.answers.raw;
""", search=f"?u=tg_777&h={HIST}")
    scores = got["scores"]
    assert scores["tonus"] == 5, f"свой ответ не записался: {scores}"
    for key in ("mood", "sleep_quality", "sleep_hours", "practice_min"):
        assert key not in scores, \
            (f"поле «{key}» уехало в базу из истории — в запись попадает только "
             "то, что человек дал в этом заходе (011, FR-004)")
    assert "9" not in str(got["raw"]), \
        f"значения истории попали в читаемую строку записи: {got['raw']}"
    ok("8. в записи только этот заход, история в базу не уходит")

    # Поля формы историей не заполняются: она только показывается.
    got = day_run("OUT.form = form;", search=f"?u=tg_777&h={HIST}")
    assert got["form"]["mood"] is None and got["form"]["tonus"] is None, \
        "история подставилась в поля формы"
    ok("8. история в поля формы не подставляется")


# ---------------------------------------------------------------- 9
def check_catalog_forwards() -> None:
    """9. Каталог передаёт странице только её запись истории."""
    got = _node(pure_block(CATALOG) + r"""
const OUT = {
  day: histPick(%s, 'state_day'),
  week: histPick(%s, 'state_week'),
  none: histPick(%s, 'state_month'),
  junk: histPick('state_day!tonus', 'state_day'),
  empty: histPick('', 'state_day')
};
console.log('RESULT<' + JSON.stringify(OUT) + '>RESULT');
""" % (json.dumps(HIST + "~state_week!vitality!260801:5!260808:6"),
       json.dumps(HIST + "~state_week!vitality!260801:5!260808:6"),
       json.dumps(HIST)))
    assert got["day"] == HIST, f"запись суточной выбралась не целиком: {got['day']}"
    assert got["week"] == "state_week!vitality!260801:5!260808:6", \
        "запись недельной выбралась неверно"
    assert got["none"] == "" and got["junk"] == "" and got["empty"] == "", \
        "каталог отдаёт обломок или чужую запись"
    ok("9. каталог выбирает ровно запись нужной карточки")

    src = inline_script(CATALOG)
    assert "histPick(HIST_RAW, card.key)" in src, \
        "каталог не подставляет историю в адрес страницы"
    assert 'params.get("h")' in src, "каталог не читает историю от бота"
    ok("9. каталог берёт историю от бота и отдаёт её дальше")

    # Главное — не текст исходника, а СОБРАННАЯ ссылка: по ней человек и уходит.
    pair = HIST + "~state_week!vitality!260801:5!260808:6"
    page = catalog_render("?u=tg_777&h=" + pair)
    links = [m.group(1) for m in
             re.finditer(r'href="([^"]*state-day[^"]*)"', page)]
    assert links, "в каталоге нет ссылки на суточный замер"
    for href in links:
        url = href.replace("&amp;", "&")
        assert "h=state_day" in url, \
            f"история в ссылку на замер не поехала: {url}"
        got = urllib.parse.parse_qs(url.split("?", 1)[1]).get("h", [""])[0]
        assert got == HIST, f"история приехала искажённой: {got}"
    ok("9. в собранной ссылке на замер стоит история, и ровно своя")

    # Истории нет — параметра в ссылке нет: пустое место страница прочитала бы
    # как настоящие данные.
    page = catalog_render("?u=tg_777")
    for m in re.finditer(r'href="([^"]*state-day[^"]*)"', page):
        assert "h=" not in m.group(1), \
            f"истории нет, а параметр в ссылке есть: {m.group(1)}"
    ok("9. истории нет — параметра в ссылке нет")


if __name__ == "__main__":
    raise SystemExit(run([
        check_no_read_with_public_key, check_keys_match_bot,
        check_history_from_url, check_fallback_and_priority, check_chart,
        check_practice_field, check_signal_to_bot,
        check_history_never_written, check_catalog_forwards,
    ]))
