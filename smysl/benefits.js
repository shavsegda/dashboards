/* Переключатель контекста обновляет только три примера общих выгод. */
const benefitsSection = document.querySelector('#benefits-for-you');
if (benefitsSection) {
  const examples = {
    development: ['Разобраться, что привлекает в новом направлении', 'Решить, чему сейчас уделить время и силы', 'Проверить интерес небольшой пробой'],
    leadership: ['Выяснить, почему договорённость не выполняется', 'Выбрать, что изменить в организации работы', 'Посмотреть, помогло ли изменение'],
    parenting: ['Понять, что ребёнку сейчас трудно и какая помощь нужна', 'Выбрать, где поддержать, а где дать самостоятельность', 'Заметить, помогает ли выбранный способ'],
    couple: ['Выяснить, что каждый понимает и чего хочет', 'Договориться, как поступить с учётом интересов обоих', 'Проверить, подходит ли договорённость в жизни'],
    society: ['Разобраться в интересах участников, правилах и ограничениях', 'Определить свою позицию и доступный способ участия', 'Оценить, что дало собственное участие']
  };
  const controls = benefitsSection.querySelector('.benefits-contexts');
  const buttons = [...benefitsSection.querySelectorAll('[data-benefits-context]')];
  const outputs = [...benefitsSection.querySelectorAll('[data-benefit-example]')];
  const announcement = benefitsSection.querySelector('.benefits-announcement');
  if (controls && buttons.length === 5 && outputs.length === 3) {
    controls.hidden = false;
    for (const button of buttons) {
      button.addEventListener('click', () => {
        const context = button.dataset.benefitsContext;
        if (!Object.hasOwn(examples, context)) return;
        buttons.forEach((item) => item.setAttribute('aria-pressed', String(item === button)));
        outputs.forEach((output, index) => { output.textContent = examples[context][index]; });
        announcement.textContent = `Примеры: ${button.textContent.trim()}. ${examples[context].join('. ')}.`;
      });
    }
  }
}
