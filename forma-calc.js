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
  if (typeof timeSec !== 'number' || !Number.isFinite(timeSec) || timeSec <= 0) return null;
  // Вне возрастного покрытия таблиц оценки нет: раньше пятнадцатилетний
  // молча получал коэффициент двадцатилетнего (правка перед публикацией).
  if (!withinCoverage(age, NORMS.running.ageCoverage)) return null;
  // Результат быстрее открытого мирового стандарта — это опечатка, а не
  // результат. Раньше «24» в поле пяти километров давало «3332% от мирового
  // стандарта, уровень мирового рекорда» (правка по ревью задачи 7).
  if (timeSec < entry.openStandardSec) return null;
  const bucket = ageBucket(age, entry.factors);
  if (bucket === undefined) return null; // пустая таблица коэффициентов
  const factor = entry.factors[bucket];
  const ageStandard = entry.openStandardSec / factor;
  return (ageStandard / timeSec) * 100;
}

// Классификация уровня age grading по шкале USATF Masters (normy-beg.md,
// раздел 3): 60%+ — местный уровень, 70%+ — региональный, 80%+ —
// национальный, 90%+ — мировой, 100% — уровень мирового рекорда.
// ПРАВКА ПЕРЕД ПУБЛИКАЦИЕЙ: каждый порог стоял на 10 пунктов ниже, а порога
// 50% в источниках нет вообще. Из-за этого контрольный пример самого
// источника (мужчина 40 лет, 10 км за 40:00 — 68,5%, «местный уровень»)
// код называл региональным. Ниже 60% источник уровня не даёт — это и есть
// начальный уровень.
export function ageGradeClass(pct) {
  if (pct < 60) return 'начальный уровень';
  if (pct < 70) return 'местный уровень';
  if (pct < 80) return 'региональный уровень';
  if (pct < 90) return 'национальный уровень';
  if (pct < 100) return 'мировой уровень';
  return 'уровень мирового рекорда';
}

// Общий помощник: выбор ближайшего ключа объекта снизу по числовому параметру.
// Один помощник на все таблицы со сплошной (без дыр) шкалой — коэффициенты
// age grading, перцентили VO2max, состав тела, восстановление,
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

// Перцентиль VO2max внутри своей возрастной группы. Вне покрытия таблицы
// FRIEND возвращает null: подставлять группу двадцатилетних подростку или
// восьмидесятилетнему нельзя (правка по ревью задачи 7).
export function vo2maxPercentile(vo2max, sex, age) {
  if (!withinCoverage(age, NORMS.vo2max.ageCoverage)) return null;
  return percentile(vo2max, vo2maxTable(sex, age));
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

// Возраст, для которого главную цифру вообще можно считать: покрытие
// таблицы FRIEND. Границы лежат в данных (forma-norms.js).
export function bodyAgeCoverage() {
  const a = NORMS.vo2max.ageCoverage;
  return { min: a.min, max: a.max };
}

// Попадает ли возраст в покрытие конкретной таблицы. Границы приходят из
// данных; отсутствующая граница (null) означает открытую группу — например,
// у пульса покоя верхняя группа источника «80 и старше».
export function withinCoverage(age, coverage) {
  if (typeof age !== 'number' || !Number.isFinite(age)) return false;
  if (!coverage) return true;
  if (typeof coverage.min === 'number' && age < coverage.min) return false;
  if (typeof coverage.max === 'number' && age > coverage.max) return false;
  return true;
}

// Покрыт ли возраст для ГЛАВНОЙ ЦИФРЫ. Это ограничение только возраста тела:
// у каждого теста своё покрытие, и вне него отказывает сам тест, а не вся
// страница. Подростку 15 лет возраст тела не считаем: сравнивать его с
// медианами взрослых возрастных групп FRIEND не на чем.
export function ageCovered(age) {
  const c = bodyAgeCoverage();
  return typeof age === 'number' && Number.isFinite(age) && age >= c.min && age <= c.max;
}

// Границы, между которыми вообще может оказаться возраст тела: центры
// младшей и старшей возрастных групп таблицы FRIEND. Возраст тела упирается
// в них — оговорку про пол показываем только когда это действительно так.
export function bodyAgeBounds(sex) {
  const bySex = NORMS.vo2max[sex];
  const ages = Object.keys(bySex).map(Number).sort((a, b) => a - b);
  return { min: ages[0] + 5, max: ages[ages.length - 1] + 5 };
}

// Оценка VO2max по тесту Купера. Только для мужчин: выборка оригинала —
// 115 мужчин-военных, женщин в ней не было, отдельной женской формулы не
// опубликовано. Применять мужскую к женщинам — то же нарушение, за которое
// правили силовые нормы. Коэффициенты и список полов — в данных.
export function vo2maxFromCooper(distanceM, sex, age) {
  const spec = NORMS.cooper;
  if (!spec.applicableSex.includes(sex)) return null;
  // Возрастной охват когорты оригинала — 17-52 года, он назван в источнике.
  // Вне его формулу не применяем (правка перед публикацией).
  if (!withinCoverage(age, spec.ageCoverage)) return null;
  if (typeof distanceM !== 'number' || !Number.isFinite(distanceM) || distanceM <= 0) return null;
  const value = (distanceM - spec.formula.offsetM) / spec.formula.divisor;
  return value > 0 ? value : null;
}

// Индекс физической активности (шкала Kurtze, используется в модели Nes/Wisløff,
// HUNT Study). Частота × интенсивность × продолжительность тренировки.
// Источник программно доступен в NORMS.ntnuFormula.activityIndexSource
// (Bye A. и соавт., PLoS ONE, 2013 — см. normy-vo2max.md, набор 3).
function kurtzeIndex(trainingFreq, trainingIntensity, trainingDuration) {
  // Правило анкеты HUNT: при частоте ниже порога («никогда», «реже раза в
  // неделю») индекс равен нулю независимо от остальных ответов. Сам порог —
  // в данных, раньше это правило жило в разметке страницы.
  const zeroBelow = NORMS.ntnuFormula.activityIndex.zeroBelowFrequency;
  if (typeof trainingFreq !== 'number' || trainingFreq < zeroBelow) return 0;
  return trainingFreq * trainingIntensity * trainingDuration;
}

// Оценка VO2peak без нагрузочного теста — формула HUNT/NTNU (Nes, Janszky,
// Vatten, Nilsen, Aspenes, Wisløff, MSSE, 2011), версия с ИМТ вместо окружности
// талии, подтверждённая дословной цитатой в Jalene S. и соавт., Frontiers in
// Physiology, 2019 (см. normy-vo2max.md, набор 3). Версия с окружностью талии
// не подтверждена рецензируемым источником и намеренно не используется.
// Источник программно доступен в NORMS.ntnuFormula.source.
export function estimateVo2maxNTNU({ sex, age, bmi, restingHR, trainingFreq, trainingIntensity, trainingDuration }) {
  const spec = NORMS.ntnuFormula;
  // Границы применимости из источника: модель откалибрована на участниках
  // 20-90 лет. Раньше границ не было вовсе.
  if (!withinCoverage(age, spec.ageCoverage)) return null;

  const pa = kurtzeIndex(trainingFreq, trainingIntensity, trainingDuration);
  const value = sex === 'f'
    ? 70.77 - 0.244 * age - 0.749 * bmi - 0.107 * restingHR + 0.213 * pa
    : 92.05 - 0.327 * age - 0.933 * bmi - 0.167 * restingHR + 0.257 * pa;

  // Нижний предел осмысленного результата. При возрасте 79, индексе массы
  // тела 45 и пульсе 95 формула отдаёт около 8 мл/кг/мин — такой оценки нет
  // ни в одной строке таблицы, в которую мы её переводим, и молча уходить в
  // возраст тела она не должна.
  const floor = spec.minPlausibleVo2max[sex];
  if (typeof floor === 'number' && value < floor) return null;
  return value;
}

// Фитнес-возраст NTNU — запасной путь, когда VO2max неизвестен.
// Сначала оцениваем VO2peak по неспортивным показателям, потом переводим
// его в возраст тела через ту же таблицу FRIEND.
export function fitnessAgeNTNU({ sex, age, bmi, restingHR, trainingFreq, trainingIntensity, trainingDuration }) {
  const estimated = estimateVo2maxNTNU({ sex, age, bmi, restingHR, trainingFreq, trainingIntensity, trainingDuration });
  if (estimated === null) return null; // вне применимости формулы возраста тела нет
  return bodyAgeFromVo2max(estimated, sex);
}

// Перцентильная таблица для точного возраста: линейная интерполяция между
// двумя соседними возрастными точками источника. Нужна там, где источник
// публикует параметры распределения ДЛЯ ТОЧНЫХ ВОЗРАСТОВ (20, 30, 40 ...),
// а не для десятилетних групп — процент жира по NHANES/DXA именно такой.
// Читать такие точки как группы нельзя: 29-летний сравнивался бы с нормой
// двадцатилетнего, ошибка доходит до десяти перцентильных пунктов
// (правка перед публикацией). За краями таблицы берём крайнюю точку —
// но вызывающий код обязан сначала проверить покрытие возраста.
export function tableAtAge(age, byAge) {
  const keys = Object.keys(byAge).map(Number).sort((a, b) => a - b);
  if (!keys.length) return null;
  if (age <= keys[0]) return byAge[keys[0]];
  const last = keys[keys.length - 1];
  if (age >= last) return byAge[last];

  let lo = keys[0];
  let hi = last;
  for (let i = 0; i < keys.length - 1; i += 1) {
    if (age >= keys[i] && age <= keys[i + 1]) {
      lo = keys[i];
      hi = keys[i + 1];
      break;
    }
  }
  const share = (age - lo) / (hi - lo);
  const out = {};
  for (const node of Object.keys(byAge[lo])) {
    const a = byAge[lo][node];
    const b = byAge[hi][node];
    if (typeof a === 'number' && typeof b === 'number') out[node] = a + share * (b - a);
  }
  return out;
}

// Состав тела: четыре показателя, каждый со своим источником и оговорками
export function bodyComposition({ sex, age, height, weight, bodyFatPct, limbMuscleKg, waist }) {
  const heightM = height / 100;

  const smiValue = limbMuscleKg / (heightM * heightM);
  const smiThreshold = NORMS.smi.threshold[sex];

  const bmiValue = weight / (heightM * heightM);
  const wthrValue = waist / height;

  // Вне покрытия таблицы NHANES перцентиля нет — крайнюю группу не подставляем
  const bodyFatCovered = withinCoverage(age, NORMS.bodyFat.ageCoverage);
  const bodyFatPercentile = bodyFatCovered
    ? percentile(bodyFatPct, tableAtAge(age, NORMS.bodyFat[sex]))
    : null;

  return {
    bodyFat: {
      value: bodyFatPct,
      percentile: bodyFatPercentile,
      level: bodyFatLevel(bodyFatPercentile), // у процента жира меньше значит лучше
      note: appendNote(
        'Перцентиль рассчитан по измерениям методом DXA и по одной этнической подгруппе обследования NHANES (White) — только для неё в источнике есть полные ряды по всем возрастам. Бытовые весы с биоимпедансом дают отклонение в среднем 3-4 процентных пункта, иногда больше — направление ошибки зависит от модели весов. Следите за динамикой своих замеров на одних и тех же весах, а не за точным попаданием в перцентиль.',
        bodyFatCovered ? '' : `Для этого возраста перцентилей в источнике нет: таблица покрывает возраст от ${NORMS.bodyFat.ageCoverage.min} до ${NORMS.bodyFat.ageCoverage.max} лет, поэтому разряда по проценту жира здесь не будет.`,
      ),
      reference: NORMS.bodyFat.source,
    },
    smi: {
      value: smiValue,
      flag: smiValue < smiThreshold ? 'ниже порога саркопении' : 'в норме',
      // Оговорка про метод — по образцу процента жира: порог получен на DXA,
      // а число обычно вводится с бытовых весов с биоимпедансом.
      note: 'Порог саркопении получен по измерениям методом DXA, а мышечную массу конечностей чаще вводят с бытовых весов с биоимпедансом — они дают другое число. Смотрите на динамику своих замеров на одних и тех же весах, а не на точное попадание в порог.',
      reference: NORMS.smi.source,
    },
    bmi: {
      value: bmiValue,
      // Категория — только для взрослых: детских кривых ИМТ по возрасту в проекте нет
      category: withinCoverage(age, NORMS.bmi.ageCoverage) ? bmiCategory(bmiValue) : null,
      note: appendNote(
        'При развитой мускулатуре ИМТ завышает оценку жировой массы. Смотреть вместе с процентом жира.',
        withinCoverage(age, NORMS.bmi.ageCoverage) ? '' : 'Категория ВОЗ здесь не выдаётся: она построена для взрослых, а для детей и подростков ВОЗ публикует отдельные кривые по возрасту — их в собранных нормах нет.',
      ),
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
  // Вне покрытия таблицы NHANES перцентиля нет (нижняя граница — 20 лет,
  // верхняя группа источника открытая, «80 и старше»)
  const hrCovered = withinCoverage(age, NORMS.restingHR.ageCoverage);
  const hrPercentile = hrCovered
    ? percentile(-restingHR, reversed(NORMS.restingHR[sex][ageBucket(age, NORMS.restingHR[sex])]))
    : null;

  return {
    restingHR: {
      value: restingHR,
      percentile: hrPercentile,
      level: levelFromPercentile(hrPercentile),
      note: hrCovered ? null : 'Нормы пульса покоя для этого возраста не опубликованы: таблица начинается с 20 лет. Значение показано как есть.',
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
  if (!extra) return base;
  const addition = extra.charAt(0).toUpperCase() + extra.slice(1);
  if (!base) return addition;
  const trimmed = base.trim();
  const withStop = /[.!?…]$/.test(trimmed) ? trimmed : `${trimmed}.`;
  return `${withStop} ${addition}`;
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

// На каком краю таблицы обрезано значение. percentile() отдаёт ровно 0,
// когда значение ниже самого нижнего узла, и ровно 100, когда выше самого
// верхнего — узлов p0 и p100 в таблицах нет, поэтому признак надёжный.
// Разряд при этом присваивается (крайнее значение — тоже информация), но
// подпись обязана говорить, что это край таблицы, а не «лучше 100% людей».
export function clampSide(p) {
  if (typeof p !== 'number') return null;
  if (p <= 0) return 'below';
  if (p >= 100) return 'above';
  return null;
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
    clamped: null, // 'below' | 'above' — значение за краем таблицы (см. clampSide)
    secondaryClamped: null,
    secondaryLabel: spec.secondary ? spec.secondary.label : null,
    secondaryPopulation: null, // название популяции для подписи вторичного чтения
    bounds: null, // две опубликованные точки распределения там, где источник даёт только их
    informational: Boolean(spec.informational),
    belowThreshold: null, // считается ниже: только для числа и только внутри когорты порога
    reference: spec.source,
    note: spec.note ?? null,
  };

  // Порог из исследования (стойка на одной ноге). Два условия, и оба
  // обязательны. Первое: значение — настоящее число; пустое поле раньше
  // проходило проверку как «порог пройден» (null < 10 — это false).
  // Второе: человек внутри когорты, на которой порог измерен. Araújo мерил
  // людей 51-75 лет — 25-летнему вердикт по этой работе не полагается,
  // ему показываем время без вердикта и объясняем почему.
  if (spec.threshold !== undefined && typeof value === 'number' && Number.isFinite(value)) {
    if (!spec.thresholdAgeRange || withinCoverage(profile.age, spec.thresholdAgeRange)) {
      result.belowThreshold = value < spec.threshold;
    } else {
      result.note = appendNote(result.note, spec.thresholdCohortNote || 'порог измерен на другой возрастной группе, поэтому вердикта здесь нет');
    }
  }

  // Тесты, у которых источник публикует только две крайние точки
  // распределения (наклон вперёд сидя: 5-й и 95-й перцентиль). Достроить
  // между ними прямую и назвать результат перцентилем нельзя — такого
  // распределения не существует. Показываем сами опубликованные точки.
  if (spec.boundsOnly) {
    const bySex = spec[profile.sex];
    const youngest = bySex ? Math.min(...Object.keys(bySex).map(Number)) : null;
    const covered = Boolean(bySex)
      && (spec.maxAge === undefined || profile.age <= spec.maxAge)
      && profile.age >= youngest;
    if (covered) {
      const table = bySex[ageBucket(profile.age, bySex)];
      result.bounds = { p5: table.p5, p95: table.p95 };
    } else {
      result.note = appendNote(result.note, 'опубликованных точек для этого возраста нет: нормы не опубликованы');
    }
  }

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
      // Нижняя граница таблицы — её же самый младший ключ. Раньше ageBucket()
      // подставлял младшую группу всем, кто младше неё: 17-летний получал
      // разряд по таблице двадцатилетних (правка по ревью задачи 7).
      const youngest = Math.min(...Object.keys(bySex).map(Number));
      if (profile.age < youngest) {
        result.note = appendNote(result.note, `нормы для этого возраста не опубликованы: таблица начинается с ${youngest} лет`);
      } else {
        const table = bySex[ageBucket(profile.age, bySex)];
        result.percentile = percentile(value, table);
        result.level = levelFromPercentile(result.percentile);
        result.clamped = clampSide(result.percentile);
      }
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
  // ПРАВКА ПЕРЕД ПУБЛИКАЦИЕЙ (критично): вторичное чтение живёт только внутри
  // покрытия весовой таблицы и только рядом с посчитанным основным разрядом.
  // Раньше человек 170 кг сравнивался со строкой 140 кг, человек 42 кг — со
  // строкой 50 кг, а пятнадцатилетний и девяностопятилетний, у которых
  // основной разряд честно пустой, всё равно получали вторичный по таблице,
  // откалиброванной на возраст 25-40 лет.
  if (spec.secondary && typeof result.percentile === 'number') {
    const w = profile.bodyWeight;
    const bySexW = spec.secondary[profile.sex];
    if (bySexW && typeof w === 'number' && Number.isFinite(w) && w > 0) {
      const weights = Object.keys(bySexW).map(Number).sort((a, b) => a - b);
      const lightest = weights[0];
      const heaviest = weights[weights.length - 1];
      if (w >= lightest && w <= heaviest) {
        const tableW = bySexW[ageBucket(w, bySexW)];
        result.secondaryPercentile = percentile(value, tableW);
        result.secondaryLevel = levelFromPercentile(result.secondaryPercentile);
        result.secondaryClamped = clampSide(result.secondaryPercentile);
        result.secondaryPopulation = spec.secondary.population ?? null;
      } else {
        result.note = appendNote(result.note, `второе чтение по весу тела здесь не показываем: таблица весов в источнике идёт от ${lightest} до ${heaviest} кг`);
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

// Зачтён ли тест. Две разные шкалы, каждая по своей логике.
// Перцентильная норма: зачёт — медиана своей группы и выше.
// Знак ГТО: зачёт — серебро или золото, незачёт — бронза и ниже. Это
// официальный смысл самого знака, никакой доли населения за ним не стоит:
// ГТО нигде не публикует, какая часть людей берёт серебро, и приравнивать
// знак к позиции в распределении нельзя (правка перед публикацией).
function isPass(r) {
  if (typeof r.percentile === 'number') return r.percentile >= 50;
  if (typeof r.badge === 'string') return (BADGE_ORDER[r.badge] ?? -1) >= BADGE_ORDER['серебро'];
  return false;
}

// Счёт формы: по каждому из шести блоков — зелёный (больше половины тестов
// блока зачтено), красный (половина или меньше) либо серый
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
    const passed = items.filter(isPass).length;
    const isGreen = passed > items.length / 2;
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

// Попал ли человек в ту группу, для которой опубликован коэффициент.
// Условие берётся из данных (NORMS.hazards[key].trigger), а не собирается
// на месте из общего правила «нижняя четверть» — иначе карточка приписывает
// человеку чужое сравнение (правка по ревью задачи 7, критично).
// Входит ли человек в охват когорты источника — по полу и по возрасту.
// Применять коэффициент к возрасту, на котором его не измеряли, — то же
// самое, что подставлять чужую норму (правка по ревью задачи 7).
// Где охвата в источнике нет, поле пустое и ограничение не применяется.
// Возраст известен не всегда: если у результата его нет, а у когорты
// диапазон задан, проверить попадание нечем — коэффициент не показываем.
function cohortCovers(h, r) {
  if (Array.isArray(h.applicableSex) && !h.applicableSex.includes(r.sex)) return false;
  if (h.cohortAgeRange && !withinCoverage(r.age, h.cohortAgeRange)) return false;
  return true;
}

function hazardApplies(h, r) {
  const t = h.trigger;
  if (!t) return false; // условия срабатывания нет — карточки нет
  if (!cohortCovers(h, r)) return false;
  switch (t.kind) {
    case 'gradient':
      // Градиент «на каждые N единиц» — не персональный множитель.
      return false;
    case 'groupComparison':
      // Сравнение двух групп источника, в которое человека поставить нечем:
      // либо граница группы задана не тем, что мы измеряем (VO2max —
      // квинтили когорты другой клиники), либо связку с нашим порогом никто
      // не публиковал (саркопения). Персональной карточки не даёт никогда.
      return false;
    case 'percentileBelow':
      return typeof r.percentile === 'number' && r.percentile < t.value;
    case 'valueBelow': {
      const limit = sexSplitOrPlain(t.value, r.sex);
      return typeof limit === 'number' && typeof r.value === 'number' && r.value < limit;
    }
    case 'valueAtOrAbove': {
      const limit = sexSplitOrPlain(t.value, r.sex);
      return typeof limit === 'number' && typeof r.value === 'number' && r.value >= limit;
    }
    case 'badgeAtOrBelow': {
      const rank = BADGE_ORDER[r.badge];
      const limit = BADGE_ORDER[t.value];
      return typeof rank === 'number' && typeof limit === 'number' && rank <= limit;
    }
    default:
      return false;
  }
}

// Знак ГТО «бронза» или «ниже бронзы» — незачёт по официальному смыслу
// самого знака. Никакой доли населения за этим не стоит: сколько людей
// берёт бронзу, ГТО не публикует. Сейчас ни у одного badge-теста
// (подтягивания, прыжок в длину) нет записи в hazards, поэтому ветка ничего
// не включает на практике — но как только коэффициент риска для такого
// теста появится, знак должен уметь стать причиной карточки, а не молча
// теряться из-за отсутствия перцентиля.
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

    // Человек должен реально попасть в группу сравнения источника —
    // иначе карточки нет, даже если по общему ощущению «показатель плохой».
    if (!hazardApplies(h, r)) continue;

    cards.push({
      testKey: r.key,
      label: TEST_NORMS[r.key]?.label ?? h.label ?? r.key,
      hazard,
      condition: h.condition,
      outcome: h.outcome,
      ci: sexSplitOrPlain(h.ci ?? null, r.sex),
      ciNote: h.ciNote ?? null,
      cohortSize: h.cohortSize ?? null,
      cohortAgeRangeSource: h.cohortAgeRangeSource ?? null,
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

// Коэффициенты, которые нельзя превратить в утверждение о конкретном
// человеке. Их два вида, и оба показываются отдельным списком от третьего
// лица — «в исследовании было так», а не «у тебя риск выше».
//   gradient        — «на каждые −5 кг силы хвата»: чтобы получить личный
//                     множитель, нужна точка отсчёта, которой источник не даёт;
//   groupComparison — сравнение двух групп источника, в которое человека
//                     поставить нечем: граница группы задана не тем, что мы
//                     измеряем (VO2max), или связку с нашим порогом никто не
//                     публиковал (саркопения).
// Возвращаем только те показатели, которые человек действительно заполнил.
const THIRD_PERSON_TRIGGERS = ['gradient', 'groupComparison'];

export function riskContext(results) {
  const out = [];
  for (const r of results) {
    const h = NORMS.hazards[r.key];
    if (!h || !h.trigger || !THIRD_PERSON_TRIGGERS.includes(h.trigger.kind)) continue;
    if (typeof r.value !== 'number') continue;
    // Тот же охват когорты, что и у карточек: цифру, измеренную на людях
    // 35-70 лет, восьмидесятилетнему не показываем даже справочно.
    if (!cohortCovers(h, r)) continue;

    const hazard = sexSplitOrPlain(h.hazard, r.sex);
    if (typeof hazard !== 'number') continue;

    out.push({
      testKey: r.key,
      label: TEST_NORMS[r.key]?.label ?? h.label ?? r.key,
      kind: h.trigger.kind,
      hazard,
      step: h.trigger.step ?? null,
      condition: h.condition,
      outcome: h.outcome,
      ci: sexSplitOrPlain(h.ci ?? null, r.sex),
      ciNote: h.ciNote ?? null,
      cohortSize: h.cohortSize ?? null,
      cohortAgeRangeSource: h.cohortAgeRangeSource ?? null,
      reference: h.source,
    });
  }
  return out;
}

// Что удалось проверить по опубликованным порогам, а что нет. Молчание
// нельзя подавать как «всё в порядке»: человек вне охвата когорты не «прошёл
// проверку», её просто не на чем было провести (правка по ревью задачи 7).
// checked — показатели, по которым порог реально применили;
// outOfCohort — заполненные показатели с опубликованным порогом, которые
// проверить нечем, с человеческой причиной.
export function riskCoverage(results) {
  const checked = [];
  const outOfCohort = [];

  for (const r of results) {
    const h = NORMS.hazards[r.key];
    if (!h || !h.trigger || THIRD_PERSON_TRIGGERS.includes(h.trigger.kind)) continue;

    const label = TEST_NORMS[r.key]?.label ?? h.label ?? r.key;
    if (cohortCovers(h, r)) {
      checked.push({ testKey: r.key, label });
      continue;
    }

    const parts = [];
    if (Array.isArray(h.applicableSex) && !h.applicableSex.includes(r.sex)) {
      parts.push(h.applicableSex.includes('m') ? 'только мужчины' : 'только женщины');
    }
    if (h.cohortAgeRange && !withinCoverage(r.age, h.cohortAgeRange)) {
      parts.push(`возраст ${h.cohortAgeRange.min}-${h.cohortAgeRange.max} лет`);
    }
    outOfCohort.push({ testKey: r.key, label, cohort: parts.join(', ') });
  }

  return { checked, outOfCohort };
}

// Сравнение с прошлым замером: только те показатели, что есть в обоих.
// Названия можно передать снаружи (у страницы есть свои показатели вроде
// VO2max и пульса покоя, которых нет в таблицах тестов).
export function diffWithPrevious(current, previous, labels = {}) {
  if (!previous) return [];
  const out = [];
  for (const key of Object.keys(current)) {
    if (typeof previous[key] !== 'number' || typeof current[key] !== 'number') continue;
    out.push({
      key,
      label: labels[key] ?? TEST_NORMS[key]?.label ?? key,
      from: previous[key],
      to: current[key],
      delta: current[key] - previous[key],
    });
  }
  return out;
}

// Слабое звено — два разных утверждения, и смешивать их в одно число
// нельзя (правка по итогам повторного ревью задачи 6: раньше знак ГТО
// раскладывался в число и усреднялся с настоящими перцентилями —
// самодельная шкала, которую никто не публиковал). Ровно
// та же честность, что уже есть у isPass(): знак и перцентиль
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
