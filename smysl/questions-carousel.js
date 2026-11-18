/* Ручная карусель вопросов с доступным исходным списком без JavaScript. */
const questionCarousel = document.querySelector('#questions-carousel .questions-carousel');
if (questionCarousel) {
  const slides = [...questionCarousel.querySelectorAll('.questions-slide')];
  const controls = questionCarousel.querySelector('.questions-controls');
  const counter = questionCarousel.querySelector('.questions-counter');
  const announcement = questionCarousel.querySelector('.questions-announcement');
  let current = 0;
  function showQuestion(index, announce = true) {
    current = (index + slides.length) % slides.length;
    slides.forEach((slide, i) => { slide.hidden = i !== current; });
    counter.textContent = `${current + 1} из ${slides.length}`;
    if (announce) announcement.textContent = `Вопрос ${current + 1} из ${slides.length}. ${slides[current].textContent.trim()}`;
  }
  if (slides.length) {
    questionCarousel.classList.add('is-enhanced');
    controls.hidden = false;
    showQuestion(0, false);
    questionCarousel.querySelector('.questions-previous').addEventListener('click', () => showQuestion(current - 1));
    questionCarousel.querySelector('.questions-next').addEventListener('click', () => showQuestion(current + 1));
    questionCarousel.addEventListener('keydown', (event) => {
      if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || event.target.closest('input, textarea, select, [contenteditable="true"]')) return;
      if (event.key === 'ArrowLeft') { event.preventDefault(); showQuestion(current - 1); }
      if (event.key === 'ArrowRight') { event.preventDefault(); showQuestion(current + 1); }
    });
  }
}
