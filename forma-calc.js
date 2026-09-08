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
