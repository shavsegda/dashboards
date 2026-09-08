import { test } from 'node:test';
import assert from 'node:assert/strict';
import { percentile, levelFromPercentile } from '../forma-calc.js';

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
