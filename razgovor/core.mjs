import { normaliseAiDrafts } from './ai-drafts.mjs';
// Общие данные и правила сессии не зависят от интерфейса страницы.
export const FIELD_LABELS = Object.freeze({
  why_now: 'Рассказ участника и повод встречи',
  today: 'Желаемый результат сегодняшнего разговора',
  episode: 'Конкретная ситуация или эпизод',
  change: 'Желаемое изменение',
  tried: 'Что уже пробовали',
  tried_result: 'Что получилось после предыдущих попыток',
  constraints: 'Существенные условия и то, что важно сохранить',
  help_expected: 'Ожидаемая помощь',
  questions: 'Вопросы о специалисте и его работе',
  shared_question: 'Рабочая формулировка вопроса',
  question_status: 'Статус формулировки вопроса',
  proposal_result: 'Предлагаемый результат помощи',
  proposal_method: 'Предлагаемый способ работы',
  proposal_client: 'Предлагаемое участие клиента',
  proposal_limits: 'Предлагаемые границы помощи',
  proposal_check: 'Предлагаемая проверка пользы',
  fit_feedback: 'Отклик на предложение',
  fit_status: 'Соответствие предложения задаче',
  next_choice: 'Выбранное продолжение',
  next_step: 'Следующий шаг',
  next_when: 'Срок или условие следующего шага',
  next_check: 'Как проверить результат следующего шага',
  terms_scope: 'Обсуждаемый объём работы',
  terms_schedule: 'Обсуждаемые сроки и ритм',
  terms_price: 'Обсуждаемая цена',
  terms_payment: 'Обсуждаемый порядок оплаты',
  terms_review: 'Обсуждаемая проверка пользы работы',
  terms_change: 'Обсуждаемые условия пересмотра или завершения',
  agreement_status: 'Статус договорённости',
  hypothesis_basis: 'Основание предположения ведущего',
  hypothesis_text: 'Предположение ведущего',
  hypothesis_reply: 'Отклик участника на предположение',
  advice_basis: 'Основание предварительного мнения или совета',
  advice_text: 'Предварительное мнение или совет ведущего',
  advice_limits: 'Ограничения предварительного мнения или совета',
  advice_reply: 'Отклик участника на мнение или совет',
  process_feedback: 'Обратная связь о ходе разговора',
  process_adjustment: 'Изменение хода разговора',
  known_info: 'Что известно по словам участника и из названных источников',
  interpretation: 'Текущее понимание ситуации — версия',
  unknown_info: 'Что пока неизвестно',
  unknown_priority: 'Какое неизвестное существенно для следующего шага',
  success_criteria: 'Предварительные критерии подходящего результата',
  unacceptable_costs: 'Какая цена изменений неприемлема',
  stakeholders: 'Кого затрагивает решение',
  stakeholder_known: 'Что о позициях участников известно со слов и из источников',
  stakeholder_assumed: 'Что о позициях участников пока предполагается',
  alternative_framings: 'Другие возможные формулировки задачи',
  distinguishing_info: 'Что поможет различить возможные понимания задачи',
  proposal_basis: 'На какие сведения опирается предложение помощи',
  proposal_assumption: 'При каких предположениях предложенная помощь может быть полезна',
  proposal_uncertainty: 'Что в предложении помощи ещё предстоит проверить',
  today_outcome: 'Что участник отмечает как результат сегодняшнего разговора',
  remaining_check: 'Что ещё предстоит проверить на опыте',
  question_change_reason: 'Основание изменения рабочей формулировки',
  task_type: 'Какой вопрос сейчас актуален',
  task_type_details: 'Уточнение вида задачи своими словами',
  trigger_event: 'Событие, после которого возник вопрос',
  preserve: 'Что пока сохраняется',
  decision_owner: 'Кто вправе принимать какие решения',
  decision_deadline: 'Реальный срок решения или условие возвращения к вопросу',
  deadline_source: 'Откуда известен срок решения',
  delay_consequences: 'Последствия отсрочки или сохранения положения',
  desired_effect: 'Желаемый эффект, ради которого рассматривается способ',
  considered_method: 'Уже рассматриваемый способ',
  participant_question: 'Как участник формулирует свой вопрос',
  clarification_status: 'Состояние прояснения текущего вопроса',
  learning_choice: 'Выбор учебной работы',
  learn_own_attempt: 'Учебная попытка на собственной ситуации',
  learn_own_help: 'Помощь при попытке на собственной ситуации',
  learn_own_feedback: 'Обратная связь по попытке на собственной ситуации',
  learn_case_question: 'Вопрос решения в новом учебном случае',
  learn_case_facts: 'События и объяснения в новом учебном случае',
  learn_case_change: 'Желаемое изменение и способ в новом учебном случае',
  learn_case_limits: 'Границы и неизвестное в новом учебном случае',
  learn_feedback: 'Конкретная обратная связь по учебной попытке',
  learn_transfer_action: 'Где и как попробует применить способ',
  learn_transfer_when: 'Когда попробует применить способ',
  learn_transfer_check: 'По чему проверим самостоятельное применение',
  learn_open: 'Что в освоении способа остаётся непроверенным',
  learn_question_level: 'Наблюдение: формулирование вопроса',
  learn_question_evidence: 'Свидетельство формулирования вопроса в этой попытке',
  learn_goal_method_level: 'Наблюдение: различение цели и способа',
  learn_goal_method_evidence: 'Свидетельство различения цели и способа в этой попытке',
  learn_event_level: 'Наблюдение: различение события и объяснения',
  learn_event_evidence: 'Свидетельство различения события и объяснения в этой попытке',
  learn_boundary_level: 'Наблюдение: определение границ решения',
  learn_boundary_evidence: 'Свидетельство определения границ в этой попытке',
  learn_unknown_level: 'Наблюдение: определение существенного неизвестного',
  learn_unknown_evidence: 'Свидетельство определения неизвестного в этой попытке',
  help_role: 'Какой вклад ведущего рассматриваем',
  helper_experience: 'Какие знания и опыт ведущего относятся к задаче',
  helper_fit_reason: 'На чём основана оценка ведущего о подходящей помощи',
  helper_fit_status: 'Предварительная оценка соответствия ведущим',
  help_preferences: 'Что участнику важно при выборе помощи',
  help_informed_preference: 'Предпочтение участника после обсуждения вариантов и его основания',
  help_use_conditions: 'Какие условия позволят воспользоваться помощью',
  agreement_stage_task: 'Задача предлагаемого этапа',
  agreement_stage_result: 'Ожидаемый результат предлагаемого этапа',
  agreement_stage_limits: 'Границы предлагаемого этапа',
  agreement_leader_actions: 'Что берёт на себя ведущий',
  agreement_client_actions: 'Что берёт на себя участник',
  agreement_load: 'Предполагаемая нагрузка сторон',
  agreement_required: 'Необходимые условия работы',
  agreement_preferred: 'Желательные условия работы',
  agreement_data: 'Использование и доступ к данным',
  agreement_third_parties: 'Участие третьих сторон',
  agreement_postponement: 'Переносы и паузы',
  agreement_client_understanding: 'Как участник понял предложение своими словами',
  agreement_corrections: 'Что требуется изменить в предложении',
  agreement_unknown: 'Что ещё нужно выяснить до решения',
  agreement_client_decision: 'Решение участника по текущему предложению',
  agreement_leader_decision: 'Решение ведущего по текущему предложению',
  intake_name: 'Как к вам обращаться',
  intake_age: 'Возраст',
  intake_role: 'Занятие и текущая роль',
  intake_context: 'Важные обстоятельства жизни',
});

const MAX_TEXT = 12000;
const TOPIC_LABELS = Object.freeze({
  why_now: 'Рассказ участника и повод встречи',
  today: 'Полезный результат сегодняшнего разговора',
  episode: 'Конкретный пример',
  change: 'Желаемое изменение',
  tried: 'Предыдущие попытки и их результат',
  constraints: 'Существенные условия',
  help_expected: 'Ожидания от помощи',
  questions: 'Вопросы о специалисте',
  shared_question: 'Рабочая формулировка вопроса',
  proposal: 'Возможная помощь',
  next: 'Следующий шаг',
  hypothesis: 'Предположение ведущего',
  advice: 'Предварительное мнение или совет',
  process: 'Ход разговора',
  knowledge: 'Сведения, понимание и неизвестное',
  outcome: 'Результат разговора и будущая проверка',
  orientation: 'Какой вопрос сейчас актуален',
  timing: 'Срок решения и последствия отсрочки',
  clarify: 'Краткое прояснение своего вопроса',
  learn_intro: 'Ориентация в учебной работе',
  learn_example: 'Разобранный учебный пример',
  learn_own: 'Учебная попытка на своей ситуации',
  learn_case: 'Новый учебный случай',
  learn_feedback: 'Наблюдения и учебная обратная связь',
  learn_transfer: 'Проверка применения способа',
  fit_check: 'Подходит ли эта помощь',
  agreement: 'Условия работы',
  agreement_summary: 'Краткое предложение работы',
});
const LEARNING_LEVELS = Object.freeze({ '': 'не отмечено', self: 'получилось самостоятельно в этой попытке', prompt: 'получилось с подсказкой в этой попытке', not_yet: 'в этой попытке пока не получилось', not_checked: 'не проверялось' });
const LEARNING_SKILLS = Object.freeze(['question', 'goal_method', 'event', 'boundary', 'unknown']);
const AGREEMENT_DECISIONS = Object.freeze({ '': 'не отмечено', start: 'готов начать на записанных условиях', revise: 'предлагает изменить условия', information: 'нужны сведения до решения', pause: 'берёт паузу', decline: 'отказывается от этого предложения' });
const ENUMS = Object.freeze({
  question_status: Object.freeze({ '': 'не отмечено', confirmed: 'подтверждена', revise: 'нужно уточнить', unknown: 'пока не определена' }),
  fit_status: Object.freeze({ '': 'не отмечено', yes: 'подходит', revise: 'нужны изменения', no: 'не подходит', unknown: 'недостаточно сведений' }),
  next_choice: Object.freeze({ '': 'не отмечено', together: 'продолжить вместе', self: 'действовать самостоятельно', information: 'получить недостающие сведения', other: 'рассмотреть другую помощь', later: 'вернуться позже', undecided: 'решение пока не принято' }),
  agreement_status: Object.freeze({ '': 'не отмечено', discussing: 'обсуждается', agreed: 'есть отметка о согласовании' }),
  task_type: Object.freeze({ '': 'не отмечено', choice: 'выбор направления', implementation: 'осуществление уже выбранного', exploration: 'исследование интересующей темы', other: 'другой вопрос', unclear: 'пока неясно' }),
  clarification_status: Object.freeze({ '': 'не отмечено', clear: 'текущий вопрос прояснили', partial: 'прояснили частично', no_current_decision: 'актуального решения пока не выявили' }),
  learning_choice: Object.freeze({ '': 'не отмечено', yes: 'выбрана учебная работа', later: 'вернуться к обучению позже', not_needed: 'учебная работа сейчас не нужна' }),
  learn_own_help: Object.freeze({ '': 'не отмечено', self: 'выполнил самостоятельно', together: 'выполнили вместе', leader: 'формулировал ведущий', not_checked: 'не проверялось' }),
  help_role: Object.freeze({ '': 'не отмечено', exploration: 'вместе исследовать вопрос', advice: 'дать объяснение или совет', learning: 'обучать способу', joint: 'вместе работать над задачей', other: 'другой способ помощи', unclear: 'подходящий вклад пока неясен' }),
  helper_fit_status: Object.freeze({ '': 'не отмечено', yes: 'предварительно могу помочь с обозначенной частью', no: 'не могу предложить подходящую помощь', information: 'нужны дополнительные сведения для оценки' }),
  agreement_client_decision: AGREEMENT_DECISIONS,
  agreement_leader_decision: AGREEMENT_DECISIONS,
  ...Object.fromEntries(LEARNING_SKILLS.map(skill => [`learn_${skill}_level`, LEARNING_LEVELS])),
});
const TERM_KEYS = Object.freeze(['terms_scope', 'terms_schedule', 'terms_price', 'terms_payment', 'terms_review', 'terms_change']);
export const AGREEMENT_TERM_KEYS = Object.freeze(['agreement_stage_task', 'agreement_stage_result', 'agreement_stage_limits', 'terms_scope', 'agreement_leader_actions', 'agreement_client_actions', 'agreement_load', 'terms_schedule', 'agreement_required', 'agreement_preferred', 'terms_price', 'terms_payment', 'agreement_data', 'agreement_third_parties', 'terms_review', 'terms_change', 'agreement_postponement']);
export const AGREEMENT_FIELDS = Object.freeze([...AGREEMENT_TERM_KEYS, 'agreement_client_understanding', 'agreement_corrections', 'agreement_unknown', 'agreement_client_decision', 'agreement_leader_decision', 'agreement_status']);
const PROPOSAL_KEYS = Object.freeze(['proposal_result', 'proposal_method', 'proposal_client', 'proposal_limits', 'proposal_check']);
const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
const hasText = value => value.trim().length > 0;
const isObject = value => value !== null && typeof value === 'object' && !Array.isArray(value)
  && (Object.getPrototypeOf(value) === Object.prototype || Object.getPrototypeOf(value) === null);
const makeId = () => globalThis.crypto?.randomUUID?.() ?? `record-${Date.now()}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`;

function checkedString(value, label, maximum = MAX_TEXT) {
  if (typeof value !== 'string') throw new Error(`Поле «${label}» должно содержать текст.`);
  if (value.length > maximum) throw new Error(`Поле «${label}» длиннее ${maximum.toLocaleString('ru-RU')} знаков. Сократите его и повторите импорт.`);
  return value;
}

function checkedDate(value) {
  checkedString(value, 'Дата', 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) throw new Error('Дата встречи должна быть в формате ГГГГ-ММ-ДД.');
  const parsed = new Date(`${value}T12:00:00Z`);
  if (!Number.isFinite(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== value) throw new Error('Указана несуществующая дата встречи.');
  return value;
}

function checkedTimestamp(value) {
  checkedString(value, 'Время обновления', 50);
  // Часовой пояс обязателен: локальное время без смещения неоднозначно.
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})$/.test(value)
      || !Number.isFinite(Date.parse(value))) throw new Error('Время обновления должно быть корректной датой ISO с часовым поясом.');
  checkedDate(value.slice(0, 10));
  return value;
}

function checkedTopicTexts(raw, label, maximum) {
  if (!isObject(raw)) throw new Error(`Поле «${label}» должно быть объектом с текстами по темам разговора.`);
  const result = {};
  // Старые записи не содержат этих объектов; новые сохраняют только известные темы.
  for (const [key, topicLabel] of Object.entries(TOPIC_LABELS)) {
    if (own(raw, key)) result[key] = checkedString(raw[key], `${label}: ${topicLabel}`, maximum);
  }
  return result;
}

function checkedFieldTexts(raw, label, maximum = MAX_TEXT, checkEnums = false) {
  if (!isObject(raw)) throw new Error(`Поле «${label}» должно быть объектом с текстовыми записями.`);
  const result = {};
  for (const [key, fieldLabel] of Object.entries(FIELD_LABELS)) {
    if (!own(raw, key)) continue;
    const value = checkedString(raw[key], `${label}: ${fieldLabel}`, maximum);
    if (checkEnums && own(ENUMS, key) && !own(ENUMS[key], value)) throw new Error(`Поле «${fieldLabel}» содержит неизвестный вариант ответа.`);
    result[key] = value;
  }
  return result;
}

function checkedTopic(value) {
  if (typeof value !== 'string' || !own(TOPIC_LABELS, value)) throw new Error('У записи указан неизвестный раздел разговора.');
  return value;
}

function checkedId(value) {
  checkedString(value, 'Идентификатор записи', 200);
  if (!hasText(value)) throw new Error('В записи отсутствует идентификатор.');
  return value;
}

function checkedQaEntries(raw) {
  if (!Array.isArray(raw)) throw new Error('Дополнительные вопросы должны быть списком записей.');
  const ids = new Set();
  return raw.map(entry => {
    if (!isObject(entry)) throw new Error('Каждый дополнительный вопрос должен содержать вопрос и ответ отдельной записью.');
    const id = checkedId(entry.id);
    if (ids.has(id)) throw new Error('У дополнительных вопросов повторяются идентификаторы.');
    ids.add(id);
    return { id, topic: checkedTopic(entry.topic), question: checkedString(entry.question, 'Дополнительный вопрос', 2000),
      answer: checkedString(entry.answer, 'Ответ на дополнительный вопрос'), anchor: checkedString(entry.anchor, 'Опорная запись дополнительного вопроса'),
      at: checkedTimestamp(entry.at), updatedAt: checkedTimestamp(entry.updatedAt) };
  });
}

function checkedQaHistory(raw) {
  if (!Array.isArray(raw)) throw new Error('История исправлений вопросов должна быть списком записей.');
  const ids = new Set();
  return raw.map(entry => {
    if (!isObject(entry) || entry.kind !== 'prompt_correction') throw new Error('Неизвестный вид записи в истории исправлений вопросов.');
    const id = checkedId(entry.id);
    if (ids.has(id)) throw new Error('В истории исправлений вопросов повторяются идентификаторы.');
    ids.add(id);
    return { id, topic: checkedTopic(entry.topic), question: checkedString(entry.question, 'Вопрос до исправления', 2000),
      answers: checkedFieldTexts(entry.answers, 'Ответы до исправления', MAX_TEXT, true),
      answerPrompts: checkedFieldTexts(entry.answerPrompts, 'Вопросы к прежним ответам', 2000),
      at: checkedTimestamp(entry.at), kind: 'prompt_correction' };
  });
}

function checkedHelpOptions(raw) {
  if (!Array.isArray(raw)) throw new Error('Варианты помощи должны быть списком записей.');
  const ids = new Set();
  return raw.map(option => {
    if (!isObject(option)) throw new Error('Вариант помощи должен содержать название, результат, участие и неизвестное.');
    const id = checkedId(option.id);
    if (ids.has(id)) throw new Error('У вариантов помощи повторяются идентификаторы.');
    ids.add(id);
    return { id, name: checkedString(option.name, 'Название варианта помощи', 2000),
      benefit: checkedString(option.benefit, 'Что даст вариант помощи'),
      effort: checkedString(option.effort, 'Что потребуется от участника'),
      unknown: checkedString(option.unknown, 'Что пока неизвестно о варианте помощи') };
  });
}

function checkedAgreementHistory(raw) {
  if (!Array.isArray(raw)) throw new Error('История условий работы должна быть списком редакций.');
  const ids = new Set();
  return raw.map(entry => {
    if (!isObject(entry) || !['conditions_changed', 'decision_changed'].includes(entry.kind)) throw new Error('Неизвестная запись в истории условий работы.');
    const id = checkedId(entry.id);
    if (ids.has(id)) throw new Error('В истории условий повторяются идентификаторы.');
    ids.add(id);
    const answers = checkedFieldTexts(entry.answers, 'Прежняя редакция условий', MAX_TEXT, true);
    const answerPrompts = checkedFieldTexts(entry.answerPrompts, 'Вопросы к прежним условиям', 2000);
    return { id, at: checkedTimestamp(entry.at), kind: entry.kind,
      answers: Object.fromEntries(Object.entries(answers).filter(([key]) => AGREEMENT_FIELDS.includes(key))),
      answerPrompts: Object.fromEntries(Object.entries(answerPrompts).filter(([key]) => AGREEMENT_FIELDS.includes(key))) };
  });
}

function checkedGuidedTrail(raw) {
  if (!Array.isArray(raw)) throw new Error('Путь пошагового разговора должен быть списком идентификаторов.');
  if (raw.length > 1000) throw new Error('Путь пошагового разговора содержит больше 1000 записей.');
  // Проверяем данные, а допустимость шага определяет интерфейс, знающий свой маршрут.
  return raw.map(value => checkedString(value, 'Шаг в пути разговора', 200));
}

function checkedQuestionHistory(raw) {
  if (!Array.isArray(raw)) throw new Error('История формулировок должна быть списком сохранённых версий.');
  return raw.map((entry, index) => {
    if (!isObject(entry)) throw new Error(`Версия ${index + 1} в истории формулировок должна быть записью с текстом, причиной, временем и статусом.`);
    const text = checkedString(entry.text, `Текст версии ${index + 1}`);
    const reason = checkedString(entry.reason, `Основание версии ${index + 1}`);
    const status = checkedString(entry.status, `Статус версии ${index + 1}`);
    if (!own(ENUMS.question_status, status)) throw new Error(`Версия ${index + 1} содержит неизвестный статус формулировки.`);
    return { text, reason, at: checkedTimestamp(entry.at), status };
  });
}

export function createSession(now = new Date()) {
  if (!(now instanceof Date) || !Number.isFinite(now.getTime())) throw new Error('Не удалось определить дату новой встречи.');
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Moscow', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(now);
  const dateParts = Object.fromEntries(parts.map(part => [part.type, part.value]));
  const id = makeId();
  return {
    id,
    date: `${dateParts.year}-${dateParts.month}-${dateParts.day}`,
    title: '',
    step: 0,
    updatedAt: now.toISOString(),
    answers: Object.fromEntries(Object.keys(FIELD_LABELS).map(key => [key, ''])),
    prompts: {},
    anchors: {},
    questionHistory: [],
    answerPrompts: {},
    qaEntries: [],
    qaHistory: [],
    helpOptions: [],
    agreementHistory: [],
    guidedStep: 'welcome',
    guidedTrail: [],
    aiDrafts: {},
    aiConsent: false,
  };
}

export function normaliseSession(raw) {
  if (!isObject(raw)) throw new Error('В файле должна быть одна запись встречи.');
  const id = checkedString(raw.id, 'Идентификатор встречи', 200);
  if (!hasText(id)) throw new Error('В записи отсутствует идентификатор встречи.');
  const date = checkedDate(raw.date);
  const title = checkedString(raw.title, 'Название встречи');
  if (!Number.isInteger(raw.step) || raw.step < 0 || raw.step > 10) throw new Error('Номер темы должен быть целым числом от 0 до 10.');
  const updatedAt = checkedTimestamp(raw.updatedAt);
  if (!isObject(raw.answers)) throw new Error('В записи отсутствует объект с ответами встречи.');
  // Создаём новый объект только с известными полями: импорт не меняет исходник.
  const answers = {};
  for (const [key, label] of Object.entries(FIELD_LABELS)) {
    const value = own(raw.answers, key) ? checkedString(raw.answers[key], label) : '';
    if (own(ENUMS, key) && !own(ENUMS[key], value)) throw new Error(`Поле «${label}» содержит неизвестный вариант ответа.`);
    answers[key] = value;
  }
  const prompts = checkedTopicTexts(own(raw, 'prompts') ? raw.prompts : {}, 'Изменённые вопросы', 2000);
  const anchors = checkedTopicTexts(own(raw, 'anchors') ? raw.anchors : {}, 'Опорные фрагменты разговора', MAX_TEXT);
  const questionHistory = checkedQuestionHistory(own(raw, 'questionHistory') ? raw.questionHistory : []);
  const answerPrompts = checkedFieldTexts(own(raw, 'answerPrompts') ? raw.answerPrompts : {}, 'Вопросы к записанным ответам', 2000);
  const qaEntries = checkedQaEntries(own(raw, 'qaEntries') ? raw.qaEntries : []);
  const qaHistory = checkedQaHistory(own(raw, 'qaHistory') ? raw.qaHistory : []);
  const helpOptions = checkedHelpOptions(own(raw, 'helpOptions') ? raw.helpOptions : []);
  const agreementHistory = checkedAgreementHistory(own(raw, 'agreementHistory') ? raw.agreementHistory : []);
  const guidedStep = checkedString(own(raw, 'guidedStep') ? raw.guidedStep : 'welcome', 'Текущий шаг разговора', 200);
  const guidedTrail = checkedGuidedTrail(own(raw, 'guidedTrail') ? raw.guidedTrail : []);
  const aiDrafts = normaliseAiDrafts(own(raw, 'aiDrafts') ? raw.aiDrafts : {});
  if (own(raw, 'aiConsent') && typeof raw.aiConsent !== 'boolean') throw new Error('Согласие на помощника должно быть явной отметкой.');
  const aiConsent = raw.aiConsent === true;
  return { id, date, title, step: raw.step, updatedAt, answers, prompts, anchors, questionHistory, answerPrompts, qaEntries, qaHistory, helpOptions, agreementHistory, guidedStep, guidedTrail, aiDrafts, aiConsent };
}

export function updateAgreementAnswer(session, key, value, { now = new Date() } = {}) {
  const result = normaliseSession(session);
  if (!AGREEMENT_FIELDS.includes(key)) throw new Error('Неизвестное поле условий работы.');
  checkedString(value, FIELD_LABELS[key]);
  if (own(ENUMS, key) && !own(ENUMS[key], value)) throw new Error('Неизвестный вариант решения по предложению.');
  if (!(now instanceof Date) || !Number.isFinite(now.getTime())) throw new Error('Не удалось определить время изменения условий.');
  const a = result.answers;
  const changed = a[key].trim() !== value.trim();
  const isTerm = AGREEMENT_TERM_KEYS.includes(key);
  const hasDecision = hasText(a.agreement_client_decision) || hasText(a.agreement_leader_decision);
  const hasUnderstanding = hasText(a.agreement_client_understanding);
  const changesOldDecision = ['agreement_client_decision', 'agreement_leader_decision'].includes(key)
    && value !== 'start' && a.agreement_status === 'agreed';
  if (changed && ((isTerm && (a.agreement_status === 'agreed' || hasDecision || hasUnderstanding)) || changesOldDecision)) {
    // Снимок хранит прошлую редакцию и её отметки. Новым условиям они не принадлежат.
    result.agreementHistory.push({ id: makeId(), at: now.toISOString(), kind: isTerm ? 'conditions_changed' : 'decision_changed',
      answers: Object.fromEntries(AGREEMENT_FIELDS.map(field => [field, a[field]])),
      answerPrompts: Object.fromEntries(AGREEMENT_FIELDS.filter(field => own(result.answerPrompts, field)).map(field => [field, result.answerPrompts[field]])) });
    if (a.agreement_status === 'agreed') a.agreement_status = 'discussing';
    if (isTerm) {
      a.agreement_client_decision = '';
      a.agreement_leader_decision = '';
      a.agreement_client_understanding = '';
    }
  }
  a[key] = value;
  result.updatedAt = now.toISOString();
  return result;
}

export function addFollowup(session, { topic, question, anchor = '', now = new Date() }) {
  const result = normaliseSession(session);
  checkedTopic(topic);
  checkedString(question, 'Дополнительный вопрос', 2000);
  if (!hasText(question)) throw new Error('Запишите дополнительный вопрос перед его сохранением.');
  checkedString(anchor, 'Опорная запись дополнительного вопроса');
  if (!(now instanceof Date) || !Number.isFinite(now.getTime())) throw new Error('Не удалось определить время дополнительного вопроса.');
  const at = now.toISOString();
  const entryId = makeId();
  // Новый вопрос не переподписывает ответы основной темы и начинается без ответа.
  result.qaEntries.push({ id: entryId, topic, question, answer: '', anchor, at, updatedAt: at });
  result.updatedAt = at;
  return { session: result, entryId };
}

export function correctPrompt(session, { topic, question, previousQuestion = '', keys = [], now = new Date() }) {
  const result = normaliseSession(session);
  checkedTopic(topic);
  checkedString(question, 'Исправленная формулировка вопроса', 2000);
  if (!hasText(question)) throw new Error('Запишите исправленную формулировку вопроса.');
  checkedString(previousQuestion, 'Вопрос до исправления', 2000);
  if (!Array.isArray(keys) || keys.some(key => typeof key !== 'string' || !own(FIELD_LABELS, key))) throw new Error('Для исправления вопроса указан неизвестный ответ.');
  if (!(now instanceof Date) || !Number.isFinite(now.getTime())) throw new Error('Не удалось определить время исправления вопроса.');
  const at = now.toISOString();
  const uniqueKeys = [...new Set(keys)];
  if (uniqueKeys.some(key => hasText(result.answers[key]))) {
    const answers = Object.fromEntries(uniqueKeys.map(key => [key, result.answers[key]]));
    // Не восстанавливаем прежние вопросы по названиям полей: сохраняем лишь то, что было записано.
    const answerPrompts = Object.fromEntries(uniqueKeys.filter(key => own(result.answerPrompts, key)).map(key => [key, result.answerPrompts[key]]));
    result.qaHistory.push({ id: makeId(), topic, question: previousQuestion, answers, answerPrompts, at, kind: 'prompt_correction' });
  }
  result.prompts[topic] = question;
  result.updatedAt = at;
  return result;
}

export function saveQuestionVersion(session, { previousText = '', previousStatus = '', previousReason = '', reason = '', now = new Date() } = {}) {
  const result = normaliseSession(session);
  checkedString(previousText, 'Прежняя формулировка вопроса');
  checkedString(previousStatus, 'Статус прежней формулировки');
  if (!own(ENUMS.question_status, previousStatus)) throw new Error('У прежней формулировки указан неизвестный статус.');
  checkedString(previousReason, 'Основание прежней формулировки');
  checkedString(reason, 'Основание изменения рабочей формулировки');
  if (!(now instanceof Date) || !Number.isFinite(now.getTime())) throw new Error('Не удалось определить время сохранения формулировки.');
  const at = now.toISOString();
  const history = result.questionHistory;
  const last = () => history[history.length - 1];
  const currentText = result.answers.shared_question;
  // Повторное сохранение текущего текста не возвращает в историю старый черновик.
  if (hasText(currentText) && currentText === last()?.text) {
    last().reason = reason;
    last().status = result.answers.question_status;
    result.answers.question_change_reason = reason;
    result.updatedAt = at;
    return result;
  }
  // Историю меняет только явное сохранение версии, а не ввод каждого символа.
  if (hasText(previousText) && previousText !== last()?.text) {
    history.push({ text: previousText, reason: previousReason, at, status: previousStatus });
  }
  if (hasText(currentText)) {
    if (currentText !== last()?.text) {
      // Статус берём из текущей записи: подтверждение прежней версии не переносится.
      history.push({ text: currentText, reason, at, status: result.answers.question_status });
    } else {
      last().reason = reason;
      last().status = result.answers.question_status;
    }
  }
  result.answers.question_change_reason = reason;
  result.updatedAt = at;
  return result;
}

export function parseImport(text) {
  if (typeof text !== 'string') throw new Error('Для импорта нужен текст файла JSON.');
  let raw;
  try { raw = JSON.parse(text.replace(/^\uFEFF/, '')); }
  catch { throw new Error('Не удалось прочитать JSON. Выберите файл встречи, сохранённый этой страницей.'); }
  if (!isObject(raw)) throw new Error('Файл должен содержать запись встречи в формате JSON.');
  if (own(raw, 'format') || own(raw, 'version') || own(raw, 'session')) {
    if (raw.format !== 'first-meeting-sheet') throw new Error('Этот файл относится к другому формату. Нужен файл первой встречи.');
    if (![1, 2, 3, 4, 5, 6, 7].includes(raw.version)) throw new Error('Версия файла не поддерживается. Для этой страницы нужна версия от 1 до 7.');
    if (!own(raw, 'session')) throw new Error('В файле отсутствует запись встречи.');
    return { ...normaliseSession(raw.session), aiConsent: false };
  }
  return { ...normaliseSession(raw), aiConsent: false };
}

export function exportSession(session) {
  return JSON.stringify({ format: 'first-meeting-sheet', version: 7, session: normaliseSession(session) }, null, 2);
}

export function makeSummary(session) {
  const clean = normaliseSession(session);
  const a = clean.answers;
  const output = [`Встреча: ${hasText(clean.title) ? clean.title : 'без названия'}`, `Дата: ${clean.date}`, `Обновлено: ${clean.updatedAt}`];
  let sections = 0;
  const displayAnswer = (key, value) => own(ENUMS, key) ? ENUMS[key][value] : value;
  const recordLines = (answers, answerPrompts, keys) => keys.filter(key => own(answers, key) && hasText(answers[key])).map(key => {
    const line = `${FIELD_LABELS[key]}: ${displayAnswer(key, answers[key])}`;
    // Привязка принадлежит ответу, а не нынешней редакции вопроса на экране.
    return own(answerPrompts, key) && hasText(answerPrompts[key]) ? `Вопрос к этой записи: ${answerPrompts[key]}\n${line}` : line;
  });
  const linesFor = keys => recordLines(a, clean.answerPrompts, keys);
  const section = (heading, lines) => {
    if (!lines.length) return;
    sections += 1;
    output.push('', heading, ...lines);
  };
  section('Несколько слов об участнике — записано на этой встрече', linesFor(['intake_name', 'intake_age', 'intake_role', 'intake_context']));
  section('Ситуация и желаемые результаты', linesFor(['why_now', 'today', 'episode', 'change']));
  section('Вид текущей задачи и событие, после которого возник вопрос', linesFor(['task_type', 'task_type_details', 'trigger_event']));
  section('Желаемый эффект и уже рассматриваемый способ', linesFor(['desired_effect', 'considered_method']));
  section('Предварительные критерии результата и допустимая цена изменений', linesFor(['success_criteria', 'unacceptable_costs']));
  section('Предыдущий опыт и существенные условия', linesFor(['tried', 'tried_result', 'constraints']));
  section('Что сохраняется и кто вправе принимать решение', linesFor(['preserve', 'decision_owner']));
  section('Срок самого решения, его источник и последствия отсрочки', linesFor(['decision_deadline', 'deadline_source', 'delay_consequences']));
  section('Известные сведения — как они записаны участником', linesFor(['known_info']));
  section('Текущее понимание — версия, а не установленная причина', linesFor(['interpretation']));
  section('Неизвестное и существенный вопрос для проверки', linesFor(['unknown_info', 'unknown_priority']));
  section('Участники и сведения об их позициях', linesFor(['stakeholders', 'stakeholder_known']));
  section('Предположения о позициях участников — требуют проверки', linesFor(['stakeholder_assumed']));
  section('Альтернативные понимания задачи', linesFor(['alternative_framings', 'distinguishing_info']));
  section('Ожидания от помощи и вопросы', linesFor(['help_expected', 'questions']));
  section('Что важно участнику при выборе помощи', linesFor(['help_preferences']));
  clean.helpOptions.filter(option => ['name', 'benefit', 'effort', 'unknown'].some(key => hasText(option[key]))).forEach((option, index) => {
    section(`Обсуждаемый вариант помощи ${index + 1}`, [
      `Вариант: ${hasText(option.name) ? option.name : 'название не записано'}`,
      `Что может дать: ${hasText(option.benefit) ? option.benefit : 'не записано'}`,
      `Что потребуется от участника: ${hasText(option.effort) ? option.effort : 'не записано'}`,
      `Что пока неизвестно: ${hasText(option.unknown) ? option.unknown : 'не записано'}`,
    ]);
  });
  const preference = linesFor(['help_informed_preference']);
  if (preference.length) preference.push('Предпочтение после обсуждения вариантов не означает согласия на условия работы.');
  section('Предпочтение после обсуждения вариантов', preference);
  section('Условия использования помощи', linesFor(['help_use_conditions']));
  const helper = linesFor(['help_role', 'helper_experience', 'helper_fit_reason', 'helper_fit_status']);
  if (helper.length) helper.push('Это предварительная оценка ведущего. Она не подтверждает эффективность помощи и не заменяет решение участника.');
  section('Возможный вклад, основания и оценка ведущего', helper);

  const hypothesis = linesFor(['hypothesis_basis', 'hypothesis_text', 'hypothesis_reply']);
  if (hypothesis.length) hypothesis.push('Запись предположения и отклика не устанавливает причину и не подтверждает договорённость о работе.');
  section('Предположение ведущего — версия для проверки', hypothesis);
  section('Предварительное мнение или совет ведущего', linesFor(['advice_basis', 'advice_text', 'advice_limits', 'advice_reply']));
  section('Как идёт разговор', linesFor(['process_feedback', 'process_adjustment']));

  const question = linesFor(['shared_question', 'question_change_reason']);
  if (question.length || a.question_status) {
    question.push(`Подтверждение формулировки: ${ENUMS.question_status[a.question_status]}.`);
    if (a.question_status === 'confirmed' && !hasText(a.shared_question)) question.push('Формулировка самого вопроса не записана.');
  }
  section('Рабочий вопрос', question);
  const clarification = linesFor(['participant_question', 'clarification_status']);
  if (clarification.length) clarification.push('Совместное прояснение вопроса не подтверждает самостоятельное владение способом его формулирования.');
  section('Краткое завершение прояснения текущего вопроса', clarification);

  if (clean.questionHistory.length) {
    const historyLines = clean.questionHistory.flatMap((entry, index) => [
      `Версия ${index + 1}. Сохранено: ${entry.at}`,
      `Формулировка: ${entry.text}`,
      `Статус этой версии: ${ENUMS.question_status[entry.status]}.`,
      `Основание сохранения или изменения: ${hasText(entry.reason) ? entry.reason : 'не записано'}`,
    ]);
    historyLines.push('Отметки относятся к конкретным сохранённым формулировкам и не подтверждают причины ситуации или согласие на работу.');
    section('История рабочих формулировок', historyLines);
  }

  const proposal = linesFor(PROPOSAL_KEYS);
  section('Предложение помощи', proposal);
  const participantFit = linesFor(['fit_feedback']);
  if (participantFit.length || a.fit_status || proposal.length) {
    participantFit.push(`Отклик о соответствии: ${ENUMS.fit_status[a.fit_status]}.`);
    participantFit.push('Предложение и отклик сами по себе не подтверждают договорённость о работе.');
  }
  section('Отклик и предварительная оценка участника', participantFit);
  section('Основания и предположения предложения помощи', linesFor(['proposal_basis', 'proposal_assumption', 'proposal_uncertainty']));

  section('Результат сегодняшнего разговора — по записи участника', linesFor(['today_outcome']));
  section('Будущая проверка — результат ещё не установлен', linesFor(['remaining_check']));

  section('Выбор учебной работы', linesFor(['learning_choice']));
  section('Учебная попытка на собственной ситуации', linesFor(['learn_own_attempt', 'learn_own_help', 'learn_own_feedback']));
  section('Запись решения нового учебного случая', linesFor(['learn_case_question', 'learn_case_facts', 'learn_case_change', 'learn_case_limits']));
  const learning = linesFor(LEARNING_SKILLS.flatMap(skill => [`learn_${skill}_level`, `learn_${skill}_evidence`]));
  learning.push(...linesFor(['learn_feedback']));
  if (learning.length) learning.push('Это наблюдения по конкретной учебной попытке. Отметки не устанавливают общую компетентность или перенос навыка на другие ситуации.');
  section('Наблюдаемое выполнение, помощь и учебная обратная связь', learning);
  const transfer = linesFor(['learn_transfer_action', 'learn_transfer_when', 'learn_transfer_check', 'learn_open']);
  if (transfer.length) transfer.push('План будущего применения не является подтверждением освоения способа.');
  section('Применение способа и то, что остаётся непроверенным', transfer);

  const next = [];
  if (a.next_choice) next.push(`Выбранное продолжение: ${ENUMS.next_choice[a.next_choice]}.`);
  next.push(...linesFor(['next_step', 'next_when', 'next_check']));
  section('Следующий шаг', next);

  const terms = linesFor(AGREEMENT_TERM_KEYS);
  if (a.agreement_status === 'agreed') {
    // В итог попадает отметка пользователя, а не автоматически сделанный вывод.
    const agreed = ['Статус в записи: есть отметка «согласовано».', ...terms];
    if (!terms.length) agreed.push('Содержание условий не записано; объём, срок и цена из этой отметки не следуют.');
    agreed.push('Общая отметка не создаёт отдельных решений участника и ведущего по текущему предложению.');
    if (a.agreement_client_decision !== 'start' || a.agreement_leader_decision !== 'start') agreed.push('Отдельные решения сторон не подтверждают готовность обоих начать на этой редакции условий. Нужно уточнить общую отметку.');
    if (hasText(a.agreement_corrections) || hasText(a.agreement_unknown)) agreed.push('Перед началом нужно проверить, разрешены ли записанные поправки и вопросы.');
    if (a.next_choice && a.next_choice !== 'together') agreed.push('Выбранное продолжение отличается от «продолжить вместе»; нужно сверить, к чему относится отметка о согласовании.');
    section('Зафиксированные условия и отметка о согласовании', agreed);
  } else if (terms.length || a.agreement_status === 'discussing') {
    section('Обсуждавшееся предложение — согласование не подтверждено', [
      `Статус в записи: ${ENUMS.agreement_status[a.agreement_status]}.`,
      ...terms,
    ]);
  }
  const agreementDecisions = linesFor(['agreement_client_understanding', 'agreement_corrections', 'agreement_unknown', 'agreement_client_decision', 'agreement_leader_decision']);
  if (agreementDecisions.length) agreementDecisions.push('Понимание предложения и решения сторон записаны раздельно. Эти отметки не создают юридический договор автоматически.');
  section('Понимание, открытые вопросы и отдельные решения по условиям', agreementDecisions);
  clean.agreementHistory.forEach((entry, index) => {
    const lines = [`Прежняя редакция сохранена: ${entry.at}`, entry.kind === 'conditions_changed' ? 'После изменения условий прежние решения нужно принять заново.' : 'Решение по прежней редакции изменилось.'];
    lines.push(...recordLines(entry.answers, entry.answerPrompts, AGREEMENT_FIELDS));
    section(`История условий — прежняя редакция ${index + 1}`, lines);
  });
  clean.qaEntries.forEach((entry, index) => {
    const lines = [`Записано: ${entry.at}`, `Обновлено: ${entry.updatedAt}`, `Вопрос: ${entry.question}`];
    if (hasText(entry.anchor)) lines.push(`Опорная запись: ${entry.anchor}`);
    lines.push(hasText(entry.answer) ? `Ответ: ${entry.answer}` : 'Ответ пока не записан.');
    section(`Отдельный дополнительный вопрос ${index + 1} — ${TOPIC_LABELS[entry.topic]}`, lines);
  });
  clean.qaHistory.forEach((entry, index) => {
    const lines = [`Снимок сохранён: ${entry.at}`, `Вопрос на экране до исправления: ${hasText(entry.question) ? entry.question : 'не был записан'}`];
    lines.push(...recordLines(entry.answers, entry.answerPrompts, Object.keys(entry.answers)));
    const missingBindings = Object.keys(entry.answers).filter(key => hasText(entry.answers[key]) && !own(entry.answerPrompts, key));
    if (missingBindings.length) lines.push(`Точная привязка к прежнему вопросу отсутствует для записей: ${missingBindings.map(key => FIELD_LABELS[key]).join('; ')}. Она не восстановлена предположением.`);
    section(`Снимок перед исправлением вопроса ${index + 1} — ${TOPIC_LABELS[entry.topic]}`, lines);
  });
  // Формулировки на экране сохраняются отдельно от ответов и договорённостей.
  section('Изменённые вопросы на экране', Object.entries(clean.prompts)
    .filter(([, value]) => hasText(value))
    .map(([key, value]) => `${TOPIC_LABELS[key]} — вопрос: ${value}`));
  section('Опорные фрагменты, показанные в разговоре', Object.entries(clean.anchors)
    .filter(([, value]) => hasText(value))
    .map(([key, value]) => `${TOPIC_LABELS[key]} — опорная запись: ${value}`));
  if (!sections) output.push('', 'Ответы пока не записаны.');
  return output.join('\n');
}
