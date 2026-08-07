# -*- coding: utf-8 -*-
"""Проверки: старые адреса замеров не показывают человеку ни балла, ни шкалы.

Задача. Каждый замер за лето переписывался по нескольку раз, и рядом с рабочей
страницей остались её прежние версии: `state-week/app.html`, `neurotype/app7.html`,
`weekly/index.html` и ещё четыре десятка. Из бота на них ссылок больше нет — но
ссылки живут в сообщениях Телеграма, а сообщения живут годами. Человек открывает
давнее напоминание и попадает на страницу, где ему в лицо показывают «PHQ-9
(Kroenke)» и «Настроение 22 · Диапазон 0–27». Ровно то, что убрано с рабочих
страниц: балл человек читает как приговор, хотя это просто сумма его ответов.

Решение. Файлы не удаляем — 404 хуже внятной страницы. Каждая старая версия
становится короткой страницей-переходом на свою актуальную.

Что проверяем:
  · ни один файл не пропал, и рядом с ним на месте актуальная версия;
  · на старой странице не осталось ни названия шкалы, ни балла — ни в тексте,
    ни в исходнике, и показать их страница физически больше не может;
  · переход исполняется по-настоящему в node и сохраняет хвост адреса: в нём
    приходит `u=tg_…`, без него страница не знает, чьи это замеры;
  · переход не ждёт Телеграма — значит работает и в обычном браузере;
  · адрес цели относительный, и это `replace`: старая страница не остаётся в
    истории, кнопка «назад» не возвращает человека сюда;
  · цель — тот адрес, который бот открывает сегодня, а не ещё одна старая версия;
  · страница ничего не спрашивает и ничего не пишет в базу;
  · без скриптов человек читает честную строку, куда идти, и без упрёка.

Запуск:  python3 checks/starye_stranicy.py
"""

import json
import re

import lib_path  # noqa: F401  — добавляет папку проверок в путь импорта
from lib import BOT, ROOT, _node, html, inline_script, ok, run, visible


def _chain(folder: str, names, target: str) -> dict:
    """Прежние версии одного замера и их актуальная страница."""
    return {f"{folder}/{n}": target for n in names}


# Старый адрес → относительный адрес актуальной страницы. Список прибит руками:
# посчитать его из папки значит согласиться с любым её состоянием, включая
# «старых версий больше нет, проверять нечего».
OLD = {
    # Подвижный слой. Недельный переписывался трижды, месячный и квартальный дважды.
    **_chain("state-week", ["app.html", "app2.html", "app3.html"], "app4.html"),
    **_chain("state-month", ["app.html", "app2.html"], "app3.html"),
    **_chain("state-quarter", ["app.html", "app2.html"], "app3.html"),
    # Самый первый недельный замер, ещё до подвижного слоя. Жил по адресу папки.
    "weekly/index.html": "../state-week/app4.html",
    # Разовые замеры: у каждого одна прежняя версия.
    "attachment/app.html": "app2.html",
    "decisions/app.html": "app2.html",
    "nervsystem/app.html": "app2.html",
    "stressrisk/app.html": "app2.html",
    "vulnerabilities/app.html": "app2.html",
    # Длинные цепочки версий. `index.html` — копия одной из них, тоже старая.
    **_chain("motivators", [
        "app.html", "app3.html", "app4.html", "app5.html", "app6.html",
        "app7.html", "app8.html", "app9.html", "index.html"], "app10.html"),
    **_chain("neurotype", [
        "app.html", "app2.html", "app3.html", "app4.html", "app5.html",
        "app6.html", "app7.html", "app8.html", "app9.html", "app10.html",
        "index.html"], "app11.html"),
    **_chain("personality-hexaco", [
        "app.html", "app3.html", "app4.html", "app5.html", "app6.html",
        "app7.html", "index.html"], "app8.html"),
    **_chain("values", [
        "app.html", "app3.html", "app4.html", "app5.html", "app6.html",
        "app7.html", "index.html"], "app8.html"),
}

# Полный список страниц в затронутых папках — на сегодня. Проверка на удаление:
# файл пропал, и человек по давней ссылке получает 404 вместо перехода.
INVENTORY = {
    "attachment": ["app.html", "app2.html"],
    "decisions": ["app.html", "app2.html"],
    "motivators": ["app.html", "app10.html", "app3.html", "app4.html",
                   "app5.html", "app6.html", "app7.html", "app8.html",
                   "app9.html", "index.html"],
    "nervsystem": ["app.html", "app2.html"],
    "neurotype": ["app.html", "app10.html", "app11.html", "app2.html",
                  "app3.html", "app4.html", "app5.html", "app6.html",
                  "app7.html", "app8.html", "app9.html", "index.html"],
    "personality-hexaco": ["app.html", "app3.html", "app4.html", "app5.html",
                           "app6.html", "app7.html", "app8.html", "index.html"],
    "state-month": ["app.html", "app2.html", "app3.html"],
    "state-quarter": ["app.html", "app2.html", "app3.html"],
    "state-week": ["app.html", "app2.html", "app3.html", "app4.html"],
    "stressrisk": ["app.html", "app2.html"],
    "values": ["app.html", "app3.html", "app4.html", "app5.html", "app6.html",
               "app7.html", "app8.html", "index.html"],
    "vulnerabilities": ["app.html", "app2.html"],
    "weekly": ["index.html"],
}

# Сокращения инструментов, которые встречались в этих файлах. Человек не должен
# видеть их нигде, а на странице-переходе им и лежать негде.
INSTRUMENTS = [
    "PHQ", "GAD", "WHO", "PANAS", "ISI", "PSS", "SWLS", "MLQ", "FFMQ", "RSES",
    "OLBI", "ASRM", "AUDIT", "BPNSFS", "MSPSS", "ASRS", "AQ", "HSPS", "MEQ",
    "EQ", "SQ", "HEXACO", "IPIP", "PVQ", "MFQ", "PID", "FMPS", "SD", "ECR",
    "REI", "AOT", "RFQ", "GCOS", "PTS", "DOSPERT", "IUS", "COPE", "ZTPI",
    "DSM", "APA", "ШПАНА", "ШВС",
]

# Машинерия опросника. Осталась — значит страница всё ещё может что-то посчитать
# и показать. Пустая страница-переход не умеет ни того, ни другого.
MACHINERY = [
    "TESTS", "SCORERS", "nums:", "pushToSupabase", "supabase", "fetch(",
    "localStorage", "addEventListener", "setTimeout", "<input", "<button",
    "<form", "<textarea", "Telegram",
]

# Слова про балл и норму — и в тексте, и в исходнике.
SCORE_WORDS = ["балл", "Диапазон", "диапазон", "норма", "Норма", "норм"]

# Упрёк и оценка. Человек пришёл, чтобы перестать себя винить.
BLAME_WORDS = [
    "забыл", "забросил", "давно не", "пропустил", "устарел ты", "поздно",
    "надо было", "жаль", "к сожалению", "ошибка", "неверн",
]

LATIN = re.compile(r"[A-Za-z]{2,}")
DIGIT = re.compile(r"\d")

STYLE_SCRIPT = re.compile(r"<(style|script)\b[^>]*>.*?</\1>", re.S | re.I)


def page_text(rel: str) -> str:
    """Текст, который человек читает на странице: без разметки, стилей и скрипта.

    Заголовок окна оставляем: его видно на вкладке, и «Личность — HEXACO» там
    такое же название шкалы, как в тексте.
    """
    return visible(STYLE_SCRIPT.sub(" ", html(rel)))


def title(rel: str) -> str:
    m = re.search(r"<title>(.*?)</title>", html(rel), re.S | re.I)
    assert m, f"{rel}: нет заголовка окна"
    return m.group(1).strip()


def go(rel: str, search: str, hash_: str) -> dict:
    """Открыть страницу так, как её открывает человек, и посмотреть, куда ушли.

    Телеграма в стабах нет намеренно: страница обязана переносить человека и в
    обычном браузере, без всякого мини-аппа.
    """
    stubs = r"""
globalThis.OUT = {};
Object.defineProperty(globalThis, 'location', {
  configurable: true, writable: true,
  value: {
    search: %s, hash: %s, pathname: '/старый/адрес.html',
    replace: function (u) { OUT.replaced = String(u); },
    assign: function (u) { OUT.assigned = String(u); },
    set href(u) { OUT.href = String(u); },
    get href() { return '/старый/адрес.html'; }
  }
});
""" % (json.dumps(search), json.dumps(hash_))
    code = stubs + inline_script(rel) + r"""
console.log('RESULT<' + JSON.stringify(globalThis.OUT) + '>RESULT');
"""
    return _node(code)


def check_nothing_deleted() -> None:
    """1. Ни один файл не удалён, и рядом лежит актуальная версия."""
    for folder, names in INVENTORY.items():
        d = ROOT / folder
        assert d.is_dir(), f"пропала папка {folder}"
        got = sorted(p.name for p in d.glob("*.html"))
        assert got == sorted(names), \
            f"в папке {folder} список страниц стал {got}"
    ok(f"все {sum(len(v) for v in INVENTORY.values())} страниц на месте, "
       f"ни одна не удалена")

    for rel, target in OLD.items():
        assert (ROOT / rel).exists(), f"пропал старый адрес {rel}"
        dest = (ROOT / rel).parent / target
        assert dest.exists(), f"{rel}: цели перехода {target} нет"
    ok(f"у всех {len(OLD)} старых адресов цель перехода существует")


def check_no_scale_no_score() -> None:
    """2. Ни названия шкалы, ни балла — ни в тексте, ни в исходнике."""
    for rel in OLD:
        text = page_text(rel)
        latin = sorted(set(LATIN.findall(text)))
        assert not latin, f"{rel}: латиница в тексте {latin}"
        assert not DIGIT.search(text), f"{rel}: цифра в тексте «{text.strip()}»"
        bad = [w for w in SCORE_WORDS if w in text]
        assert not bad, f"{rel}: {bad} в тексте"
        assert not LATIN.search(title(rel)), \
            f"{rel}: латиница в заголовке окна «{title(rel)}»"
    ok(f"на {len(OLD)} старых страницах человек не видит ни шкалы, ни балла")

    for rel in OLD:
        src = html(rel)
        hits = [a for a in INSTRUMENTS
                if re.search(r"(?<![A-Za-zА-Яа-яЁё0-9])" + a
                             + r"(?![a-zА-Яа-яЁё])", src)]
        assert not hits, f"{rel}: сокращение инструмента в исходнике: {hits}"
        bad = [w for w in SCORE_WORDS if w in src]
        assert not bad, f"{rel}: слово про балл в исходнике: {bad}"
    ok("в исходниках старых страниц не осталось ни одного сокращения шкалы")


def check_cannot_score_anymore() -> None:
    """3. Показать балл страница физически больше не может."""
    for rel in OLD:
        src = html(rel)
        left = [m for m in MACHINERY if m in src]
        assert not left, f"{rel}: осталась машинерия опросника: {left}"
        assert len(src) < 4000, \
            f"{rel}: страница на {len(src)} знаков — опросник так и не убран"
    ok("на старых страницах нет ни подсчёта, ни полей, ни записи в базу")


def check_redirect_keeps_query() -> None:
    """4. Переход сохраняет хвост адреса: и параметры, и якорь."""
    for rel, target in OLD.items():
        got = go(rel, "?u=tg_777&r=5", "#itog")
        assert got.get("replaced") == f"{target}?u=tg_777&r=5#itog", \
            f"{rel}: перешли на «{got.get('replaced')}», хвост адреса потерян"

        bare = go(rel, "", "")
        assert bare.get("replaced") == target, \
            f"{rel}: без параметров перешли на «{bare.get('replaced')}»"
    ok(f"все {len(OLD)} переходов доносят «u=tg_…» до актуальной страницы")


def check_works_without_telegram() -> None:
    """5. Переход не ждёт Телеграма — значит работает и в браузере."""
    for rel in OLD:
        s = inline_script(rel)
        for word in ("Telegram", "WebApp", "initData", "tg."):
            assert word not in s, f"{rel}: переход зависит от «{word}»"
        assert "setTimeout" not in s and "onload" not in s, \
            f"{rel}: переход отложен, человек успеет увидеть страницу"
    ok("переход срабатывает сразу и без Телеграма")


def check_relative_and_replace() -> None:
    """6. Адрес цели относительный, уход через replace."""
    for rel, target in OLD.items():
        assert not target.startswith(("/", "http")), \
            f"{rel}: адрес цели «{target}» не относительный"
        s = inline_script(rel)
        assert "location.replace" in s, \
            f"{rel}: уход не через replace — старый адрес останется в истории"
        assert "location.href" not in s and "location.assign" not in s, \
            f"{rel}: кроме replace есть другой способ ухода"
        got = go(rel, "?u=tg_777", "")
        assert "href" not in got and "assigned" not in got, \
            f"{rel}: страница уходит не только через replace: {got}"
        assert "://" not in got["replaced"] and not got["replaced"].startswith("/"), \
            f"{rel}: ушли на «{got['replaced']}» — адрес привязан к домену"
    ok("переход относительный и не оставляет старый адрес в истории")


def check_target_is_live() -> None:
    """7. Цель — тот адрес, который бот открывает сегодня."""
    bot_src = BOT.read_text(encoding="utf-8")
    catalog = html("kak-ty/app.html")
    for rel, target in OLD.items():
        dest = ((ROOT / rel).parent / target).resolve().relative_to(ROOT)
        addr = "/" + str(dest)
        assert addr in bot_src or addr in catalog, \
            f"{rel}: цель «{addr}» бот сегодня не открывает — это тоже старая версия"
        assert str(dest) not in OLD, \
            f"{rel}: переход ведёт на другую старую страницу «{dest}»"
    ok("все переходы ведут на страницы, которые бот открывает сегодня")


def check_honest_text() -> None:
    """8. Без скриптов человек читает, куда идти, и без упрёка."""
    for rel in OLD:
        src = html(rel)
        m = re.search(r"<noscript>(.*?)</noscript>", src, re.S | re.I)
        assert m, f"{rel}: без скриптов человек не видит ничего"
        text = visible(m.group(1))
        assert "Что со мной?" in text, \
            f"{rel}: не сказано, что замеры теперь в кнопке «Что со мной?»"
        assert "устарел" in text, f"{rel}: не сказано, что страница устарела"
        low = text.lower()
        blame = [w for w in BLAME_WORDS if w in low]
        assert not blame, f"{rel}: упрёк в тексте: {blame}"
    ok("на всех старых страницах честный текст без упрёка")


def check_titles_human() -> None:
    """9. Заголовок окна остался человеческим: человек узнаёт, куда попал."""
    for rel in OLD:
        t = title(rel)
        assert t, f"{rel}: заголовок окна пустой"
        assert not DIGIT.search(t), f"{rel}: цифра в заголовке «{t}»"
        assert len(t) <= 40, f"{rel}: заголовок «{t}» слишком длинный"
    ok("заголовки окон человеческие")


if __name__ == "__main__":
    raise SystemExit(run([
        check_nothing_deleted, check_no_scale_no_score,
        check_cannot_score_anymore, check_redirect_keeps_query,
        check_works_without_telegram, check_relative_and_replace,
        check_target_is_live, check_honest_text, check_titles_human,
    ]))
