const labels = {leadership:'Люди и общее дело', development:'Собственное развитие', parenting:'Родительство', couple:'Отношения в паре', society:'Общество и ИИ'};
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const cleanText = value => String(value ?? '').replace(/\[([^\]]+)\]\([^)]*\)/g,'$1').replace(/\*\*|__/g,'').replace(/(?<!\w)\*|\*(?!\w)/g,'').trim();
const text = value => escapeHTML(cleanText(value));
const paragraphs = value => (Array.isArray(value) ? value : String(value ?? '').split(/\n\s*\n/)).filter(Boolean).map(item => `<p>${text(item)}</p>`).join('');
const list = values => `<ul>${values.map(value => `<li>${text(value)}</li>`).join('')}</ul>`;
let curriculum = [];
let searchRestoreOpenIds = null;

function renderRole(role) {
  return `<article class="module-role"><h4>${labels[role.id]}</h4><p><strong>Задача.</strong> ${text(role.task)}</p><p><strong>Что сможешь показать.</strong> ${text(role.result)}</p><p><strong>Польза.</strong> ${text(role.benefit)}</p><p><strong>Пример ситуации.</strong> ${text(role.difficulty)}</p></article>`;
}

function renderWeek(week,profile,query,module) {
  const applications = Object.entries(week.applications).filter(([id])=>profile==='all'||id===profile);
  const matched = !!query && JSON.stringify(week).toLocaleLowerCase('ru').includes(query);
  return `<details class="week" id="week-${week.week}" ${matched?'open data-search-match="true"':''}>
    <summary><span class="week-index"><strong>Неделя ${String(week.week).padStart(2,'0')}</strong><small>${week.week-module.start+1}-я в модуле</small></span><span>${text(week.title)}</span></summary>
    <div class="week-body"><dl class="week-dl">
      <div class="wide"><dt>С чего начнём исследование</dt><dd class="week-question">${text(week.question)}</dd></div>
      <div class="wide"><dt>В чём разберёмся</dt><dd>${text(week.concepts)}</dd></div>
      <div><dt>На что опираемся</dt><dd>${text(week.prerequisites)}</dd></div>
      <div><dt>Источники и тема</dt><dd>${text(week.source)}</dd></div>
      <div class="wide"><dt>Что пробуем и как смотрим на результат</dt><dd>${text(week.result)}</dd></div>
    </dl><div class="applications"><h5>Как это связано с жизнью</h5>${applications.map(([id,application])=>`<p class="application"><strong>${labels[id]}:</strong> ${text(application)}</p>`).join('')}</div></div>
  </details>`;
}

function renderModule(module,profile,query,openIds) {
  const allModuleText = `${module.title} ${JSON.stringify(module.global)} ${module.overview.join(' ')} ${JSON.stringify(module.portraits)} ${JSON.stringify(module.learningOutcomes || [])}`.toLocaleLowerCase('ru');
  const broadMatch = query && allModuleText.includes(query);
  const matchingWeeks = query ? module.weeks.filter(week=>JSON.stringify(week).toLocaleLowerCase('ru').includes(query)) : [];
  const weeks = query && matchingWeeks.length ? matchingWeeks : query && !broadMatch ? [] : module.weeks;
  if (query && !broadMatch && !weeks.length) return '';
  const roles = module.portraits.filter(role=>profile==='all'||role.id===profile);
  const open = query || openIds.has(module.id);
  return `<details class="module" id="module-${module.id}" data-module="${module.id}" ${open?'open':''}>
    <summary><span class="module-no">${String(module.id).padStart(2,'0')}</span><span class="module-summary-copy"><span class="module-title">${text(module.title)}</span><span class="module-benefit">${text(module.global.benefit)}</span></span><span class="module-weeks"><span>${module.weeksCount} учебных недель</span><span>Недели ${module.start}–${module.end}</span></span><span class="module-toggle" aria-hidden="true"></span></summary>
    <div class="module-body">
      <div class="module-learning-header"><div class="module-benefit-block"><h4>Что это даст тебе</h4>${paragraphs(module.global.benefit)}</div><div class="module-outcomes"><h4>Чему будем учиться</h4>${list(module.learningOutcomes || [])}</div></div>
      <div class="module-global"><div class="global-block"><span>Задача модуля</span>${paragraphs(module.global.task)}</div><div class="global-block"><span>Как увидим результат</span>${paragraphs(module.global.result)}</div><div class="global-block difficulty"><span>Когда это особенно полезно</span>${paragraphs(module.global.difficulty)}</div></div>
      ${module.global.notes.length ? `<div class="module-notes">${paragraphs(module.global.notes)}</div>`:''}
      ${module.overview.length ? `<details class="module-overview"><summary>Подробнее о занятиях и связях с другими темами</summary><div>${paragraphs(module.overview)}</div></details>`:''}
      <h4 class="module-roles-title">Где пригодится</h4><p class="module-roles-caption">Задача, результат и польза для ${profile==='all'?'каждой жизненной ситуации':'выбранной ситуации'}</p><div class="module-roles">${roles.map(renderRole).join('')}</div>
      <div class="weeks-heading"><h4>Что внутри</h4><span>Все недели модуля · ${query?`${weeks.length} по запросу`:`${module.weeksCount} тем`} · раскрой интересующую</span></div>
      <p class="week-numbering-note">Номера недель в опорах относятся к этому модулю, если не указан другой.</p>
      ${query && broadMatch && !matchingWeeks.length ? '<p class="search-module-note">Запрос нашёлся в описании модуля. Ниже можно посмотреть все его недели.</p>' : ''}
      ${weeks.map(week=>renderWeek(week,profile,query,module)).join('')}
    </div>
  </details>`;
}

function renderCurriculum() {
  const query = document.querySelector('#program-search').value.trim().toLocaleLowerCase('ru');
  const profile = document.querySelector('#program-profile').value;
  let openIds = new Set([...document.querySelectorAll('.module[open]')].map(el=>Number(el.dataset.module)));
  if(query && searchRestoreOpenIds===null)searchRestoreOpenIds=new Set(openIds);
  if(!query && searchRestoreOpenIds!==null){openIds=searchRestoreOpenIds;searchRestoreOpenIds=null;}
  const html = curriculum.map(module=>renderModule(module,profile,query,openIds)).filter(Boolean);
  document.querySelector('#curriculum').innerHTML = html.join('');
  document.querySelector('#no-results').hidden = !!html.length;
  const matchedWeeks = document.querySelectorAll('.week[data-search-match="true"]').length;
  const suffix=profile==='all'?' · Примеры: все ситуации':` · Примеры: ${labels[profile]}`;
  document.querySelector('#program-count').textContent = (query ? `Найдено модулей: ${html.length} · Совпадений в неделях: ${matchedWeeks}` : '11 модулей · 103 учебные недели')+suffix;
  document.querySelector('#clear-search').hidden=!query;
  syncExpandLabel();
}

function syncExpandLabel(){
  const modules=[...document.querySelectorAll('.module')];
  const allOpen=modules.length>0&&modules.every(module=>module.open);
  document.querySelector('#expand-modules').textContent=allOpen?'Свернуть все модули −':'Раскрыть все модули ＋';
  document.querySelector('#expand-modules').disabled=!modules.length;
}

document.querySelectorAll('.mobile-nav a').forEach(link=>link.addEventListener('click',()=>{document.querySelector('.mobile-nav').open=false;}));
document.querySelector('#expand-modules').addEventListener('click',()=>{
  const modules=[...document.querySelectorAll('.module')];
  const shouldOpen=!modules.every(module=>module.open);
  modules.forEach(module=>module.open=shouldOpen);
  syncExpandLabel();
});
document.querySelector('#curriculum').addEventListener('toggle',event=>{if(event.target.classList.contains('module'))syncExpandLabel();},true);
document.querySelector('#clear-search').addEventListener('click',()=>{const search=document.querySelector('#program-search');search.value='';clearTimeout(searchTimer);renderCurriculum();search.focus();});
let searchTimer;
document.querySelector('#program-search').addEventListener('input',()=>{clearTimeout(searchTimer);searchTimer=setTimeout(renderCurriculum,180);});
document.querySelector('#program-profile').addEventListener('change',renderCurriculum);

// Публикуем весь маршрут, сохраняя раскрывающиеся подробности и пять способов применения.
try {
  const curriculumResponse=await fetch('curriculum.json');
  if(!curriculumResponse.ok)throw new Error('Содержимое не загружено');
  const data=await curriculumResponse.json();
  if(data.modules.length!==11)throw new Error('Неполная программа');
  curriculum=data.modules;renderCurriculum();
  if(/^#(?:module|week)-\d+$/.test(location.hash)){
    const target=document.querySelector(location.hash);
    if(target){target.open=true;target.closest('.module').open=true;target.scrollIntoView();}
  }
} catch(error) {
  console.error(error);
  document.querySelector('#curriculum').innerHTML='<p>Интерактивная программа не загрузилась. <a class="text-link" href="program.html">Открыть весь маршрут отдельной страницей ↗</a></p>';
}
