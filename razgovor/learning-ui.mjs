import { CONCEPTS, WORKED_CASE, PRACTICE_CASE, RUBRIC } from './learning.mjs';

const LEARNING_TABS = [
  { mode: 'learn_intro', title: 'Зачем этот навык' },
  { mode: 'learn_example', title: 'Разобранный пример' },
  { mode: 'learn_own', title: 'Ваша попытка' },
  { mode: 'learn_case', title: 'Новый случай' },
  { mode: 'learn_feedback', title: 'Разбор попытки' },
  { mode: 'learn_transfer', title: 'Применить в жизни' },
];

const NEXT_ACTIONS = {
  learn_intro: { title: 'Посмотреть пример', mode: 'learn_example' },
  learn_example: { title: 'Попробовать на своём вопросе', mode: 'learn_own' },
  learn_own: { title: 'Открыть новый случай', mode: 'learn_case' },
  learn_case: { title: 'Разобрать попытку', mode: 'learn_feedback' },
  learn_feedback: { title: 'Наметить применение в жизни', mode: 'learn_transfer' },
  learn_transfer: { title: 'Посмотреть итог', summary: true },
};

// Показываем учебные материалы и записи, не делая выводов об освоении за человека.
export function renderLearning({
  mode,
  session,
  parent,
  dom,
  renderField,
  openMode,
  fields = [],
  returnToConversation,
  viewSummary,
}) {
  if (!LEARNING_TABS.some(tab => tab.mode === mode)) return;
  const answers = session.answers;
  const fieldMap = new Map(fields.map(field => [field.key, field]));
  const hasText = value => typeof value === 'string' && value.trim().length > 0;
  const returnToTalk = () => {
    if (typeof returnToConversation === 'function') returnToConversation();
    else openMode('orientation');
  };
  const showSummary = () => {
    if (typeof viewSummary === 'function') viewSummary();
    else openMode('outcome');
  };
  const button = (title, className, action) => {
    const node = dom('button', className, title);
    node.type = 'button';
    node.addEventListener('click', action);
    return node;
  };
  const appendFields = (target, selected = fields, compact = true) => {
    selected.forEach(field => renderField(field, target, compact));
  };
  const scenario = (title, text, target = parent) => {
    const block = dom('section', 'learning-example');
    block.append(dom('p', 'case-label', title), dom('p', 'case-scenario', text));
    target.append(block);
    return block;
  };

  const navigation = dom('nav', 'learning-tabs');
  navigation.setAttribute('aria-label', 'Учебная часть');
  LEARNING_TABS.forEach(tab => {
    const tabButton = button(tab.title, '', () => openMode(tab.mode));
    if (tab.mode === mode) {
      tabButton.classList.add('current');
      tabButton.setAttribute('aria-current', 'page');
    }
    navigation.append(tabButton);
  });
  parent.append(navigation);

  if (mode === 'learn_intro') {
    parent.append(dom('p', 'learning-intro', 'Здесь можно попробовать точнее формулировать вопрос: что сейчас требуется решить, что сохраняется и чего ещё не хватает для ответа. Можно взять отдельное объяснение или пройти пример и собственную пробу.'));
    parent.append(dom('p', 'learning-why', 'Можно остановиться на нужном объяснении. Попытку разберём вместе, с учётом полученной помощи.'));
    CONCEPTS.forEach(concept => {
      const article = dom('article', 'learning-concept');
      article.append(dom('h3', '', concept.title), dom('p', 'learning-why', concept.why), dom('p', '', concept.explanation));
      const example = dom('details', 'learning-example');
      example.append(dom('summary', '', 'Условный пример'));
      example.append(dom('p', 'case-label', 'Исходная фраза'), dom('p', '', concept.before));
      example.append(dom('p', 'case-label', 'Как можно уточнить'), dom('p', '', concept.after));
      article.append(example);
      parent.append(article);
    });
    appendFields(parent);
  }

  if (mode === 'learn_example') {
    scenario(WORKED_CASE.title, WORKED_CASE.scenario);
    WORKED_CASE.rows.forEach((row, index) => {
      const detail = dom('details', 'worked-row');
      detail.open = index === 0;
      detail.append(dom('summary', '', row.question));
      detail.append(dom('p', 'example-answer', row.answer), dom('p', 'learning-why', row.why));
      parent.append(detail);
    });
    const result = dom('section', 'worked-result');
    result.append(dom('h3', '', 'Один возможный рабочий вопрос'), dom('p', '', WORKED_CASE.question), dom('p', 'learning-why', WORKED_CASE.limits));
    parent.append(result);
    appendFields(parent);
  }

  if (mode === 'learn_own') {
    parent.append(dom('p', 'learning-intro', 'Попробуйте сформулировать свой текущий вопрос и обозначить его границы. Можно использовать свой рассказ или условную ситуацию, которую вам удобно обсуждать.'));
    parent.append(dom('p', 'learning-why', 'Если нужна подсказка, её можно попросить. Потом отдельно отметим, что получилось самому и где помог ведущий.'));
    appendFields(parent, fields, false);
  }

  if (mode === 'learn_case') {
    scenario(PRACTICE_CASE.title, PRACTICE_CASE.scenario);
    parent.append(dom('p', 'learning-intro', PRACTICE_CASE.instruction));
    appendFields(parent, fields, false);
    const review = dom('details', 'practice-review');
    review.append(dom('summary', '', 'Обсудить один возможный разбор'));
    review.append(dom('p', 'learning-why', 'Обычно к разбору возвращаемся после собственной попытки. Можно открыть его как подсказку раньше; тогда при обсуждении отметим, какую помощь вы использовали.'));
    PRACTICE_CASE.review.forEach(item => {
      const row = dom('section', 'review-item');
      row.append(dom('h3', '', item.title), dom('p', '', item.text));
      review.append(row);
    });
    parent.append(review);
  }

  if (mode === 'learn_feedback') {
    const reminder = dom('section', 'practice-reminder');
    reminder.append(dom('p', 'case-label', 'Ваша запись на новом случае'));
    reminder.append(dom('p', '', hasText(answers.learn_case_question) ? answers.learn_case_question : 'Вопрос на новом случае пока не записан. Можно вернуться к случаю или отметить, что применение ещё не проверяли.'));
    const additionalAnswers = [
      ['learn_case_facts', 'Событие и срок'],
      ['learn_case_change', 'Желаемое изменение и способ'],
      ['learn_case_limits', 'Границы и неизвестное'],
    ].filter(([key]) => hasText(answers[key]));
    if (additionalAnswers.length) {
      const otherNotes = dom('details', 'practice-reminder');
      otherNotes.append(dom('summary', '', 'Другие записи этой попытки'));
      additionalAnswers.forEach(([key, label]) => otherNotes.append(dom('p', 'case-label', label), dom('p', '', answers[key])));
      reminder.append(otherNotes);
    }
    const condition = dom('details', 'practice-reminder');
    condition.append(dom('summary', '', 'Условие учебного случая'), dom('p', 'case-scenario', PRACTICE_CASE.scenario));
    reminder.append(condition);
    parent.append(reminder);
    parent.append(dom('p', 'learning-intro', 'Разберём эту попытку по отдельным признакам. Для каждой отметки нужен конкретный ответ или действие; если не проверяли, так и запишем.'));
    parent.append(dom('p', 'learning-why', 'Если использовали разбор или подсказку, запишем, в чём она помогла.'));
    RUBRIC.forEach((criterion, index) => {
      const levelKey = `learn_${criterion.key}_level`;
      const evidenceKey = `learn_${criterion.key}_evidence`;
      const item = dom('details', 'rubric-item');
      item.open = index === 0 || hasText(answers[levelKey]) || hasText(answers[evidenceKey]);
      item.append(dom('summary', '', criterion.title), dom('p', 'learning-why', criterion.prompt));
      const level = fieldMap.get(levelKey);
      const evidence = fieldMap.get(evidenceKey);
      if (level) renderField({ ...level, label: 'Как получилось в этой попытке' }, item, true);
      if (evidence) renderField({ ...evidence, label: 'На каком ответе или действии это видно' }, item, true);
      parent.append(item);
    });
    const feedback = fieldMap.get('learn_feedback');
    if (feedback) renderField(feedback, parent, false);
  }

  if (mode === 'learn_transfer') {
    parent.append(dom('p', 'learning-intro', 'Выберем ситуацию, где этот способ может пригодиться, и договоримся, какой опыт стоит получить.'));
    appendFields(parent, fields, false);
    parent.append(dom('p', 'learning-why', 'По одной учебной попытке нельзя судить, как способ сработает в других условиях; это проверим отдельно.'));
  }

  const actions = dom('div', 'learning-actions');
  actions.append(button('Вернуться к разговору', 'button button-light', returnToTalk));
  const next = NEXT_ACTIONS[mode];
  const continueButton = button(next.title, 'button button-primary', () => {
    if (mode === 'learn_intro' && ['later', 'not_needed'].includes(answers.learning_choice)) returnToTalk();
    else if (next.summary) showSummary();
    else openMode(next.mode);
  });
  const updateIntroAction = () => {
    if (mode !== 'learn_intro') return;
    continueButton.textContent = ['later', 'not_needed'].includes(answers.learning_choice) ? 'Продолжить разговор' : next.title;
  };
  actions.append(continueButton);
  parent.append(actions);
  updateIntroAction();
  // Отказ или пауза меняют направление кнопки, не закрывая доступ к материалам.
  if (mode === 'learn_intro') parent.querySelector('[name="learning_choice"]')?.addEventListener('change', updateIntroAction);
}
