import { AI_DRAFT_LABELS, isDraftCurrent, normaliseAiDrafts } from './ai-drafts.mjs';

// Возвращает панель или null. Состояние меняют только callbacks вызывающего интерфейса.
// onAccept(key), onReject(key), onUseQuestion(question, key).
// Все значения выводятся через текстовый dom(), без innerHTML и исполнения разметки.
export function renderDraftPanel({ key, session, parent, onAccept, onReject, onUseQuestion, dom }) {
  const draft = normaliseAiDrafts(session.aiDrafts || {})[key];
  if (!draft || draft.status !== 'suggested' || !isDraftCurrent(session, key)) return null;
  const panel = dom('section', 'ai-draft-panel'); panel.setAttribute('aria-label', 'Предложение записи');
  panel.append(dom('h3', 'ai-draft-title', 'Предложение записи'));
  panel.append(dom('p', 'ai-draft-note', 'Помощник предложил запись по тому, что уже обсуждали. Проверьте, точно ли она передаёт смысл.'));
  if (draft.text.trim()) panel.append(dom('p', 'ai-draft-text', draft.text));
  if (draft.basis.length) {
    const sources = dom('div', 'ai-draft-basis'); sources.append(dom('h4', '', 'На какие слова опирается запись'));
    for (const item of draft.basis) {
      const source = dom('div', 'ai-draft-source');
      source.append(dom('p', 'ai-draft-source-label', AI_DRAFT_LABELS[item.key]), dom('blockquote', 'ai-draft-quote', item.quote));
      sources.append(source);
    }
    panel.append(sources);
  }
  if (draft.question) panel.append(dom('p', 'ai-draft-question', `Можно спросить: ${draft.question}`));
  const actions = dom('div', 'ai-draft-actions');
  const status = dom('p', 'ai-draft-action-status'); status.setAttribute('role', 'status');
  const button = (label, callback) => {
    const item = dom('button', 'button button-light', label); item.type = 'button';
    item.addEventListener('click', async () => {
      item.disabled = true; status.textContent = '';
      try { await callback(); }
      catch (error) { status.textContent = error instanceof Error ? error.message : 'Не удалось применить действие. Попробуйте ещё раз.'; }
      finally { item.disabled = false; }
    });
    actions.append(item);
  };
  if (draft.text.trim() && typeof onAccept === 'function') button('Записать этот вариант', () => onAccept(key));
  if (draft.question && typeof onUseQuestion === 'function') button('Перейти к вопросу', () => onUseQuestion(draft.question, key));
  if (typeof onReject === 'function') button('Не использовать', () => onReject(key));
  panel.append(actions, status);
  if (draft.text.trim()) panel.append(dom('p', 'ai-draft-note', 'Запись появится в поле ответа. Её можно будет изменить.'));
  parent.append(panel);
  return panel;
}
