// Код ведущего передаётся только заголовком этому серверу и нигде не сохраняется модулем.
export const DRAFT_ENDPOINT = 'https://tsregyrxtmkxrxvpsvot.supabase.co/functions/v1/meeting-drafts';
export async function requestDrafts(request, accessCode, { signal, fetchImpl = fetch, timeoutMs = 35000 } = {}) {
  if (typeof accessCode !== 'string' || !accessCode.trim() || accessCode.length > 1024 || /[\r\n]/.test(accessCode)) throw new Error('Введите код доступа в меню «Встреча» → «Помощник».');
  const controller = new AbortController();
  const abort = () => controller.abort();
  if (signal?.aborted) abort(); else signal?.addEventListener('abort', abort, { once: true });
  const timeout = setTimeout(abort, timeoutMs);
  try {
    const response = await fetchImpl(DRAFT_ENDPOINT, {
      method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessCode.trim()}` },
      body: JSON.stringify({ answers: request.answers, targets: request.targets, requestId: request.requestId }),
      signal: controller.signal, credentials: 'omit', referrerPolicy: 'no-referrer',
    });
    if (!response.ok) {
      if (response.status === 401 || response.status === 403) throw new Error('Код доступа не подошёл. Проверьте его в настройках помощника.');
      if (response.status === 503) throw new Error('Помощник пока не подключён на сервере. Можно продолжать разговор и заполнять ответы самостоятельно.');
      if (response.status === 429) throw new Error('Помощник получил слишком много запросов. Попробуйте чуть позже.');
      throw new Error('Помощник сейчас не ответил. Можно продолжать разговор и попробовать позже.');
    }
    const body = await response.text();
    if (body.length > 262144) throw new Error('Ответ помощника слишком большой. Попробуйте ещё раз.');
    try { return JSON.parse(body); } catch { throw new Error('Ответ помощника не удалось прочитать. Попробуйте ещё раз.'); }
  } catch (error) {
    if (controller.signal.aborted) throw new Error('Запрос остановлен или помощник не успел ответить за 35 секунд. Можно попробовать ещё раз.');
    if (error instanceof TypeError) throw new Error('Не удалось связаться с помощником. Проверьте интернет или продолжайте без него.');
    throw error;
  } finally { clearTimeout(timeout); signal?.removeEventListener('abort', abort); }
}
