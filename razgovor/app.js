import { FIELD_LABELS, createSession, normaliseSession, parseImport, exportSession, makeSummary, saveQuestionVersion, addFollowup, correctPrompt, AGREEMENT_FIELDS, AGREEMENT_TERM_KEYS, updateAgreementAnswer, saveChatTurn } from './core.mjs';
import { TOPIC_PURPOSES } from './learning.mjs';
import { renderLearning } from './learning-ui.mjs';
import { GUIDED_FLOW, GUIDED_PHASES } from './guided-flow.mjs';
import { invalidateStaleDrafts, isDraftCurrent, acceptDraft, rejectDraft } from './ai-drafts.mjs';
import { FIELD_SCHEMA, SCREEN_SCHEMA } from './ai-schema.mjs';
import { collectCardContext, cardFingerprint, buildCardRequest, validateCardResponse, isCardCurrent, acceptCardDraft, rejectCardDraft, invalidateAiCards } from './ai-cards.mjs';
import { requestDrafts } from './ai-client.mjs';

const STORAGE_KEY = 'first-meeting-sheet:v1';
const EMPTY = 'Пока не записано';
const choices = {
  question_status: [['', 'Пока не отмечено'], ['confirmed', 'Сейчас понимаем задачу так'], ['revise', 'Нужно уточнить'], ['unknown', 'Вопрос пока не определили']],
  fit_status: [['', 'Пока не отмечено'], ['yes', 'Предварительно подходит'], ['revise', 'Нужно изменить предложение'], ['no', 'Не подходит'], ['unknown', 'Нужны сведения']],
  help_role: [['', 'Пока не выбрали'], ['exploration', 'Вместе исследовать вопрос'], ['advice', 'Получить объяснение или совет'], ['learning', 'Освоить способ с моей помощью'], ['joint', 'Вместе работать над задачей'], ['other', 'Другой способ помощи'], ['unclear', 'Подходящий способ пока неясен']],
  helper_fit_status: [['', 'Пока не отметил'], ['yes', 'Предварительно могу помочь с этой частью'], ['no', 'Не могу предложить подходящую помощь'], ['information', 'Мне нужны дополнительные сведения']],
  next_choice: [['', 'Пока не выбрали'], ['together', 'Продолжить вместе'], ['self', 'Действовать самостоятельно'], ['information', 'Получить недостающие сведения'], ['other', 'Рассмотреть другую помощь'], ['later', 'Вернуться позже'], ['undecided', 'Решение пока не принято']],
  agreement_status: [['', 'Пока не отмечено'], ['discussing', 'Предложение обсуждается'], ['agreed', 'Эти условия согласованы']],
  task_type: [['', 'Пока не отмечено'], ['choice', 'Выбрать направление'], ['implementation', 'Разобраться, как осуществить выбранное'], ['exploration', 'Пока исследовать интересующую тему'], ['other', 'Другой вопрос'], ['unclear', 'Это ещё предстоит понять']],
  clarification_status: [['', 'Пока не отмечено'], ['clear', 'Текущий вопрос стал понятен'], ['partial', 'Остались существенные неясности'], ['no_current_decision', 'Сейчас нет решения, которое нужно принять']],
  learning_choice: [['', 'Пока не выбирали'], ['yes', 'Хочу попробовать'], ['later', 'Вернуться к этому позже'], ['not_needed', 'Сейчас достаточно прояснения моего вопроса']],
  learn_own_help: [['', 'Пока не отмечено'], ['self', 'Сформулировал сам'], ['together', 'Сформулировали вместе'], ['leader', 'Формулировку предложил ведущий'], ['not_checked', 'Самостоятельность не проверяли']],
};
const learningLevels = [['', 'Пока не отмечено'], ['self', 'Получилось самостоятельно'], ['prompt', 'Получилось с подсказкой'], ['not_yet', 'Пока трудно'], ['not_checked', 'Не проверяли']];
const agreementDecisions = [['', 'Пока не отмечено'], ['start', 'Готов начать на записанных условиях'], ['revise', 'Предлагаю изменить условия'], ['information', 'Нужны сведения до решения'], ['pause', 'Беру паузу'], ['decline', 'Отказываюсь от этого предложения']];
choices.agreement_client_decision = agreementDecisions;
choices.agreement_leader_decision = agreementDecisions;
for (const key of ['question', 'goal_method', 'event', 'boundary', 'unknown']) choices[`learn_${key}_level`] = learningLevels;
const textField = (key, label = FIELD_LABELS[key], hint = '') => ({ key, label, hint });
const selectField = (key, label) => ({ key, label, select: choices[key] });
const HELP_PURPOSES = {
  fit_check: 'Зачем: сравнить реальные способы помощи и понять, какой подходит вам и что я могу предложить.',
  proposal: 'Зачем: проверить конкретное предложение. Ваше предпочтение и моя оценка ещё не означают согласия на работу.',
  agreement: 'Зачем: обсудить конкретный этап, вклад каждого и условия до решения о начале работы.',
  agreement_summary: 'Зачем: увидеть предложение целиком, поправить непонятное и отдельно записать решение каждого.',
};
const steps = [
  { group: 'Рассказ', short: 'Свободный рассказ', title: 'Расскажите, с чем вы пришли. С чего вам удобно начать?', hint: 'Начните с того, что сейчас важно для вас. Сначала выслушаем рассказ; уточнения выберем по ходу.', fields: [textField('why_now', 'Ваш рассказ — краткая запись')], context: [] },
  { group: 'Ситуация', short: 'Результат разговора', title: 'Что было бы полезно получить к концу сегодняшнего разговора?', hint: 'Например, что-то понять, уточнить, решить или наметить следующий шаг. Если пока неясно, так и запишем.', fields: [textField('today', 'Что сделает этот разговор полезным')], context: ['why_now'] },
  { group: 'Ситуация', short: 'Конкретный пример', title: 'Можете привести недавний пример, на котором это видно?', hint: 'Берём один пример. Затем, если нужно, уточним, после чего сам вопрос стал актуальным.', fields: [textField('episode', 'Ситуация и то, что произошло'), textField('trigger_event', 'После чего возник вопрос или он стал важным сейчас')], context: ['why_now', 'today'] },
  { group: 'Желаемое изменение', short: 'Что хочется изменить', title: 'Что вам хочется изменить в этой ситуации?', hint: 'Желаемый результат и признаки его приемлемости могут уточняться. Запишем то, что сейчас понятно.', fields: [textField('change', 'Желаемое изменение'), textField('success_criteria', 'По каким признакам результат вам подойдёт'), textField('unacceptable_costs', 'Чего этот результат не должен потребовать')], context: ['episode', 'today'] },
  { group: 'Опыт и условия', short: 'Что уже пробовали', title: 'Что вы уже пробовали?', hint: 'Сначала запишем действия, затем посмотрим, что они дали и что осталось неясным.', fields: [textField('tried', 'Что вы делали'), textField('tried_result', 'Что из этого получилось')], context: ['change', 'episode'] },
  { group: 'Опыт и условия', short: 'Что важно учесть', title: 'Какие обстоятельства важно учесть?', hint: 'Отмечаем только существенное. Срок самого решения можно отдельно разобрать в теме «Срок и отсрочка».', fields: [textField('constraints', 'Существенные обстоятельства'), textField('preserve', 'Что вам важно сохранить'), textField('decision_owner', 'Кто принимает решение и что зависит от других')], context: ['change', 'tried_result'] },
  { group: 'Ожидания от помощи', short: 'Какая помощь нужна', title: 'Какой помощи вы сейчас ожидаете от меня?', hint: 'Вместе разобраться, получить мнение, освоить способ, что-то сделать вместе — или пока трудно сказать.', fields: [textField('help_expected', 'Ваше ожидание от помощи')], context: ['today', 'change', 'tried_result', 'constraints'] },
  { group: 'Ожидания от помощи', short: 'Вопросы ко мне', title: 'Что вам нужно узнать о моей работе?', hint: 'Можно уточнить опыт, способ работы, ваше участие, возможные результаты и ограничения. К этому вопросу можно перейти в любой момент.', fields: [textField('questions', 'Что важно спросить или уточнить')], context: ['help_expected', 'constraints'] },
  { group: 'Вопрос и возможная помощь', short: 'Наше понимание задачи', title: 'Как мы сейчас понимаем задачу?', hint: 'Это рабочая версия. Её можно уточнять при новых сведениях; предыдущие формулировки сохраняются после редактирования.', speaker: 'Формулируем и проверяем вместе', fields: [textField('shared_question', 'Текущее понимание задачи'), selectField('question_status', 'Как вы оцениваете эту версию?'), textField('question_change_reason', 'Что нового мы узнали и почему уточнили вопрос', 'Можно оставить пустым, если это первая формулировка или основание пока неясно.')], context: ['why_now', 'change', 'tried_result', 'constraints', 'help_expected', 'unknown_priority'] },
  { group: 'Вопрос и возможная помощь', short: 'Предложение помощи', title: 'Подходит ли вам такое предложение помощи?', hint: 'Сначала объясню, с какой частью вашего вопроса могу помочь и почему. Затем проверим ваше понимание и отклик. Цена и условия начала — отдельный следующий вопрос.', speaker: 'Предложение ведущего и ваш отклик', fields: [textField('proposal_basis', 'На какие сведения опирается предложение', 'Проверяем, точно ли я понял вашу задачу и на чём основан мой вывод.'), textField('proposal_method', 'Как предлагаю работать и почему'), textField('proposal_result', 'С чем я предлагаю помочь и какой результат ожидаем', 'Обозначаем подходящую часть вашего вопроса и ожидаемый результат.'), textField('proposal_client', 'Что потребуется от вас', 'Какие действия, знания, время или участие нужны, чтобы воспользоваться помощью.'), textField('proposal_limits', 'Границы помощи и существенные последствия', 'Чего эта помощь не решит; какие условия и влияние на другие дела стоит учесть.'), textField('proposal_check', 'Как посмотрим, даёт ли это пользу'), textField('fit_feedback', 'Что подходит, что вызывает сомнения и что нужно изменить', 'Как вы поняли предложенный способ? Если я упустил что-то важное, поправьте меня.'), selectField('fit_status', 'Ваша предварительная оценка')], context: ['participant_question', 'shared_question', 'help_expected', 'help_preferences', 'help_informed_preference', 'help_role', 'helper_experience', 'helper_fit_reason', 'helper_fit_status', 'constraints', 'unknown_priority'] },
  { group: 'Решение и следующий шаг', short: 'Что дальше', title: 'Что вы выбираете делать дальше?', hint: 'Можно продолжить вместе, действовать самостоятельно, получить сведения, рассмотреть другую помощь или взять паузу.', fields: [selectField('next_choice', 'Вариант продолжения'), textField('next_step', 'Ближайший шаг: кто и что делает'), textField('next_when', 'Когда или при каком условии', 'Указываем срок или условие, о котором действительно договорились.'), textField('next_check', 'Что хотим увидеть в результате')], context: ['shared_question', 'proposal_result', 'fit_feedback'] },
];
const topicKeys = ['why_now', 'today', 'episode', 'change', 'tried', 'constraints', 'help_expected', 'questions', 'shared_question', 'proposal', 'next'];
const extraViews = {
  agreement: { group: 'Условия работы', short: 'Условия работы', title: 'На каких условиях мы могли бы работать?', hint: 'Это предложение для обсуждения. Можно изменить условия, попросить сведения, взять паузу или отказаться. Решение о продолжении не нужно принимать заранее.', speaker: 'Конкретный этап и решения сторон', context: ['participant_question', 'shared_question', 'help_expected', 'help_informed_preference', 'helper_fit_reason', 'fit_feedback'], fields: [] },
  agreement_summary: { group: 'Краткое предложение', short: 'Предложение целиком', title: 'Правильно ли здесь записано наше предложение?', hint: 'Проверьте результат, вклад каждого, сроки, цену и способ пересмотра. Исправления и решения участников записываем отдельно.', speaker: 'Проверяем предложение вместе', context: [], fields: [] },
  fit_check: { group: 'Выбор помощи', short: 'Подходит ли помощь', title: 'Какую помощь мы можем выбрать для вашей задачи?', hint: 'Вы расскажете, что важно вам. Я объясню, с чем могу помочь, на что опираюсь и чего пока не знаю. Можно выбрать другой способ или взять паузу.', speaker: 'Совместный выбор помощи', context: ['participant_question', 'shared_question', 'help_expected', 'questions', 'help_preferences', 'constraints', 'preserve', 'unknown_priority'], fields: [textField('help_preferences', 'Что вам важно при выборе помощи', 'Например, результат, собственное участие и то, что важно сохранить. Берём ваши критерии.'), selectField('help_role', 'Какой вклад ведущего сейчас рассматриваем'), textField('helper_experience', 'Какие мои знания и опыт относятся к вашей задаче', 'Я называю конкретный опыт и его пределы.'), textField('help_use_conditions', 'Что нужно, чтобы вы могли воспользоваться помощью', 'Проверяем доступные действия, знания и условия. Если сведений нет, оставляем вопрос открытым.'), textField('helper_fit_reason', 'Почему я считаю этот вклад подходящим или неподходящим', 'Как я понял задачу, что умею предложить и какие условия или последствия ещё нужно учесть.'), selectField('helper_fit_status', 'Моя предварительная оценка'), textField('help_informed_preference', 'Теперь, когда мы обсудили варианты, какой вам подходит и почему?', 'Можно выбрать другой способ, попросить сведения, отказаться или взять паузу. Это ещё не согласие на условия работы.')] },
  hypothesis: { group: 'Совместное обсуждение', short: 'Предположение', title: 'Хочу проверить своё предположение. Что в нём соответствует вашей ситуации, а что нет?', hint: 'Сначала обозначу, на что опираюсь и какую версию предлагаю. Затем запишем ваш отклик. Версия может оказаться неподходящей.', speaker: 'Версия ведущего — для проверки', context: ['why_now', 'episode', 'shared_question'], fields: [textField('hypothesis_basis', 'На какую запись или наблюдение я опираюсь'), textField('hypothesis_text', 'Моё предположение'), textField('hypothesis_reply', 'Ваш отклик и поправки')] },
  advice: { group: 'Совместное обсуждение', short: 'Мнение или совет', title: 'Как моё предварительное мнение соотносится с вашим опытом?', hint: 'Я обозначу основания, предложу свой взгляд и назову, что пока неясно. Затем проверим, полезно ли это вам.', speaker: 'Мнение ведущего и ваш отклик', context: ['shared_question', 'help_expected', 'constraints'], fields: [textField('advice_basis', 'На что я опираюсь'), textField('advice_text', 'Моё предварительное мнение или предложение'), textField('advice_limits', 'Что ещё неясно и где границы этого мнения'), textField('advice_reply', 'Что вы об этом думаете')] },
  process: { group: 'Как идёт разговор', short: 'Ход разговора', title: 'Что в разговоре помогало, а что мешало?', hint: 'Можно поправить тему, темп, вопрос или моё понимание. Возвращаемся к этому, когда это полезно, без обязательной оценки.', speaker: 'Проверяем ход разговора вместе', context: ['today', 'help_expected'], fields: [textField('process_feedback', 'Что помогало, что мешало и где я вас не понял'), textField('process_adjustment', 'Что стоит сохранить или изменить')] },
  knowledge: { group: 'Понимание ситуации', short: 'На что опираемся', title: 'Что мы знаем, как это понимаем и что нужно выяснить?', hint: 'Берём только существенное для текущего вопроса. Рассказ человека, наше объяснение и независимая проверка — разные основания.', speaker: 'Собираем общую картину по необходимости', context: ['shared_question', 'episode', 'tried_result', 'hypothesis_text'], fields: [textField('known_info', 'Что известно и откуда'), textField('interpretation', 'Как мы это пока понимаем'), textField('unknown_info', 'Что ещё нужно выяснить'), textField('unknown_priority', 'Какое неизвестное сейчас влияет на следующий шаг')] },
  outcome: { group: 'Итог встречи', short: 'Что прояснили сегодня', title: 'Что сегодня стало понятнее или было решено?', hint: 'Отделим результат сегодняшнего разговора от того, что ещё предстоит проверить на опыте.', speaker: 'Подводим итог вместе', context: ['today', 'shared_question', 'next_step', 'next_check'], fields: [textField('today_outcome', 'Что сегодня прояснили или решили'), textField('remaining_check', 'Что ещё предстоит проверить на опыте')] },
  orientation: { group: 'Текущая задача', short: 'С чем разбираемся', title: 'Какой вопрос сейчас требует внимания?', hint: 'Выбор направления, осуществление уже выбранного и исследование темы могут требовать разной помощи. Можно назвать свой вариант.', context: ['why_now', 'change', 'shared_question'], fields: [selectField('task_type', 'Что сейчас полезнее'), textField('task_type_details', 'Как вы сами описываете этот вопрос')] },
  timing: { group: 'Границы решения', short: 'Срок и отсрочка', title: 'Когда нужно принять решение и что будет, если пока ничего не менять?', hint: 'У решения может не быть жёсткого срока. Неизвестный срок и неизвестные последствия так и отмечаем.', context: ['shared_question', 'trigger_event', 'constraints'], fields: [textField('decision_deadline', 'К какому сроку или при каком событии требуется решение'), textField('deadline_source', 'Откуда взялся этот срок и что о нём известно'), textField('delay_consequences', 'Что произойдёт, если пока ничего не менять')] },
  clarify: { group: 'Краткая карта вопроса', short: 'С чем идём дальше', title: 'С каким вопросом мы сейчас идём дальше?', hint: 'Проверим общую картину. Неясности можно оставить открытыми. Затем вы сможете назвать вопрос своими словами.', speaker: 'Подводим итог прояснения', context: ['shared_question', 'change', 'decision_deadline'], fields: [textField('participant_question', 'Как вы сами сейчас сформулировали бы свой вопрос'), selectField('clarification_status', 'Что получилось прояснить')] },
  learn_intro: { group: 'Учебная часть', short: 'Зачем этот навык', title: 'Хотите попробовать самостоятельно формулировать такие вопросы?', hint: 'Можно взять только нужное объяснение или пройти пример и пробу. Эту часть можно провести отдельно от знакомства.', speaker: 'Выбираем обучение по потребности', context: ['shared_question'], fields: [selectField('learning_choice', 'Как вам сейчас полезнее')] },
  learn_example: { group: 'Учебная часть', short: 'Разобранный пример', title: 'Посмотрим, как из большой темы получается конкретный вопрос.', hint: 'Это учебная ситуация. Разбор показывает ход рассуждения и оставляет неизвестное неизвестным.', context: [], fields: [] },
  learn_own: { group: 'Учебная часть', short: 'Ваша попытка', title: 'Как вы сами сейчас сформулировали бы свой вопрос?', hint: 'Можно опираться на свой рассказ и пример. После попытки разберём, что получилось и где понадобилась помощь.', context: ['why_now', 'change', 'trigger_event', 'preserve', 'decision_deadline'], fields: [textField('learn_own_attempt', 'Ваша формулировка и её границы'), selectField('learn_own_help', 'Как получилась эта формулировка'), textField('learn_own_feedback', 'Что получилось и что стоит уточнить')] },
  learn_case: { group: 'Учебная часть', short: 'Новый случай', title: 'Попробуйте уточнить вопрос в другой ситуации.', hint: 'Это отдельный учебный случай. Допустимы разные формулировки, если они опираются на условие.', context: [], fields: [textField('learn_case_question', 'Какой вопрос здесь нужно решить'), textField('learn_case_facts', 'Что произошло и что известно о сроке'), textField('learn_case_change', 'Желаемое изменение и предлагаемый способ'), textField('learn_case_limits', 'Что сохраняется и что ещё неизвестно')] },
  learn_feedback: { group: 'Учебная часть', short: 'Разбор попытки', title: 'Что получилось в этой попытке и какая помощь понадобилась?', hint: 'Смотрим на конкретные действия. Если что-то не проверяли, так и отмечаем.', context: [], fields: [...['question', 'goal_method', 'event', 'boundary', 'unknown'].flatMap(key => [selectField(`learn_${key}_level`, ''), textField(`learn_${key}_evidence`)]), textField('learn_feedback', 'Что удалось и что попробуем улучшить')] },
  learn_transfer: { group: 'Учебная часть', short: 'Применить в жизни', title: 'Где этот способ может пригодиться вам дальше?', hint: 'Выберем подходящую ситуацию и способ вернуться к опыту. Одна удачная попытка ещё не показывает применение в любых обстоятельствах.', context: ['learn_own_attempt', 'learn_feedback'], fields: [textField('learn_transfer_action', 'В какой ситуации и что попробуете'), textField('learn_transfer_when', 'Когда или при каком условии'), textField('learn_transfer_check', 'Как поймёте, что способ помог'), textField('learn_open', 'Что ещё осталось неясным')] },
};
const agreementBlocks = [
  { id: 'offer', title: 'Что предлагаю', purpose: 'Чтобы понять, какую задачу решаем на этом этапе и что в него входит.', fields: [textField('agreement_stage_task', 'Задача именно этого этапа'), textField('agreement_stage_result', 'Ожидаемый результат этапа'), textField('terms_scope', 'Предлагаемый объём работы'), textField('agreement_stage_limits', 'Границы: что в этот этап не входит')] },
  { id: 'work', title: 'Как работаем', purpose: 'Чтобы каждый понимал свой вклад, нагрузку и полную цену до решения о начале.', fields: [textField('agreement_leader_actions', 'Что беру на себя я, ведущий'), textField('agreement_client_actions', 'Что берёте на себя вы, участник'), textField('agreement_load', 'Какая нагрузка потребуется каждому'), textField('terms_schedule', 'Срок и ритм работы'), textField('agreement_required', 'Без каких условий работа не получится'), textField('agreement_preferred', 'Какие условия желательны, но не обязательны'), textField('terms_price', 'Цена предлагаемого этапа', 'Уточняем полную сумму, что в неё входит и что оплачивается отдельно. Если цена неизвестна, так и записываем.'), textField('terms_payment', 'Порядок оплаты')], optional: [textField('agreement_data', 'Какие данные нужны, кто получит доступ и что сохраняется'), textField('agreement_third_parties', 'Кто ещё участвует и о чём нужно договориться с ним')] },
  { id: 'review', title: 'Польза и пересмотр', purpose: 'Чтобы заранее понимать, как проверим пользу и что делать, если условия или задача изменятся.', fields: [textField('terms_review', 'Как и когда проверим пользу'), textField('terms_change', 'Как можно пересмотреть или завершить работу'), textField('agreement_postponement', 'Как договариваемся о переносах и паузах')] },
  { id: 'decisions', title: 'Решение', purpose: 'Чтобы проверить понимание, оставить неясности открытыми и отдельно услышать решение каждого.', fields: [textField('agreement_client_understanding', 'Как вы поняли предложение своими словами'), textField('agreement_corrections', 'Что нужно поправить'), textField('agreement_unknown', 'Что ещё нужно выяснить до решения'), selectField('agreement_client_decision', 'Ваше решение по записанному предложению'), selectField('agreement_leader_decision', 'Моё решение как ведущего')] },
];
extraViews.agreement.fields = [...agreementBlocks.flatMap(block => [...block.fields, ...(block.optional || [])]), selectField('agreement_status', 'Общая отметка в записи')];

const $ = id => document.getElementById(id);
const dom = (tag, className, text) => { const element = document.createElement(tag); if (className) element.className = className; if (text !== undefined) element.textContent = text; return element; };
let state = { sessions: [], currentId: '', summary: false, mode: 'guided', followupId: '' };
let persistenceBlocked = false;

// Сетевые задачи и код доступа живут отдельно от сохраняемой записи встречи.
const AI_CODE_KEY = 'first-meeting-sheet:access-code';
const aiJobs = new Map();
const aiAttempts = new Map();
const aiQuestions = new Map();
const aiMessages = new Map();
let aiCode = '';
try { aiCode = sessionStorage.getItem(AI_CODE_KEY) || ''; } catch { /* Код можно держать только до закрытия страницы. */ }
function shownFieldQuestion(key) { return aiQuestions.get(`${current().id}:${key}`) || currentQuestion(); }
function aiStatus(message = '') { aiMessages.set(current().id, message); for (const id of ['ai-status', 'ai-summary-status']) { const element = $(id); if (element) { element.textContent = message; element.hidden = !message; } } }
function stopAiRequests() { for (const [id, job] of aiJobs) { job.controller.abort(); aiMessages.set(id, 'Запрос остановлен. Можно подготовить новый черновик.'); } aiJobs.clear(); }
function syncAiSettings() {
  if (!$('ai-consent') || !current()) return;
  $('ai-consent').checked = current().aiConsent;
  $('ai-code-state').textContent = aiCode ? 'Код сохранён до закрытия вкладки.' : 'Код пока не указан. Помощник выключен.';
  aiStatus(aiMessages.get(current().id) || '');
}
function setupAiSettings(parent) {
  const box = dom('details', 'ai-settings'); box.id = 'ai-settings'; box.append(dom('summary', '', 'Помощник'));
  box.append(dom('p', '', 'Помощник предлагает вопрос и короткие подсказки для каждого экрана по записям текущей встречи. Вы обсуждаете их и сами решаете, что принять. Он не заполняет ответы без вашего действия.'));
  const label = dom('label', '', 'Код доступа ведущего');
  const input = dom('input'); input.id = 'ai-access-code'; input.type = 'password'; input.autocomplete = 'off'; input.maxLength = 1024; label.append(input); box.append(label);
  const actions = dom('div', 'ai-draft-actions');
  const save = dom('button', 'button button-light', 'Сохранить код'); save.type = 'button';
  save.addEventListener('click', () => {
    const value = input.value.trim();
    if (!value || /[\r\n]/.test(value)) { aiStatus('Введите код доступа без переноса строки.'); return; }
    stopAiRequests(); aiCode = value; input.value = '';
    try { sessionStorage.setItem(AI_CODE_KEY, aiCode); } catch { aiStatus('Код доступен до обновления страницы: браузер не разрешил сохранить его на время вкладки.'); }
    syncAiSettings(); refreshAiPanels();
    aiAttempts.get(current().id)?.signatures.clear(); ensureAiCard();
  });
  const clear = dom('button', 'text-button', 'Убрать код'); clear.type = 'button';
  clear.addEventListener('click', () => { stopAiRequests(); aiCode = ''; input.value = ''; try { sessionStorage.removeItem(AI_CODE_KEY); } catch {} syncAiSettings(); refreshAiPanels(); });
  actions.append(save, clear); box.append(actions, Object.assign(dom('p', 'field-hint'), { id: 'ai-code-state' }));
  const consentLabel = dom('label', 'ai-consent-label'); const consent = dom('input'); consent.type = 'checkbox'; consent.id = 'ai-consent';
  consentLabel.append(consent, dom('span', '', 'Мы договорились использовать помощника'));
  box.append(consentLabel, dom('p', 'field-hint', 'При подготовке подсказки в Supabase и OpenRouter отправляются записи всей текущей встречи: форма знакомства, ваш вопрос, обсуждение помощи, условий и итога, записанные варианты и уточняющие ответы. Черновики помощника не отправляются как ваши ответы. Код доступа передаётся только серверу.'));
  consent.addEventListener('change', () => {
    stopAiRequests(); current().aiConsent = consent.checked; persist();
    aiStatus(consent.checked ? (aiCode ? 'Помощник включён для этой встречи. Подсказки появятся при переходе на следующий экран или по вашей кнопке.' : 'Договорённость отмечена. Для отправки запроса ещё нужен код доступа.') : 'Помощник выключен. Новые записи никуда не отправляются.');
    refreshAiPanels();
    if (consent.checked) aiAttempts.get(current().id)?.signatures.clear();
    ensureAiCard();
  }); parent.append(box);
}
function activeAiScreen() { return state.summary ? 'summary' : state.mode === 'guided' ? guidedSpec().id : ''; }
function cardMount() { return state.summary ? $('ai-summary-panel') : $('ai-card-panel'); }
function canRequestCard() { return current()?.aiConsent && aiCode && !!SCREEN_SCHEMA[activeAiScreen()]; }
function cardPlan() { return { sessionId: current().id, screenId: activeAiScreen(), fingerprint: cardFingerprint(current()) }; }
function ensureAiCard() {
  const screenId = activeAiScreen();
  if (!canRequestCard() || ['welcome', 'about_you'].includes(screenId) || isCardCurrent(current(), screenId) || !collectCardContext(current()).length) return;
  void prepareAiDrafts(cardPlan());
}
async function prepareAiDrafts(plan, manual = false) {
  if (current().id !== plan.sessionId || !current().aiConsent) return;
  if (!aiCode) { aiStatus('Сначала сохраните код доступа в меню «Встреча» → «Помощник».'); return; }
  if (cardFingerprint(current()) !== plan.fingerprint) return;
  const running = aiJobs.get(plan.sessionId);
  if (running) { running.queued = { plan, manual }; return; }
  const signature = JSON.stringify([plan.fingerprint, plan.screenId]);
  const attempts = aiAttempts.get(plan.sessionId) || { signatures: new Set(), count: 0, at: 0 };
  if (!manual && attempts.signatures.has(signature)) return;
  if (attempts.count >= 80) { aiStatus('Для этой встречи уже было много запросов. Продолжим с имеющимися записями.'); return; }
  if (manual && Date.now() - attempts.at < 3000) { aiStatus('Подождите несколько секунд перед следующим запросом.'); return; }
  let built;
  try { built = buildCardRequest(current(), plan.screenId, { requestId: crypto.randomUUID() }); }
  catch (error) { aiStatus(error.message); return; }
  attempts.signatures.add(signature); attempts.count++; attempts.at = Date.now(); aiAttempts.set(plan.sessionId, attempts);
  const job = { controller: new AbortController(), requestId: built.request.requestId, queued: null }; aiJobs.set(plan.sessionId, job);
  aiStatus('Помощник готовит подсказку. Можно продолжать разговор.'); refreshAiPanels();
  try {
    const response = await requestDrafts(built.request, aiCode, { signal: job.controller.signal });
    if (aiJobs.get(plan.sessionId) !== job || current().id !== plan.sessionId || !current().aiConsent || !aiCode) return;
    if (cardFingerprint(current()) !== built.contextFingerprint) { aiStatus('Записи изменились. Можно подготовить подсказку по новой записи.'); return; }
    const card = validateCardResponse(response, { session: current(), ...built });
    current().aiCards = { ...current().aiCards, [plan.screenId]: card }; persist();
    aiStatus(activeAiScreen() === plan.screenId ? 'Подсказка готова. Проверьте её вместе с участником.' : '');
    refreshAiPanels();
  } catch (error) {
    if (aiJobs.get(plan.sessionId) === job && current().id === plan.sessionId && current().aiConsent && aiCode && !job.controller.signal.aborted) {
      aiStatus(cardFingerprint(current()) === built.contextFingerprint ? (error.message || 'Помощник сейчас не ответил.') : 'Записи изменились. Можно подготовить подсказку по новой записи.');
    }
  } finally {
    if (aiJobs.get(plan.sessionId) === job) {
      aiJobs.delete(plan.sessionId); refreshAiPanels();
      if (job.queued) void prepareAiDrafts(job.queued.plan, job.queued.manual);
    }
  }
}
function renderAiBasis(parent, basis) {
  if (!basis?.length) return;
  const details = dom('details', 'ai-card-basis'); details.append(dom('summary', '', 'На какие записи опирается подсказка'));
  for (const item of basis) { const source = dom('div', 'ai-draft-source'); source.append(dom('p', 'ai-draft-source-label', FIELD_SCHEMA[item.key]?.label || 'Запись текущего разговора'), dom('blockquote', 'ai-draft-quote', item.quote)); details.append(source); }
  parent.append(details);
}
function aiReadiness({ consent, hasCode, hasContext, screenId, busy, hasCard }) {
  if (!consent) return { state: 'off', title: 'Помощник выключен', text: 'Чтобы получать подсказки, откройте настройки и отметьте договорённость об использовании помощника.', settings: true };
  if (!hasCode) return { state: 'code', title: 'Нужен код ведущего', text: 'Договорённость отмечена. Сохраните код доступа в настройках помощника.', settings: true };
  if (!hasContext || ['welcome', 'about_you'].includes(screenId)) return { state: 'waiting', title: 'Помощник готов к разговору', text: 'Запишите и отправьте ответ. Подсказки учитывают отправленные записи; набранный текст до отправки остаётся черновиком.', settings: false };
  if (busy) return { state: 'busy', title: 'Помощник готовит подсказку', text: 'Можно продолжать писать: ваш текст останется в поле.', settings: false };
  if (hasCard) return { state: 'ready', title: 'Подсказка по разговору готова', text: '', settings: false };
  return { state: 'ready', title: 'Помощник включён', text: 'Учитывает отправленные записи этой встречи. Подсказку можно подготовить кнопкой ниже.', settings: false };
}
function openAiSettings() {
  $('facilitator-menu').open = true; $('ai-settings').open = true;
  (current().aiConsent ? $('ai-access-code') : $('ai-consent')).focus({ preventScroll: true });
}
function renderAiReadiness(mount, screenId, card) {
  const readiness = aiReadiness({ consent: current().aiConsent, hasCode: !!aiCode, hasContext: !!collectCardContext(current()).length, screenId, busy: aiJobs.has(current().id), hasCard: !!card });
  const indicator = dom('section', 'ai-readiness'); indicator.dataset.state = readiness.state;
  indicator.append(dom('p', 'ai-readiness-title', readiness.title));
  if (readiness.text) indicator.append(dom('p', 'ai-readiness-text', readiness.text));
  if (readiness.settings) { const button = dom('button', 'text-button', 'Настроить помощника'); button.type = 'button'; button.addEventListener('click', openAiSettings); indicator.append(button); }
  mount.append(indicator);
}
function renderAiCard() {
  const mount = cardMount(); if (!mount) return;
  mount.replaceChildren();
  const screenId = activeAiScreen();
  if (!screenId) return;
  const card = SCREEN_SCHEMA[screenId] && isCardCurrent(current(), screenId) ? current().aiCards[screenId] : null;
  renderAiReadiness(mount, screenId, card);
  if (['welcome', 'about_you'].includes(screenId)) return;
  if (card) {
    const panel = dom('section', 'ai-card-guidance'); panel.setAttribute('aria-label', 'Подсказка по вашему разговору');
    panel.append(dom('h3', 'ai-draft-title', 'Подсказка по вашему разговору'), dom('p', 'ai-draft-note', 'Предложение помощника. Обсудите и поправьте, если оно не подходит.'));
    if (card.explanation && !/[?？]/.test(card.explanation)) panel.append(dom('p', 'ai-card-explanation', card.explanation));
    const statements = (card.hints || []).filter(hint => !/[?？]/.test(hint));
    if (statements.length) { const hints = dom('ul', 'ai-card-hints'); for (const hint of statements) hints.append(dom('li', '', hint)); panel.append(hints); }
    if (!state.summary && card.question && card.question !== chatQuestion() && (chatKey() || guidedSpec().input === 'free')) {
      const input = $(`answer-${chatKey() || 'chat-free'}`); const use = dom('button', 'text-button', 'Уточнить вопрос'); use.type = 'button';
      use.disabled = !!chatEditingTurnId || !!input?.value.trim() || !!(chatKey() && current().answers[chatKey()].trim());
      use.addEventListener('click', () => showAiQuestion(card.question, chatKey())); panel.append(use);
    }
    renderAiBasis(panel, card.basis); mount.append(panel);
  }
  if (current().aiConsent && aiCode) {
    const button = dom('button', 'text-button ai-prepare', aiJobs.has(current().id) ? 'Помощник готовит подсказку…' : card ? 'Обновить подсказку по разговору' : 'Подготовить подсказку по разговору');
    button.type = 'button'; button.disabled = aiJobs.has(current().id);
    button.addEventListener('click', () => void prepareAiDrafts(cardPlan(), true)); mount.append(button);
  }
}
function applyAiAnswer(key, accept) {
  const input = $(`answer-${key}`);
  if (!input || input.value.trim() || current().answers[key].trim()) throw new Error('В поле уже есть запись. Черновик её не заменит.');
  if (state.mode === 'guided') {
    const screenId = guidedSpec().id;
    const card = isCardCurrent(current(), screenId) ? current().aiCards[screenId] : null;
    const draft = card?.drafts?.[key] || current().aiDrafts[key];
    if (!draft?.text?.trim()) throw new Error('Этот черновик больше недоступен.');
    const source = card?.drafts?.[key] ? { kind: 'card', screenId, key, card: structuredClone(card) } : { kind: 'legacy', key, draft: structuredClone(draft) };
    current().chatDrafts[chatDraftKey()] = { text: draft.text, source, question: chatQuestion(), origin: chatQuestionOrigin() }; input.value = draft.text; grow(input); persist(); input.focus();
    aiStatus('Черновик перенесён в поле. Обсудите и поправьте текст; ответ запишется только после «Отправить».'); return;
  }
  const original = current();
  const previous = { previousText: original.answers.shared_question, previousStatus: original.answers.question_status, previousReason: original.answers.question_change_reason };
  const question = shownFieldQuestion(key);
  let accepted = accept(original);
  if (AGREEMENT_FIELDS.includes(key)) accepted = { ...updateAgreementAnswer(original, key, accepted.answers[key]), aiCards: accepted.aiCards, aiDrafts: accepted.aiDrafts };
  replaceCurrent(accepted); current().answerPrompts[key] = question;
  if (key === 'shared_question') {
    current().answers.question_status = ''; current().answers.question_change_reason = '';
    replaceCurrent(saveQuestionVersion(current(), previous));
  }
  for (const other of ['question_status', 'question_change_reason', 'agreement_status', 'agreement_client_decision', 'agreement_leader_decision', 'agreement_client_understanding']) {
    const element = $(`answer-${other}`); if (element) element.value = current().answers[other];
  }
  input.value = current().answers[key]; grow(input); persist(); renderContext();
  aiStatus('Черновик принят в запись. Проверьте его вместе и при необходимости поправьте.');
}
function showAiQuestion(question, key) {
  const input = $(`answer-${key || 'chat-free'}`);
  if (chatEditingTurnId || !input || input.value.trim() || (key && current().answers[key].trim())) { aiStatus('В поле уже есть текст. Сохраним вопрос, к которому вы начали отвечать.'); return; }
  aiQuestions.set(`${current().id}:${key || '@' + guidedSpec().id}`, question);
  current().chatDrafts[chatDraftKey()] = { text: input.value, source: chatDraft()?.source || null, question, origin: 'ai' };
  persist();
  $('chat-question').textContent = question; $('question-title').textContent = question; $('chat-speaker').textContent = 'Уточнение с помощью ИИ';
  refreshAiPanels(); input.focus();
}
function renderCardFieldPanel(key, screenId, mount) {
  const card = SCREEN_SCHEMA[screenId] && isCardCurrent(current(), screenId) ? current().aiCards[screenId] : null;
  const draft = card?.drafts?.[key];
  if (!draft || draft.status !== 'suggested') return false;
  const panel = dom('section', 'ai-draft-panel'); panel.append(dom('h3', 'ai-draft-title', 'Черновик записи'), dom('p', 'ai-draft-note', 'Это текст помощника. Сначала проверьте его вместе с человеком, чьи слова записываем.'));
  if (draft.text) panel.append(dom('p', 'ai-draft-text', draft.text));
  renderAiBasis(panel, draft.basis);
  const actions = dom('div', 'ai-draft-actions');
  const add = (label, callback) => { const button = dom('button', 'button button-light', label); button.type = 'button'; button.addEventListener('click', () => { try { callback(); } catch (error) { aiStatus(error.message); } }); actions.append(button); };
  if (draft.text?.trim()) add('Взять за основу ответа', () => applyAiAnswer(key, session => acceptCardDraft(session, screenId, key)));
  if (draft.question) add('Уточнить вопрос', () => showAiQuestion(draft.question, key));
  add('Убрать черновик', () => { replaceCurrent(rejectCardDraft(current(), screenId, key)); persist(); });
  panel.append(actions); mount.append(panel); return true;
}
function refreshAiPanels() {
  if (!current()) return;
  renderAiCard();
  if (state.mode !== 'guided' || state.summary) return;
  const screenId = guidedSpec().id;
  document.querySelectorAll('[data-ai-field]').forEach(mount => {
    const key = mount.dataset.aiField; mount.replaceChildren();
    const accepted = current().aiDrafts[key]?.status === 'accepted' || Object.values(current().aiCards || {}).some(card => card.drafts?.[key]?.status === 'accepted');
    if (current().answers[key].trim()) { if (accepted) mount.append(dom('p', 'field-hint', 'Эту запись начали с принятого черновика помощника. Можно поправить её своими словами.')); return; }
    if ($(`answer-${key}`)?.value.trim()) { if (chatDraft()?.source) mount.append(dom('p', 'field-hint', 'Черновик в поле ещё не отправлен. Можно исправить его перед записью.')); return; }
    if (renderCardFieldPanel(key, screenId, mount)) return;
    const legacy = current().aiDrafts[key];
    if (legacy?.status === 'suggested' && isDraftCurrent(current(), key)) {
      const panel = dom('section', 'ai-draft-panel'); panel.append(dom('h3', 'ai-draft-title', 'Прежний черновик помощника'));
      if (legacy.text) panel.append(dom('p', 'ai-draft-text', legacy.text)); renderAiBasis(panel, legacy.basis);
      const actions = dom('div', 'ai-draft-actions');
      if (legacy.text.trim()) { const use = dom('button', 'button button-light', 'Взять за основу ответа'); use.type = 'button'; use.addEventListener('click', () => { try { applyAiAnswer(key, session => acceptDraft(session, key)); } catch (error) { aiStatus(error.message); } }); actions.append(use); }
      if (legacy.question) { const question = dom('button', 'text-button', 'Уточнить вопрос'); question.type = 'button'; question.addEventListener('click', () => showAiQuestion(legacy.question, key)); actions.append(question); }
      const reject = dom('button', 'text-button', 'Убрать'); reject.type = 'button'; reject.addEventListener('click', () => { replaceCurrent(rejectDraft(current(), key)); persist(); }); actions.append(reject); panel.append(actions); mount.append(panel);
    }
  });
}

function current() { return state.sessions.find(item => item.id === state.currentId); }
function activeEntry() { return current().qaEntries.find(entry => entry.id === state.followupId); }
function activeSpec() { return state.mode === 'guided' ? { ...guidedSpec(), context: [], fields: guidedSpec().fields || [] } : state.mode === 'followup' && activeEntry() ? { group: 'Уточнение из разговора', title: activeEntry().question, hint: 'Предыдущий вопрос и ответ сохранены. Здесь записываем ответ на это уточнение.', context: ['shared_question'], fields: [] } : extraViews[state.mode] || steps[current().step]; }
function activeKey() { if (state.mode === 'guided') { const key = guidedSpec().fields?.[0]?.key; const index = steps.findIndex(step => step.fields.some(field => field.key === key)); return index >= 0 ? topicKeys[index] : AGREEMENT_FIELDS.includes(key) ? 'agreement' : 'fit_check'; } return state.mode === 'followup' && activeEntry() ? activeEntry().topic : extraViews[state.mode] ? state.mode : topicKeys[current().step]; }
function currentQuestion() { return state.mode === 'guided' ? chatQuestion() : state.mode === 'followup' && activeEntry() ? activeEntry().question : current().prompts[activeKey()] || activeSpec().title; }
function notice(message) { $('notice').textContent = message; $('notice').hidden = !message; }
function say(message) { $('live-message').textContent = message; }
function load() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const raw = JSON.parse(stored);
      if (![1, 2, 3, 4, 5, 6, 7, 8].includes(raw.version) || !Array.isArray(raw.sessions)) throw new Error('Формат сохранённых записей не распознан.');
      state.sessions = raw.sessions.map(item => ({ ...normaliseSession(item), aiConsent: false }));
      state.currentId = state.sessions.some(s => s.id === raw.currentId) ? raw.currentId : state.sessions[0]?.id;
    }
  } catch (error) {
    // При ошибке не затираем существующие записи новым пустым листом.
    persistenceBlocked = true;
    notice('Не удалось открыть прежние записи. Они не перезаписаны. Текущую встречу можно сохранить отдельным файлом.');
  }
  if (!state.sessions.length) { const session = createSession(); state.sessions.push(session); state.currentId = session.id; }
}
function persist() {
  replaceCurrent(invalidateAiCards(invalidateStaleDrafts(current())));
  refreshAiPanels();
  current().updatedAt = new Date().toISOString();
  if (persistenceBlocked) { $('save-status').textContent = 'Сохраните отдельную копию встречи'; return; }
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ version: 8, sessions: state.sessions, currentId: state.currentId }));
    $('save-status').textContent = 'Сохранено в этом браузере';
  } catch (error) {
    $('save-status').textContent = 'Не удалось сохранить в браузере';
    notice('В браузере не удалось сохранить изменения. Скачайте копию через «Файл встречи», чтобы не потерять запись.');
  }
}
function hasAnswer(index) { return steps[index].fields.some(field => current().answers[field.key]?.trim()); }
function grow(textarea) { textarea.style.height = 'auto'; textarea.style.height = `${Math.max(textarea.classList.contains('short') ? 85 : 140, textarea.scrollHeight + 3)}px`; }
function selectedLabel(key, value) { return choices[key]?.find(([option]) => option === value)?.[1] || value; }
function replaceCurrent(session) { state.sessions[state.sessions.findIndex(item => item.id === state.currentId)] = session; }
function hasActiveAnswers() { return state.mode === 'followup' ? !!activeEntry()?.answer.trim() : activeSpec().fields.some(field => current().answers[field.key]?.trim()); }
function startNewQuestion(question) {
  const anchor = state.mode === 'followup' ? activeEntry()?.answer || activeEntry()?.anchor || '' : current().anchors[activeKey()] || '';
  const result = addFollowup(current(), { topic: activeKey(), question, anchor });
  replaceCurrent(result.session); state.followupId = result.entryId; state.mode = 'followup'; state.summary = false; persist(); render(); focusCurrentView();
}
function showFollowup(id) { state.followupId = id; state.mode = 'followup'; state.summary = false; render(); focusCurrentView(); }
function applyPromptChange(question, correction = false) {
  if (question.trim() === currentQuestion().trim()) { $('prompt-editor').hidden = true; return; }
  if (state.mode.startsWith('learn_') && !correction) { startNewQuestion(question); return; }
  if (state.mode === 'followup') {
    if (activeEntry().answer.trim()) { startNewQuestion(question); return; }
    activeEntry().question = question; activeEntry().updatedAt = new Date().toISOString();
  } else if (hasActiveAnswers() && !correction) { startNewQuestion(question); return; }
  else if (correction) replaceCurrent(correctPrompt(current(), { topic: activeKey(), question, previousQuestion: currentQuestion(), keys: activeSpec().fields.map(field => field.key) }));
  else current().prompts[activeKey()] = question;
  persist(); renderQuestion(); say('Формулировка сохранена.');
}

function renderNav() {
  const nav = $('steps-nav'); nav.replaceChildren();
  let group = '';
  steps.forEach((step, index) => {
    if (step.group !== group) { nav.append(dom('p', 'group-title', step.group)); group = step.group; }
    const button = dom('button', 'step-nav-button', step.short); button.type = 'button'; button.dataset.step = index;
    if (index === current().step && state.mode === 'topic') { button.classList.add('current'); button.setAttribute('aria-current', 'page'); }
    if (hasAnswer(index)) button.classList.add('recorded');
    button.addEventListener('click', () => go(index)); nav.append(button);
  });
  nav.append(dom('p', 'group-title', 'По необходимости'));
  for (const mode of ['orientation', 'timing', 'clarify', 'fit_check', 'agreement', 'agreement_summary', 'knowledge', 'outcome', 'learn_intro']) {
    const button = dom('button', 'step-nav-button', extraViews[mode].short); button.type = 'button';
    if (state.mode === mode) { button.classList.add('current'); button.setAttribute('aria-current', 'page'); }
    button.addEventListener('click', () => openMode(mode)); nav.append(button);
  }
}
function refreshNavMarks() {
  document.querySelectorAll('[data-step]').forEach(button => button.classList.toggle('recorded', hasAnswer(Number(button.dataset.step))));
}
function renderField(field, parent, compact = false) {
  const wrapper = dom('div', `answer-field${compact ? ' compact' : ''}`);
  if (state.mode === 'guided' && !field.select && FIELD_SCHEMA[field.key]?.draftable) { const mount = dom('div', 'ai-draft-mount'); mount.dataset.aiField = field.key; wrapper.append(mount); }
  const label = dom('label', '', field.label); label.htmlFor = `answer-${field.key}`; wrapper.append(label);
  const input = document.createElement(field.select ? 'select' : 'textarea'); input.id = `answer-${field.key}`; input.name = field.key;
  if (field.select) field.select.forEach(([value, text]) => { const option = dom('option', '', text); option.value = value; input.append(option); });
  else { input.rows = compact ? 2 : 4; input.maxLength = 12000; input.placeholder = 'Запишем здесь'; input.spellcheck = true; if (compact) input.classList.add('short'); }
  input.value = current().answers[field.key];
  const boundQuestion = current().answerPrompts[field.key];
  let sourceNote = null;
  if (input.value.trim() && boundQuestion && boundQuestion !== currentQuestion()) { sourceNote = dom('p', 'answer-source', `Записано к прежнему вопросу: ${boundQuestion}`); wrapper.append(sourceNote); }
  let questionBaseline = { previousText: current().answers.shared_question, previousStatus: current().answers.question_status, previousReason: current().answers.question_change_reason };
  let beganQuestionEdit = false;
  if (field.key === 'shared_question') input.addEventListener('focus', () => {
    questionBaseline = { previousText: current().answers.shared_question, previousStatus: current().answers.question_status, previousReason: current().answers.question_change_reason };
    beganQuestionEdit = false;
  });
  if (field.hint) { const hint = dom('p', 'field-hint', field.hint); hint.id = `hint-${field.key}`; input.setAttribute('aria-describedby', hint.id); wrapper.append(input, hint); }
  else wrapper.append(input);
  input.addEventListener(field.select ? 'change' : 'input', () => {
    if (field.key === 'shared_question') {
      const changed = input.value !== questionBaseline.previousText;
      if (changed && !beganQuestionEdit) {
        current().answers.question_change_reason = '';
        const reasonInput = $('answer-question_change_reason'); if (reasonInput) reasonInput.value = '';
        beganQuestionEdit = true;
      }
      current().answers.question_status = changed ? '' : questionBaseline.previousStatus;
      const statusInput = $('answer-question_status'); if (statusInput) statusInput.value = current().answers.question_status;
    }
    if (AGREEMENT_FIELDS.includes(field.key)) {
      const historySize = current().agreementHistory.length;
      replaceCurrent(updateAgreementAnswer(current(), field.key, input.value));
      if (current().agreementHistory.length > historySize) {
        for (const key of ['agreement_status', 'agreement_client_decision', 'agreement_leader_decision', 'agreement_client_understanding']) {
          const element = $(`answer-${key}`); if (element) element.value = current().answers[key];
        }
        notice('Предложение изменилось. Прежняя редакция сохранена; понимание и решения по новым условиям нужно записать заново.');
        renderAgreementHistory();
      }
    } else current().answers[field.key] = input.value;
    current().answerPrompts[field.key] = shownFieldQuestion(field.key);
    if (sourceNote) { sourceNote.remove(); sourceNote = null; }
    persist(); refreshNavMarks(); renderContext();
    if (!field.select) grow(input);
    if (field.key === 'question_status') recordQuestionVersion();
    if (field.key === 'learning_choice') renderQuestion();
  });
  if (field.key === 'shared_question') input.addEventListener('change', () => recordQuestionVersion(questionBaseline));
  if (field.key === 'question_change_reason') input.addEventListener('change', () => recordQuestionVersion());
  parent.append(wrapper);
}
function recordQuestionVersion(previous = {}) {
  const index = state.sessions.findIndex(session => session.id === state.currentId);
  state.sessions[index] = saveQuestionVersion(current(), { ...previous, reason: current().answers.question_change_reason });
  persist(); renderQuestionHistory();
}
function renderQuestionHistory(parent) {
  const oldPanel = $('question-history');
  if (!parent && !oldPanel) return;
  const wasOpen = oldPanel?.open || false; oldPanel?.remove();
  const panel = dom('details', 'question-history'); panel.id = 'question-history'; panel.open = wasOpen;
  const history = current().questionHistory;
  panel.append(dom('summary', '', `Как менялось понимание задачи${history.length ? ` · ${history.length}` : ''}`));
  if (!history.length) panel.append(dom('p', 'fields-note', 'Версии появятся после записи или уточнения формулировки.'));
  history.slice().reverse().forEach((entry, reversedIndex) => {
    const version = dom('section', 'question-version');
    const date = new Intl.DateTimeFormat('ru-RU', { dateStyle: 'short', timeStyle: 'short', timeZone: 'Europe/Moscow' }).format(new Date(entry.at));
    version.append(dom('h3', '', `Версия ${history.length - reversedIndex} · ${date}`), dom('p', '', entry.text));
    if (entry.reason) version.append(dom('p', 'version-reason', `Почему уточнили: ${entry.reason}`));
    version.append(dom('p', 'version-status', entry.status ? selectedLabel('question_status', entry.status) : 'Оценка этой версии не отмечена'));
    if (entry.text !== current().answers.shared_question) {
      const restore = dom('button', 'text-button', 'Взять эту формулировку'); restore.type = 'button';
      restore.addEventListener('click', () => {
        const previous = { previousText: current().answers.shared_question, previousStatus: current().answers.question_status, previousReason: current().answers.question_change_reason };
        current().answers.shared_question = entry.text; current().answers.question_status = '';
        current().answers.question_change_reason = `Вернулись к формулировке от ${date}`;
        recordQuestionVersion(previous); renderQuestion();
      }); version.append(restore);
    }
    panel.append(version);
  });
  (parent || $('answer-fields')).append(panel);
}
function renderOptionalFields(parent, title, fields) {
  const panel = dom('details', 'optional-fields'); panel.append(dom('summary', '', title));
  panel.open = fields.some(field => current().answers[field.key]?.trim());
  fields.forEach(field => renderField(field, panel, true)); parent.append(panel);
}
function renderClarificationMap(parent) {
  const a = current().answers;
  const card = dom('section', 'clarification-map');
  const rows = [
    ['Текущий вопрос', a.shared_question, () => go(8)],
    ['После чего он возник', a.trigger_event, () => go(2)],
    ['Какого изменения хочется', a.change, () => go(3)],
    ['Что сохраняем', a.preserve, () => go(5)],
    ['Кто принимает решение', a.decision_owner, () => go(5)],
    ['Срок или условие решения', [a.decision_deadline, a.deadline_source ? `Источник срока: ${a.deadline_source}` : ''].filter(Boolean).join('\n'), () => openMode('timing')],
    ['Что будет при паузе', a.delay_consequences, () => openMode('timing')],
  ];
  if (a.unknown_info.trim()) rows.push(['Что ещё неизвестно', a.unknown_info, () => openMode('knowledge')]);
  rows.forEach(([label, value, edit]) => {
    const row = dom('div', 'clarification-row'); const content = dom('div'); content.append(dom('h3', '', label), dom('p', value.trim() ? '' : 'context-empty', value.trim() || 'Пока не записано'));
    const button = dom('button', 'text-button', 'Уточнить'); button.type = 'button'; button.addEventListener('click', edit); row.append(content, button); card.append(row);
  });
  parent.append(card);
}
function renderAgreementLinks(parent) {
  const links = dom('div', 'inline-actions agreement-actions');
  const edit = dom('button', 'button button-light', 'Обсудить условия работы'); edit.type = 'button'; edit.addEventListener('click', () => openMode('agreement'));
  const summary = dom('button', 'button button-light', 'Посмотреть предложение целиком'); summary.type = 'button'; summary.addEventListener('click', () => openMode('agreement_summary'));
  links.append(edit, summary); parent.append(links);
}

function renderAgreementHistory(parent) {
  const old = $('agreement-history');
  if (!parent && !old) return;
  const opened = old?.open || false; old?.remove();
  const details = dom('details', 'agreement-history'); details.id = 'agreement-history'; details.open = opened;
  details.append(dom('summary', '', `Прежние редакции условий · ${current().agreementHistory.length}`));
  if (!current().agreementHistory.length) details.append(dom('p', 'fields-note', 'Если условия изменятся после проверки понимания или решения, прежняя редакция останется здесь.'));
  current().agreementHistory.slice().reverse().forEach(entry => {
    const item = dom('section', 'question-version');
    const at = new Intl.DateTimeFormat('ru-RU', { dateStyle: 'short', timeStyle: 'short', timeZone: 'Europe/Moscow' }).format(new Date(entry.at));
    item.append(dom('h3', '', `Прежняя редакция · ${at}`), dom('p', 'fields-note', 'Эти ответы и отметки относятся к прежней редакции, а не к новым условиям.'));
    for (const key of AGREEMENT_FIELDS) if (entry.answers[key]?.trim()) item.append(dom('p', '', `${FIELD_LABELS[key]}: ${selectedLabel(key, entry.answers[key])}`));
    details.append(item);
  });
  (parent || $('answer-fields')).append(details);
}

function renderAgreement(parent) {
  const context = dom('details', 'agreement-context');
  context.append(dom('summary', '', 'На что опираемся из предыдущего разговора'), dom('p', 'fields-note', 'Это исходные записи. Они не становятся условиями конкретного этапа автоматически.'));
  for (const key of ['participant_question', 'shared_question', 'help_expected', 'help_informed_preference', 'proposal_result', 'helper_fit_reason', 'fit_feedback']) {
    if (current().answers[key].trim()) { const item = dom('div', 'summary-item'); item.append(dom('h4', '', FIELD_LABELS[key]), dom('p', '', current().answers[key])); context.append(item); }
  }
  parent.append(context);
  for (const block of agreementBlocks) {
    const details = dom('details', 'agreement-block'); details.id = `agreement-block-${block.id}`; details.open = ['offer', 'decisions'].includes(block.id);
    details.append(dom('summary', '', block.title), dom('p', 'purpose-note', `Зачем: ${block.purpose}`));
    block.fields.forEach(field => renderField(field, details, true));
    if (block.optional) renderOptionalFields(details, 'Если нужны данные или участие других людей', block.optional);
    if (block.id === 'decisions') {
      details.append(dom('p', 'fields-note', 'Ваше решение и моё решение записываем отдельно. Подходящая помощь и прежняя общая отметка не означают, что мы оба приняли эти условия.'));
      renderOptionalFields(details, 'Общая отметка в записи', [selectField('agreement_status', 'Общая отметка о договорённости')]);
    }
    parent.append(details);
  }
  renderAgreementLinks(parent); renderAgreementHistory(parent);
}

function renderAgreementOverview(parent, includeActions = true) {
  const a = current().answers;
  const overview = dom('section', 'agreement-overview');
  overview.append(dom('h3', '', 'Предложение конкретного этапа'), dom('p', 'fields-note', 'Здесь только записанные условия. Неизвестное и решения каждой стороны остаются видимыми.'));
  const groups = [
    ['Этап и результат', ['agreement_stage_task', 'agreement_stage_result', 'terms_scope', 'agreement_stage_limits']],
    ['Взаимные обязательства', ['agreement_leader_actions', 'agreement_client_actions', 'agreement_load', 'agreement_required', 'agreement_preferred']],
    ['Срок и цена', ['terms_schedule', 'terms_price', 'terms_payment']],
    ['Проверка и выход', ['terms_review', 'terms_change', 'agreement_postponement']],
    ['Понимание и открытые вопросы', ['agreement_client_understanding', 'agreement_corrections', 'agreement_unknown']],
    ['Отдельные решения', ['agreement_client_decision', 'agreement_leader_decision']],
    ['Следующий шаг', ['next_step', 'next_when', 'next_check']],
  ];
  if (a.agreement_data.trim() || a.agreement_third_parties.trim()) groups.splice(4, 0, ['Данные и другие участники', ['agreement_data', 'agreement_third_parties']]);
  const grid = dom('div', 'agreement-overview-grid');
  for (const [heading, keys] of groups) {
    const block = dom('section', 'agreement-overview-group'); block.append(dom('h4', '', heading));
    for (const key of keys) {
      const row = dom('div', 'agreement-overview-row'); row.append(dom('span', '', FIELD_LABELS[key]), dom('p', a[key].trim() ? '' : 'context-empty', a[key].trim() ? selectedLabel(key, a[key]) : 'Пока не записано')); block.append(row);
    }
    grid.append(block);
  }
  overview.append(grid);
  if (a.agreement_status) overview.append(dom('p', 'fields-note', `Общая отметка в записи: ${selectedLabel('agreement_status', a.agreement_status)}. Она не заменяет отдельные решения выше.`));
  if (a.agreement_status === 'agreed' && (a.agreement_client_decision !== 'start' || a.agreement_leader_decision !== 'start')) overview.append(dom('p', 'status-callout', 'Есть общая отметка «согласовано», но отдельные решения по этому предложению не подтверждают готовность обоих начать. Уточним, к какой редакции относится отметка.'));
  if (a.agreement_corrections.trim() || a.agreement_unknown.trim()) overview.append(dom('p', 'fields-note', 'Перед началом проверим, разрешены ли записанные поправки и вопросы.'));
  if (includeActions) {
    const links = dom('div', 'inline-actions agreement-actions');
    const edit = dom('button', 'button button-primary', 'Поправить условия или решение'); edit.type = 'button'; edit.addEventListener('click', () => openMode('agreement'));
    const next = dom('button', 'button button-light', 'Обсудить следующий шаг'); next.type = 'button'; next.addEventListener('click', () => go(10)); links.append(edit, next); overview.append(links);
  }
  parent.append(overview);
}

function renderFitContext(parent) {
  const a = current().answers;
  const card = dom('section', 'fit-context');
  card.append(dom('h3', '', 'От чего отталкиваемся'), dom('p', 'fields-note', 'Мы выбираем способ вместе. Вы оцениваете, подходит ли помощь вам; я — могу ли предложить нужный вклад.'));
  const rows = [
    ['Ваша формулировка', a.participant_question, () => openMode('clarify')],
    ['Наше текущее понимание', a.shared_question, () => go(8)],
    ['Ожидание от помощи', a.help_expected, () => go(6)],
    ['Что важно учесть', [a.constraints, a.preserve].filter(Boolean).join('\n'), () => go(5)],
  ];
  for (const [label, value, edit] of rows) {
    const row = dom('div', 'clarification-row');
    const text = dom('div'); text.append(dom('h4', '', label), dom('p', value.trim() ? '' : 'context-empty', value.trim() || 'Пока не записано'));
    const button = dom('button', 'text-button', 'Уточнить'); button.type = 'button'; button.addEventListener('click', edit);
    row.append(text, button); card.append(row);
  }
  parent.append(card);
}

function renderHelpOptions(parent) {
  const section = dom('section', 'help-options');
  section.append(dom('h3', 'fields-heading', 'Какие способы рассматриваем'), dom('p', 'fields-note', 'Записываем реальные варианты без готового набора. Если известен только один, обсудим, какие ещё способы стоит рассмотреть. Ожидаемую пользу и неизвестное отмечаем раздельно.'));
  const blankOption = () => ({ id: globalThis.crypto?.randomUUID?.() || `option-${Date.now()}-${Math.random().toString(36).slice(2)}`, name: '', benefit: '', effort: '', unknown: '' });
  const rows = current().helpOptions.slice();
  while (rows.length < 2) rows.push(blankOption());
  const tableWrap = dom('div', 'help-options-scroll'); tableWrap.tabIndex = 0; tableWrap.setAttribute('role', 'region'); tableWrap.setAttribute('aria-label', 'Сравнение рассматриваемых способов помощи');
  const table = dom('table', 'help-options-table');
  const caption = dom('caption', 'sr-only', 'Вариант, ожидаемая польза, участие и неизвестное'); table.append(caption);
  const header = document.createElement('thead'); const headerRow = document.createElement('tr');
  const columns = [['name', 'Вариант'], ['benefit', 'Что даст'], ['effort', 'Что потребуется от меня'], ['unknown', 'Что пока неизвестно']];
  for (const [, title] of columns) { const th = dom('th', '', title); th.scope = 'col'; headerRow.append(th); }
  header.append(headerRow); table.append(header); const body = document.createElement('tbody'); table.append(body);
  const commitRows = () => {
    // Пустые строки не описывают готовые варианты. Сохраняем порядок при первом вводе.
    for (const option of rows) if (!current().helpOptions.some(saved => saved.id === option.id)) current().helpOptions.push(option);
  };
  const renderRow = (option, index) => {
    const row = document.createElement('tr');
    for (const [key, title] of columns) {
      const cell = document.createElement('td'); const input = document.createElement('textarea');
      input.rows = 3; input.className = 'short'; input.maxLength = key === 'name' ? 2000 : 12000;
      input.value = option[key]; input.placeholder = 'Запишем здесь'; input.setAttribute('aria-label', `${title}, вариант ${index + 1}`);
      input.addEventListener('input', () => { commitRows(); option[key] = input.value; persist(); grow(input); });
      cell.append(input); row.append(cell);
    }
    body.append(row);
  };
  rows.forEach(renderRow); tableWrap.append(table); section.append(tableWrap);
  const add = dom('button', 'button button-light', 'Добавить вариант'); add.type = 'button';
  add.addEventListener('click', () => {
    const option = blankOption(); rows.push(option); commitRows(); persist(); renderRow(option, rows.length - 1);
    body.lastElementChild?.querySelector('textarea')?.focus();
  });
  section.append(add); parent.append(section);
}

function renderFitActions(parent, fromProposal = false) {
  const links = dom('div', 'inline-actions');
  const clarify = dom('button', 'button button-light', 'Вернуться к вопросу'); clarify.type = 'button'; clarify.addEventListener('click', () => openMode('clarify'));
  const next = dom('button', 'button button-primary', fromProposal ? 'Обсудить условия работы' : 'Объяснить конкретное предложение'); next.type = 'button'; next.addEventListener('click', () => fromProposal ? openMode('agreement') : go(9));
  links.append(clarify, next); parent.append(links);
  parent.append(dom('p', 'fields-note', fromProposal ? 'Можно закончить на этом, выбрать другую помощь или взять паузу. Если продолжим, можно вернуться к цели, способу помощи и нашему взаимодействию после первого опыта.' : 'Не обязательно начинать работу вместе. Цена, окончательный объём и условия согласия обсуждаются отдельно.'));
}
function renderContext() {
  const target = $('context-records'); target.replaceChildren();
  const keys = state.mode === 'topic' && current().step === 0
    ? [] : [...new Set(['why_now', ...activeSpec().context])];
  const populated = keys.filter(key => current().answers[key]?.trim());
  if (!populated.length && !current().qaEntries.some(entry => entry.answer.trim())) target.append(dom('p', 'context-empty', 'Здесь будут записи, к которым полезно вернуться.'));
  populated.forEach(key => {
    const record = dom('section', 'context-record');
    const origin = /^(hypothesis|advice|proposal|helper)_/.test(key) ? 'Запись ведущего' : key === 'shared_question' ? 'Совместная формулировка' : key === 'help_role' ? 'Рассматриваемый вклад' : /^learn_/.test(key) ? 'Учебная запись' : 'Запись участника';
    record.append(dom('span', 'record-origin', origin), dom('h3', '', FIELD_LABELS[key]), dom('p', '', selectedLabel(key, current().answers[key])));
    const edit = dom('button', '', 'Уточнить запись'); edit.type = 'button'; edit.addEventListener('click', () => {
      const index = steps.findIndex(step => step.fields.some(field => field.key === key));
      if (index >= 0) go(index);
      else { const extra = Object.entries(extraViews).find(([, spec]) => spec.fields.some(field => field.key === key)); if (extra) openMode(extra[0]); }
    });
    const use = dom('button', 'use-record', 'Вернуться к этому моменту'); use.type = 'button'; use.addEventListener('click', () => {
      current().anchors[activeKey()] = selectedLabel(key, current().answers[key]); persist(); renderAnchor(); $('anchor-note').open = true; $('anchor-text').focus();
    });
    record.append(edit, use); target.append(record);
  });
  current().qaEntries.filter(entry => entry.answer.trim() && entry.id !== (state.mode === 'followup' ? state.followupId : '')).slice(-2).forEach(entry => {
    const record = dom('section', 'context-record'); record.append(dom('span', 'record-origin', 'Уточняющий вопрос и ответ'), dom('h3', '', entry.question), dom('p', '', entry.answer));
    const edit = dom('button', '', 'Вернуться к ответу'); edit.type = 'button'; edit.addEventListener('click', () => showFollowup(entry.id)); record.append(edit); target.append(record);
  });
}
function renderAnchor() {
  const value = current().anchors[activeKey()] || '';
  $('anchor-text').value = value; $('anchor-note').open = !!value.trim();
  $('anchor-summary').textContent = value.trim() ? 'Возвращаемся к этой записи' : 'Выбрать фразу или эпизод для уточнения';
}
function openPromptEditor() {
  $('prompt-input').value = currentQuestion(); $('prompt-editor').hidden = false; $('prompt-input').focus(); grow($('prompt-input'));
  const answered = hasActiveAnswers();
  $('save-prompt').textContent = answered || state.mode.startsWith('learn_') ? 'Задать как новый вопрос' : 'Сохранить вопрос';
  $('prompt-integrity-note').hidden = !answered;
  $('correct-prompt').hidden = state.mode === 'followup' || state.mode.startsWith('learn_') || !answered;
  $('reset-prompt').hidden = state.mode === 'followup';
}
function renderChooser() {
  const chooser = $('topic-choices'); chooser.replaceChildren();
  const introductions = ['Продолжить рассказ', 'Уточнить полезный результат встречи', 'Рассмотреть конкретную ситуацию', 'Уточнить желаемое изменение', 'Разобрать предыдущие попытки', 'Учесть обстоятельства', 'Обсудить ожидания от помощи', 'Ответить на вопросы о моей работе', 'Проверить наше понимание вопроса', 'Обсудить возможную помощь', 'Определить следующий шаг'];
  steps.forEach((step, index) => {
    const button = dom('button', 'topic-choice'); button.type = 'button';
    button.append(dom('span', 'topic-choice-title', introductions[index]), dom('span', 'topic-choice-question', current().prompts[topicKeys[index]] || step.title));
    button.addEventListener('click', () => go(index)); chooser.append(button);
  });
  for (const mode of ['orientation', 'timing', 'clarify', 'fit_check', 'agreement', 'agreement_summary', 'knowledge', 'outcome', 'learn_intro']) {
    const button = dom('button', 'topic-choice'); button.type = 'button';
    button.append(dom('span', 'topic-choice-title', extraViews[mode].short), dom('span', 'topic-choice-question', current().prompts[mode] || extraViews[mode].title));
    button.addEventListener('click', () => openMode(mode)); chooser.append(button);
  }
}
function guidedSpec() {
  return GUIDED_FLOW.find(item => item.id === current().guidedStep) || GUIDED_FLOW[0];
}
function goGuided(id, backwards = false, editingId = '') {
  const next = GUIDED_FLOW.find(item => item.id === id);
  if (!next) return;
  chatEditingTurnId = editingId;
  const previous = guidedSpec().id;
  if (!backwards && next.id !== previous) {
    current().guidedTrail.push(previous);
    if (current().guidedTrail.length > 1000) current().guidedTrail.shift();
  }
  current().guidedStep = next.id;
  state.mode = 'guided'; state.summary = false;
  $('facilitator-menu').open = false;
  persist(); render(); focusCurrentView();
}
function nextGuided() { recordChatAction('continue'); advanceChat(); }
function previousGuided() {
  chatReturnStep = '';
  let id = current().guidedTrail.pop();
  if (!GUIDED_FLOW.some(item => item.id === id)) id = GUIDED_FLOW[Math.max(0, GUIDED_FLOW.indexOf(guidedSpec()) - 1)].id;
  goGuided(id, true);
}
function guidedField(field) {
  return { ...field, select: choices[field.key] };
}
let chatReturnStep = '';
let chatEditingTurnId = '';
function chatTurn(step = guidedSpec()) { return current().chatLog.find(turn => turn.id === chatEditingTurnId && turn.screenId === step.id) || current().chatLog.slice().reverse().find(turn => turn.screenId === step.id); }
function chatKey(step = guidedSpec()) { return step.fields?.[0]?.key || null; }
function chatDraftKey(step = guidedSpec()) { return chatEditingTurnId ? `turn:${chatEditingTurnId}` : step.id; }
function chatDraft(step = guidedSpec()) { return current().chatDrafts[chatDraftKey(step)]; }
function chatQuestion(step = guidedSpec()) { if (chatEditingTurnId && chatTurn(step)) return chatTurn(step).question; return aiQuestions.get(`${current().id}:${chatKey(step) || '@' + step.id}`) || chatDraft(step)?.question || chatTurn(step)?.question || step.title; }
function chatQuestionOrigin(step = guidedSpec()) { if (chatEditingTurnId && chatTurn(step)) return chatTurn(step).origin; return aiQuestions.has(`${current().id}:${chatKey(step) || '@' + step.id}`) ? 'ai' : chatDraft(step)?.origin || chatTurn(step)?.origin || 'template'; }
function advanceChat() {
  const step = guidedSpec();
  const index = GUIDED_FLOW.indexOf(step);
  if (chatReturnStep && chatReturnStep !== step.id) { const back = chatReturnStep; chatReturnStep = ''; goGuided(back, true); return; }
  chatReturnStep = '';
  const next = GUIDED_FLOW.slice(index + 1).find(item => !item.skipInMain);
  if (next) goGuided(next.id); else viewSummary();
}
function recordChatAction(action, answer = '') {
  const step = guidedSpec(); const existing = chatTurn(step);
  replaceCurrent(saveChatTurn(current(), { id: existing?.id || null, screenId: step.id, draftKey: chatDraftKey(step), key: chatKey(step), question: chatQuestion(step), origin: chatQuestionOrigin(step), action, answer, topic: step.phase === 'terms' ? 'agreement' : 'fit_check' }));
  persist();
}
function submitChatAnswer() {
  const step = guidedSpec(); const key = chatKey(step); const input = $(`answer-${key || 'chat-free'}`);
  if (!input) { recordChatAction('continue'); advanceChat(); return; }
  const value = input.value; const existing = chatTurn(step);
  if (!value.trim() && existing?.action !== 'answer') { say('Можно записать ответ или пропустить вопрос.'); input.focus(); return; }
  const original = current(); const draft = chatDraft(step);
  let source = draft?.source ? structuredClone(draft.source) : existing?.answerSource || null;
  let accepted = null;
  if (draft?.source && key && !original.answers[key].trim()) {
    try { accepted = draft.source.kind === 'card' ? acceptCardDraft(original, draft.source.screenId, key) : acceptDraft(original, key); }
    catch { /* Человек может отправить отредактированный текст; устаревший ИИ-ответ сам не принимается. */ }
  }
  if (source?.kind === 'card') source.card.drafts[source.key].status = 'accepted';
  if (source?.kind === 'legacy') source.draft.status = 'accepted';
  let next = saveChatTurn(original, { id: existing?.id || null, screenId: step.id, draftKey: chatDraftKey(step), key, question: chatQuestion(step), answer: value, origin: chatQuestionOrigin(step), action: 'answer', answerSource: source, topic: step.phase === 'terms' ? 'agreement' : 'fit_check' });
  if (accepted) { next.aiCards = accepted.aiCards; next.aiDrafts = accepted.aiDrafts; }
  replaceCurrent(next); persist(); advanceChat();
}
function editChatTurn(turn) {
  const returnStep = guidedSpec().id;
  goGuided(turn.screenId, true, turn.id);
  chatReturnStep = returnStep === turn.screenId ? '' : returnStep;
  const input = $(`answer-${turn.key || 'chat-free'}`); input?.focus();
}
function renderChatPhases() {
  const nav = $('chat-phases'); nav.hidden = false; nav.replaceChildren();
  for (const [id, label] of [['about', 'Знакомство'], ['question', 'Ваш вопрос'], ['help', 'Помощь'], ['terms', 'Условия'], ['outcome', 'Итог']]) {
    const first = GUIDED_FLOW.find(step => step.phase === id && !step.skipInMain); if (!first) continue;
    const button = dom('button', 'chat-phase', label); button.type = 'button';
    const visited = current().chatLog.some(turn => GUIDED_FLOW.find(step => step.id === turn.screenId)?.phase === id && turn.action === 'answer');
    if (visited) { button.classList.add('visited'); button.setAttribute('aria-label', `${label}: уже обсуждали`); }
    if (guidedSpec().phase === id) { button.classList.add('current'); button.setAttribute('aria-current', 'step'); }
    button.addEventListener('click', () => { chatReturnStep = ''; goGuided(first.id); }); nav.append(button);
  }
}
function renderChatHistory() {
  const thread = $('chat-thread'); thread.hidden = false; thread.replaceChildren();
  const logged = new Set(current().chatLog.filter(turn => turn.action === 'answer').map(turn => turn.key));
  const older = Object.keys(FIELD_LABELS).filter(key => current().answers[key].trim() && !logged.has(key));
  const loggedQa = new Set(current().chatLog.map(turn => turn.qaEntryId));
  const olderQa = current().qaEntries.filter(entry => entry.answer.trim() && !loggedQa.has(entry.id));
  if (older.length || olderQa.length) {
    const earlier = dom('details', 'chat-earlier'); earlier.append(dom('summary', '', 'Ранее записано'), dom('p', 'field-hint', 'Это прежние записи. Мы не восстанавливаем по ним последовательность разговора.'));
    for (const key of older) earlier.append(dom('h3', '', FIELD_LABELS[key]), dom('p', '', selectedLabel(key, current().answers[key])));
    for (const entry of olderQa) earlier.append(dom('h3', '', entry.question), dom('p', '', entry.answer));
    thread.append(earlier);
  }
  for (const turn of current().chatLog) {
    const pair = dom('section', 'chat-pair'); pair.dataset.turnId = turn.id;
    const question = dom('div', 'chat-bubble chat-assistant');
    question.append(dom('span', 'chat-origin', turn.origin === 'ai' ? 'Вопрос с помощью ИИ' : 'Ведущий'), dom('p', '', turn.question)); pair.append(question);
    if (turn.action === 'answer' || turn.action === 'choice') {
      const reply = dom('div', 'chat-bubble chat-answer');
      const actor = turn.key ? FIELD_SCHEMA[turn.key]?.actor : '';
      reply.append(dom('span', 'chat-origin', turn.action === 'choice' ? 'Выбрано' : actor === 'ведущий' ? 'Запись ведущего' : actor === 'обсуждение вместе' ? 'Общая запись' : actor === 'учебная запись вместе' ? 'Учебная запись' : 'Запись ответа'), dom('p', '', (turn.key ? selectedLabel(turn.key, turn.answer) : turn.answer) || 'Запись очищена'));
      if (turn.answerSource) reply.append(dom('p', 'chat-provenance', 'Текст начали с черновика помощника и отправили после проверки.'));
      if (turn.key && current().answers[turn.key] !== turn.answer) reply.append(dom('p', 'chat-provenance', `Текущая запись уже изменена: ${selectedLabel(turn.key, current().answers[turn.key]) || 'не заполнено'}. Эта реплика оставлена в истории.`));
      if (turn.action === 'answer' && GUIDED_FLOW.some(step => step.id === turn.screenId)) { const edit = dom('button', 'text-button', 'Поправить запись'); edit.type = 'button'; edit.addEventListener('click', () => editChatTurn(turn)); reply.append(edit); }
      if (turn.revisions.length) {
        const history = dom('details', 'chat-revisions'); history.append(dom('summary', '', 'Прежние редакции'));
        for (const version of turn.revisions) history.append(dom('p', 'chat-old-question', version.question), dom('p', '', version.action === 'skip' ? 'Вопрос пропустили' : (turn.key ? selectedLabel(turn.key, version.answer) : version.answer) || 'Без ответа'));
        reply.append(history);
      }
      if (turn.answerSource) { const sources = turn.answerSource.kind === 'card' ? turn.answerSource.card.drafts[turn.answerSource.key].basis : turn.answerSource.draft.basis; renderAiBasis(reply, sources); }
      pair.append(reply);
    } else if (turn.action === 'skip') pair.append(dom('p', 'chat-skip', 'Вопрос пока пропустили'));
    thread.append(pair);
  }
}
function renderGuidedQuestion() {
  const step = guidedSpec(); const key = chatKey(step); const field = step.fields?.[0];
  $('topic-chooser').hidden = true; $('question-card').hidden = false; $('step-actions').hidden = false;
  $('chat-active').hidden = false; renderChatPhases(); renderChatHistory();
  $('question-card').classList.toggle('chat-correcting', !!chatReturnStep);
  $('step-label').textContent = GUIDED_PHASES[step.phase] || 'Первый разговор';
  $('speaker-label').textContent = step.speaker || 'Обсуждаем вместе';
  $('question-title').textContent = chatQuestion(step);
  $('chat-speaker').textContent = chatQuestionOrigin(step) === 'ai' ? 'Уточнение с помощью ИИ' : step.speaker || 'Обсуждаем вместе';
  $('chat-question').textContent = chatQuestion(step);
  $('chat-explanation').textContent = step.explanation || '';
  $('chat-explanation').hidden = !step.explanation;
  for (const id of ['prompt-editor', 'anchor-note', 'story-invitations', 'opinion-options']) $(id).hidden = true;
  const fields = $('answer-fields'); fields.replaceChildren();
  const acceptsAnswer = !!field || step.input === 'free';
  if (acceptsAnswer) {
    const form = dom('form', 'chat-composer'); form.addEventListener('submit', event => { event.preventDefault(); submitChatAnswer(); });
    const label = dom('label', 'sr-only', field?.label || 'Запись ответа'); label.htmlFor = `answer-${key || 'chat-free'}`;
    const options = key ? choices[key] : null; const input = dom(options ? 'select' : 'textarea'); input.id = label.htmlFor; input.name = key || 'chat-free';
    if (options) for (const [value, text] of options) { const option = dom('option', '', text); option.value = value; input.append(option); }
    else { input.rows = 3; input.maxLength = 12000; input.placeholder = 'Запишем ответ и отправим'; input.spellcheck = true; }
    const existing = chatTurn(step); const draft = chatDraft(step);
    if (chatEditingTurnId && existing && current().chatLog.slice(current().chatLog.indexOf(existing) + 1).some(turn => turn.key === key && turn.action === 'answer')) form.append(dom('p', 'field-hint', 'Вы исправляете раннюю реплику. Более поздняя запись останется текущей.')); 
    input.value = draft ? draft.text : chatEditingTurnId && existing ? existing.answer : key ? current().answers[key] : existing?.qaEntryId ? current().qaEntries.find(entry => entry.id === existing.qaEntryId)?.answer || '' : '';
    input.addEventListener(options ? 'change' : 'input', () => { const previous = chatDraft(step); current().chatDrafts[chatDraftKey(step)] = { text: input.value, source: previous?.source || null, question: chatQuestion(step), origin: chatQuestionOrigin(step) }; persist(); if (!options) grow(input); });
    input.addEventListener('keydown', event => { if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') { event.preventDefault(); submitChatAnswer(); } });
    form.append(label, input);
    if (field?.hint && !/[?？]/.test(field.hint)) form.append(dom('p', 'field-hint', field.hint));
    if (step.input === 'free') { const advanced = dom('button', 'text-button', step.kind === 'options' ? 'Открыть сравнение вариантов' : 'Открыть записанные условия'); advanced.type = 'button'; advanced.addEventListener('click', () => openMode(step.kind === 'options' ? 'fit_check' : 'agreement_summary')); form.append(advanced); }
    const actions = dom('div', 'chat-compose-actions');
    const submit = dom('button', 'button button-primary', existing?.action === 'answer' ? 'Сохранить исправление' : 'Отправить'); submit.type = 'submit';
    const skip = dom('button', 'text-button', existing?.action === 'answer' ? 'Оставить запись и продолжить' : 'Пока пропустить'); skip.type = 'button';
    skip.addEventListener('click', () => { if (existing?.action !== 'answer') recordChatAction('skip'); advanceChat(); });
    actions.append(submit, skip); form.append(actions); fields.append(form);
    if (key && FIELD_SCHEMA[key]?.draftable) { const mount = dom('div', 'ai-draft-mount'); mount.dataset.aiField = key; form.insertBefore(mount, label); }
  }
  if (step.choices?.length) {
    const links = dom('div', 'guided-choices');
    step.choices.forEach((choice, index) => { const button = dom('button', `button ${index ? 'button-light' : 'button-primary'}`, choice.label); button.type = 'button'; button.addEventListener('click', () => { recordChatAction('choice', choice.label); chatReturnStep = ''; goGuided(choice.to); }); links.append(button); }); fields.append(links);
  }
  $('previous-step').hidden = GUIDED_FLOW.indexOf(step) === 0;
  $('previous-step').textContent = 'Назад';
  $('next-step').hidden = acceptsAnswer || !!step.choices?.length;
  $('next-step').textContent = step.kind === 'welcome' ? 'Начать разговор' : 'Дальше';
  $('navigation-note').textContent = acceptsAnswer ? 'Ответ попадёт в разговор после отправки. Запись можно будет поправить.' : '';
  refreshAiPanels(); ensureAiCard();
  requestAnimationFrame(() => fields.querySelectorAll('textarea').forEach(grow));
}

function renderQuestion() {
  for (const id of ['chat-thread', 'chat-active', 'chat-phases']) $(id).hidden = state.mode !== 'guided';
  if (state.mode === 'guided') { renderGuidedQuestion(); return; }
  $('step-purpose').hidden = false; $('question-hint').hidden = false; $('next-step').hidden = false;
  $('previous-step').textContent = 'Продолжить рассказ';
  $('navigation-note').textContent = 'Выбираем уточнения по ходу разговора.';
  const index = current().step, step = activeSpec();
  const choosing = state.mode === 'choose';
  $('topic-chooser').hidden = !choosing; $('question-card').hidden = choosing; $('step-actions').hidden = choosing || state.mode.startsWith('learn_');
  $('step-label').textContent = choosing ? 'Выбираем по ходу разговора' : step.group;
  if (choosing) { renderChooser(); renderNav(); renderContext(); return; }
  $('speaker-label').textContent = step.speaker || 'Вопрос для разговора';
  $('question-title').textContent = currentQuestion();
  $('step-purpose').textContent = HELP_PURPOSES[activeKey()] || TOPIC_PURPOSES[state.mode === 'followup' ? 'followup' : activeKey()] || 'Уточняем этот вопрос, чтобы выбрать полезный следующий ход.';
  $('question-hint').textContent = current().prompts[activeKey()] ? 'Уточнение выбрано для этого разговора. Ответ и формулировку можно поправить.' : step.hint;
  $('prompt-editor').hidden = true; renderAnchor();
  $('anchor-note').hidden = state.mode === 'topic' && index === 0 && !current().anchors.why_now;
  $('story-invitations').hidden = !(state.mode === 'topic' && index === 0);
  $('opinion-options').hidden = !['hypothesis', 'advice'].includes(state.mode);
  document.querySelectorAll('[data-opinion-mode]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.opinionMode === state.mode)));
  const fields = $('answer-fields'); fields.replaceChildren();
  if (state.mode === 'followup' && activeEntry()) {
    const entry = activeEntry();
    if (entry.anchor) fields.append(dom('p', 'status-callout', `Возвращаемся к записи: ${entry.anchor}`));
    const wrapper = dom('div', 'answer-field'); const label = dom('label', '', 'Ваш ответ на этот вопрос'); label.htmlFor = 'followup-answer';
    const input = document.createElement('textarea'); input.id = 'followup-answer'; input.rows = 5; input.maxLength = 12000; input.value = entry.answer; input.placeholder = 'Запишем здесь';
    input.addEventListener('input', () => { entry.answer = input.value; entry.updatedAt = new Date().toISOString(); persist(); grow(input); renderContext(); });
    wrapper.append(label, input); fields.append(wrapper);
  } else if (state.mode.startsWith('learn_')) renderLearning({ mode: state.mode, session: current(), parent: fields, dom, renderField, openMode, fields: step.fields, returnToConversation: () => go(0), viewSummary });
  else if (state.mode === 'agreement') renderAgreement(fields);
  else if (state.mode === 'agreement_summary') renderAgreementOverview(fields);
  else {
    if (state.mode === 'clarify') renderClarificationMap(fields);
    if (state.mode === 'fit_check') {
      renderFitContext(fields);
      renderField(step.fields[0], fields);
      fields.append(dom('h3', 'fields-heading', 'Что могу предложить я'));
      step.fields.slice(1, -1).forEach(field => renderField(field, fields, true));
      fields.append(dom('p', 'fields-note', 'Это моя предварительная оценка соответствия. Она не обещает результат и может измениться после уточнений.'));
      renderHelpOptions(fields);
      fields.append(dom('h3', 'fields-heading', 'Ваше предпочтение после обсуждения'));
      renderField(step.fields[step.fields.length - 1], fields);
      renderFitActions(fields);
    } else step.fields.forEach(field => {
      renderField(field, fields, index === 9 || state.mode !== 'topic');
      if (field.key === 'shared_question') {
        const check = dom('div', 'goal-check');
        const question = 'Это то, над чем вы хотите работать? Что поправить?';
        check.append(dom('p', '', question));
        const button = dom('button', 'text-button', 'Записать уточнение отдельно'); button.type = 'button'; button.addEventListener('click', () => startNewQuestion(question));
        check.append(button); fields.append(check);
      }
    });
  }
  if (state.mode === 'topic' && index === 3) renderOptionalFields(fields, 'Если уже назван конкретный способ', [textField('considered_method', 'Какой способ вы сейчас рассматриваете'), textField('desired_effect', 'Что должно измениться благодаря этому способу')]);
  if (state.mode === 'topic' && index === 5) renderOptionalFields(fields, 'Если решение затрагивает других людей', [textField('stakeholders', 'Кого затронет решение и от кого оно зависит'), textField('stakeholder_known', 'Что об их позиции известно напрямую'), textField('stakeholder_assumed', 'Что об их позиции мы пока предполагаем')]);
  if (state.mode === 'topic' && index === 8) {
    const links = dom('div', 'inline-actions');
    const orient = dom('button', 'button button-light', 'Уточнить, какую задачу решаем'); orient.type = 'button'; orient.addEventListener('click', () => openMode('orientation'));
    const close = dom('button', 'button button-primary', 'Собрать краткую карту вопроса'); close.type = 'button'; close.addEventListener('click', () => openMode('clarify')); links.append(orient, close); fields.append(links);
    renderOptionalFields(fields, 'Можно ли понять эту задачу иначе?', [textField('alternative_framings', 'Другие возможные понимания задачи'), textField('distinguishing_info', 'Какие сведения помогут различить эти версии')]);
    renderQuestionHistory(fields);
  }
  if (state.mode === 'topic' && index === 9) renderOptionalFields(fields, 'Что предполагаем и что нужно проверить', [textField('proposal_assumption', 'Какое предположение лежит в основе помощи'), textField('proposal_uncertainty', 'Что ещё нужно проверить')]);
  if (state.mode === 'topic' && index === 9) {
    const button = dom('button', 'button button-light section-action', 'Сравнить способы и проверить мой вклад'); button.type = 'button'; button.addEventListener('click', () => openMode('fit_check')); fields.append(button);
    renderFitActions(fields, true);
  }
  if (state.mode === 'topic' && [6, 7].includes(index)) {
    const button = dom('button', 'button button-light section-action', 'Проверить, какая помощь подходит'); button.type = 'button'; button.addEventListener('click', () => openMode('fit_check')); fields.append(button);
  }
  if (state.mode === 'topic' && index === 5) { const button = dom('button', 'button button-light section-action', 'Уточнить срок решения и последствия отсрочки'); button.type = 'button'; button.addEventListener('click', () => openMode('timing')); fields.append(button); }
  if (state.mode === 'clarify') { const button = dom('button', 'button button-light section-action', 'Проверить, какая помощь подходит'); button.type = 'button'; button.addEventListener('click', () => openMode('fit_check')); fields.append(button); }
  if (index === 10 && state.mode === 'topic') renderAgreementLinks(fields);
  $('previous-step').hidden = index === 0 && state.mode === 'topic';
  $('next-step').textContent = state.mode === 'agreement' ? 'Посмотреть предложение целиком' : state.mode === 'agreement_summary' ? 'Обсудить следующий шаг' : state.mode === 'outcome' ? 'Посмотреть итог' : state.mode === 'topic' && index === 10 ? 'Подвести итог разговора' : 'Выбрать, что уточнить';
  renderNav(); renderContext(); requestAnimationFrame(() => fields.querySelectorAll('textarea').forEach(grow));
}
function renderHistory() {
  const list = $('history-list'); list.replaceChildren();
  const others = state.sessions.filter(session => session.id !== state.currentId).slice().reverse();
  if (!others.length) { list.append(dom('p', '', 'Других записей пока нет.')); return; }
  others.forEach(session => {
    const button = dom('button', '', session.title.trim() || session.answers.intake_name.trim() || 'Встреча без названия'); button.type = 'button'; button.append(dom('small', '', session.date));
    button.addEventListener('click', () => { persist(); stopAiRequests(); chatReturnStep = ''; chatEditingTurnId = ''; state.currentId = session.id; state.summary = false; state.mode = 'guided'; persist(); render(); document.querySelector('.history-menu').open = false; $('facilitator-menu').open = false; say('Открыта сохранённая встреча.'); });
    list.append(button);
  });
}
function addSummarySection(title, keys, status = '') {
  const block = dom('article', 'summary-card'); block.append(dom('h3', '', title));
  if (status) block.append(dom('p', 'summary-state', status));
  const populated = keys.filter(key => current().answers[key].trim());
  if (!populated.length) block.append(dom('p', 'context-empty', EMPTY));
  populated.forEach(key => {
    const promptKey = topicKeys.includes(key) ? key : null;
    const field = dom('div', 'summary-item'); field.append(dom('h4', '', FIELD_LABELS[key]));
    if (current().answerPrompts[key] && promptKey) field.append(dom('p', 'answer-source', `Вопрос при записи ответа: ${current().answerPrompts[key]}`));
    if (promptKey && current().anchors[promptKey]?.trim()) field.append(dom('p', 'summary-anchor', `Возвращались к записи: ${current().anchors[promptKey]}`));
    const value = current().answers[key]; field.append(dom('p', value.trim() ? '' : 'empty-answer', value.trim() ? selectedLabel(key, value) : EMPTY)); block.append(field);
  });
  $('summary-content').append(block);
}
function renderSummary() {
  const target = $('summary-content'); target.replaceChildren();
  target.append(dom('p', 'summary-meta', `${current().title.trim() || 'Встреча без названия'} · ${current().date}`));
  addSummarySection('Ситуация и желаемое изменение', ['why_now', 'today', 'episode', 'change']);
  if (['task_type', 'task_type_details', 'trigger_event', 'considered_method', 'desired_effect'].some(key => current().answers[key].trim())) addSummarySection('Какой вопрос сейчас решаем', ['task_type', 'task_type_details', 'trigger_event', 'considered_method', 'desired_effect']);
  if (['success_criteria', 'unacceptable_costs'].some(key => current().answers[key].trim())) addSummarySection('Что сделает результат подходящим', ['success_criteria', 'unacceptable_costs']);
  addSummarySection('Опыт и существенные условия', ['tried', 'tried_result', 'constraints', 'preserve', 'decision_owner']);
  if (['decision_deadline', 'deadline_source', 'delay_consequences'].some(key => current().answers[key].trim())) addSummarySection('Срок решения и последствия отсрочки', ['decision_deadline', 'deadline_source', 'delay_consequences']);
  if (['known_info', 'interpretation', 'unknown_info', 'unknown_priority'].some(key => current().answers[key].trim())) addSummarySection('На что опираемся', ['known_info', 'interpretation', 'unknown_info', 'unknown_priority']);
  if (['stakeholders', 'stakeholder_known', 'stakeholder_assumed'].some(key => current().answers[key].trim())) addSummarySection('Участники и их позиции', ['stakeholders', 'stakeholder_known', 'stakeholder_assumed']);
  addSummarySection('Ожидания от помощи', ['help_expected', 'questions']);
  if (current().answers.help_preferences.trim()) addSummarySection('Что важно при выборе помощи', ['help_preferences']);
  if (['help_role', 'helper_experience', 'helper_fit_reason', 'helper_fit_status'].some(key => current().answers[key].trim())) {
    addSummarySection('Вклад, основания и оценка ведущего', ['help_role', 'helper_experience', 'helper_fit_reason'], current().answers.helper_fit_status ? selectedLabel('helper_fit_status', current().answers.helper_fit_status) : 'Оценка ведущего пока не отмечена');
  }
  if (current().answers.help_use_conditions.trim()) addSummarySection('Условия использования помощи', ['help_use_conditions']);
  const options = current().helpOptions.filter(option => ['name', 'benefit', 'effort', 'unknown'].some(key => option[key].trim()));
  if (options.length) {
    const block = dom('article', 'summary-card'); block.append(dom('h3', '', 'Рассмотренные способы помощи'));
    for (const option of options) {
      const item = dom('section', 'summary-item help-option-summary');
      item.append(dom('h4', '', option.name.trim() || 'Название варианта не записано'));
      for (const [key, label] of [['benefit', 'Что может дать'], ['effort', 'Что потребуется от участника'], ['unknown', 'Что пока неизвестно']]) item.append(dom('p', '', `${label}: ${option[key].trim() || 'не записано'}`));
      block.append(item);
    }
    target.append(block);
  }
  if (current().answers.help_informed_preference.trim()) addSummarySection('Предпочтение после обсуждения вариантов', ['help_informed_preference'], 'Это предпочтение, а не согласие на условия работы');
  if (['hypothesis_basis', 'hypothesis_text', 'hypothesis_reply'].some(key => current().answers[key].trim())) addSummarySection('Предположение ведущего — версия для проверки', ['hypothesis_basis', 'hypothesis_text', 'hypothesis_reply']);
  if (['advice_basis', 'advice_text', 'advice_limits', 'advice_reply'].some(key => current().answers[key].trim())) addSummarySection('Предварительное мнение ведущего', ['advice_basis', 'advice_text', 'advice_limits', 'advice_reply']);
  if (['process_feedback', 'process_adjustment'].some(key => current().answers[key].trim())) addSummarySection('Как идёт разговор', ['process_feedback', 'process_adjustment']);
  addSummarySection('Текущее понимание задачи', ['shared_question', 'question_change_reason'], current().answers.question_status ? selectedLabel('question_status', current().answers.question_status) : 'Оценка текущей версии пока не отмечена');
  if (current().answers.participant_question.trim() || current().answers.clarification_status) addSummarySection('Итог прояснения вопроса', ['participant_question'], current().answers.clarification_status ? selectedLabel('clarification_status', current().answers.clarification_status) : 'Итог прояснения пока не отмечен');
  if (['alternative_framings', 'distinguishing_info'].some(key => current().answers[key].trim())) addSummarySection('Другие понимания задачи', ['alternative_framings', 'distinguishing_info']);
  if (current().questionHistory.length) {
    const block = dom('article', 'summary-card'); block.append(dom('h3', '', 'Как менялось понимание задачи'));
    current().questionHistory.forEach((entry, index) => {
      const version = dom('section', 'summary-item');
      const date = new Intl.DateTimeFormat('ru-RU', { dateStyle: 'short', timeStyle: 'short', timeZone: 'Europe/Moscow' }).format(new Date(entry.at));
      version.append(dom('h4', '', `Версия ${index + 1} · ${date}`), dom('p', '', entry.text));
      if (entry.reason) version.append(dom('p', 'summary-anchor', `Почему уточнили: ${entry.reason}`));
      version.append(dom('p', 'version-status', entry.status ? selectedLabel('question_status', entry.status) : 'Оценка этой версии не отмечена'));
      block.append(version);
    }); target.append(block);
  }
  addSummarySection('Предложение ведущего', ['proposal_basis', 'proposal_method', 'proposal_result', 'proposal_client', 'proposal_limits', 'proposal_check', 'proposal_assumption', 'proposal_uncertainty']);
  addSummarySection('Отклик и оценка участника', ['fit_feedback'], current().answers.fit_status ? selectedLabel('fit_status', current().answers.fit_status) : 'Оценка участника пока не отмечена');
  addSummarySection('Что получили сегодня и что ещё проверим', ['today_outcome', 'remaining_check']);
  if (current().qaEntries.length) {
    const block = dom('article', 'summary-card'); block.append(dom('h3', '', 'Уточняющие вопросы и ответы'));
    for (const entry of current().qaEntries) { const pair = dom('section', 'summary-item'); pair.append(dom('h4', '', entry.question)); if (entry.anchor) pair.append(dom('p', 'summary-anchor', `Вернулись к записи: ${entry.anchor}`)); pair.append(dom('p', entry.answer.trim() ? '' : 'empty-answer', entry.answer.trim() || EMPTY)); block.append(pair); }
    target.append(block);
  }
  if (current().qaHistory.length) {
    const block = dom('article', 'summary-card'); const details = dom('details', 'correction-history'); details.append(dom('summary', '', 'Сохранённые записи до исправления вопросов'));
    for (const snapshot of current().qaHistory) { const pair = dom('section', 'summary-item'); pair.append(dom('h4', '', `Вопрос на экране до исправления: ${snapshot.question}`)); for (const [key, answer] of Object.entries(snapshot.answers)) if (answer.trim()) { pair.append(dom('p', 'record-origin', FIELD_LABELS[key])); if (snapshot.answerPrompts[key]) pair.append(dom('p', 'answer-source', `Записано к вопросу: ${snapshot.answerPrompts[key]}`)); pair.append(dom('p', '', answer)); } details.append(pair); }
    block.append(details); target.append(block);
  }
  if (current().answers.learning_choice || Object.entries(current().answers).some(([key, value]) => key.startsWith('learn_') && value.trim())) {
    addSummarySection('Учебная часть: выбор и собственная попытка', ['learning_choice', 'learn_own_attempt', 'learn_own_help', 'learn_own_feedback']);
    if (['learn_case_question', 'learn_case_facts', 'learn_case_change', 'learn_case_limits'].some(key => current().answers[key].trim())) addSummarySection('Попытка на другом учебном случае', ['learn_case_question', 'learn_case_facts', 'learn_case_change', 'learn_case_limits']);
    for (const key of ['question', 'goal_method', 'event', 'boundary', 'unknown']) if (current().answers[`learn_${key}_level`] || current().answers[`learn_${key}_evidence`].trim()) addSummarySection(FIELD_LABELS[`learn_${key}_level`], [`learn_${key}_level`, `learn_${key}_evidence`]);
    if (current().answers.learn_feedback.trim()) addSummarySection('Обратная связь по попытке', ['learn_feedback']);
    if (['learn_transfer_action', 'learn_transfer_when', 'learn_transfer_check', 'learn_open'].some(key => current().answers[key].trim())) addSummarySection('Применение в жизни и открытые вопросы', ['learn_transfer_action', 'learn_transfer_when', 'learn_transfer_check', 'learn_open']);
  }
  addSummarySection('Следующий шаг', ['next_step', 'next_when', 'next_check'], current().answers.next_choice ? selectedLabel('next_choice', current().answers.next_choice) : 'Продолжение пока не выбрано');
  if (AGREEMENT_FIELDS.some(key => current().answers[key].trim()) || current().agreementHistory.length) {
    const block = dom('article', 'summary-card'); renderAgreementOverview(block); renderAgreementHistory(block); target.append(block);
  }
}
function render() {
  syncAiSettings();
  document.body.classList.toggle('guided-mode', state.mode === 'guided' || state.summary);
  $('resume-guided').hidden = state.mode === 'guided' && !state.summary;
  $('meeting-title').value = current().title; $('meeting-date').value = current().date;
  $('work-layout').hidden = state.summary; $('summary-view').hidden = !state.summary;
  $('summary-toggle').textContent = state.summary ? 'Вернуться к вопросам' : 'Посмотреть итог';
  if (state.summary) { renderSummary(); refreshAiPanels(); ensureAiCard(); } else renderQuestion(); renderHistory();
}
function go(index) {
  current().step = Math.max(0, Math.min(steps.length - 1, index)); state.summary = false; state.mode = 'topic'; persist(); render();
  focusCurrentView();
}
function focusCurrentView() {
  requestAnimationFrame(() => {
    (state.mode === 'choose' ? $('chooser-title') : state.mode === 'guided' ? $('chat-question') : $('question-title')).focus({ preventScroll: true });
    (state.mode === 'guided' ? $('chat-active') : document.querySelector('.question-area')).scrollIntoView({ block: state.mode === 'guided' ? 'center' : 'start', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  });
}
function openMode(mode) {
  if (!['choose', ...Object.keys(extraViews)].includes(mode)) return;
  state.mode = mode; state.summary = false; persist(); render();
  focusCurrentView();
}
function viewSummary() { state.summary = true; persist(); render(); window.scrollTo({ top: 0, behavior: 'smooth' }); }
function filename(suffix) { const title = (current().title.trim() || 'первый-разговор').replace(/[\\/:*?"<>|]/g, '-').slice(0, 90); return `${current().date} — ${title}.${suffix}`; }
function download(contents, mime, suffix) {
  const url = URL.createObjectURL(new Blob([contents], { type: mime })); const link = document.createElement('a'); link.href = url; link.download = filename(suffix); document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 2000); $('file-menu').open = false;
  say('Файл встречи сохранён.');
}

$('meeting-title').addEventListener('input', event => { current().title = event.target.value; persist(); });
$('meeting-title').addEventListener('change', renderHistory);
$('meeting-date').addEventListener('change', event => { if (/^\d{4}-\d{2}-\d{2}$/.test(event.target.value)) { current().date = event.target.value; persist(); } else event.target.value = current().date; });
$('previous-step').addEventListener('click', () => state.mode === 'guided' ? previousGuided() : go(0));
$('next-step').addEventListener('click', () => {
  if (state.mode === 'guided') nextGuided();
  else if (state.mode === 'agreement') openMode('agreement_summary');
  else if (state.mode === 'agreement_summary') go(10);
  else if (state.mode === 'outcome') viewSummary();
  else if (state.mode === 'topic' && current().step === 10) openMode('outcome');
  else openMode('choose');
});
$('choose-topic').addEventListener('click', () => openMode('choose'));
$('check-understanding').addEventListener('click', () => go(8));
$('open-opinion').addEventListener('click', () => openMode('hypothesis'));
$('check-process').addEventListener('click', () => openMode('process'));
$('open-knowledge').addEventListener('click', () => openMode('knowledge'));
$('open-fit-check').addEventListener('click', () => openMode('fit_check'));
$('open-agreement').addEventListener('click', () => openMode('agreement'));
$('edit-outcome').addEventListener('click', () => openMode('outcome'));
$('chooser-story').addEventListener('click', () => go(0));
$('chooser-summary').addEventListener('click', viewSummary);
$('edit-prompt').addEventListener('click', openPromptEditor);
$('cancel-prompt').addEventListener('click', () => { $('prompt-editor').hidden = true; });
$('save-prompt').addEventListener('click', () => {
  const value = $('prompt-input').value.trim();
  if (!value) { say('Запишите вопрос или отмените изменение.'); $('prompt-input').focus(); return; }
  applyPromptChange(value);
});
$('correct-prompt').addEventListener('click', () => { const value = $('prompt-input').value.trim(); if (value) applyPromptChange(value, true); });
$('reset-prompt').addEventListener('click', () => applyPromptChange(activeSpec().title, true));
$('anchor-text').addEventListener('input', event => { current().anchors[activeKey()] = event.target.value; persist(); grow(event.target); });
document.querySelectorAll('[data-opinion-mode]').forEach(button => button.addEventListener('click', () => openMode(button.dataset.opinionMode)));
document.querySelectorAll('[data-invitation]').forEach(button => button.addEventListener('click', () => {
  applyPromptChange(button.dataset.invitation);
}));
$('summary-toggle').addEventListener('click', () => { if (state.summary) { state.summary = false; render(); } else viewSummary(); });
$('back-to-questions').addEventListener('click', () => { state.summary = false; render(); });
$('new-session').addEventListener('click', () => {
  persist(); stopAiRequests(); chatReturnStep = ''; chatEditingTurnId = ''; const session = createSession(); state.sessions.push(session); state.currentId = session.id; state.summary = false; state.mode = 'guided'; persist(); render(); $('facilitator-menu').open = false; notice('Открыт чистый лист. Предыдущая встреча сохранена в «Предыдущих записях».');
});
$('download-text').addEventListener('click', () => { persist(); download(makeSummary(current()), 'text/plain;charset=utf-8', 'txt'); });
$('download-json').addEventListener('click', () => { persist(); download(exportSession(current()), 'application/json;charset=utf-8', 'json'); });
$('print-button').addEventListener('click', () => { $('file-menu').open = false; viewSummary(); requestAnimationFrame(() => window.print()); });
$('import-button').addEventListener('click', () => { $('file-menu').open = false; $('import-file').click(); });
$('import-file').addEventListener('change', async event => {
  const file = event.target.files?.[0]; if (!file) return;
  try {
    if (file.size > 2 * 1024 * 1024) throw new Error('Файл слишком большой для записи одной встречи.');
    const session = parseImport(await file.text());
    // Копия не затирает прежний вариант встречи с таким же идентификатором.
    if (state.sessions.some(existing => existing.id === session.id)) session.id = createSession().id;
    persist(); stopAiRequests(); chatReturnStep = ''; chatEditingTurnId = ''; state.sessions.push(session); state.currentId = session.id; state.summary = false; state.mode = 'guided'; persist(); render(); $('facilitator-menu').open = false; notice('Открыта копия встречи. Прежние записи сохранены.');
  } catch (error) { notice(error.message || 'Не удалось открыть файл встречи.'); }
  finally { event.target.value = ''; }
});
document.addEventListener('click', event => { if (!event.target.closest('.file-menu')) $('file-menu').open = false; });
window.addEventListener('beforeprint', renderSummary);
window.addEventListener('storage', event => {
  if (event.key !== STORAGE_KEY || !event.newValue) return;
  // Вторая вкладка не должна молча затирать редактируемую здесь встречу.
  persistenceBlocked = true;
  notice('Записи изменились в другой вкладке. Сохраните текущую встречу отдельным файлом перед обновлением страницы.');
  $('save-status').textContent = 'Есть изменения в другой вкладке';
});

// Служебные действия убраны с основного экрана, но прежние записи и инструменты доступны.
const facilitatorContent = $('facilitator-content');
facilitatorContent.append(document.querySelector('.meeting-meta'), document.querySelector('.header-actions'));
const guidedMap = dom('details', 'guided-map'); guidedMap.append(dom('summary', '', 'Перейти к части разговора'));
const phases = new Set();
for (const item of GUIDED_FLOW) {
  if (!item.phase || phases.has(item.phase) || item.kind === 'welcome') continue;
  phases.add(item.phase); const button = dom('button', 'text-button', GUIDED_PHASES[item.phase] || item.phase);
  button.type = 'button'; button.addEventListener('click', () => goGuided(item.id)); guidedMap.append(button);
}
const optionalMap = dom('details', 'guided-map'); optionalMap.append(dom('summary', '', 'Дополнительные уточнения'));
for (const step of GUIDED_FLOW.filter(item => item.skipInMain)) { const button = dom('button', 'text-button', step.title); button.type = 'button'; button.addEventListener('click', () => { chatReturnStep = guidedSpec().id; goGuided(step.id, true); }); optionalMap.append(button); }
facilitatorContent.append(guidedMap, optionalMap);
const advanced = dom('button', 'button button-light', 'Все инструменты ведущего'); advanced.type = 'button';
advanced.addEventListener('click', () => { $('facilitator-menu').open = false; go(current().step); }); facilitatorContent.append(advanced);
$('resume-guided').addEventListener('click', () => goGuided(guidedSpec().id, true));
setupAiSettings(facilitatorContent);
load(); render(); if (!persistenceBlocked) persist();
