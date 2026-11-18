/* Пошаговое знакомство: сначала полезная формулировка, затем отправка заявки. */
const form = document.querySelector('#intake-form');
if (form) {
  const $ = (selector) => form.querySelector(selector);
  const all = (selector) => [...form.querySelectorAll(selector)];
  const steps = all('.intake-step');
  const error = $('#intake-error');
  const next = $('#intake-next');
  const back = $('#intake-back');
  const submit = $('#intake-submit');
  const situation = $('#intake-situation');
  const question = $('#intake-question');
  const progress = document.querySelector('#intake-progress');
  const labels = ['Твой контекст', 'Твоя ситуация', 'Нужный результат', 'Люди рядом', 'Ритм участия', 'Вопрос и контакты'];
  const openings = { decision: 'Я выбираю между…', pattern: 'Я замечаю, что снова…', change: 'Я хочу изменить…', curiosity: 'Мне интересно, как устроено…' };
  const desired = { understand: 'Хочу лучше понять происходящее.', choose: 'Хочу определиться с выбором.', first_step: 'Хочу найти первый шаг.' };
  const examples = {
    leadership: { decision: 'Я выбираю между развитием своего дела и партнёрством в другой компании.', pattern: 'Я замечаю, что снова беру на себя работу, которую договорился передать команде.', change: 'Я хочу изменить то, как мы обсуждаем спорные решения в команде.', curiosity: 'Мне интересно, как люди договариваются об общем деле.' },
    development: { decision: 'Я выбираю между привычной работой и новым направлением.', pattern: 'Я замечаю, что снова берусь за несколько интересных дел и не заканчиваю их.', change: 'Я хочу изменить то, как выбираю, чему учиться.', curiosity: 'Мне интересно, как меняются взгляды человека в течение жизни.' },
    parenting: { decision: 'Я выбираю, сколько самостоятельности дать ребёнку в новом деле.', pattern: 'Я замечаю, что снова спорю с ребёнком из-за одних и тех же правил.', change: 'Я хочу изменить то, как мы обсуждаем с ребёнком его ошибки.', curiosity: 'Мне интересно, как дети учатся понимать других людей.' },
    couple: { decision: 'Я выбираю, как обсудить с партнёром важную перемену в нашей жизни.', pattern: 'Я замечаю, что снова откладываю разговор о том, что мне важно.', change: 'Я хочу изменить то, как мы договариваемся об общих делах.', curiosity: 'Мне интересно, как у пары появляются общие привычки и правила.' },
    society: { decision: 'Я выбираю, в каком общем деле мне хотелось бы участвовать.', pattern: 'Я замечаю, что снова читаю противоположные объяснения одного события.', change: 'Я хочу изменить то, как проверяю общественно важные новости.', curiosity: 'Мне интересно, как ИИ меняет отношения между людьми и организациями.' },
    curiosity: { decision: 'Я выбираю, какую из интересных мне тем изучить глубже.', pattern: 'Я замечаю, что снова возвращаюсь к вопросу, почему люди меняют свои убеждения.', change: 'Я хочу изменить то, как разбираюсь в сложных темах.', curiosity: 'Мне интересно, как человек понимает, что для него важно.' }
  };
  let step = 0;
  let busy = false;
  let lastGenerated = '';
  let requestId = null;
  const selected = (name) => all(`input[name="${name}"]:checked`).map((input) => input.value);
  const chosen = (name) => $(`input[name="${name}"]:checked`)?.value || '';
  const clearError = () => { error.hidden = true; error.textContent = ''; all('[aria-invalid="true"]').forEach((el) => { el.removeAttribute('aria-invalid'); const ids = (el.getAttribute('aria-describedby') || '').split(' ').filter((id) => id && id !== 'intake-error'); if (ids.length) el.setAttribute('aria-describedby', ids.join(' ')); else el.removeAttribute('aria-describedby'); }); };
  function fail(message, field) {
    error.textContent = message;
    error.hidden = false;
    if (field) { field.setAttribute('aria-invalid', 'true'); const ids = new Set((field.getAttribute('aria-describedby') || '').split(' ').filter(Boolean)); ids.add('intake-error'); field.setAttribute('aria-describedby', [...ids].join(' ')); field.focus(); }
    return false;
  }
  function updateKind() {
    const kind = chosen('kind');
    $('#intake-situation-area').hidden = !kind;
    if (!kind) return;
    $('#intake-situation-label').textContent = openings[kind];
    situation.placeholder = openings[kind];
    const role = selected('roles')[0] || 'curiosity';
    $('#intake-example').textContent = `Например: ${examples[role][kind]}`;
  }
  function cleanSentence(value) { return value.trim().replace(/[.!?]+$/, ''); }
  function generateQuestion() {
    const intro = openings[chosen('kind')].replace('…', '').trim();
    const text = situation.value.trim();
    const startsWithIntro = text.toLocaleLowerCase('ru').startsWith(intro.toLocaleLowerCase('ru'));
    const startsWithOwn = /^(?:я|мне|мы|как|почему|что|зачем|когда|хочу)(?:\s|[,!?…:]|$)/iu.test(text);
    const completePhrase = /^[А-ЯЁA-Z]/u.test(text);
    const first = startsWithIntro || startsWithOwn || completePhrase ? text : `${intro} ${text.charAt(0).toLocaleLowerCase('ru')}${text.slice(1)}`;
    const result = chosen('desiredResult') === 'custom' ? $('#intake-desired-detail').value.trim() : desired[chosen('desiredResult')];
    const generated = `${cleanSentence(first)}. ${cleanSentence(result)}.`;
    if (!question.value.trim() || question.value === lastGenerated) question.value = generated;
    lastGenerated = generated;
  }
  function showStep(index) {
    step = index;
    clearError();
    steps.forEach((el, i) => { el.hidden = i !== step; });
    back.hidden = step === 0;
    next.hidden = step === steps.length - 1;
    submit.hidden = step !== steps.length - 1;
    document.querySelector('#intake-step-label').textContent = `Шаг ${step + 1} из ${steps.length}`;
    document.querySelector('#intake-step-name').textContent = labels[step];
    progress.setAttribute('aria-valuenow', String(step + 1));
    progress.firstElementChild.style.width = `${((step + 1) / steps.length) * 100}%`;
    if (step === 1) updateKind();
    if (step === 5) generateQuestion();
    steps[step].querySelector('legend').focus({ preventScroll: true });
    const card = document.querySelector('.intake-card');
    if (card.getBoundingClientRect().top < 90) card.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start' });
  }
  function validate(index) {
    clearError();
    if (index === 0 && !selected('roles').length) return fail('Выбери хотя бы один контекст.', $('input[name="roles"]'));
    if (index === 1) {
      if (!chosen('kind')) return fail('Выбери, что тебе сейчас ближе.', $('input[name="kind"]'));
      if (situation.value.trim().length < 10) return fail('Добавь немного подробностей — хотя бы 10 символов.', situation);
      if (situation.value.trim().length > 1200) return fail('Сократи описание до 1200 символов.', situation);
    }
    if (index === 2) {
      if (!chosen('desiredResult')) return fail('Выбери желаемый результат.', $('input[name="desiredResult"]'));
      if (chosen('desiredResult') === 'custom' && $('#intake-desired-detail').value.trim().length < 3) return fail('Напиши, какого результата тебе хочется.', $('#intake-desired-detail'));
    }
    if (index === 3) {
      if (!selected('socialExpectations').length) return fail('Выбери, что тебе хотелось бы получить от общения.', $('input[name="socialExpectations"]'));
      if (selected('socialExpectations').includes('custom') && $('#intake-social-detail').value.trim().length < 3) return fail('Добавь свой вариант.', $('#intake-social-detail'));
    }
    if (index === 4 && !chosen('cadence')) return fail('Выбери, насколько тебе подходит такой ритм.', $('input[name="cadence"]'));
    if (index === 5) {
      if (question.value.trim().length < 10 || question.value.trim().length > 2400) return fail('Проверь формулировку: от 10 до 2400 символов.', question);
      if (!telegramUsername($('#intake-telegram').value)) return fail('Укажи имя пользователя Telegram: например, @username или t.me/username.', $('#intake-telegram'));
      const email = $('#intake-email');
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim()) || email.value.trim().length > 254) return fail('Проверь адрес электронной почты.', email);
    }
    return true;
  }
  function telegramUsername(value) {
    const normalized = value.trim().replace(/^https?:\/\//i, '').replace(/^(?:www\.)?t\.me\//i, '').replace(/^@/, '').replace(/\/$/, '');
    return /^[A-Za-z][A-Za-z0-9_]{4,31}$/.test(normalized) ? `@${normalized}` : '';
  }
  async function copyQuestion(status) {
    const text = question.value.trim();
    if (!text) return;
    try {
      if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(text);
      else throw new Error('clipboard unavailable');
      status.textContent = 'Вопрос скопирован';
    } catch {
      const scratch = document.createElement('textarea');
      scratch.value = text; scratch.style.position = 'fixed'; scratch.style.opacity = '0'; document.body.append(scratch); scratch.select();
      let copied = false;
      try { copied = document.execCommand('copy'); } catch { /* Выделение ниже остаётся запасным способом. */ }
      scratch.remove();
      if (copied) status.textContent = 'Вопрос скопирован';
      else { status.textContent = 'Выдели текст вопроса и скопируй его.'; if (!form.hidden) { question.focus(); question.select(); } }
    }
  }
  next.addEventListener('click', () => { if (!busy && validate(step)) showStep(step + 1); });
  back.addEventListener('click', () => { if (!busy) showStep(step - 1); });
  form.addEventListener('change', (event) => {
    clearError();
    if (event.target.name === 'kind') updateKind();
    if (event.target.name === 'desiredResult') $('#intake-desired-area').hidden = chosen('desiredResult') !== 'custom';
    if (event.target.name === 'socialExpectations') $('#intake-social-area').hidden = !selected('socialExpectations').includes('custom');
  });
  form.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && event.target.tagName !== 'TEXTAREA' && event.target.tagName !== 'BUTTON') {
      event.preventDefault();
      if (step < 5 && !busy && validate(step)) showStep(step + 1);
    }
  });
  $('#intake-copy').addEventListener('click', () => copyQuestion($('#intake-copy-status')));
  document.querySelector('#intake-success-copy').addEventListener('click', () => copyQuestion(document.querySelector('#intake-success-copy-status')));
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (busy || step !== 5) return;
    for (let i = 0; i < steps.length; i++) {
      if (!validate(i)) { if (i !== step) { showStep(i); validate(i); } return; }
    }
    busy = true; submit.disabled = true; back.disabled = true; submit.textContent = 'Отправляем…';
    try {
      requestId ||= crypto.randomUUID();
      const payload = { requestId, roles: selected('roles'), kind: chosen('kind'), situation: situation.value.trim(), desiredResult: chosen('desiredResult'), desiredDetail: chosen('desiredResult') === 'custom' ? $('#intake-desired-detail').value.trim() : '', socialExpectations: selected('socialExpectations'), socialDetail: selected('socialExpectations').includes('custom') ? $('#intake-social-detail').value.trim() : '', cadence: chosen('cadence'), question: question.value.trim(), telegram: telegramUsername($('#intake-telegram').value), email: $('#intake-email').value.trim(), website: $('#intake-website').value };
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 20000);
      let response;
      try { response = await fetch(form.dataset.apiEndpoint || '/api/requests', { method: 'POST', credentials: 'omit', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), signal: controller.signal }); }
      finally { clearTimeout(timeout); }
      const result = await response.json().catch(() => null);
      if (!response.ok || !result?.ok || !result?.id) throw new Error(result?.error || 'Не удалось отправить заявку. Попробуй ещё раз — ответы сохранены на странице.');
      form.hidden = true; document.querySelector('#intake-progress-area').hidden = true;
      const success = document.querySelector('#intake-success'); success.hidden = false;
      document.querySelector('#intake-request-number').textContent = `Номер заявки: ${result.id}`;
      success.querySelector('h3').focus();
    } catch (err) {
      fail(err.name === 'AbortError' ? 'Не дождались ответа сервера. Попробуй отправить ещё раз — ответы сохранены на странице.' : err.message || 'Не удалось отправить. Попробуй ещё раз.');
    } finally { busy = false; submit.disabled = false; back.disabled = false; submit.textContent = 'Получить личный разбор'; }
  });
}
