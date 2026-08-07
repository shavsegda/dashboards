# -*- coding: utf-8 -*-
"""Проверки: человек не видит ни названия шкалы, ни балла.

Задача. На страницах-опросниках человек читал «PHQ-9 (Kroenke…)» и «Настроение
22 · Диапазон 0–27». Балл он принимает как приговор, хотя это просто сумма его
ответов. Правила мини-аппов, часть 4: ни аббревиатуры, ни фамилии автора, ни
балла, ни диапазона, ни слова про нормы в видимом тексте быть не должно.

Что проверяем — на собранных ЭКРАНАХ, а не в исходнике:
  · в видимом тексте нет ни одного латинского слова (это и есть все аббревиатуры
    инструментов) и ни одной фамилии автора;
  · балл не показывается: подменяем цифру и диапазон метками-ловушками и смотрим,
    не утекли ли они на экран;
  · вместо балла человек читает свои ответы, сдвиг с прошлого раза и честную
    первую точку;
  · в формулировках самого замера нет цифр, слов про нормы и оценочных слов;
  · тяжёлый результат по-прежнему отправляет к специалисту;
  · ключи записи в базу не поехали — сверяем с `bot.py`.

Запуск:  python3 checks/no_scales_no_scores.py
"""

import re

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
from lib import app_run, block_paths, bot, dig, html, ok, run, visible

# Страницы подвижного слоя, которые человек проходит формой.
# Адреса — те, что стоят в `bot.py` и в каталоге «Как ты?». Старые версии
# (app.html, app2.html рядом) не подключены никуда и сюда не входят.
PAGES = [
    "state-week/app4.html",
    "state-month/app3.html",
    "state-clinical/app.html",
    "state-year/app.html",
    "state-team/app.html",
    "state-needs/app.html",
    "state-quarter/app3.html",
    "selfhood/app.html",
]

# Суточная страница устроена иначе: там человек сам ставит свои цифры, и они же
# и есть его ответ. Балла-суммы там нет вовсе, поэтому она проверяется только на
# латиницу в видимом тексте.
DAY_PAGE = "state-day/app.html"

# Ключи полей записи — как есть сегодня. Прибиты руками: посчитать их из самого
# файла значит согласиться с любым его состоянием, включая «полей не осталось».
FIELDS = {
    "state-week/app4.html": {
        "panas": ["pa", "na"], "vitality": ["mean"],
        "gate": ["phq", "gad", "alert"], "flow": ["value"], "couple": ["sum"],
    },
    "state-month/app3.html": {"pss": ["total"], "isi": ["total", "alert"]},
    "state-clinical/app.html": {
        "phq": ["total", "item9", "item9_flag", "alert"],
        "gad": ["total", "alert"], "asrm": ["total", "alert"],
    },
    "state-year/app.html": {
        "audit": ["total", "alert", "threshold", "sex_asked"]},
    "state-team/app.html": {"safety": ["mean"]},
    "state-needs/app.html": {"bpnsfs": [
        "autonomy_satisfaction", "autonomy_frustration",
        "competence_satisfaction", "competence_frustration",
        "relatedness_satisfaction", "relatedness_frustration",
        "satisfaction", "frustration"]},
    "state-quarter/app3.html": {
        "swls": ["sum"], "mlq": ["presence", "search"],
        "ffmq": ["mean", "observe", "describe", "act_aware", "nonjudge",
                 "nonreact"],
        "rses": ["sum"],
        "olbi": ["exhaustion", "disengagement", "exhaustion_sum",
                 "disengagement_sum"],
        "support": ["significant_other", "family", "friends"],
    },
    "selfhood/app.html": {
        "clarity": ["mean", "sum"],
        "authenticity": ["authentic_living", "self_alienation",
                         "external_influence"],
        "identity": ["commitment", "identification", "rumination",
                     "exploration_breadth", "exploration_depth"],
        "iposition": ["mean", "sum"],
    },
}

# Блок базы у каждой страницы. Поехал блок — панели бота смотрят в пустоту.
BLOCKS = {
    "state-week/app4.html": "state_week",
    "state-month/app3.html": "state_month",
    "state-clinical/app.html": "state_clinical",
    "state-year/app.html": "state_year",
    "state-team/app.html": "state_team",
    "state-needs/app.html": "state_needs",
    "state-quarter/app3.html": "state_quarter",
    "selfhood/app.html": "selfhood",
}

# Расхождение с `bot.py`, которое было до этой работы и остаётся: недельный
# мини-апп пишет «couple.sum», а бот читает «couple.total». Записано, чтобы
# проверка падала, если список расхождений изменится в любую сторону.
KNOWN_MISMATCH = {"state_week": {"couple.total"}}

# Фамилии и русские сокращения инструментов из строк-источников. Латиницу ловит
# отдельная проверка, здесь то, что написано по-русски.
AUTHORS = [
    "ШПАНА", "ШВС", "Осин", "Абабков", "Минздрав", "Леонтьев", "Елшанский",
    "Голубев", "Дорошева", "Смирнов", "Сирота", "Ялтонский", "Чистопольская",
    "Вдовенко", "Щебетенко", "Старовойтенко", "Нартова", "Резниченко",
    "Малтби", "Борисенко", "Томпсон", "Коэн", "ВОЗ", "клинрекоменд",
]

# Слова, которых не должно быть в формулировках самого замера: балл, диапазон,
# норма и оценка. Похвала запрещена так же, как порицание.
BAD_WORDS = [
    "балл", "диапазон", "норм", "мало", "много", "немного", "плохо", "низк",
    "высок", "средн", "запустил", "молодец", "в пределах", "у людей",
]

LATIN = re.compile(r"[A-Za-z]{2,}")

# Целым словом: «ВОЗ» не должно ловиться внутри «нервозности».
AUTHOR_RE = [(a, re.compile(r"(?<![A-Za-zА-Яа-яЁё])" + a + r"(?![A-Za-zА-Яа-яЁё])",
                            re.I)) for a in AUTHORS]


def screens(rel: str) -> dict:
    """Собрать все экраны страницы: список, первый вопрос, результаты.

    Ответы даём средним значением шкалы — как человек, который просто отвечает.
    """
    js = r"""
  OUT.hub = app.innerHTML;
  OUT.q = (function () { startTest(TESTS[0].key); return app.innerHTML; })();
  OUT.results = {};
  for (const t of TESTS) { OUT.results[t.key] = await __pass(t.key, 2); }
  OUT.all = (function () { renderAllResults(); return app.innerHTML; })();
  OUT.labels = {};
  for (const t of TESTS) { OUT.labels[t.key] = results[t.key].nums.map(n => n.l); }
"""
    return app_run(rel, js)


def check_no_latin() -> None:
    """1. В видимом тексте нет ни одного латинского слова."""
    for rel in PAGES + [DAY_PAGE]:
        if rel == DAY_PAGE:
            got = app_run(rel, "OUT.hub = app.innerHTML;")
            parts = {"форма": got["hub"]}
        else:
            s = screens(rel)
            parts = {"список": s["hub"], "вопрос": s["q"],
                     "все результаты": s["all"]}
            parts.update({f"результат {k}": v for k, v in s["results"].items()})
        for name, h in parts.items():
            found = sorted(set(LATIN.findall(visible(h))))
            assert not found, f"{rel}, экран «{name}»: латиница {found}"
    ok(f"на {len(PAGES) + 1} страницах ни одного латинского слова в тексте")


def check_no_authors() -> None:
    """2. Ни одной фамилии автора и ни одного русского сокращения шкалы."""
    for rel in PAGES:
        s = screens(rel)
        parts = {"список": s["hub"], "вопрос": s["q"], "все": s["all"]}
        parts.update({f"результат {k}": v for k, v in s["results"].items()})
        for name, h in parts.items():
            text = visible(h)
            hits = [a for a, rx in AUTHOR_RE if rx.search(text)]
            assert not hits, f"{rel}, экран «{name}»: {hits}"
    ok("на восьми страницах нет ни фамилий, ни русских сокращений шкал")


def check_score_not_shown() -> None:
    """3. Балл и диапазон на экран не попадают.

    Подменяем цифру и диапазон метками-ловушками и смотрим, не появились ли они
    на экране. Так проверка не зависит от того, какое число получилось: если
    страница вообще берёт `n.v` или `n.range`, ловушка утечёт.
    """
    js = r"""
  OUT.leaks = {};
  for (const t of TESTS) {
    await __pass(t.key, 2);
    results[t.key].nums = results[t.key].nums.map(n => ({
      l: n.l, v: 'ЦИФРАУТЕКЛА', range: 'ДИАПАЗОНУТЁК'
    }));
    renderResult(t.key);
    OUT.leaks[t.key] = app.innerHTML;
  }
  renderAllResults();
  OUT.leaks['все результаты'] = app.innerHTML;
"""
    for rel in PAGES:
        got = app_run(rel, js)
        for name, h in got["leaks"].items():
            for trap in ("ЦИФРАУТЕКЛА", "ДИАПАЗОНУТЁК"):
                assert trap not in h, \
                    f"{rel}, экран «{name}»: показывает {trap}"
            for cls in ("result-val", "result-norm", "Диапазон"):
                assert cls not in h, f"{rel}, экран «{name}»: остался «{cls}»"
    ok("ни одна страница не показывает цифру балла и диапазон")


def check_result_in_words() -> None:
    """4. Вместо балла — свои ответы, сдвиг с прошлого раза и первая точка."""
    js = r"""
  OUT.first = {}; OUT.second = {}; OUT.answer = {};
  for (const t of TESTS) {
    const scale = t.items[0].scale || t.scale;
    const low = scale[0].v, high = scale[scale.length - 1].v;
    OUT.first[t.key] = await __pass(t.key, low);
    OUT.answer[t.key] = (scale.find(s => s.v === low) || scale[0]).l;
    OUT.second[t.key] = await __pass(t.key, high);
  }
"""
    for rel in PAGES:
        got = app_run(rel, js)
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


def check_bands_clean() -> None:
    """5. В формулировках замера нет цифр, норм и оценочных слов.

    Прогоняем каждый подсчёт по ВСЕМ значениям шкалы: формулировок много, и
    плохая может лежать в редкой ветке.
    """
    js = r"""
  OUT.bands = [];
  for (const t of TESTS) {
    const scale = t.items[0].scale || t.scale;
    for (const s of scale) {
      OUT.bands.push([t.key, SCORERS[t.key](__answers(t.key, s.v)).band]);
    }
    if (t.filter) OUT.bands.push([t.key, t.filter.skipBand]);
  }
  OUT.texts = TESTS.map(t => [t.key, [t.title, t.what, t.note, t.window || ''].join(' · ')]);
"""
    for rel in PAGES:
        got = app_run(rel, js)
        for key, band in got["bands"] + got["texts"]:
            low = (band or "").lower()
            bad = [w for w in BAD_WORDS if w in low]
            assert not bad, f"{rel}, «{key}»: {bad} в «{band}»"
            if band and band not in [t[1] for t in got["texts"]]:
                assert not re.search(r"\d", band), \
                    f"{rel}, «{key}»: цифра в формулировке «{band}»"
    ok("формулировки чистые: ни цифр, ни норм, ни оценок")


def check_labels_clean() -> None:
    """6. Названия линий человеку — без сокращений шкал и без слова «сумма»."""
    for rel in PAGES:
        for key, labels in screens(rel)["labels"].items():
            for lab in labels:
                low = lab.lower()
                score_words = [w for w in ("сумма", "уровень", "средн", "балл")
                               if w in low]
                assert not score_words, \
                    f"{rel}, «{key}»: название линии «{lab}» говорит про балл"
                assert not LATIN.search(lab), \
                    f"{rel}, «{key}»: в названии линии «{lab}» латиница"
    ok("названия линий человеческие")


def check_alert_still_refers() -> None:
    """7. Тяжёлый результат по-прежнему отправляет к специалисту."""
    js = r"""
  OUT.high = {};
  for (const t of TESTS) {
    const scale = t.items[0].scale || t.scale;
    OUT.high[t.key] = await __pass(t.key, scale[scale.length - 1].v);
  }
"""
    for rel, keys in (("state-clinical/app.html", ["phq", "gad", "asrm"]),
                      ("state-month/app3.html", ["isi"]),
                      ("state-year/app.html", ["audit"])):
        got = app_run(rel, js)
        for key in keys:
            text = visible(got["high"][key]).lower()
            assert "врач" in text or "специалист" in text, \
                f"{rel}, «{key}»: тяжёлый результат никуда не направляет"
    ok("тяжёлый результат ведёт к врачу или специалисту")

    got = app_run("state-clinical/app.html", js)
    text = visible(got["high"]["phq"])
    assert "989-50-50" in text, "пропала круглосуточная линия помощи"
    ok("при отмеченном пункте про вред себе линия помощи на месте")


def check_write_keys_unchanged() -> None:
    """8. Ключи записи в базу не поехали — сверка с `bot.py`."""
    b = bot()
    js = r"""
  for (const t of TESTS) { await __pass(t.key, 2); }
  const last = PUSHED[PUSHED.length - 1].body;
  OUT.block = last.block;
  OUT.instrument = last.instrument;
  OUT.scores = last.scores;
  OUT.answered = Object.keys(last.answers);
"""
    for rel in PAGES:
        got = app_run(rel, js)
        assert got["block"] == BLOCKS[rel], \
            f"{rel}: блок базы стал «{got['block']}»"
        assert got["instrument"], f"{rel}: пропала подпись инструмента в записи"
        assert got["scores"].get("source") == "manual", \
            f"{rel}: пропала метка источника записи"
        for key, fields in FIELDS[rel].items():
            # Прошлый результат живёт в памяти телефона и в базу не уходит:
            # иначе каждая точка тащила бы за собой предыдущую.
            assert "prev" not in (got["scores"].get(key) or {}), \
                f"{rel}, «{key}»: прошлый результат уехал в запись"
            got_fields = sorted(set(got["scores"].get(key) or {})
                                - {"band", "nums"})
            assert got_fields == sorted(fields), \
                f"{rel}, «{key}»: поля записи стали {got_fields}"
        assert sorted(got["answered"]) == sorted(FIELDS[rel]), \
            f"{rel}: в ответах не все тесты: {got['answered']}"

        want = block_paths(b, BLOCKS[rel])
        missing = {p for p in want if dig(got["scores"], p) is None}
        assert missing == KNOWN_MISMATCH.get(BLOCKS[rel], set()), \
            (f"{rel}: список расхождений с bot.py изменился: {sorted(missing)}")
    ok("блоки, поля и ответы записи прежние, расхождений с ботом не добавилось")


def check_source_lines_gone() -> None:
    """9. Строки-источника на странице больше нет как элемента."""
    for rel in PAGES:
        body = html(rel)
        assert 'class="hub-src"' not in body, \
            f"{rel}: строка-источник всё ещё выводится"
    ok("строка-источник убрана со всех восьми страниц")


if __name__ == "__main__":
    raise SystemExit(run([
        check_no_latin, check_no_authors, check_score_not_shown,
        check_result_in_words, check_bands_clean, check_labels_clean,
        check_alert_still_refers, check_write_keys_unchanged,
        check_source_lines_gone,
    ]))
