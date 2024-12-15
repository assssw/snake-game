// Инициализация Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();

// API URL
const API_URL = 'http://localhost:5000';

// Фиксим дергание экрана
document.body.style.overflow = 'hidden';
document.documentElement.style.overflow = 'hidden';

// Игровые переменные
let canvas = document.getElementById('gameCanvas');
let ctx = canvas.getContext('2d');
let tileCount = 20;
let gridSize;
let headX = 10;
let headY = 10;
let dx = 0;
let dy = 0;
let appleX = 5;
let appleY = 5;
let trail = [];
let tail = 3;
let score = 0;
let sun = 0;
let isGameRunning = false;
let touchStartX = null;
let touchStartY = null;
let animationFrame = null;
let lastTime = 0;
let snakeColor = '#4CAF50';
let hasSunSkin = false;
let hasPremiumSkin = false;
let lastGameTime = 0;
let bestScore = 0;
let moveTimer = null;
let gameSpeed = 125; // Начальная скорость 125мс
const minGameSpeed = 30; // Минимальная скорость 30мс
let speedTimer = null; // Таймер для увеличения скорости
let activeSkin = 'default';
let hasVisitedChannel = false;
let subscriptionCheckAttempts = 0;

// Функции для работы с API
async function checkApiConnection() {
    try {
        const response = await fetch(`${API_URL}/api/test`);
        if (response.ok) {
            console.log('API connection successful');
            return true;
        }
        console.error('API connection failed');
        return false;
    } catch (e) {
        console.error('API connection error:', e);
        return false;
    }
}

async function loadUserData() {
    try {
        const userId = tg.initDataUnsafe?.user?.id;
        if (!userId) {
            console.error('User ID not found');
            return;
        }
        
        const response = await fetch(`${API_URL}/api/user/${userId}`);
        const data = await response.json();
        
        if (data.error) {
            console.error('Error loading user data:', data.error);
            return;
        }
        
        // Обновляем локальные данные
        sun = data.sun;
        hasSunSkin = data.has_sun_skin;
        hasPremiumSkin = data.has_premium_skin;
        updateScore();
        
        console.log('User data loaded:', data);
    } catch (e) {
        console.error('Error loading user data:', e);
    }
}

async function updateGameData(score, earnedSun) {
    try {
        const userId = tg.initDataUnsafe?.user?.id;
        if (!userId) {
            console.error('User ID not found');
            return;
        }
        
        console.log('Sending game data:', {
            user_id: userId,
            score: score,
            earned_sun: earnedSun
        });
        
        const response = await fetch(`${API_URL}/api/update_game`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: userId,
                score: score,
                earned_sun: earnedSun
            })
        });
        
        const data = await response.json();
        console.log('Server response:', data);
        
        if (data.error) {
            console.error('Error updating game data:', data.error);
            return;
        }
        
        // Обновляем локальные данные
        sun = data.new_sun;
        updateScore();
        
        // Отправляем данные в Telegram WebApp
        tg.sendData(JSON.stringify({
            sun: sun,
            score: score,
            gameOver: true
        }));
        
    } catch (e) {
        console.error('Error updating game data:', e);
    }
}

// Функции для работы с частицами и анимациями
function createParticles(x, y, color, count = 5) {
    for (let i = 0; i < count; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.cssText = `
            position: absolute;
            left: ${x}px;
            top: ${y}px;
            width: 4px;
            height: 4px;
            background: ${color};
            border-radius: 50%;
            pointer-events: none;
            z-index: 1000;
        `;
        document.body.appendChild(particle);

        const angle = (Math.PI * 2 * i) / count;
        const velocity = 2;
        const vx = Math.cos(angle) * velocity;
        const vy = Math.sin(angle) * velocity;

        let opacity = 1;
        function animateParticle() {
            const currentLeft = parseFloat(particle.style.left);
            const currentTop = parseFloat(particle.style.top);
            
            particle.style.left = `${currentLeft + vx}px`;
            particle.style.top = `${currentTop + vy}px`;
            opacity -= 0.02;
            particle.style.opacity = opacity;

            if (opacity > 0) {
                requestAnimationFrame(animateParticle);
            } else {
                particle.remove();
            }
        }

        requestAnimationFrame(animateParticle);
    }
}

function createScorePopup(x, y, amount, type = 'score') {
    const popup = document.createElement('div');
    popup.className = 'score-popup';
    popup.textContent = type === 'score' ? `+${amount}` : `+${amount} ☀️`;
    popup.style.cssText = `
        position: absolute;
        left: ${x}px;
        top: ${y}px;
        color: ${type === 'score' ? '#4CAF50' : '#ffd700'};
        font-weight: bold;
        font-size: 18px;
        pointer-events: none;
        z-index: 1000;
        text-shadow: 0 0 5px ${type === 'score' ? '#4CAF50' : '#ffd700'};
    `;
    document.body.appendChild(popup);
    
    setTimeout(() => popup.remove(), 800);
}

// Функции инициализации и оптимизации
function resizeCanvas() {
    const container = document.querySelector('.game-wrapper');
    const size = Math.min(container.clientWidth, window.innerHeight * 0.6);
    canvas.width = Math.floor(size);
    canvas.height = Math.floor(size);
    gridSize = Math.floor(size / tileCount);
}

window.onload = async function() {
    const apiAvailable = await checkApiConnection();
    if (!apiAvailable) {
        alert('Ошибка подключения к серверу. Некоторые функции могут быть недоступны.');
    }
    
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    setupEventListeners();
    await loadUserData();
    updateTimer();
    setInterval(updateTimer, 1000);
    optimizeRendering();
};

function optimizeRendering() {
    canvas.style.willChange = 'transform';
    canvas.style.backfaceVisibility = 'hidden';
    canvas.style.transform = 'translateZ(0)';
    
    const gameWrapper = document.querySelector('.game-wrapper');
    gameWrapper.style.willChange = 'transform';
    gameWrapper.style.backfaceVisibility = 'hidden';
    gameWrapper.style.transform = 'translateZ(0)';
}

// Функции навигации по меню
function hideAllContainers() {
    ['main-menu', 'game-container', 'shop-container', 'tasks-container'].forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => {
                element.style.display = 'none';
                element.style.animation = '';
            }, 300);
        }
    });
}

function showMenu() {
    if (!isGameRunning) {
        hideAllContainers();
        setTimeout(() => {
            const menu = document.getElementById('main-menu');
            menu.style.display = 'flex';
            menu.style.animation = 'fadeIn 0.3s ease-out';
            document.querySelector('.back-button').style.display = 'none';
        }, 300);
        stopGame();
    }
}

function showShop() {
    if (!isGameRunning) {
        hideAllContainers();
        setTimeout(() => {
            const shop = document.getElementById('shop-container');
            shop.style.display = 'block';
            shop.style.animation = 'fadeIn 0.3s ease-out';
            document.querySelector('.back-button').style.display = 'flex';
        }, 300);
    }
}

function showTasks() {
    if (!isGameRunning) {
        hideAllContainers();
        setTimeout(() => {
            const tasks = document.getElementById('tasks-container');
            tasks.style.display = 'block';
            tasks.style.animation = 'fadeIn 0.3s ease-out';
            document.querySelector('.back-button').style.display = 'flex';
        }, 300);
    }
}

// Игровые функции
function tryStartGame() {
    const now = Date.now();
    const cooldownTime = hasPremiumSkin ? 5 * 60 * 1000 : 10 * 60 * 1000;
    
    if (lastGameTime && now - lastGameTime < cooldownTime) {
        const timeLeft = Math.ceil((cooldownTime - (now - lastGameTime)) / 60000);
        alert(`Подождите ${timeLeft} минут между играми!${hasPremiumSkin ? '\n✨ У вас Premium скин: ждать 5 минут вместо 10!' : ''}`);
        return;
    }
    startGame();
}

function startGame() {
    hideAllContainers();
    setTimeout(() => {
        const gameContainer = document.getElementById('game-container');
        gameContainer.style.display = 'block';
        gameContainer.style.animation = 'fadeIn 0.3s ease-out';
        document.querySelector('.back-button').style.display = 'none';
        
        canvas = document.getElementById('gameCanvas');
        ctx = canvas.getContext('2d');
        resizeCanvas();
        resetGame();
        
        isGameRunning = true;
        lastGameTime = Date.now();
        gameSpeed = 125;
        
        moveTimer = setInterval(updateGame, gameSpeed);
        requestAnimationFrame(gameLoop);
        
        speedTimer = setInterval(() => {
            if (gameSpeed > minGameSpeed) {
                gameSpeed = Math.max(minGameSpeed, gameSpeed - 1);
                clearInterval(moveTimer);
                moveTimer = setInterval(updateGame, gameSpeed);
            }
        }, 1000);
        
        createParticles(canvas.width / 2, canvas.height / 2, '#4CAF50', 10);
    }, 300);
}

function gameLoop() {
    if (!isGameRunning) return;
    render();
    requestAnimationFrame(gameLoop);
}

function updateGame() {
    if (!isGameRunning) return;
    
    headX += dx;
    headY += dy;

    // Проверка столкновений со стенами
    if (headX < 0 || headX >= tileCount || headY < 0 || headY >= tileCount) {
        gameOver();
        return;
    }

    // Проверка столкновений с хвостом
    for (let i = 3; i < trail.length; i++) {
        if (trail[i].x === headX && trail[i].y === headY) {
            gameOver();
            return;
        }
    }

    trail.push({x: headX, y: headY});
    while (trail.length > tail) {
        trail.shift();
    }

    // Сбор яблока
    if (headX === appleX && headY === appleY) {
        tail++;
        score += 1;
        
        // Расчет бонуса sun
        let sunBonus = 1;
        if (activeSkin === 'sun') sunBonus = 2; // +100% за sun скин
        if (activeSkin === 'premium') sunBonus = 3; // +200% за premium скин
        
        sun += sunBonus;
        
        const canvasRect = canvas.getBoundingClientRect();
        const popupX = canvasRect.left + appleX * gridSize;
        const popupY = canvasRect.top + appleY * gridSize;
        
        createScorePopup(popupX, popupY, 1, 'score');
        createScorePopup(popupX + 20, popupY, sunBonus, 'sun');
        createParticles(popupX + gridSize/2, popupY + gridSize/2, '#ffd700', 8);
        
        updateScore();
        placeApple();
    }
}

function render() {
    // Очистка канваса
    ctx.fillStyle = 'rgba(10, 10, 46, 0.8)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Рисуем змейку
    for (let i = 0; i < trail.length; i++) {
        if (i === trail.length - 1) {
            // Голова змейки
            if (activeSkin === 'premium') {
                const gradient = ctx.createLinearGradient(
                    trail[i].x * gridSize,
                    trail[i].y * gridSize,
                    (trail[i].x + 1) * gridSize,
                    (trail[i].y + 1) * gridSize
                );
                gradient.addColorStop(0, '#ff0066');
                gradient.addColorStop(1, '#6600ff');
                ctx.fillStyle = gradient;
            } else {
                ctx.fillStyle = snakeColor;
            }

            ctx.save();
            ctx.translate(
                trail[i].x * gridSize + gridSize/2,
                trail[i].y * gridSize + gridSize/2
            );
            
            if (dx === 1) ctx.rotate(0);
            else if (dx === -1) ctx.rotate(Math.PI);
            else if (dy === 1) ctx.rotate(Math.PI/2);
            else if (dy === -1) ctx.rotate(-Math.PI/2);
            
            ctx.fillRect(-gridSize/2 + 1, -gridSize/2 + 1, gridSize - 2, gridSize - 2);

            // Рисуем глаза
            ctx.fillStyle = 'white';
            const eyeSize = gridSize / 6;
            const eyeOffset = gridSize / 4;
            
            ctx.beginPath();
            ctx.arc(-eyeOffset, -eyeOffset, eyeSize, 0, Math.PI * 2);
            ctx.arc(eyeOffset, -eyeOffset, eyeSize, 0, Math.PI * 2);
            ctx.fill();
            
            ctx.fillStyle = 'black';
            ctx.beginPath();
            ctx.arc(-eyeOffset, -eyeOffset, eyeSize/2, 0, Math.PI * 2);
            ctx.arc(eyeOffset, -eyeOffset, eyeSize/2, 0, Math.PI * 2);
            ctx.fill();
            
            ctx.restore();
        } else {
            // Тело змейки
            if (activeSkin === 'premium') {
                const gradient = ctx.createLinearGradient(
                    trail[i].x * gridSize,
                    trail[i].y * gridSize,
                    (trail[i].x + 1) * gridSize,
                    (trail[i].y + 1) * gridSize
                );
                gradient.addColorStop(0, '#ff0066');
                gradient.addColorStop(1, '#6600ff');
                ctx.fillStyle = gradient;
                
                ctx.shadowBlur = 10;
                ctx.shadowColor = '#ff0066';
            } else {
                ctx.fillStyle = snakeColor;
            }
            
            ctx.fillRect(
                trail[i].x * gridSize + 1,
                trail[i].y * gridSize + 1,
                gridSize - 2,
                gridSize - 2
            );
            
            ctx.shadowBlur = 0;
        }
    }

    // Рисуем яблоко
    ctx.save();
    ctx.shadowBlur = 15;
    ctx.shadowColor = "red";
    
    const appleGradient = ctx.createRadialGradient(
        appleX * gridSize + gridSize/2,
        appleY * gridSize + gridSize/2,
        0,
        appleX * gridSize + gridSize/2,
        appleY * gridSize + gridSize/2,
        gridSize/2
    );
    appleGradient.addColorStop(0, '#ff0000');
    appleGradient.addColorStop(1, '#990000');
    ctx.fillStyle = appleGradient;
    
    const pulseScale = 1 + Math.sin(Date.now() / 200) * 0.1;
    ctx.translate(
        appleX * gridSize + gridSize/2,
        appleY * gridSize + gridSize/2
    );
    ctx.scale(pulseScale, pulseScale);
    
    ctx.beginPath();
    ctx.arc(0, 0, gridSize/2 - 1, 0, Math.PI * 2);
    ctx.fill();
    
    // Блик на яблоке
    ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.beginPath();
    ctx.arc(-gridSize/6, -gridSize/6, gridSize/6, 0, Math.PI * 2);
    ctx.fill();
    
    ctx.restore();
}

function gameOver() {
    isGameRunning = false;
    
    if (moveTimer) clearInterval(moveTimer);
    if (speedTimer) clearInterval(speedTimer);
    if (animationFrame) cancelAnimationFrame(animationFrame);
    
    // Отправляем данные на сервер
    updateGameData(score, sun);
    
    const canvasRect = canvas.getBoundingClientRect();
    const headScreenX = canvasRect.left + headX * gridSize + gridSize/2;
    const headScreenY = canvasRect.top + headY * gridSize + gridSize/2;
    
    createParticles(headScreenX, headScreenY, snakeColor, 20);
    createParticles(headScreenX, headScreenY, '#ff0000', 15);
    
    const gameOverScreen = document.createElement('div');
    gameOverScreen.className = 'game-over-screen';
    
    const title = document.createElement('h1');
    title.className = 'game-over-title';
    title.textContent = 'GAME OVER';
    
    const stats = document.createElement('div');
    stats.className = 'game-over-stats';
    
    stats.innerHTML = `
        <p>Счет: ${score}</p>
        <p>Заработано: ${sun} ☀️</p>
    `;
    
    const buttons = document.createElement('div');
    buttons.className = 'game-over-buttons';
    
    // Проверяем таймер перед созданием кнопки "Играть снова"
    const now = Date.now();
    const cooldownTime = hasPremiumSkin ? 5 * 60 * 1000 : 10 * 60 * 1000;
    const canPlayAgain = !lastGameTime || (now - lastGameTime >= cooldownTime);
    
    const retryButton = document.createElement('button');
    retryButton.className = 'button';
    if (canPlayAgain) {
        retryButton.innerHTML = '🔄 Играть снова';
        retryButton.onclick = () => {
            gameOverScreen.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => {
                gameOverScreen.remove();
                tryStartGame();
            }, 300);
        };
    } else {
        const timeLeft = Math.ceil((cooldownTime - (now - lastGameTime)) / 60000);
        retryButton.innerHTML = `⏳ Подождите ${timeLeft} мин`;
        retryButton.disabled = true;
    }
    
    const menuButton = document.createElement('button');
    menuButton.className = 'button';
    menuButton.innerHTML = '🏠 Главное меню';
    menuButton.onclick = () => {
        gameOverScreen.style.animation = 'fadeOut 0.3s ease-out';
        setTimeout(() => {
            gameOverScreen.remove();
            showMenu();
        }, 300);
    };
    
    buttons.appendChild(retryButton);
    buttons.appendChild(menuButton);
    
    gameOverScreen.appendChild(title);
    gameOverScreen.appendChild(stats);
    gameOverScreen.appendChild(buttons);
    
    setTimeout(() => {
        document.body.appendChild(gameOverScreen);
        createParticles(0, window.innerHeight/2, '#ff0000', 10);
        createParticles(window.innerWidth, window.innerHeight/2, '#ff0000', 10);
        createParticles(window.innerWidth/2, 0, '#ff0000', 10);
        createParticles(window.innerWidth/2, window.innerHeight, '#ff0000', 10);
    }, 500);
}

function resetGame() {
    headX = 10;
    headY = 10;
    dx = 0;
    dy = 0;
    trail = [
        {x: 10, y: 10},
        {x: 9, y: 10},
        {x: 8, y: 10}
    ];
    tail = 3;
    score = 0;
    updateScore();
    placeApple();
}

function updateScore() {
    const scoreElement = document.getElementById('score');
    const sunElement = document.getElementById('sun-display');
    const sunBalanceElement = document.getElementById('sun-balance');
    
    scoreElement.textContent = `Score: ${score}`;
    sunElement.textContent = `☀️ ${sun}`;
    if (sunBalanceElement) {
        sunBalanceElement.textContent = sun;
    }
    
    scoreElement.classList.add('highlight');
    sunElement.classList.add('highlight');
    
    setTimeout(() => {
        scoreElement.classList.remove('highlight');
        sunElement.classList.remove('highlight');
    }, 300);
}

function placeApple() {
    do {
        appleX = Math.floor(Math.random() * tileCount);
        appleY = Math.floor(Math.random() * tileCount);
    } while (trail.some(segment => segment.x === appleX && segment.y === appleY));

    const canvasRect = canvas.getBoundingClientRect();
    const appleScreenX = canvasRect.left + appleX * gridSize + gridSize/2;
    const appleScreenY = canvasRect.top + appleY * gridSize + gridSize/2;
    createParticles(appleScreenX, appleScreenY, '#ff0000', 6);
}

// Обработчики управления
function handleKeyPress(e) {
    if (!isGameRunning) return;
    
    switch(e.keyCode) {
        case 37: // left
            if (dx !== 1) { dx = -1; dy = 0; }
            break;
        case 38: // up
            if (dy !== 1) { dx = 0; dy = -1; }
            break;
        case 39: // right
            if (dx !== -1) { dx = 1; dy = 0; }
            break;
        case 40: // down
            if (dy !== -1) { dx = 0; dy = 1; }
            break;
    }
}

function handleTouchStart(e) {
    if (!isGameRunning) return;
    e.preventDefault();
    
    const touch = e.touches[0];
    touchStartX = touch.clientX;
    touchStartY = touch.clientY;
}

function handleTouchMove(e) {
    if (!isGameRunning || !touchStartX || !touchStartY) return;
    e.preventDefault();
    
    const touch = e.touches[0];
    const touchEndX = touch.clientX;
    const touchEndY = touch.clientY;
    
    const deltaX = touchEndX - touchStartX;
    const deltaY = touchEndY - touchStartY;
    
    const minSwipeDistance = 30;
    
    if (Math.abs(deltaX) > minSwipeDistance || Math.abs(deltaY) > minSwipeDistance) {
        if (Math.abs(deltaX) > Math.abs(deltaY)) {
            if (deltaX > 0 && dx !== -1) { dx = 1; dy = 0; }
            else if (deltaX < 0 && dx !== 1) { dx = -1; dy = 0; }
        } else {
            if (deltaY > 0 && dy !== -1) { dx = 0; dy = 1; }
            else if (deltaY < 0 && dy !== 1) { dx = 0; dy = -1; }
        }
        
        touchStartX = touchEndX;
        touchStartY = touchEndY;
    }
}

function handleTouchEnd() {
    touchStartX = null;
    touchStartY = null;
}

function setupEventListeners() {
    document.addEventListener('keydown', handleKeyPress);
    canvas.addEventListener('touchstart', handleTouchStart, { passive: false });
    canvas.addEventListener('touchmove', handleTouchMove, { passive: false });
    canvas.addEventListener('touchend', handleTouchEnd);
}

// Функции для работы с магазином и заданиями
function handleSunSkin() {
    if (hasSunSkin) {
        if (activeSkin === 'sun') {
            activeSkin = 'default';
            document.getElementById('sun-skin-button').textContent = 'Выбрать';
            alert('Sun скин деактивирован');
        } else {
            activeSkin = 'sun';
            document.getElementById('sun-skin-button').textContent = 'Активен';
            document.getElementById('default-skin-button').textContent = 'Выбрать';
            document.getElementById('premium-button').textContent = hasPremiumSkin ? 'Выбрать' : 'Купить';
            alert('Sun скин активирован! (+100% к фарму sun)');
        }
    } else if (sun >= 40) {
        sun -= 40;
        hasSunSkin = true;
        activeSkin = 'sun';
        document.getElementById('sun-skin-button').textContent = 'Активен';
        document.getElementById('default-skin-button').textContent = 'Выбрать';
        document.getElementById('premium-button').textContent = hasPremiumSkin ? 'Выбрать' : 'Купить';
        updateScore();
        alert('Вы приобрели Sun скин! (+100% к фарму sun)');
    } else {
        alert('Недостаточно sun! Нужно 40 ☀️');
    }
    updateSnakeColor();
}

function handlePremiumSkin() {
    if (hasPremiumSkin) {
        if (activeSkin === 'premium') {
            activeSkin = 'default';
            document.getElementById('premium-button').textContent = 'Выбрать';
            alert('Premium скин деактивирован');
        } else {
            activeSkin = 'premium';
            document.getElementById('premium-button').textContent = 'Активен';
            document.getElementById('default-skin-button').textContent = 'Выбрать';
            document.getElementById('sun-skin-button').textContent = hasSunSkin ? 'Выбрать' : '40 ☀️';
            alert('Premium скин активирован! (+200% к фарму sun)');
        }
        updateSnakeColor();
    } else {
        tg.openTelegramLink('https://t.me/Kertiron');
    }
}

function selectSkin(skinType) {
    if (skinType === 'default') {
        activeSkin = 'default';
        document.getElementById('default-skin-button').textContent = 'Активен';
        document.getElementById('sun-skin-button').textContent = hasSunSkin ? 'Выбрать' : '40 ☀️';
        document.getElementById('premium-button').textContent = hasPremiumSkin ? 'Выбрать' : 'Купить';
        alert('Базовый скин активирован');
        updateSnakeColor();
    }
}

function updateSnakeColor() {
    switch(activeSkin) {
        case 'sun':
            snakeColor = '#ffd700';
            break;
        case 'premium':
            snakeColor = 'gradient';
            break;
        default:
            snakeColor = '#4CAF50';
    }
}

function handleChannelVisit() {
    try {
        tg.openTelegramLink('https://t.me/mariartytt');
        hasVisitedChannel = true;
        document.getElementById('check-subscription-button').disabled = false;
    } catch (e) {
        console.error('Error opening channel:', e);
    }
}

function checkSubscription() {
    if (!hasVisitedChannel) {
        alert('Сначала перейдите по ссылке на канал!');
        return;
    }

    subscriptionCheckAttempts++;
    
    if (subscriptionCheckAttempts === 1) {
        alert('❌ Подписка не найдена. Попробуйте еще раз через несколько секунд.');
        return;
    }
    
    sun += 50;
    updateScore();
    
    const task = document.getElementById('subscription-task');
    if (task) {
        task.classList.add('completed');
        createParticles(
            task.offsetLeft + task.offsetWidth/2,
            task.offsetTop + task.offsetHeight/2,
            '#4CAF50',
            8
        );
        
        setTimeout(() => {
            task.remove();
        }, 500);
        
        alert('✅ Награда получена: +50 ☀️');
    }
}

function updateTimer() {
    if (!lastGameTime) return;
    
    const now = Date.now();
    const cooldown = hasPremiumSkin ? 5 * 60 * 1000 : 10 * 60 * 1000;
    const timePassed = now - lastGameTime;
    
    if (timePassed < cooldown) {
        const timeLeft = cooldown - timePassed;
        const minutes = Math.floor(timeLeft / 60000);
        const seconds = Math.floor((timeLeft % 60000) / 1000);
        document.getElementById('timer').textContent = 
            `Следующая игра через: ${minutes}:${seconds.toString().padStart(2, '0')}`;
        document.querySelector('.play-button').disabled = true;
    } else {
        document.getElementById('timer').textContent = '';
        document.querySelector('.play-button').disabled = false;
    }
}
