document.addEventListener("DOMContentLoaded", () => {
  const subjectSelect = document.getElementById("add-q-subject");
  const topicSelect = document.getElementById("add-q-topic");
  const addQForm = document.getElementById("add-question-form");

  // Quick subject UI elements
  const btnShowQuickSubject = document.getElementById("btn-show-quick-subject");
  const quickSubjectBox = document.getElementById("quick-subject-box");
  const quickSubjectName = document.getElementById("quick-subject-name");
  const saveQuickSubject = document.getElementById("save-quick-subject");
  const cancelQuickSubject = document.getElementById("cancel-quick-subject");

  // Quick topic UI elements
  const btnShowQuickTopic = document.getElementById("btn-show-quick-topic");
  const quickTopicBox = document.getElementById("quick-topic-box");
  const quickTopicName = document.getElementById("quick-topic-name");
  const saveQuickTopic = document.getElementById("save-quick-topic");
  const cancelQuickTopic = document.getElementById("cancel-quick-topic");

  let allTopicOptions = [];

  if (topicSelect) {
    allTopicOptions = Array.from(
      topicSelect.querySelectorAll("option[data-subject-id]"),
    );
  }

  function filterTopicsBySubject() {
    if (!subjectSelect || !topicSelect) return;

    const selectedSubjectId = subjectSelect.value;
    topicSelect.innerHTML =
      '<option value="" disabled selected>Choose topic</option>';

    if (!selectedSubjectId) {
      topicSelect.disabled = true;
      if (btnShowQuickTopic) btnShowQuickTopic.disabled = true;
      return;
    }

    if (btnShowQuickTopic) btnShowQuickTopic.disabled = false;

    const matchingOptions = allTopicOptions.filter(
      (opt) => opt.getAttribute("data-subject-id") === selectedSubjectId,
    );

    if (matchingOptions.length > 0) {
      topicSelect.disabled = false;
      matchingOptions.forEach((opt) =>
        topicSelect.appendChild(opt.cloneNode(true)),
      );
    } else {
      topicSelect.disabled = false;
      topicSelect.innerHTML =
        '<option value="" disabled selected>No topics in this subject (add one below)</option>';
    }
  }

  if (subjectSelect) {
    subjectSelect.addEventListener("change", filterTopicsBySubject);
  }

  // --- Quick Add Subject ---
  if (btnShowQuickSubject) {
    btnShowQuickSubject.addEventListener("click", () => {
      quickSubjectBox.classList.remove("hidden");
      quickSubjectName.focus();
    });

    cancelQuickSubject.addEventListener("click", () => {
      quickSubjectBox.classList.add("hidden");
      quickSubjectName.value = "";
    });

    saveQuickSubject.addEventListener("click", async () => {
      const name = quickSubjectName.value.trim();
      if (!name) return alert("Enter a subject name.");

      const formData = new FormData();
      formData.append("name", name);

      try {
        const res = await fetch("/subjects/add", {
          method: "POST",
          body: formData,
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        const data = await res.json();

        if (!res.ok || data.error)
          return alert(data.error || "Failed to add subject.");

        const opt = document.createElement("option");
        opt.value = data.subject.id;
        opt.textContent = data.subject.name;
        subjectSelect.appendChild(opt);

        subjectSelect.value = data.subject.id;
        filterTopicsBySubject();

        quickSubjectName.value = "";
        quickSubjectBox.classList.add("hidden");
      } catch (err) {
        alert("An error occurred while creating subject.");
      }
    });
  }

  // --- Quick Add Topic ---
  if (btnShowQuickTopic) {
    btnShowQuickTopic.addEventListener("click", () => {
      if (!subjectSelect.value) return alert("Please select a subject first.");
      quickTopicBox.classList.remove("hidden");
      quickTopicName.focus();
    });

    cancelQuickTopic.addEventListener("click", () => {
      quickTopicBox.classList.add("hidden");
      quickTopicName.value = "";
    });

    saveQuickTopic.addEventListener("click", async () => {
      const name = quickTopicName.value.trim();
      const subjectId = subjectSelect.value;

      if (!subjectId) return alert("Select a subject first.");
      if (!name) return alert("Enter a topic name.");

      const formData = new FormData();
      formData.append("subject_id", subjectId);
      formData.append("name", name);

      try {
        const res = await fetch("/topics/add", {
          method: "POST",
          body: formData,
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        const data = await res.json();

        if (!res.ok || data.error)
          return alert(data.error || "Failed to add topic.");

        const opt = document.createElement("option");
        opt.value = data.topic.id;
        opt.textContent = data.topic.name;
        opt.setAttribute("data-subject-id", data.topic.subject_id);

        allTopicOptions.push(opt);
        filterTopicsBySubject();
        topicSelect.value = data.topic.id;

        quickTopicName.value = "";
        quickTopicBox.classList.add("hidden");
      } catch (err) {
        alert("An error occurred while creating topic.");
      }
    });
  }

  // --- AJAX Question Submit ---
  if (addQForm) {
    addQForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      document
        .querySelectorAll("#add-question-form .rich-editor")
        .forEach((editor) => {
          const targetInput = document.getElementById(editor.dataset.target);
          if (targetInput) targetInput.value = editor.innerHTML.trim();
        });

      const formData = new FormData(addQForm);

      try {
        const res = await fetch(addQForm.action, {
          method: "POST",
          body: formData,
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });

        const data = await res.json();

        if (!res.ok || data.error) {
          alert(data.error || "Failed to add question.");
          return;
        }

        document
          .querySelectorAll("#add-question-form .rich-editor")
          .forEach((editor) => (editor.innerHTML = ""));
        document.getElementById("text-input").value = "";
        document.getElementById("answer-input").value = "";

        const questionList = document.querySelector(".question-list");
        if (questionList && data.question) {
          const q = data.question;
          const emptyMsg = questionList.querySelector("li.muted");
          if (emptyMsg) emptyMsg.remove();

          const li = document.createElement("li");
          li.innerHTML = `
            <div class="question-text">${q.text}</div>
            ${q.answer ? `<div class="question-answer-preview muted small"><strong>Ans:</strong> ${q.answer}</div>` : ""}
            <div class="question-meta">
              <span>${q.topic_name}</span>
              <span class="rating-pill ${q.rating_class}">${q.rating_label}</span>
              <div class="question-actions">
                <a href="/questions/${q.id}/edit" class="btn-icon btn-icon-edit" title="Edit Question">✎ Edit</a>
                <form method="post" action="/questions/${q.id}/delete" onsubmit="return confirm('Delete this question?');">
                  <input type="hidden" name="topic_id" value="">
                  <button type="submit" class="btn-icon" title="Delete">✕</button>
                </form>
              </div>
            </div>
          `;
          questionList.prepend(li);
        }
      } catch (err) {
        alert("An error occurred while saving the question.");
      }
    });
  }

  const revealBtn = document.getElementById("reveal-btn");
  const answerBlock = document.getElementById("answer-block");
  const gradeButtons = document.getElementById("grade-buttons");
  const questionText = document.getElementById("question-text");
  const answerText = document.getElementById("answer-text");
  const topicBadge = document.getElementById("topic-badge");
  const qCount = document.getElementById("q-count");
  const qEditBtn = document.getElementById("q-edit-btn");

  // Lightbox functionality
  const lightbox = document.getElementById("image-lightbox");
  const lightboxImg = document.getElementById("lightbox-img");

  document.addEventListener("click", (e) => {
    if (
      e.target.tagName === "IMG" &&
      (e.target.classList.contains("zoomable") ||
        e.target.closest(".question-card") ||
        e.target.closest(".question-list") ||
        e.target.closest(".answer-block") ||
        e.target.closest(".rich-editor"))
    ) {
      if (lightbox && lightboxImg) {
        lightboxImg.src = e.target.src;
        lightbox.classList.remove("hidden");
      }
    }
  });

  if (lightbox) {
    lightbox.addEventListener("click", () => {
      lightbox.classList.add("hidden");
    });
  }

  // Study Session Controls
  if (revealBtn) {
    revealBtn.addEventListener("click", () => {
      answerBlock.classList.remove("hidden");
      gradeButtons.classList.remove("hidden");
      revealBtn.classList.add("hidden");
    });

    document.querySelectorAll(".btn-grade").forEach((btn) => {
      btn.addEventListener("click", async () => {
        document
          .querySelectorAll(".btn-grade")
          .forEach((b) => (b.disabled = true));
        const score = parseFloat(btn.dataset.score);

        try {
          const res = await fetch("/study/answer", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ score }),
          });
          const data = await res.json();

          if (data.empty) {
            window.location.href = "/study/complete";
            return;
          }

          const q = data.next;
          topicBadge.textContent = q.topic_name;
          questionText.innerHTML = q.text;
          answerText.innerHTML =
            q.answer || "No reference answer saved for this question.";
          qCount.textContent = q.count + 1;

          if (qEditBtn && q.id) {
            qEditBtn.href = `/questions/${q.id}/edit`;
          }

          answerBlock.classList.add("hidden");
          gradeButtons.classList.add("hidden");
          revealBtn.classList.remove("hidden");
          document
            .querySelectorAll(".btn-grade")
            .forEach((b) => (b.disabled = false));
        } catch (err) {
          alert("Something went wrong saving that answer. Please try again.");
          document
            .querySelectorAll(".btn-grade")
            .forEach((b) => (b.disabled = false));
        }
      });
    });
  }

  // Notion/Docs-style Drag & Drop Rich Editor
  document.querySelectorAll(".rich-editor").forEach((editor) => {
    const targetInputId = editor.dataset.target;
    const targetInput = document.getElementById(targetInputId);

    if (targetInput) {
      editor.innerHTML = targetInput.value;
      editor.addEventListener("input", () => {
        targetInput.value = editor.innerHTML;
      });
    }

    editor.addEventListener("dragover", (e) => e.preventDefault());
    editor.addEventListener("drop", async (e) => {
      e.preventDefault();
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        await uploadInlineImage(e.dataTransfer.files[0], editor, targetInput);
      }
    });

    editor.addEventListener("paste", async (e) => {
      const items = (e.clipboardData || e.originalEvent.clipboardData).items;
      for (const item of items) {
        if (item.type.indexOf("image") === 0) {
          e.preventDefault();
          const file = item.getAsFile();
          await uploadInlineImage(file, editor, targetInput);
        }
      }
    });
  });

  async function uploadInlineImage(file, editor, targetInput) {
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch("/upload_image", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (data.url) {
        const img = document.createElement("img");
        img.src = data.url;
        img.className = "zoomable inline-img";
        editor.appendChild(img);
        if (targetInput) targetInput.value = editor.innerHTML;
      }
    } catch (err) {
      alert("Image upload failed.");
    }
  }
});

function openModal(id) {
  document.getElementById(id).classList.remove("hidden");
}
function closeModal(id) {
  document.getElementById(id).classList.add("hidden");
}

document.addEventListener("DOMContentLoaded", () => {
  // Rich Text Editor Toolbar Actions (Bold, Italic, Lists, Code)
  document.querySelectorAll(".editor-toolbar").forEach((toolbar) => {
    const targetId = toolbar.dataset.target;
    const editor = document.getElementById(targetId);

    if (!editor) return;

    toolbar.querySelectorAll(".tb-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        editor.focus();

        const cmd = btn.dataset.cmd;
        const val = btn.dataset.val || null;

        document.execCommand(cmd, false, val);
      });
    });
  });

  // Best Practices Modal Handlers
  const btnOpenBP = document.getElementById("btn-open-best-practices");
  const btnSaveBP = document.getElementById("btn-save-best-practices");
  const bpEditor = document.getElementById("best-practices-editor");

  if (btnOpenBP) {
    btnOpenBP.addEventListener("click", () => {
      openModal("modal-best-practices");
    });
  }

  if (btnSaveBP && bpEditor) {
    btnSaveBP.addEventListener("click", async () => {
      const formData = new FormData();
      formData.append("content", bpEditor.innerHTML.trim());

      try {
        const res = await fetch("/settings/best-practices", {
          method: "POST",
          body: formData,
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        const data = await res.json();

        if (data.success) {
          alert("Best practices saved!");
          closeModal("modal-best-practices");
        } else {
          alert("Failed to save best practices.");
        }
      } catch (err) {
        alert("Error saving best practices notes.");
      }
    });
  }

  // --- Existing dynamic subject & topic JavaScript logic from previous step ---
  const subjectSelect = document.getElementById("add-q-subject");
  const topicSelect = document.getElementById("add-q-topic");
  const addQForm = document.getElementById("add-question-form");

  const btnShowQuickSubject = document.getElementById("btn-show-quick-subject");
  const quickSubjectBox = document.getElementById("quick-subject-box");
  const quickSubjectName = document.getElementById("quick-subject-name");
  const saveQuickSubject = document.getElementById("save-quick-subject");
  const cancelQuickSubject = document.getElementById("cancel-quick-subject");

  const btnShowQuickTopic = document.getElementById("btn-show-quick-topic");
  const quickTopicBox = document.getElementById("quick-topic-box");
  const quickTopicName = document.getElementById("quick-topic-name");
  const saveQuickTopic = document.getElementById("save-quick-topic");
  const cancelQuickTopic = document.getElementById("cancel-quick-topic");

  let allTopicOptions = [];
  if (topicSelect) {
    allTopicOptions = Array.from(
      topicSelect.querySelectorAll("option[data-subject-id]"),
    );
  }

  function filterTopicsBySubject() {
    if (!subjectSelect || !topicSelect) return;
    const selectedSubjectId = subjectSelect.value;
    topicSelect.innerHTML =
      '<option value="" disabled selected>Choose topic</option>';

    if (!selectedSubjectId) {
      topicSelect.disabled = true;
      if (btnShowQuickTopic) btnShowQuickTopic.disabled = true;
      return;
    }

    if (btnShowQuickTopic) btnShowQuickTopic.disabled = false;

    const matchingOptions = allTopicOptions.filter(
      (opt) => opt.getAttribute("data-subject-id") === selectedSubjectId,
    );

    if (matchingOptions.length > 0) {
      topicSelect.disabled = false;
      matchingOptions.forEach((opt) =>
        topicSelect.appendChild(opt.cloneNode(true)),
      );
    } else {
      topicSelect.disabled = false;
      topicSelect.innerHTML =
        '<option value="" disabled selected>No topics in this subject (add one below)</option>';
    }
  }

  if (subjectSelect) {
    subjectSelect.addEventListener("change", filterTopicsBySubject);
  }

  if (btnShowQuickSubject) {
    btnShowQuickSubject.addEventListener("click", () => {
      quickSubjectBox.classList.remove("hidden");
      quickSubjectName.focus();
    });
    cancelQuickSubject.addEventListener("click", () => {
      quickSubjectBox.classList.add("hidden");
      quickSubjectName.value = "";
    });
    saveQuickSubject.addEventListener("click", async () => {
      const name = quickSubjectName.value.trim();
      if (!name) return alert("Enter a subject name.");

      const formData = new FormData();
      formData.append("name", name);

      try {
        const res = await fetch("/subjects/add", {
          method: "POST",
          body: formData,
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        const data = await res.json();
        if (!res.ok || data.error)
          return alert(data.error || "Failed to add subject.");

        const opt = document.createElement("option");
        opt.value = data.subject.id;
        opt.textContent = data.subject.name;
        subjectSelect.appendChild(opt);
        subjectSelect.value = data.subject.id;
        filterTopicsBySubject();

        quickSubjectName.value = "";
        quickSubjectBox.classList.add("hidden");
      } catch (err) {
        alert("An error occurred while creating subject.");
      }
    });
  }

  if (btnShowQuickTopic) {
    btnShowQuickTopic.addEventListener("click", () => {
      if (!subjectSelect.value) return alert("Please select a subject first.");
      quickTopicBox.classList.remove("hidden");
      quickTopicName.focus();
    });
    cancelQuickTopic.addEventListener("click", () => {
      quickTopicBox.classList.add("hidden");
      quickTopicName.value = "";
    });
    saveQuickTopic.addEventListener("click", async () => {
      const name = quickTopicName.value.trim();
      const subjectId = subjectSelect.value;

      if (!subjectId) return alert("Select a subject first.");
      if (!name) return alert("Enter a topic name.");

      const formData = new FormData();
      formData.append("subject_id", subjectId);
      formData.append("name", name);

      try {
        const res = await fetch("/topics/add", {
          method: "POST",
          body: formData,
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        const data = await res.json();
        if (!res.ok || data.error)
          return alert(data.error || "Failed to add topic.");

        const opt = document.createElement("option");
        opt.value = data.topic.id;
        opt.textContent = data.topic.name;
        opt.setAttribute("data-subject-id", data.topic.subject_id);

        allTopicOptions.push(opt);
        filterTopicsBySubject();
        topicSelect.value = data.topic.id;

        quickTopicName.value = "";
        quickTopicBox.classList.add("hidden");
      } catch (err) {
        alert("An error occurred while creating topic.");
      }
    });
  }

  if (addQForm) {
    addQForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      document
        .querySelectorAll("#add-question-form .rich-editor")
        .forEach((editor) => {
          const targetInput = document.getElementById(editor.dataset.target);
          if (targetInput) targetInput.value = editor.innerHTML.trim();
        });

      const formData = new FormData(addQForm);

      try {
        const res = await fetch(addQForm.action, {
          method: "POST",
          body: formData,
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });

        const data = await res.json();
        if (!res.ok || data.error)
          return alert(data.error || "Failed to add question.");

        document
          .querySelectorAll("#add-question-form .rich-editor")
          .forEach((editor) => (editor.innerHTML = ""));
        document.getElementById("text-input").value = "";
        document.getElementById("answer-input").value = "";

        const questionList = document.querySelector(".question-list");
        if (questionList && data.question) {
          const q = data.question;
          const emptyMsg = questionList.querySelector("li.muted");
          if (emptyMsg) emptyMsg.remove();

          const li = document.createElement("li");
          li.innerHTML = `
            <div class="question-text">${q.text}</div>
            ${q.answer ? `<div class="question-answer-preview muted small"><strong>Ans:</strong> ${q.answer}</div>` : ""}
            <div class="question-meta">
              <span>${q.topic_name}</span>
              <span class="rating-pill ${q.rating_class}">${q.rating_label}</span>
              <div class="question-actions">
                <a href="/questions/${q.id}/edit" class="btn-icon btn-icon-edit" title="Edit Question">✎ Edit</a>
                <form method="post" action="/questions/${q.id}/delete" onsubmit="return confirm('Delete this question?');">
                  <input type="hidden" name="topic_id" value="">
                  <button type="submit" class="btn-icon" title="Delete">✕</button>
                </form>
              </div>
            </div>
          `;
          questionList.prepend(li);
        }
      } catch (err) {
        alert("An error occurred while saving the question.");
      }
    });
  }
});

function openModal(id) {
  document.getElementById(id).classList.remove("hidden");
}
function closeModal(id) {
  document.getElementById(id).classList.add("hidden");
}
