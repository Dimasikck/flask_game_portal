 // Функция для перехода в полноэкранный режим
function toggleFullScreen() {
const iframe = document.getElementById("game-frame");
const fullscreenBtn = document.getElementById("fullscreen-btn");

if (!document.fullscreenElement) {
  // Переход в полноэкранный режим
  if (iframe.requestFullscreen) {
    iframe.requestFullscreen();
  } else if (iframe.mozRequestFullScreen) { // Для Firefox
    iframe.mozRequestFullScreen();
  } else if (iframe.webkitRequestFullscreen) { // Для Chrome, Safari и Opera
    iframe.webkitRequestFullscreen();
  } else if (iframe.msRequestFullscreen) { // Для IE/Edge
    iframe.msRequestFullscreen();
  }
  fullscreenBtn.textContent = "Развернуть на весь экран";
} else {
  // Выход из полноэкранного режима
  if (document.exitFullscreen) {
    document.exitFullscreen();
  } else if (document.mozCancelFullScreen) { // Для Firefox
    document.mozCancelFullScreen();
  } else if (document.webkitExitFullscreen) { // Для Chrome, Safari и Opera
    document.webkitExitFullscreen();
  } else if (document.msExitFullscreen) { // Для IE/Edge
    document.msExitFullscreen();
  }
  fullscreenBtn.textContent = "Развернуть на весь экран";
}
}

// Добавляем слушатель на кнопку
document.getElementById("fullscreen-btn").addEventListener("click", toggleFullScreen);