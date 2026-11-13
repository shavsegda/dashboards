'use strict';

// Упражнение работает локально: ответы не отправляются в сеть.
const scenarios = {
  feedback: {name:'замечание по работе',event:'Коллега попросил переделать один раздел.',verdict:'Я совершенно неспособный.',fact:'В одном разделе нужны исправления.'},
  opportunity: {name:'ожидание провала',event:'Увидел интересную вакансию и пока не отправил отклик.',verdict:'Меня сразу разоблачат: я ничего не умею.',fact:'Я пока не отправил отклик. Ответ работодателя мне неизвестен.'},
  perfect: {name:'требование безупречности',event:'Нашёл две неточности в готовой работе.',verdict:'Если есть ошибки, значит я недостаточно хорош.',fact:'В этой работе есть две неточности, которые можно исправить.'},
  approval: {name:'согласие ради одобрения',event:'Меня попросили помочь в выходной, хотя у меня были свои планы.',verdict:'Если откажусь, я плохой человек.',fact:'У меня есть свои планы, и я получил просьбу. Ответ на неё ещё можно выбрать.'},
  comparison: {name:'сравнение с чужими успехами',event:'Прочитал о повышении знакомого.',verdict:'Я ничего не добился и хуже всех.',fact:'Знакомый получил повышение. Это событие не описывает всю мою жизнь.'}
};
const fields = ['event','verdict','fact'];
const storageKey = 'selfesteem-practice-v1';
let selectedScenario = 'feedback';
let currentStep = 0;
const form = document.getElementById('exercise-form');
const result = document.getElementById('exercise-result');
const message = document.getElementById('exercise-message');
const error = document.getElementById('field-error');
const savedBanner = document.getElementById('saved-banner');
const fieldNodes = fields.map(id => document.getElementById(id));

function readAnswers() {
  return Object.fromEntries(fields.map((id,index) => [id,fieldNodes[index].value.trim()]));
}
function hasSavedRecord() {
  try { return localStorage.getItem(storageKey) !== null; } catch { return false; }
}
function validateRecord(record) {
  return record && fields.every(id => typeof record[id] === 'string' && record[id].trim().length > 0 && record[id].length <= 2000);
}
function notify(text) { message.textContent = text; }
function showStep(step, moveFocus = true) {
  currentStep = Math.max(0,Math.min(2,step));
  form.hidden = false;
  result.hidden = true;
  document.querySelectorAll('.exercise-step').forEach((node,index) => { node.hidden = index !== currentStep; });
  document.getElementById('step-label').textContent = `ШАГ 0${currentStep + 1} / 03`;
  document.getElementById('progress-fill').style.width = `${(currentStep + 1) / 3 * 100}%`;
  document.getElementById('previous').hidden = currentStep === 0;
  document.getElementById('next').textContent = currentStep === 2 ? 'Посмотреть записи →' : 'Дальше →';
  error.textContent = '';
  fieldNodes.forEach(field => field.removeAttribute('aria-invalid'));
  if (moveFocus) fieldNodes[currentStep].focus({preventScroll:true});
}
function showResult(moveFocus = true) {
  const answers = readAnswers();
  fields.forEach(id => { document.getElementById(`result-${id}`).textContent = answers[id]; });
  form.hidden = true;
  result.hidden = false;
  document.getElementById('step-label').textContent = 'ЗАПИСЬ ГОТОВА';
  document.getElementById('progress-fill').style.width = '100%';
  if (moveFocus) document.getElementById('result-title').focus({preventScroll:true});
}
function exportText() {
  const answers = readAnswers();
  return `МОЯ ЗАПИСЬ\n\nЧто произошло\n${answers.event}\n\nЧто я решил о себе\n${answers.verdict}\n\nКонкретное описание\n${answers.fact}\n\nЭто письменное наблюдение, а не тест или диагностика.\n`;
}

document.querySelectorAll('[data-scenario]').forEach(button => {
  button.addEventListener('click',() => {
    selectedScenario = button.dataset.scenario;
    const scenario = scenarios[selectedScenario];
    document.querySelectorAll('[data-scenario]').forEach(node => {
      const active = node === button;
      node.classList.toggle('active',active);
      node.setAttribute('aria-pressed',String(active));
    });
    fields.forEach((id,index) => {
      document.getElementById(`sample-${id}`).textContent = id === 'verdict' ? `«${scenario[id]}»` : scenario[id];
      fieldNodes[index].placeholder = scenario[id];
    });
    document.getElementById('selection-status').textContent = `Выбран пример: ${scenario.name}. Ваши записи не изменены.`;
  });
});

form.addEventListener('submit',event => {
  event.preventDefault();
  const field = fieldNodes[currentStep];
  if (!field.value.trim()) {
    error.textContent = 'Добавьте свою запись или подставьте демонстрационный пример.';
    field.setAttribute('aria-invalid','true');
    field.focus({preventScroll:true});
    return;
  }
  notify('');
  if (currentStep < 2) showStep(currentStep + 1);
  else showResult();
});
document.getElementById('previous').addEventListener('click',() => { notify(''); showStep(currentStep - 1); });
document.getElementById('use-example').addEventListener('click',() => {
  const field = fieldNodes[currentStep];
  if (field.value.trim()) {
    notify('В этом шаге уже есть запись. Сначала очистите поле, если хотите заменить её примером.');
    field.focus({preventScroll:true});
    return;
  }
  field.value = scenarios[selectedScenario][fields[currentStep]];
  error.textContent = '';
  field.removeAttribute('aria-invalid');
  notify('Подставлен демонстрационный пример. Его можно изменить.');
  field.focus({preventScroll:true});
});
document.getElementById('edit-result').addEventListener('click',() => { notify(''); showStep(0); });
document.getElementById('copy-result').addEventListener('click',async () => {
  try {
    await navigator.clipboard.writeText(exportText());
    notify('Запись скопирована.');
  } catch {
    const selection = window.getSelection();
    if (selection) {
      const range = document.createRange();
      range.selectNodeContents(document.querySelector('.result-record'));
      selection.removeAllRanges();
      selection.addRange(range);
    }
    notify('Автоматическое копирование недоступно. Записи выделены — скопируйте их обычной командой браузера.');
  }
});
document.getElementById('download-result').addEventListener('click',() => {
  const url = URL.createObjectURL(new Blob([exportText()],{type:'text/plain;charset=utf-8'}));
  const link = document.createElement('a');
  link.href = url;
  link.download = 'moya-zapis-samootsenka.txt';
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url),1000);
  notify('Файл подготовлен к скачиванию.');
});
document.getElementById('save-result').addEventListener('click',() => {
  try {
    localStorage.setItem(storageKey,JSON.stringify(readAnswers()));
    savedBanner.hidden = false;
    notify('Запись сохранена только в браузере на этом устройстве. Удалить её можно кнопкой «Очистить записи» или «Удалить».');
  } catch {
    notify('Браузер не разрешил сохранение. Можно скачать или скопировать запись.');
  }
});
document.getElementById('restore').addEventListener('click',() => {
  if (fieldNodes.some(field => field.value.trim())) {
    notify('На странице уже есть запись. Чтобы открыть сохранённую, сначала очистите текст в полях. Кнопка «Очистить записи» удалит и сохранённую копию.');
    return;
  }
  try {
    const record = JSON.parse(localStorage.getItem(storageKey));
    if (!validateRecord(record)) { notify('Сохранённая запись не читается. Её можно удалить и начать заново.'); return; }
    fields.forEach((id,index) => { fieldNodes[index].value = record[id]; });
    showResult();
    notify('Открыта запись с этого устройства.');
  } catch { notify('Не удалось прочитать запись. Можно начать новое упражнение.'); }
});
document.getElementById('delete-saved').addEventListener('click',() => {
  try {
    localStorage.removeItem(storageKey);
    savedBanner.hidden = true;
    notify('Сохранённая копия удалена. Записи, открытые на странице, пока остаются.');
  } catch { notify('Не удалось удалить копию. Проверьте настройки хранения данных браузера.'); }
});
document.getElementById('clear-result').addEventListener('click',() => {
  fieldNodes.forEach(field => { field.value = ''; });
  fields.forEach(id => { document.getElementById(`result-${id}`).textContent = ''; });
  let removed = true;
  try { localStorage.removeItem(storageKey); } catch { removed = false; }
  savedBanner.hidden = !hasSavedRecord();
  showStep(0);
  notify(removed ? 'Записи очищены на странице и в хранилище этого браузера.' : 'Поля очищены. Браузер не разрешил удалить сохранённую копию.');
});

document.getElementById('exercise-ui').hidden = false;
savedBanner.hidden = !hasSavedRecord();
showStep(0,false);
