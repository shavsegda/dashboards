import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { tableAtAge, percentile, levelFromPercentile, ageGrade, ageGradeClass, vo2maxTable, bodyAgeFromVo2max, interpolateBodyAge, fitnessAgeNTNU, bodyComposition, recovery, evaluateTest, formScore, riskCards, weakestLink, bodyAgeCoverage, ageCovered, bodyAgeBounds, vo2maxFromCooper, clampSide, riskContext, estimateVo2maxNTNU, withinCoverage, vo2maxPercentile, riskCoverage, diffWithPrevious } from '../forma-calc.js';
import { NORMS, TEST_NORMS, KIND_POPULATION } from '../forma-norms.js';

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

test('классы age grading стоят ровно там, где их ставит источник', () => {
  // normy-beg.md, раздел 3 (USATF Masters): 60%+ местный, 70%+ региональный,
  // 80%+ национальный, 90%+ мировой, 100% — уровень мирового рекорда.
  assert.equal(ageGradeClass(45), 'начальный уровень');
  assert.equal(ageGradeClass(59.9), 'начальный уровень');
  assert.equal(ageGradeClass(60), 'местный уровень');
  assert.equal(ageGradeClass(65), 'местный уровень');
  assert.equal(ageGradeClass(70), 'региональный уровень');
  assert.equal(ageGradeClass(75), 'региональный уровень');
  assert.equal(ageGradeClass(80), 'национальный уровень');
  assert.equal(ageGradeClass(85), 'национальный уровень');
  assert.equal(ageGradeClass(90), 'мировой уровень');
  assert.equal(ageGradeClass(95), 'мировой уровень');
  assert.equal(ageGradeClass(100), 'уровень мирового рекорда');
});

test('контрольный пример самого источника: 68,5% — это местный уровень', () => {
  // Мужчина 40 лет, 10 км за 40:00 — 68,5% (normy-beg.md, раздел 4).
  // Раньше код называл этот результат региональным уровнем.
  const pct = ageGrade('m', 40, 10, 40 * 60);
  assert.equal(ageGradeClass(pct), 'местный уровень');
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
    // NORMS.hazards — коллекция из задачи 6, как когда-то TEST_NORMS внутри
    // NORMS.tests: у неё самой не может быть ОДНОГО source, потому что внутри
    // много независимых показателей с разными источниками (Mandsager 2018,
    // Yang 2019, Araújo 2022 и т.д. — см. отдельный тест на entries hazards
    // ниже). Общий source на всю коллекцию был бы придуманной атрибуцией —
    // именно поэтому TEST_NORMS в своё время вынесли из NORMS отдельным
    // экспортом. Здесь коллекция маленькая и специфичная для одной задачи,
    // выносить наружу отдельным экспортом ради неё избыточно — достаточно
    // пропустить её в этой общей проверке и полностью проверить отдельным
    // тестом на completeness каждой записи (см. ниже, задача 6).
    if (name === 'hazards') continue;
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

test('таблица дожития и показатель «доживают до N лет» удалены из данных и расчёта', () => {
  // Сцепка «перцентили FRIEND + таблица дожития + паспортный возраст» не
  // описана ни одним источником и выдавала абсурд (двадцатилетнему в плохой
  // форме — «до 29 лет»). Главной цифрой стал возраст тела.
  assert.equal(NORMS.lifeTable, undefined, 'таблица дожития обязана быть удалена целиком');
  const files = ['../forma-calc.js', '../forma-norms.js', '../forma.html'];
  for (const f of files) {
    const src = readFileSync(new URL(f, import.meta.url), 'utf8');
    assert.ok(!/lifeExpectancy|lifeTable/.test(src), `${f}: остались следы расчёта продолжительности жизни`);
    assert.ok(!/доживают|продолжительность жизни/i.test(src), `${f}: остался текст про продолжительность жизни`);
  }
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
  // ПРАВКА ПЕРЕД ПУБЛИКАЦИЕЙ: это не обследование населения, а уравнение
  // регрессии на добровольцах когорты HUNT3 — вторичные данные. То же самое
  // у реестра FRIEND: лабораторные тесты, а не репрезентативная выборка.
  assert.equal(NORMS.ntnuFormula.source.kind, 'population-secondary');
  assert.equal(NORMS.vo2max.source.kind, 'population-secondary');
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

test('порог стойки на одной ноге применяется только внутри когорты 51-75 лет', () => {
  // Araújo мерил людей 51-75 лет. Раньше 25-летний получал вердикт «порог
  // пройден» со ссылкой на работу, в которую он не входил, и одновременно
  // читал этажом выше «этот порог тебе проверить нечем».
  assert.deepEqual(TEST_NORMS.onelegstand.thresholdAgeRange, { min: 51, max: 75 });

  const inside = evaluateTest('onelegstand', 8, { sex: 'm', age: 60 });
  assert.equal(inside.belowThreshold, true);
  assert.equal(evaluateTest('onelegstand', 25, { sex: 'm', age: 60 }).belowThreshold, false);

  // Вне когорты вердикта нет вообще — ни «ниже порога», ни «порог пройден»
  const young = evaluateTest('onelegstand', 6, { sex: 'm', age: 25 });
  assert.equal(young.belowThreshold, null);
  assert.equal(young.value, 6, 'само время обязано остаться на экране');
  assert.match(young.note, /51-75/);

  const old = evaluateTest('onelegstand', 6, { sex: 'm', age: 80 });
  assert.equal(old.belowThreshold, null);

  // Ровно на границах когорта работает
  assert.equal(evaluateTest('onelegstand', 6, { sex: 'm', age: 51 }).belowThreshold, true);
  assert.equal(evaluateTest('onelegstand', 6, { sex: 'm', age: 75 }).belowThreshold, true);
});

test('пустое значение стойки не проходит проверку как «порог пройден»', () => {
  // null < 10 — это false, поэтому раньше пустое поле давало «порог пройден».
  for (const empty of [null, undefined, NaN, '']) {
    assert.equal(evaluateTest('onelegstand', empty, { sex: 'm', age: 60 }).belowThreshold, null,
      `пустое значение ${String(empty)} не должно давать вердикт`);
  }
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

test('наклон вперёд сидя не даёт перцентиля вовсе — только две опубликованные точки', () => {
  // Источник даёт только 5-й и 95-й перцентиль. Раньше между ними
  // достраивалась прямая, и человек читал «средний, 48,8 перцентиля» из
  // распределения, которого не существует.
  const r = evaluateTest('sitandreach', 20, { sex: 'm', age: 38, bodyWeight: 78 });
  assert.equal(r.percentile, null);
  assert.equal(r.level, null);
  assert.equal(r.informational, true);
  assert.equal(r.bounds.p5, TEST_NORMS.sitandreach.m[35].p5);
  assert.equal(r.bounds.p95, TEST_NORMS.sitandreach.m[35].p95);
  assert.match(r.note, /Разряда по этому тесту нет/);
});

test('наклон вперёд сидя для 70+ не даёт даже точек, и это сказано', () => {
  const r = evaluateTest('sitandreach', 20, { sex: 'm', age: 72, bodyWeight: 78 });
  assert.equal(r.percentile, null);
  assert.equal(r.bounds, null);
  assert.match(r.note, /не опубликован/);
  // Содержательная оговорка источника при этом никуда не делась
  assert.match(r.note, /перцентил/);
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
// 'population-secondary' добавлен по итогам ревью задачи 7: вторичная
// компиляция по обследованию населения (реконструированные перцентили
// отжиманий, наклон вперёд по цепочке цитирования) — значок 'population'
// обещал больше, чем стоит за этими таблицами.
const VALID_KINDS = ['population', 'population-secondary', 'training-classification', 'occupational', 'clinical', 'state-standard', 'none'];

test('у каждой таблицы норм указан тип данных', () => {
  for (const [name, entry] of Object.entries(NORMS)) {
    if (!entry || !entry.source) continue;
    assert.ok(VALID_KINDS.includes(entry.source.kind), `у таблицы ${name} нет корректного source.kind`);
  }
  for (const [name, spec] of Object.entries(TEST_NORMS)) {
    assert.ok(VALID_KINDS.includes(spec.source.kind), `у теста ${name} нет корректного source.kind`);
  }
});

// ---------------------------------------------------------------------
// Задача 6: счёт формы, цена провала, слабое звено.

const profile38m = { sex: 'm', age: 38, bodyWeight: 82 };

// pullups и broadjump — badge-тесты ГТО: у них percentile ВСЕГДА null,
// evaluateTest() никогда не вернёт для них число (см. forma-calc.js).
// ПРАВКА ПО ИТОГАМ РЕВЬЮ ЗАДАЧИ 6: раньше здесь стояли фиктивные
// percentile: 60 / percentile: 20 — тесты проходили, но не проверяли
// настоящий путь со знаком, и именно поэтому не поймали баг, из-за
// которого блок power был структурно не способен стать слабым звеном.
// Теперь оба результата получены через реальный evaluateTest().
const pullupsResult = evaluateTest('pullups', 9, profile38m); // 35-39 лет: bronze 4 / silver 7 / gold 11 → серебро
const broadjumpResult = evaluateTest('broadjump', 180, profile38m); // 35-39 лет: bronze 192 → ниже бронзы

const sample = [
  { key: 'vo2max', block: 'endurance', percentile: 80, informational: false },
  { key: 'pushups', block: 'strength', percentile: 75, informational: false },
  { key: pullupsResult.key, block: pullupsResult.block, badge: pullupsResult.badge, informational: pullupsResult.informational },
  { key: 'deadhang', block: 'strength', percentile: null, informational: true },
  { key: broadjumpResult.key, block: broadjumpResult.block, badge: broadjumpResult.badge, informational: broadjumpResult.informational },
];

test('счёт формы считает блоки, где больше половины тестов на медиане или выше', () => {
  const s = formScore(sample);
  assert.equal(s.byBlock.endurance, 'green');
  assert.equal(s.byBlock.strength, 'green');
  assert.equal(s.byBlock.power, 'red');
  assert.equal(s.green, 2);
});

test('справочные тесты в счёт не идут', () => {
  const onlyInfo = [{ key: 'deadhang', block: 'strength', percentile: null, informational: true }];
  assert.equal(formScore(onlyInfo).byBlock.strength, 'grey');
});

test('блок без данных серый и не считается ни зелёным, ни красным', () => {
  const s = formScore(sample);
  assert.equal(s.byBlock.mobility, 'grey');
  assert.equal(s.counted, 3);
});

test('знак ГТО в счёте формы: серебро/золото — зелёный, бронза и ниже — красный', () => {
  const gold = formScore([{ key: 'pullups', block: 'strength', badge: 'золото', informational: false }]);
  assert.equal(gold.byBlock.strength, 'green');
  const silver = formScore([{ key: 'pullups', block: 'strength', badge: 'серебро', informational: false }]);
  assert.equal(silver.byBlock.strength, 'green');
  const bronze = formScore([{ key: 'pullups', block: 'strength', badge: 'бронза', informational: false }]);
  assert.equal(bronze.byBlock.strength, 'red');
  const belowBronze = formScore([{ key: 'pullups', block: 'strength', badge: 'ниже бронзы', informational: false }]);
  assert.equal(belowBronze.byBlock.strength, 'red');
});

// ПРАВКА ПО ИТОГАМ ПОВТОРНОГО РЕВЬЮ ЗАДАЧИ 6 (критично): раньше знак ГТО
// раскладывался в число 0/33,3/66,7/100 и усреднялся с настоящими
// перцентилями других тестов блока — самодельная шкала, никто не
// публиковал, что «серебро» соответствует 67-му перцентилю населения.
// Теперь знак и перцентиль — два разных утверждения в разных полях, как
// уже честно сделано в isPass(). Блок power (единственный
// тест — прыжок в длину, он всегда badge, не перцентиль) в primary
// вообще не попадает — там нечего усреднять, а провал уходит в
// badgeFailures отдельной строкой.
test('провал по знаку ГТО попадает в badgeFailures, а не подмешивается в primary', () => {
  const weakPower = evaluateTest('broadjump', 150, profile38m); // сильно ниже порога бронзы (192 для 35-39)
  assert.equal(weakPower.percentile, null); // у этого теста перцентиля не бывает вообще
  assert.equal(weakPower.badge, 'ниже бронзы');

  const results = [
    { key: 'vo2max', block: 'endurance', percentile: 90, informational: false },
    { key: 'pushups', block: 'strength', percentile: 85, informational: false },
    { key: weakPower.key, block: weakPower.block, badge: weakPower.badge, informational: weakPower.informational },
  ];
  const result = weakestLink(results);
  // среди блоков с перцентилями хуже endurance (90) блок strength (85) —
  // power в это сравнение не входит, у него нет ни одного перцентиля
  assert.equal(result.primary.block, 'strength');
  assert.equal(result.badgeFailures.length, 1);
  assert.equal(result.badgeFailures[0].block, 'power');
  assert.equal(result.badgeFailures[0].testKey, 'broadjump');
  assert.equal(result.badgeFailures[0].badge, 'ниже бронзы');
});

test('если перцентилей нигде нет, а провал по знаку есть — primary равен null, badgeFailures заполнен', () => {
  const results = [
    { key: 'pullups', block: 'strength', badge: 'золото', informational: false },
    { key: 'broadjump', block: 'power', badge: 'бронза', informational: false },
  ];
  const result = weakestLink(results);
  assert.notEqual(result, null); // объект возвращается, а не null — данные есть (провал по знаку)
  assert.equal(result.primary, null); // ни у одного блока нет перцентиля
  assert.equal(result.badgeFailures.length, 1);
  assert.equal(result.badgeFailures[0].block, 'power');
  assert.equal(result.badgeFailures[0].badge, 'бронза');
});

test('знак «серебро» — не провал, в badgeFailures не попадает', () => {
  const results = [{ key: 'pullups', block: 'strength', badge: 'серебро', informational: false }];
  const result = weakestLink(results);
  // ни перцентилей, ни провалов — данных для weakestLink нет вообще
  assert.equal(result, null);
});

test('при наличии и перцентилей, и провала по знаку возвращаются оба поля заполненными', () => {
  const results = [
    { key: 'vo2max', block: 'endurance', percentile: 40, informational: false },
    { key: 'broadjump', block: 'power', badge: 'ниже бронзы', informational: false },
  ];
  const result = weakestLink(results);
  assert.ok(result.primary);
  assert.equal(result.primary.block, 'endurance');
  assert.equal(result.badgeFailures.length, 1);
  assert.equal(result.badgeFailures[0].block, 'power');
});

test('перевод знака ГТО в число нигде в forma-calc.js не остался', () => {
  const src = readFileSync(new URL('../forma-calc.js', import.meta.url), 'utf8');
  // раньше была функция badgeOrdinalPosition() и формула (rank / BADGE_ORDER['золото']) * 100 —
  // проверяем, что они не вернулись
  assert.ok(!src.includes('badgeOrdinalPosition'));
  assert.ok(!/BADGE_ORDER\['золото'\]\)\s*\*\s*100/.test(src));
});

test('карточки риска сгруппированы по исходу и отсортированы внутри группы от самого дорогого провала', () => {
  const groups = riskCards([
    { key: 'onelegstand', block: 'mobility', value: 6, percentile: 5, belowThreshold: true, age: 60 },
    { key: 'waistToHeight', block: 'body', value: 0.6, sex: 'm', age: 60 },
  ]);
  assert.equal(groups.length, 1); // оба про общую смертность — одна группа
  assert.equal(groups[0].outcome, 'общая смертность');
  const [first, second] = groups[0].cards;
  assert.ok(first.hazard >= second.hazard);
});

test('в каждой карточке риска сказано, что именно мерили, и указан источник', () => {
  const groups = riskCards([{ key: 'onelegstand', block: 'mobility', value: 6, age: 60 }]);
  const card = groups[0].cards[0];
  assert.ok(card.outcome.length > 0);
  assert.ok(card.reference.url);
});

test('VO2max и саркопения больше не персональные карточки, а сообщение от третьего лица', () => {
  // VO2max: перцентиль берётся из реестра FRIEND, а группа сравнения
  // опубликована на когорте другой клиники — сопоставить их нечем.
  // Саркопения: связки категории метаанализа с порогом EWGSOP2 не публиковал
  // никто. Обе цифры остаются, но уже без утверждения про человека.
  assert.equal(NORMS.hazards.vo2max.trigger.kind, 'groupComparison');
  assert.equal(NORMS.hazards.smi.trigger.kind, 'groupComparison');

  const results = [
    { key: 'vo2max', block: 'endurance', value: 22, percentile: 5, sex: 'm', age: 38 },
    { key: 'smi', block: 'body', value: 6.5, sex: 'm', age: 70 },
  ];
  assert.equal(riskCards(results).length, 0, 'персональных карточек у них быть не должно');

  const context = riskContext(results);
  assert.equal(context.length, 2);
  for (const item of context) {
    assert.equal(item.kind, 'groupComparison');
    assert.ok(item.hazard > 1);
    assert.ok(item.reference.url);
  }

  // И в охват проверки порогов они не попадают: порога, по которому можно
  // проверить человека, здесь нет вовсе
  const coverage = riskCoverage(results);
  assert.equal(coverage.checked.length, 0);
  assert.equal(coverage.outOfCohort.length, 0);
});

test('карточка не создаётся для показателя без опубликованного коэффициента', () => {
  const groups = riskCards([{ key: 'deadhang', block: 'strength', percentile: null, informational: true }]);
  assert.equal(groups.length, 0);
});

test('карточка риска, разбитого по полу (талия к росту), берёт цифру и ДИ своего пола', () => {
  const menGroups = riskCards([{ key: 'waistToHeight', block: 'body', value: 0.6, belowThreshold: true, sex: 'm' }]);
  const womenGroups = riskCards([{ key: 'waistToHeight', block: 'body', value: 0.6, belowThreshold: true, sex: 'f' }]);
  assert.equal(menGroups[0].cards[0].hazard, NORMS.hazards.waistToHeight.hazard.m);
  assert.equal(womenGroups[0].cards[0].hazard, NORMS.hazards.waistToHeight.hazard.f);
  assert.deepEqual(menGroups[0].cards[0].ci, NORMS.hazards.waistToHeight.ci.m);
  assert.deepEqual(womenGroups[0].cards[0].ci, NORMS.hazards.waistToHeight.ci.f);
});

test('карточка риска с полом не указан — карточка не создаётся, чтобы не подставлять чужую цифру', () => {
  const groups = riskCards([{ key: 'waistToHeight', block: 'body', value: 0.6, belowThreshold: true }]);
  assert.equal(groups.length, 0);
});

test('карточка риска различает исход: сердечно-сосудистые события идут отдельной группой от общей смертности', () => {
  const groups = riskCards([
    { key: 'pushups', block: 'strength', value: 5, sex: 'm', age: 40 },
    { key: 'onelegstand', block: 'mobility', value: 6, sex: 'm', age: 60 },
  ]);
  assert.equal(groups.length, 2);
  const mortality = groups.find((g) => g.outcome === 'общая смертность');
  const cvEvents = groups.find((g) => g.outcome === 'сердечно-сосудистые события');
  assert.ok(mortality, 'должна быть группа "общая смертность"');
  assert.ok(cvEvents, 'должна быть группа "сердечно-сосудистые события"');
  assert.equal(cvEvents.cards[0].testKey, 'pushups');
  assert.equal(mortality.cards[0].testKey, 'onelegstand');
  // группы не сравниваются между собой — у групп нет общего рейтинга,
  // порядок групп фиксированный (см. OUTCOME_ORDER в forma-calc.js)
  assert.equal(groups[0].outcome, 'общая смертность');
  assert.equal(groups[1].outcome, 'сердечно-сосудистые события');
});

test('карточка риска несёт доверительный интервал и размер когорты там, где источник их даёт', () => {
  const withCi = riskCards([{ key: 'onelegstand', block: 'mobility', value: 6, age: 60 }])[0].cards[0];
  assert.deepEqual(withCi.ci, NORMS.hazards.onelegstand.ci);
  assert.ok(withCi.cohortSize);

  // Отжимания: верхняя граница интервала получена из округлённого числа —
  // это подписано, а не выдаётся за точную величину.
  const pushups = riskCards([{ key: 'pushups', block: 'strength', value: 5, sex: 'm', age: 40 }])[0].cards[0];
  assert.equal(pushups.ci.high, 100);
  assert.match(pushups.ciNote, /округлённого/);
});

test('пульс покоя: взят коэффициент, который источник подаёт основным, вместе с интервалом', () => {
  // Раньше стоял 1,17 вообще без интервала, хотя сводная таблица источника
  // основным даёт 1,09 с интервалом 1,07-1,12.
  const h = NORMS.hazards.restingHR;
  assert.equal(h.hazard, 1.09);
  assert.deepEqual(h.ci, { low: 1.07, high: 1.12 });
  assert.equal(h.alternative.hazard, 1.17); // вторая оценка не потеряна, но не выбрана
  assert.ok(h.source.authors && !/не указан/.test(h.source.authors));

  const item = riskContext([{ key: 'restingHR', block: 'recovery', value: 82, percentile: 16, age: 55 }])[0];
  assert.deepEqual(item.ci, { low: 1.07, high: 1.12 });
  assert.ok(item.cohortSize);
});

// ПРАВКА ПО ИТОГАМ РЕВЬЮ ЗАДАЧИ 6: раньше условие провала в riskCards не
// умело смотреть на знак ГТО вообще — как только у badge-теста появился
// бы коэффициент риска, карточка не создавалась бы никогда, даже при
// «ниже бронзы». Сейчас ни у одного badge-теста нет реального коэффициента
// в NORMS.hazards, поэтому проверяем ветку через временную тестовую запись
// и сразу её убираем.
test('провал по знаку ГТО тоже создаёт карточку риска — защита от будущей мины', () => {
  NORMS.hazards.__test_badge_hazard__ = {
    hazard: 2,
    ci: null,
    cohortSize: null,
    condition: 'тестовое условие',
    trigger: { kind: 'badgeAtOrBelow', value: 'бронза' },
    outcome: 'общая смертность',
    source: { title: 'тест', authors: 'тест', year: 2000, url: 'https://example.com' },
  };
  try {
    const belowBronze = riskCards([{ key: '__test_badge_hazard__', block: 'power', badge: 'ниже бронзы', informational: false }]);
    assert.equal(belowBronze.length, 1);
    assert.equal(belowBronze[0].cards[0].hazard, 2);

    const bronze = riskCards([{ key: '__test_badge_hazard__', block: 'power', badge: 'бронза', informational: false }]);
    assert.equal(bronze.length, 1);

    const gold = riskCards([{ key: '__test_badge_hazard__', block: 'power', badge: 'золото', informational: false }]);
    assert.equal(gold.length, 0); // золото — не провал, карточки нет
  } finally {
    delete NORMS.hazards.__test_badge_hazard__;
  }
});

test('слабое звено — блок с самым низким средним перцентилем среди блоков с перцентилями, badgeFailures отдельно', () => {
  const result = weakestLink(sample);
  // power в primary не участвует: у него в sample только badge ('ниже бронзы'
  // у broadjump), ни одного перцентиля. Из блоков с перцентилями (endurance
  // 80, strength — только pushups 75, пуллапы badge в среднее не входят)
  // хуже strength.
  assert.equal(result.primary.block, 'strength');
  assert.equal(result.badgeFailures.length, 1);
  assert.equal(result.badgeFailures[0].testKey, 'broadjump');
});

test('слабое звено не выбирается, когда данных нет совсем', () => {
  assert.equal(weakestLink([]), null);
});

test('каждый коэффициент риска в NORMS.hazards полностью описан: условие, исход, источник, ДИ/когорта корректной формы', () => {
  const allowedOutcomes = ['общая смертность', 'сердечно-сосудистые события'];
  const isCiShape = (ci) => ci === null || ci === undefined
    || (typeof ci.low === 'number' && typeof ci.high === 'number');
  for (const [key, h] of Object.entries(NORMS.hazards)) {
    assert.ok(allowedOutcomes.includes(h.outcome), `${key}: неизвестный исход "${h.outcome}"`);
    assert.ok(typeof h.condition === 'string' && h.condition.length > 0, `${key}: нет условия сравнения`);
    assert.ok(h.source && h.source.title && h.source.authors && h.source.year && h.source.url, `${key}: неполный источник`);
    const hazardOk = typeof h.hazard === 'number' || (h.hazard && typeof h.hazard.m === 'number' && typeof h.hazard.f === 'number');
    assert.ok(hazardOk, `${key}: hazard должен быть числом либо объектом {m, f}`);
    // ci — либо null (в источнике интервала нет), либо {low, high}, либо
    // {m: {low, high}, f: {low, high}} для показателей, разбитых по полу.
    const ciOk = h.ci === undefined || h.ci === null || isCiShape(h.ci)
      || (h.ci && isCiShape(h.ci.m) && isCiShape(h.ci.f));
    assert.ok(ciOk, `${key}: ci должен быть null, {low, high} либо {m, f} c такой формой`);
    assert.ok(h.cohortSize === undefined || h.cohortSize === null || typeof h.cohortSize === 'string', `${key}: cohortSize должен быть строкой либо null`);
  }
});


// ---------------------------------------------------------------------
// Задача 7, правки по ревью.

test('главная цифра не считается за границами покрытия таблицы FRIEND', () => {
  const c = bodyAgeCoverage();
  assert.equal(c.min, NORMS.vo2max.ageCoverage.min);
  assert.equal(c.max, NORMS.vo2max.ageCoverage.max);

  // Ровно на границах — считается, за ними нет
  assert.ok(ageCovered(c.min) && ageCovered(c.max));
  assert.ok(!ageCovered(c.min - 1) && !ageCovered(c.max + 1));
  assert.ok(!ageCovered(14) && !ageCovered(100));
  assert.ok(!ageCovered(null));
});

test('границы возраста тела берутся из таблицы FRIEND, а не из текста', () => {
  const b = bodyAgeBounds('m');
  assert.equal(b.min, 25);
  assert.equal(b.max, 75);
  assert.equal(bodyAgeFromVo2max(99, 'm'), b.min); // очень высокий VO2max упирается в пол
  assert.equal(bodyAgeFromVo2max(5, 'm'), b.max); // очень низкий — в потолок
});

test('формула Купера считается только мужчинам и только внутри возрастной когорты', () => {
  const men = vo2maxFromCooper(2800, 'm', 38);
  assert.ok(Math.abs(men - (2800 - 504.9) / 44.73) < 1e-9);
  assert.ok(men > 50 && men < 52, `ожидали около 51, получили ${men}`);
  assert.equal(vo2maxFromCooper(2800, 'f', 38), null); // женщин в выборке Купера не было
  assert.equal(vo2maxFromCooper(0, 'm', 38), null);
  assert.equal(vo2maxFromCooper(400, 'm', 38), null); // ниже свободного члена — отрицательный VO2max

  // Возрастной охват когорты оригинала — 17-52 года, он назван в источнике
  assert.deepEqual(NORMS.cooper.ageCoverage, { min: 17, max: 52 });
  assert.equal(vo2maxFromCooper(2800, 'm', 16), null);
  assert.equal(vo2maxFromCooper(2800, 'm', 60), null);
  assert.equal(typeof vo2maxFromCooper(2800, 'm', 17), 'number');
  assert.equal(typeof vo2maxFromCooper(2800, 'm', 52), 'number');
  assert.equal(vo2maxFromCooper(2800, 'm', null), null); // без возраста проверить нечем
});

test('карточка риска не создаётся, когда человек не попал в группу сравнения', () => {
  // 20 отжиманий: источник сравнивает «меньше 10» с «больше 40» — человек не в группе
  assert.equal(riskCards([{ key: 'pushups', block: 'strength', value: 20, percentile: 10, sex: 'm', age: 40 }]).length, 0);
  // 5 отжиманий — в группе, карточка есть
  assert.equal(riskCards([{ key: 'pushups', block: 'strength', value: 5, percentile: 5, sex: 'm', age: 40 }]).length, 1);

  // Стойка на одной ноге: порог 10 секунд
  assert.equal(riskCards([{ key: 'onelegstand', block: 'mobility', value: 12, age: 60 }]).length, 0);
  assert.equal(riskCards([{ key: 'onelegstand', block: 'mobility', value: 6, age: 60 }]).length, 1);

  // Талия к росту: сравнение источника — 0,55 и выше
  assert.equal(riskCards([{ key: 'waistToHeight', block: 'body', value: 0.52, sex: 'm' }]).length, 0);
  assert.equal(riskCards([{ key: 'waistToHeight', block: 'body', value: 0.56, sex: 'm' }]).length, 1);

  // Саркопения и VO2max — не персональные карточки вовсе (см. отдельный тест)
  assert.equal(riskCards([{ key: 'smi', block: 'body', value: 6.5, sex: 'm' }]).length, 0);
});

test('коэффициенты-градиенты не попадают в персональные карточки', () => {
  const results = [
    { key: 'restingHR', block: 'recovery', value: 82, percentile: 16, age: 55 },
    { key: 'grip', block: 'strength', value: 25, percentile: 0, age: 55 },
  ];
  assert.equal(riskCards(results).length, 0, 'градиент не может быть личным множителем риска');

  const gradients = riskContext(results);
  assert.equal(gradients.length, 2);
  assert.ok(gradients.every((g) => typeof g.step === 'string' && g.step.length > 0));
  assert.ok(gradients.every((g) => g.reference && g.reference.url));
  // Незаполненный показатель в список не попадает
  assert.equal(riskContext([{ key: 'grip', block: 'strength', value: null, age: 55 }]).length, 0);
});

test('невозможный беговой результат не оценивается', () => {
  assert.equal(ageGrade('m', 38, '5', 24), null); // 5 км за 24 секунды
  assert.equal(ageGrade('m', 38, '5', 0), null);
  assert.equal(ageGrade('m', 38, '5', -10), null);
  assert.ok(ageGrade('m', 38, '5', 1470) > 0); // нормальные 24:30 считаются
});

test('значение за краем таблицы помечается, но разряд получает', () => {
  assert.equal(clampSide(0), 'below');
  assert.equal(clampSide(100), 'above');
  assert.equal(clampSide(50), null);
  assert.equal(clampSide(null), null);

  // Сила хвата 5 кг у мужчины 38 лет — ниже нижнего узла таблицы
  const r = evaluateTest('grip', 5, { sex: 'm', age: 38 });
  assert.equal(r.percentile, 0);
  assert.equal(r.level, 'начальный уровень'); // разряд всё равно присвоен
  assert.equal(r.clamped, 'below');

  // Вторичное чтение силовых тоже помечается
  const light = evaluateTest('squat1rm', 30, { sex: 'm', age: 38, bodyWeight: 95 });
  assert.equal(light.secondaryClamped, 'below');
});

test('правило обнуления индекса активности живёт в данных и работает', () => {
  const zeroBelow = NORMS.ntnuFormula.activityIndex.zeroBelowFrequency;
  assert.equal(typeof zeroBelow, 'number');
  const base = { sex: 'm', age: 40, bmi: 25, restingHR: 60 };
  const never = fitnessAgeNTNU({ ...base, trainingFreq: 0, trainingIntensity: 3, trainingDuration: 1 });
  const rare = fitnessAgeNTNU({ ...base, trainingFreq: 0.5, trainingIntensity: 3, trainingDuration: 1 });
  const often = fitnessAgeNTNU({ ...base, trainingFreq: 5, trainingIntensity: 3, trainingDuration: 1 });
  assert.equal(never, rare, '«реже раза в неделю» обязано давать тот же индекс 0, что и «никогда»');
  assert.ok(often < never, 'тренирующийся человек получает возраст тела моложе');
});

test('варианты ответов шкалы активности лежат в данных, а не в разметке', () => {
  const ai = NORMS.ntnuFormula.activityIndex;
  for (const key of ['frequency', 'intensity', 'duration']) {
    assert.ok(Array.isArray(ai[key]) && ai[key].length >= 3, `${key}: нет вариантов ответа`);
    for (const option of ai[key]) {
      assert.equal(typeof option.label, 'string');
      assert.equal(typeof option.value, 'number');
    }
  }
});

test('перевёрнутые шкалы: у пульса покоя и процента жира выше перцентиль — лучше показатель', () => {
  const low = recovery({ sex: 'm', age: 38, restingHR: 50 }).restingHR;
  const high = recovery({ sex: 'm', age: 38, restingHR: 85 }).restingHR;
  assert.ok(low.percentile > high.percentile, 'низкий пульс обязан давать более высокий перцентиль');

  const lean = bodyComposition({ sex: 'm', age: 38, height: 178, weight: 78, bodyFatPct: 12 });
  const fat = bodyComposition({ sex: 'm', age: 38, height: 178, weight: 78, bodyFatPct: 35 });
  assert.ok(lean.bodyFat.percentile < fat.bodyFat.percentile, 'в таблице жира больше процент — выше перцентиль');
  assert.equal(lean.bodyFat.level, 'продвинутый'); // а уровень при этом перевёрнут
  assert.equal(fat.bodyFat.level, 'начальный уровень');
  assert.match(lean.bodyFat.note, /этническ/i); // оговорка про подгруппу NHANES видна пользователю
});

test('у каждого коэффициента риска есть машиночитаемое условие срабатывания', () => {
  const kinds = ['valueBelow', 'valueAtOrAbove', 'percentileBelow', 'badgeAtOrBelow', 'gradient', 'groupComparison'];
  for (const [key, h] of Object.entries(NORMS.hazards)) {
    assert.ok('trigger' in h, `${key}: нет поля trigger`);
    if (h.trigger === null) continue; // осознанное «условие определить нечем» (регулярность сна)
    assert.ok(kinds.includes(h.trigger.kind), `${key}: неизвестный вид условия ${h.trigger.kind}`);
    if (h.trigger.kind === 'gradient') {
      assert.ok(typeof h.trigger.step === 'string' && h.trigger.step.length > 0, `${key}: у градиента нет шага`);
    }
  }
});

test('примечания склеиваются как предложения, без строчной буквы после точки', () => {
  const r = evaluateTest('pullups', 5, { sex: 'm', age: 62 }); // возраст вне собранных ступеней ГТО
  assert.match(r.note, /не опубликован/);
  assert.ok(!/\.\s+[а-яё]/.test(r.note), `в примечании строчная буква после точки: ${r.note}`);
});

test('в клиентские тексты норм не утекли имена переменных', () => {
  const texts = [];
  for (const spec of Object.values(TEST_NORMS)) {
    if (spec.note) texts.push(spec.note);
    if (spec.coverageNote) texts.push(spec.coverageNote);
  }
  for (const t of texts) {
    assert.ok(!/secondaryPercentile|belowThreshold|percentile:/.test(t), `имя переменной в тексте: ${t}`);
  }
});


// ---------------------------------------------------------------------
// Задача 7, вторая правка по ревью: границы 20-79 ограничивают только
// главную цифру. Каждый тест живёт по своему покрытию.

test('покрытие таблицы читается из данных, открытая верхняя группа не ограничивает', () => {
  assert.equal(withinCoverage(38, { min: 20, max: 79 }), true);
  assert.equal(withinCoverage(17, { min: 20, max: 79 }), false);
  assert.equal(withinCoverage(82, { min: 20, max: 79 }), false);
  assert.equal(withinCoverage(95, { min: 20, max: null }), true); // «80 и старше» у пульса покоя
  assert.equal(withinCoverage(null, { min: 20, max: 79 }), false);
});

test('вне границ главной цифры отдельный тест продолжает считаться внутри своего покрытия', () => {
  // Женщина 82: главной цифры нет, а сила хвата покрыта до 85 лет
  assert.equal(ageCovered(82), false);

  const grip = evaluateTest('grip', 20, { sex: 'f', age: 82 });
  assert.equal(typeof grip.percentile, 'number', 'разряд по хвату в 82 года обязан считаться');
  assert.ok(grip.level);

  // А тест, чья таблица кончается раньше, честно отказывает
  const pushups = evaluateTest('pushups', 10, { sex: 'f', age: 82 });
  assert.equal(pushups.percentile, null);
  assert.match(pushups.note, /не опубликован/);
});

test('младше нижней границы таблицы разряд не присваивается', () => {
  // 17 лет: таблица отжиманий начинается с 20 — раньше ageBucket() молча
  // подставлял группу двадцатилетних
  const pushups = evaluateTest('pushups', 30, { sex: 'm', age: 17 });
  assert.equal(pushups.percentile, null);
  assert.equal(pushups.level, null);
  assert.match(pushups.note, /таблица начинается с 20 лет/);

  // Сила хвата покрыта с 18 лет — в 17 тоже отказ, в 18 уже считается
  assert.equal(evaluateTest('grip', 40, { sex: 'm', age: 17 }).percentile, null);
  assert.equal(typeof evaluateTest('grip', 40, { sex: 'm', age: 18 }).percentile, 'number');

  // Знак ГТО для 17 лет из собранных ступеней тоже не выдаётся
  assert.equal(evaluateTest('pullups', 10, { sex: 'm', age: 17 }).badge, null);
});

test('перцентиль VO2max, процента жира и пульса покоя не берётся из чужой возрастной группы', () => {
  assert.equal(vo2maxPercentile(55, 'm', 17), null);
  assert.equal(vo2maxPercentile(30, 'f', 82), null);
  assert.equal(typeof vo2maxPercentile(52, 'm', 38), 'number');

  const teenFat = bodyComposition({ sex: 'm', age: 17, height: 180, weight: 70, bodyFatPct: 15 });
  assert.equal(teenFat.bodyFat.percentile, null);
  assert.equal(teenFat.bodyFat.level, null);
  assert.match(teenFat.bodyFat.note, /от 20 до 80/);

  const teenHr = recovery({ sex: 'm', age: 17, restingHR: 60 });
  assert.equal(teenHr.restingHR.percentile, null);
  assert.match(teenHr.restingHR.note, /не опубликован/);

  // Пожилой человек по пульсу покоя покрыт: верхняя группа источника открытая
  const oldHr = recovery({ sex: 'f', age: 82, restingHR: 72 });
  assert.equal(typeof oldHr.restingHR.percentile, 'number');
});

test('карточка риска не показывается полу, которого не было в когорте источника', () => {
  // Yang 2019 — «Among Active Adult Men», 1104 мужчины-пожарные
  assert.deepEqual(NORMS.hazards.pushups.applicableSex, ['m']);
  assert.equal(riskCards([{ key: 'pushups', block: 'strength', value: 8, sex: 'f', age: 40 }]).length, 0);
  assert.equal(riskCards([{ key: 'pushups', block: 'strength', value: 8, sex: 'm', age: 40 }]).length, 1);
});

test('категория ИМТ по ВОЗ не выдаётся тем, для кого она не построена', () => {
  const teen = bodyComposition({ sex: 'm', age: 17, height: 180, weight: 70 });
  assert.equal(teen.bmi.category, null);
  assert.match(teen.bmi.note, /для взрослых/);
  assert.ok(teen.bmi.value > 21 && teen.bmi.value < 22); // само значение считается

  const adult = bodyComposition({ sex: 'm', age: 38, height: 178, weight: 78 });
  assert.equal(adult.bmi.category, 'норма');
});

test('карточка риска не показывается возрасту, которого не было в когорте источника', () => {
  // Yang 2019: «men aged 21 to 66 years»
  assert.deepEqual(NORMS.hazards.pushups.cohortAgeRange, { min: 21, max: 66 });
  const card = (age) => riskCards([{ key: 'pushups', block: 'strength', value: 5, sex: 'm', age }]).length;
  assert.equal(card(82), 0, 'мужчина 82 лет вне когорты пожарных — карточки быть не должно');
  assert.equal(card(40), 1, 'мужчина 40 лет внутри когорты — карточка есть');
  assert.equal(card(21), 1); // ровно на границе
  assert.equal(card(66), 1);
  assert.equal(card(20), 0);
  assert.equal(card(67), 0);

  // Стойка на одной ноге: когорта CLINIMEX 51-75 лет
  const stand = (age) => riskCards([{ key: 'onelegstand', block: 'mobility', value: 6, age }]).length;
  assert.equal(stand(38), 0, '38 лет — вне когорты 51-75');
  assert.equal(stand(60), 1);
  assert.equal(stand(80), 0);

  // Возраст неизвестен, а охват у когорты задан — проверить нечем, карточки нет
  assert.equal(riskCards([{ key: 'pushups', block: 'strength', value: 5, sex: 'm' }]).length, 0);

  // Где охвата в источнике нет, ограничение не применяется
  assert.equal(NORMS.hazards.waistToHeight.cohortAgeRange, null);
  assert.equal(riskCards([{ key: 'waistToHeight', block: 'body', value: 0.6, sex: 'm', age: 82 }]).length, 1);
});

test('градиент тоже не показывается вне охвата когорты', () => {
  // PURE: «aged 35–70 years»
  assert.deepEqual(NORMS.hazards.grip.cohortAgeRange, { min: 35, max: 70 });
  assert.equal(riskContext([{ key: 'grip', block: 'strength', value: 20, age: 82 }]).length, 0);
  assert.equal(riskContext([{ key: 'grip', block: 'strength', value: 20, age: 55 }]).length, 1);
  // У пульса покоя охвата нет — показывается в любом возрасте
  assert.equal(riskContext([{ key: 'restingHR', block: 'recovery', value: 72, age: 82 }]).length, 1);
});

test('у каждого коэффициента риска описан охват когорты и сказано, откуда он взят', () => {
  for (const [key, h] of Object.entries(NORMS.hazards)) {
    assert.ok('cohortAgeRange' in h, `${key}: нет поля cohortAgeRange`);
    assert.ok(typeof h.cohortAgeRangeSource === 'string' && h.cohortAgeRangeSource.length > 0,
      `${key}: не сказано, откуда взят возрастной охват (или почему его нет)`);
    if (h.cohortAgeRange !== null) {
      assert.equal(typeof h.cohortAgeRange.min, 'number');
      assert.equal(typeof h.cohortAgeRange.max, 'number');
      assert.ok(h.cohortAgeRange.min < h.cohortAgeRange.max, `${key}: границы охвата перепутаны`);
    }
    if (h.applicableSex !== undefined) {
      assert.ok(Array.isArray(h.applicableSex) && h.applicableSex.every((x) => x === 'm' || x === 'f'), `${key}: неверный applicableSex`);
    }
  }
});


// ---------------------------------------------------------------------
// Задача 8: история замеров и разница с прошлым разом.

test('дельта считается только по показателям, которые есть в обоих замерах', () => {
  const prev = { vo2max: 48, pushups: 30 };
  const cur = { vo2max: 52, pullups: 12 };
  const d = diffWithPrevious(cur, prev);
  assert.equal(d.length, 1);
  assert.equal(d[0].key, 'vo2max');
  assert.equal(d[0].delta, 4);
});

test('без прошлого замера дельта пустая', () => {
  assert.deepEqual(diffWithPrevious({ vo2max: 52 }, null), []);
});

test('дельта несёт откуда, куда и на сколько, а название берёт из таблиц или снаружи', () => {
  const d = diffWithPrevious({ pushups: 25, vo2max: 50 }, { pushups: 30, vo2max: 48 }, { vo2max: 'VO2max' });
  const pushups = d.find((x) => x.key === 'pushups');
  assert.equal(pushups.from, 30);
  assert.equal(pushups.to, 25);
  assert.equal(pushups.delta, -5);
  assert.equal(pushups.label, TEST_NORMS.pushups.label); // название из таблицы теста
  assert.equal(d.find((x) => x.key === 'vo2max').label, 'VO2max'); // название передано снаружи
});

test('нечисловые и пустые значения в дельту не попадают', () => {
  const d = diffWithPrevious({ vo2max: 52, sex: 'm', pushups: null }, { vo2max: 48, sex: 'm', pushups: 30 });
  assert.equal(d.length, 1);
  assert.equal(d[0].key, 'vo2max');
});

test('охват проверки различает «проверили» и «проверить было нечем»', () => {
  const young = riskCoverage([{ key: 'onelegstand', block: 'mobility', value: 6, age: 38, sex: 'm' }]);
  assert.equal(young.checked.length, 0);
  assert.equal(young.outOfCohort.length, 1);
  assert.match(young.outOfCohort[0].cohort, /51-75/);

  const inCohort = riskCoverage([{ key: 'onelegstand', block: 'mobility', value: 6, age: 60, sex: 'm' }]);
  assert.equal(inCohort.checked.length, 1);
  assert.equal(inCohort.outOfCohort.length, 0);

  // Женщина и отжимания: когорта источника — только мужчины
  const woman = riskCoverage([{ key: 'pushups', block: 'strength', value: 8, age: 40, sex: 'f' }]);
  assert.equal(woman.outOfCohort.length, 1);
  assert.match(woman.outOfCohort[0].cohort, /мужчин/);

  // Градиенты и показатели без порога в охват проверки не входят
  assert.equal(riskCoverage([{ key: 'grip', block: 'strength', value: 25, age: 55, sex: 'm' }]).checked.length, 0);
  assert.equal(riskCoverage([{ key: 'plank', block: 'strength', value: 60, age: 40, sex: 'm' }]).outOfCohort.length, 0);
});

test('протокол подтягиваний и обе стороны сравнения талии лежат в данных', () => {
  assert.equal(TEST_NORMS.pullups.protocol.lowBarHeightCm, 90);
  assert.ok(TEST_NORMS.pullups.protocol.m.length > 0 && TEST_NORMS.pullups.protocol.f.length > 0);
  const t = NORMS.hazards.waistToHeight.trigger;
  assert.equal(t.value, 0.55);
  assert.equal(t.referenceBelow, 0.5);
});


// ---------------------------------------------------------------------
// Правки перед публикацией.

test('перцентиль жира считается интерполяцией между возрастными точками источника', () => {
  // Источник (NHANES/DXA) даёт параметры распределения для точных возрастов
  // 20, 30, 40... Раньше код читал их как десятилетние группы, и 29-летний
  // сравнивался с нормой двадцатилетнего.
  const at20 = bodyComposition({ sex: 'm', age: 20, height: 178, weight: 78, bodyFatPct: 20 }).bodyFat.percentile;
  const at29 = bodyComposition({ sex: 'm', age: 29, height: 178, weight: 78, bodyFatPct: 20 }).bodyFat.percentile;
  const at30 = bodyComposition({ sex: 'm', age: 30, height: 178, weight: 78, bodyFatPct: 20 }).bodyFat.percentile;

  assert.notEqual(at29, at20, '29 лет не должен сравниваться с нормой двадцатилетнего');
  assert.ok(at29 < at20, 'с возрастом медиана жира растёт — тот же процент даёт меньший перцентиль');
  assert.ok(at29 > at30, 'и 29-летний обязан оказаться между точками 20 и 30');
  // Ровно на опубликованных точках интерполяция ничего не меняет
  assert.equal(at20, percentile(20, NORMS.bodyFat.m[20]));
  assert.equal(at30, percentile(20, NORMS.bodyFat.m[30]));
});

test('интерполяция таблицы: на узле возвращает узел, между узлами — середину', () => {
  const byAge = { 20: { p50: 10 }, 30: { p50: 20 } };
  assert.equal(tableAtAge(20, byAge).p50, 10);
  assert.equal(tableAtAge(30, byAge).p50, 20);
  assert.equal(tableAtAge(25, byAge).p50, 15);
  assert.equal(tableAtAge(10, byAge).p50, 10); // за краем — крайняя точка
  assert.equal(tableAtAge(90, byAge).p50, 20);
});

test('верхняя граница покрытия по проценту жира — 80 лет, как в источнике', () => {
  assert.equal(NORMS.bodyFat.ageCoverage.max, 80);
  assert.equal(typeof bodyComposition({ sex: 'f', age: 80, height: 160, weight: 60, bodyFatPct: 40 }).bodyFat.percentile, 'number');
  assert.equal(bodyComposition({ sex: 'f', age: 85, height: 160, weight: 60, bodyFatPct: 40 }).bodyFat.percentile, null);
});

test('вторичное чтение силовых не выходит за таблицу веса и не живёт без основного разряда', () => {
  const weights = Object.keys(TEST_NORMS.squat1rm.secondary.m).map(Number).sort((a, b) => a - b);
  const lightest = weights[0];
  const heaviest = weights[weights.length - 1];

  // Внутри таблицы — считается
  const inside = evaluateTest('squat1rm', 120, { sex: 'm', age: 38, bodyWeight: 80 });
  assert.equal(typeof inside.secondaryPercentile, 'number');

  // Тяжелее и легче таблицы — не считается, и человеку сказано почему
  const heavy = evaluateTest('squat1rm', 120, { sex: 'm', age: 38, bodyWeight: heaviest + 30 });
  assert.equal(heavy.secondaryPercentile, null);
  assert.match(heavy.note, new RegExp(`от ${lightest} до ${heaviest} кг`));
  const light = evaluateTest('squat1rm', 60, { sex: 'm', age: 38, bodyWeight: lightest - 8 });
  assert.equal(light.secondaryPercentile, null);

  // Основного разряда нет — вторичного тоже нет: и у подростка, и у 95-летнего
  const teen = evaluateTest('squat1rm', 100, { sex: 'm', age: 15, bodyWeight: 70 });
  assert.equal(teen.percentile, null);
  assert.equal(teen.secondaryPercentile, null);
  const old = evaluateTest('squat1rm', 60, { sex: 'm', age: 95, bodyWeight: 70 });
  assert.equal(old.percentile, null);
  assert.equal(old.secondaryPercentile, null);
});

test('название популяции лежит в данных рядом с типом источника', () => {
  assert.equal(KIND_POPULATION['population'], 'людей твоего пола и возраста');
  assert.equal(KIND_POPULATION['training-classification'], 'тренирующихся твоего пола и возраста');
  // У знака ГТО и у «норм нет» перцентиля не бывает — популяции тоже
  assert.equal(KIND_POPULATION['state-standard'], null);
  assert.equal(KIND_POPULATION['none'], null);

  // Каждый тип данных, встречающийся в нормах, обязан иметь запись
  const kinds = new Set();
  for (const entry of Object.values(NORMS)) if (entry && entry.source) kinds.add(entry.source.kind);
  for (const spec of Object.values(TEST_NORMS)) kinds.add(spec.source.kind);
  for (const k of kinds) assert.ok(k in KIND_POPULATION, `нет названия популяции для типа ${k}`);

  // Вторичное чтение по весу тела — своя популяция, без возраста
  const secondary = evaluateTest('squat1rm', 120, { sex: 'm', age: 38, bodyWeight: 80 });
  assert.equal(secondary.secondaryPopulation, 'людей твоего веса');
  assert.ok(!/возраст/.test(secondary.secondaryPopulation));
});

// Тест-страж на утечку служебных текстов. Сканирует ВСЕ клиентские строки во
// всех трёх файлах: данные норм целиком, строковые литералы расчёта и
// разметки, а также текст самой страницы вне скрипта.
const LEAK_PATTERNS = [
  { re: /[A-Za-z0-9_-]+\.(?:js|md|html)\b/, what: 'имя файла проекта' },
  { re: /\bforma-(?:calc|norms)\b|\bnormy-[a-z]/i, what: 'имя файла проекта' },
  { re: /secondaryPercentile|belowThreshold|secondaryLevel|informational|ageBucket|cohortAgeRange|applicableSex|badgeTest|maxAge|percentile\(\)|evaluateTest|TEST_NORMS|NORMS\./, what: 'имя переменной или функции' },
];

function assertNoLeak(text, where) {
  for (const { re, what } of LEAK_PATTERNS) {
    assert.ok(!re.test(text), `${where}: в клиентский текст утёк ${what} — «${text.slice(0, 160)}»`);
  }
}

// Все строки из данных норм, кроме адресов ссылок (там точки и латиница —
// это адрес, а не текст для человека).
function collectStrings(node, path, out) {
  if (typeof node === 'string') {
    out.push({ text: node, path });
    return;
  }
  if (!node || typeof node !== 'object') return;
  for (const [key, value] of Object.entries(node)) {
    if (key === 'url' || key === 'mirrorUrl') continue;
    collectStrings(value, `${path}.${key}`, out);
  }
}

// Строковые и шаблонные литералы с кириллицей — то, что реально видит человек.
function literalsWithCyrillic(source) {
  const withoutComments = source
    .replace(/^\s*\/\/.*$/gm, '')
    .replace(/([^:'"`\\])\/\/[^'"`\n]*$/gm, '$1');
  const out = [];
  const re = /'((?:[^'\\\n]|\\.)*)'|"((?:[^"\\\n]|\\.)*)"|`((?:[^`\\]|\\.)*)`/g;
  let m;
  while ((m = re.exec(withoutComments)) !== null) {
    // Подстановки ${...} — это код, а не текст: их содержимое проверяется
    // отдельно (данные норм) либо является числом. Вырезаем.
    const text = (m[1] ?? m[2] ?? m[3] ?? '').replace(/\$\{[^{}]*\}/g, '');
    if (/[а-яё]/i.test(text)) out.push(text);
  }
  return out;
}

test('тест-страж: ни имён файлов, ни имён переменных в клиентских текстах', () => {
  const fromNorms = [];
  collectStrings(NORMS, 'NORMS', fromNorms);
  collectStrings(TEST_NORMS, 'TEST_NORMS', fromNorms);
  for (const { text, path } of fromNorms) assertNoLeak(text, path);

  for (const file of ['../forma-calc.js', '../forma.html']) {
    const source = readFileSync(new URL(file, import.meta.url), 'utf8');
    for (const text of literalsWithCyrillic(source)) assertNoLeak(text, file);
  }

  // Текст самой страницы вне скрипта — то, что человек читает рядом с полями
  const html = readFileSync(new URL('../forma.html', import.meta.url), 'utf8');
  const markup = html.replace(/<script[\s\S]*?<\/script>/g, '').replace(/<style[\s\S]*?<\/style>/g, '');
  for (const line of markup.replace(/<[^>]+>/g, ' ').split('\n')) {
    if (/[а-яё]/i.test(line)) assertNoLeak(line, 'разметка forma.html');
  }
});

test('у беговых таблиц есть возрастное покрытие, и вне него оценки нет', () => {
  // Раньше пятнадцатилетний молча получал коэффициент двадцатилетнего.
  assert.deepEqual(NORMS.running.ageCoverage, { min: 20, max: 80 });
  assert.equal(ageGrade('m', 15, 5, 1500), null);
  assert.equal(ageGrade('m', 85, 5, 1800), null);
  assert.equal(typeof ageGrade('m', 20, 5, 1500), 'number');
  assert.equal(typeof ageGrade('m', 80, 5, 2400), 'number');
});

test('формула NTNU не работает за границами применимости и не отдаёт оценку ниже шкалы', () => {
  const spec = NORMS.ntnuFormula;
  assert.deepEqual(spec.ageCoverage, { min: 20, max: 90 });

  // Возраст вне когорты HUNT
  assert.equal(fitnessAgeNTNU({ sex: 'm', age: 15, bmi: 22, restingHR: 60, trainingFreq: 2.5, trainingIntensity: 2, trainingDuration: 0.75 }), null);
  assert.equal(fitnessAgeNTNU({ sex: 'm', age: 95, bmi: 22, restingHR: 60, trainingFreq: 2.5, trainingIntensity: 2, trainingDuration: 0.75 }), null);

  // Пример из находок: возраст 79, индекс массы тела 45, пульс 95 — формула
  // отдавала около 8 мл/кг/мин, и это молча уходило в возраст тела
  const absurd = estimateVo2maxNTNU({ sex: 'm', age: 79, bmi: 45, restingHR: 95, trainingFreq: 0, trainingIntensity: 1, trainingDuration: 0.1 });
  assert.equal(absurd, null);
  assert.equal(fitnessAgeNTNU({ sex: 'm', age: 79, bmi: 45, restingHR: 95, trainingFreq: 0, trainingIntensity: 1, trainingDuration: 0.1 }), null);

  // Нижний предел взят из данных, а не с потолка: это самая низкая
  // опубликованная точка таблицы FRIEND для этого пола
  const lowestPublished = Math.min(...Object.values(NORMS.vo2max.m).map((row) => row.p5));
  assert.equal(spec.minPlausibleVo2max.m, lowestPublished);
  const lowestF = Math.min(...Object.values(NORMS.vo2max.f).map((row) => row.p5));
  assert.equal(spec.minPlausibleVo2max.f, lowestF);

  // Обычный случай считается как раньше
  assert.equal(typeof fitnessAgeNTNU({ sex: 'm', age: 38, bmi: 24.6, restingHR: 52, trainingFreq: 5, trainingIntensity: 3, trainingDuration: 1 }), 'number');
});

test('ошибка оценки формулы NTNU хранится отдельно для мужчин и женщин', () => {
  const see = NORMS.ntnuFormula.standardError;
  assert.equal(see.m, 5.70);
  assert.equal(see.f, 5.14);
});

// Тест-страж: знак ГТО нигде не приравнивается к перцентилю. Смотрит на ОБА
// файла и на разметку — раньше он видел только forma-calc.js и пропустил
// формулировки «серебро означает перцентиль 50 и выше» и «бронза означает
// нижнюю четверть».
test('тест-страж: знак ГТО нигде не приравнивается к доле населения', () => {
  const badge = /(золот|серебр|бронз)/i;
  const share = /(перцентил\w*\s*\d|\bp\d{1,2}\b|нижн\w+\s+четверт|медиан|\d{1,3}\s*%\s*(людей|населен))/i;

  for (const file of ['../forma-calc.js', '../forma-norms.js', '../forma.html']) {
    const source = readFileSync(new URL(file, import.meta.url), 'utf8');
    source.split('\n').forEach((line, i) => {
      if (badge.test(line) && share.test(line)) {
        assert.fail(`${file}, строка ${i + 1}: знак ГТО стоит рядом с долей населения — «${line.trim()}»`);
      }
    });
  }

  // И в самом расчёте: знак сравнивается со знаком, а не с числом
  const calc = readFileSync(new URL('../forma-calc.js', import.meta.url), 'utf8');
  assert.ok(!/badgeOrdinalPosition/.test(calc));
  assert.ok(!/BADGE_ORDER\[[^\]]+\]\s*[/*]\s*\d/.test(calc), 'знак ГТО пересчитывается в число');
});

test('зачёт блока: перцентиль по медиане, знак ГТО — по самому знаку', () => {
  // Серебро и золото — зачёт, бронза и ниже — нет. Никакого перцентиля.
  assert.equal(formScore([{ key: 'pullups', block: 'strength', badge: 'серебро', informational: false }]).byBlock.strength, 'green');
  assert.equal(formScore([{ key: 'pullups', block: 'strength', badge: 'бронза', informational: false }]).byBlock.strength, 'red');
  // Знаменатель счёта — посчитанные блоки, а не всегда шесть
  const s = formScore([
    { key: 'vo2max', block: 'endurance', percentile: 80, informational: false },
    { key: 'pushups', block: 'strength', percentile: 75, informational: false },
  ]);
  assert.equal(s.counted, 2);
  assert.equal(s.green, 2);
});

test('первоисточник формулы NTNU показан основным, подтверждающая работа — рядом', () => {
  const spec = NORMS.ntnuFormula;
  assert.match(spec.source.title, /HUNT Study/);
  assert.match(spec.source.authors, /^Nes B\.M\./);
  assert.equal(spec.source.year, 2011);
  assert.ok(spec.confirmedBy.url && spec.confirmedBy.year === 2019);
});

test('протокол отжиманий лежит в данных: у женщин он с колен', () => {
  const p = TEST_NORMS.pushups.protocol;
  assert.match(p.f, /колен/);
  assert.ok(p.m.length > 0);
});

test('мёртвых данных в нормах не осталось', () => {
  assert.equal(NORMS.sleepRegularity.sriBands, undefined);
  assert.equal(TEST_NORMS.plank.context, undefined);
  assert.equal(TEST_NORMS.onelegstand.context60plus, undefined);
});

test('ссылки ведут туда, куда обещает заголовок', () => {
  // ВОЗ: каноническая страница основной, зеркало запасным полем
  assert.match(NORMS.bmi.source.url, /iris\.who\.int/);
  assert.ok(NORMS.bmi.source.mirrorUrl);
  // Стойка на одной ноге — DOI, а не поисковая база
  assert.match(TEST_NORMS.onelegstand.source.url, /^https:\/\/doi\.org\//);
  assert.match(NORMS.hazards.onelegstand.source.url, /^https:\/\/doi\.org\//);
  // Талия к росту: заголовок и адрес — от одной работы, вторая рядом
  assert.match(NORMS.waistToHeight.source.url, /waisttoheight-ratio-as-a-screening-tool/);
  assert.match(NORMS.waistToHeight.source.title, /^A systematic review of waist-to-height ratio/);
  assert.ok(NORMS.waistToHeight.alsoSee.title !== NORMS.waistToHeight.source.title);
});
