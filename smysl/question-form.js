const HELP_LABELS = Object.freeze({ choose: "Помочь разобраться и выбрать", learn: "Научиться делать то, что пока не умею", perspectives: "Обсудить ситуацию с людьми другого опыта", specialist: "Найти специалиста или партнёра", unsure: "Пока не понимаю, какая помощь нужна" });
const FIELD_STEPS = { kind: 0, goal: 0, tried: 1, attempts: 1, unknownDetail: 1, help: 2, role: 2, name: 3, telegram: 3, email: 3, consent: 3 };
const STEP_NAMES = ["Твоя задача", "Что уже происходило", "Какая помощь нужна", "Твой вопрос и контакты"];
const normalizeTelegram = value => value.trim().replace(/^https?:\/\/(?:www\.)?t\.me\//i, "").replace(/^t\.me\//i, "").replace(/^@/, "").replace(/\/$/, "");

export function initProgramForm(doc = document, options = {}) {
  const form = doc.getElementById("question-form");
  if (!form || form.dataset.initialized) return;
  form.dataset.initialized = "true";
  const win = doc.defaultView;
  const byId = id => doc.getElementById(id);
  const steps = [...form.querySelectorAll("[data-question-step]")];
  const submitButton = byId("question-submit");
  const card = byId("question-card-text");
  let step = 0, busy = false, sent = false, pendingPayload = null;
  const chosen = name => form.querySelector(`input[name="${name}"]:checked`)?.value || "";
  const value = name => form.querySelector(`[name="${name}"]`)?.value.trim() || "";
  const checked = name => Boolean(form.querySelector(`[name="${name}"]`)?.checked);

  function answers() {
    return { kind: chosen("kind"), goal: value("goal"), tried: chosen("tried"), attempts: value("attempts"), unknownDetail: value("unknownDetail"), hardToExplain: checked("hardToExplain"), help: [...form.querySelectorAll('input[name="help"]:checked')].map(input => input.value), role: value("role"), name: value("name"), telegram: value("telegram"), email: value("email"), consent: checked("consent") };
  }

  function updateCard() {
    const d = answers();
    card.value = [
      "Что хочу сделать или выбрать: " + d.goal,
      "Что уже пробовал и что получилось: " + (d.tried === "yes" ? d.attempts : "Пока не пробовал"),
      "В чём нужно разобраться: " + (d.unknownDetail || "Пока трудно сформулировать"),
      "Какая помощь была бы полезна: " + d.help.map(key => HELP_LABELS[key]).join("; "),
    ].join("\n\n");
  }

  function clearError(field) {
    const node = byId("error-" + field);
    if (node) node.textContent = "";
    const group = form.querySelector(`[data-field="${field}"]`);
    group?.querySelectorAll("[aria-invalid]").forEach(input => input.removeAttribute("aria-invalid"));
  }

  function showError(field, message) {
    const node = byId("error-" + field);
    if (node) node.textContent = message;
    const group = form.querySelector(`[data-field="${field}"]`);
    group?.querySelectorAll("input,textarea").forEach(input => {
      input.setAttribute("aria-invalid", "true");
      const described = new Set((input.getAttribute("aria-describedby") || "").split(" ").filter(Boolean));
      described.add("error-" + field); input.setAttribute("aria-describedby", [...described].join(" "));
    });
  }

  function syncBranches() {
    const isChoice = chosen("kind") === "choice";
    byId("goal-label").textContent = isChoice ? "Между чем выбираешь и что затрудняет выбор?" : "Что хочешь создать или изменить и почему это важно?";
    byId("goal-hint").textContent = isChoice ? "Рассматриваю… Пока трудно выбрать, потому что…" : "Хочу сделать… Для меня это важно, потому что…";
    const tried = chosen("tried") === "yes";
    byId("attempts-field").hidden = !tried;
    byId("question-attempts").required = tried;
    byId("question-unknown").required = !checked("hardToExplain");
    if (!tried) clearError("attempts");
  }

  function goTo(next, focus = true) {
    step = next;
    steps.forEach((fieldset, index) => { fieldset.hidden = index !== step; });
    byId("question-progress-label").textContent = `Шаг ${step + 1} из 4 — ${STEP_NAMES[step]}`;
    byId("question-progress").setAttribute("aria-valuenow", String(step + 1));
    byId("question-progress").querySelector("span").style.width = `${(step + 1) * 25}%`;
    updateCard();
    if (focus) steps[step].querySelector("legend").focus();
  }

  function validate(index) {
    const d = answers(), errors = [];
    Object.entries(FIELD_STEPS).filter(([, i]) => i === index).forEach(([field]) => clearError(field));
    const fail = (field, message) => errors.push([field, message]);
    if (index === 0) {
      if (!d.kind) fail("kind", "Выбери, с чем хочется разобраться.");
      if (d.goal.length < 5 || d.goal.length > 1600) fail("goal", "Опиши свою задачу: от 5 до 1600 символов.");
    }
    if (index === 1) {
      if (!d.tried) fail("tried", "Укажи, пробовал ли что-нибудь сделать.");
      if (d.attempts.length > 1600 || (d.tried === "yes" && d.attempts.length < 3)) fail("attempts", "Коротко опиши, что пробовал и что получилось.");
      if (d.unknownDetail.length > 1000 || (!d.hardToExplain && d.unknownDetail.length < 3)) fail("unknownDetail", "Напиши, что пока непонятно, или отметь «Пока трудно сформулировать».");
    }
    if (index === 2) {
      if (!d.help.length) fail("help", "Выбери, какая помощь сейчас была бы полезна.");
      if (d.role.length < 2 || d.role.length > 300) fail("role", "Коротко напиши, чем занимаешься и какая у тебя роль.");
    }
    if (index === 3) {
      if (!d.name || d.name.length > 100 || /[\u0000-\u001f\u007f]/.test(d.name)) fail("name", "Укажи, как к тебе обращаться.");
      if (!/^[a-zA-Z][a-zA-Z0-9_]{4,31}$/.test(normalizeTelegram(d.telegram))) fail("telegram", "Укажи Telegram: @username или t.me/username.");
      if (d.email.length > 254 || !/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(d.email)) fail("email", "Проверь адрес электронной почты.");
      if (!d.consent) fail("consent", "Нужно согласие на обработку ответов и связь по указанным контактам.");
    }
    for (const [field, message] of errors) showError(field, message);
    if (errors.length) {
      goTo(index, false);
      form.querySelector(`[data-field="${errors[0][0]}"] input, [data-field="${errors[0][0]}"] textarea`)?.focus();
    }
    return errors.length === 0;
  }

  function draftChanged() {
    // Новый вариант ответов — новая отправка; простой повтор сетевой ошибки сохраняет ID.
    if (!busy) pendingPayload = null;
    updateCard();
  }

  form.addEventListener("change", event => {
    const input = event.target;
    if (input.name === "help" && input.checked) {
      form.querySelectorAll('input[name="help"]').forEach(other => {
        if (other !== input && (input.value === "unsure" || other.value === "unsure")) other.checked = false;
      });
    }
    syncBranches(); draftChanged();
    if (Object.hasOwn(FIELD_STEPS, input.name)) clearError(input.name);
  });
  form.addEventListener("input", event => {
    draftChanged();
    if (Object.hasOwn(FIELD_STEPS, event.target.name)) clearError(event.target.name);
  });
  form.querySelectorAll("[data-question-next]").forEach(button => button.addEventListener("click", () => { if (!busy && validate(step)) goTo(step + 1); }));
  form.querySelectorAll("[data-question-back]").forEach(button => button.addEventListener("click", () => { if (!busy) goTo(step - 1); }));
  byId("question-edit").addEventListener("click", () => { if (!busy) goTo(0); });
  byId("question-copy").addEventListener("click", async () => {
    updateCard(); const status = byId("question-copy-status");
    try {
      const clipboard = options.clipboard || win.navigator.clipboard;
      if (!clipboard?.writeText) throw new Error("Clipboard unavailable");
      await clipboard.writeText(card.value); status.textContent = "Вопрос скопирован.";
    } catch {
      card.focus(); card.select();
      status.textContent = "Текст выделен. Скопируй его через меню браузера или сочетанием клавиш.";
    }
  });

  async function send(event) {
    event?.preventDefault();
    if (busy || sent) return;
    for (let index = 0; index < steps.length; index++) if (!validate(index)) return;
    if (!pendingPayload) pendingPayload = { ...answers(), requestId: win.crypto.randomUUID() };
    busy = true;
    steps.forEach(fieldset => { fieldset.disabled = true; });
    submitButton.disabled = true; submitButton.textContent = "Отправляем…";
    form.setAttribute("aria-busy", "true"); byId("question-send-error").hidden = true;
    const controller = new win.AbortController();
    const timeout = win.setTimeout(() => controller.abort(), 20000);
    try {
      const fetcher = options.fetch || win.fetch.bind(win);
      const response = await fetcher(form.dataset.apiEndpoint, { method: "POST", headers: { "Content-Type": "application/json" }, mode: "cors", credentials: "omit", cache: "no-store", redirect: "error", body: JSON.stringify(pendingPayload), signal: controller.signal });
      const data = await response.json().catch(() => null);
      if (!response.ok || data?.ok !== true || data.id !== pendingPayload.requestId) {
        if (response.status === 400 && data?.field && Object.hasOwn(FIELD_STEPS, data.field)) {
          goTo(FIELD_STEPS[data.field], false); showError(data.field, data.error || "Проверь ответ.");
        }
        throw new Error("Not saved");
      }
      sent = true; form.hidden = true; byId("question-progress-area").hidden = true;
      byId("question-receipt").textContent = data.id;
      byId("question-success").hidden = false;
      byId("question-success").querySelector("h3").focus();
    } catch {
      byId("question-send-error").hidden = false;
      submitButton.textContent = "Повторить отправку";
    } finally {
      win.clearTimeout(timeout); busy = false; form.removeAttribute("aria-busy");
      steps.forEach(fieldset => { fieldset.disabled = false; });
      submitButton.disabled = false;
    }
  }

  form.addEventListener("submit", send);
  syncBranches(); goTo(0, false); submitButton.disabled = false;
  return { send };
}

if (typeof document !== "undefined") initProgramForm(document);
