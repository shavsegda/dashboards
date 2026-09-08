import { test } from 'node:test';
import assert from 'node:assert/strict';
import { percentile, levelFromPercentile, ageGrade, ageGradeClass } from '../forma-calc.js';
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
