# -*- coding: utf-8 -*-
"""Общие помощники для проверок мини-аппов.

Зачем это есть. Мини-аппы — это HTML со скриптом внутри, и проверить их
разбором текста можно только поверхностно: «слово есть, слова нет». Настоящие
ошибки — в логике: тест остался в списке, ключ поля переехал, старый результат
из памяти телефона снова уехал в базу. Поэтому проверки делают две вещи:

1. **Вырезают скрипт из HTML и исполняют его в node** с заглушками вместо
   браузера и Телеграма. После этого можно звать те же функции, что зовёт
   человек, и смотреть, что уходит в базу.
2. **Читают `bot.py` разбором AST** — как проверки в `specs/00*/checks.py`.
   Импортировать бота нельзя: при импорте он тянет токены и сеть.

Правило конституции, принцип II: проверка обязана падать при сломанной логике.
Поэтому сравниваем не «есть ли слово», а конкретные ключи и значения.
"""

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]           # локальный клон dashboards
BOT = Path(os.environ.get("BOT_PY") or (
    Path.home() / "Desktop" / "Файлы для работы на воркшопах" /
    "Рабочие вопросы" / "vslukh-bot" / "bot.py"))

PASSED = 0
FAILED: List[str] = []


def ok(name: str) -> None:
    global PASSED
    PASSED += 1
    print(f"  ok   {name}")


def report(title: str) -> int:
    """Итог прогона. Возвращает код выхода: 0 — всё зелёное."""
    if FAILED:
        print(f"\n{title}: провалено {len(FAILED)} из {len(FAILED) + PASSED}")
        for f in FAILED:
            print(f"  ПАДАЕТ  {f}")
        return 1
    print(f"\n{title}: всё зелёное, {PASSED} проверок.")
    return 0


def run(fns) -> int:
    """Прогнать проверки по очереди. Упавшая не останавливает остальные:
    иначе после первой ошибки не видно всей картины."""
    for fn in fns:
        print(f"{(fn.__doc__ or fn.__name__).splitlines()[0]}")
        try:
            fn()
        except KeyError as e:
            FAILED.append(f"{fn.__name__}: нет карточки или ключа {e}")
            print(f"  ПАДАЕТ нет карточки или ключа {e}")
        except AssertionError as e:
            FAILED.append(f"{fn.__name__}: {e}")
            print(f"  ПАДАЕТ {e}")
    return report(sys.argv[0].rsplit("/", 1)[-1])


# --------------------------------------------------------------------------
# HTML мини-аппа
# --------------------------------------------------------------------------
def html(rel: str) -> str:
    p = ROOT / rel
    assert p.exists(), f"нет файла {p}"
    return p.read_text(encoding="utf-8")


def inline_script(rel: str) -> str:
    """Свой скрипт мини-аппа: тег `<script>` без `src`. Их всегда один."""
    src = html(rel)
    found = [m.group(1) for m in
             re.finditer(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", src, re.S)]
    assert len(found) == 1, f"в {rel} не один свой скрипт, а {len(found)}"
    return found[0]


def pure_block(rel: str) -> str:
    """Блок «ЧИСТАЯ ЛОГИКА» — часть скрипта, которая не трогает DOM и сеть."""
    s = inline_script(rel)
    m = re.search(r"ЧИСТАЯ ЛОГИКА: НАЧАЛО(.*?)ЧИСТАЯ ЛОГИКА: КОНЕЦ", s, re.S)
    assert m, f"в {rel} нет границ блока чистой логики"
    body = m.group(1)
    # Отрезаем хвост комментария-заголовка и начало комментария-подвала: сами
    # маркеры лежат внутри /* … */, и без этого в node уедет мусор.
    body = body[body.index("*/") + 2:]
    return body[:body.rindex("/*")]


NODE_STUBS = r"""
// Заглушки вместо браузера и Телеграма. Всё, что уходит в сеть и в DOM,
// подменяется; логика замера, подсчёта и сборки записи остаётся боевой.
globalThis.window = { location: { search: '?u=tg_777' } };
globalThis.localStorage = {
  _s: {},
  getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
  setItem(k, v) { this._s[k] = String(v); },
  removeItem(k) { delete this._s[k]; }
};
globalThis.document = {
  getElementById() { return { style: {}, innerHTML: '', textContent: '' }; },
  createElement() { return { style: {}, setAttribute() {}, select() {} }; },
  body: { appendChild() {}, removeChild() {} },
  execCommand() { return true; }
};
globalThis.PUSHED = [];
globalThis.fetch = async function (url, opts) {
  globalThis.PUSHED.push({ url: String(url), body: opts && opts.body ? JSON.parse(opts.body) : null });
  return { ok: true, status: 201, json: async () => [] };
};
"""


def _node(js: str) -> Dict:
    """Выполнить JS в node и забрать то, что он напечатал через RESULT<json>."""
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
    assert m, f"скрипт ничего не вернул. stdout: {r.stdout[:500]}"
    return json.loads(m.group(1))


def form_app(rel: str, extra_js: str = "") -> Dict:
    """Прогнать мини-апп-опросник: заполнить все его тесты и посмотреть запись.

    Скрипт берётся до метки «=== Старт ===»: дальше идёт запуск отрисовки,
    который в проверке ни к чему. Всё до неё — объявления, шкалы, подсчёт и
    сборка записи, то есть ровно то, что надо проверить.
    """
    s = inline_script(rel)
    mark = "// === Старт ==="
    assert mark in s, f"в {rel} нет метки «{mark}» — не знаю, где кончаются объявления"
    body = s.split(mark)[0]
    js = NODE_STUBS + body + r"""
globalThis.__api = { TESTS, SCORERS, BLOCK, INSTRUMENT, buildScores, buildAnswers,
                     results, STORE_KEY, RESULT_KEY, CLOUD_KEY, UID };
const api = globalThis.__api;

/** Пройти один тест, отвечая одним и тем же значением. Как живой человек,
 *  только без тапов: state здесь не нужен, считает та же функция. */
function fill(key, value) {
  const t = api.TESTS.find(x => x.key === key);
  if (!t) throw new Error('нет теста ' + key);
  const ans = {};
  t.items.forEach((it, i) => {
    const scale = it.scale || t.scale;
    const v = (value === null) ? scale[0].v : value;
    ans[i] = v;
  });
  const s = api.SCORERS[key](ans);
  api.results[key] = { nums: s.nums, band: s.band, c: s.c, data: s.data,
                       answers: ans, completed_at: new Date().toISOString() };
  return s;
}
const OUT = {
  block: api.BLOCK, instrument: api.INSTRUMENT,
  keys: api.TESTS.map(t => t.key),
  titles: api.TESTS.map(t => t.title),
  sizes: api.TESTS.map(t => t.items.length),
  scorers: Object.keys(api.SCORERS),
  storeKeys: [api.STORE_KEY, api.RESULT_KEY, api.CLOUD_KEY]
};
""" + extra_js + r"""
console.log('RESULT<' + JSON.stringify(OUT) + '>RESULT');
"""
    return _node(js)


DOM_STUB = r"""
globalThis.document.getElementById = function () {
  return { style: {}, innerHTML: '', textContent: '',
           querySelectorAll: function () { return []; },
           classList: { toggle() {} } };
};
globalThis.window.scrollTo = function () {};
"""


def form_render(rel: str) -> str:
    """Собрать экран списка мини-аппа целиком и отдать готовый HTML.

    Ошибку шаблона разбором текста не поймать: страница просто останется пустой.
    Поэтому скрипт исполняется весь, с заглушками вместо браузера и сети.
    """
    js = NODE_STUBS + DOM_STUB + inline_script(rel) + r"""
setTimeout(function () {
  console.log('RESULT<' + JSON.stringify({ html: app.innerHTML }) + '>RESULT');
}, 50);
"""
    return _node(js)["html"]


def catalog_render(search: str) -> str:
    """Собрать каталог целиком, как в телефоне, и отдать готовый HTML.

    Скрипт исполняется весь, включая отрисовку: заглушки подменяют только
    браузер и сеть. Так ловятся ошибки шаблона, которых разбор текста не видит.
    """
    js = (NODE_STUBS.replace("'?u=tg_777'", repr(search).replace('"', "'"))
          + DOM_STUB + inline_script("kak-ty/app.html")) + r"""
setTimeout(function () {
  console.log('RESULT<' + JSON.stringify({ html: app.innerHTML }) + '>RESULT');
}, 50);
"""
    return _node(js)["html"]


def catalog(extra_js: str = "") -> Dict:
    """Прогнать чистую логику каталога «Как ты?»."""
    js = pure_block("kak-ty/app.html") + r"""
const OUT = {
  containers: LIFE_CONTAINERS,
  rhythms: RHYTHMS.map(r => r.id),
  registry: REGISTRY.map(r => ({
    key: r.key, label: r.label, days: r.days, section: r.section,
    containers: r.containers, group: r.group, what: r.what, size: r.size,
    url: r.url || null, phrase: r.phrase || null, cond: r.cond || null,
    once: !!r.once, after: r.after || null
  }))
};
""" + extra_js + r"""
console.log('RESULT<' + JSON.stringify(OUT) + '>RESULT');
"""
    return _node(js)


# --------------------------------------------------------------------------
# bot.py — только чтение, разбором AST
# --------------------------------------------------------------------------
_BOT_WANTED = {
    "LIFE_CONTAINERS", "CARD_META", "COVERAGE_MAP", "STATE_BLOCK_LINES",
    "INSTRUMENT_PAST_BLOCKS", "KAK_TY_KEYS", "STATE_BLOCKS_META",
    "INSTRUMENT_VALID", "VALID_RU", "VALID_DRAFT", "VALID_NONE",
}


def bot() -> Dict:
    """Реестры бота. Ключи полей сверяем по ним, а не по памяти."""
    src = BOT.read_text(encoding="utf-8")
    tree = ast.parse(src)
    picked = []
    found: Set[str] = set()
    for node in tree.body:
        name = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
        if name in _BOT_WANTED:
            picked.append(node)
            found.add(name)
    missing = _BOT_WANTED - found
    assert not missing, f"в bot.py не нашёл: {', '.join(sorted(missing))}"
    ns: Dict = {"Dict": Dict, "List": List, "Optional": Optional,
                "Set": Set, "Tuple": Tuple}
    exec(compile(ast.Module(body=picked, type_ignores=[]), "<bot>", "exec"), ns)
    return ns


def block_paths(b: Dict, block: str) -> Set[str]:
    """Пути, которые бот читает из блока: «pss.total» → берём как есть."""
    return {p for p, *_rest in b["STATE_BLOCK_LINES"].get(block, [])}


def dig(scores: Dict, path: str):
    """Достать значение по пути «инструмент.поле». Нет — None, не догадка."""
    cur = scores
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur
