(() => {
  'use strict';
  const {roles, blocks} = window.CONTENT;
  const byId = id => document.getElementById(id);
  const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let readingRole = 0;
  let quizRole = 0;
  let task = '';
  let questionIndex = -1;
  let answers = Array(12).fill(undefined);
  let focusBlock = 0;
  let toastTimer;
  const options = [
    {value:2,title:'Делаю самостоятельно',detail:'Могу вспомнить недавний пример и объяснить свои действия.'},
    {value:1,title:'Получается с поддержкой',detail:'Использую подсказки или помощь другого человека.'},
    {value:0,title:'Пока затрудняюсь',detail:'Такая ситуация была, но способ действия пока не освоен.'},
    {value:null,title:'Такой ситуации пока не было',detail:'Не могу оценить по недавнему опыту.'}
  ];
  function toast(message){byId('toast').textContent=message;byId('toast').classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>byId('toast').classList.remove('visible'),3000);}
  function renderStory(){
    const role=roles[readingRole];
    byId('role-tabs').innerHTML=roles.map((r,i)=>`<button type="button" data-role="${i}" aria-pressed="${i===readingRole}">${escape(r.title)}</button>`).join('');
    byId('case').innerHTML=`<div class="case-opportunity">${escape(role.opportunity)}</div><h3>${escape(role.storyTitle)}</h3><p class="case-scene">${escape(role.scene)}</p><div class="scenario"><h4>Один возможный ход</h4><p>${escape(role.first)}</p></div><div class="scenario alternative"><h4>Другой возможный ход</h4><p>${escape(role.second)}</p></div><div class="case-outcome"><div class="eyebrow">К чему это может привести</div><p>${escape(role.outcome)}</p></div><ul class="case-actions" aria-label="Что помогает в этой ситуации">${role.actions.map(a=>`<li>${escape(a)}</li>`).join('')}</ul>`;
  }
  function renderSkills(){if(byId('skill-list').dataset.complete==='true')return;byId('skill-list').innerHTML=blocks.map((b,i)=>`<div class="skill-item"><span class="skill-index">0${i+1}</span><div><h3>${escape(b.title)}</h3><p>${escape(b.description)}</p><p class="skill-question">${escape(b.question)}</p></div></div>`).join('');}
  function focusQuiz(){const heading=byId('quiz').querySelector('[data-focus]');if(heading){heading.setAttribute('tabindex','-1');heading.focus({preventScroll:true});}}
  function renderStart(){
    byId('quiz').innerHTML=`<form id="start-form"><div class="eyebrow">Около 5–7 минут</div><h3 data-focus>Вспомните свою<br>реальную задачу</h3><p>Отвечайте по опыту последних недель. Если ситуация не возникала, так и отметьте.</p><label class="quiz-label" for="quiz-role">В какой роли вы сейчас отвечаете?</label><select class="quiz-select" id="quiz-role" name="role">${roles.map((r,i)=>`<option value="${i}" ${i===readingRole?'selected':''}>${escape(r.title)}</option>`).join('')}</select><label class="quiz-label" for="quiz-task">Что вы хотите осуществить?</label><input class="quiz-input" id="quiz-task" name="task" maxlength="180" value="${escape(task)}" placeholder="Например, ${escape(roles[readingRole].task.toLowerCase())}" autocomplete="off"><p class="quiz-note">Можно оставить пустым — тогда используем пример для выбранной роли.</p><button class="button primary quiz-submit" type="submit">Начать самопроверку <span>→</span></button><p class="quiz-note">Контактные данные не нужны. Результат появится сразу.</p></form>`;
    byId('quiz-role').value = String(readingRole);
  }
  function renderQuestion(shouldFocus=true){
    const bIndex=Math.floor(questionIndex/3), localIndex=questionIndex%3;
    const block=blocks[bIndex], q=block.questions[localIndex];
    byId('quiz').innerHTML=`<div class="quiz-top"><span>Блок ${bIndex+1} из 4</span><span>Вопрос ${questionIndex+1} из 12</span></div><div class="quiz-bar" aria-hidden="true"><span style="width:${questionIndex/12*100}%"></span></div><p class="quiz-context">${escape(roles[quizRole].context)}</p><div class="eyebrow" style="color:var(--orange);margin-bottom:12px">${escape(block.title)}</div><h3 class="quiz-question" data-focus>${escape(q.text)}</h3><p class="quiz-hint">${escape(q.hint)}<br>Ваша ситуация: ${escape(roles[quizRole].examples[bIndex])}</p><div class="answers" role="group" aria-label="Выберите ответ">${options.map((o,i)=>`<button class="answer" type="button" data-answer="${i}" aria-pressed="${answers[questionIndex]===o.value}"><span class="answer-circle" aria-hidden="true"></span><span><strong>${o.title}</strong><small>${o.detail}</small></span></button>`).join('')}</div><div class="quiz-nav"><button class="back" type="button" data-action="back">← ${questionIndex===0?'К задаче':'Назад'}</button><button class="button primary" type="button" data-action="next" ${answers[questionIndex]===undefined?'disabled':''}>${questionIndex===11?'Посмотреть карту':'Дальше'} <span>→</span></button></div>`;
    if(shouldFocus)focusQuiz();
  }
  function blockStats(index){const values=answers.slice(index*3,index*3+3);return{independent:values.filter(v=>v===2).length,supported:values.filter(v=>v===1).length,difficult:values.filter(v=>v===0).length,unknown:values.filter(v=>v===null).length};}
  function statsText(s){const parts=[];if(s.independent)parts.push(`Самостоятельно: ${s.independent}`);if(s.supported)parts.push(`С поддержкой: ${s.supported}`);if(s.difficult)parts.push(`Затруднение: ${s.difficult}`);if(s.unknown)parts.push(`Нет примера: ${s.unknown}`);return parts.join(' · ');}
  function trajectory(index){
    const s=blockStats(index);
    const scenario=window.CONSEQUENCES[roles[quizRole].id][index];
    const block=blocks[index];
    if(s.unknown>=2)return {title:block.title,kind:'unknown',observation:'Для этого блока пока мало примеров из вашей практики.',consequence:'По этим ответам нельзя сделать вывод о способе действий или его последствиях. Начните с небольшой задачи и посмотрите, как вы её решаете.',next:scenario.change};
    if(s.difficult>0)return {title:block.title,kind:'difficulty',observation:'Вы отметили затруднения в '+s.difficult+' из трёх ситуаций этого блока.',consequence:scenario.risk,next:scenario.change};
    if(s.supported>0)return {title:block.title,kind:'support',observation:'В части ситуаций вы действуете с поддержкой. Это может быть подходящим способом работы.',consequence:'Если для вашей следующей задачи потребуется самостоятельное действие, а нужная помощь окажется недоступна, возможны остановки и дополнительные согласования. Уточните, какую поддержку стоит сохранить, а что хотите освоить сами.',next:scenario.change};
    return {title:block.title,kind:'strength',observation:'В оценённых ситуациях вы описали самостоятельные действия.',consequence:'По ответам здесь уже есть опора. Способ действия стоит проверить на новой или более сложной задаче: самопроверка не показывает качество конкретного результата.',next:scenario.change};
  }
  function trajectoryHtml(){
    return '<section class="trajectory"><div class="eyebrow">Ваша роль: '+escape(roles[quizRole].title)+'</div><h4>Если продолжать так же</h4><p class="trajectory-intro">Возможные последствия описанных вами действий. Это условные сценарии: сопоставьте их со своей задачей и условиями работы.</p>'+blocks.map((b,i)=>{const t=trajectory(i);return '<div class="trajectory-item '+t.kind+'"><h5>'+escape(t.title)+'</h5><p class="trajectory-observation">'+escape(t.observation)+'</p><p>'+escape(t.consequence)+'</p><p class="trajectory-next"><strong>Что можно развивать.</strong> '+escape(t.next)+'</p></div>';}).join('')+'</section>';
  }
  function renderResults(shouldFocus=true){
    const block=blocks[focusBlock], practice=block.practice;
    byId('quiz').innerHTML=`<div class="eyebrow" style="color:var(--orange);margin-bottom:15px">Самопроверка завершена</div><h3 class="results-title" data-focus>Ваша карта практики</h3><p class="result-task">${escape(roles[quizRole].title)} · ${escape(task)}</p><p>Это сводка ваших ответов, а не оценка компетентности. Выберите блок, который важен для вашей задачи сейчас.</p><div class="result-blocks">${blocks.map((b,i)=>{const s=blockStats(i);return `<div class="result-block"><h4>${escape(b.title)} <span class="mini-dots" aria-hidden="true">${answers.slice(i*3,i*3+3).map(v=>`<span class="${v===2?'independent':v===1?'supported':v===null?'unknown':''}"></span>`).join('')}</span></h4><div class="result-counts">${statsText(s)}${s.unknown>=2?'<br>Для вывода о практике пока мало примеров.':''}</div><button class="practice-choice" type="button" data-practice="${i}" aria-pressed="${i===focusBlock}">${i===focusBlock?'Выбрано для практики':'Посмотреть упражнение'} →</button></div>`;}).join('')}</div>${trajectoryHtml()}<div class="practice-panel" id="practice-panel"><div class="eyebrow">Первая практика · ${escape(block.title)}</div><h4>${escape(practice.title)}</h4><p class="practice-time">${escape(practice.time)}</p><ol>${practice.steps.map(s=>`<li>${escape(s)}</li>`).join('')}</ol><p class="practice-evidence"><strong>Что можно проверить после попытки:</strong> ${escape(practice.evidence)}</p></div><div class="result-tools"><button type="button" data-action="download">Скачать карту и упражнение ↓</button><button type="button" data-action="copy">Скопировать результат</button><button type="button" data-action="restart">Пройти заново</button></div><div class="result-contact"><p>Хотите разобрать свой пример и выбрать обучение? Скопируйте результат и напишите Алексею. Передавать ответы необязательно.</p><a class="button primary" href="https://t.me/shapovalov_vsegda" target="_blank" rel="noopener noreferrer">Обсудить развитие навыков <span>↗</span></a></div>`;
    if(shouldFocus)focusQuiz();
  }
  function resultText(){const b=blocks[focusBlock];const scenarios=blocks.map((block,i)=>{const t=trajectory(i);return t.title+'\n'+t.observation+'\n'+t.consequence+'\nЧто можно развивать: '+t.next;}).join('\n\n');return `МОЯ КАРТА ПРАКТИКИ\nРоль: ${roles[quizRole].title}\nЗадача: ${task}\n\nАвторская самопроверка по моим ответам, не измерение компетентности.\n\n${blocks.map((block,i)=>`${block.title}\n${statsText(blockStats(i))}\n${block.questions.map((q,j)=>`— ${q.text}\n  ${options.find(o=>o.value===answers[i*3+j])?.title||'Нет ответа'}`).join('\n')}`).join('\n\n')}\n\nЕСЛИ ПРОДОЛЖАТЬ ТАК ЖЕ\nУсловные сценарии по моим ответам, не прогноз.\n${scenarios}\n\nВЫБРАННАЯ ПРАКТИКА\n${b.practice.title}\n${b.practice.time}\n${b.practice.steps.map((s,i)=>`${i+1}. ${s}`).join('\n')}\n\nПосле попытки: ${b.practice.evidence}\n\nОбсудить обучение: https://t.me/shapovalov_vsegda\n`;}
  byId('role-tabs').addEventListener('click',event=>{const button=event.target.closest('[data-role]');if(!button)return;readingRole=Number(button.dataset.role);renderStory();const restored=byId('role-tabs').querySelector(`[data-role="${readingRole}"]`);restored?.focus({preventScroll:true});if(questionIndex===-1)renderStart();});
  byId('quiz').addEventListener('input',event=>{if(event.target.id==='quiz-task')task=event.target.value;});
  byId('quiz').addEventListener('change',event=>{if(event.target.id==='quiz-role'){const input=byId('quiz-task');input.placeholder=`Например, ${roles[Number(event.target.value)].task.toLowerCase()}`;}});
  byId('quiz').addEventListener('submit',event=>{if(event.target.id!=='start-form')return;event.preventDefault();quizRole=Number(byId('quiz-role').value);task=byId('quiz-task').value.trim()||roles[quizRole].task;questionIndex=0;renderQuestion();});
  byId('quiz').addEventListener('click',async event=>{
    const button=event.target.closest('button');if(!button)return;
    if(button.dataset.answer!==undefined){answers[questionIndex]=options[Number(button.dataset.answer)].value;byId('quiz').querySelectorAll('[data-answer]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));byId('quiz').querySelector('[data-action="next"]').disabled=false;return;}
    if(button.dataset.practice!==undefined){focusBlock=Number(button.dataset.practice);renderResults(false);const choice=byId('quiz').querySelector(`[data-practice="${focusBlock}"]`);choice?.focus({preventScroll:true});return;}
    switch(button.dataset.action){
      case 'back': if(questionIndex===0){questionIndex=-1;readingRole=quizRole;renderStart();focusQuiz();}else{questionIndex--;renderQuestion();}break;
      case 'next': if(answers[questionIndex]===undefined)return;questionIndex++;if(questionIndex===12){focusBlock=0;renderResults();}else renderQuestion();break;
      case 'restart': answers=Array(12).fill(undefined);questionIndex=-1;readingRole=quizRole;renderStart();focusQuiz();break;
      case 'download': {const url=URL.createObjectURL(new Blob([resultText()],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='моя-карта-навыков-и-практика.txt';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('Карта и упражнение сохранены в файл.');break;}
      case 'copy': try{await navigator.clipboard.writeText(resultText());toast('Результат скопирован. Его можно вставить в сообщение.');}catch{toast('Не удалось скопировать. Скачайте карту в файл.');}break;
    }
  });
  document.querySelectorAll('a[href^="#source-"]').forEach(a=>a.addEventListener('click',()=>{byId('sources').querySelector('details').open=true;}));
  function readingProgress(){const available=document.documentElement.scrollHeight-window.innerHeight;byId('reading-progress').style.width=`${available>0?window.scrollY/available*100:0}%`;}
  window.addEventListener('scroll',readingProgress,{passive:true});window.addEventListener('resize',readingProgress);
  if('IntersectionObserver' in window){const observer=new IntersectionObserver(entries=>{for(const entry of entries){if(entry.isIntersecting){document.querySelectorAll('.contents nav a').forEach(a=>a.classList.toggle('active',a.getAttribute('href')===`#${entry.target.id}`));}}},{rootMargin:'-15% 0px -60% 0px'});['opportunities','challenges','stories','skills','diagnostic'].forEach(id=>observer.observe(byId(id)));}
  renderStory();renderSkills();renderStart();readingProgress();
})();
