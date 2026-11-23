import { GUIDED_FLOW } from './guided-flow.mjs';

// Модуль не обращается к сети и не меняет ответы без явного acceptDraft.
// API: buildDraftRequest(session, { targets, requestId }) -> { request, contextFingerprint };
// validateDraftResponse(response, { session, request, contextFingerprint, now }) -> map aiDrafts.
// acceptDraft/rejectDraft/invalidateStaleDrafts возвращают независимую копию session.
// Привязку принятого ответа к действительно показанному вопросу записывает вызывающий UI.
const ENUM_FIELDS = new Set(['task_type', 'question_status', 'clarification_status']);
// Явный список согласован с сервером. Новые поля, включая intake_*, не попадают в ИИ автоматически.
const approvedFields = Object.freeze(['why_now', 'today', 'episode', 'trigger_event', 'change', 'success_criteria', 'considered_method', 'desired_effect', 'tried', 'tried_result', 'constraints', 'preserve', 'decision_owner', 'unacceptable_costs', 'decision_deadline', 'deadline_source', 'delay_consequences', 'shared_question', 'question_change_reason', 'unknown_priority', 'participant_question']);
const fieldEntries = GUIDED_FLOW.filter(step => step.phase === 'question')
  .flatMap(step => [...(step.fields || []), ...(step.optional || [])])
  .filter(field => approvedFields.includes(field.key) && !ENUM_FIELDS.has(field.key) && !field.key.startsWith('intake_'));
export const AI_DRAFT_FIELDS = Object.freeze(approvedFields.filter(key => fieldEntries.some(field => field.key === key)));
export const AI_DRAFT_LABELS = Object.freeze(Object.fromEntries(fieldEntries.map(field => [field.key, field.label])));
const allowed = new Set(AI_DRAFT_FIELDS);
const MAX_TEXT = 12000;
const MAX_QUESTION = 2000;
const MAX_TARGET_QUESTION = 500;
const MAX_CONTEXT_CHARS = 24000;
const MAX_BASIS = 8;
const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
const objectLike = value => value !== null && typeof value === 'object' && !Array.isArray(value)
  && (Object.getPrototypeOf(value) === Object.prototype || Object.getPrototypeOf(value) === null);
const hasText = value => value.trim().length > 0;

function text(value, label, limit = MAX_TEXT, required = false) {
  if (typeof value !== 'string') throw new Error(`Поле «${label}» должно содержать текст.`);
  if (value.length > limit) throw new Error(`Поле «${label}» превышает допустимую длину ${limit} знаков.`);
  if (required && !hasText(value)) throw new Error(`Поле «${label}» не должно быть пустым.`);
  return value;
}

function fieldKey(key) {
  if (typeof key !== 'string' || !allowed.has(key)) throw new Error('Черновик относится к неподдерживаемому полю первой карточки.');
  return key;
}

function requestId(value) {
  text(value, 'Номер запроса', 80, true);
  if (!/^[A-Za-z0-9_-]+$/.test(value)) throw new Error('Номер запроса может содержать только латинские буквы, цифры, дефис и подчёркивание.');
  return value;
}

function answersOf(session) {
  if (!objectLike(session) || !objectLike(session.answers)) throw new Error('Для черновика нужна запись встречи с ответами.');
  return session.answers;
}

function contextAnswers(session) {
  const answers = answersOf(session);
  return AI_DRAFT_FIELDS.flatMap(key => {
    const value = own(answers, key) ? text(answers[key], AI_DRAFT_LABELS[key]) : '';
    return hasText(value) ? [{ key, text: value }] : [];
  });
}

// SHA-256 нужен для обнаружения изменений, а не для подписи или авторизации запроса.
// Синхронный расчёт позволяет проверять актуальность прямо перед принятием черновика.
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

export function contextFingerprint(session) {
  return `sha256:${sha256(JSON.stringify(contextAnswers(session)))}`;
}

function checkedFingerprint(value) {
  if (typeof value !== 'string' || !/^sha256:[a-f0-9]{64}$/.test(value)) throw new Error('У черновика отсутствует корректный отпечаток исходных ответов.');
  return value;
}

function timestamp(value) {
  text(value, 'Время создания черновика', 50, true);
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})$/.test(value) || !Number.isFinite(Date.parse(value))) throw new Error('Время создания черновика указано неверно.');
  const day = new Date(`${value.slice(0, 10)}T12:00:00Z`);
  if (!Number.isFinite(day.getTime()) || day.toISOString().slice(0, 10) !== value.slice(0, 10)) throw new Error('Дата создания черновика не существует.');
  return value;
}

function basisList(raw) {
  if (!Array.isArray(raw) || raw.length > MAX_BASIS) throw new Error('У черновика должен быть список не более восьми оснований.');
  const seen = new Set();
  return raw.map(item => {
    if (!objectLike(item)) throw new Error('Основание черновика должно содержать поле и дословную цитату.');
    const key = fieldKey(item.key);
    const quote = text(item.quote, 'Цитата из ответа', 2000, true);
    const identity = JSON.stringify([key, quote]);
    if (seen.has(identity)) throw new Error('В основаниях черновика повторяется одна и та же цитата.');
    seen.add(identity);
    return { key, quote };
  });
}

function draftContent(raw) {
  if (!objectLike(raw)) throw new Error('Черновик должен быть отдельной текстовой записью.');
  const draftText = text(raw.text, 'Текст черновика');
  const question = raw.question === null ? null : text(raw.question, 'Предложение уточняющего вопроса', MAX_QUESTION, true);
  const basis = basisList(raw.basis);
  if (!hasText(draftText) && !question) throw new Error('Пустой черновик должен содержать предложение уточняющего вопроса.');
  if (hasText(draftText) && !basis.length) throw new Error('Текстовый черновик не имеет оснований в записанных ответах.');
  return { text: draftText, basis, question };
}

export function normaliseAiDrafts(raw = {}) {
  if (!objectLike(raw)) throw new Error('Черновики помощника должны быть объектом с записями по полям.');
  const result = {};
  for (const [key, record] of Object.entries(raw)) {
    fieldKey(key);
    const content = draftContent(record);
    if (!['suggested', 'accepted', 'rejected'].includes(record.status)) throw new Error('У черновика указан неизвестный статус.');
    if (record.status === 'accepted' && !hasText(content.text)) throw new Error('Уточняющий вопрос нельзя считать принятым ответом участника.');
    result[key] = { ...content, status: record.status, createdAt: timestamp(record.createdAt), contextFingerprint: checkedFingerprint(record.contextFingerprint) };
  }
  return result;
}

function targetsList(raw, session) {
  if (!Array.isArray(raw) || !raw.length || raw.length > 3) throw new Error('Для одного запроса выберите от одного до трёх пустых полей первой карточки.');
  const answers = answersOf(session);
  const seen = new Set();
  return raw.map(item => {
    if (!objectLike(item)) throw new Error('Цель запроса должна содержать поле и вопрос.');
    const key = fieldKey(item.key);
    if (seen.has(key)) throw new Error('В запросе повторяется поле для черновика.');
    seen.add(key);
    if (own(answers, key) && hasText(text(answers[key], AI_DRAFT_LABELS[key]))) throw new Error('В этом поле уже есть ответ. Черновик не может его перезаписать.');
    return { key, question: text(item.question, 'Вопрос для будущего ответа', MAX_TARGET_QUESTION, true) };
  });
}

export function buildDraftRequest(session, { targets, requestId: id }) {
  const request = { answers: contextAnswers(session), targets: targetsList(targets, session), requestId: requestId(id) };
  if (!request.answers.length) throw new Error('Сначала запишите хотя бы один ответ первой карточки. Сведения начальной формы не используются для черновиков.');
  const contextLength = request.answers.reduce((sum, answer) => sum + answer.text.length, 0)
    + request.targets.reduce((sum, target) => sum + target.question.length, 0);
  if (contextLength > MAX_CONTEXT_CHARS) throw new Error('Записанный контекст и вопросы превышают 24 000 знаков. Черновики не запрошены; ответы сохранены без сокращения.');
  return { request, contextFingerprint: contextFingerprint(session) };
}

function verifyBasis(basis, answers) {
  for (const item of basis) {
    if (!own(answers, item.key) || typeof answers[item.key] !== 'string' || !answers[item.key].includes(item.quote)) throw new Error('Цитата-основание не найдена дословно в указанном записанном ответе.');
  }
}

export function validateDraftResponse(response, { session, request, contextFingerprint: requestedFingerprint, now = new Date() }) {
  if (!objectLike(request)) throw new Error('Для проверки черновиков нужен исходный запрос.');
  const id = requestId(request.requestId);
  if (!objectLike(response) || response.requestId !== id) throw new Error('Черновики относятся к другому запросу.');
  if (checkedFingerprint(requestedFingerprint) !== contextFingerprint(session)) throw new Error('Ответы изменились, пока готовились черновики. Нужен новый запрос.');
  if (JSON.stringify(request.answers) !== JSON.stringify(contextAnswers(session))) throw new Error('Исходные ответы запроса не соответствуют текущему контексту.');
  const targets = new Set(targetsList(request.targets, session).map(target => target.key));
  if (!Array.isArray(response.drafts) || response.drafts.length > 3) throw new Error('Ответ помощника должен содержать не более трёх черновиков.');
  if (!(now instanceof Date) || !Number.isFinite(now.getTime())) throw new Error('Не удалось определить время создания черновика.');
  const sourceAnswers = Object.fromEntries(request.answers.map(item => [item.key, item.text]));
  const result = {};
  for (const raw of response.drafts) {
    if (!objectLike(raw)) throw new Error('Некорректная запись черновика в ответе помощника.');
    const key = fieldKey(raw.key);
    if (!targets.has(key)) throw new Error('Помощник предложил черновик для незапрошенного поля.');
    if (own(result, key)) throw new Error('Помощник прислал несколько черновиков для одного поля.');
    const content = draftContent(raw);
    verifyBasis(content.basis, sourceAnswers);
    verifyBasis(content.basis, answersOf(session));
    result[key] = { ...content, status: 'suggested', createdAt: now.toISOString(), contextFingerprint: requestedFingerprint };
  }
  return result;
}

function copySession(session) {
  answersOf(session);
  const copy = typeof structuredClone === 'function' ? structuredClone(session) : JSON.parse(JSON.stringify(session));
  copy.aiDrafts = normaliseAiDrafts(session.aiDrafts || {});
  return copy;
}

export function isDraftCurrent(session, key) {
  fieldKey(key);
  const draft = normaliseAiDrafts(session.aiDrafts || {})[key];
  if (!draft || draft.status !== 'suggested') return false;
  const answers = answersOf(session);
  if (own(answers, key) && hasText(text(answers[key], AI_DRAFT_LABELS[key]))) return false;
  if (draft.contextFingerprint !== contextFingerprint(session)) return false;
  try { verifyBasis(draft.basis, answers); } catch { return false; }
  return true;
}

export function invalidateStaleDrafts(session) {
  const copy = copySession(session);
  for (const [key, draft] of Object.entries(copy.aiDrafts)) {
    // Устаревший черновик удаляем, а не приписываем пользователю отказ от него.
    if (draft.status === 'suggested' && !isDraftCurrent(copy, key)) delete copy.aiDrafts[key];
  }
  return copy;
}

export function acceptDraft(session, key) {
  fieldKey(key);
  const answers = answersOf(session);
  if (own(answers, key) && hasText(text(answers[key], AI_DRAFT_LABELS[key]))) throw new Error('В поле уже есть ответ. Он сохранён без изменений.');
  const copy = copySession(session);
  const draft = copy.aiDrafts[key];
  if (!draft || !isDraftCurrent(copy, key)) throw new Error('Черновик устарел или больше недоступен. Подготовьте новый.');
  if (!hasText(draft.text)) throw new Error('Это предложение уточняющего вопроса, а не готовый ответ участника.');
  copy.answers[key] = draft.text;
  draft.status = 'accepted';
  // Принятый ответ изменил контекст: другие ожидающие черновики нужно проверить заново.
  return invalidateStaleDrafts(copy);
}

export function rejectDraft(session, key) {
  fieldKey(key);
  const copy = copySession(session);
  if (copy.aiDrafts[key]?.status === 'suggested') copy.aiDrafts[key].status = 'rejected';
  return copy;
}
