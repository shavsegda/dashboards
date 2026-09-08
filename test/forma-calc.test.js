import { test } from 'node:test';
import assert from 'node:assert/strict';
import { percentile, levelFromPercentile, ageGrade, ageGradeClass, vo2maxTable, bodyAgeFromVo2max, interpolateBodyAge, lifeExpectancy, fitnessAgeNTNU, bodyComposition, recovery, evaluateTest } from '../forma-calc.js';
import { NORMS, TEST_NORMS } from '../forma-norms.js';

test('перцентиль на узле таблицы возвращает сам узел', () => {
  const t = { p25: 30, p50: 40, p75: 50 };
  assert.equal(percentile(40, t), 50);
  assert.equal(percentile(30, t), 25);
});

test('перцентиль между узлами считается линейной интерполяцией', () => {
  const t = { p25: 30, p50: 40, p75: 50 };
  assert.equal(percentile(35, t), 37.5);
});

test('значение ниже самого низкого узла даёт 0, выше самого высокого — 100', () => {
  const t = { p25: 30, p50: 40, p75: 50 };
  assert.equal(percentile(10, t), 0);
  assert.equal(percentile(90, t), 100);
});

test('уровень называется нейтрально и растёт вместе с перцентилем', () => {
  assert.equal(levelFromPercentile(5), 'начальный уровень');
  assert.equal(levelFromPercentile(30), 'ниже среднего');
  assert.equal(levelFromPercentile(55), 'средний');
  assert.equal(levelFromPercentile(80), 'выше среднего');
  assert.equal(levelFromPercentile(95), 'продвинутый');
});

test('результат на уровне мирового стандарта для своего возраста даёт около 100 процентов', () => {
  const std = NORMS.running.m['5'].openStandardSec;
  const pct = ageGrade('m', 25, 5, std);
  assert.ok(Math.abs(pct - 100) < 3, `ожидали около 100, получили ${pct}`);
});

test('вдвое более медленный результат даёт вдвое меньший процент', () => {
  const std = NORMS.running.m['5'].openStandardSec;
  const pct = ageGrade('m', 25, 5, std * 2);
  assert.ok(Math.abs(pct - 50) < 3, `ожидали около 50, получили ${pct}`);
});

test('с возрастом тот же результат даёт больший процент', () => {
  const t = 1500; // 25 минут на пятёрке
  assert.ok(ageGrade('m', 60, 5, t) > ageGrade('m', 30, 5, t));
});

test('классы age grading названы по классификации WMA', () => {
  assert.equal(ageGradeClass(45), 'начальный уровень');
  assert.equal(ageGradeClass(55), 'местный уровень');
  assert.equal(ageGradeClass(65), 'региональный уровень');
  assert.equal(ageGradeClass(75), 'национальный уровень');
  assert.equal(ageGradeClass(85), 'мировой уровень');
  assert.equal(ageGradeClass(95), 'уровень мирового рекорда');
});

test('проверочный пример: мужчина 40 лет, 10 км за 40:00 — около 68.5%', () => {
  const pct = ageGrade('m', 40, 10, 40 * 60);
  assert.ok(Math.abs(pct - 68.5) < 0.2, `ожидали около 68.5, получили ${pct}`);
});

test('у таблицы беговых норм есть источник с названием, авторами, годом и ссылкой', () => {
  const src = NORMS.running.source;
  assert.ok(src, 'нет поля source у NORMS.running');
  assert.ok(src.title, 'нет title');
  assert.ok(src.authors, 'нет authors');
  assert.ok(src.year, 'нет year');
  assert.ok(src.url, 'нет url');
});

test('у каждой таблицы норм указан источник', () => {
  for (const [name, entry] of Object.entries(NORMS)) {
    assert.ok(entry.source, `нет поля source у таблицы ${name}`);
    assert.ok(entry.source.title, `нет названия источника у ${name}`);
    assert.ok(entry.source.year, `нет года у ${name}`);
    assert.ok(entry.source.url, `нет ссылки у ${name}`);
  }
});

test('таблица VO2max подбирается по полу и возрастной группе', () => {
  const t = vo2maxTable('m', 34);
  assert.equal(typeof t.p50, 'number');
  assert.ok(t.p50 > t.p25);
  assert.ok(t.p95 > t.p50);
});

test('возраст тела — это возраст, где VO2max человека равен медиане', () => {
  const sex = 'm';
  const bodyAge = bodyAgeFromVo2max(vo2maxTable(sex, 45).p50, sex);
  assert.ok(Math.abs(bodyAge - 45) <= 5, `ожидали около 45, получили ${bodyAge}`);
});

test('высокий VO2max даёт возраст тела моложе, низкий — старше', () => {
  const young = bodyAgeFromVo2max(55, 'm');
  const old = bodyAgeFromVo2max(28, 'm');
  assert.ok(young < old);
});

test('при одном паспортном возрасте молодое тело даёт больший итог', () => {
  assert.ok(lifeExpectancy(30, 45, 'm') > lifeExpectancy(60, 45, 'm'));
});

test('возраст тела равен паспортному — получается обычная таблица дожития', () => {
  const v = lifeExpectancy(45, 45, 'm');
  assert.ok(v > 45 && v < 110, `неправдоподобный итог ${v}`);
});

test('фитнес-возраст NTNU считается без VO2max', () => {
  const age = fitnessAgeNTNU({
    sex: 'm', age: 38, bmi: 24.6, restingHR: 52,
    trainingFreq: 5, trainingIntensity: 3, trainingDuration: 3,
  });
  assert.equal(typeof age, 'number');
  assert.ok(age > 0 && age < 100);
});

test('интерполяция возраста тела не делит на ноль при равных соседних медианах', () => {
  // Подсовываем два соседних узла с одинаковой медианой — раньше
  // (a.v - b.v) в знаменателе давало 0 и результат был NaN.
  const a = { age: 30, v: 40 };
  const b = { age: 40, v: 40 };
  const result = interpolateBodyAge(40, a, b);
  assert.equal(typeof result, 'number');
  assert.ok(!Number.isNaN(result), `ожидали число, получили NaN`);
  assert.equal(result, 30, 'при равных медианах берём возраст левого узла');
});

test('у формулы NTNU есть источник, доступный программно, а не только в комментарии', () => {
  const src = NORMS.ntnuFormula.source;
  assert.ok(src, 'нет поля source у NORMS.ntnuFormula');
  assert.ok(src.title, 'нет title');
  assert.ok(src.authors, 'нет authors');
  assert.ok(src.year, 'нет year');
  assert.ok(src.url, 'нет url');
  // ПРАВКА ПО ИТОГАМ РЕВЬЮ: kind перенесён внутрь source (единая конвенция
  // без исключений) — путь проверки поправлен на .source.kind, покрытие то же.
  assert.equal(NORMS.ntnuFormula.source.kind, 'population', 'формула на популяционной когорте HUNT — kind population');
});

test('состав тела возвращает четыре показателя со ссылками', () => {
  const r = bodyComposition({ sex: 'm', age: 38, height: 178, weight: 78, bodyFatPct: 14, limbMuscleKg: 27, waist: 82 });
  for (const key of ['bodyFat', 'smi', 'bmi', 'waistToHeight']) {
    assert.ok(r[key], `нет показателя ${key}`);
    assert.ok(r[key].reference.url, `нет ссылки у ${key}`);
  }
});

test('индекс мышечной массы считается как мышцы конечностей делить на рост в квадрате', () => {
  const r = bodyComposition({ sex: 'm', age: 38, height: 200, weight: 100, bodyFatPct: 15, limbMuscleKg: 28, waist: 85 });
  assert.equal(Math.round(r.smi.value * 100) / 100, 7);
});

test('индекс мышечной массы ниже порога помечается флагом саркопении', () => {
  const low = bodyComposition({ sex: 'm', age: 70, height: 178, weight: 60, bodyFatPct: 22, limbMuscleKg: 20, waist: 88 });
  assert.equal(low.smi.flag, 'ниже порога саркопении');
});

test('ИМТ всегда идёт с оговоркой про мускулатуру', () => {
  const r = bodyComposition({ sex: 'm', age: 38, height: 178, weight: 90, bodyFatPct: 12, limbMuscleKg: 32, waist: 84 });
  assert.match(r.bmi.note, /мускулатур/i);
});

test('талия к росту сравнивается с порогом ноль пять', () => {
  const r = bodyComposition({ sex: 'm', age: 38, height: 180, weight: 80, bodyFatPct: 15, limbMuscleKg: 27, waist: 95 });
  assert.equal(r.waistToHeight.flag, 'выше порога');
});

test('у процента жира есть предупреждение про бытовые весы', () => {
  const r = bodyComposition({ sex: 'm', age: 38, height: 178, weight: 78, bodyFatPct: 14, limbMuscleKg: 27, waist: 82 });
  assert.match(r.bodyFat.note, /биоимпеданс/i);
});

test('восстановление возвращает пульс покоя, HRV и регулярность сна', () => {
  const r = recovery({ sex: 'm', age: 38, restingHR: 48, rmssd: 55, bedtimeSdMin: 35 });
  for (const key of ['restingHR', 'rmssd', 'sleepRegularity']) {
    assert.ok(r[key], `нет показателя ${key}`);
  }
});

test('HRV помечается как показатель личного тренда, а не нормы', () => {
  const r = recovery({ sex: 'm', age: 38, restingHR: 48, rmssd: 55, bedtimeSdMin: 35 });
  assert.match(r.rmssd.note, /личн/i);
});

test('низкий пульс покоя даёт высокий перцентиль, а не низкий (перевёрнутая шкала)', () => {
  const low = recovery({ sex: 'm', age: 38, restingHR: 48, rmssd: 55, bedtimeSdMin: 35 });
  const high = recovery({ sex: 'm', age: 38, restingHR: 89, rmssd: 55, bedtimeSdMin: 35 });
  assert.ok(low.restingHR.percentile > high.restingHR.percentile,
    `низкий пульс должен давать перцентиль выше: low=${low.restingHR.percentile}, high=${high.restingHR.percentile}`);
});

// --- Задача 4: сила, мощность, подвижность ---------------------------------

const profile = { sex: 'm', age: 38, bodyWeight: 78 };

test('оценка теста возвращает перцентиль, уровень и ссылку на источник', () => {
  const r = evaluateTest('pushups', 35, profile);
  assert.equal(typeof r.percentile, 'number');
  assert.equal(typeof r.level, 'string');
  assert.ok(r.reference.title);
  assert.ok(r.reference.url);
});

test('больше отжиманий — выше перцентиль', () => {
  assert.ok(evaluateTest('pushups', 45, profile).percentile > evaluateTest('pushups', 12, profile).percentile);
});

// ПРАВКА 1 (второй заход, критично): у силовых тестов основная ось —
// ВОЗРАСТ, как и у всего остального продукта. Весовая таблица Strength
// Level, которая раньше ошибочно была основной, вообще не хранит возраст
// (агрегирована по всем возрастам, откалибрована на плато 25-40 лет) —
// поэтому при ОДИНАКОВОМ возрасте и ОДИНАКОВОМ абсолютном весе снаряда
// основной перцентиль теперь не зависит от веса тела вовсе, а зависимость
// от веса тела переехала во ВТОРОЕ, независимое число (secondaryPercentile).
test('силовые считаются по возрасту: основной перцентиль не зависит от веса тела при одинаковом возрасте', () => {
  const light = evaluateTest('squat1rm', 100, { sex: 'm', age: 38, bodyWeight: 60 });
  const heavy = evaluateTest('squat1rm', 100, { sex: 'm', age: 38, bodyWeight: 110 });
  assert.equal(light.percentile, heavy.percentile, 'основной перцентиль общий — считается по возрасту, не по весу');
  assert.notEqual(light.secondaryPercentile, heavy.secondaryPercentile, 'а вот вторичное чтение «среди людей твоего веса» у них обязано различаться');
});

test('ПРАВКА 1: ключевой пример ревью — мужчина 75 лет весом 70 кг с приседом 71 кг получает осмысленный разряд по возрастной таблице (50-й перцентиль), а не по весовой (10,6-й)', () => {
  const r = evaluateTest('squat1rm', 71, { sex: 'm', age: 75, bodyWeight: 70 });
  assert.equal(Math.round(r.percentile), 50);
  assert.equal(r.level, 'средний');
  assert.ok(r.secondaryPercentile !== null, 'второе число по весу должно присутствовать');
  assert.notEqual(Math.round(r.percentile), Math.round(r.secondaryPercentile), 'основной и вторичный разряд не должны совпадать в этом примере');
  assert.ok(r.secondaryPercentile < 15, `ожидали низкий вторичный перцентиль (около 10,6), получили ${r.secondaryPercentile}`);
  assert.equal(r.secondaryLabel, 'среди людей твоего веса');
});

test('ПРАВКА 1: силовой тест вне покрытия возрастной таблицы (95 лет) даёт честный null в основном чтении', () => {
  const r = evaluateTest('squat1rm', 60, { sex: 'm', age: 95, bodyWeight: 70 });
  assert.equal(r.percentile, null);
  assert.match(r.note, /не опубликован/);
});

test('ПРАВКА 1: в подписи силового теста прямо сказано, что шкала построена на посетителях залов, а не на населении', () => {
  const r = evaluateTest('squat1rm', 100, profile);
  assert.match(r.note, /тренирующихся/i);
  assert.equal(r.reference.kind, 'training-classification');
});

test('вис на перекладине помечен как справочный и не даёт перцентиля', () => {
  const r = evaluateTest('deadhang', 60, profile);
  assert.equal(r.informational, true);
  assert.equal(r.percentile, null);
});

test('вис на перекладине честно помечен как источник, которого не существует', () => {
  const r = evaluateTest('deadhang', 60, profile);
  assert.equal(r.reference.kind, 'none');
  assert.match(r.note, /не существ/);
});

test('стойка на одной ноге отмечает порог десяти секунд', () => {
  assert.equal(evaluateTest('onelegstand', 8, profile).belowThreshold, true);
  assert.equal(evaluateTest('onelegstand', 25, profile).belowThreshold, false);
});

test('неизвестный тест возвращает null, а не падает', () => {
  assert.equal(evaluateTest('несуществующий', 10, profile), null);
});

test('сила хвата оценивается по популяционным нормам', () => {
  const r = evaluateTest('grip', 45, profile);
  assert.equal(typeof r.percentile, 'number');
  assert.equal(r.reference.kind, 'population');
});

test('ПРАВКА 3: сила хвата в 90 лет не занимает верхний бакет — вне покрытия источника', () => {
  const r = evaluateTest('grip', 30, { sex: 'm', age: 90, bodyWeight: 78 });
  assert.equal(r.percentile, null);
  assert.match(r.note, /не опубликован/);
});

test('ПРАВКА 3: 75-летний по отжиманиям не занимает бакет 60-69 — вне покрытия CSEP-PATH', () => {
  const r = evaluateTest('pushups', 20, { sex: 'm', age: 75, bodyWeight: 78 });
  assert.equal(r.percentile, null);
  assert.match(r.note, /не опубликован/);
});

test('наклон вперёд сидя для 70+ возвращает null с пометкой', () => {
  const r = evaluateTest('sitandreach', 20, { sex: 'm', age: 72, bodyWeight: 78 });
  assert.equal(r.percentile, null);
  assert.match(r.note, /не опубликован/);
});

test('ПРАВКА 7: пометка о непокрытом возрасте добавляется к содержательной пометке источника, а не затирает её', () => {
  // У sitandreach в note лежит содержательная оговорка про диапазон P5-P95 —
  // она должна остаться видна даже когда возраст вне покрытия (70+).
  const r = evaluateTest('sitandreach', 20, { sex: 'm', age: 75, bodyWeight: 78 });
  assert.match(r.note, /P5-P95/);
  assert.match(r.note, /не опубликован/);
});

test('планка справочная и не участвует в подсчёте перцентиля даже при большом значении', () => {
  const r = evaluateTest('plank', 300, profile);
  assert.equal(r.informational, true);
  assert.equal(r.percentile, null);
});

// ПРАВКА 1 (первый заход) + ПРАВКА 3 (второй заход, добор ступеней ГТО):
// подтягивания и прыжок в длину — знак ГТО, а не выдуманный перцентиль.
// Раньше бронза/серебро/золото были сопоставлены с p50/p75/p90 — у этого
// сопоставления был явный артефакт: 3 подтягивания давали percentile 0, а
// 4 подтягивания (ровно бронза) — сразу percentile 50. Теперь оба — просто
// целые соседние знака, без скачка.
test('ПРАВКА 1: подтягивания дают знак ГТО, а не перцентиль; level в этот знак НЕ дублируется (ПРАВКА 4)', () => {
  const r = evaluateTest('pullups', 12, profile); // мужчина 38 лет — ступень 35-39: бронза 4 / серебро 7 / золото 11
  assert.equal(r.percentile, null);
  assert.equal(r.badge, 'золото'); // 12 выше золота (11)
  assert.equal(r.level, null, 'знак ГТО живёт только в badge, level остаётся из словаря уровней либо null');
  assert.equal(r.reference.kind, 'state-standard');
});

test('ПРАВКА 1: 3 и 4 подтягивания — соседние целые знаки, не артефакт 0/50', () => {
  const below = evaluateTest('pullups', 3, profile);
  const atBronze = evaluateTest('pullups', 4, profile);
  assert.equal(below.percentile, null);
  assert.equal(atBronze.percentile, null);
  assert.equal(below.badge, 'ниже бронзы');
  assert.equal(atBronze.badge, 'бронза');
});

test('ПРАВКА 3: человек 30 лет получает знак ГТО по СВОЕЙ ступени (30-34), а не по соседней', () => {
  // Ступень 30-34 (бронза 4 / серебро 8 / золото 13) дособрана по итогам
  // второго ревью. Значение 10 нарочно выбрано так, чтобы отличать разряд
  // по своей ступени от разряда по соседней: по 30-34 это «серебро»
  // (10 >= 8), а по чужой соседней ступени 20-24 (бронза 9/серебро 13/
  // золото 16) было бы «бронза» (10 < 13) — то есть баг «человек получает
  // чужую ступень», который правка должна была устранить, дал бы другой
  // результат и тест бы его поймал.
  const r = evaluateTest('pullups', 10, { sex: 'm', age: 30, bodyWeight: 78 });
  assert.equal(r.badge, 'серебро');
});

test('ПРАВКА 3: диапазон 25-60 лет по подтягиваниям и прыжку в длину закрыт значительно полнее, чем до правки', () => {
  // До правки было 15 возрастов из 36 (25..60 включительно) по подтягиваниям
  // у обоих полов. Считаем то же самое после правки — цифры уходят в отчёт.
  let pullCovered = 0;
  let jumpCovered = 0;
  for (let age = 25; age <= 60; age += 1) {
    if (evaluateTest('pullups', 5, { sex: 'm', age, bodyWeight: 78 }).badge !== null) pullCovered += 1;
    if (evaluateTest('broadjump', 200, { sex: 'm', age, bodyWeight: 78 }).badge !== null) jumpCovered += 1;
  }
  assert.ok(pullCovered > 15, `ожидали рост покрытия подтягиваний выше 15 из 36, получили ${pullCovered}`);
  assert.ok(jumpCovered > 5, `ожидали рост покрытия прыжка выше исходных 5 из 36, получили ${jumpCovered}`);
});

test('ПРАВКА 3: ступень 65-69 лет по подтягиваниям осталась честно непокрытой', () => {
  const r = evaluateTest('pullups', 8, { sex: 'm', age: 67, bodyWeight: 78 });
  assert.equal(r.badge, null);
  assert.match(r.note, /не опубликован/);
});

test('прыжок в длину для 40+ возвращает знак null с пометкой — норматив ГТО отсутствует', () => {
  const r = evaluateTest('broadjump', 220, { sex: 'm', age: 45, bodyWeight: 78 });
  assert.equal(r.percentile, null);
  assert.equal(r.badge, null);
  assert.match(r.note, /не опубликован/);
});

test('прыжок в длину внутри ступени даёт знак ГТО, а не null', () => {
  const inRange = evaluateTest('broadjump', 220, { sex: 'm', age: 22, bodyWeight: 78 }); // ступень 20-24: бронза207/серебро228/золото244 — 220 между бронзой и серебром
  assert.equal(inRange.badge, 'бронза');
  assert.equal(inRange.level, null); // ПРАВКА 4: знак не дублируется в level
});

// ПРАВКА 4: level всегда либо словарь levelFromPercentile(), либо null —
// знак ГТО (бронза/серебро/золото/ниже бронзы) живёт ТОЛЬКО в badge.
test('ПРАВКА 4: в поле level никогда нет знаков ГТО, а в badge — никогда нет обычных уровней', () => {
  const LEVEL_WORDS = ['начальный уровень', 'ниже среднего', 'средний', 'выше среднего', 'продвинутый'];
  const BADGE_WORDS = ['золото', 'серебро', 'бронза', 'ниже бронзы'];

  const pull = evaluateTest('pullups', 12, profile);
  assert.ok(BADGE_WORDS.includes(pull.badge));
  assert.ok(pull.level === null || LEVEL_WORDS.includes(pull.level));
  assert.ok(!BADGE_WORDS.includes(pull.level));

  const push = evaluateTest('pushups', 35, profile);
  assert.ok(LEVEL_WORDS.includes(push.level));
  assert.ok(!BADGE_WORDS.includes(push.level));
  assert.equal(push.badge, null);
});

// ПРАВКА 4: у TEST_NORMS нет фантомных ключей (раньше 'source'/'kind' лежали
// прямо в NORMS.tests как «одиннадцать с половиной тестов»)
test('в TEST_NORMS только одиннадцать настоящих тестов, никаких фантомных метаданных', () => {
  const expected = ['pushups', 'pullups', 'plank', 'squat1rm', 'bench1rm', 'deadlift1rm', 'deadhang', 'grip', 'broadjump', 'sitandreach', 'onelegstand'];
  assert.deepEqual(Object.keys(TEST_NORMS).sort(), expected.sort());
});

// Защита от нулевого/некорректного веса тела — теперь это касается только
// ВТОРИЧНОГО чтения (secondaryPercentile), потому что основной перцентиль
// у силовых тестов больше не зависит от веса тела вообще (ПРАВКА 1).
test('силовой тест с нулевым весом тела: основной разряд по возрасту всё равно считается, а вторичный честно остаётся null', () => {
  const zero = evaluateTest('squat1rm', 100, { sex: 'm', age: 38, bodyWeight: 0 });
  assert.equal(typeof zero.percentile, 'number', 'основной перцентиль по возрасту не должен зависеть от некорректного веса');
  assert.equal(zero.secondaryPercentile, null);
});

test('силовой тест без веса тела (undefined) — вторичное чтение null, а не NaN-перцентиль', () => {
  const r = evaluateTest('squat1rm', 100, { sex: 'm', age: 38, bodyWeight: undefined });
  assert.equal(r.secondaryPercentile, null);
  assert.ok(!Number.isNaN(r.secondaryPercentile));
});

test('силовой тест с отрицательным весом тела — вторичное чтение тоже null', () => {
  const r = evaluateTest('squat1rm', 100, { sex: 'm', age: 38, bodyWeight: -10 });
  assert.equal(r.secondaryPercentile, null);
});

// У каждой таблицы норм указан тип данных, и у kind — единая конвенция
// (ПРАВКА 5, без исключений после повторного ревью): kind всегда лежит
// ВНУТРИ source, включая NORMS.ntnuFormula. Допустимых значений шесть: три
// из исходного брифа задачи 4 (population/training-classification/
// occupational) плюс 'clinical' (клинический консенсус, унаследовано из
// задач 2-3: NORMS.smi, NORMS.bmi, планка, стойка на одной ноге),
// 'state-standard' (государственный норматив на присвоение знака ГТО — не
// обследование населения) и 'none' (опубликованного источника нет вообще —
// вис на перекладине).
const VALID_KINDS = ['population', 'training-classification', 'occupational', 'clinical', 'state-standard', 'none'];

test('у каждой таблицы норм указан тип данных', () => {
  for (const [name, entry] of Object.entries(NORMS)) {
    if (!entry || !entry.source) continue;
    assert.ok(VALID_KINDS.includes(entry.source.kind), `у таблицы ${name} нет корректного source.kind`);
  }
  for (const [name, spec] of Object.entries(TEST_NORMS)) {
    assert.ok(VALID_KINDS.includes(spec.source.kind), `у теста ${name} нет корректного source.kind`);
  }
});
