import { test } from 'node:test';
import assert from 'node:assert/strict';
import { percentile, levelFromPercentile, ageGrade, ageGradeClass, vo2maxTable, bodyAgeFromVo2max, lifeExpectancy, fitnessAgeNTNU, bodyComposition, recovery } from '../forma-calc.js';
import { NORMS } from '../forma-norms.js';

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
