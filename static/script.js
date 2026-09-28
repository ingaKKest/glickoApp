document.addEventListener('DOMContentLoaded', () => {
  const revealBtn = document.getElementById('reveal-btn');
  const answerBlock = document.getElementById('answer-block');
  const gradeButtons = document.getElementById('grade-buttons');
  const questionText = document.getElementById('question-text');
  const answerText = document.getElementById('answer-text');
  const topicBadge = document.getElementById('topic-badge');
  const qCount = document.getElementById('q-count');
  const questionImage = document.getElementById('question-image');
  const answerImage = document.getElementById('answer-image');

  if (!revealBtn) return;

  revealBtn.addEventListener('click', () => {
    answerBlock.classList.remove('hidden');
    gradeButtons.classList.remove('hidden');
    revealBtn.classList.add('hidden');
  });

  function setImage(imgEl, url) {
    if (url) {
      imgEl.src = url;
      imgEl.classList.remove('hidden');
    } else {
      imgEl.removeAttribute('src');
      imgEl.classList.add('hidden');
    }
  }

  document.querySelectorAll('.btn-grade').forEach(btn => {
    btn.addEventListener('click', async () => {
      document.querySelectorAll('.btn-grade').forEach(b => b.disabled = true);
      const score = parseFloat(btn.dataset.score);

      try {
        const res = await fetch('/study/answer', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ score })
        });
        const data = await res.json();

        if (data.empty) {
          window.location.href = '/study/complete';
          return;
        }

        const q = data.next;
        topicBadge.textContent = q.topic_name;
        questionText.textContent = q.text;
        answerText.textContent = q.answer || 'No reference answer saved for this question.';
        setImage(questionImage, q.image_url);
        setImage(answerImage, q.answer_image_url);
        qCount.textContent = q.count + 1;

        answerBlock.classList.add('hidden');
        gradeButtons.classList.add('hidden');
        revealBtn.classList.remove('hidden');
        document.querySelectorAll('.btn-grade').forEach(b => b.disabled = false);
      } catch (err) {
        alert('Something went wrong saving that answer. Please try again.');
        document.querySelectorAll('.btn-grade').forEach(b => b.disabled = false);
      }
    });
  });
});
