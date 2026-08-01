document.getElementById('loginForm').addEventListener('submit', function(e) {
    e.preventDefault(); // Отменяем перезагрузку страницы

    const username = document.getElementById('username').value;
    
    // Показываем приветственный экран
    document.getElementById('loginCard').style.display = 'none';
    document.getElementById('chatScreen').style.display = 'block';
    document.getElementById('userDisplay').textContent = username;
});

function logout() {
    // Возвращаем обратно на экран входа
    document.getElementById('loginCard').style.display = 'block';
    document.getElementById('chatScreen').style.display = 'none';
    document.getElementById('username').value = '';
    document.getElementById('password').value = '';
}
