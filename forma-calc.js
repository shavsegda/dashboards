// Чистые функции расчёта. DOM здесь не трогаем.

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
