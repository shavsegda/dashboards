import { FIELD_SCHEMA, SCREEN_SCHEMA } from './ai-schema.mjs';

// Полный контекст собирается только из записанного разговора. Предложения ИИ сюда не попадают.
const MAX_ITEMS = 200;
const MAX_ITEM_TEXT = 12000;
const MAX_CONTEXT_TEXT = 64000;
const own = (value, key) => Object.prototype.hasOwnProperty.call(value, key);
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value)
  && (Object.getPrototypeOf(value) === Object.prototype || Object.getPrototypeOf(value) === null);
const nonempty = value => value.trim().length > 0;

function checkedText(value, label, maximum = MAX_ITEM_TEXT, required = false) {
  if (typeof value !== 'string' || value.length > maximum || (required && !nonempty(value))) throw new Error(`Некорректная запись «${label}».`);
  return value;
}
function checkedScreen(id) {
  if (typeof id !== 'string' || !own(SCREEN_SCHEMA, id)) throw new Error('Не найден экран для подготовки подсказки.');
  return SCREEN_SCHEMA[id];
}
function checkedSession(session) {
  if (!object(session) || !object(session.answers)) throw new Error('Для помощника нужна запись текущей встречи.');
  checkedText(session.id, 'Идентификатор встречи', 200, true);
  return session;
}
function checkedRequestId(id) {
  if (typeof id !== 'string' || !/^[A-Za-z0-9_-]{1,80}$/.test(id)) throw new Error('Некорректный номер запроса помощника.');
  return id;
}
function checkedContext(raw) {
  if (!Array.isArray(raw) || raw.length > MAX_ITEMS) throw new Error('Для помощника допустимо не более 200 записей разговора.');
  const seen = new Set(); let length = 0;
  const result = raw.map(item => {
    if (!object(item) || typeof item.key !== 'string' || !(own(FIELD_SCHEMA, item.key) || /^(option|qa):\d+$/.test(item.key)) || seen.has(item.key)) throw new Error('В контексте повторяется или не распознана запись.');
    seen.add(item.key);
    const value = checkedText(item.text, 'Запись разговора', MAX_ITEM_TEXT, true);
    length += value.length;
    return { key: item.key, text: value };
  });
  if (length > MAX_CONTEXT_TEXT) throw new Error('Разговор превышает 64 000 знаков. Записи сохранены; помощник не получил сокращённую версию.');
  return result;
}

export function collectCardContext(session) {
  checkedSession(session);
  const context = [];
  for (const [key, schema] of Object.entries(FIELD_SCHEMA)) {
    if (!own(session.answers, key)) continue;
    const value = checkedText(session.answers[key], schema.label);
    if (!nonempty(value)) continue;
    if (schema.type === 'choice') {
      const option = schema.options?.find(([id]) => id === value);
      if (!option) throw new Error(`Не распознан выбор в поле «${schema.label}».`);
      context.push({ key, text: option[1] });
    } else context.push({ key, text: value });
  }
  if (session.helpOptions !== undefined) {
    if (!Array.isArray(session.helpOptions)) throw new Error('Не распознан список способов помощи.');
    session.helpOptions.forEach((option, index) => {
      if (!object(option)) throw new Error('Не распознан вариант помощи.');
      const parts = [['name', 'Вариант'], ['benefit', 'Ожидаемая польза'], ['effort', 'Участие человека'], ['unknown', 'Что неизвестно']]
        .map(([key, label]) => [label, checkedText(option[key], label)]);
      if (parts.some(([, value]) => nonempty(value))) context.push({ key: `option:${index}`, text: parts.filter(([, value]) => nonempty(value)).map(([label, value]) => `${label}: ${value}`).join('\n') });
    });
  }
  if (session.qaEntries !== undefined) {
    if (!Array.isArray(session.qaEntries)) throw new Error('Не распознан список уточнений разговора.');
    session.qaEntries.forEach((entry, index) => {
      if (!object(entry)) throw new Error('Не распознана запись уточняющего вопроса.');
      const answer = checkedText(entry.answer, 'Ответ на уточнение');
      if (!nonempty(answer)) return;
      const question = checkedText(entry.question, 'Уточняющий вопрос', 2000, true);
      context.push({ key: `qa:${index}`, text: `Вопрос: ${question}\nОтвет: ${answer}` });
    });
  }
  // Бюджет сети проверяем при построении запроса, чтобы большой разговор не мешал обычному сохранению.
  return context;
}

// Синхронный SHA-256 позволяет проверить актуальность непосредственно перед нажатием «Записать».
function sha256(value) {
  const constants = [0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2];
  const state = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19];
  const bytes = new TextEncoder().encode(value);
  const padded = new Uint8Array(Math.ceil((bytes.length + 9) / 64) * 64);
  padded.set(bytes); padded[bytes.length] = 0x80;
  const view = new DataView(padded.buffer);
  view.setUint32(padded.length - 8, Math.floor(bytes.length * 8 / 2 ** 32));
  view.setUint32(padded.length - 4, bytes.length * 8 >>> 0);
  const words = new Uint32Array(64);
  const rotate = (word, bits) => (word >>> bits) | (word << (32 - bits));
  for (let offset = 0; offset < padded.length; offset += 64) {
    for (let i = 0; i < 16; i++) words[i] = view.getUint32(offset + i * 4);
    for (let i = 16; i < 64; i++) {
      const a = words[i - 15], b = words[i - 2];
      words[i] = (words[i - 16] + (rotate(a, 7) ^ rotate(a, 18) ^ (a >>> 3)) + words[i - 7] + (rotate(b, 17) ^ rotate(b, 19) ^ (b >>> 10))) >>> 0;
    }
    let [a, b, c, d, e, f, g, h] = state;
    for (let i = 0; i < 64; i++) {
      const first = (h + (rotate(e, 6) ^ rotate(e, 11) ^ rotate(e, 25)) + ((e & f) ^ (~e & g)) + constants[i] + words[i]) >>> 0;
      const second = ((rotate(a, 2) ^ rotate(a, 13) ^ rotate(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))) >>> 0;
      h = g; g = f; f = e; e = (d + first) >>> 0; d = c; c = b; b = a; a = (first + second) >>> 0;
    }
    [a, b, c, d, e, f, g, h].forEach((word, i) => { state[i] = (state[i] + word) >>> 0; });
  }
  return state.map(word => word.toString(16).padStart(8, '0')).join('');
}

const fingerprintOf = (sessionId, context) => `sha256:${sha256(JSON.stringify({ sessionId, context }))}`;
export function cardFingerprint(session) {
  return fingerprintOf(checkedSession(session).id, collectCardContext(session));
}
function checkedFingerprint(value) {
  if (typeof value !== 'string' || !/^sha256:[a-f0-9]{64}$/.test(value)) throw new Error('Не распознан отпечаток разговора.');
  return value;
}
function checkedDate(value) {
  checkedText(value, 'Время подготовки карточки', 50, true);
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})$/.test(value) || !Number.isFinite(Date.parse(value))) throw new Error('Некорректное время подготовки карточки.');
  const day = new Date(`${value.slice(0, 10)}T12:00:00Z`);
  if (!Number.isFinite(day.getTime()) || day.toISOString().slice(0, 10) !== value.slice(0, 10)) throw new Error('Дата подготовки карточки не существует.');
  return value;
}

export function buildCardRequest(session, screenId, { requestId } = {}) {
  checkedScreen(screenId);
  const context = checkedContext(collectCardContext(session));
  if (!context.length) throw new Error('Сначала запишите рассказ или несколько сведений о человеке. После этого помощник сможет учесть разговор.');
  return { request: { version: 2, requestId: checkedRequestId(requestId), screenId, context }, contextFingerprint: cardFingerprint(session) };
}

function checkedBasis(raw) {
  if (!Array.isArray(raw) || raw.length > 6) throw new Error('В основании карточки должно быть не более шести цитат.');
  const seen = new Set();
  return raw.map(item => {
    if (!object(item) || typeof item.key !== 'string' || !(own(FIELD_SCHEMA, item.key) || /^(option|qa):\d+$/.test(item.key))) throw new Error('Не распознан источник цитаты.');
    const quote = checkedText(item.quote, 'Цитата разговора', 400, true);
    const identity = JSON.stringify([item.key, quote]);
    if (seen.has(identity)) throw new Error('Одна цитата повторяется в основаниях.');
    seen.add(identity); return { key: item.key, quote };
  });
}
function checkedDraft(raw, key, screen) {
  const field = FIELD_SCHEMA[key];
  if (!field || field.type !== 'text' || field.draftable !== true || key.startsWith('intake_') || !screen.fields.some(item => item.key === key)) throw new Error('Помощник предложил запись для неподходящего поля этого экрана.');
  if (!object(raw)) throw new Error('Не распознан черновик записи.');
  const text = checkedText(raw.text, 'Предложение записи', 900);
  const basis = checkedBasis(raw.basis);
  const question = raw.question === null ? null : checkedText(raw.question, 'Уточняющий вопрос', 500, true);
  if (nonempty(text) && (!basis.length || question !== null)) throw new Error('У предложения записи должны быть цитаты и не должно быть дополнительного вопроса.');
  if (!nonempty(text) && (basis.length || question === null)) throw new Error('Вместо необоснованного ответа нужен один уточняющий вопрос.');
  return { text, basis, question };
}
function verifyBasis(basis, context) {
  const sources = new Map(context.map(item => [item.key, item.text]));
  for (const item of basis) if (!sources.has(item.key) || !sources.get(item.key).includes(item.quote)) throw new Error('Цитата не найдена дословно в записанном разговоре.');
}
function checkedCard(raw, screenId) {
  const screen = checkedScreen(screenId);
  if (!object(raw) || raw.screenId !== screenId || !object(raw.drafts)) throw new Error('Не распознана карточка помощника.');
  const question = checkedText(raw.question, 'Вопрос карточки', 500, true);
  const explanation = checkedText(raw.explanation, 'Пояснение карточки', 700);
  if (!Array.isArray(raw.hints) || raw.hints.length > 2) throw new Error('У карточки должно быть не более двух подсказок.');
  const hints = raw.hints.map(hint => checkedText(hint, 'Подсказка карточки', 240, true));
  const basis = checkedBasis(raw.basis);
  const drafts = {};
  for (const [key, draft] of Object.entries(raw.drafts)) {
    const content = checkedDraft(draft, key, screen);
    if (!['suggested', 'accepted', 'rejected'].includes(draft.status) || (draft.status === 'accepted' && !nonempty(content.text))) throw new Error('Не распознан статус предложения записи.');
    drafts[key] = { ...content, status: draft.status };
  }
  return { screenId, question, explanation, hints, basis, drafts, createdAt: checkedDate(raw.createdAt), contextFingerprint: checkedFingerprint(raw.contextFingerprint) };
}

export function normaliseAiCards(raw = {}) {
  if (!object(raw)) throw new Error('Карточки помощника должны быть отдельными записями по экранам.');
  return Object.fromEntries(Object.entries(raw).map(([id, card]) => [id, checkedCard(card, id)]));
}

export function validateCardResponse(response, { session, request, contextFingerprint, now = new Date() }) {
  checkedSession(session);
  if (!object(request) || request.version !== 2) throw new Error('Не распознан запрос карточки.');
  const screen = checkedScreen(request.screenId);
  checkedRequestId(request.requestId);
  const requestContext = checkedContext(request.context);
  if (checkedFingerprint(contextFingerprint) !== cardFingerprint(session) || JSON.stringify(requestContext) !== JSON.stringify(collectCardContext(session))) throw new Error('Записи встречи изменились. Нужна новая карточка.');
  if (!object(response) || response.version !== 2 || response.requestId !== request.requestId || response.screenId !== request.screenId) throw new Error('Карточка относится к другому запросу или экрану.');
  if (!Array.isArray(response.drafts) || response.drafts.length > screen.fields.length) throw new Error('Не распознан список предложений записи.');
  if (!(now instanceof Date) || !Number.isFinite(now.getTime())) throw new Error('Не удалось определить время подготовки карточки.');
  const drafts = {};
  for (const raw of response.drafts) {
    if (!object(raw) || typeof raw.key !== 'string' || own(drafts, raw.key)) throw new Error('В карточке повторяется или не распознан черновик.');
    const content = checkedDraft(raw, raw.key, screen);
    if (nonempty(checkedText(session.answers[raw.key] ?? '', 'Текущий ответ'))) throw new Error('В поле уже есть запись. Помощник не может её заменить.');
    verifyBasis(content.basis, requestContext);
    const numbers = value => value.match(/\d+(?:[.,]\d+)*/g) || [];
    const cited = new Set(numbers(content.basis.map(item => item.quote).join(' ')));
    if (numbers(content.text).some(number => !cited.has(number))) throw new Error('В предложении записи появились числа, которых нет в его основаниях.');
    drafts[raw.key] = { ...content, status: 'suggested' };
  }
  const card = checkedCard({ ...response, drafts, createdAt: now.toISOString(), contextFingerprint }, request.screenId);
  verifyBasis(card.basis, requestContext);
  return card;
}

function cardMatches(card, fingerprint, context) {
  if (!card || card.contextFingerprint !== fingerprint) return false;
  try {
    verifyBasis(card.basis, context);
    for (const draft of Object.values(card.drafts)) verifyBasis(draft.basis, context);
  } catch { return false; }
  return true;
}
export function isCardCurrent(session, screenId) {
  checkedScreen(screenId);
  const card = normaliseAiCards(session.aiCards || {})[screenId];
  if (!card) return false;
  const context = collectCardContext(session);
  return cardMatches(card, fingerprintOf(session.id, context), context);
}
function copySession(session) {
  checkedSession(session);
  const copy = typeof structuredClone === 'function' ? structuredClone(session) : JSON.parse(JSON.stringify(session));
  copy.aiCards = normaliseAiCards(session.aiCards || {});
  return copy;
}

export function invalidateAiCards(session) {
  const copy = copySession(session);
  // Один расчёт на изменение ответа: число сохранённых карточек не умножает стоимость хеширования.
  const context = collectCardContext(copy);
  const fingerprint = fingerprintOf(copy.id, context);
  for (const [screenId, card] of Object.entries(copy.aiCards)) {
    if (cardMatches(card, fingerprint, context)) continue;
    // Принятое происхождение и явный отказ сохраняются; неподтверждённые старые варианты убираем.
    card.drafts = Object.fromEntries(Object.entries(card.drafts).filter(([, draft]) => draft.status !== 'suggested'));
    if (!Object.keys(card.drafts).length) delete copy.aiCards[screenId];
  }
  return copy;
}

export function acceptCardDraft(session, screenId, key) {
  const screen = checkedScreen(screenId);
  if (!isCardCurrent(session, screenId)) throw new Error('Карточка устарела. Подготовьте новую по текущему разговору.');
  if (nonempty(checkedText(session.answers[key] ?? '', 'Текущий ответ'))) throw new Error('В поле уже есть запись. Она сохранена без изменений.');
  const copy = copySession(session);
  const draft = copy.aiCards[screenId]?.drafts[key];
  if (!draft || draft.status !== 'suggested') throw new Error('Предложение записи больше недоступно.');
  checkedDraft(draft, key, screen);
  if (!nonempty(draft.text)) throw new Error('Это уточняющий вопрос, а не готовый ответ человека.');
  copy.answers[key] = draft.text;
  draft.status = 'accepted';
  return invalidateAiCards(copy);
}

export function rejectCardDraft(session, screenId, key) {
  checkedScreen(screenId);
  const copy = copySession(session);
  if (copy.aiCards[screenId]?.drafts[key]?.status === 'suggested') copy.aiCards[screenId].drafts[key].status = 'rejected';
  return copy;
}
