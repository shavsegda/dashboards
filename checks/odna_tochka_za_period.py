# -*- coding: utf-8 -*-
"""Проверки: одна точка за период на восьми страницах с тестами.

ПЕРЕПИСАНО 10.08.2026, спека 023 «Замер сохраняется, важность спрашивается».

Что было. Правило «одна точка за период» держалось на ЗАПИСИ: номер строки
считался от id человека, блока и периода, повтор натыкался на занятый номер и
уходил в правку той же строки.

Почему отменено. Проверка 10.08.2026 показала: ключ, с которым работают
страницы, умеет только вставлять. Правка возвращает HTTP 200 и ноль строк,
чтение отдаёт пустой массив. Значит повтор всегда упирался в отказ, человек
видел красную строку «Не удалось сохранить», а ответы не уходили никуда. Права
ключа не меняем: `user_id` берётся из адреса страницы и подделывается, а право
на правку означало бы право менять чужие замеры.

Как стало.
  · FR-001: каждый заход создаёт НОВУЮ строку со случайным номером. Занятого
    номера быть не может, и отказа от базы по этой причине тоже.
  · FR-002: правило «одна точка за период» переехало на ЧТЕНИЕ. Строк за период
    в базе несколько, а в линии стоит одна — с самым поздним `completed_at`.
  · FR-003: права ключа не трогаем. Только вставка, ни одной правки.
  · FR-004: черновик ответов стирается только после подтверждённой записи.

Поэтому проверки смотрят на две вещи сразу: что страница отправляет в базу (это
СЕТЬ — метод, адрес, тело) и что из накопленных строк прочитает бот. Читающая
часть берётся из `bot.py` разбором AST: `period_key`, `latest_per_period` и
`line_series` — те самые, которыми бот строит «Динамику».

Период у каждой страницы свой, по её ритму: неделя, месяц, квартал, полгода,
год. Ритм берётся не из головы, а сверяется с реестром каталога.

Запуск:      python3 checks/odna_tochka_za_period.py
Одна страница: ODNA_PAGE=state-week/app4.html python3 checks/odna_tochka_za_period.py
"""

import ast
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
from lib import (BOT, ROOT, app_run, block_paths, bot, bot_reader, catalog,
                 form_app, html, ok, run)

CHECKS = Path(__file__).resolve().parent

# Имена, вырезанные из страниц спекой 023. Ни одно из них не должно вернуться:
# каждое было частью механики «повтор правит существующую строку».
GONE_FROM_PAGES = ("recordId", "recordIdFor", "idKeyString", "fnvBytes",
                   "patchById", "patchWindow", "patchBody", "countRows",
                   "periodWindow", "decideWrite", "postThenPatch")


def line_aliases() -> Dict[str, Tuple[str, ...]]:
    """Синонимы имён полей из `bot.py`. Только чтение, разбором AST.

    Бот читает линию не по одному имени: `couple.total` он ищет и как `sum`,
    потому что недельная страница пишет именно `sum`. Проверка обязана читать
    запись так же, иначе она ругалась бы на нормальную запись.
    """
    tree = ast.parse(BOT.read_text(encoding="utf-8"))
    for node in tree.body:
        name = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
        if name == "LINE_FIELD_ALIASES":
            return ast.literal_eval(node.value)
    raise AssertionError("в bot.py нет LINE_FIELD_ALIASES")


def bot_number(scores: Dict, path: str, aliases: Dict[str, Tuple[str, ...]]):
    """Число, которое бот прочитает по этому пути. Нет — None, как у бота."""
    test, _dot, field = path.partition(".")
    v = (scores or {}).get(test)
    if not isinstance(v, dict):
        return None
    for name in (field,) + tuple(aliases.get(path) or ()):
        x = v.get(name)
        if isinstance(x, (int, float)):
            return x
    return None

# --------------------------------------------------------------------------
# Восемь страниц, у каждой свой ритм
# --------------------------------------------------------------------------
# (страница · блок базы · сколько дней в периоде · подпись инструмента)
PAGES: List[Tuple[str, str, int, str]] = [
    ("state-week/app4.html", "state_week", 7,
     "PANAS-SF + Vitality + PHQ-2/GAD-2 + поток + KMS-3"),
    ("state-month/app3.html", "state_month", 30, "PSS-10 + ISI"),
    ("state-clinical/app.html", "state_clinical", 30, "PHQ-9 + GAD-7 + ASRM"),
    ("state-quarter/app3.html", "state_quarter", 91,
     "SWLS + MLQ + FFMQ-15 + RSES + OLBI + MSPSS"),
    ("state-needs/app.html", "state_needs", 91, "BPNSFS"),
    ("state-team/app.html", "state_team", 91,
     "Шкала психологической безопасности команды (Edmondson, 1999)"),
    ("selfhood/app.html", "selfhood", 180,
     "SCCS + Authenticity Scale + DIDS + DSI-R (I-position)"),
    ("state-year/app.html", "state_year", 365, "AUDIT-C"),
]

# Мутации гоняют проверку по одной странице: иначе каждая поломка стоит минуту.
ONE = os.environ.get("ODNA_PAGE") or ""
if ONE:
    PAGES = [p for p in PAGES if p[0] == ONE]
    assert PAGES, f"ODNA_PAGE={ONE}: такой страницы в списке нет"

BLOCK = {rel: blk for rel, blk, _d, _i in PAGES}
DAYS = {rel: d for rel, _b, d, _i in PAGES}
INSTRUMENT = {rel: i for rel, _b, _d, i in PAGES}

# Форма записи, замороженная до починки. Ключи полей и числа менять было нельзя:
# по ним читают бот и панели. Значения — ответ «2» на каждый пункт.
SHAPE: Dict[str, Dict[str, List[str]]] = {
    "state-week/app4.html": {
        "panas": ["band", "na", "nums", "pa"],
        "vitality": ["band", "mean", "nums"],
        "gate": ["alert", "band", "gad", "nums", "phq"],
        "flow": ["band", "nums", "value"],
        "couple": ["band", "nums", "sum"],
    },
    "state-month/app3.html": {
        "pss": ["band", "nums", "total"],
        "isi": ["alert", "band", "nums", "total"],
    },
    "state-clinical/app.html": {
        "phq": ["alert", "band", "item9", "item9_flag", "nums", "total"],
        "gad": ["alert", "band", "nums", "total"],
        "asrm": ["alert", "band", "nums", "total"],
    },
    "state-quarter/app3.html": {
        "swls": ["band", "nums", "sum"],
        "mlq": ["band", "nums", "presence", "search"],
        "ffmq": ["act_aware", "band", "describe", "mean", "nonjudge",
                 "nonreact", "nums", "observe"],
        "rses": ["band", "nums", "sum"],
        "olbi": ["band", "disengagement", "disengagement_sum", "exhaustion",
                 "exhaustion_sum", "nums"],
        "support": ["band", "family", "friends", "nums", "significant_other"],
    },
    "state-needs/app.html": {
        "bpnsfs": ["autonomy_frustration", "autonomy_satisfaction", "band",
                   "competence_frustration", "competence_satisfaction",
                   "frustration", "nums", "relatedness_frustration",
                   "relatedness_satisfaction", "satisfaction"],
    },
    "state-team/app.html": {"safety": ["band", "mean", "nums"]},
    "selfhood/app.html": {
        "clarity": ["band", "mean", "nums", "sum"],
        "authenticity": ["authentic_living", "band", "external_influence",
                         "nums", "self_alienation"],
        "identity": ["band", "commitment", "exploration_breadth",
                     "exploration_depth", "identification", "nums",
                     "rumination"],
        "iposition": ["band", "mean", "nums", "sum"],
    },
    "state-year/app.html": {
        "audit": ["alert", "band", "nums", "sex_asked", "threshold", "total"],
    },
}

# Сколько пунктов в каждом тесте. Столько же ключей обязано доехать в ответах.
SIZES: Dict[str, List[int]] = {
    "state-week/app4.html": [10, 7, 4, 1, 3],
    "state-month/app3.html": [10, 7],
    "state-clinical/app.html": [9, 7, 5],
    "state-quarter/app3.html": [5, 10, 15, 10, 16, 12],
    "state-needs/app.html": [24],
    "state-team/app.html": [7],
    "selfhood/app.html": [12, 11, 25, 11],
    "state-year/app.html": [3],
}

# Даты для проверки границ периода: две внутри одного периода и одна за ним.
# Считаем по UTC — база и бот живут в UTC, и период обязан считаться так же.
BOUNDS: Dict[int, Tuple[str, str, str]] = {
    # неделя: понедельник и воскресенье одной недели ISO, потом следующий день
    7: ("2026-08-03T05:00:00.000Z", "2026-08-09T23:00:00.000Z",
        "2026-08-10T05:00:00.000Z"),
    # месяц: первое и последнее число, потом первое следующего
    30: ("2026-08-01T00:30:00.000Z", "2026-08-31T22:00:00.000Z",
         "2026-09-01T00:30:00.000Z"),
    # квартал: июль и сентябрь, потом октябрь
    91: ("2026-07-01T09:00:00.000Z", "2026-09-30T20:00:00.000Z",
         "2026-10-01T09:00:00.000Z"),
    # полгода: июль и декабрь, потом январь
    180: ("2026-07-01T09:00:00.000Z", "2026-12-31T20:00:00.000Z",
          "2027-01-01T09:00:00.000Z"),
    # год: январь и декабрь, потом январь следующего
    365: ("2026-01-02T09:00:00.000Z", "2026-12-31T20:00:00.000Z",
          "2027-01-02T09:00:00.000Z"),
}


# --------------------------------------------------------------------------
# Поддельная база
# --------------------------------------------------------------------------
# Ведёт себя как настоящая в том одном, что здесь важно: номер записи —
# первичный ключ, POST с занятым номером получает 409.
#
# Правка тут нарочно ПОСЛУШНАЯ, хотя настоящий ключ прав на неё не имеет: правка
# по номеру меняет строку, правка по окну — все строки человека по этому блоку.
# Так сделано, чтобы поломка была видна. Смысл проверок — что страница не ходит
# правкой вовсе; если бы поддельная база молчала в ответ, как настоящая,
# вернувшаяся правка выглядела бы безобидно.
FAKE_DB = r"""
  globalThis.ROWS = %s;
  globalThis.REQ = [];
  globalThis.fetch = async function (url, opts) {
    var o = opts || {};
    var m = String(o.method || 'GET').toUpperCase();
    var body = o.body ? JSON.parse(o.body) : null;
    var u = String(url);
    var st = 200, id = null, hit = 0;
    // Номер запроса, которым строку тронули последний раз. Нужен, чтобы
    // отличить «правку доставили» от «правка ушла в пустоту, а нам сказали да».
    var seq = globalThis.REQ.length + 1;
    if (m === 'POST') {
      id = (body && body.id === undefined) ? '(без номера)' : String(body.id);
      if (id !== '(без номера)' &&
          Object.prototype.hasOwnProperty.call(globalThis.ROWS, id)) {
        st = 409;
      } else {
        st = 201;
        // Без номера база кладёт КАЖДУЮ отправку новой строкой — так и было.
        var newId = (id === '(без номера)')
          ? ('rnd_' + Object.keys(globalThis.ROWS).length) : id;
        globalThis.ROWS[newId] = JSON.parse(JSON.stringify(body));
        globalThis.ROWS[newId].__seq = seq;
        hit = 1;
      }
    } else if (m === 'PATCH') {
      var mm = /[?&]id=eq\.([^&]+)/.exec(u);
      id = mm ? decodeURIComponent(mm[1]) : null;
      var targets = id
        ? (globalThis.ROWS[id] ? [id] : [])
        // Правка без номера — по окну: под неё попадают ВСЕ строки человека по
        // этому блоку, включая старые. Ровно так история и потерялась бы.
        : Object.keys(globalThis.ROWS).filter(function (k) {
            var r = globalThis.ROWS[k];
            return String(r.user_id) === String((body || {}).user_id)
                && String(r.block) === String((body || {}).block);
          });
      targets.forEach(function (k) {
        Object.keys(body || {}).forEach(function (f) { globalThis.ROWS[k][f] = body[f]; });
        globalThis.ROWS[k].__seq = seq;
        hit++;
      });
      // PostgREST на правку мимо строки отвечает успехом, не ошибкой.
      st = 200;
    }
    globalThis.REQ.push({ method: m, url: u, id: id, body: body,
                          status: st, hit: hit });
    return { ok: st < 300, status: st, json: async function () { return []; } };
  };
"""

# База, которая отказывает: сеть отвалилась, ключ отозвали, таблица занята.
# Нужна ради FR-004: человек обязан увидеть честную ошибку, а черновик ответов —
# остаться на месте. Ошибка молчаливого успеха здесь стоит всего замера.
FAKE_DB_REFUSES = r"""
  globalThis.ROWS = %s;
  globalThis.REQ = [];
  globalThis.fetch = async function (url, opts) {
    var o = opts || {};
    var m = String(o.method || 'GET').toUpperCase();
    globalThis.REQ.push({ method: m, url: String(url), id: null,
                          body: o.body ? JSON.parse(o.body) : null,
                          status: 500, hit: 0 });
    return { ok: false, status: 500, json: async function () { return []; } };
  };
"""

TAIL = r"""
  OUT.req = globalThis.REQ.map(function (r) {
    return { method: r.method, url: r.url, id: r.id, status: r.status,
             hit: r.hit, body: r.body };
  });
  OUT.rows = globalThis.ROWS;
  OUT.sync = (typeof state !== 'undefined' && state) ? state.sync : null;
"""

# Старые строки в базе: те самые пять квартальных за 3 августа, со случайными
# номерами. Их нельзя ни переписать, ни удалить.
def junk(block: str, n: int = 3) -> str:
    rows = {}
    for i in range(n):
        rows["old_%d" % i] = {
            "user_id": 777, "block": block, "instrument": "прежний заход",
            "scores": {"source": "manual", "старое": i},
            "answers": {"старое": i},
            "completed_at": "2026-08-03T1%d:00:00.000Z" % i,
        }
    return json.dumps(rows, ensure_ascii=False)


def db_run(rel: str, body: str, seed: str = "{}") -> Dict:
    """Прогнать страницу с поддельной базой и вернуть запросы и строки."""
    return app_run(rel, (FAKE_DB % seed) + body + TAIL)


PASS_ALL = "  for (const t of TESTS) { await __pass(t.key, %d); }\n"

# То же самое, но с паузой между ответами. Нужно там, где важна «самая
# поздняя запись»: в жизни между тестами проходят секунды, а в node — доли
# миллисекунды, и все строки получают одну и ту же метку времени. Тогда
# «последнюю» не различить, и проверка ругалась бы на исправный код.
PASS_ALL_SLOW = ("  for (const t of TESTS) { await __pass(t.key, %d);"
                 " await new Promise(r => setTimeout(r, 3)); }\n")


def new_rows(got: Dict, block: str) -> Dict:
    """Строки, которых до захода не было."""
    return {k: v for k, v in got["rows"].items() if not k.startswith("old_")}


def posts(got: Dict) -> List[Dict]:
    return [r for r in got["req"] if r["method"] == "POST"]


def patches(got: Dict) -> List[Dict]:
    return [r for r in got["req"] if r["method"] == "PATCH"]


# --------------------------------------------------------------------------
# 1. Период берётся из своего ритма страницы
# --------------------------------------------------------------------------
def check_period_days_match_rhythm() -> None:
    """1. Ритм периода на странице совпадает с реестром каталога."""
    reg = {r["key"]: r["days"] for r in catalog()["registry"]}
    for rel, blk, days, _i in PAGES:
        got = form_app(rel, "OUT.days = PERIOD_DAYS;\n")
        assert got["days"] == days, \
            f"{rel}: на странице период {got['days']} дней, ждали {days}"
        assert reg.get(blk) == days, \
            f"{rel}: в каталоге у «{blk}» ритм {reg.get(blk)}, а на странице {days}"
    ok("ритм периода на странице тот же, что в реестре каталога")


def check_period_key_from_rhythm() -> None:
    """2. Две даты внутри периода дают один ключ, дата за границей — другой."""
    for rel, _b, days, _i in PAGES:
        a, b, out = BOUNDS[days]
        got = form_app(rel, "OUT.pk = %s.map(function (s) { return periodKey(s); });\n"
                       % json.dumps([a, b, out]))
        pk = got["pk"]
        assert pk[0] == pk[1], \
            f"{rel}: {a} и {b} внутри одного периода, а ключи разные: {pk[0]} и {pk[1]}"
        assert pk[1] != pk[2], \
            f"{rel}: {b} и {out} в разных периодах, а ключ один: {pk[1]}"
        assert isinstance(pk[0], str) and pk[0], f"{rel}: ключ периода пустой"
    ok("ключ периода меняется ровно на границе своего ритма")


# --------------------------------------------------------------------------
# 2. Номер записи случайный: каждый заход — своя строка
# --------------------------------------------------------------------------
def check_record_id_is_random() -> None:
    """3. FR-001: номер записи свежий на каждый заход и не считается ни от чего."""
    seen: Dict[str, str] = {}
    for rel, blk, _d, _i in PAGES:
        got = form_app(rel, r"""
  OUT.ids = { a: newRecordId(), b: newRecordId(), c: newRecordId() };
""")
        ids = got["ids"]
        assert len(set(ids.values())) == 3, \
            f"{rel}: три захода подряд дали не три разных номера: {ids}"
        for name, val in ids.items():
            parts = val.split("-")
            assert [len(x) for x in parts] == [8, 4, 4, 4, 12], \
                f"{rel}: номер записи не похож на uuid — «{val}»"
            assert parts[2][0] == "4", \
                f"{rel}: номер записи не случайный (версия uuid не 4): «{val}»"
        seen[rel] = ids["a"]
        # Механика «повтор правит строку» вырезана целиком. Любое из этих имён
        # на странице означает, что она вернулась.
        src = html(rel)
        back = [n for n in GONE_FROM_PAGES if n in src]
        assert not back, f"{rel}: вернулись имена правки по номеру: {back}"
    ok("номер записи свежий на каждый заход, старая механика правки не вернулась")


# --------------------------------------------------------------------------
# 3. Две отправки за период — две строки, и обе доехали
# --------------------------------------------------------------------------
def check_two_sends_two_rows() -> None:
    """4. FR-001: два захода за период сохраняются оба, ни одного отказа."""
    for rel, blk, _d, _i in PAGES:
        got = db_run(rel, PASS_ALL % 2 + PASS_ALL % 3, seed=junk(blk))
        mine = new_rows(got, blk)
        assert len(mine) >= 2, \
            f"{rel}: после двух заходов новых строк {len(mine)} — повтор не записался"
        assert got["sync"] == "ok", \
            f"{rel}: повторный заход объявлен провалом (sync={got['sync']})"
        # Успех без строки — худшее из возможного: человек видит «записано», а в
        # базе ничего. Каждый принятый запрос обязан был дойти до строки.
        for r in got["req"]:
            assert r["status"] < 300, \
                f"{rel}: база отказала запросу {r['method']} со статусом {r['status']}"
            assert r["hit"] == 1, \
                f"{rel}: запрос {r['method']} задел {r['hit']} строк вместо одной"
    ok("два захода за период: обе записи сохранены, ни одного отказа")


def check_only_inserts() -> None:
    """5. FR-003: страница только вставляет. Ни правки, ни чтения."""
    for rel, blk, _d, _i in PAGES:
        got = db_run(rel, PASS_ALL % 2 + PASS_ALL % 3, seed=junk(blk))
        assert not patches(got), \
            f"{rel}: страница ушла правкой — прав на неё у ключа нет"
        bad = [r for r in got["req"] if r["method"] != "POST"]
        assert not bad, \
            f"{rel}: в базу ушли не только вставки: {[r['method'] for r in bad]}"
        assert posts(got), f"{rel}: в базу не ушло ни одной вставки"
        # Номер записи у каждой вставки свой: одинаковый означал бы отказ базы.
        ids = [r["id"] for r in posts(got)]
        assert len(set(ids)) == len(ids), \
            f"{rel}: две вставки ушли под одним номером: {ids}"
    ok("страница только вставляет: ни правки, ни чтения, номера не повторяются")


def check_return_visit_saves_again() -> None:
    """6. Человек вернулся позже в том же периоде — запись проходит."""
    for rel, blk, _d, _i in PAGES:
        # Заход первый: снимаем строки.
        first = db_run(rel, PASS_ALL % 2, seed=junk(blk))
        mine = new_rows(first, blk)
        assert mine, f"{rel}: первый заход не записал ничего"
        assert first["sync"] == "ok", f"{rel}: первый заход провалился"

        # Заход второй, страница загружена заново: в памяти телефона ничего про
        # базу нет, а строки уже там. Это и есть повтор за период.
        seed = json.loads(junk(blk))
        seed.update(mine)
        got = db_run(rel, PASS_ALL % 3, seed=json.dumps(seed, ensure_ascii=False))
        assert got["sync"] == "ok", \
            f"{rel}: возвращение объявлено провалом (sync={got['sync']})"
        again = {k: v for k, v in new_rows(got, blk).items() if k not in mine}
        assert again, f"{rel}: повтор не создал ни одной новой строки"
        # Прежние строки захода на месте: их никто не трогал.
        for k, v in mine.items():
            assert got["rows"].get(k) == v, \
                f"{rel}: строка первого захода «{k}» изменилась при повторе"
    ok("вернулся в том же периоде: запись прошла, прежние строки целы")


def check_failure_is_honest() -> None:
    """7. FR-004: запись не прошла — сказано честно, черновик не стёрт."""
    for rel, blk, _d, _i in PAGES:
        got = app_run(rel, (FAKE_DB_REFUSES % junk(blk)) + r"""
  // Черновик, как его сохраняет живой человек посреди прохождения.
  state.key = TESTS[0].key;
  state.idx = 1;
  state.answers = {0: 1};
  saveProgress();
""" + PASS_ALL % 2 + TAIL + r"""
  OUT.draft = localStorage.getItem(STORE_KEY) !== null;
  OUT.screen = app.innerHTML;
""")
        assert got["sync"] == "error", \
            f"{rel}: база отказала, а страница говорит sync={got['sync']}"
        assert got["draft"], \
            f"{rel}: запись не прошла, а черновик ответов уже стёрт"
        assert not new_rows(got, blk), \
            f"{rel}: база отказывала, а строки всё равно появились"
    ok("отказ базы показан честно, черновик ответов на месте")


# --------------------------------------------------------------------------
# 4. Уже накопленное не портится
# --------------------------------------------------------------------------
def check_old_rows_untouched() -> None:
    """8. Старые строки со случайными номерами не переписываются и не исчезают."""
    for rel, blk, _d, _i in PAGES:
        seed = junk(blk, 5)
        before = json.loads(seed)
        got = db_run(rel, PASS_ALL % 2 + PASS_ALL % 3, seed=seed)
        for k, v in before.items():
            assert k in got["rows"], f"{rel}: старая строка «{k}» исчезла"
            assert got["rows"][k] == v, \
                f"{rel}: старая строка «{k}» переписана новым замером"
        # Ни одного запроса по окну дат: он и переписывает всё разом.
        for r in got["req"]:
            assert "completed_at=gte" not in r["url"], \
                f"{rel}: запрос идёт по окну дат — так теряется история"
    ok("старые строки целы: страница ходит в базу только новой строкой")


# --------------------------------------------------------------------------
# 5. Ключи полей и суммы не изменились
# --------------------------------------------------------------------------
def check_record_keys_and_sums_unchanged() -> None:
    """9. Ключи полей и числа те же — и в первой строке, и в последней.

    Запись собирается по ходу захода: после первого теста в ней один тест, после
    последнего — все. Поэтому полную форму спрашиваем у ПОСЛЕДНЕЙ вставки, а у
    первой — только набор колонок.
    """
    b = bot()
    aliases = line_aliases()
    COLUMNS = {"user_id", "block", "instrument", "scores", "answers",
               "completed_at"}
    for rel, blk, _d, instr in PAGES:
        got = db_run(rel, PASS_ALL % 2 + PASS_ALL % 3, seed=junk(blk))
        made = [r for r in posts(got) if r["status"] < 300]
        assert made, f"{rel}: новой строки в базе не появилось"
        first = made[0]["body"]
        last = made[-1]["body"]

        # У каждой строки одни и те же колонки плюс номер записи. Номер теперь
        # едет в теле всегда: без него база кладёт строку под своим, и страница
        # перестаёт отвечать за то, что записала.
        for name, body in (("первая строка", first), ("последняя строка", last)):
            assert set(body) == COLUMNS | {"id"}, \
                f"{rel}, {name}: колонки {sorted(body)}"
            assert body["block"] == blk, \
                f"{rel}, {name}: блок стал «{body['block']}»"
            assert body["instrument"] == instr, \
                f"{rel}, {name}: подпись инструмента стала «{body['instrument']}»"
            assert body["user_id"] == 777, \
                f"{rel}, {name}: id человека стал «{body['user_id']}»"
            assert body["scores"].get("source") == "manual", \
                f"{rel}, {name}: пропала метка источника"

        # Полная форма — в последней вставке: там весь заход.
        sc = last["scores"]
        for key, fields in SHAPE[rel].items():
            assert key in sc, f"{rel}: пропал тест «{key}»"
            assert sorted(k for k in sc[key] if k != "nums") == \
                sorted(f for f in fields if f != "nums"), \
                f"{rel}, «{key}»: поля стали {sorted(sc[key])}"
            assert isinstance(sc[key].get("nums"), list) and sc[key]["nums"], \
                f"{rel}, «{key}»: пропали числа"
        sizes = [len(last["answers"].get(k, {})) for k in SHAPE[rel]]
        assert sizes == SIZES[rel], \
            f"{rel}: пунктов в ответах {sizes} вместо {SIZES[rel]}"
        # Линии, которые бот рисует в «Динамике», обязаны читаться числами —
        # иначе линия окажется пустой при полной базе.
        for path in block_paths(b, blk):
            v = bot_number(sc, path, aliases)
            assert isinstance(v, (int, float)), \
                f"{rel}: бот читает «{path}», а там {v!r}"
        # Первая вставка — часть того же захода: её тесты обязаны быть внутри.
        assert set(first["scores"]) <= set(sc), \
            f"{rel}: в первой строке тесты, которых нет в последней"
    ok("ключи полей, подпись инструмента и числа не поехали")


# --------------------------------------------------------------------------
# 5а. Главное правило: одна точка за период — на ЧТЕНИИ
# --------------------------------------------------------------------------
# Ради чего вся спека 023. В базе за период лежит столько строк, сколько раз
# человек нажал «готово». В линии обязана стоять ОДНА точка — самая поздняя.
# Читающий код живёт в `bot.py` (`period_key`, `latest_per_period`,
# `line_series`), поэтому проверка гоняет именно его — по строкам, которые
# реально написала страница.
def check_one_point_per_period_on_read() -> None:
    """10. FR-002: строк за период много, точка в линии одна — последняя."""
    R = bot_reader()
    b = bot()
    aliases = line_aliases()
    checked = 0
    for rel, blk, _d, _i in PAGES:
        days = R["CARD_DAYS"].get(blk)
        paths = sorted(block_paths(b, blk))
        if not days or not paths:
            # У карточки нет срока или нет своих линий — схлопывать нечего.
            continue
        got = db_run(rel, PASS_ALL_SLOW % 2 + PASS_ALL_SLOW % 3, seed=junk(blk))
        rows = [dict(v, block=blk) for v in new_rows(got, blk).values()]
        assert len(rows) >= 2, f"{rel}: строк за период меньше двух — нечего схлопывать"

        # Точка из ПРОШЛОГО периода: линия обязана её сохранить, а не съесть.
        past_when = (datetime.now(timezone.utc)
                     - timedelta(days=max(days, 31) * 2 + 5)).isoformat()
        last_scores = [r["body"]["scores"] for r in posts(got)][-1]

        for path in paths:
            want = bot_number(last_scores, path, aliases)
            if not isinstance(want, (int, float)):
                continue
            past_row = {"block": blk, "completed_at": past_when,
                        "scores": json.loads(json.dumps(last_scores))}
            series = R["line_series"](rows + [past_row], blk, path)
            # Ровно две точки: прошлый период и этот. Не десять.
            assert len(series) == 2, \
                f"{rel}, «{path}»: в линии {len(series)} точек при {len(rows)} строках"
            assert series[-1][1] == want, \
                f"{rel}, «{path}»: в линии не последняя запись периода: {series}"

            # У проверки обязаны быть зубы: без схлопывания точек было бы
            # больше. Если данные вдруг перестали содержать повтор, проверка
            # проходила бы вхолостую — и мы бы этого не заметили.
            naive = sorted({(str(r["completed_at"])[:10], id(r))
                            for r in rows + [past_row]})
            assert len(naive) > 2, \
                f"{rel}: в наборе нет повтора за период — проверка бессмысленна"
            checked += 1
    assert checked, "ни одной линии не проверено — правило чтения не покрыто"
    ok(f"одна точка за период на чтении: {checked} линий, в каждой последняя запись")


# --------------------------------------------------------------------------
# 6. Сравнение с прошлым разом
# --------------------------------------------------------------------------
def check_prev_comparison_still_works() -> None:
    """9. «С прошлым разом» работает: история после правки чище, а не пустее."""
    for rel, blk, _d, _i in PAGES:
        got = db_run(rel, r"""
  var key = TESTS[0].key;
  // Прошлый замер лежит в памяти телефона — по нему считается сдвиг.
  results[key] = { nums: [1], band: 'прошлое', c: 'ok',
                   data: { total: 1 }, answers: { 0: 1 },
                   completed_at: '2026-05-01T10:00:00.000Z' };
  saveResultsLocal();
  await __pass(key, 3);
  OUT.prev = results[key].prev;
  OUT.screen = app.innerHTML;
""", seed=junk(blk))
        prev = got["prev"]
        assert prev, f"{rel}: прошлый замер потерялся, сравнивать нечем"
        assert prev["completed_at"] == "2026-05-01T10:00:00.000Z", \
            f"{rel}: в «прошлом разе» лежит не прошлый замер: {prev}"
        screen = got["screen"]
        assert "undefined" not in screen and "NaN" not in screen, \
            f"{rel}: экран результата собрался с дырами"
    ok("сравнение с прошлым разом живо и считается по прошлому замеру")


def check_repeat_does_not_compare_with_itself() -> None:
    """10. Повтор за тот же период не сравнивается сам с собой."""
    for rel, blk, _d, _i in PAGES:
        got = db_run(rel, r"""
  var key = TESTS[0].key;
  results[key] = { nums: [1], band: 'прошлое', c: 'ok',
                   data: { total: 1 }, answers: { 0: 1 },
                   completed_at: '2026-05-01T10:00:00.000Z' };
  saveResultsLocal();
  await __pass(key, 2);
  var afterFirst = results[key].prev;
  // Второй раз тот же тест в том же периоде — это правка одной точки.
  await retryStore(key);
  OUT.first = afterFirst;
  OUT.second = results[key].prev;
""", seed=junk(blk))
        assert got["second"] == got["first"], \
            f"{rel}: повтор сдвинул «прошлый раз» на себя же: {got['second']}"
    ok("повтор за период не подменяет прошлый замер собой")


# --------------------------------------------------------------------------
# Мутации: ломаем починку и смотрим, покраснеет ли проверка
# --------------------------------------------------------------------------
# Конституция, принцип II: проверка обязана падать при сломанной логике.
# (что ломаем · файл · было · стало · какая проверка обязана покраснеть)
MUTATIONS: List[Tuple[str, str, str, str, str]] = [
    ("номер записи один и тот же на все заходы",
     "state-week/app4.html",
     "      body: JSON.stringify(Object.assign({id: newRecordId()}, record))",
     "      body: JSON.stringify(Object.assign({id: 'один-и-тот-же'}, record))",
     "check_two_sends_two_rows"),

    ("номер записи снова считается, а не берётся случайным",
     "state-month/app3.html",
     "function newRecordId() {\n  try {",
     "function newRecordId() {\n  return '00000000-0000-4000-8000-000000000000';\n  try {",
     "check_return_visit_saves_again"),

    ("номер записи один на всех",
     "state-quarter/app3.html",
     "function newRecordId() {\n  try {",
     "function newRecordId() {\n  return '11111111-1111-4111-8111-111111111111';\n  try {",
     "check_record_id_is_random"),

    ("номер записи не отправляется вовсе",
     "state-clinical/app.html",
     "      body: JSON.stringify(Object.assign({id: newRecordId()}, record))",
     "      body: JSON.stringify(record)",
     "check_record_keys_and_sums_unchanged"),

    ("период считается сутками, а не своим ритмом",
     "state-week/app4.html",
     "  if (PERIOD_DAYS <= 7) return isoWeekKey(d);",
     "  if (PERIOD_DAYS <= 7) return d.toISOString().slice(0, 10);",
     "check_period_key_from_rhythm"),

    ("ритм периода не тот, что в каталоге",
     "state-clinical/app.html",
     "const PERIOD_DAYS = 30;",
     "const PERIOD_DAYS = 7;",
     "check_period_days_match_rhythm"),

    ("страница снова правит строки по окну дат",
     "state-needs/app.html",
     "    return res.status < 300;",
     "    if (res.status < 300) { await fetch(TABLE + '?user_id=eq.'"
     " + record.user_id + '&block=eq.' + BLOCK, {method: 'PATCH',"
     " headers: sbHeaders(), body: JSON.stringify(record)}); }\n"
     "    return res.status < 300;",
     "check_old_rows_untouched"),

    ("правка вернулась и ходит по номеру записи",
     "state-team/app.html",
     "    return res.status < 300;",
     "    await fetch(TABLE + '?id=eq.' + record.user_id, {method: 'PATCH',"
     " headers: sbHeaders(), body: JSON.stringify(record)});\n"
     "    return res.status < 300;",
     "check_only_inserts"),

    ("отказ базы объявлен успехом",
     "state-year/app.html",
     "    return res.status < 300;",
     "    return true;",
     "check_failure_is_honest"),

    ("черновик стирается до ответа базы",
     "selfhood/app.html",
     "  if (okPush) {\n    saveResultsLocal();",
     "  if (true) {\n    saveResultsLocal();",
     "check_failure_is_honest"),

    ("у всех строк захода одна и та же дата — «последнюю» не выбрать",
     "state-year/app.html",
     "    completed_at: results[key].completed_at",
     "    completed_at: '2026-08-10T12:00:00.000Z'",
     "check_one_point_per_period_on_read"),

    ("прошлый замер затирается повтором",
     "state-week/app4.html",
     "    prev: keepPrev ? ((before && before.prev) || null)",
     "    prev: keepPrev ? (before ? {nums: before.nums,"
     " completed_at: before.completed_at} : null)",
     "check_repeat_does_not_compare_with_itself"),
]

MUST_COVER = {
    "check_period_days_match_rhythm",
    "check_period_key_from_rhythm",
    "check_record_id_is_random",
    "check_two_sends_two_rows",
    "check_only_inserts",
    "check_return_visit_saves_again",
    "check_failure_is_honest",
    "check_old_rows_untouched",
    "check_record_keys_and_sums_unchanged",
    "check_one_point_per_period_on_read",
    "check_repeat_does_not_compare_with_itself",
}


def _one_check(name: str, page: str) -> int:
    """Прогнать одну проверку по одной странице отдельным процессом."""
    code = (
        "import lib_path\n"
        "from lib import run\n"
        "import odna_tochka_za_period as C\n"
        "raise SystemExit(run([getattr(C, %r)]))\n" % name
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(CHECKS) + os.pathsep + env.get("PYTHONPATH", "")
    env["ODNA_PAGE"] = page
    r = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT),
                       capture_output=True, text=True, env=env, timeout=1800)
    return r.returncode


def check_every_requirement_has_a_mutation() -> None:
    """11. У каждого требования приёмки есть хотя бы одна поломка."""
    used = {m[4] for m in MUTATIONS}
    missing = MUST_COVER - used
    assert not missing, "без мутации остались: " + ", ".join(sorted(missing))
    ok(f"{len(MUST_COVER)} требований закрыты мутациями")


def check_mutations_are_caught() -> None:
    """12. Каждая поломка ловится проверкой, и файл возвращается на место."""
    before = {}
    for _w, rel, *_r in MUTATIONS:
        before[rel] = (ROOT / rel).read_text(encoding="utf-8")

    caught, misses = 0, []
    for what, rel, old, new, name in MUTATIONS:
        path = ROOT / rel
        src = before[rel]
        n = src.count(old)
        assert n == 1, f"«{what}»: место поломки в {rel} встречается {n} раз"
        try:
            path.write_text(src.replace(old, new, 1), encoding="utf-8")
            rc = _one_check(name, rel)
            if rc == 0:
                misses.append(f"{what} → {name} осталась зелёной")
            else:
                caught += 1
                print(f"  ловит  {what}  →  {name}")
        finally:
            path.write_text(src, encoding="utf-8")

    for rel, src in before.items():
        got = (ROOT / rel).read_text(encoding="utf-8")
        assert hashlib.sha256(got.encode()).digest() == \
            hashlib.sha256(src.encode()).digest(), \
            f"{rel} не вернулся к исходному состоянию"

    assert not misses, "не поймано: " + "; ".join(misses)
    ok(f"все {caught} поломок из {len(MUTATIONS)} пойманы, страницы на месте")


CHECKS_LIST = [
    check_period_days_match_rhythm,
    check_period_key_from_rhythm,
    check_record_id_is_random,
    check_two_sends_two_rows,
    check_only_inserts,
    check_return_visit_saves_again,
    check_failure_is_honest,
    check_old_rows_untouched,
    check_record_keys_and_sums_unchanged,
    check_one_point_per_period_on_read,
    check_prev_comparison_still_works,
    check_repeat_does_not_compare_with_itself,
]

if __name__ == "__main__":
    fns = list(CHECKS_LIST)
    # Под мутациями гоняется одна проверка, сами мутации тогда не нужны.
    if not ONE:
        fns += [check_every_requirement_has_a_mutation, check_mutations_are_caught]
    raise SystemExit(run(fns))
