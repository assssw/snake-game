import telebot
from telebot.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import json
import os
from datetime import datetime, timedelta
import sqlite3
import threading
import time
import logging
import traceback

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Инициализация бота
TOKEN = '8028147928:AAHC2PSGPmrYYRn7vSQ5sXnw4QNrbX69ZU8'
ADMIN_ID = 1454515378 # Замените на ваш ID
CHANNEL_ID = '@mariartytt'  # ID канала для проверки подписки
bot = telebot.TeleBot(TOKEN)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('snake_game.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id TEXT PRIMARY KEY,
                  username TEXT,
                  best_score INTEGER DEFAULT 0,
                  sun INTEGER DEFAULT 0,
                  has_sun_skin BOOLEAN DEFAULT 0,
                  has_premium_skin BOOLEAN DEFAULT 0,
                  last_game TEXT,
                  registration_date TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT,
                  type TEXT,
                  amount INTEGER,
                  timestamp TEXT,
                  FOREIGN KEY (user_id) REFERENCES users(user_id))''')
    
    conn.commit()
    conn.close()

init_db()

# Функции для работы с базой данных
def get_user_data(user_id):
    conn = sqlite3.connect('snake_game.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (str(user_id),))
    data = c.fetchone()
    conn.close()
    if data:
        return {
            'user_id': data[0],
            'username': data[1],
            'best_score': data[2],
            'sun': data[3],
            'has_sun_skin': bool(data[4]),
            'has_premium_skin': bool(data[5]),
            'last_game': data[6],
            'registration_date': data[7]
        }
    return None

def update_user_data(user_id, data):
    conn = sqlite3.connect('snake_game.db')
    c = conn.cursor()
    try:
        c.execute('''INSERT OR REPLACE INTO users 
                     (user_id, username, best_score, sun, has_sun_skin, has_premium_skin, last_game)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                 (str(user_id), data.get('username'), data.get('best_score', 0),
                  data.get('sun', 0), data.get('has_sun_skin', False),
                  data.get('has_premium_skin', False), datetime.now().isoformat()))
        conn.commit()
    except Exception as e:
        logger.error(f"Error updating user data: {e}")
        conn.rollback()
    finally:
        conn.close()

def log_transaction(user_id, type, amount):
    conn = sqlite3.connect('snake_game.db')
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO transactions (user_id, type, amount, timestamp)
                     VALUES (?, ?, ?, ?)''',
                 (str(user_id), type, amount, datetime.now().isoformat()))
        conn.commit()
    except Exception as e:
        logger.error(f"Error logging transaction: {e}")
        conn.rollback()
    finally:
        conn.close()

# Клавиатуры
def get_webapp_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(
        text="🎮 Играть",
        web_app=WebAppInfo(url="YOUR_WEBAPP_URL")
    ))
    return keyboard

def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🎮 Играть"))
    keyboard.add(KeyboardButton("📊 Статистика"), KeyboardButton("💰 Баланс"))
    keyboard.add(KeyboardButton("ℹ️ Помощь"))
    return keyboard

# Обработчики команд
@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    username = message.from_user.username
    
    # Регистрация нового пользователя
    if not get_user_data(user_id):
        update_user_data(user_id, {
            'username': username,
            'best_score': 0,
            'sun': 0,
            'has_sun_skin': False,
            'has_premium_skin': False
        })
        logger.info(f"New user registered: {user_id} (@{username})")
    
    bot.send_message(
        message.chat.id,
        "🐍 Добро пожаловать в Star Snake!\n\n"
        "🎮 Управляйте змейкой, собирайте яблоки и зарабатывайте sun!\n"
        "💫 Покупайте скины и улучшения в магазине\n"
        "🏆 Соревнуйтесь за место в топе игроков\n\n"
        "Нажмите кнопку ниже, чтобы начать игру:",
        reply_markup=get_webapp_keyboard()
    )

@bot.message_handler(commands=['stats'])
def stats(message):
    user_id = str(message.from_user.id)
    data = get_user_data(user_id)
    
    if data:
        stats_text = (
            f"📊 Ваша статистика:\n\n"
            f"🏆 Рекорд: {data['best_score']}\n"
            f"☀️ Sun: {data['sun']}\n"
            f"🎨 Sun скин: {'✅' if data['has_sun_skin'] else '❌'}\n"
            f"✨ Premium: {'✅' if data['has_premium_skin'] else '❌'}\n\n"
            f"📅 Дата регистрации: {data['registration_date'][:10]}"
        )
        
        bot.send_message(message.chat.id, stats_text)
    else:
        bot.send_message(
            message.chat.id,
            "❌ У вас пока нет статистики. Сыграйте в игру!"
        )

@bot.message_handler(commands=['premium'])
def give_premium(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ У вас нет прав для выполнения этой команды")
        return
    
    try:
        args = message.text.split()
        if len(args) != 2:
            bot.send_message(message.chat.id, "❌ Использование: /premium USER_ID")
            return
        
        target_user_id = args[1]
        user_data = get_user_data(target_user_id)
        
        if not user_data:
            bot.send_message(message.chat.id, "❌ Пользователь не найден")
            return
        
        user_data['has_premium_skin'] = True
        update_user_data(target_user_id, user_data)
        log_transaction(target_user_id, 'premium_given', 0)
        
        # Уведомляем пользователя
        try:
            bot.send_message(
                int(target_user_id),
                "✨ Поздравляем! Вам выдан Premium скин!\n\n"
                "Особенности Premium:\n"
                "• Уникальный градиентный скин\n"
                "• +50% к фарму sun\n"
                "• Уменьшенный таймер между играми"
            )
        except:
            logger.error(f"Could not send message to user {target_user_id}")
        
        bot.send_message(
            message.chat.id,
            f"✅ Premium успешно выдан пользователю {target_user_id}"
        )
        
    except Exception as e:
        logger.error(f"Error giving premium: {e}")
        bot.send_message(
            message.chat.id,
            "❌ Произошла ошибка при выдаче Premium"
        )

# Обработчик данных от веб-приложения
@bot.message_handler(content_types=['web_app_data'])
def web_app_data(message):
    try:
        data = json.loads(message.web_app_data.data)
        user_id = str(message.from_user.id)
        user_data = get_user_data(user_id) or {}
        
        # Обновляем данные
        user_data['best_score'] = max(user_data.get('best_score', 0), data.get('bestScore', 0))
        user_data['sun'] = data.get('sun', user_data.get('sun', 0))
        user_data['has_sun_skin'] = data.get('hasSunSkin', user_data.get('has_sun_skin', False))
        user_data['has_premium_skin'] = data.get('hasPremiumSkin', user_data.get('has_premium_skin', False))
        user_data['last_game'] = datetime.now().isoformat()
        
        update_user_data(user_id, user_data)
        
        # Проверяем новый рекорд
        if data.get('bestScore', 0) > user_data.get('best_score', 0):
            bot.send_message(
                message.chat.id,
                f"🏆 Новый рекорд: {data['bestScore']}!"
            )
        
        # Отправляем статистику игры
        bot.send_message(
            message.chat.id,
            f"🎮 Игра завершена!\n\n"
            f"📊 Статистика:\n"
            f"🏆 Счёт: {data.get('score', 0)}\n"
            f"☀️ Заработано: {data.get('sun', 0) - user_data.get('sun', 0)}\n"
            f"💰 Всего sun: {data.get('sun', 0)}"
        )
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON data received")
        bot.send_message(
            message.chat.id,
            "❌ Ошибка при обработке данных игры"
        )
    except Exception as e:
        logger.error(f"Error processing web app data: {e}\n{traceback.format_exc()}")
        bot.send_message(
            message.chat.id,
            "❌ Произошла ошибка при сохранении прогресса"
        )

# Проверка подписки на канал
def check_subscription(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# Периодическое сохранение данных
def backup_data():
    while True:
        try:
            # Создаем резервную копию базы данных
            os.system('cp snake_game.db snake_game_backup.db')
            logger.info("Database backup created")
        except Exception as e:
            logger.error(f"Backup error: {e}")
        time.sleep(3600)  # Каждый час

# Запуск бота
if __name__ == '__main__':
    # Запускаем резервное копирование в отдельном потоке
    backup_thread = threading.Thread(target=backup_data)
    backup_thread.daemon = True
    backup_thread.start()
    
    # Запускаем бота
    logger.info("Bot started")
    bot.infinity_polling()