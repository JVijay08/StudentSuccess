(() => {
  const examples = {
    math: ['Open your notes. Try problem one.', 'You don\u2019t need to finish the whole set to get started.'],
    essay: ['Write one sentence. Let it be rough.', 'A first draft only needs to give you something to work with.'],
    exam: ['Close the book. Recall three ideas.', 'Find one thing you remember, then one thing to revisit.']
  };
  const done = document.getElementById('lab-done');
  if (!done) return;
  const feedback = document.getElementById('lab-feedback');
  const scene = document.getElementById('desk-scene');
  const arrange = document.getElementById('arrange-desk');
  const assignments = { math: 'The whole problem set.', essay: 'That unwritten essay.', exam: 'Everything on the exam.' };
  arrange.hidden = false;
  arrange.addEventListener('click', () => {
    const arranged = scene.classList.toggle('is-arranged');
    arrange.setAttribute('aria-pressed', String(arranged));
    arrange.innerHTML = arranged ? 'Spread it out again <span aria-hidden="true">&#8634;</span>' : 'Find a starting point <span aria-hidden="true">&#8599;</span>';
    document.getElementById('desk-status').textContent = arranged
      ? 'One assignment. Five minutes. A place to begin.'
      : 'A plan can start smaller than you think.';
  });
  document.querySelectorAll('[data-example]').forEach(button => {
    button.addEventListener('click', () => {
      document.querySelectorAll('[data-example]').forEach(tab => tab.setAttribute('aria-pressed', String(tab === button)));
      const [title, detail] = examples[button.dataset.example];
      document.getElementById('lab-task').textContent = title;
      document.getElementById('lab-detail').textContent = detail;
      document.getElementById('desk-assignment').textContent = assignments[button.dataset.example];
      done.checked = false;
      done.closest('.start-lab').classList.remove('is-ready');
      feedback.textContent = 'A beginning counts.';
    });
  });
  done.addEventListener('change', () => {
    done.closest('.start-lab').classList.toggle('is-ready', done.checked);
    feedback.textContent = done.checked ? 'That\u2019s your way in. One small step.' : 'A beginning counts.';
  });
})();
