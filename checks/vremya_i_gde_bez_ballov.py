# -*- coding: utf-8 -*-
"""Проверки двух оставшихся страниц: ни балла, ни шкалы, ни «правильного профиля».

Задача. В подвижном слое (`no_scales_no_scores.py`) и во второй двери
(`vtoraya_dver_bez_ballov.py`) названия шкал и баллы человеку убраны. Две
страницы остались с прежней болезнью:

  · `ztpi/index.html` — человек читал «Опросник Зимбардо (ZTPI)», «Шкала
    1.0–5.0», пять цифр по шкалам и сравнение со «сбалансированным профилем».
    Балл он принимает как приговор, а «сбалансированный профиль» — как норму.
    Русская версия на нашей выборке не валидизирована, значит нормы у нас нет:
    называть её нельзя, ни строгим тоном, ни ласковым.
  · `where/index.html` — прежняя страница того же замера, что и `state-needs`:
    те же 24 утверждения, тот же квартальный ритм. Одна и та же величина в двух
    местах, и одно из них показывает цифры. Сделана страницей-перехода на
    актуальную — образец в `starye_stranicy.py`.

Что меняется и что НЕ меняется. Меняется только видимый текст. Запись остаётся
прежней до последнего знака: подпись действия, ключи полей и сами числа —
их читает бот, по ним собирается контекст и выгрузка. Проверка 8 прибивает
запись отпечатком: поехала хоть одна цифра — падает.

Что проверяем — на собранных ЭКРАНАХ, а не в исходнике:
  · в видимом тексте нет ни одного латинского слова (это и есть аббревиатуры
    инструментов) и ни одной фамилии автора;
  · нет слов про балл, шкалу, диапазон, норму и «сбалансированный профиль»;
  · нет оценки и похвалы: приятный ярлык запрещён так же, как неприятный;
  · цифра на экран не попадает: подменяем числа замера и числа истории
    метками-ловушками и смотрим, не утекли ли они;
  · на экране результата нет ни одной цифры вообще;
  · вместо балла человек читает свои ответы словами, сдвиг с прошлого раза и
    честную первую точку;
  · показать норму страница физически больше не может: подсчёта «правильного
    профиля» в ней не осталось;
  · запись не изменилась: подпись действия, ключи, числа и число ответов;
  · страница-переход доносит хвост адреса с «u=tg_…» до актуальной страницы.

Запуск:  python3 checks/vremya_i_gde_bez_ballov.py
"""

import hashlib
import json
import re

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
from lib import BOT, ROOT, _node, html, inline_script, ok, run, visible

ZTPI = "ztpi/index.html"
WHERE = "where/index.html"
WHERE_TARGET = "../state-needs/app.html"

# --------------------------------------------------------------------------
# Запись. Отпечаток снят с рабочего кода ДО правки текстов и прибит руками:
# посчитать его из самой страницы значит согласиться с любым её состоянием.
# Ответы узором «1,2,3,4,5,1,2…»: у каждой линии своё среднее, поэтому ошибка в
# индексах или в обратном подсчёте видна, а не прячется за одинаковыми числами.
# --------------------------------------------------------------------------
ACTION = "ztpi_assessment"
FIELDS = ["answers", "future", "past_negative", "past_positive",
          "present_fatalistic", "present_hedonistic", "questionnaire_version"]
DIGEST = "8f634cefd78d176b"
ANSWERS_COUNT = 56

# Фамилии авторов и русские сокращения инструментов. Латиницу ловит отдельная
# проверка, здесь то, что написано по-русски.
AUTHORS = ["Зимбардо", "Бойд", "Сырцов", "Митина", "Осин", "Деси", "Райан",
           "Чен", "Ванстенкисте", "ВОЗ"]

# Слова про балл, шкалу и норму. «Баланс» тут же: «сбалансированный профиль» —
# это норма, а нормы на русской выборке у нас не замерено.
SCORE_WORDS = [
    "балл", "диапазон", "порог", "шкала", "шкале", "шкал", "норм", "баланс",
    "оптимальн", "эталон", "сумма", "суммарн", "индекс", "процент",
    "как и нужно", "должно быть", "у людей", "в пределах", "правильн",
]

# Оценка и похвала. Приятный ярлык примут не проверяя, и это хуже неприятного.
BAD_WORDS = [
    "мало", "много", "немного", "плохо", "низк", "высок", "средн", "слаб",
    "сильн", "просело", "перекос", "молодец", "отличн", "выражен", "ведущ",
    "запустил", "приговор", "зона работы", "снижать", "растить", "добрать",
]

# Упрёк на странице-переходе. Человек пришёл, чтобы перестать себя винить.
BLAME_WORDS = [
    "забыл", "забросил", "давно не", "пропустил", "поздно", "надо было",
    "жаль", "к сожалению", "ошибка", "неверн",
]

# Машинерия опросника на странице-переходе. Осталась — значит страница всё ещё
# может что-то посчитать и показать.
MACHINERY = [
    "QUESTIONS", "SCALE", "supabase", "fetch(", "localStorage",
    "addEventListener", "setTimeout", "<input", "<button", "<form", "Telegram",
]

# Подсчёт «правильного профиля» и вывод цифры. Пока он в файле — норму можно
# вернуть одной строкой шаблона.
NORM_MACHINERY = [
    "OPTIMAL", "verdict", "target", "renderRadarSVG", "renderTrendSVG",
    "barWidth", "result-need-val", "сбалансированн", "SCALE_META",
]

LATIN = re.compile(r"[A-Za-z]{2,}")
DIGIT = re.compile(r"\d")

# Целым словом: «ВОЗ» не должен ловиться внутри «нервозности».
AUTHOR_RE = [(a, re.compile(r"(?<![A-Za-zА-Яа-яЁё])" + a
                            + r"(?![A-Za-zА-Яа-яЁё])", re.I)) for a in AUTHORS]

TRAP = "ЦИФРАУТЕКЛА"


# --------------------------------------------------------------------------
# Запуск страницы в node
# --------------------------------------------------------------------------
# Заглушки: своя, а не общая. Странице нужны библиотека базы, Телеграм и DOM с
# памятью по id — шапка прогресса живёт вне блока страницы, и её человек тоже
# читает.
STUBS = r"""
globalThis.window = { location: { search: '?v=6&u=tg_777' } };
globalThis.localStorage = {
  _s: {},
  getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
  setItem(k, v) { this._s[k] = String(v); },
  removeItem(k) { delete this._s[k]; }
};
// DOM с памятью по id: один и тот же элемент отдаётся одним объектом, поэтому
// видно и то, что страница написала в шапку прогресса.
globalThis.EL = {};
globalThis.document = {
  getElementById(id) {
    if (!globalThis.EL[id]) {
      globalThis.EL[id] = { style: {}, innerHTML: '', textContent: '', value: '',
                            addEventListener() {}, setAttribute() {},
                            getAttribute() { return null; },
                            querySelectorAll() { return []; },
                            classList: { toggle() {}, add() {}, remove() {} } };
    }
    return globalThis.EL[id];
  },
  createElement() { return { style: {}, setAttribute() {}, select() {} }; },
  body: { appendChild() {}, removeChild() {} }
};
globalThis.window.scrollTo = function () {};
// Библиотека базы: цепочка вызовов та же, что у настоящей, отдаёт что положим.
globalThis.SB_ROWS = [];
globalThis.window.supabase = { createClient() {
  const q = { select() { return q; }, eq() { return q; }, order() { return q; },
              limit() { return Promise.resolve({ data: globalThis.SB_ROWS, error: null }); } };
  return { from() { return q; } };
}};
globalThis.SENT = [];
"""

TG = r"""
globalThis.window.Telegram = { WebApp: {
  initData: '', initDataUnsafe: {}, version: '7.0',
  ready() {}, expand() {}, close() {},
  isVersionAtLeast() { return true; },
  sendData(d) { globalThis.SENT.push(JSON.parse(String(d))); }
}};
"""

HELPERS = r"""
/** Пройти замер тем же путём, каким его проходит человек: свой ответ на каждое
 *  утверждение, потом отправка. Узор ответов — как в отпечатке записи. */
async function __pass(mode) {
  start();
  for (let i = 0; i < QUESTIONS.length; i++) {
    state.answers['q' + (i + 1)] = (mode === 'ровно') ? 3 : (1 + (i % 5));
  }
  state.questionIdx = QUESTIONS.length - 1;
  await finish();
  await new Promise(r => setTimeout(r, 20));
  return app.innerHTML;
}
"""


def ztpi_run(js: str, rows=None, telegram: bool = True) -> dict:
    """Исполнить страницу замера целиком и вернуть то, что собрал кусок JS.

    Смотреть надо на ЭКРАНЫ: человек читает собранный HTML, а не исходник.
    `rows` — история, которая приходит из базы: ею проверяется и сдвиг с прошлым
    разом, и утечка чисел истории на экран.
    """
    rows_js = "globalThis.SB_ROWS = %s;\n" % json.dumps(rows or [],
                                                        ensure_ascii=False)
    code = (STUBS + rows_js + (TG if telegram else "")
            + inline_script(ZTPI) + HELPERS
            + "\nconst OUT = {};\n(async function () {\n"
            + "  await new Promise(r => setTimeout(r, 30));\n" + js
            + "\n  OUT.progress = globalThis.EL.progressText.textContent;"
            + "\n  OUT.sent = globalThis.SENT;"
            + "\n  console.log('RESULT<' + JSON.stringify(OUT) + '>RESULT');"
            + "\n})();\n")
    return _node(code)


# Прошлый замер: цифры любые, важна только дата — она другая, значит сравнивать
# есть с чем.
def prev_row(value=1.0) -> dict:
    keys = ["past_negative", "past_positive", "present_hedonistic",
            "present_fatalistic", "future"]
    row = {"checkin_date": "2026-05-01",
           "completed_at": "2026-05-01T10:00:00.000Z"}
    row.update({k: value for k in keys})
    return row


SCREENS_JS = r"""
  OUT.s = {};
  OUT.s['вход'] = app.innerHTML;
  start();
  OUT.s['вопрос первый'] = app.innerHTML;
  state.questionIdx = QUESTIONS.length - 1;
  renderQuestion();
  OUT.s['вопрос последний'] = app.innerHTML;
  OUT.s['результат'] = await __pass('узор');
  showHistory();
  OUT.s['история'] = app.innerHTML;
"""

_CACHE: dict = {}


def screens(rows=None, telegram: bool = True) -> dict:
    """Экраны страницы. Считаются один раз: 56 утверждений в node небыстрые."""
    key = (json.dumps(rows or [], ensure_ascii=False), telegram)
    if key not in _CACHE:
        _CACHE[key] = ztpi_run(SCREENS_JS, rows=rows, telegram=telegram)
    return _CACHE[key]


_WORDS: list = []


def instrument_words() -> list:
    """Утверждения опросника и подписи вариантов — чужой текст, не наш.

    Их человек читает, пока отвечает, и они же возвращаются ему в «Что ты
    ответил». Менять их нельзя: правка утверждения — это правка инструмента.
    Зато и проверять в них нечего: ни аббревиатур, ни баллов там нет. Поэтому из
    видимого текста мы их вычитаем и смотрим на СВОИ формулировки.
    """
    global _WORDS
    if not _WORDS:
        got = ztpi_run("  OUT.w = QUESTIONS.concat(SCALE.map(s => s.label));")
        _WORDS = sorted(set(w for w in got["w"] if w and len(w) > 2),
                        key=len, reverse=True)
    return _WORDS


def own(h: str) -> str:
    """Видимый текст без утверждений опросника: только то, что написали мы."""
    text = visible(h)
    for w in instrument_words():
        if w in text:
            text = text.replace(w, " ")
    return text


def title(rel: str) -> str:
    m = re.search(r"<title>(.*?)</title>", html(rel), re.S | re.I)
    assert m, f"{rel}: нет заголовка окна"
    return m.group(1).strip()


STYLE_SCRIPT = re.compile(r"<(style|script)\b[^>]*>.*?</\1>", re.S | re.I)


def page_text(rel: str) -> str:
    """Текст страницы-перехода: без разметки, стилей и скрипта."""
    return visible(STYLE_SCRIPT.sub(" ", html(rel)))


def go(search: str, hash_: str) -> dict:
    """Открыть страницу-переход так, как её открывает человек.

    Телеграма в заглушках нет намеренно: переход обязан работать и в обычном
    браузере.
    """
    stubs = r"""
globalThis.OUT = {};
Object.defineProperty(globalThis, 'location', {
  configurable: true, writable: true,
  value: {
    search: %s, hash: %s, pathname: '/where/',
    replace: function (u) { OUT.replaced = String(u); },
    assign: function (u) { OUT.assigned = String(u); },
    set href(u) { OUT.href = String(u); },
    get href() { return '/where/'; }
  }
});
""" % (json.dumps(search), json.dumps(hash_))
    return _node(stubs + inline_script(WHERE)
                 + "\nconsole.log('RESULT<' + JSON.stringify(globalThis.OUT) + '>RESULT');\n")


# --------------------------------------------------------------------------
# Проверки страницы замера
# --------------------------------------------------------------------------
def check_no_latin() -> None:
    """1. В видимом тексте нет ни одного латинского слова."""
    parts = dict(screens()["s"])
    parts["шапка прогресса"] = screens()["progress"]
    parts["вне бота"] = screens(telegram=False)["s"]["результат"]
    for name, h in parts.items():
        found = sorted(set(LATIN.findall(own(h))))
        assert not found, f"{ZTPI}, экран «{name}»: латиница {found}"
    assert not LATIN.search(title(ZTPI)), \
        f"{ZTPI}: латиница в заголовке вкладки «{title(ZTPI)}»"
    ok("на странице замера ни одного латинского слова в тексте")


def check_no_authors() -> None:
    """2. Ни одной фамилии автора и ни одного русского сокращения шкалы."""
    for name, h in screens()["s"].items():
        hits = [a for a, rx in AUTHOR_RE if rx.search(own(h))]
        assert not hits, f"{ZTPI}, экран «{name}»: {hits}"
    ok("на странице замера нет ни фамилий, ни русских сокращений шкал")


def check_no_score_and_norm_words() -> None:
    """3. Ни слова про балл, шкалу, диапазон и норму."""
    parts = dict(screens()["s"])
    parts["шапка прогресса"] = screens()["progress"]
    parts["заголовок вкладки"] = title(ZTPI)
    for name, h in parts.items():
        low = own(h).lower()
        bad = [w for w in SCORE_WORDS if w in low]
        assert not bad, f"{ZTPI}, экран «{name}»: {bad}"
    ok("слов про балл, шкалу и норму на экранах нет")


def check_no_praise_no_blame() -> None:
    """4. Ни оценки, ни похвалы: приятный ярлык запрещён так же, как неприятный."""
    parts = dict(screens()["s"])
    parts["результат со сдвигом"] = screens(rows=[prev_row()])["s"]["результат"]
    for name, h in parts.items():
        low = own(h).lower()
        bad = [w for w in BAD_WORDS if w in low]
        assert not bad, f"{ZTPI}, экран «{name}»: {bad}"
    ok("на экранах нет ни оценки, ни похвалы")


def check_score_not_shown() -> None:
    """5. Цифра на экран не попадает — проверка ловушками.

    Подменяем числа замера и числа истории метками-ловушками. Так проверка не
    зависит от того, какое число получилось: если страница вообще берёт цифру,
    ловушка утечёт.
    """
    trap_row = {k: TRAP for k in prev_row()}
    trap_row["checkin_date"] = "2026-05-01"
    trap_row["completed_at"] = "2026-05-01T10:00:00.000Z"
    got = ztpi_run(r"""
  const orig = computeRecord;
  computeRecord = function () {
    const r = orig();
    ['past_negative', 'past_positive', 'present_hedonistic',
     'present_fatalistic', 'future'].forEach(k => { r[k] = 'ЦИФРАУТЕКЛА'; });
    return r;
  };
  OUT.s = {'результат': await __pass('узор')};
  showHistory();
  OUT.s['история'] = app.innerHTML;
""", rows=[trap_row])
    for name, h in got["s"].items():
        assert TRAP not in h, f"{ZTPI}, экран «{name}»: показывает {TRAP}"
    ok("страница не берёт на экран ни своё число, ни число из истории")

    for name, h in screens(rows=[prev_row()])["s"].items():
        if not name.startswith("результат"):
            continue
        text = own(h)
        assert not DIGIT.search(text), \
            f"{ZTPI}, экран «{name}»: цифра в тексте «{text.strip()[:200]}»"
    ok("на экране результата нет ни одной цифры")


def check_result_in_words() -> None:
    """6. Вместо балла — свои ответы, сдвиг с прошлого раза и первая точка."""
    first = screens()["s"]["результат"]
    text = visible(first)
    assert "точка отсчёта" in text, \
        f"{ZTPI}: на первом замере нет честной первой точки"
    got = ztpi_run("  OUT.label = SCALE[2].label;")
    assert got["label"] in text, \
        f"{ZTPI}: своего ответа «{got['label']}» на экране не видно"

    second = visible(screens(rows=[prev_row()])["s"]["результат"])
    assert "прошлый раз" in second, \
        f"{ZTPI}: на втором замере нет сдвига с прошлого раза"
    assert "точка отсчёта" not in second, \
        f"{ZTPI}: второй замер всё ещё зовётся точкой отсчёта"
    ok("результат словами: свои ответы, сдвиг с прошлого раза, первая точка")


def check_cannot_show_norm() -> None:
    """7. Сравнения с «правильным профилем» в странице больше нет.

    Пока подсчёт нормы лежит в файле, вернуть её на экран можно одной строкой
    шаблона. Норму без валидизации на русской выборке называть нельзя.
    """
    src = html(ZTPI)
    left = [w for w in NORM_MACHINERY if w in src]
    assert not left, f"{ZTPI}: в файле осталась машинерия нормы: {left}"
    ok("подсчёта «правильного профиля» в файле не осталось")


def check_write_unchanged() -> None:
    """8. Запись не изменилась: подпись действия, ключи, числа и ответы."""
    got = ztpi_run("  await __pass('узор');")
    sent = got["sent"]
    assert len(sent) == 1, f"{ZTPI}: ушло записей {len(sent)} вместо одной"
    assert sent[0].get("action") == ACTION, \
        f"{ZTPI}: подпись действия стала «{sent[0].get('action')}»"
    payload = dict(sent[0]["payload"])
    for k in ("checkin_date", "completed_at"):
        assert k in payload, f"{ZTPI}: из записи пропало поле «{k}»"
        payload.pop(k)
    assert sorted(payload) == sorted(FIELDS), \
        f"{ZTPI}: ключи записи стали {sorted(payload)}"
    assert len(payload["answers"]) == ANSWERS_COUNT, \
        f"{ZTPI}: в базу ушло ответов {len(payload['answers'])}"
    nums = {k: v for k, v in payload.items() if k != "answers"}
    blob = json.dumps(nums, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(blob.encode()).hexdigest()[:16]
    assert digest == DIGEST, (
        f"{ZTPI}: числа записи поехали (отпечаток {digest} вместо {DIGEST}). "
        f"Ключи и суммы менять нельзя — на них стоят контекст бота и выгрузки")
    ok("запись прежняя: подпись действия, ключи, числа и число ответов")


# --------------------------------------------------------------------------
# Проверки страницы-перехода
# --------------------------------------------------------------------------
def check_where_is_redirect() -> None:
    """9. Прежняя страница того же замера стала переходом, а не осталась второй."""
    assert (ROOT / WHERE).exists(), f"пропал старый адрес {WHERE}"
    dest = (ROOT / WHERE).parent / WHERE_TARGET
    assert dest.exists(), f"{WHERE}: цели перехода {WHERE_TARGET} нет"
    src = html(WHERE)
    left = [m for m in MACHINERY if m in src]
    assert not left, f"{WHERE}: осталась машинерия опросника: {left}"
    assert len(src) < 4000, \
        f"{WHERE}: страница на {len(src)} знаков — опросник так и не убран"
    ok("прежняя страница замера стала переходом и посчитать ничего не может")


def check_where_text_clean() -> None:
    """10. На переходе человек не видит ни шкалы, ни балла, ни упрёка."""
    text = page_text(WHERE)
    latin = sorted(set(LATIN.findall(text)))
    assert not latin, f"{WHERE}: латиница в тексте {latin}"
    assert not DIGIT.search(text), f"{WHERE}: цифра в тексте «{text.strip()}»"
    low = text.lower()
    bad = [w for w in SCORE_WORDS + BAD_WORDS if w in low]
    assert not bad, f"{WHERE}: {bad} в тексте"
    blame = [w for w in BLAME_WORDS if w in low]
    assert not blame, f"{WHERE}: упрёк в тексте: {blame}"
    t = title(WHERE)
    assert t and not LATIN.search(t) and not DIGIT.search(t), \
        f"{WHERE}: заголовок вкладки «{t}»"

    m = re.search(r"<noscript>(.*?)</noscript>", html(WHERE), re.S | re.I)
    assert m, f"{WHERE}: без скриптов человек не видит ничего"
    ns = visible(m.group(1))
    assert "устарел" in ns, f"{WHERE}: не сказано, что страница устарела"
    assert "Что со мной?" in ns, \
        f"{WHERE}: не сказано, что замеры теперь в кнопке «Что со мной?»"
    ok("на переходе честный текст: ни шкалы, ни балла, ни упрёка")


def check_where_keeps_user() -> None:
    """11. Переход доносит «u=tg_…» до актуальной страницы и уходит через replace."""
    got = go("?v=6&u=tg_777", "#itog")
    assert got.get("replaced") == f"{WHERE_TARGET}?v=6&u=tg_777#itog", \
        f"{WHERE}: перешли на «{got.get('replaced')}», хвост адреса потерян"
    assert "href" not in got and "assigned" not in got, \
        f"{WHERE}: страница уходит не только через replace: {got}"

    bare = go("", "")
    assert bare.get("replaced") == WHERE_TARGET, \
        f"{WHERE}: без параметров перешли на «{bare.get('replaced')}»"

    s = inline_script(WHERE)
    assert "location.replace" in s, \
        f"{WHERE}: уход не через replace — старый адрес останется в истории"
    assert "location.href" not in s and "location.assign" not in s, \
        f"{WHERE}: кроме replace есть другой способ ухода"
    for word in ("Telegram", "WebApp", "initData", "tg."):
        assert word not in s, f"{WHERE}: переход зависит от «{word}»"
    assert "setTimeout" not in s and "onload" not in s, \
        f"{WHERE}: переход отложен, человек успеет увидеть страницу"
    assert not WHERE_TARGET.startswith(("/", "http")), \
        f"{WHERE}: адрес цели «{WHERE_TARGET}» не относительный"
    ok("переход относительный, срабатывает сразу и доносит «u=tg_…»")


def check_where_target_is_live() -> None:
    """12. Цель перехода — страница, которую бот открывает сегодня."""
    dest = ((ROOT / WHERE).parent / WHERE_TARGET).resolve().relative_to(ROOT)
    addr = "/" + str(dest)
    bot_src = BOT.read_text(encoding="utf-8")
    catalog = html("kak-ty/app.html")
    assert addr in bot_src or addr in catalog, \
        f"{WHERE}: цель «{addr}» бот сегодня не открывает"
    ok("переход ведёт на страницу, которую бот открывает сегодня")


if __name__ == "__main__":
    raise SystemExit(run([
        check_no_latin, check_no_authors, check_no_score_and_norm_words,
        check_no_praise_no_blame, check_score_not_shown, check_result_in_words,
        check_cannot_show_norm, check_write_unchanged,
        check_where_is_redirect, check_where_text_clean,
        check_where_keeps_user, check_where_target_is_live,
    ]))
