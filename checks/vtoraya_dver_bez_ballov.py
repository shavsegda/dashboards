# -*- coding: utf-8 -*-
"""Проверки второй двери «Как я устроен»: человек не видит ни балла, ни шкалы.

Задача. В подвижном слое названия шкал и баллы убраны (`no_scales_no_scores.py`).
У второй двери — нет: на актуальных страницах человек читал «AQ: 32/50»,
«SQ-R 90/150 · EQ 40/80», «MEQ: 55 (16–86)», «средний балл 4.2/7», а во вкладке
браузера — название инструмента. Балл человек принимает как приговор, а ярлык
(«надёжный», «системщик», «высокий») — как утверждение о своём характере.
Конституция, принципы IV и V: сводных баллов нет, замер характер не описывает.

Что меняется и что НЕ меняется. Меняется только видимый текст. Запись в базу
остаётся прежней до последнего знака: блок, подпись инструмента, ключи полей и
сами числа. Строки `band` и `nums` тоже остаются в записи — их читает бот и по
ним собирается файл разбора; человеку они больше не показываются. Проверка 9
прибивает запись отпечатком: поехала хоть одна цифра — падает.

Что проверяем — на собранных ЭКРАНАХ, а не в исходнике:
  · в видимом тексте нет ни одного латинского слова (это и есть аббревиатуры
    инструментов) и ни одной фамилии автора;
  · нет слов про балл, шкалу, диапазон, порог и норму;
  · формулировки самого замера — без цифр, оценок и похвалы;
  · балл на экран не попадает: подменяем цифры и ярлык метками-ловушками;
  · строки записи `band` и `nums` на экране не появляются;
  · вместо балла человек читает свои ответы словами, сдвиг с прошлого раза и
    честную первую точку;
  · в нейротипе направление к специалисту сохранено — screen and refer;
  · запись в базу не изменилась: блок, инструмент, ключи и числа.

Запуск:  python3 checks/vtoraya_dver_bez_ballov.py
"""

import hashlib
import json
import re

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
from lib import (NODE_STUBS, RICH_DOM, ROOT, _node, html, inline_script, ok,
                 run, visible)

# --------------------------------------------------------------------------
# Страницы. Адреса — те, что бот открывает сегодня; прежние версии рядом уже
# превращены в страницы-переходы и проверяются в `starye_stranicy.py`.
# --------------------------------------------------------------------------
# Восемь страниц одного устройства: список тестов → вопросы → результат.
TPL_PAGES = [
    "attachment/app2.html",
    "decisions/app2.html",
    "interests/app.html",
    "motivators/app10.html",
    "nervsystem/app2.html",
    "neurotype/app11.html",
    "stressrisk/app2.html",
    "vulnerabilities/app2.html",
]
VALUES = "values/app8.html"                  # один сквозной проход по двум тестам
HEXACO = "personality-hexaco/app8.html"      # один тест на 240 пунктов
PAGES = TPL_PAGES + [VALUES, HEXACO]

# Запись в базу: блок · подпись инструмента · отпечаток чисел · ключи · размеры.
# Отпечаток снят с рабочего кода ДО правки текстов. Прибит руками: посчитать его
# из самой страницы значит согласиться с любым её состоянием, включая «полей не
# осталось». Ответы одинаковые: в каждой шкале берётся вариант по её середине.
RECORD = {
    "attachment/app2.html": (
        "attachment", "ECR-R", "d01e99c6b3c92d73", ["ecrr"], [36]),
    "decisions/app2.html": (
        "decisions", "REI + AOT + DUTCH", "1a5e9f5cc6526e4f",
        ["aot", "dutch", "rei"], [40, 11, 20]),
    "interests/app.html": (
        "interests", "O*NET Interest Profiler (RIASEC)", "fc22b97b03d6011f",
        ["riasec"], [60]),
    "motivators/app10.html": (
        "motivators", "RFQ + GCOS", "2459da7be49a922b",
        ["gcos", "rfq"], [11, 36]),
    "nervsystem/app2.html": (
        "nervsystem", "PTS (Стреляу)", "321344ddcde7e212", ["pts"], [134]),
    "neurotype/app11.html": (
        "neurotype", "ASRS-v1.1", "5271e85112970f37",
        ["adhd", "autism", "chrono", "es", "hsp"], [18, 50, 27, 19, 135]),
    "stressrisk/app2.html": (
        "stressrisk", "Brief COPE + DOSPERT + IUS-12", "64f2a50aa236923b",
        ["cope", "dospert", "ius"], [28, 30, 12]),
    "vulnerabilities/app2.html": (
        "vulnerabilities", "SD4 + PID-5-BF + FMPS", "98fce212704f40d0",
        ["fmps", "pid5bf", "sd4"], [28, 25, 35]),
    VALUES: ("values", "MFQ-30 + PVQ-RR", "37aea594f6cfc662",
             ["mfq", "schwartz"], [32, 57]),
    HEXACO: ("personality", "IPIP-HEXACO", "9b14ecaa8e8687eb",
             ["facets", "factors"], [240]),
}

# Фамилии авторов и русские сокращения инструментов из строк-источников.
# Латиницу ловит отдельная проверка, здесь то, что написано по-русски.
AUTHORS = [
    "Фрейли", "Уоллер", "Бреннан", "Пачини", "Эпстайн", "Барон", "Де Дрё",
    "Дрё", "Хиггинс", "Деси", "Райан", "Стреляу", "Данилов", "Шмелёв",
    "Шмелев", "Барон-Коэн", "Кембридж", "Арон", "Хорн-Остберг", "Уилрайт",
    "Карвер", "Блэ", "Вебер", "Карлтон", "Полхус", "Фрост", "Хайдт", "Грэм",
    "Носек", "Шварц", "Голланд", "ВОЗ", "Терман", "Кроненке", "Эдмондсон",
]

# Слова про балл, шкалу и норму. Проверяются на всех экранах: в пунктах
# опросников и в подписях вариантов их быть не может.
SCORE_WORDS = [
    "балл", "диапазон", "порог", "шкала", "шкале", "в норме", "выше нормы",
    "ниже нормы", "сумма", "суммарн", "индекс", "процент",
]

# Оценка и похвала в формулировках замера. Приятный ярлык запрещён так же, как
# неприятный: приятный примут не проверяя, и это хуже.
BAD_WORDS = [
    "балл", "диапазон", "норм", "мало", "много", "немного", "плохо", "низк",
    "высок", "средн", "слаб", "сильн", "устойчив", "молодец", "отличн",
    "выражен", "перевес", "ведущ", "ниже", "выше", "запустил", "у людей",
    "в пределах", "приговор",
]

LATIN = re.compile(r"[A-Za-z]{2,}")
DIGIT = re.compile(r"\d")

# Целым словом: «Барон» не должен ловиться внутри «Барометра», «ВОЗ» — внутри
# «нервозности».
AUTHOR_RE = [(a, re.compile(r"(?<![A-Za-zА-Яа-яЁё])" + a
                            + r"(?![A-Za-zА-Яа-яЁё])", re.I)) for a in AUTHORS]

TRAP_NUM = "ЦИФРАУТЕКЛА"
TRAP_BAND = "ЯРЛЫКУТЁК"


# --------------------------------------------------------------------------
# Запуск страницы в node
# --------------------------------------------------------------------------
# Выбор варианта по ПОЛОЖЕНИЮ в шкале: не зависит от того, какие в ней числа.
PICK = r"""
function __pick(opts, mode) {
  if (mode === 'max') return opts.reduce((a, b) => (b.v > a.v ? b : a));
  if (mode === 'min') return opts.reduce((a, b) => (b.v < a.v ? b : a));
  return opts[Math.floor(opts.length / 2)];
}
// Ловушки вместо чисел и ярлыка. Так проверка не зависит от того, какое число
// получилось: если страница вообще берёт цифру или ярлык, ловушка утечёт.
function __trapLeaf(v) {
  if (typeof v === 'boolean') return v;          // им гейтится «к специалисту»
  if (typeof v === 'number') return '""" + TRAP_NUM + r"""';
  if (typeof v === 'string') return '""" + TRAP_BAND + r"""';
  if (v && typeof v === 'object') {
    const out = Array.isArray(v) ? [] : {};
    Object.keys(v).forEach(k => { out[k] = __trapLeaf(v[k]); });
    return out;
  }
  return v;
}
function __trapResult(r) {
  return {band: {t: '""" + TRAP_BAND + r"""', c: (r.band && r.band.c) || 'neu'},
          nums: '""" + TRAP_NUM + r"""', data: __trapLeaf(r.data || {})};
}
"""

TPL_HELPERS = PICK + r"""
function __answer(t, mode) {
  answers[t.key] = {};
  t.items.forEach((it, i) => { answers[t.key][i] = __pick(it.opts || t.scale, mode).v; });
}
function __trap() {
  TESTS.forEach(t => { const orig = t.score; t.score = (a) => __trapResult(orig(a)); });
}
/** Заставить скрин сработать (или не сработать) независимо от порога: проверяем
 *  не сам порог — его мы не меняли, — а что направление к специалисту на месте. */
let __POS = null;
function __force(keys, v) {
  __POS = v;
  keys.forEach(k => {
    const t = TESTS.find(x => x.key === k);
    if (t.__wrapped) return;
    const orig = t.score;
    t.score = (a) => {
      const r = orig(a);
      return __POS === null ? r
        : Object.assign({}, r, {data: Object.assign({}, r.data, {positive: __POS})});
    };
    t.__wrapped = true;
  });
}
/** Пройти все тесты страницы тем же путём, каким их проходит человек. */
async function __pass(mode, into) {
  for (const t of TESTS) {
    __answer(t, mode);
    await finishTest(t);
    into[t.key] = app.innerHTML;
  }
}
"""

VAL_HELPERS = PICK + r"""
function __answer(t, mode) {
  answers[t.key] = {};
  t.items.forEach((it, i) => { answers[t.key][i] = __pick(it.opts || t.scale, mode).v; });
}
function __trap() {
  TESTS.forEach(t => { const orig = t.score; t.score = (a) => __trapResult(orig(a)); });
}
async function __pass(mode) {
  TESTS.forEach(t => __answer(t, mode));
  pos = FLAT.length;
  await finish();
  return app.innerHTML;
}
"""

HEX_HELPERS = PICK + r"""
// Форма ответа тут другая: {factors, facets}. Ловушки кладём в те же поля.
function __trap() {
  const orig = score;
  score = () => { const r = orig();
                  return {factors: __trapLeaf(r.factors), facets: __trapLeaf(r.facets)}; };
}
async function __pass(mode) {
  ITEMS.forEach((it, i) => { answers[i] = __pick(LIKERT, mode).v; });
  idx = ITEMS.length;
  await renderFinish();
  return app.innerHTML;
}
"""

HELPERS = {**{p: TPL_HELPERS for p in TPL_PAGES},
           VALUES: VAL_HELPERS, HEXACO: HEX_HELPERS}


def page_run(rel: str, js: str) -> dict:
    """Исполнить страницу целиком и вернуть то, что собрал переданный кусок JS.

    Смотреть надо на ЭКРАНЫ: человек читает собранный HTML, а не исходник.
    Заглушки подменяют браузер, сеть и Телеграм, поэтому запись доходит до конца
    и виден настоящий экран результата, а не «Сохраняю…».
    """
    extra = ""
    if rel == HEXACO:
        # Банк пунктов лежит отдельным файлом и подключён тегом со `src`.
        extra = (ROOT / "personality-hexaco" / "items.js").read_text(
            encoding="utf-8")
    code = (NODE_STUBS + RICH_DOM + extra + inline_script(rel) + HELPERS[rel]
            + "\nconst OUT = {};\n(async function () {\n"
            + "  await new Promise(r => setTimeout(r, 30));\n" + js
            + "\n  console.log('RESULT<' + JSON.stringify(OUT) + '>RESULT');"
            + "\n})();\n")
    return _node(code)


# Все экраны страницы: вход, вопросы, результат каждого теста, сводка.
TPL_SCREENS = r"""
  OUT.s = {'вход': app.innerHTML};
  TESTS.forEach((t, i) => { cur = {ti: i, pos: 0}; renderQuestion();
                            OUT.s['вопрос ' + t.key] = app.innerHTML; });
  const first = {}; await __pass('mid', first);
  Object.keys(first).forEach(k => { OUT.s['результат ' + k] = first[k]; });
  renderHub(); OUT.s['список после'] = app.innerHTML;
  renderResults(); OUT.s['сводка'] = app.innerHTML;
"""

VAL_SCREENS = r"""
  OUT.s = {'вход': app.innerHTML};
  [0, FLAT.length - 1].forEach(p => { pos = p; renderQuestion();
                                      OUT.s['вопрос ' + p] = app.innerHTML; });
  OUT.s['результат'] = await __pass('mid');
"""

HEX_SCREENS = r"""
  OUT.s = {'вход': app.innerHTML};
  idx = 0; render(); OUT.s['вопрос'] = app.innerHTML;
  OUT.s['результат'] = await __pass('mid');
"""

SCREENS_JS = {**{p: TPL_SCREENS for p in TPL_PAGES},
              VALUES: VAL_SCREENS, HEXACO: HEX_SCREENS}

_CACHE: dict = {}


def screens(rel: str) -> dict:
    """Экраны страницы. Считаются один раз: node на 240 пунктов небыстрый."""
    if rel not in _CACHE:
        _CACHE[rel] = page_run(rel, SCREENS_JS[rel])["s"]
    return _CACHE[rel]


def texts(rel: str) -> list:
    """Формулировки замера: название, «что это даст», пометка, рамка.

    Плюс рамки самой страницы: их человек читает на каждом экране. Отдаём
    тройками «тест · поле · текст»: цифра в «пометке» бывает честной («последние
    полгода»), а в названии и в рамке — нет.
    """
    js = ("  OUT.t = [['страница', 'название', PAGE_TITLE],"
          " ['страница', 'подпись', PAGE_SUB],"
          " ['страница', 'рамка', PAGE_FRAME]];")
    if rel != HEXACO:
        js += r"""
  TESTS.forEach(t => {
    OUT.t.push([t.key, 'название', t.title]);
    OUT.t.push([t.key, 'что даст', t.what || '']);
    OUT.t.push([t.key, 'пометка', t.note || '']);
    OUT.t.push([t.key, 'рамка', t.frame || '']);
  });
"""
    return page_run(rel, js)["t"]


_WORDS: dict = {}


def instrument_words(rel: str) -> list:
    """Пункты опросника и подписи вариантов — чужой текст, не наш.

    Их человек читает, пока отвечает, и они же возвращаются ему в «Твоих
    ответах». Менять их нельзя: правка пункта — это правка инструмента. Зато и
    проверять в них нечего: там нет ни аббревиатур шкал, ни баллов. Поэтому из
    видимого текста мы их вычитаем и смотрим на СВОИ формулировки.
    """
    if rel not in _WORDS:
        js = (r"""
  OUT.w = [];
  ITEMS.forEach(it => OUT.w.push(it.t));
  LIKERT.forEach(o => OUT.w.push(o.l));
""" if rel == HEXACO else r"""
  OUT.w = [];
  TESTS.forEach(t => t.items.forEach(it => {
    OUT.w.push(it.t);
    if (it.ctx) OUT.w.push(it.ctx);
    (it.opts || t.scale || []).forEach(o => OUT.w.push(o.l || ''));
  }));
""")
        got = [w for w in page_run(rel, js)["w"] if w and len(w) > 2]
        _WORDS[rel] = sorted(set(got), key=len, reverse=True)
    return _WORDS[rel]


def own(rel: str, h: str) -> str:
    """Видимый текст без пунктов опросника: только то, что написали мы сами."""
    text = visible(h)
    for w in instrument_words(rel):
        if w in text:
            text = text.replace(w, " ")
    return text


def title(rel: str) -> str:
    m = re.search(r"<title>(.*?)</title>", html(rel), re.S | re.I)
    assert m, f"{rel}: нет заголовка окна"
    return m.group(1).strip()


# --------------------------------------------------------------------------
# Проверки
# --------------------------------------------------------------------------
def check_no_latin() -> None:
    """1. В видимом тексте нет ни одного латинского слова."""
    for rel in PAGES:
        for name, h in screens(rel).items():
            found = sorted(set(LATIN.findall(own(rel, h))))
            assert not found, f"{rel}, экран «{name}»: латиница {found}"
        assert not LATIN.search(title(rel)), \
            f"{rel}: латиница в заголовке вкладки «{title(rel)}»"
    ok(f"на {len(PAGES)} страницах ни одного латинского слова в тексте")


def check_no_authors() -> None:
    """2. Ни одной фамилии автора и ни одного русского сокращения шкалы."""
    for rel in PAGES:
        for name, h in screens(rel).items():
            text = own(rel, h)
            hits = [a for a, rx in AUTHOR_RE if rx.search(text)]
            assert not hits, f"{rel}, экран «{name}»: {hits}"
    ok("на десяти страницах нет ни фамилий, ни русских сокращений шкал")


def check_no_score_words() -> None:
    """3. Ни слова про балл, шкалу, диапазон, порог и норму."""
    for rel in PAGES:
        for name, h in screens(rel).items():
            low = own(rel, h).lower()
            bad = [w for w in SCORE_WORDS if w in low]
            assert not bad, f"{rel}, экран «{name}»: {bad}"
    ok("слов про балл, шкалу и норму на экранах нет")


def check_texts_clean() -> None:
    """4. Формулировки замера: без цифр, без оценок и без похвалы.

    Рамка — то, что человек читает вместо ярлыка. Значит в ней не может быть ни
    оценки, ни похвалы: приятный ярлык примут не проверяя, и это хуже.
    """
    for rel in PAGES:
        assert not DIGIT.search(title(rel)), \
            f"{rel}: цифра в заголовке вкладки «{title(rel)}»"
        got = texts(rel)
        empty = [k for k, f, t in got if f == "рамка" and not t.strip()]
        assert not empty, \
            f"{rel}: нет рамки у {empty} — человеку нечего читать вместо ярлыка"
        for key, field, line in got:
            low = line.lower()
            bad = [w for w in BAD_WORDS if w in low]
            assert not bad, f"{rel}, «{key}» / {field}: {bad} в «{line}»"
            assert not LATIN.search(line), \
                f"{rel}, «{key}» / {field}: латиница в «{line}»"
            if field in ("название", "подпись", "рамка"):
                assert not DIGIT.search(line), \
                    f"{rel}, «{key}» / {field}: цифра в «{line}»"
    ok("формулировки замеров чистые: ни цифр, ни оценок, ни похвалы")


def check_score_not_shown() -> None:
    """5. Балл и ярлык на экран не попадают — проверка ловушками."""
    js = {
        **{p: "  __trap();\n" + TPL_SCREENS for p in TPL_PAGES},
        VALUES: "  __trap();\n" + VAL_SCREENS,
        HEXACO: "  __trap();\n" + HEX_SCREENS,
    }
    for rel in PAGES:
        got = page_run(rel, js[rel])["s"]
        for name, h in got.items():
            for trap in (TRAP_NUM, TRAP_BAND):
                assert trap not in h, \
                    f"{rel}, экран «{name}»: показывает {trap}"
    ok("ни одна страница не берёт на экран ни цифру, ни ярлык подсчёта")


def check_band_and_nums_not_shown() -> None:
    """6. Строки записи `band` и `nums` человеку не показываются.

    Они остаются в базе — их читает бот и по ним собирается разбор. Но это
    утверждения о характере и суммы ответов, и на экране им места нет.
    """
    js = {
        **{p: TPL_SCREENS + "\n  OUT.rec = combinedScores();" for p in TPL_PAGES},
        VALUES: VAL_SCREENS + r"""
  OUT.rec = {};
  TESTS.forEach(t => { const r = t.score(answers[t.key]);
                       OUT.rec[t.key] = {band: r.band.t, nums: r.nums}; });
""",
    }
    for rel in TPL_PAGES + [VALUES]:
        got = page_run(rel, js[rel])
        for key, s in got["rec"].items():
            for field in ("band", "nums"):
                val = (s.get(field) or "").strip()
                if not val:
                    continue
                for name, h in got["s"].items():
                    assert val not in visible(h), \
                        (f"{rel}, экран «{name}»: показывает «{field}» "
                         f"теста «{key}»: {val}")
    ok("ярлык и сумма ответов остались в базе, но не на экране")


def check_result_in_words() -> None:
    """7. Вместо балла — свои ответы, сдвиг с прошлого раза и первая точка."""
    js = {
        **{p: r"""
  const first = {}; await __pass('mid', first);
  OUT.first = first;
  OUT.answer = {};
  TESTS.forEach(t => { const it = t.items[0];
    OUT.answer[t.key] = __pick(it.opts || t.scale, 'mid').l; });
  const second = {}; await __pass('max', second);
  OUT.second = second;
""" for p in TPL_PAGES},
        VALUES: r"""
  OUT.first = {все: await __pass('mid')};
  OUT.answer = {все: __pick(TESTS[0].items[0].opts || TESTS[0].scale, 'mid').l};
  OUT.second = {все: await __pass('max')};
""",
        HEXACO: r"""
  OUT.first = {все: await __pass('mid')};
  OUT.answer = {все: __pick(LIKERT, 'mid').l};
  OUT.second = {все: await __pass('max')};
""",
    }
    for rel in PAGES:
        got = page_run(rel, js[rel])
        for key, h in got["first"].items():
            text = visible(h)
            assert "точка отсчёта" in text, \
                f"{rel}, «{key}»: на первом замере нет честной первой точки"
            assert got["answer"][key] in text, \
                f"{rel}, «{key}»: своего ответа «{got['answer'][key]}» не видно"
        for key, h in got["second"].items():
            text = visible(h)
            assert "прошлый раз" in text, \
                f"{rel}, «{key}»: на втором замере нет сдвига с прошлого раза"
            assert "точка отсчёта" not in text, \
                f"{rel}, «{key}»: второй замер всё ещё зовётся точкой отсчёта"
    ok("на всех страницах результат словами: ответы, сдвиг, первая точка")


def check_neurotype_still_refers() -> None:
    """8. Нейротип: скрин сработал — человека по-прежнему ведут к специалисту."""
    rel = "neurotype/app11.html"
    got = page_run(rel, r"""
  const SCREENS = ['adhd', 'autism', 'hsp'];
  __force(SCREENS, true);
  const hi = {}; await __pass('mid', hi);
  __force(SCREENS, false);
  const lo = {}; await __pass('mid', lo);
  OUT.hi = hi; OUT.lo = lo;
  OUT.hub = (function () { renderHub(); return app.innerHTML; })();
  OUT.svodka = (function () { renderResults(); return app.innerHTML; })();
""")
    for key in ("adhd", "autism", "hsp"):
        text = visible(got["hi"][key]).lower()
        assert "специалист" in text or "врач" in text, \
            f"{rel}, «{key}»: выраженные черты никуда не направляют"
    ok("выраженные черты по скрину ведут к специалисту")

    low = visible(got["hub"]).lower()
    assert "не диагноз" in low, f"{rel}: со списка ушло «это не диагноз»"
    ok("на списке скринов осталось «это не диагноз»")

    for key in ("adhd", "autism", "hsp"):
        text = visible(got["lo"][key]).lower()
        assert "диагноз" not in text.replace("не диагноз", ""), \
            f"{rel}, «{key}»: спокойный результат всё равно говорит про диагноз"
    ok("спокойный результат диагнозов не называет")


def check_write_keys_unchanged() -> None:
    """9. Запись в базу не изменилась: блок, инструмент, ключи и числа."""
    js = {
        **{p: r"""
  TESTS.forEach(t => __answer(t, 'mid'));
  await pushCombined();
  const last = PUSHED[PUSHED.length - 1].body;
  OUT.rec = {block: last.block, instrument: last.instrument,
             scores: last.scores,
             sizes: TESTS.map(t => Object.keys(last.answers[t.key] || {}).length),
             keys: TESTS.map(t => t.key)};
""" for p in TPL_PAGES},
        VALUES: r"""
  await __pass('mid');
  const last = PUSHED[PUSHED.length - 1].body;
  OUT.rec = {block: last.block, instrument: last.instrument,
             scores: last.scores,
             sizes: TESTS.map(t => Object.keys(last.answers[t.key] || {}).length),
             keys: TESTS.map(t => t.key)};
""",
        HEXACO: r"""
  await __pass('mid');
  const last = PUSHED[PUSHED.length - 1].body;
  OUT.rec = {block: last.block, instrument: last.instrument,
             scores: last.scores,
             sizes: [Object.keys(last.answers || {}).length],
             keys: ['hexaco']};
""",
    }
    for rel in PAGES:
        block, instrument, digest, keys, sizes = RECORD[rel]
        rec = page_run(rel, js[rel])["rec"]
        assert rec["block"] == block, \
            f"{rel}: блок базы стал «{rec['block']}» вместо «{block}»"
        assert rec["instrument"] == instrument, \
            f"{rel}: подпись инструмента стала «{rec['instrument']}»"
        assert sorted(rec["scores"]) == sorted(keys), \
            f"{rel}: ключи записи стали {sorted(rec['scores'])}"
        assert sorted(rec["sizes"]) == sorted(sizes), \
            f"{rel}: в базу ушло ответов {sorted(rec['sizes'])} вместо {sorted(sizes)}"
        blob = json.dumps(rec["scores"], sort_keys=True, ensure_ascii=False)
        got = hashlib.sha256(blob.encode()).hexdigest()[:16]
        assert got == digest, (
            f"{rel}: числа записи поехали (отпечаток {got} вместо {digest}). "
            f"Ключи и суммы менять нельзя — на них стоят панели бота и выгрузки")
    ok("запись в базу прежняя: блоки, подписи, ключи и числа не поехали")


if __name__ == "__main__":
    raise SystemExit(run([
        check_no_latin, check_no_authors, check_no_score_words,
        check_texts_clean, check_score_not_shown,
        check_band_and_nums_not_shown, check_result_in_words,
        check_neurotype_still_refers, check_write_keys_unchanged,
    ]))
