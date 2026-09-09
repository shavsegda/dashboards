// Чистые функции расчёта. DOM здесь не трогаем.

import { NORMS, TEST_NORMS } from './forma-norms.js';

// Узлы перцентильных таблиц в порядке возрастания. p20/p80 добавлены ради
// категорий Strength Level (Beginner=p5, Novice=p20, Intermediate=p50,
// Advanced=p80, Elite=p95) — старые таблицы их не используют и не страдают.
const NODES = ['p5', 'p10', 'p20', 'p25', 'p50', 'p75', 'p80', 'p90', 'p95'];

// Считаем, на каком перцентиле стоит значение, линейно интерполируя между узлами
export function percentile(value, table) {
  const points = NODES
    .filter((key) => typeof table[key] === 'number')
    .map((key) => ({ p: Number(key.slice(1)), v: table[key] }));

  if (points.length === 0) return null;
  if (value <= points[0].v) return value < points[0].v ? 0 : points[0].p;
  const last = points[points.length - 1];
  if (value >= last.v) return value > last.v ? 100 : last.p;

  for (let i = 0; i < points.length - 1; i += 1) {
    const a = points[i];
    const b = points[i + 1];
    if (value >= a.v && value <= b.v) {
      const share = (value - a.v) / (b.v - a.v);
      return a.p + share * (b.p - a.p);
    }
  }
  return null;
}

// Нейтральные названия уровней. Никаких унижающих слов.
export function levelFromPercentile(p) {
  if (p === null || p === undefined) return null;
  if (p < 20) return 'начальный уровень';
  if (p < 40) return 'ниже среднего';
  if (p < 70) return 'средний';
  if (p < 90) return 'выше среднего';
  return 'продвинутый';
}

// Age grading: результат в процентах от открытого мирового стандарта
// для своего пола и возраста (система World Masters Athletics)
export function ageGrade(sex, age, distanceKm, timeSec) {
  const entry = NORMS.running[sex][String(distanceKm)];
  if (!entry) return null; // нет данных по этой дистанции (например, миля — см. отчёт)
  const bucket = ageBucket(age, entry.factors);
  if (bucket === undefined) return null; // пустая таблица коэффициентов
  const factor = entry.factors[bucket];
  const ageStandard = entry.openStandardSec / factor;
  return (ageStandard / timeSec) * 100;
}

// Классификация уровня age grading по шкале WMA/USATF Masters
export function ageGradeClass(pct) {
  if (pct < 50) return 'начальный уровень';
  if (pct < 60) return 'местный уровень';
  if (pct < 70) return 'региональный уровень';
  if (pct < 80) return 'национальный уровень';
  if (pct < 90) return 'мировой уровень';
  return 'уровень мирового рекорда';
}

// Общий помощник: выбор ближайшего ключа объекта снизу по числовому параметру.
// Один помощник на все таблицы со сплошной (без дыр) шкалой — коэффициенты
// age grading, перцентили VO2max, таблица дожития, состав тела, восстановление,
// а с задачи 4 ещё и силовые тесты Strength Level (там ключ — вес тела, не
// возраст, но алгоритм тот же: ближайший ключ снизу). За пределами таблицы
// берём крайнее значение. Для пустого объекта возвращает undefined —
// вызывающий код должен это проверить сам. Для шкал С ДЫРАМИ (ступени ГТО)
// не подходит — там используется matchAgeRange(), которая умеет возвращать
// «нет данных», а не подставлять соседний бакет.
function ageBucket(age, buckets) {
  const keys = Object.keys(buckets).map(Number).sort((a, b) => a - b);
  let chosen = keys[0];
  for (const k of keys) if (age >= k) chosen = k;
  return chosen;
}

// Таблица перцентилей VO2max (реестр FRIEND) для нужного пола и возраста
export function vo2maxTable(sex, age) {
  const bySex = NORMS.vo2max[sex];
  return bySex[ageBucket(age, bySex)];
}

// Линейная интерполяция возраста между двумя соседними узлами «медиана
// VO2max → возраст». Если у соседних узлов одинаковая медиана (a.v === b.v),
// делить не на что — возвращаем возраст левого узла вместо NaN от деления
// на ноль. Вынесена отдельной экспортированной функцией, чтобы можно было
// проверить именно эту защиту напрямую, без внешних отсечек по краям таблицы.
export function interpolateBodyAge(vo2max, a, b) {
  if (a.v === b.v) return a.age;
  const share = (a.v - vo2max) / (a.v - b.v);
  return Math.round(a.age + share * (b.age - a.age));
}

// Возраст тела: ищем возраст, в котором собственный VO2max человека
// является медианой (p50). Между узлами интерполируем линейно,
// за краями таблицы обрезаем крайним значением.
export function bodyAgeFromVo2max(vo2max, sex) {
  const bySex = NORMS.vo2max[sex];
  const ages = Object.keys(bySex).map(Number).sort((a, b) => a - b);
  const medians = ages.map((a) => ({ age: a + 5, v: bySex[a].p50 })); // центр десятилетия

  if (vo2max >= medians[0].v) return medians[0].age;
  const last = medians[medians.length - 1];
  if (vo2max <= last.v) return last.age;

  for (let i = 0; i < medians.length - 1; i += 1) {
    const a = medians[i];
    const b = medians[i + 1];
    if (vo2max <= a.v && vo2max >= b.v) {
      return interpolateBodyAge(vo2max, a, b);
    }
  }
  return last.age;
}

// До скольки лет в среднем доживает человек.
// Важно: к ПАСПОРТНОМУ возрасту прибавляем остаток жизни, ожидаемый у человека
// с таким ВОЗРАСТОМ ТЕЛА. Прибавлять остаток к возрасту тела нельзя — из-за
// эффекта дожития получится, что молодое тело живёт меньше старого
// (у молодого тела остаток жизни исчисляется от малого возраста в таблице
// смертности, и складывать его с возрастом тела, а не с паспортным, занизит итог).
export function lifeExpectancy(bodyAge, chronoAge, sex) {
  const table = NORMS.lifeTable[sex];
  const remaining = table[ageBucket(bodyAge, table)];
  return Math.round(chronoAge + remaining);
}

// Индекс физической активности (шкала Kurtze, используется в модели Nes/Wisløff,
// HUNT Study). Частота × интенсивность × продолжительность тренировки.
// Источник программно доступен в NORMS.ntnuFormula.activityIndexSource
// (Bye A. и соавт., PLoS ONE, 2013 — см. normy-vo2max.md, набор 3).
function kurtzeIndex(trainingFreq, trainingIntensity, trainingDuration) {
  return trainingFreq * trainingIntensity * trainingDuration;
}

// Оценка VO2peak без нагрузочного теста — формула HUNT/NTNU (Nes, Janszky,
// Vatten, Nilsen, Aspenes, Wisløff, MSSE, 2011), версия с ИМТ вместо окружности
// талии, подтверждённая дословной цитатой в Jalene S. и соавт., Frontiers in
// Physiology, 2019 (см. normy-vo2max.md, набор 3). Версия с окружностью талии
// не подтверждена рецензируемым источником и намеренно не используется.
// Источник программно доступен в NORMS.ntnuFormula.source.
function estimateVo2maxNTNU({ sex, age, bmi, restingHR, trainingFreq, trainingIntensity, trainingDuration }) {
  const pa = kurtzeIndex(trainingFreq, trainingIntensity, trainingDuration);
  if (sex === 'f') {
    return 70.77 - 0.244 * age - 0.749 * bmi - 0.107 * restingHR + 0.213 * pa;
  }
  return 92.05 - 0.327 * age - 0.933 * bmi - 0.167 * restingHR + 0.257 * pa;
}

// Фитнес-возраст NTNU — запасной путь, когда VO2max неизвестен.
// Сначала оцениваем VO2peak по неспортивным показателям, потом переводим
// его в возраст тела через ту же таблицу FRIEND.
export function fitnessAgeNTNU({ sex, age, bmi, restingHR, trainingFreq, trainingIntensity, trainingDuration }) {
  const estimated = estimateVo2maxNTNU({ sex, age, bmi, restingHR, trainingFreq, trainingIntensity, trainingDuration });
  return bodyAgeFromVo2max(estimated, sex);
}

// Состав тела: четыре показателя, каждый со своим источником и оговорками
export function bodyComposition({ sex, age, height, weight, bodyFatPct, limbMuscleKg, waist }) {
  const heightM = height / 100;

  const smiValue = limbMuscleKg / (heightM * heightM);
  const smiThreshold = NORMS.smi.threshold[sex];

  const bmiValue = weight / (heightM * heightM);
  const wthrValue = waist / height;

  const bodyFatPercentile = percentile(bodyFatPct, NORMS.bodyFat[sex][ageBucket(age, NORMS.bodyFat[sex])]);

  return {
    bodyFat: {
      value: bodyFatPct,
      percentile: bodyFatPercentile,
      level: bodyFatLevel(bodyFatPercentile), // у процента жира меньше значит лучше
      note: 'Перцентиль рассчитан по измерениям методом DXA (NHANES). Бытовые весы с биоимпедансом дают отклонение в среднем 3-4 процентных пункта, иногда больше — направление ошибки зависит от модели весов. Следите за динамикой своих замеров на одних и тех же весах, а не за точным попаданием в перцентиль.',
      reference: NORMS.bodyFat.source,
    },
    smi: {
      value: smiValue,
      flag: smiValue < smiThreshold ? 'ниже порога саркопении' : 'в норме',
      reference: NORMS.smi.source,
    },
    bmi: {
      value: bmiValue,
      category: bmiCategory(bmiValue),
      note: 'При развитой мускулатуре ИМТ завышает оценку жировой массы. Смотреть вместе с процентом жира.',
      reference: NORMS.bmi.source,
    },
    waistToHeight: {
      value: wthrValue,
      flag: wthrValue >= NORMS.waistToHeight.threshold ? 'выше порога' : 'в норме',
      reference: NORMS.waistToHeight.source,
    },
  };
}

// У процента жира шкала перевёрнута: меньше — лучше. percentile() построен
// по возрастающей таблице (больше жира — выше перцентиль в таблице), поэтому
// для уровня инвертируем перцентиль: 100 минус исходное значение.
function bodyFatLevel(p) {
  if (p === null || p === undefined) return null;
  return levelFromPercentile(100 - p);
}

// Категории ИМТ по ВОЗ. Пороги — данные, лежат в NORMS.bmi.thresholds
// (forma-norms.js), здесь только логика сравнения.
function bmiCategory(bmi) {
  const { underweight, normal, overweight, obeseI, obeseII } = NORMS.bmi.thresholds;
  if (bmi < underweight) return 'недостаточный вес';
  if (bmi < normal) return 'норма';
  if (bmi < overweight) return 'избыточный вес';
  if (bmi < obeseI) return 'ожирение I степени';
  if (bmi < obeseII) return 'ожирение II степени';
  return 'ожирение III степени';
}

// Восстановление: пульс покоя — по возрастной норме, HRV и регулярность сна —
// без готовой возрастной нормы (см. forma-norms.js), поэтому даём личный тренд
export function recovery({ sex, age, restingHR, rmssd, bedtimeSdMin }) {
  const hrPercentile = percentile(-restingHR, reversed(NORMS.restingHR[sex][ageBucket(age, NORMS.restingHR[sex])]));

  return {
    restingHR: {
      value: restingHR,
      percentile: hrPercentile,
      level: levelFromPercentile(hrPercentile),
      reference: NORMS.restingHR.source,
    },
    rmssd: {
      value: rmssd,
      note: 'Разброс между людьми огромный, а метаанализ Nunan с соавт. не даёт возрастной разбивки — только общий диапазон 19-75 мс у здоровых взрослых. Значение имеет смысл смотреть как личный тренд, а не сравнивать с чужими цифрами.',
      reference: NORMS.rmssd.source,
    },
    sleepRegularity: {
      value: bedtimeSdMin,
      flag: null, // порога в минутах в источниках нет — см. note
      note: 'В источнике (Windred и др., 2024) регулярность сна измеряется индексом SRI (0-100) по многодневной актиграфии, а не стандартным отклонением времени отбоя в минутах. Порога в минутах в собранных источниках нет, поэтому флаг «регулярно/нерегулярно» здесь не рассчитывается — смотрите на динамику времени отбоя.',
      reference: NORMS.sleepRegularity.source,
    },
  };
}

// Складывает содержательную пометку источника (например, протокол
// измерения или оговорку про точность) с дополнительной служебной пометкой
// (например, «нормы не опубликованы») — не затирает одну другой, как было
// раньше (правка по итогам ревью задачи 4).
function appendNote(base, extra) {
  return base ? `${base} ${extra}` : extra;
}

// Ищет диапазон возраста, в который попадает человек, среди ОПУБЛИКОВАННЫХ
// диапазонов ступеней ГТО. В отличие от ageBucket() (берёт ближайший ключ
// СНИЗУ и всегда что-то возвращает — годится для сплошных шкал вроде
// FRIEND/NHANES), ступени ГТО образуют шкалу С ДЫРАМИ: между собранными
// ступенями есть возраста, для которых у нас просто нет опубликованных
// чисел. matchAgeRange() возвращает undefined в дыре — это осознанное
// отсутствие данных, а не ошибка выбора бакета.
function matchAgeRange(age, ranges) {
  return ranges.find((r) => age >= r.ageMin && age <= r.ageMax);
}

// Знак ГТО по официальным порогам конкретной ступени — не перцентиль.
function badgeFromThresholds(value, { bronze, silver, gold }) {
  if (value >= gold) return 'золото';
  if (value >= silver) return 'серебро';
  if (value >= bronze) return 'бронза';
  return 'ниже бронзы';
}

// Единая оценка простого теста силы/мощности/подвижности по таблицам
// TEST_NORMS. Один движок на все одиннадцать тестов задачи 4 — не плодим
// по функции на тест. profile — { sex, age, bodyWeight }.
//
// result.level — ВСЕГДА либо словарь levelFromPercentile() («средний»,
// «выше среднего» и т.д.), либо null. Знак ГТО живёт ТОЛЬКО в result.badge
// («золото»/«серебро»/«бронза»/«ниже бронзы») — раньше badge дублировался
// и в level тоже, из-за чего в одном поле жили два разных словаря (правка
// по итогам повторного ревью задачи 4).
export function evaluateTest(testKey, value, profile) {
  const spec = TEST_NORMS[testKey];
  if (!spec) return null; // неизвестный тест — не падаем, отдаём null

  const result = {
    key: testKey,
    block: spec.block,
    label: spec.label,
    unit: spec.unit,
    value,
    percentile: null,
    level: null,
    badge: null, // знак ГТО для тестов-badgeTest (pullups, broadjump), иначе null; НЕ дублируется в level
    secondaryPercentile: null, // второе, независимое чтение того же источника (см. spec.secondary)
    secondaryLevel: null,
    secondaryLabel: spec.secondary ? spec.secondary.label : null,
    informational: Boolean(spec.informational),
    belowThreshold: spec.threshold !== undefined ? value < spec.threshold : null,
    reference: spec.source,
    note: spec.note ?? null,
  };

  // Справочные тесты (планка, вис на перекладине) — без перцентиля,
  // опубликованных возрастных норм для них нет.
  if (spec.informational) return result;

  // Тесты-«знаки» ГТО (подтягивания, прыжок в длину): у ГТО нет
  // перцентильной кривой, есть только три официальных порога на ступень.
  // Отдаём знак и точную ступень, в которую попал возраст, а не выдуманный
  // перцентиль поверх этих порогов (правка по итогам ревью задачи 4).
  if (spec.badgeTest) {
    const ranges = spec[profile.sex];
    const range = ranges && matchAgeRange(profile.age, ranges);
    if (!range) {
      result.note = appendNote(result.note, 'норматив для этого возраста не опубликован (нет собранной ступени ГТО)');
      return result;
    }
    result.badge = badgeFromThresholds(value, range);
    return result;
  }

  // Основной перцентиль — ВСЕГДА по полу и ВОЗРАСТУ, как и весь остальной
  // продукт (правка по итогам повторного ревью: раньше силовые тесты
  // индексировались по весу тела как по основной оси — эта таблица источника
  // возраст вообще не хранит и откалибрована на плато 25-40 лет, из-за чего
  // пожилой человек получал сильно завышенный или заниженный разряд вместо
  // честного «по твоему возрасту»). Тесты, для которых норма опубликована
  // только до определённого возраста (отжимания CSEP-PATH — до 69, наклон
  // вперёд сидя CHMS — до 69, сила хвата Wang/JOSPT — до 85, силовые
  // Strength Level — до 90, это реальный предел ИМЕННО возрастной таблицы),
  // за пределами дают не «неизвестно», а прямо подтверждённое отсутствие
  // норматива: раньше возраст вне таблицы молча получал ближайший (чужой) бакет.
  if (spec.maxAge === undefined || profile.age <= spec.maxAge) {
    const bySex = spec[profile.sex];
    if (bySex) {
      const table = bySex[ageBucket(profile.age, bySex)];
      result.percentile = percentile(value, table);
      result.level = levelFromPercentile(result.percentile);
    }
  } else {
    result.note = appendNote(result.note, 'нормы для этого возраста не опубликованы');
  }

  // Вторичное, независимое чтение — по весу тела (сейчас только у силовых
  // тестов Strength Level: spec.secondary). Считается НЕЗАВИСИМО от основного
  // и не участвует в нём — источник публикует таблицу «по весу тела» отдельно
  // от таблицы «по возрасту», совмещать их значило бы придумывать двумерную
  // поверхность, которой источник не даёт (та самая самодельная свёртка,
  // которую в проекте запрещено делать). Работает независимо от возраста и
  // от maxAge основной таблицы — весовая таблица возраст вообще не хранит.
  // Без корректного веса тела вторичное чтение просто остаётся null — раньше
  // здесь было деление на profile.bodyWeight без проверки, и нулевой вес тела
  // давал Infinity → percentile 100 → «продвинутый»; теперь тихо подставлять
  // это как разряд нельзя нигде, в том числе во вторичном чтении.
  if (spec.secondary) {
    const w = profile.bodyWeight;
    if (typeof w === 'number' && Number.isFinite(w) && w > 0) {
      const bySexW = spec.secondary[profile.sex];
      if (bySexW) {
        const tableW = bySexW[ageBucket(w, bySexW)];
        result.secondaryPercentile = percentile(value, tableW);
        result.secondaryLevel = levelFromPercentile(result.secondaryPercentile);
      }
    }
  }

  return result;
}

// ---------------------------------------------------------------------
// Задача 6: счёт формы, цена провала, слабое звено. Три сводки поверх
// результатов evaluateTest/bodyComposition/recovery — сюда приходит общий
// плоский список { key, block, percentile, informational, belowThreshold,
// badge?, sex? } (форма собирает его из результатов прошлых задач).

// Шесть блоков дашборда. Если по блоку вообще нет результатов — блок серый
// и не участвует ни в счёте формы, ни в поиске слабого звена.
const BLOCKS = ['endurance', 'strength', 'power', 'mobility', 'body', 'recovery'];

// Знак ГТО имеет естественный, официально опубликованный порядок: ниже
// бронзы < бронза < серебро < золото. Это структура самого норматива, а не
// наша выдумка — заводим одну карту знак → порядковый номер и переиспользуем
// её везде, где нужно сравнивать знаки между собой (счёт формы, слабое
// звено, провал в карточке риска), вместо трёх раздельных проверок строк.
const BADGE_ORDER = {
  'ниже бронзы': 0,
  'бронза': 1,
  'серебро': 2,
  'золото': 3,
};

// Годный для счёта результат: не справочный (не informational) и содержит
// либо перцентиль (числом), либо знак ГТО (badge) — у знака ГТО перцентиля
// нет и быть не может (это опубликованный разряд, а не позиция в
// перцентильном распределении), но это не повод выкидывать тест из счёта.
function isCountable(r) {
  if (r.informational) return false;
  return typeof r.percentile === 'number' || typeof r.badge === 'string';
}

// Тест на медиане или выше. Для знака ГТО перцентиля нет — вместо него
// используем сам разряд по BADGE_ORDER: серебро и золото официально
// означают «на уровне или выше нормы для этой ступени», бронза и «ниже
// бронзы» — «не дотянул». Подменять это выдуманным числом перцентиля
// нельзя, поэтому знак и перцентиль оцениваются каждый по своей логике,
// а не приводятся к общей шкале.
function isAtOrAboveMedian(r) {
  if (typeof r.percentile === 'number') return r.percentile >= 50;
  if (typeof r.badge === 'string') return (BADGE_ORDER[r.badge] ?? -1) >= BADGE_ORDER['серебро'];
  return false;
}

// Счёт формы: по каждому из шести блоков — зелёный (больше половины тестов
// блока на медиане или выше), красный (половина или меньше) либо серый
// (в блоке вообще нет годных результатов). green — сколько блоков зелёных,
// counted — сколько блоков вообще участвовало в счёте (не серых).
export function formScore(results) {
  const byBlock = {};
  let green = 0;
  let counted = 0;

  for (const block of BLOCKS) {
    const items = results.filter((r) => r.block === block && isCountable(r));
    if (items.length === 0) {
      byBlock[block] = 'grey';
      continue;
    }
    counted += 1;
    const atOrAboveMedian = items.filter(isAtOrAboveMedian).length;
    const isGreen = atOrAboveMedian > items.length / 2;
    byBlock[block] = isGreen ? 'green' : 'red';
    if (isGreen) green += 1;
  }

  return { green, counted, byBlock };
}

// Достаёт значение, которое может быть либо общим на всех, либо разбитым
// по полу как { m, f } — так устроены и hazard, и ci у отношения талии к
// росту (Patel 2025 публикует разные цифры для мужчин и женщин). Без
// указанного пола у результата для разбитого по полу значения возвращаем
// null, а не чужую цифру — это и есть выдумывание числа.
function sexSplitOrPlain(value, sex) {
  if (value === null || value === undefined) return null;
  if (typeof value === 'object' && ('m' in value || 'f' in value)) {
    const v = value[sex];
    return v === undefined ? null : v;
  }
  return value;
}

// Знак ГТО «бронза» или «ниже бронзы» — провал по опубликованному разряду,
// ровно так же, как нижняя четверть перцентильного распределения. Сейчас ни
// у одного badge-теста (подтягивания, прыжок в длину) нет записи в
// NORMS.hazards, поэтому эта ветка пока ничего не включает на практике —
// но как только коэффициент риска для badge-теста появится, знак должен
// уметь стать причиной карточки, а не молча теряться из-за отсутствия
// перцентиля (правка по итогам ревью задачи 6 — раньше ветки для badge
// не было вовсе).
function badgeIndicatesFailure(badge) {
  const rank = BADGE_ORDER[badge];
  return typeof rank === 'number' && rank <= BADGE_ORDER['бронза'];
}

// Порядок разделов на экране — фиксированный, это НЕ рейтинг между ними.
// Общая смертность и сердечно-сосудистые события — принципиально разные
// исходы: коэффициент 25 у отжиманий (сердечно-сосудистые события, когорта
// 1104 пожарных, всего 37 событий, доверительный интервал после переворота
// примерно 2,78–100) не означает «риск умереть в 25 раз выше», чем у
// показателей общей смертности с коэффициентом 1,1–5 — это разные вещи,
// разного качества доказательности, и класть их в один отсортированный
// список означало бы визуально соврать (правка по итогам ревью задачи 6).
const OUTCOME_ORDER = ['общая смертность', 'сердечно-сосудистые события'];

// Цена провала: карточки риска смертности/сердечно-сосудистых событий,
// сгруппированные по исходу. Риски РАЗНЫХ тестов не суммируются —
// показатели связаны между собой (например, сила хвата и мышечная масса),
// и сумма дала бы двойной счёт. Каждая карточка живёт отдельно, со своим
// hazard, доверительным интервалом и размером когорты (где источник их
// даёт — иначе поле остаётся пустым, не выдумываем), своим condition (что
// именно сравнивали — осознанное расширение сверх интерфейса из брифа, см.
// отчёт), своим outcome и своим источником. Нет опубликованного
// коэффициента для показателя (NORMS.hazards[key] отсутствует) — карточки
// для него нет. Возвращает МАССИВ ГРУПП { outcome, cards }, а не плоский
// список — сравнивать карточки МЕЖДУ группами нельзя (см. OUTCOME_ORDER
// выше), внутри группы карточки отсортированы по убыванию hazard.
export function riskCards(results) {
  const cards = [];
  for (const r of results) {
    const h = NORMS.hazards[r.key];
    if (!h) continue; // нет опубликованного коэффициента — не выдумываем

    const hazard = sexSplitOrPlain(h.hazard, r.sex);
    if (typeof hazard !== 'number') continue; // коэффициент по полу, а пол не указан

    // «Провал» — явный флаг по опубликованному порогу (belowThreshold, как
    // у стойки на одной ноге — там вообще нет перцентильной кривой), нижняя
    // четверть перцентильного распределения, либо знак ГТО не выше бронзы.
    const failed = r.belowThreshold === true
      || (typeof r.percentile === 'number' && r.percentile < 25)
      || badgeIndicatesFailure(r.badge);
    if (!failed) continue;

    cards.push({
      testKey: r.key,
      label: TEST_NORMS[r.key]?.label ?? h.label ?? r.key,
      hazard,
      condition: h.condition,
      outcome: h.outcome,
      ci: sexSplitOrPlain(h.ci ?? null, r.sex),
      cohortSize: h.cohortSize ?? null,
      reference: h.source,
    });
  }

  const groups = [];
  for (const outcome of OUTCOME_ORDER) {
    const inOutcome = cards.filter((c) => c.outcome === outcome).sort((a, b) => b.hazard - a.hazard);
    if (inOutcome.length > 0) groups.push({ outcome, cards: inOutcome });
  }
  return groups;
}

// Слабое звено — два разных утверждения, и смешивать их в одно число
// нельзя (правка по итогам повторного ревью задачи 6: раньше знак ГТО
// раскладывался в число 0/33,3/66,7/100 и усреднялся с настоящими
// перцентилями — самодельная шкала, которую никто не публиковал). Ровно
// та же честность, что уже есть у isAtOrAboveMedian(): знак и перцентиль
// оцениваются каждый по своей логике, а не приводятся к общей шкале.
//
// primary — худший блок СРЕДИ ТЕХ, где есть настоящие числовые перцентили.
// Блоки без перцентилей (например power, где единственный тест —
// прыжок в длину — всегда badge) в это сравнение не входят.
//
// badgeFailures — тесты со знаком «бронза» или «ниже бронзы»: по
// официальному смыслу норматива это «не дотянул». Серебро и золото сюда
// не попадают — это не провал, а норма или выше.
//
// Возвращает null, только если нет вообще ничего: ни перцентилей, ни
// провалов по знаку. Если провалы по знаку есть, а блоков с перцентилями
// нет — возвращает объект с primary: null и заполненным badgeFailures,
// а не null (иначе провал по знаку молча терялся бы).
export function weakestLink(results) {
  let primary = null;
  for (const block of BLOCKS) {
    const items = results.filter(
      (r) => r.block === block && !r.informational && typeof r.percentile === 'number',
    );
    if (items.length === 0) continue;
    const average = items.reduce((s, r) => s + r.percentile, 0) / items.length;
    if (primary === null || average < primary.average) {
      primary = { block, average, items };
    }
  }

  const badgeFailures = results
    .filter((r) => !r.informational && badgeIndicatesFailure(r.badge))
    .map((r) => ({
      block: r.block,
      testKey: r.key,
      label: r.label ?? TEST_NORMS[r.key]?.label ?? r.key,
      badge: r.badge,
    }));

  if (primary === null && badgeFailures.length === 0) return null;
  return { primary, badgeFailures };
}

// У пульса покоя меньше значит лучше. Просто поменять знак нельзя — узлы
// таблицы должны остаться по возрастанию. Поэтому зеркалим: p5 берём из p95
// и меняем знак (самый низкий исходный пульс становится верхним перцентилем
// зеркальной таблицы, самый высокий — нижним), порядок узлов остаётся
// по возрастанию.
function reversed(table) {
  const keys = ['p5', 'p10', 'p25', 'p50', 'p75', 'p90', 'p95'];
  const out = {};
  for (const k of keys) {
    const mirror = `p${100 - Number(k.slice(1))}`;
    if (typeof table[mirror] === 'number') out[k] = -table[mirror];
  }
  return out;
}
