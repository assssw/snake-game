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
logger.info("Bot initialization started")

# Инициализация бота
TOKEN = '8028147928:AAHC2PSGPmrYYRn7vSQ5sXnw4QNrbX69ZU8'
ADMIN_ID = 1454515378
CHANNEL_ID = '@mariartytt'
bot = telebot.TeleBot(TOKEN)

# Инициализация базы данных
def init_db():
    try:
        conn = sqlite3.connect('snake_game.db')
        c = conn.cursor()
        
        # Создаем таблицу пользователей
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (user_id TEXT PRIMARY KEY,
                      username TEXT,
                      sun INTEGER DEFAULT 0,
                      has_sun_skin BOOLEAN DEFAULT 0,
                      has_premium_skin BOOLEAN DEFAULT 0,
                      subscription_task_completed BOOLEAN DEFAULT 0,
                      referral_count INTEGER DEFAULT 0,
                      last_game TEXT,
                      registration_date TEXT)''')
        
        # Создаем таблицу транзакций
        c.execute('''CREATE TABLE IF NOT EXISTS transactions
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id TEXT,
                      type TEXT,
                      amount INTEGER,
                      timestamp TEXT)''')
        
        conn.commit()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
    finally:
        conn.close()

init_db()

def get_user_data(user_id):
    try:
        conn = sqlite3.connect('snake_game.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE user_id = ?', (str(user_id),))
        data = c.fetchone()
        conn.close()
        
        if data:
            return {
                'user_id': data[0],
                'username': data[1],
                'sun': data[2],
                'has_sun_skin': bool(data[3]),
                'has_premium_skin': bool(data[4]),
                'subscription_task_completed': bool(data[5]),
                'referral_count': data[6],
                'last_game': data[7],
                'registration_date': data[8]
            }
        return None
    except Exception as e:
        logger.error(f"Error getting user data: {e}")
        return None

def update_user_data(user_id, data):
    try:
        conn = sqlite3.connect('snake_game.db')
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO users 
                     (user_id, username, sun, has_sun_skin, has_premium_skin, 
                      subscription_task_completed, referral_count, last_game, registration_date)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                 (str(user_id), data.get('username'), data.get('sun', 0),
                  data.get('has_sun_skin', False), data.get('has_premium_skin', False),
                  data.get('subscription_task_completed', False), data.get('referral_count', 0),
                  data.get('last_game', datetime.now().isoformat()),
                  data.get('registration_date', datetime.now().isoformat())))
        conn.commit()
        logger.info(f"Updated data for user {user_id}")
    except Exception as e:
        logger.error(f"Error updating user data: {e}")
    finally:
        conn.close()

def log_transaction(user_id, type, amount):
    try:
        conn = sqlite3.connect('snake_game.db')
        c = conn.cursor()
        c.execute('''INSERT INTO transactions (user_id, type, amount, timestamp)
                     VALUES (?, ?, ?, ?)''',
                 (str(user_id), type, amount, datetime.now().isoformat()))
        conn.commit()
        logger.info(f"Logged transaction: {user_id} {type} {amount}")
    except Exception as e:
        logger.error(f"Error logging transaction: {e}")
    finally:
        conn.close()

# Клавиатуры
def get_webapp_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(
        text="🎮 Играть",
        web_app=WebAppInfo(url="https://assssw.github.io/snake-game/")
    ))
    return keyboard

def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(KeyboardButton("🎮 Играть"))
    keyboard.row(KeyboardButton("🏆 Лидерборд"), KeyboardButton("👥 Рефералка"))
    keyboard.row(KeyboardButton("ℹ️ Помощь"))
    return keyboard

# Обработчики команд
@bot.message_handler(commands=['start'])
def start(message):
    try:
        user_id = str(message.from_user.id)
        username = message.from_user.username
        
        if not username:
            bot.send_message(
                message.chat.id,
                "❌ Для игры необходимо установить username в настройках Telegram"
            )
            return
        
        # Проверяем реферальный код
        args = message.text.split()
        referrer_id = args[1] if len(args) > 1 else None
        
        # Регистрация нового пользователя
        user_data = get_user_data(user_id)
        if not user_data:
            user_data = {
                'user_id': user_id,
                'username': username,
                'sun': 20 if referrer_id else 0,
                'has_sun_skin': False,
                'has_premium_skin': False,
                'subscription_task_completed': False,
                'referral_count': 0,
                'last_game': None,
                'registration_date': datetime.now().isoformat()
            }
            update_user_data(user_id, user_data)
            
            # Награждаем реферера
            if referrer_id:
                referrer_data = get_user_data(referrer_id)
                if referrer_data:
                    referrer_data['sun'] = referrer_data.get('sun', 0) + 20
                    referrer_data['referral_count'] = referrer_data.get('referral_count', 0) + 1
                    update_user_data(referrer_id, referrer_data)
                    log_transaction(referrer_id, 'referral_bonus', 20)
                    
                    bot.send_message(
                        referrer_id,
                        f"🎉 Новый реферал @{username}!\n"
                        f"Получено: +20 ☀️\n"
                        f"Всего sun: {referrer_data['sun']}"
                    )
        
        # Отправляем приветственное сообщение
        bot.send_message(
            message.chat.id,
            "🐍 Добро пожаловать в Star Snake!\n\n"
            "🎮 Управляйте змейкой, собирайте яблоки и зарабатывайте sun!\n"
            "💫 Покупайте скины и улучшения в магазине\n"
            "🏆 Соревнуйтесь за место в топе игроков\n"
            "👥 Приглашайте друзей и получайте награды\n\n"
            "Нажмите кнопку ниже, чтобы начать игру:",
            reply_markup=get_webapp_keyboard()
        )
        
        # Отправляем основную клавиатуру
        bot.send_message(
            message.chat.id,
            "Выберите действие:",
            reply_markup=get_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка при запуске")

@bot.message_handler(func=lambda message: message.text == "🎮 Играть")
def play_button(message):
    try:
        if not message.from_user.username:
            bot.send_message(
                message.chat.id,
                "❌ Для игры необходимо установить username в настройках Telegram"
            )
            return
            
        bot.send_message(
            message.chat.id,
            "🎮 Нажмите кнопку ниже, чтобы начать игру:",
            reply_markup=get_webapp_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in play button: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка")

@bot.message_handler(func=lambda message: message.text == "🏆 Лидерборд")
def show_leaderboard_button(message):
    try:
        conn = sqlite3.connect('snake_game.db')
        c = conn.cursor()
        c.execute('''SELECT username, sun 
                    FROM users 
                    WHERE username IS NOT NULL 
                    ORDER BY sun DESC 
                    LIMIT 10''')
        leaders = c.fetchall()
        conn.close()
        
        if not leaders:
            bot.send_message(message.chat.id, "🏆 Пока нет игроков в топе")
            return
            
        text = "🏆 Топ-10 игроков:\n\n"
        for i, (username, sun) in enumerate(leaders, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "👑"
            text += f"{medal} {i}. @{username}\n└ {sun} ☀️\n\n"
        
        bot.send_message(message.chat.id, text)
        
    except Exception as e:
        logger.error(f"Error showing leaderboard: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка при загрузке лидерборда")

@bot.message_handler(func=lambda message: message.text == "👥 Рефералка")
def show_referral_button(message):
    try:
        if not message.from_user.username:
            bot.send_message(
                message.chat.id,
                "❌ Для использования реферальной системы необходимо установить username"
            )
            return
            
        user_id = str(message.from_user.id)
        bot_username = bot.get_me().username
        link = f"https://t.me/{bot_username}?start={user_id}"
        
        user_data = get_user_data(user_id)
        if not user_data:
            bot.send_message(message.chat.id, "❌ Ошибка получения данных")
            return
            
        text = (
            f"👥 Реферальная система\n\n"
            f"🔗 Ваша ссылка:\n{link}\n\n"
            f"📊 Статистика:\n"
            f"• Рефералов: {user_data['referral_count']}\n"
            f"• Sun: {user_data['sun']} ☀️\n\n"
            f"💰 Награды:\n"
            f"• +20 ☀️ за приглашение реферала\n"
            f"• +10% от фарма рефералов\n\n"
            f"ℹ️ Отправьте эту ссылку друзьям и\n"
            f"получайте награды за их игру!"
        )
        
        bot.send_message(message.chat.id, text)
    except Exception as e:
        logger.error(f"Error showing referral: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка")

@bot.message_handler(commands=['give_sun'])
def give_sun(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        args = message.text.split()
        if len(args) != 3:
            bot.send_message(message.chat.id, "❌ Использование: /give_sun USERNAME AMOUNT")
            return
            
        username = args[1].replace('@', '')
        amount = int(args[2])
        
        conn = sqlite3.connect('snake_game.db')
        c = conn.cursor()
        c.execute('SELECT user_id FROM users WHERE username = ?', (username,))
        result = c.fetchone()
        conn.close()
        
        if not result:
            bot.send_message(message.chat.id, f"❌ Пользователь @{username} не найден")
            return
            
        user_id = result[0]
        user_data = get_user_data(user_id)
        user_data['sun'] = user_data.get('sun', 0) + amount
        update_user_data(user_id, user_data)
        log_transaction(user_id, 'admin_give_sun', amount)
        
        bot.send_message(
            user_id,
            f"🎁 Администратор выдал вам {amount} ☀️!"
        )
        
        bot.send_message(
            message.chat.id,
            f"✅ Выдано {amount} ☀️ пользователю @{username}"
        )
        
    except Exception as e:
        logger.error(f"Error giving sun: {e}")
        bot.send_message(message.chat.id, "❌ Использование: /give_sun USERNAME AMOUNT")

@bot.message_handler(commands=['stats'])
def admin_stats(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        conn = sqlite3.connect('snake_game.db')
        c = conn.cursor()
        
        # Общее количество пользователей
        c.execute('SELECT COUNT(*) FROM users')
        total_users = c.fetchone()[0]
        
        # Активные пользователи за 24 часа
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        c.execute('SELECT COUNT(*) FROM users WHERE last_game > ?', (yesterday,))
        active_users = c.fetchone()[0]
        
        # Общее количество sun
        c.execute('SELECT SUM(sun) FROM users')
        total_sun = c.fetchone()[0] or 0
        
        # Количество Premium пользователей
        c.execute('SELECT COUNT(*) FROM users WHERE has_premium_skin = 1')
        premium_users = c.fetchone()[0]
        
        conn.close()
        
        text = (
            f"📊 Статистика бота:\n\n"
            f"👥 Всего пользователей: {total_users}\n"
            f"📱 Активных за 24ч: {active_users}\n"
            f"☀️ Всего sun: {total_sun}\n"
            f"✨ Premium пользователей: {premium_users}"
        )
        
        bot.send_message(message.chat.id, text)
        
    except Exception as e:
        logger.error(f"Error showing stats: {e}")
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        text = message.text.split(maxsplit=1)[1]
        
        conn = sqlite3.connect('snake_game.db')
        c = conn.cursor()
        c.execute('SELECT user_id FROM users')
        users = c.fetchall()
        conn.close()
        
        success = 0
        failed = 0
        
        for user in users:
            try:
                bot.send_message(user[0], text)
                success += 1
            except:
                failed += 1
        
        bot.send_message(
            message.chat.id,
            f"✅ Рассылка завершена\n"
            f"Успешно: {success}\n"
            f"Ошибок: {failed}"
        )
        
    except Exception as e:
        logger.error(f"Error broadcasting: {e}")
        bot.send_message(message.chat.id, "❌ Использование: /broadcast ТЕКСТ")

# Обработчик данных от веб-приложения
@bot.message_handler(content_types=['web_app_data'])
def web_app_data(message):
    try:
        data = json.loads(message.web_app_data.data)
        user_id = str(message.from_user.id)
        user_data = get_user_data(user_id)
        
        if not user_data:
            logger.error(f"User data not found: {user_id}")
            return
            
        # Обновляем данные пользователя
        earned_sun = data.get('sun', 0) - user_data.get('sun', 0)
        user_data['sun'] = data.get('sun', user_data.get('sun', 0))
        user_data['last_game'] = datetime.now().isoformat()
        
        # Если есть реферер, начисляем бонус
        if user_data.get('referrer_id') and earned_sun > 0:
            referrer_data = get_user_data(user_data['referrer_id'])
            if referrer_data:
                referral_bonus = int(earned_sun * 0.1)  # 10% от заработка
                referrer_data['sun'] = referrer_data.get('sun', 0) + referral_bonus
                update_user_data(user_data['referrer_id'], referrer_data)
                log_transaction(user_data['referrer_id'], 'referral_farm_bonus', referral_bonus)
                
                bot.send_message(
                    user_data['referrer_id'],
                    f"💰 Ваш реферал заработал {earned_sun} ☀️\n"
                    f"Ваш бонус: +{referral_bonus} ☀️"
                )
        
        update_user_data(user_id, user_data)
        
        # Отправляем статистику игры
        bot.send_message(
            message.chat.id,
            f"🎮 Игра завершена!\n\n"
            f"📊 Статистика:\n"
            f"☀️ Заработано: {earned_sun}\n"
            f"💰 Всего sun: {user_data['sun']}"
        )
        
    except Exception as e:
        logger.error(f"Error processing web app data: {e}\n{traceback.format_exc()}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка при сохранении прогресса")

# Запуск бота
if __name__ == '__main__':
    logger.info("Bot started")
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        logger.error(f"Bot polling error: {e}")