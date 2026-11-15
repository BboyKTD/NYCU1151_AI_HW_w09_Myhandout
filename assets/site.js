(() => {
  const search = document.querySelector('#lesson-search');
  if (search) {
    const cards = [...document.querySelectorAll('.lesson-card')];
    const normalize = text => text.normalize('NFKC').toLowerCase().replace(/\s+/g, '');
    search.addEventListener('input', () => {
      const query = normalize(search.value);
      let count = 0;
      cards.forEach(card => {
        const match = normalize(card.dataset.search).includes(query);
        card.hidden = !match;
        if (match) count++;
      });
      document.querySelector('#search-status').textContent = query
        ? `找到 ${count} 篇講義` : `顯示全部 ${cards.length} 篇講義`;
      document.querySelector('#no-results').hidden = count !== 0;
    });
  }
  document.querySelectorAll('[data-quiz]').forEach(form => {
    const questions = [...form.querySelectorAll('[data-answer]')];
    form.querySelector('.quiz-submit').hidden = false;
    form.addEventListener('submit', event => {
      event.preventDefault();
      let correct = 0;
      let answered = 0;
      questions.forEach(question => {
        const selected = question.querySelector('input:checked');
        const feedback = question.querySelector('.question-feedback');
        if (!selected) {
          feedback.textContent = '尚未作答，請先選一個答案。';
          return;
        }
        answered++;
        const isCorrect = selected.value === question.dataset.answer;
        if (isCorrect) correct++;
        feedback.textContent = isCorrect ? '✓ 答對了，看看你的理由是否也一致。' : '再想一想，請閱讀下方解析後重新作答。';
        question.querySelector('details').open = true;
      });
      form.querySelector('.quiz-result').textContent = `已作答 ${answered}／${questions.length} 題，答對 ${correct} 題。${answered < questions.length ? '還有題目未選答案。' : '可修改答案，再檢查一次。'}`;
    });
  });
  document.querySelectorAll('[data-case-exercise]').forEach(exercise => {
    const draft = exercise.querySelector('[data-exercise-draft]');
    const paper = exercise.querySelector('[data-paper-complete]');
    const gate = exercise.querySelector('.review-gate');
    const review = exercise.querySelector('[data-review]');
    const status = gate.querySelector('.gate-status');
    review.hidden = true;
    gate.hidden = false;
    gate.querySelector('[data-review-unlock]').addEventListener('click', () => {
      if (!draft.value.trim() && !paper.checked) {
        status.textContent = '請先在作答區寫下分析，或勾選已在紙本／其他地方完整作答，再開啟檢討。';
        draft.focus();
        return;
      }
      review.hidden = false;
      review.open = true;
      status.textContent = '已開啟檢討區。請自行展開提示或擬答；本站不會自動評分你的申論。';
      review.querySelector('summary').focus();
    });
  });
  document.querySelectorAll('.print-button').forEach(button => {
    button.hidden = false;
    button.addEventListener('click', () => window.print());
  });
  // 保留案例題的展開與鎖定狀態，避免列印時意外洩露擬答。
  let previouslyOpen = [];
  window.addEventListener('beforeprint', () => {
    previouslyOpen = [...document.querySelectorAll('details')].filter(detail => detail.open);
    document.querySelectorAll('details').forEach(detail => {
      if (!detail.closest('[data-case-exercise]')) detail.open = true;
    });
  });
  window.addEventListener('afterprint', () => {
    document.querySelectorAll('details').forEach(detail => { detail.open = previouslyOpen.includes(detail); });
  });
})();
