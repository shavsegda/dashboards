# -*- coding: utf-8 -*-
"""Проверки: одна точка за период на восьми страницах с тестами.

Дефект с живого человека, 07.08.2026. У Алексея за 3 августа в базе лежит пять
строк квартального замера и восемь строк месячного — вместо одной и одной.
Каждая отправка создавала свою строку, потому что страницы писали в базу POST
без номера записи: базе нечем было понять, что это тот же замер.

Что из этого следовало:
  · линия в «Динамике» строилась по мусору — восемь точек за один день;
  · «уже проходил за этот период» не определялось вовсе;
  · сторож бота считал это дублями и шумел владельцу.

Правило проекта — **одна точка за период**. Номер записи считается от id
человека, блока и периода замера, поэтому повтор физически попадает в ту же
строку. Так сделано в `state-day/app.html`, отсюда и взято.

Период у каждой страницы свой, по её ритму: неделя, месяц, квартал, полгода,
год. Ритм берётся не из головы, а сверяется с реестром каталога.

Про уже накопленные строки. Старые строки лежат в базе со случайными номерами.
Правка по окну «человек + блок + даты периода» переписала бы ВСЕ пять строк
одним и тем же содержимым — это не починка, а потеря истории. Поэтому правка
идёт **только по номеру записи**: старые строки не трогаются никогда, а с этого
момента на период добавляется ровно одна новая строка, и дальше правится она.
Проверка `check_old_rows_untouched` следит именно за этим.

Проверки смотрят на СЕТЬ: не «как написан код», а какой метод, по какому адресу
и с каким телом уходит запрос. База подделана и ведёт себя как настоящая: POST
с занятым номером отвечает 409.

Запуск:      python3 checks/odna_tochka_za_period.py
Одна страница: ODNA_PAGE=state-week/app4.html python3 checks/odna_tochka_za_period.py
"""

import ast
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
from lib import BOT, ROOT, app_run, block_paths, bot, catalog, form_app, ok, run

CHECKS = Path(__file__).resolve().parent


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
# первичный ключ. POST с занятым номером получает 409. Правка по номеру меняет
# ту самую строку. Правка БЕЗ номера (по окну дат) меняет все строки человека по
# этому блоку — ровно так и потерялись бы старые строки, и проверка это увидит.
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
# 2. Номер записи детерминированный
# --------------------------------------------------------------------------
def check_record_id_deterministic() -> None:
    """3. Номер записи одинаковый при одинаковых id и периоде, иначе разный."""
    seen: Dict[str, str] = {}
    for rel, blk, _d, _i in PAGES:
        got = form_app(rel, r"""
  OUT.ids = {
    same_a: await recordIdFor(777, 'P-1'),
    same_b: await recordIdFor(777, 'P-1'),
    other_user: await recordIdFor(778, 'P-1'),
    other_period: await recordIdFor(777, 'P-2'),
    key: idKeyString(777, 'P-1')
  };
""")
        ids = got["ids"]
        assert ids["same_a"] == ids["same_b"], \
            f"{rel}: один человек и один период дали разные номера записи"
        assert ids["same_a"] != ids["other_user"], \
            f"{rel}: у двух людей за один период один номер записи"
        assert ids["same_a"] != ids["other_period"], \
            f"{rel}: два периода дали один номер записи"
        # Номер обязан выглядеть как uuid: колонка id в базе именно такая.
        parts = ids["same_a"].split("-")
        assert [len(p) for p in parts] == [8, 4, 4, 4, 12], \
            f"{rel}: номер записи не похож на uuid — «{ids['same_a']}»"
        assert blk in ids["key"], \
            f"{rel}: блок не участвует в номере записи — «{ids['key']}»"
        seen[rel] = ids["same_a"]
    # Разные замеры за один и тот же период не должны попадать в одну строку.
    if len(seen) > 1:
        assert len(set(seen.values())) == len(seen), \
            "разные страницы дают один номер записи: " + json.dumps(seen)
    ok("номер записи считается от человека, блока и периода — и только от них")


# --------------------------------------------------------------------------
# 3. Две отправки за период — одна строка
# --------------------------------------------------------------------------
def check_two_sends_one_row() -> None:
    """4. Две отправки за один период дают ОДНУ строку, и в ней вторая отправка."""
    for rel, blk, _d, _i in PAGES:
        got = db_run(rel, PASS_ALL % 2 + PASS_ALL % 3, seed=junk(blk))
        mine = new_rows(got, blk)
        assert len(mine) == 1, \
            f"{rel}: после двух отправок строк {len(mine)}, а не одна: {sorted(mine)}"
        assert got["sync"] == "ok", \
            f"{rel}: повторная отправка объявлена провалом (sync={got['sync']})"
        # Успех без строки — худшее из возможного: человек видит «записано», а в
        # базе ничего. Значит последний запрос обязан был долететь до строки.
        row = list(mine.values())[0]
        assert row.get("__seq") == len(got["req"]), \
            f"{rel}: последняя отправка до строки не дошла, " \
            f"строку тронул запрос №{row.get('__seq')} из {len(got['req'])}"
        # Запрос, который база приняла, обязан был долететь до строки. Отказ
        # (409 на занятый номер) — не успех, его пропускаем: за ним идёт правка.
        for r in got["req"]:
            assert r["hit"] >= 1 or r["status"] >= 300, \
                f"{rel}: запрос {r['method']} не задел ни одной строки, " \
                f"а база ответила {r['status']}"
    ok("две отправки за один период: одна строка, и в ней последние ответы")


def check_second_send_is_patch_by_id() -> None:
    """5. Строка правится, а не добавляется: вторая отправка — правка по номеру."""
    for rel, blk, _d, _i in PAGES:
        got = db_run(rel, PASS_ALL % 2 + PASS_ALL % 3, seed=junk(blk))
        made = [r for r in posts(got) if r["status"] < 300]
        assert len(made) == 1, \
            f"{rel}: строк создано {len(made)}, а должна быть одна"
        the_id = made[0]["id"]
        after = got["req"][got["req"].index(made[0]) + 1:]
        assert after, f"{rel}: после первой записи в базу больше не ходили"
        # Дальше строку меняет только правка по тому же номеру. Попытки создать
        # вторую строку допустимы — но обязаны разбиваться о занятый номер.
        for r in after:
            assert r["id"] == the_id, \
                f"{rel}: запрос ушёл по номеру «{r['id']}» вместо «{the_id}»"
            if r["method"] == "POST":
                assert r["status"] == 409, \
                    f"{rel}: вторая строка создалась, база ответила {r['status']}"
                continue
            assert r["method"] == "PATCH", \
                f"{rel}: повтор ушёл методом {r['method']}, а не правкой"
            assert "id=eq." in r["url"], \
                f"{rel}: правка идёт не по номеру записи — {r['url']}"
        assert [r for r in after if r["method"] == "PATCH"], \
            f"{rel}: правки не было вовсе — значит повтор ничего не записал"
        # Содержимое строки — от ПОСЛЕДНЕЙ отправки, а не от первой.
        row = new_rows(got, blk)[the_id]
        last = patches(got)[-1]["body"]
        assert row["scores"] == last["scores"], \
            f"{rel}: в строке остались цифры первой отправки"
        assert row["completed_at"] == last["completed_at"], \
            f"{rel}: у строки осталась дата первой отправки"
    ok("повтор правит ту же строку, и в ней последние ответы")


def check_return_visit_edits_the_row() -> None:
    """6. Человек вернулся позже в том же периоде — строка та же."""
    for rel, blk, _d, _i in PAGES:
        # Заход первый: снимаем номер и строку.
        first = db_run(rel, PASS_ALL % 2, seed=junk(blk))
        mine = new_rows(first, blk)
        assert len(mine) == 1, f"{rel}: первый заход дал строк {len(mine)}"
        the_id = list(mine)[0]

        # Заход второй, страница загружена заново: в памяти телефона ничего про
        # базу нет, а строка уже там. Повтор обязан наткнуться на номер.
        seed = json.loads(junk(blk))
        seed[the_id] = mine[the_id]
        got = db_run(rel, PASS_ALL % 3, seed=json.dumps(seed, ensure_ascii=False))
        again = new_rows(got, blk)
        assert len(again) == 1, \
            f"{rel}: после возвращения строк {len(again)}, а не одна"
        assert the_id in again, f"{rel}: строка сменила номер"
        assert got["sync"] == "ok", \
            f"{rel}: возвращение объявлено провалом (sync={got['sync']})"
        # Ровно то, ради чего всё: POST наткнулся на номер и ушёл в правку.
        conflicts = [r for r in posts(got) if r["status"] == 409]
        assert conflicts, \
            f"{rel}: повтор не наткнулся на занятый номер — значит номер не тот"
        assert [r for r in patches(got) if r["id"] == the_id], \
            f"{rel}: после конфликта правки по номеру не было"
        assert not [r for r in posts(got) if r["status"] < 300], \
            f"{rel}: при занятом номере всё равно создалась новая строка"
    ok("вернулся в том же периоде: правится та же строка, второй не появилось")


# --------------------------------------------------------------------------
# 4. Уже накопленное не портится
# --------------------------------------------------------------------------
def check_old_rows_untouched() -> None:
    """7. Старые строки со случайными номерами не переписываются и не исчезают."""
    for rel, blk, _d, _i in PAGES:
        seed = junk(blk, 5)
        before = json.loads(seed)
        got = db_run(rel, PASS_ALL % 2 + PASS_ALL % 3, seed=seed)
        for k, v in before.items():
            assert k in got["rows"], f"{rel}: старая строка «{k}» исчезла"
            assert got["rows"][k] == v, \
                f"{rel}: старая строка «{k}» переписана новым замером"
        # Правки по окну дат быть не должно: она и переписывает всё разом.
        for r in patches(got):
            assert "completed_at=gte" not in r["url"], \
                f"{rel}: правка идёт по окну дат — так теряется история"
            assert r["hit"] <= 1, \
                f"{rel}: одна правка задела {r['hit']} строк"
    ok("старые строки целы: правка ходит только по номеру записи")


# --------------------------------------------------------------------------
# 5. Ключи полей и суммы не изменились
# --------------------------------------------------------------------------
def check_record_keys_and_sums_unchanged() -> None:
    """8. Ключи полей и числа те же — и в новой строке, и в правке.

    Запись собирается по ходу захода: после первого теста в ней один тест, после
    последнего — все. Поэтому полную форму спрашиваем у ПОСЛЕДНЕГО запроса, а у
    первого — только набор колонок.
    """
    b = bot()
    aliases = line_aliases()
    COLUMNS = {"user_id", "block", "instrument", "scores", "answers",
               "completed_at"}
    for rel, blk, _d, instr in PAGES:
        got = db_run(rel, PASS_ALL % 2 + PASS_ALL % 3, seed=junk(blk))
        made = [r for r in posts(got) if r["status"] < 300]
        assert made, f"{rel}: новой строки в базе не появилось"
        assert patches(got), f"{rel}: правки не было — повтор ушёл иначе"
        first = made[0]["body"]
        last = patches(got)[-1]["body"]

        # Новая строка: те же колонки плюс номер записи.
        assert set(first) == COLUMNS | {"id"}, \
            f"{rel}: у новой строки колонки {sorted(first)}"
        # Правка: те же колонки без номера — он в адресе.
        assert set(last) == COLUMNS, f"{rel}: у правки колонки {sorted(last)}"

        for name, body in (("новая строка", first), ("правка", last)):
            assert body["block"] == blk, \
                f"{rel}, {name}: блок стал «{body['block']}»"
            assert body["instrument"] == instr, \
                f"{rel}, {name}: подпись инструмента стала «{body['instrument']}»"
            assert body["user_id"] == 777, \
                f"{rel}, {name}: id человека стал «{body['user_id']}»"
            assert body["scores"].get("source") == "manual", \
                f"{rel}, {name}: пропала метка источника"

        # Полная форма — в последней правке: там весь заход.
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
        # иначе после починки линия окажется пустой при полной базе.
        for path in block_paths(b, blk):
            v = bot_number(sc, path, aliases)
            assert isinstance(v, (int, float)), \
                f"{rel}: бот читает «{path}», а там {v!r}"
        # Первая отправка — часть того же захода: её тесты обязаны быть внутри.
        assert set(first["scores"]) <= set(sc), \
            f"{rel}: в новой строке тесты, которых нет в правке"
    ok("ключи полей, подпись инструмента и числа не поехали")


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
    ("номер записи не отправляется вовсе",
     "state-week/app4.html",
     "      body: JSON.stringify(Object.assign({id: id}, record))",
     "      body: JSON.stringify(record)",
     "check_two_sends_one_row"),

    ("номер записи не считается от периода",
     "state-month/app3.html",
     "function idKeyString(userId, pk) { return BLOCK + '|' + userId + '|' + pk; }",
     "function idKeyString(userId, pk) { return BLOCK + '|' + userId; }",
     "check_record_id_deterministic"),

    ("номер записи не считается от человека",
     "state-quarter/app3.html",
     "function idKeyString(userId, pk) { return BLOCK + '|' + userId + '|' + pk; }",
     "function idKeyString(userId, pk) { return BLOCK + '|' + pk; }",
     "check_record_id_deterministic"),

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

    ("занятый номер не уводит в правку, а считается отказом",
     "state-team/app.html",
     "    if (res.status === 409) return await patchById(id, record);",
     "    if (res.status === 409) return false;",
     "check_return_visit_edits_the_row"),

    ("правка идёт по окну дат и переписывает старые строки",
     "state-needs/app.html",
     "  const res = await fetch(TABLE + '?id=eq.' + id, {",
     "  const res = await fetch(TABLE + '?user_id=eq.' + record.user_id"
     " + '&block=eq.' + BLOCK, {",
     "check_old_rows_untouched"),

    ("занятый номер объявлен успехом, а правки нет",
     "state-year/app.html",
     "    if (res.status === 409) return await patchById(id, record);",
     "    if (res.status === 409) return true;",
     "check_two_sends_one_row"),

    ("в правку не уходят цифры замера",
     "selfhood/app.html",
     "async function patchById(id, record) {\n  const res = await fetch",
     "async function patchById(id, record) {\n  record = {completed_at:"
     " record.completed_at};\n  const res = await fetch",
     "check_record_keys_and_sums_unchanged"),

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
    "check_record_id_deterministic",
    "check_two_sends_one_row",
    "check_return_visit_edits_the_row",
    "check_old_rows_untouched",
    "check_record_keys_and_sums_unchanged",
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
    check_record_id_deterministic,
    check_two_sends_one_row,
    check_second_send_is_patch_by_id,
    check_return_visit_edits_the_row,
    check_old_rows_untouched,
    check_record_keys_and_sums_unchanged,
    check_prev_comparison_still_works,
    check_repeat_does_not_compare_with_itself,
]

if __name__ == "__main__":
    fns = list(CHECKS_LIST)
    # Под мутациями гоняется одна проверка, сами мутации тогда не нужны.
    if not ONE:
        fns += [check_every_requirement_has_a_mutation, check_mutations_are_caught]
    raise SystemExit(run(fns))
