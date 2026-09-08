// Чистые функции расчёта. DOM здесь не трогаем.

import { NORMS } from './forma-norms.js';

// Узлы перцентильных таблиц в порядке возрастания
const NODES = ['p5', 'p10', 'p25', 'p50', 'p75', 'p90', 'p95'];

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
  const factor = nearestFactor(entry.factors, age);
  if (factor === null) return null;
  const ageStandard = entry.openStandardSec / factor;
  return (ageStandard / timeSec) * 100;
}

// Ищем коэффициент для ближайшего известного возраста снизу
// (таблица дана по годам от 20 до 80, за пределами берём крайнее значение)
function nearestFactor(factors, age) {
  const keys = Object.keys(factors).map(Number).sort((a, b) => a - b);
  if (keys.length === 0) return null;
  let chosen = keys[0];
  for (const k of keys) if (age >= k) chosen = k;
  return factors[chosen];
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

// Выбор возрастной группы: берём ближайший ключ таблицы снизу
// (таблицы даны по группам/шагам возраста, за пределами берём крайнее значение)
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
      const share = (a.v - vo2max) / (a.v - b.v);
      return Math.round(a.age + share * (b.age - a.age));
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
// Источник: Bye A. и соавт., PLoS ONE, 2013 — см. normy-vo2max.md, набор 3.
function kurtzeIndex(trainingFreq, trainingIntensity, trainingDuration) {
  return trainingFreq * trainingIntensity * trainingDuration;
}

// Оценка VO2peak без нагрузочного теста — формула HUNT/NTNU (Nes, Janszky,
// Vatten, Nilsen, Aspenes, Wisløff, MSSE, 2011), версия с ИМТ вместо окружности
// талии, подтверждённая дословной цитатой в Jalene S. и соавт., Frontiers in
// Physiology, 2019 (см. normy-vo2max.md, набор 3). Версия с окружностью талии
// не подтверждена рецензируемым источником и намеренно не используется.
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

// Категории ИМТ по ВОЗ
function bmiCategory(bmi) {
  if (bmi < 18.5) return 'недостаточный вес';
  if (bmi < 25) return 'норма';
  if (bmi < 30) return 'избыточный вес';
  if (bmi < 35) return 'ожирение I степени';
  if (bmi < 40) return 'ожирение II степени';
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
