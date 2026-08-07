# -*- coding: utf-8 -*-
"""Мутационная проверка: ломаем починку и смотрим, покраснеет ли проверка.

Зачем. Конституция, принцип II: «проверка обязана падать при сломанной логике —
иначе это не проверка, а украшение». Зелёный прогон сам по себе этого не
доказывает. Доказывает вот что: внести в страницу одну точную поломку — и
увидеть, что нужная проверка падает именно на ней.

Как устроено. Каждая мутация — одна замена в одном файле страницы. Скрипт:

1. правит файл,
2. запускает ОДНУ проверку из `progress_ne_teryaetsya.py` отдельным процессом,
3. ждёт от неё падения,
4. возвращает файл байт в байт.

Файл восстанавливается в `finally` и, для страховки, проверяется по хешу в
конце: репозиторий обязан остаться таким же, каким был.

Запуск:  python3 checks/progress_mutacii.py
"""

import hashlib
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
from lib import ROOT, ok, run

CHECKS = Path(__file__).resolve().parent

# (что ломаем · файл · было · стало · какая проверка обязана покраснеть)
MUTATIONS: List[Tuple[str, str, str, str, str]] = [
    ("черновик не пишется вовсе",
     "state-domains/app.html",
     "  seen[key] = true;\n  // После КАЖДОГО ответа, не в конце.",
     "  seen[key] = true;\n  if (false) // После КАЖДОГО ответа, не в конце.",
     "check_draft_saved_after_each_answer"),

    ("черновик пишется только в конце замера",
     "state-domains/app.html",
     "function saveDraft() {\n  try {",
     "function saveDraft() {\n  if (firstUnseenKey(answers, flags, seen) !== null) return;\n  try {",
     "check_draft_saved_after_each_answer"),

    ("набранный текст не сохраняется",
     "state-note/app.html",
     "      state.draft = field.value;\n      saveDraft();",
     "      state.draft = field.value;",
     "check_draft_saved_after_each_answer"),

    ("восстановление тихое: строки про продолжение нет",
     "state-domains/app.html",
     "    resume +\n    banner +",
     "    banner +",
     "check_return_is_visible_and_explicit"),

    ("начать заново негде",
     "state-domains/app.html",
     '<button class="secondary" id="startBtn">Начать заново</button>',
     '<button class="secondary" id="startBtn">Дальше</button>',
     "check_return_is_visible_and_explicit"),

    ("продолжение открывает начало, а не первый непройденный",
     "state-domains/app.html",
     "  var nk = firstUnseenKey(answers, flags, seen);",
     "  var nk = visibleSteps(answers, flags)[0].key;",
     "check_return_opens_first_unanswered"),

    ("период черновика не проверяется",
     "state-domains/app.html",
     "  if (d.periodKey !== periodKey(nowIso)) return false;",
     "  if (false) return false;",
     "check_foreign_period_not_restored"),

    ("срок черновика — одно число на всех",
     "state-domains/app.html",
     "function draftTtlDays() { return PERIOD_DAYS <= 1 ? 1 : PERIOD_DAYS; }",
     "function draftTtlDays() { return 30; }",
     "check_ttl_comes_from_rhythm"),

    ("черновик не стирается после отправки",
     "state-domains/app.html",
     "    // копия ответов человека.\n    clearDraft();",
     "    // копия ответов человека.",
     "check_draft_cleared_after_send"),

    ("провал отправки объявлен успехом",
     "state-domains/app.html",
     '    "<h1>" + esc(state.sync === "ok" ? RESULT_TITLE\n'
     '      : (state.sync === "error" ? SEND_FAIL_TITLE : SEND_WAIT_TITLE)) + "</h1>" +',
     '    "<h1>" + esc(RESULT_TITLE) + "</h1>" +',
     "check_failed_send_is_visible"),

    ("ключ записи переехал",
     "state-domains/app.html",
     'return { scores: { pwi: pwi, source: "manual" }, has: true };',
     'return { scores: { pwi_v2: pwi, source: "manual" }, has: true };',
     "check_record_shape_frozen"),

    ("черновик уезжает в облако",
     "state-domains/app.html",
     "function saveDraft() {\n  try {",
     "function saveDraft() {\n  try { window.Telegram.WebApp.CloudStorage.setItem('d', '1', function () {}); } catch (e) {}\n  try {",
     "check_draft_never_leaves_the_phone"),

    ("страница с тестами: результат помечен сделанным до ответа сервера",
     "state-week/app4.html",
     "  const okPush = await pushToSupabase(record);",
     "  saveResultsLocal();\n  saveToCloud();\n  clearProgress();\n"
     "  const okPush = await pushToSupabase(record);",
     "check_failed_send_is_visible"),

    ("страница с тестами: повторить отправку нечем",
     "state-week/app4.html",
     "      ${state.sync === 'error' ? `<button onclick=\"retryStore('${key}')\">"
     "Записать ещё раз</button>` : ''}\n",
     "",
     "check_failed_send_is_visible"),

    ("страница с тестами: строки про начатое нет в списке",
     "state-week/app4.html",
     "    ${resumeNote()}\n",
     "",
     "check_return_is_visible_and_explicit"),

    ("страница с тестами: продолжение открывает первый пункт",
     "state-week/app4.html",
     "  const idx = firstUnansweredIdx(d.key, state.answers);",
     "  const idx = 0;",
     "check_return_opens_first_unanswered"),

    ("страница с тестами: ячейка черновика переименована",
     "state-week/app4.html",
     "const STORE_KEY = 'state_week_' + CLIENT_ID;",
     "const STORE_KEY = 'state_week_draft2_' + CLIENT_ID;",
     "check_storage_keys_frozen"),

    ("страница с тестами: в базу уезжает всё, что лежит в памяти",
     "state-week/app4.html",
     "function buildScores() {\n  // В scores складываем всё, что уже снято, плюс метку источника\n"
     "  const scores = {source: 'manual'};\n  sessionKeys().forEach(k => {",
     "function buildScores() {\n  // В scores складываем всё, что уже снято, плюс метку источника\n"
     "  const scores = {source: 'manual'};\n  ownKeys().forEach(k => {",
     "check_draft_not_persisted_into_record"),

    ("суточная: черновик не подставляется",
     "state-day/app.html",
     "  draftRestored = true;\n})();",
     "  draftRestored = false;\n})();",
     "check_return_is_visible_and_explicit"),

    ("суточная: черновик не стирается после отправки",
     "state-day/app.html",
     "    clearDraft();\n    draftRestored = false;",
     "    draftRestored = false;",
     "check_draft_cleared_after_send"),
]


def _one_check(name: str) -> int:
    """Прогнать одну проверку отдельным процессом. Вернуть её код выхода."""
    code = (
        "import lib_path\n"
        "from lib import run\n"
        "import progress_ne_teryaetsya as C\n"
        "raise SystemExit(run([getattr(C, %r)]))\n" % name
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(CHECKS) + os.pathsep + env.get("PYTHONPATH", "")
    r = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT),
                       capture_output=True, text=True, env=env, timeout=1800)
    return r.returncode


def check_mutations_are_caught() -> None:
    """1. Каждая поломка ловится проверкой, и файл возвращается на место."""
    before = {}
    for _, rel, *_ in MUTATIONS:
        p = ROOT / rel
        before[rel] = p.read_text(encoding="utf-8")

    caught = 0
    misses = []
    for what, rel, old, new, check in MUTATIONS:
        path = ROOT / rel
        src = before[rel]
        n = src.count(old)
        assert n == 1, f"«{what}»: место мутации в {rel} встречается {n} раз"
        try:
            path.write_text(src.replace(old, new, 1), encoding="utf-8")
            rc = _one_check(check)
            if rc == 0:
                misses.append(f"{what} → {check} осталась зелёной")
            else:
                caught += 1
                print(f"  ловит  {what}  →  {check}")
        finally:
            path.write_text(src, encoding="utf-8")

    # Файлы обязаны вернуться байт в байт.
    for rel, src in before.items():
        got = (ROOT / rel).read_text(encoding="utf-8")
        assert hashlib.sha256(got.encode()).digest() == \
            hashlib.sha256(src.encode()).digest(), \
            f"{rel} не вернулся к исходному состоянию"

    assert not misses, "не поймано: " + "; ".join(misses)
    ok(f"все {caught} поломок из {len(MUTATIONS)} пойманы, страницы вернулись на место")


def check_every_requirement_has_a_mutation() -> None:
    """2. У каждого требования задания есть хотя бы одна поломка."""
    used = {m[4] for m in MUTATIONS}
    must = {
        "check_draft_saved_after_each_answer",   # сохранение после каждого ответа
        "check_return_is_visible_and_explicit",  # видно, что продолжаешь
        "check_return_opens_first_unanswered",   # первый непройденный вопрос
        "check_foreign_period_not_restored",     # свой период
        "check_ttl_comes_from_rhythm",           # срок от периода
        "check_draft_cleared_after_send",        # после отправки пусто
        "check_failed_send_is_visible",          # провал виден
        "check_record_shape_frozen",             # ключи записи не поехали
        "check_storage_keys_frozen",             # ячейки памяти не поехали
        "check_draft_not_persisted_into_record",  # черновик не тянет прошлое
        "check_draft_never_leaves_the_phone",    # черновик остаётся на телефоне
    }
    missing = must - used
    assert not missing, "без мутации остались: " + ", ".join(sorted(missing))
    ok(f"{len(must)} требований закрыты мутациями")


if __name__ == "__main__":
    raise SystemExit(run([
        check_every_requirement_has_a_mutation,
        check_mutations_are_caught,
    ]))
