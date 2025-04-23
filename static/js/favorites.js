document.addEventListener('DOMContentLoaded', () => {
    const favoriteButtons = document.querySelectorAll('.favorite-btn');

    favoriteButtons.forEach(button => {
        button.addEventListener('click', async () => {
            const gameId = button.getAttribute('data-game-id');
            const isFavorite = button.getAttribute('data-is-favorite') === 'true';

            try {
                const response = await fetch(`/game/${gameId}/favorite`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                });

                const data = await response.json();

                if (data.message) {
                    // Обновляем текст и иконку кнопки
                    button.setAttribute('data-is-favorite', data.is_favorite.toString());
                    const icon = button.querySelector('.favorite-icon');
                    const text = button.childNodes[button.childNodes.length - 1]; // Последний текстовый узел
                    if (data.is_favorite) {
                        icon.textContent = '★';
                        text.textContent = ' Удалить из избранного';
                    } else {
                        icon.textContent = '☆';
                        text.textContent = ' Добавить в избранное';
                    }

                    // Показываем уведомление
                    const flash = document.createElement('div');
                    flash.className = `flash ${response.ok ? 'success' : 'error'}`;
                    flash.textContent = data.message;
                    document.querySelector('.profile-container')?.prepend(flash) ||
                    document.querySelector('.search-container')?.prepend(flash);
                    setTimeout(() => flash.remove(), 3000);
                }
            } catch (error) {
                console.error('Ошибка при изменении статуса избранного:', error);
                const flash = document.createElement('div');
                flash.className = 'flash error';
                flash.textContent = 'Ошибка при изменении статуса избранного';
                document.querySelector('.profile-container')?.prepend(flash) ||
                document.querySelector('.search-container')?.prepend(flash);
                setTimeout(() => flash.remove(), 3000);
            }
        });
    });
});