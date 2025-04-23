function fetchComments(url) {
    fetch(url)
        .then(response => response.json())
        .then(data => {
            const commentsContainer = document.getElementById("comments-container");
            commentsContainer.innerHTML = "";
            data.comments.forEach(comment => {
                commentsContainer.appendChild(createCommentElement(comment));
            });
        });
}

function addComment(url, text, parentId, fetchUrl) {
    fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, parent_id: parentId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            document.getElementById("comment-text").value = "";
            fetchComments(fetchUrl);
        }
    });
}

function createCommentElement(comment) {
    const avatarSrc = comment.avatar ? comment.avatar : "/static/images/default.png";
    const commentElement = document.createElement("div");
    commentElement.classList.add("comment");
    commentElement.innerHTML = `
        <div class="comment-header">
            <a href="/user/${comment.user_id}" class="comment-user">${comment.user}</a>
            <span class="comment-timestamp">${comment.timestamp}</span>
        </div>
        <a href="/user/${comment.user_id}"><img src="${avatarSrc}" alt="Avatar" class="comment-avatar"></a>
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

document.addEventListener("DOMContentLoaded", function () {
    const commentsContainer = document.getElementById("comments-container");
    const commentForm = document.getElementById("comment-form");
    const commentText = document.getElementById("comment-text");

    // Переменные задаются в шаблоне (game.html или post.html)
    const entityId = window.entityId; // ID игры или поста
    const entityType = window.entityType; // "game" или "post"
    const commentsUrl = `/${entityType}/${entityId}/comments`; // Полный URL для получения комментариев
    const addCommentUrl = `/${entityType}/${entityId}/comment`; // Полный URL для добавления комментариев

    let activeReplyForms = {};

    fetchComments(commentsUrl);

    commentForm.addEventListener("submit", function (e) {
        e.preventDefault();
        const text = commentText.value.trim();
        if (!text) return;
        addComment(addCommentUrl, text, null, commentsUrl);
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
        if (e.target.classList.contains("reply-btn")) {
            const parentId = e.target.dataset.id;
            addReplyForm(e.target, parentId);
        }
        if (e.target.classList.contains("delete-btn-com")) {
            const commentId = e.target.dataset.id;
            fetch(`/comment/${commentId}/delete`, { method: "DELETE" })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        fetchComments(commentsUrl);
                    } else {
                        alert("Ошибка: " + data.error);
                    }
                });
        }
    });

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

            addComment(addCommentUrl, replyText, parentId, commentsUrl);
            replyForm.remove();
        });
    }

    setInterval(() => fetchComments(commentsUrl), 5000);
});