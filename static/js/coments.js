document.addEventListener("DOMContentLoaded", function () {
    const gameId = window.location.pathname.split("/").pop();
    const commentsContainer = document.getElementById("comments-container");
    const commentForm = document.getElementById("comment-form");
    const commentText = document.getElementById("comment-text");

    // Переменная для хранения открытых форм ответа
    let activeReplyForms = {};

    function loadComments() {
        fetch(`/game/${gameId}/comments`)
            .then(response => response.json())
            .then(data => {
                // Сохранение открытых форм перед обновлением
                document.querySelectorAll(".reply-form").forEach(form => {
                    const parentId = form.dataset.parentId;
                    activeReplyForms[parentId] = form.querySelector("textarea").value;
                });

                commentsContainer.innerHTML = "";
                data.comments.forEach(comment => {
                    commentsContainer.appendChild(createCommentElement(comment));
                });

                // Восстановление открытых форм ответа
                Object.keys(activeReplyForms).forEach(parentId => {
                    const replyBtn = document.querySelector(`.reply-btn[data-id='${parentId}']`);
                    if (replyBtn) {
                        addReplyForm(replyBtn, parentId, activeReplyForms[parentId]);
                    }
                });

                // Очистка после восстановления
                activeReplyForms = {};
            });
    }

    function createCommentElement(comment) {
        const avatarSrc = comment.avatar ? comment.avatar : "/static/images/default.png";
        const commentElement = document.createElement("div");
        commentElement.classList.add("comment");
        commentElement.innerHTML = `
            <div class="comment-header">
                <span class="comment-user">${comment.user}</span>
                <span class="comment-timestamp">${comment.timestamp}</span>
            </div>
            <img src="${avatarSrc}" alt="Avatar" class="comment-avatar">
            <div class="comment-content">
                <p class="comment-text">${comment.text}</p>
                <button class="like-btn" data-id="${comment.id}">❤️ ${comment.likes}</button>
                <button class="reply-btn" data-id="${comment.id}">💬 Ответить</button>
                ${comment.is_owner ? `<button class="delete-btn-com" data-id="${comment.id}">🗑 Удалить</button>` : ""}
            </div>
        `;

        const repliesContainer = document.createElement("div");
        repliesContainer.classList.add("replies-container");

        if (comment.replies.length > 0) {
            comment.replies.forEach(reply => {
                repliesContainer.appendChild(createCommentElement(reply));
            });
        }

        commentElement.appendChild(repliesContainer);
        return commentElement;
    }

    function addReplyForm(replyBtn, parentId, savedText = "") {
    if (replyBtn.parentNode.querySelector(".reply-form")) return;

    const replyForm = document.createElement("form");
    replyForm.classList.add("reply-form");
    replyForm.dataset.parentId = parentId;
    replyForm.innerHTML = `
        <textarea class="reply-text" placeholder="Ваш ответ..." required>${savedText}</textarea>
        <button type="submit">Ответить</button>
    `;

    replyBtn.parentNode.appendChild(replyForm);

    replyForm.addEventListener("submit", function (event) {
        event.preventDefault();
        const replyText = replyForm.querySelector(".reply-text").value.trim();
        if (!replyText) return;

        fetch(`/game/${gameId}/comment`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: replyText, parent_id: parentId })
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                loadComments();
                // Закрываем форму ответа после отправки
                replyForm.remove(); // или replyForm.style.display = 'none';
            }
        });
    });
}

    commentsContainer.addEventListener("click", function (e) {
        if (e.target.classList.contains("reply-btn")) {
            const parentId = e.target.dataset.id;
            addReplyForm(e.target, parentId);
        }
    });

    commentForm.addEventListener("submit", function (e) {
        e.preventDefault();
        const text = commentText.value.trim();
        if (!text) return;

        fetch(`/game/${gameId}/comment`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text })
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                commentText.value = "";
                loadComments();
            }
        });
    });

    commentsContainer.addEventListener("click", function (e) {
        if (e.target.classList.contains("like-btn")) {
            const commentId = e.target.dataset.id;
            fetch(`/comment/${commentId}/like`, { method: "POST" })
                .then(response => response.json())
                .then(data => {
                    e.target.textContent = `❤️ ${data.likes}`;
                });
        }
    });

    commentsContainer.addEventListener("click", function (e) {
        if (e.target.classList.contains("delete-btn-com")) {
            const commentId = e.target.dataset.id;

            fetch(`/comment/${commentId}/delete`, { method: "DELETE" })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        loadComments();
                    } else {
                        alert("Ошибка: " + data.error);
                    }
                });
        }
    });

    loadComments();
    setInterval(loadComments, 5000);
});