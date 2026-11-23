// Публичная схема разговора. Сгенерирована scripts/generate-ai-schema.mjs.
export const FIELD_SCHEMA = Object.freeze({
  "why_now": {
    "label": "Рассказ участника и повод встречи",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "today": {
    "label": "Желаемый результат сегодняшнего разговора",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "episode": {
    "label": "Конкретная ситуация или эпизод",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "change": {
    "label": "Желаемое изменение",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "tried": {
    "label": "Что уже пробовали",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "tried_result": {
    "label": "Что получилось после предыдущих попыток",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "constraints": {
    "label": "Существенные условия и то, что важно сохранить",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "help_expected": {
    "label": "Ожидаемая помощь",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "questions": {
    "label": "Вопросы о специалисте и его работе",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "shared_question": {
    "label": "Рабочая формулировка вопроса",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "question_status": {
    "label": "Статус формулировки вопроса",
    "type": "choice",
    "actor": "участник",
    "draftable": false,
    "options": [
      [
        "",
        "Пока не отмечено"
      ],
      [
        "confirmed",
        "Сейчас понимаем задачу так"
      ],
      [
        "revise",
        "Нужно уточнить"
      ],
      [
        "unknown",
        "Вопрос пока не определили"
      ]
    ]
  },
  "proposal_result": {
    "label": "Предлагаемый результат помощи",
    "type": "text",
    "actor": "ведущий",
    "draftable": true
  },
  "proposal_method": {
    "label": "Предлагаемый способ работы",
    "type": "text",
    "actor": "ведущий",
    "draftable": true
  },
  "proposal_client": {
    "label": "Предлагаемое участие клиента",
    "type": "text",
    "actor": "ведущий",
    "draftable": true
  },
  "proposal_limits": {
    "label": "Предлагаемые границы помощи",
    "type": "text",
    "actor": "ведущий",
    "draftable": true
  },
  "proposal_check": {
    "label": "Предлагаемая проверка пользы",
    "type": "text",
    "actor": "ведущий",
    "draftable": true
  },
  "fit_feedback": {
    "label": "Отклик на предложение",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "fit_status": {
    "label": "Соответствие предложения задаче",
    "type": "choice",
    "actor": "участник",
    "draftable": false,
    "options": [
      [
        "",
        "Пока не отмечено"
      ],
      [
        "yes",
        "Предварительно подходит"
      ],
      [
        "revise",
        "Нужно изменить предложение"
      ],
      [
        "no",
        "Не подходит"
      ],
      [
        "unknown",
        "Нужны сведения"
      ]
    ]
  },
  "next_choice": {
    "label": "Выбранное продолжение",
    "type": "choice",
    "actor": "участник",
    "draftable": false,
    "options": [
      [
        "",
        "Пока не выбрали"
      ],
      [
        "together",
        "Продолжить вместе"
      ],
      [
        "self",
        "Действовать самостоятельно"
      ],
      [
        "information",
        "Получить недостающие сведения"
      ],
      [
        "other",
        "Рассмотреть другую помощь"
      ],
      [
        "later",
        "Вернуться позже"
      ],
      [
        "undecided",
        "Решение пока не принято"
      ]
    ]
  },
  "next_step": {
    "label": "Следующий шаг",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "next_when": {
    "label": "Срок или условие следующего шага",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "next_check": {
    "label": "Как проверить результат следующего шага",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "terms_scope": {
    "label": "Обсуждаемый объём работы",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "terms_schedule": {
    "label": "Обсуждаемые сроки и ритм",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "terms_price": {
    "label": "Обсуждаемая цена",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": false
  },
  "terms_payment": {
    "label": "Обсуждаемый порядок оплаты",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": false
  },
  "terms_review": {
    "label": "Обсуждаемая проверка пользы работы",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "terms_change": {
    "label": "Обсуждаемые условия пересмотра или завершения",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "agreement_status": {
    "label": "Статус договорённости",
    "type": "choice",
    "actor": "обсуждение вместе",
    "draftable": false,
    "options": [
      [
        "",
        "Пока не отмечено"
      ],
      [
        "discussing",
        "Предложение обсуждается"
      ],
      [
        "agreed",
        "Эти условия согласованы"
      ]
    ]
  },
  "hypothesis_basis": {
    "label": "Основание предположения ведущего",
    "type": "text",
    "actor": "ведущий",
    "draftable": true
  },
  "hypothesis_text": {
    "label": "Предположение ведущего",
    "type": "text",
    "actor": "ведущий",
    "draftable": true
  },
  "hypothesis_reply": {
    "label": "Отклик участника на предположение",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "advice_basis": {
    "label": "Основание предварительного мнения или совета",
    "type": "text",
    "actor": "ведущий",
    "draftable": true
  },
  "advice_text": {
    "label": "Предварительное мнение или совет ведущего",
    "type": "text",
    "actor": "ведущий",
    "draftable": true
  },
  "advice_limits": {
    "label": "Ограничения предварительного мнения или совета",
    "type": "text",
    "actor": "ведущий",
    "draftable": true
  },
  "advice_reply": {
    "label": "Отклик участника на мнение или совет",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "process_feedback": {
    "label": "Обратная связь о ходе разговора",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "process_adjustment": {
    "label": "Изменение хода разговора",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "known_info": {
    "label": "Что известно по словам участника и из названных источников",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "interpretation": {
    "label": "Текущее понимание ситуации — версия",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "unknown_info": {
    "label": "Что пока неизвестно",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "unknown_priority": {
    "label": "Какое неизвестное существенно для следующего шага",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "success_criteria": {
    "label": "Предварительные критерии подходящего результата",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "unacceptable_costs": {
    "label": "Какая цена изменений неприемлема",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "stakeholders": {
    "label": "Кого затрагивает решение",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "stakeholder_known": {
    "label": "Что о позициях участников известно со слов и из источников",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "stakeholder_assumed": {
    "label": "Что о позициях участников пока предполагается",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "alternative_framings": {
    "label": "Другие возможные формулировки задачи",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "distinguishing_info": {
    "label": "Что поможет различить возможные понимания задачи",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "proposal_basis": {
    "label": "На какие сведения опирается предложение помощи",
    "type": "text",
    "actor": "ведущий",
    "draftable": true
  },
  "proposal_assumption": {
    "label": "При каких предположениях предложенная помощь может быть полезна",
    "type": "text",
    "actor": "ведущий",
    "draftable": true
  },
  "proposal_uncertainty": {
    "label": "Что в предложении помощи ещё предстоит проверить",
    "type": "text",
    "actor": "ведущий",
    "draftable": true
  },
  "today_outcome": {
    "label": "Что участник отмечает как результат сегодняшнего разговора",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "remaining_check": {
    "label": "Что ещё предстоит проверить на опыте",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "question_change_reason": {
    "label": "Основание изменения рабочей формулировки",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "task_type": {
    "label": "Какой вопрос сейчас актуален",
    "type": "choice",
    "actor": "участник",
    "draftable": false,
    "options": [
      [
        "",
        "Пока не отмечено"
      ],
      [
        "choice",
        "Выбрать направление"
      ],
      [
        "implementation",
        "Разобраться, как осуществить выбранное"
      ],
      [
        "exploration",
        "Пока исследовать интересующую тему"
      ],
      [
        "other",
        "Другой вопрос"
      ],
      [
        "unclear",
        "Это ещё предстоит понять"
      ]
    ]
  },
  "task_type_details": {
    "label": "Уточнение вида задачи своими словами",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "trigger_event": {
    "label": "Событие, после которого возник вопрос",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "preserve": {
    "label": "Что пока сохраняется",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "decision_owner": {
    "label": "Кто вправе принимать какие решения",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "decision_deadline": {
    "label": "Реальный срок решения или условие возвращения к вопросу",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "deadline_source": {
    "label": "Откуда известен срок решения",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "delay_consequences": {
    "label": "Последствия отсрочки или сохранения положения",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "desired_effect": {
    "label": "Желаемый эффект, ради которого рассматривается способ",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "considered_method": {
    "label": "Уже рассматриваемый способ",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "participant_question": {
    "label": "Как участник формулирует свой вопрос",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "clarification_status": {
    "label": "Состояние прояснения текущего вопроса",
    "type": "choice",
    "actor": "участник",
    "draftable": false,
    "options": [
      [
        "",
        "Пока не отмечено"
      ],
      [
        "clear",
        "Текущий вопрос стал понятен"
      ],
      [
        "partial",
        "Остались существенные неясности"
      ],
      [
        "no_current_decision",
        "Сейчас нет решения, которое нужно принять"
      ]
    ]
  },
  "learning_choice": {
    "label": "Выбор учебной работы",
    "type": "choice",
    "actor": "участник",
    "draftable": false,
    "options": [
      [
        "",
        "Пока не выбирали"
      ],
      [
        "yes",
        "Хочу попробовать"
      ],
      [
        "later",
        "Вернуться к этому позже"
      ],
      [
        "not_needed",
        "Сейчас достаточно прояснения моего вопроса"
      ]
    ]
  },
  "learn_own_attempt": {
    "label": "Учебная попытка на собственной ситуации",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "learn_own_help": {
    "label": "Помощь при попытке на собственной ситуации",
    "type": "choice",
    "actor": "учебная запись вместе",
    "draftable": false,
    "options": [
      [
        "",
        "Пока не отмечено"
      ],
      [
        "self",
        "Сформулировал сам"
      ],
      [
        "together",
        "Сформулировали вместе"
      ],
      [
        "leader",
        "Формулировку предложил ведущий"
      ],
      [
        "not_checked",
        "Самостоятельность не проверяли"
      ]
    ]
  },
  "learn_own_feedback": {
    "label": "Обратная связь по попытке на собственной ситуации",
    "type": "text",
    "actor": "учебная запись вместе",
    "draftable": true
  },
  "learn_case_question": {
    "label": "Вопрос решения в новом учебном случае",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "learn_case_facts": {
    "label": "События и объяснения в новом учебном случае",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "learn_case_change": {
    "label": "Желаемое изменение и способ в новом учебном случае",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "learn_case_limits": {
    "label": "Границы и неизвестное в новом учебном случае",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "learn_feedback": {
    "label": "Конкретная обратная связь по учебной попытке",
    "type": "text",
    "actor": "учебная запись вместе",
    "draftable": true
  },
  "learn_transfer_action": {
    "label": "Где и как попробует применить способ",
    "type": "text",
    "actor": "учебная запись вместе",
    "draftable": true
  },
  "learn_transfer_when": {
    "label": "Когда попробует применить способ",
    "type": "text",
    "actor": "учебная запись вместе",
    "draftable": true
  },
  "learn_transfer_check": {
    "label": "По чему проверим самостоятельное применение",
    "type": "text",
    "actor": "учебная запись вместе",
    "draftable": true
  },
  "learn_open": {
    "label": "Что в освоении способа остаётся непроверенным",
    "type": "text",
    "actor": "учебная запись вместе",
    "draftable": true
  },
  "learn_question_level": {
    "label": "Наблюдение: формулирование вопроса",
    "type": "choice",
    "actor": "учебная запись вместе",
    "draftable": false,
    "options": [
      [
        "",
        "Пока не отмечено"
      ],
      [
        "self",
        "Получилось самостоятельно"
      ],
      [
        "prompt",
        "Получилось с подсказкой"
      ],
      [
        "not_yet",
        "Пока трудно"
      ],
      [
        "not_checked",
        "Не проверяли"
      ]
    ]
  },
  "learn_question_evidence": {
    "label": "Свидетельство формулирования вопроса в этой попытке",
    "type": "text",
    "actor": "учебная запись вместе",
    "draftable": true
  },
  "learn_goal_method_level": {
    "label": "Наблюдение: различение цели и способа",
    "type": "choice",
    "actor": "учебная запись вместе",
    "draftable": false,
    "options": [
      [
        "",
        "Пока не отмечено"
      ],
      [
        "self",
        "Получилось самостоятельно"
      ],
      [
        "prompt",
        "Получилось с подсказкой"
      ],
      [
        "not_yet",
        "Пока трудно"
      ],
      [
        "not_checked",
        "Не проверяли"
      ]
    ]
  },
  "learn_goal_method_evidence": {
    "label": "Свидетельство различения цели и способа в этой попытке",
    "type": "text",
    "actor": "учебная запись вместе",
    "draftable": true
  },
  "learn_event_level": {
    "label": "Наблюдение: различение события и объяснения",
    "type": "choice",
    "actor": "учебная запись вместе",
    "draftable": false,
    "options": [
      [
        "",
        "Пока не отмечено"
      ],
      [
        "self",
        "Получилось самостоятельно"
      ],
      [
        "prompt",
        "Получилось с подсказкой"
      ],
      [
        "not_yet",
        "Пока трудно"
      ],
      [
        "not_checked",
        "Не проверяли"
      ]
    ]
  },
  "learn_event_evidence": {
    "label": "Свидетельство различения события и объяснения в этой попытке",
    "type": "text",
    "actor": "учебная запись вместе",
    "draftable": true
  },
  "learn_boundary_level": {
    "label": "Наблюдение: определение границ решения",
    "type": "choice",
    "actor": "учебная запись вместе",
    "draftable": false,
    "options": [
      [
        "",
        "Пока не отмечено"
      ],
      [
        "self",
        "Получилось самостоятельно"
      ],
      [
        "prompt",
        "Получилось с подсказкой"
      ],
      [
        "not_yet",
        "Пока трудно"
      ],
      [
        "not_checked",
        "Не проверяли"
      ]
    ]
  },
  "learn_boundary_evidence": {
    "label": "Свидетельство определения границ в этой попытке",
    "type": "text",
    "actor": "учебная запись вместе",
    "draftable": true
  },
  "learn_unknown_level": {
    "label": "Наблюдение: определение существенного неизвестного",
    "type": "choice",
    "actor": "учебная запись вместе",
    "draftable": false,
    "options": [
      [
        "",
        "Пока не отмечено"
      ],
      [
        "self",
        "Получилось самостоятельно"
      ],
      [
        "prompt",
        "Получилось с подсказкой"
      ],
      [
        "not_yet",
        "Пока трудно"
      ],
      [
        "not_checked",
        "Не проверяли"
      ]
    ]
  },
  "learn_unknown_evidence": {
    "label": "Свидетельство определения неизвестного в этой попытке",
    "type": "text",
    "actor": "учебная запись вместе",
    "draftable": true
  },
  "help_role": {
    "label": "Какой вклад ведущего рассматриваем",
    "type": "choice",
    "actor": "обсуждение вместе",
    "draftable": false,
    "options": [
      [
        "",
        "Пока не выбрали"
      ],
      [
        "exploration",
        "Вместе исследовать вопрос"
      ],
      [
        "advice",
        "Получить объяснение или совет"
      ],
      [
        "learning",
        "Освоить способ с моей помощью"
      ],
      [
        "joint",
        "Вместе работать над задачей"
      ],
      [
        "other",
        "Другой способ помощи"
      ],
      [
        "unclear",
        "Подходящий способ пока неясен"
      ]
    ]
  },
  "helper_experience": {
    "label": "Какие знания и опыт ведущего относятся к задаче",
    "type": "text",
    "actor": "ведущий",
    "draftable": true
  },
  "helper_fit_reason": {
    "label": "На чём основана оценка ведущего о подходящей помощи",
    "type": "text",
    "actor": "ведущий",
    "draftable": true
  },
  "helper_fit_status": {
    "label": "Предварительная оценка соответствия ведущим",
    "type": "choice",
    "actor": "ведущий",
    "draftable": false,
    "options": [
      [
        "",
        "Пока не отметил"
      ],
      [
        "yes",
        "Предварительно могу помочь с этой частью"
      ],
      [
        "no",
        "Не могу предложить подходящую помощь"
      ],
      [
        "information",
        "Мне нужны дополнительные сведения"
      ]
    ]
  },
  "help_preferences": {
    "label": "Что участнику важно при выборе помощи",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "help_informed_preference": {
    "label": "Предпочтение участника после обсуждения вариантов и его основания",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "help_use_conditions": {
    "label": "Какие условия позволят воспользоваться помощью",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "agreement_stage_task": {
    "label": "Задача предлагаемого этапа",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "agreement_stage_result": {
    "label": "Ожидаемый результат предлагаемого этапа",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "agreement_stage_limits": {
    "label": "Границы предлагаемого этапа",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "agreement_leader_actions": {
    "label": "Что берёт на себя ведущий",
    "type": "text",
    "actor": "ведущий",
    "draftable": true
  },
  "agreement_client_actions": {
    "label": "Что берёт на себя участник",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "agreement_load": {
    "label": "Предполагаемая нагрузка сторон",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "agreement_required": {
    "label": "Необходимые условия работы",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "agreement_preferred": {
    "label": "Желательные условия работы",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "agreement_data": {
    "label": "Использование и доступ к данным",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "agreement_third_parties": {
    "label": "Участие третьих сторон",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "agreement_postponement": {
    "label": "Переносы и паузы",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "agreement_client_understanding": {
    "label": "Как участник понял предложение своими словами",
    "type": "text",
    "actor": "участник",
    "draftable": true
  },
  "agreement_corrections": {
    "label": "Что требуется изменить в предложении",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "agreement_unknown": {
    "label": "Что ещё нужно выяснить до решения",
    "type": "text",
    "actor": "обсуждение вместе",
    "draftable": true
  },
  "agreement_client_decision": {
    "label": "Решение участника по текущему предложению",
    "type": "choice",
    "actor": "участник",
    "draftable": false,
    "options": [
      [
        "",
        "Пока не отмечено"
      ],
      [
        "start",
        "Готов начать на записанных условиях"
      ],
      [
        "revise",
        "Предлагаю изменить условия"
      ],
      [
        "information",
        "Нужны сведения до решения"
      ],
      [
        "pause",
        "Беру паузу"
      ],
      [
        "decline",
        "Отказываюсь от этого предложения"
      ]
    ]
  },
  "agreement_leader_decision": {
    "label": "Решение ведущего по текущему предложению",
    "type": "choice",
    "actor": "ведущий",
    "draftable": false,
    "options": [
      [
        "",
        "Пока не отмечено"
      ],
      [
        "start",
        "Готов начать на записанных условиях"
      ],
      [
        "revise",
        "Предлагаю изменить условия"
      ],
      [
        "information",
        "Нужны сведения до решения"
      ],
      [
        "pause",
        "Беру паузу"
      ],
      [
        "decline",
        "Отказываюсь от этого предложения"
      ]
    ]
  },
  "intake_name": {
    "label": "Как к вам обращаться",
    "type": "text",
    "actor": "участник",
    "draftable": false
  },
  "intake_age": {
    "label": "Возраст",
    "type": "text",
    "actor": "участник",
    "draftable": false
  },
  "intake_role": {
    "label": "Занятие и текущая роль",
    "type": "text",
    "actor": "участник",
    "draftable": false
  },
  "intake_context": {
    "label": "Важные обстоятельства жизни",
    "type": "text",
    "actor": "участник",
    "draftable": false
  }
});
export const SCREEN_SCHEMA = Object.freeze({
  "welcome": {
    "id": "welcome",
    "phase": "about",
    "kind": "welcome",
    "title": "Разберёмся с вашим вопросом",
    "explanation": "Сначала уточним ваш вопрос. Затем посмотрим, чем я могу помочь. Если захотите обсудить продолжение — разберём условия. Можно не отвечать, поправлять записи и возвращаться к предыдущим вопросам.",
    "speaker": "Обсуждаем вместе",
    "fields": []
  },
  "about_you": {
    "id": "about_you",
    "phase": "about",
    "kind": "question",
    "title": "Как к вам обращаться?",
    "explanation": "Сверим, как вам удобно общаться сегодня.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "intake_name",
        "label": "Как к вам обращаться"
      }
    ]
  },
  "about_you__intake_age": {
    "id": "about_you__intake_age",
    "phase": "about",
    "kind": "question",
    "title": "Сколько вам лет?",
    "explanation": "Возраст поможет учитывать ваш нынешний этап жизни. Можно его не указывать.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "intake_age",
        "label": "Возраст"
      }
    ]
  },
  "about_you__intake_role": {
    "id": "about_you__intake_role",
    "phase": "about",
    "kind": "question",
    "title": "Чем занимаетесь сейчас?",
    "explanation": "Это поможет понять, с какими делами и решениями вы сталкиваетесь сейчас.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "intake_role",
        "label": "Чем занимаетесь сейчас"
      }
    ]
  },
  "about_you__intake_context": {
    "id": "about_you__intake_context",
    "phase": "about",
    "kind": "question",
    "title": "Что сейчас важно учитывать в вашей жизни?",
    "explanation": "Учитываем только обстоятельства, которые вы считаете важными для этого разговора.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "intake_context",
        "label": "Что сейчас важно учитывать в вашей жизни"
      }
    ]
  },
  "story": {
    "id": "story",
    "phase": "question",
    "kind": "question",
    "title": "С чем вы пришли на этот разговор?",
    "explanation": "Начните с того, что сейчас важно. Я выслушаю и запишу главное так, чтобы вы могли меня поправить.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "why_now",
        "label": "Ваш рассказ"
      }
    ]
  },
  "today": {
    "id": "today",
    "phase": "question",
    "kind": "question",
    "title": "Что было бы полезно получить сегодня?",
    "explanation": "Это поможет выбрать, на чём сосредоточиться сегодня.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "today",
        "label": "Полезный результат сегодняшнего разговора"
      }
    ]
  },
  "example": {
    "id": "example",
    "phase": "question",
    "kind": "question",
    "title": "Можете привести недавний пример того, о чём рассказываете?",
    "explanation": "На конкретном случае будет легче понять, что происходит. Если примера пока нет, продолжим без него.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "episode",
        "label": "Что произошло в этой ситуации"
      }
    ]
  },
  "example__trigger_event": {
    "id": "example__trigger_event",
    "phase": "question",
    "kind": "question",
    "title": "После чего этот вопрос стал для вас важным?",
    "explanation": "Так мы поймём, почему вопрос стал актуален сейчас.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "trigger_event",
        "label": "Было ли событие, после которого вы стали об этом задумываться"
      }
    ]
  },
  "change": {
    "id": "change",
    "phase": "question",
    "kind": "question",
    "title": "Что вы хотели бы изменить?",
    "explanation": "Уточним, что вы хотите получить. Если уже рассматриваете какой-то способ, запишем и его: так будет легче проверить, ведёт ли он к нужному результату.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "change",
        "label": "Что должно стать иначе"
      }
    ]
  },
  "change__success_criteria": {
    "id": "change__success_criteria",
    "phase": "question",
    "kind": "question",
    "title": "Как вы поймёте, что нужное изменение произошло?",
    "explanation": "Этот признак поможет отличить желаемое изменение от общего пожелания.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "success_criteria",
        "label": "Как поймёте, что изменилось то, что вы хотели"
      }
    ]
  },
  "change__considered_method": {
    "id": "change__considered_method",
    "phase": "question",
    "kind": "question",
    "title": "Какой способ вы уже рассматриваете?",
    "explanation": "Запишем уже возникшую идею, чтобы затем оценить её по нужному вам результату.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "considered_method",
        "label": "Какой способ уже рассматриваете"
      }
    ]
  },
  "change__desired_effect": {
    "id": "change__desired_effect",
    "phase": "question",
    "kind": "question",
    "title": "Что вы хотите получить благодаря этому способу?",
    "explanation": "Проверим, что выбранный способ нужен ради понятного вам изменения.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "desired_effect",
        "label": "Что хотите получить благодаря этому способу"
      }
    ]
  },
  "previous": {
    "id": "previous",
    "phase": "question",
    "kind": "question",
    "title": "Что вы уже пробовали?",
    "explanation": "Посмотрим, что уже помогло и что осталось нерешённым. Это поможет выбрать следующий шаг.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "tried",
        "label": "Что уже делали"
      }
    ]
  },
  "previous__tried_result": {
    "id": "previous__tried_result",
    "phase": "question",
    "kind": "question",
    "title": "Что получилось после этой попытки?",
    "explanation": "Это поможет сохранить то, что уже работает, и не повторять бесполезные попытки.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "tried_result",
        "label": "Что получилось после этих попыток"
      }
    ]
  },
  "constraints": {
    "id": "constraints",
    "phase": "question",
    "kind": "question",
    "title": "Что важно учесть при решении?",
    "explanation": "Посмотрим, какие условия и обязательства влияют на ваше решение. Это поможет выбрать выполнимый вариант.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "constraints",
        "label": "Что нужно учесть"
      }
    ]
  },
  "constraints__preserve": {
    "id": "constraints__preserve",
    "phase": "question",
    "kind": "question",
    "title": "Что вам важно сохранить?",
    "explanation": "Изменения не должны лишать вас того, что вы хотите сохранить.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "preserve",
        "label": "Что важно пока сохранить"
      }
    ]
  },
  "constraints__decision_owner": {
    "id": "constraints__decision_owner",
    "phase": "question",
    "kind": "question",
    "title": "Какую часть решения вы можете принять сами?",
    "explanation": "Так мы не будем строить план на решениях, которые вы не можете принять за других.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "decision_owner",
        "label": "Что решаете вы, а что зависит от других"
      }
    ]
  },
  "constraints__unacceptable_costs": {
    "id": "constraints__unacceptable_costs",
    "phase": "question",
    "kind": "question",
    "title": "На что вы не готовы пойти ради этого изменения?",
    "explanation": "Посмотрим, какие условия и обязательства влияют на ваше решение. Это поможет выбрать выполнимый вариант.",
    "speaker": "Обсуждаем вместе",
    "skipInMain": true,
    "optionalFor": "constraints",
    "fields": [
      {
        "key": "unacceptable_costs",
        "label": "Какие затраты или последствия для вас неприемлемы"
      }
    ]
  },
  "timing": {
    "id": "timing",
    "phase": "question",
    "kind": "question",
    "title": "Когда вам нужно определиться?",
    "explanation": "Если срок есть, запишем, с чем он связан. Если срока нет, его не нужно придумывать.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "decision_deadline",
        "label": "Срок решения или условие возвращения к вопросу"
      }
    ]
  },
  "timing__deadline_source": {
    "id": "timing__deadline_source",
    "phase": "question",
    "kind": "question",
    "title": "Откуда взялся этот срок?",
    "explanation": "Проверим, с чем связан срок и насколько он влияет на решение.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "deadline_source",
        "label": "Откуда взялся этот срок"
      }
    ]
  },
  "timing__delay_consequences": {
    "id": "timing__delay_consequences",
    "phase": "question",
    "kind": "question",
    "title": "Что будет, если пока ничего не менять?",
    "explanation": "Это поможет оценить, что означает пауза именно в вашей ситуации.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "delay_consequences",
        "label": "Что будет, если пока ничего не менять"
      }
    ]
  },
  "shared_question": {
    "id": "shared_question",
    "phase": "question",
    "kind": "question",
    "title": "Какой вопрос мы сейчас пытаемся решить?",
    "explanation": "Запишем коротко, с чем разбираемся. Поправьте, если я что-то понял неверно.",
    "speaker": "Формулируем вместе",
    "fields": [
      {
        "key": "shared_question",
        "label": "Наша рабочая формулировка"
      }
    ]
  },
  "shared_question__question_change_reason": {
    "id": "shared_question__question_change_reason",
    "phase": "question",
    "kind": "question",
    "title": "Почему мы изменили прежнюю формулировку?",
    "explanation": "Запишем коротко, с чем разбираемся. Поправьте, если я что-то понял неверно.",
    "speaker": "Формулируем вместе",
    "skipInMain": true,
    "optionalFor": "shared_question",
    "fields": [
      {
        "key": "question_change_reason",
        "label": "Почему изменили прежнюю формулировку"
      }
    ]
  },
  "shared_question__unknown_priority": {
    "id": "shared_question__unknown_priority",
    "phase": "question",
    "kind": "question",
    "title": "Что ещё нужно узнать для следующего шага?",
    "explanation": "Запишем коротко, с чем разбираемся. Поправьте, если я что-то понял неверно.",
    "speaker": "Формулируем вместе",
    "skipInMain": true,
    "optionalFor": "shared_question",
    "fields": [
      {
        "key": "unknown_priority",
        "label": "Что ещё нужно узнать, чтобы выбрать следующий шаг"
      }
    ]
  },
  "shared_question__task_type": {
    "id": "shared_question__task_type",
    "phase": "question",
    "kind": "question",
    "title": "Какой вопрос сейчас важнее разобрать?",
    "explanation": "Запишем коротко, с чем разбираемся. Поправьте, если я что-то понял неверно.",
    "speaker": "Формулируем вместе",
    "skipInMain": true,
    "optionalFor": "shared_question",
    "fields": [
      {
        "key": "task_type",
        "label": "Какой вопрос сейчас актуален"
      }
    ]
  },
  "your_question": {
    "id": "your_question",
    "phase": "question",
    "kind": "question",
    "title": "Как вы сами сейчас сформулировали бы свой вопрос?",
    "explanation": "Проверим, что формулировка передаёт вашу задачу. Можно поправить её или оставить часть вопроса открытой.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "participant_question",
        "label": "Ваш вопрос своими словами"
      }
    ]
  },
  "your_question__question_status": {
    "id": "your_question__question_status",
    "phase": "question",
    "kind": "question",
    "title": "Насколько наша формулировка передаёт ваш вопрос?",
    "explanation": "Проверим, что формулировка передаёт вашу задачу. Можно поправить её или оставить часть вопроса открытой.",
    "speaker": "Обсуждаем вместе",
    "skipInMain": true,
    "optionalFor": "your_question",
    "fields": [
      {
        "key": "question_status",
        "label": "Как вам наша рабочая формулировка"
      }
    ]
  },
  "your_question__clarification_status": {
    "id": "your_question__clarification_status",
    "phase": "question",
    "kind": "question",
    "title": "Что нам удалось прояснить?",
    "explanation": "Проверим, что формулировка передаёт вашу задачу. Можно поправить её или оставить часть вопроса открытой.",
    "speaker": "Обсуждаем вместе",
    "skipInMain": true,
    "optionalFor": "your_question",
    "fields": [
      {
        "key": "clarification_status",
        "label": "Что получилось прояснить"
      }
    ]
  },
  "help_bridge": {
    "id": "help_bridge",
    "phase": "help",
    "kind": "bridge",
    "title": "Посмотрим, могу ли я помочь",
    "explanation": "Теперь обсудим возможный способ работы. Вы сможете задать вопросы, сравнить варианты и сказать, что вам подходит.",
    "speaker": "Обсуждаем вместе",
    "fields": []
  },
  "expectations": {
    "id": "expectations",
    "phase": "help",
    "kind": "question",
    "title": "Какой помощи вы ожидаете от меня?",
    "explanation": "Можно вместе разобраться, получить мнение, освоить способ или сделать часть работы вместе. Если пока не знаете, так и запишем.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "help_expected",
        "label": "Какой помощи вы ждёте"
      }
    ]
  },
  "expectations__questions": {
    "id": "expectations__questions",
    "phase": "help",
    "kind": "question",
    "title": "Что вы хотите узнать о моей работе?",
    "explanation": "Можно вместе разобраться, получить мнение, освоить способ или сделать часть работы вместе. Если пока не знаете, так и запишем.",
    "speaker": "Обсуждаем вместе",
    "skipInMain": true,
    "optionalFor": "expectations",
    "fields": [
      {
        "key": "questions",
        "label": "Что хотите узнать обо мне и моей работе"
      }
    ]
  },
  "preferences": {
    "id": "preferences",
    "phase": "help",
    "kind": "question",
    "title": "Что для вас важно при выборе помощи?",
    "explanation": "Ваш ответ поможет сравнить способы и оценить моё предложение.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "help_preferences",
        "label": "Что важно именно вам"
      }
    ]
  },
  "experience": {
    "id": "experience",
    "phase": "help",
    "kind": "question",
    "title": "Какой мой опыт может пригодиться в вашей задаче?",
    "explanation": "Расскажу, какой опыт может пригодиться в вашем случае и чего он не позволяет обещать. Вы сможете задать вопросы.",
    "speaker": "Объяснение ведущего",
    "fields": [
      {
        "key": "helper_experience",
        "label": "Мой опыт, относящийся к вашей задаче"
      }
    ]
  },
  "experience__help_role": {
    "id": "experience__help_role",
    "phase": "help",
    "kind": "question",
    "title": "Какой вклад ведущего сейчас нужен?",
    "explanation": "Расскажу, какой опыт может пригодиться в вашем случае и чего он не позволяет обещать. Вы сможете задать вопросы.",
    "speaker": "Объяснение ведущего",
    "skipInMain": true,
    "optionalFor": "experience",
    "fields": [
      {
        "key": "help_role",
        "label": "Какой вклад ведущего рассматриваем"
      }
    ]
  },
  "help_result": {
    "id": "help_result",
    "phase": "help",
    "kind": "question",
    "title": "С какой частью вопроса я предлагаю помочь?",
    "explanation": "Объясню, какого результата мы можем ожидать и почему.",
    "speaker": "Предложение ведущего",
    "fields": [
      {
        "key": "proposal_result",
        "label": "Возможный результат помощи"
      }
    ]
  },
  "help_result__proposal_basis": {
    "id": "help_result__proposal_basis",
    "phase": "help",
    "kind": "question",
    "title": "На что опирается моё предложение?",
    "explanation": "Объясню, какого результата мы можем ожидать и почему.",
    "speaker": "Предложение ведущего",
    "skipInMain": true,
    "optionalFor": "help_result",
    "fields": [
      {
        "key": "proposal_basis",
        "label": "На какие сведения опирается предложение"
      }
    ]
  },
  "help_method": {
    "id": "help_method",
    "phase": "help",
    "kind": "question",
    "title": "Как мы могли бы работать?",
    "explanation": "Я объясню способ и ваше участие. Затем проверим, подходит ли вам такая работа.",
    "speaker": "Предложение ведущего",
    "fields": [
      {
        "key": "proposal_method",
        "label": "Как предлагаю работать и почему"
      }
    ]
  },
  "help_method__proposal_client": {
    "id": "help_method__proposal_client",
    "phase": "help",
    "kind": "question",
    "title": "Какое участие потребуется от вас?",
    "explanation": "Я объясню способ и ваше участие. Затем проверим, подходит ли вам такая работа.",
    "speaker": "Предложение ведущего",
    "fields": [
      {
        "key": "proposal_client",
        "label": "Какое участие потребуется от вас"
      }
    ]
  },
  "help_method__help_use_conditions": {
    "id": "help_method__help_use_conditions",
    "phase": "help",
    "kind": "question",
    "title": "Что нужно, чтобы воспользоваться этой помощью?",
    "explanation": "Я объясню способ и ваше участие. Затем проверим, подходит ли вам такая работа.",
    "speaker": "Предложение ведущего",
    "skipInMain": true,
    "optionalFor": "help_method",
    "fields": [
      {
        "key": "help_use_conditions",
        "label": "Что нужно, чтобы воспользоваться помощью"
      }
    ]
  },
  "help_limits": {
    "id": "help_limits",
    "phase": "help",
    "kind": "question",
    "title": "Чего от этой помощи ждать не стоит?",
    "explanation": "Объясню ограничения и то, что ещё нужно проверить.",
    "speaker": "Объяснение ведущего",
    "fields": [
      {
        "key": "proposal_limits",
        "label": "Ограничения помощи и важные последствия"
      }
    ]
  },
  "help_limits__proposal_check": {
    "id": "help_limits__proposal_check",
    "phase": "help",
    "kind": "question",
    "title": "Как проверим, помогает ли выбранный способ?",
    "explanation": "Объясню ограничения и то, что ещё нужно проверить.",
    "speaker": "Объяснение ведущего",
    "skipInMain": true,
    "optionalFor": "help_limits",
    "fields": [
      {
        "key": "proposal_check",
        "label": "Как проверим, есть ли польза"
      }
    ]
  },
  "help_limits__proposal_assumption": {
    "id": "help_limits__proposal_assumption",
    "phase": "help",
    "kind": "question",
    "title": "Что мы пока предполагаем о пользе этого способа?",
    "explanation": "Объясню ограничения и то, что ещё нужно проверить.",
    "speaker": "Объяснение ведущего",
    "skipInMain": true,
    "optionalFor": "help_limits",
    "fields": [
      {
        "key": "proposal_assumption",
        "label": "При каких предположениях помощь может быть полезна"
      }
    ]
  },
  "help_limits__proposal_uncertainty": {
    "id": "help_limits__proposal_uncertainty",
    "phase": "help",
    "kind": "question",
    "title": "Что в предложении ещё нужно проверить?",
    "explanation": "Объясню ограничения и то, что ещё нужно проверить.",
    "speaker": "Объяснение ведущего",
    "skipInMain": true,
    "optionalFor": "help_limits",
    "fields": [
      {
        "key": "proposal_uncertainty",
        "label": "Что ещё нужно проверить"
      }
    ]
  },
  "options": {
    "id": "options",
    "phase": "help",
    "kind": "options",
    "title": "Какие способы стоит сравнить?",
    "explanation": "Запишем реальные варианты: что каждый может дать, чего потребует от вас и что о нём пока неизвестно. Можно рассмотреть самостоятельную работу, другую помощь или паузу, если это подходит вашей ситуации.",
    "speaker": "Обсуждаем вместе",
    "input": "free",
    "fields": []
  },
  "informed_preference": {
    "id": "informed_preference",
    "phase": "help",
    "kind": "question",
    "title": "Какой вариант вам сейчас ближе и почему?",
    "explanation": "Можно выбрать способ, попросить сведения, взять паузу или отказаться. Предпочтение ещё не означает согласия на платную работу.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "help_informed_preference",
        "label": "Какой вариант вам подходит и почему"
      }
    ]
  },
  "informed_preference__fit_feedback": {
    "id": "informed_preference__fit_feedback",
    "phase": "help",
    "kind": "question",
    "title": "Что в предложении вы хотели бы поправить?",
    "explanation": "Можно выбрать способ, попросить сведения, взять паузу или отказаться. Предпочтение ещё не означает согласия на платную работу.",
    "speaker": "Обсуждаем вместе",
    "skipInMain": true,
    "optionalFor": "informed_preference",
    "fields": [
      {
        "key": "fit_feedback",
        "label": "Что подходит, что вызывает сомнения и что нужно изменить"
      }
    ]
  },
  "informed_preference__fit_status": {
    "id": "informed_preference__fit_status",
    "phase": "help",
    "kind": "question",
    "title": "Как вы оцениваете, подходит ли вам эта помощь?",
    "explanation": "Можно выбрать способ, попросить сведения, взять паузу или отказаться. Предпочтение ещё не означает согласия на платную работу.",
    "speaker": "Обсуждаем вместе",
    "skipInMain": true,
    "optionalFor": "informed_preference",
    "fields": [
      {
        "key": "fit_status",
        "label": "Ваша предварительная оценка помощи"
      }
    ]
  },
  "helper_fit": {
    "id": "helper_fit",
    "phase": "help",
    "kind": "question",
    "title": "Могу ли я предложить подходящую помощь?",
    "explanation": "Я тоже обозначу своё решение и основания. Если мне не хватает сведений или нужная помощь выходит за мои возможности, скажу об этом.",
    "speaker": "Оценка ведущего",
    "fields": [
      {
        "key": "helper_fit_status",
        "label": "Моя предварительная оценка"
      }
    ]
  },
  "helper_fit__helper_fit_reason": {
    "id": "helper_fit__helper_fit_reason",
    "phase": "help",
    "kind": "question",
    "title": "Почему я считаю эту помощь подходящей или неподходящей?",
    "explanation": "Я тоже обозначу своё решение и основания. Если мне не хватает сведений или нужная помощь выходит за мои возможности, скажу об этом.",
    "speaker": "Оценка ведущего",
    "skipInMain": true,
    "optionalFor": "helper_fit",
    "fields": [
      {
        "key": "helper_fit_reason",
        "label": "Почему я так считаю и что ещё нужно уточнить"
      }
    ]
  },
  "conversation_feedback": {
    "id": "conversation_feedback",
    "phase": "help",
    "kind": "question",
    "title": "Как вам было в этом разговоре?",
    "explanation": "Ваш отклик поможет поправить мой подход. Можно сказать, где я вас не понял или что стоит делать иначе.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "process_feedback",
        "label": "Ваш отклик на разговор"
      }
    ]
  },
  "conversation_feedback__process_adjustment": {
    "id": "conversation_feedback__process_adjustment",
    "phase": "help",
    "kind": "question",
    "title": "Что мне стоит делать иначе, если мы продолжим?",
    "explanation": "Ваш отклик поможет поправить мой подход. Можно сказать, где я вас не понял или что стоит делать иначе.",
    "speaker": "Обсуждаем вместе",
    "skipInMain": true,
    "optionalFor": "conversation_feedback",
    "fields": [
      {
        "key": "process_adjustment",
        "label": "Что сохраняем или меняем"
      }
    ]
  },
  "terms_bridge": {
    "id": "terms_bridge",
    "phase": "terms",
    "kind": "bridge",
    "title": "Хотите обсудить условия продолжения?",
    "explanation": "Если возможная помощь понятна и интересна, я опишу конкретный этап: объём, участие, сроки и цену. Можно завершить сегодняшний разговор без обсуждения покупки.",
    "speaker": "Обсуждаем вместе",
    "fields": []
  },
  "stage": {
    "id": "stage",
    "phase": "terms",
    "kind": "question",
    "title": "Какую задачу предлагаю взять на ближайший этап?",
    "explanation": "Предложу ближайший этап: какую задачу решаем и что рассчитываем получить к его завершению.",
    "speaker": "Предложение ведущего",
    "fields": [
      {
        "key": "agreement_stage_task",
        "label": "Задача этого этапа"
      }
    ]
  },
  "stage__agreement_stage_result": {
    "id": "stage__agreement_stage_result",
    "phase": "terms",
    "kind": "question",
    "title": "Какой результат ожидаем к завершению этапа?",
    "explanation": "Предложу ближайший этап: какую задачу решаем и что рассчитываем получить к его завершению.",
    "speaker": "Предложение ведущего",
    "fields": [
      {
        "key": "agreement_stage_result",
        "label": "Ожидаемый результат этапа"
      }
    ]
  },
  "stage__agreement_stage_limits": {
    "id": "stage__agreement_stage_limits",
    "phase": "terms",
    "kind": "question",
    "title": "Что не входит в этот этап?",
    "explanation": "Предложу ближайший этап: какую задачу решаем и что рассчитываем получить к его завершению.",
    "speaker": "Предложение ведущего",
    "skipInMain": true,
    "optionalFor": "stage",
    "fields": [
      {
        "key": "agreement_stage_limits",
        "label": "Что не входит в этот этап"
      }
    ]
  },
  "scope": {
    "id": "scope",
    "phase": "terms",
    "kind": "question",
    "title": "Что входит в этот этап?",
    "explanation": "Перечислю встречи, материалы и другие части работы. Если нужна связь между встречами, обсудим её отдельно.",
    "speaker": "Предложение ведущего",
    "fields": [
      {
        "key": "terms_scope",
        "label": "Что входит в работу"
      }
    ]
  },
  "scope__agreement_data": {
    "id": "scope__agreement_data",
    "phase": "terms",
    "kind": "question",
    "title": "Как мы будем использовать записи и материалы?",
    "explanation": "Перечислю встречи, материалы и другие части работы. Если нужна связь между встречами, обсудим её отдельно.",
    "speaker": "Предложение ведущего",
    "skipInMain": true,
    "optionalFor": "scope",
    "fields": [
      {
        "key": "agreement_data",
        "label": "Какие данные нужны, что сохраняется и кто получит доступ"
      }
    ]
  },
  "scope__agreement_third_parties": {
    "id": "scope__agreement_third_parties",
    "phase": "terms",
    "kind": "question",
    "title": "Чьё ещё участие или согласие понадобится?",
    "explanation": "Перечислю встречи, материалы и другие части работы. Если нужна связь между встречами, обсудим её отдельно.",
    "speaker": "Предложение ведущего",
    "skipInMain": true,
    "optionalFor": "scope",
    "fields": [
      {
        "key": "agreement_third_parties",
        "label": "Кто ещё участвует и какие согласования нужны"
      }
    ]
  },
  "leader_actions": {
    "id": "leader_actions",
    "phase": "terms",
    "kind": "question",
    "title": "Что беру на себя я?",
    "explanation": "Зафиксируем мои действия и результат, который зависит от моей работы.",
    "speaker": "Предложение ведущего",
    "fields": [
      {
        "key": "agreement_leader_actions",
        "label": "Мои обязательства на этом этапе"
      }
    ]
  },
  "client_actions": {
    "id": "client_actions",
    "phase": "terms",
    "kind": "question",
    "title": "Какое участие будет нужно от вас?",
    "explanation": "Проверим, что действия и нагрузка понятны и реалистичны для вас. Если нет — изменим предложение.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "agreement_client_actions",
        "label": "Ваши действия на этом этапе"
      }
    ]
  },
  "client_actions__agreement_load": {
    "id": "client_actions__agreement_load",
    "phase": "terms",
    "kind": "question",
    "title": "Какую нагрузку потребует работа от каждого из нас?",
    "explanation": "Проверим, что действия и нагрузка понятны и реалистичны для вас. Если нет — изменим предложение.",
    "speaker": "Обсуждаем вместе",
    "skipInMain": true,
    "optionalFor": "client_actions",
    "fields": [
      {
        "key": "agreement_load",
        "label": "Какая нагрузка потребуется каждому"
      }
    ]
  },
  "conditions": {
    "id": "conditions",
    "phase": "terms",
    "kind": "question",
    "title": "Без каких условий эта работа не получится?",
    "explanation": "Отделим необходимое от желательного. Это поможет менять формат, сохраняя возможность выполнить работу.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "agreement_required",
        "label": "Необходимые условия работы"
      }
    ]
  },
  "conditions__agreement_preferred": {
    "id": "conditions__agreement_preferred",
    "phase": "terms",
    "kind": "question",
    "title": "Какие условия желательны, но не обязательны?",
    "explanation": "Отделим необходимое от желательного. Это поможет менять формат, сохраняя возможность выполнить работу.",
    "speaker": "Обсуждаем вместе",
    "skipInMain": true,
    "optionalFor": "conditions",
    "fields": [
      {
        "key": "agreement_preferred",
        "label": "Что желательно, но можно изменить"
      }
    ]
  },
  "schedule": {
    "id": "schedule",
    "phase": "terms",
    "kind": "question",
    "title": "Какой график работы вам подойдёт?",
    "explanation": "Проверим, подходит ли вам такой график.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "terms_schedule",
        "label": "Начало, встречи и завершение этапа"
      }
    ]
  },
  "price": {
    "id": "price",
    "phase": "terms",
    "kind": "question",
    "title": "Сколько стоит весь этап?",
    "explanation": "Укажем полную сумму и валюту, что входит в цену и есть ли отдельные расходы. Неизвестное оставим открытым.",
    "speaker": "Предложение ведущего",
    "fields": [
      {
        "key": "terms_price",
        "label": "Полная цена этапа"
      }
    ]
  },
  "price__terms_payment": {
    "id": "price__terms_payment",
    "phase": "terms",
    "kind": "question",
    "title": "Как проходит оплата?",
    "explanation": "Укажем полную сумму и валюту, что входит в цену и есть ли отдельные расходы. Неизвестное оставим открытым.",
    "speaker": "Предложение ведущего",
    "fields": [
      {
        "key": "terms_payment",
        "label": "Порядок оплаты"
      }
    ]
  },
  "review": {
    "id": "review",
    "phase": "terms",
    "kind": "question",
    "title": "Как проверим пользу этого этапа?",
    "explanation": "Выберем признаки продвижения и договоримся, когда их обсудим.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "terms_review",
        "label": "Как и когда проверим пользу"
      }
    ]
  },
  "change_terms": {
    "id": "change_terms",
    "phase": "terms",
    "kind": "question",
    "title": "Как можно изменить или завершить работу?",
    "explanation": "Заранее разберём, что делать, если задача, обстоятельства или оценка пользы изменятся.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "terms_change",
        "label": "Порядок изменения и завершения работы"
      }
    ]
  },
  "change_terms__agreement_postponement": {
    "id": "change_terms__agreement_postponement",
    "phase": "terms",
    "kind": "question",
    "title": "Как договариваемся о переносах и паузах?",
    "explanation": "Заранее разберём, что делать, если задача, обстоятельства или оценка пользы изменятся.",
    "speaker": "Обсуждаем вместе",
    "skipInMain": true,
    "optionalFor": "change_terms",
    "fields": [
      {
        "key": "agreement_postponement",
        "label": "Как договариваемся о переносах и паузах"
      }
    ]
  },
  "offer_overview": {
    "id": "offer_overview",
    "phase": "terms",
    "kind": "offer_overview",
    "title": "Что в предложении нужно уточнить?",
    "explanation": "Здесь собраны обсуждённые условия. Можно прокомментировать предложение целиком.",
    "speaker": "Обсуждаем вместе",
    "input": "free",
    "fields": []
  },
  "understanding": {
    "id": "understanding",
    "phase": "terms",
    "kind": "question",
    "title": "Как вы поняли это предложение своими словами?",
    "explanation": "Проверим, одинаково ли понимаем результат, участие и условия. Если что-то расходится, поправим запись до решения.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "agreement_client_understanding",
        "label": "Ваше понимание предложения"
      }
    ]
  },
  "understanding__agreement_corrections": {
    "id": "understanding__agreement_corrections",
    "phase": "terms",
    "kind": "question",
    "title": "Что нужно изменить в предложении?",
    "explanation": "Проверим, одинаково ли понимаем результат, участие и условия. Если что-то расходится, поправим запись до решения.",
    "speaker": "Обсуждаем вместе",
    "skipInMain": true,
    "optionalFor": "understanding",
    "fields": [
      {
        "key": "agreement_corrections",
        "label": "Что нужно изменить в предложении"
      }
    ]
  },
  "understanding__agreement_unknown": {
    "id": "understanding__agreement_unknown",
    "phase": "terms",
    "kind": "question",
    "title": "Что ещё нужно выяснить до решения?",
    "explanation": "Проверим, одинаково ли понимаем результат, участие и условия. Если что-то расходится, поправим запись до решения.",
    "speaker": "Обсуждаем вместе",
    "skipInMain": true,
    "optionalFor": "understanding",
    "fields": [
      {
        "key": "agreement_unknown",
        "label": "Что ещё нужно выяснить до решения"
      }
    ]
  },
  "client_decision": {
    "id": "client_decision",
    "phase": "terms",
    "kind": "question",
    "title": "Что вы сейчас выбираете по этому предложению?",
    "explanation": "Можно начать, предложить изменения, запросить сведения, взять паузу или отказаться. Записываем ваше решение по текущим условиям.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "agreement_client_decision",
        "label": "Ваше решение"
      }
    ]
  },
  "leader_decision": {
    "id": "leader_decision",
    "phase": "terms",
    "kind": "question",
    "title": "Готов ли я начать на записанных условиях?",
    "explanation": "Я отдельно обозначу готовность и свои ограничения. Решения каждой стороны сохраняются отдельно.",
    "speaker": "Решение ведущего",
    "fields": [
      {
        "key": "agreement_leader_decision",
        "label": "Моё решение"
      }
    ]
  },
  "outcome_bridge": {
    "id": "outcome_bridge",
    "phase": "outcome",
    "kind": "bridge",
    "title": "Подведём итог сегодняшнего разговора",
    "explanation": "Отметим, что стало понятнее, что ещё открыто и какой следующий шаг вы выбираете.",
    "speaker": "Обсуждаем вместе",
    "fields": []
  },
  "today_outcome": {
    "id": "today_outcome",
    "phase": "outcome",
    "kind": "question",
    "title": "Что сегодня стало понятнее или было решено?",
    "explanation": "Запишем результат с ваших слов. Он может отличаться от того, что вы ожидали в начале.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "today_outcome",
        "label": "Результат сегодняшнего разговора"
      }
    ]
  },
  "remaining": {
    "id": "remaining",
    "phase": "outcome",
    "kind": "question",
    "title": "Что ещё предстоит проверить?",
    "explanation": "Часть выводов можно проверить только на опыте. Назовём то, что пока остаётся открытым.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "remaining_check",
        "label": "Что ещё нужно проверить"
      }
    ]
  },
  "next_choice": {
    "id": "next_choice",
    "phase": "outcome",
    "kind": "question",
    "title": "Что вы выбираете делать дальше?",
    "explanation": "Это может быть совместная или самостоятельная работа, получение сведений, другая помощь или пауза.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "next_choice",
        "label": "Ваш вариант продолжения"
      }
    ]
  },
  "next_action": {
    "id": "next_action",
    "phase": "outcome",
    "kind": "question",
    "title": "О каком ближайшем шаге договоримся?",
    "explanation": "Укажем, кто что делает и когда. Если шаг пока не выбран, можно так и оставить.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "next_step",
        "label": "Кто и что делает дальше"
      }
    ]
  },
  "next_action__next_when": {
    "id": "next_action__next_when",
    "phase": "outcome",
    "kind": "question",
    "title": "Когда вы хотите сделать этот шаг?",
    "explanation": "Укажем, кто что делает и когда. Если шаг пока не выбран, можно так и оставить.",
    "speaker": "Обсуждаем вместе",
    "fields": [
      {
        "key": "next_when",
        "label": "Когда или при каком условии"
      }
    ]
  },
  "next_action__next_check": {
    "id": "next_action__next_check",
    "phase": "outcome",
    "kind": "question",
    "title": "Как проверим результат этого шага?",
    "explanation": "Укажем, кто что делает и когда. Если шаг пока не выбран, можно так и оставить.",
    "speaker": "Обсуждаем вместе",
    "skipInMain": true,
    "optionalFor": "next_action",
    "fields": [
      {
        "key": "next_check",
        "label": "Как проверим результат этого шага"
      }
    ]
  },
  "summary": {
    "id": "summary",
    "phase": "outcome",
    "kind": "summary",
    "title": "Проверим итог разговора",
    "explanation": "Сверим, что стало понятно, что пока открыто и о каком следующем шаге договорились.",
    "speaker": "Подводим итог вместе",
    "fields": []
  }
});
