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
ADMIN_ID = 1454515378
CHANNEL_ID = '@mariartytt'
bot = telebot.TeleBot(TOKEN)

# Инициализация базы данных
def init_db():
    try:
        conn = sqlite3.connect('snake_game.db')
        c = conn.cursor()
        
        # Удаляем старые таблицы если они есть
        c.execute('DROP TABLE IF EXISTS users')
        c.execute('DROP TABLE IF EXISTS transactions')
        
        # Создаем новые таблицы
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (user_id TEXT PRIMARY KEY,
                      username TEXT,
                      best_score INTEGER DEFAULT 0,
                      sun INTEGER DEFAULT 0,
                      has_sun_skin BOOLEAN DEFAULT 0,
                      has_premium_skin BOOLEAN DEFAULT 0,
                      last_game TEXT,
                      registration_date TEXT,
                      referrer_id TEXT,
                      referral_count INTEGER DEFAULT 0)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS transactions
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id TEXT,
                      type TEXT,
                      amount INTEGER,
                      timestamp TEXT,
                      FOREIGN KEY (user_id) REFERENCES users(user_id))''')
        
        conn.commit()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
    finally:
        conn.close()

init_db()

def get_user_by_username(username):
    conn = sqlite3.connect('snake_game.db')
    c = conn.cursor()
    username = username.replace('@', '')
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
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
            'registration_date': data[7],
            'referrer_id': data[8],
            'referral_count': data[9]
        }
    return None

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
            'registration_date': data[7],
            'referrer_id': data[8],
            'referral_count': data[9]
        }
    return {
        'user_id': str(user_id),
        'username': None,
        'best_score': 0,
        'sun': 0,
        'has_sun_skin': False,
        'has_premium_skin': False,
        'last_game': None,
        'registration_date': None,
        'referrer_id': None,
        'referral_count': 0
    }

def update_user_data(user_id, data):
    conn = sqlite3.connect('snake_game.db')
    c = conn.cursor()
    try:
        c.execute('''INSERT OR REPLACE INTO users 
                     (user_id, username, best_score, sun, has_sun_skin, has_premium_skin, last_game, registration_date, referrer_id, referral_count)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                 (str(user_id), data.get('username'), data.get('best_score', 0),
                  data.get('sun', 0), data.get('has_sun_skin', False),
                  data.get('has_premium_skin', False), datetime.now().isoformat(),
                  data.get('registration_date', datetime.now().isoformat()),
                  data.get('referrer_id'), data.get('referral_count', 0)))
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

def get_leaderboard():
    conn = sqlite3.connect('snake_game.db')
    c = conn.cursor()
    c.execute('''SELECT username, best_score FROM users 
                 ORDER BY best_score DESC LIMIT 10''')
    data = c.fetchall()
    conn.close()
    return data

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
    user_id = str(message.from_user.id)
    username = message.from_user.username
    
    # Проверяем реферальный код
    args = message.text.split()
    referrer_id = args[1] if len(args) > 1 else None
    
    # Регистрация нового пользователя
    if not get_user_data(user_id).get('username'):
        initial_sun = 20 if referrer_id else 0
        update_user_data(user_id, {
            'username': username,
            'best_score': 0,
            'sun': initial_sun,
            'has_sun_skin': False,
            'has_premium_skin': False,
            'referrer_id': referrer_id
        })
        
        # Награждаем реферера
        if referrer_id:
            referrer_data = get_user_data(referrer_id)
            if referrer_data.get('username'):
                referrer_data['sun'] = referrer_data.get('sun', 0) + 20
                referrer_data['referral_count'] = referrer_data.get('referral_count', 0) + 1
                update_user_data(referrer_id, referrer_data)
                
                bot.send_message(
                    referrer_id, 
                    f"🎉 Новый реферал! Получено:\n"
                    f"• +20 ☀️ за приглашение\n"
                    f"• 10% от фарма реферала"
                )
                
                bot.send_message(
                    message.chat.id, 
                    f"🎁 Добро пожаловать!\n\n"
                    f"Вы получаете:\n"
                    f"• +20 ☀️ за регистрацию по реферальной ссылке"
                )
        else:
            bot.send_message(
                message.chat.id, 
                f"🎁 Добро пожаловать в игру!"
            )
        
        logger.info(f"New user registered: {user_id} (@{username})")
    
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

@bot.message_handler(func=lambda message: message.text == "🎮 Играть")
def play_button(message):
    bot.send_message(
        message.chat.id,
        "🎮 Нажмите кнопку ниже, чтобы начать игру:",
        reply_markup=get_webapp_keyboard()
    )

@bot.message_handler(func=lambda message: message.text == "🏆 Лидерборд")
def show_leaderboard_button(message):
    leaderboard = get_leaderboard()
    text = "🏆 Топ-10 игроков:\n\n"
    for i, (username, score) in enumerate(leaderboard, 1):
        text += f"{i}. @{username or 'Неизвестный'} — {score}\n"
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda message: message.text == "👥 Рефералка")
def show_referral_button(message):
    bot_username = bot.get_me().username
    user_id = str(message.from_user.id)
    link = f"https://t.me/{bot_username}?start={user_id}"
    
    user_data = get_user_data(user_id)
    refs_count = user_data.get('referral_count', 0)
    
    text = (
        f"👥 Реферальная система\n\n"
        f"🔗 Ваша ссылка:\n{link}\n\n"
        f"📊 Ваши рефералы: {refs_count}\n\n"
        f"💰 Награды:\n"
        f"• +20 ☀️ за приглашение реферала\n"
        f"• +10% от фарма рефералов\n"
        f"• Реферал получает +20 ☀️\n\n"
        f"ℹ️ Отправьте эту ссылку друзьям и\n"
        f"получайте награды за их игру!"
    )
    
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda message: message.text == "ℹ️ Помощь")
def help_button(message):
    help_text = (
        "🎮 Как играть:\n"
        "• Управляйте змейкой стрелками или свайпами\n"
        "• Собирайте яблоки для роста и получения sun\n"
        "• Избегайте столкновений со стенами и хвостом\n\n"
        "💰 Sun и скины:\n"
        "• Sun можно потратить на скины в магазине\n"
        "• Sun скин даёт +10% к фарму\n"
        "• Premium скин даёт +50% к фарму\n\n"
        "👥 Реферальная система:\n"
        "• Приглашайте друзей и получайте награды\n"
        "• +20 ☀️ за каждого реферала\n"
        "• +10% от фарма рефералов"
    )
    bot.send_message(message.chat.id, help_text)

# Админ команды
@bot.message_handler(commands=['give_premium'])
def give_premium(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ У вас нет прав для выполнения этой команды")
        return
    
    try:
        args = message.text.split()
        if len(args) != 2:
            bot.send_message(message.chat.id, "❌ Использование: /give_premium USERNAME")
            return
        
        username = args[1].replace('@', '')
        user_data = get_user_by_username(username)
        
        if not user_data:
            bot.send_message(message.chat.id, f"❌ Пользователь @{username} не найден")
            return
        
        user_data['has_premium_skin'] = True
        update_user_data(user_data['user_id'], user_data)
        log_transaction(user_data['user_id'], 'premium_given', 0)
        
        try:
            bot.send_message(
                int(user_data['user_id']),
                "✨ Поздравляем! Вам выдан Premium скин!\n\n"
                "Особенности Premium:\n"
                "• Уникальный градиентный скин\n"
                "• +50% к фарму sun\n"
                "• Уменьшенный таймер между играми"
            )
        except Exception as e:
            logger.error(f"Could not send message to user {user_data['user_id']}: {e}")
        
        bot.send_message(
            message.chat.id,
            f"✅ Premium успешно выдан пользователю @{username}"
        )
        
    except Exception as e:
        logger.error(f"Error giving premium: {e}")
        bot.send_message(
            message.chat.id,
            "❌ Произошла ошибка при выдаче Premium"
        )

@bot.message_handler(commands=['remove_premium'])
def remove_premium(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ У вас нет прав для выполнения этой команды")
        return
    
    try:
        args = message.text.split()
        if len(args) != 2:
            bot.send_message(message.chat.id, "❌ Использование: /remove_premium USERNAME")
            return
        
        username = args[1].replace('@', '')
        user_data = get_user_by_username(username)
        
        if not user_data:
            bot.send_message(message.chat.id, f"❌ Пользователь @{username} не найден")
            return
        
        user_data['has_premium_skin'] = False
        update_user_data(user_data['user_id'], user_data)
        log_transaction(user_data['user_id'], 'premium_removed', 0)
        
        try:
            bot.send_message(
                int(user_data['user_id']),
                "❌ Ваш Premium скин был деактивирован"
            )
        except Exception as e:
            logger.error(f"Could not send message to user {user_data['user_id']}: {e}")
        
        bot.send_message(
            message.chat.id,
            f"✅ Premium успешно удален у пользователя @{username}"
        )
        
    except Exception as e:
        logger.error(f"Error removing premium: {e}")
        bot.send_message(
            message.chat.id,
            "❌ Произошла ошибка при удалении Premium"
        )

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
        
        user_data = get_user_by_username(username)
        if user_data:
            user_data['sun'] = user_data.get('sun', 0) + amount
            update_user_data(user_data['user_id'], user_data)
            log_transaction(user_data['user_id'], 'admin_give_sun', amount)
            
            bot.send_message(message.chat.id, f"✅ Выдано {amount} ☀️ пользователю @{username}")
            bot.send_message(int(user_data['user_id']), f"🎁 Администратор выдал вам {amount} ☀️!")
        else:
            bot.send_message(message.chat.id, "❌ Пользователь не найден")
    except:
        bot.send_message(message.chat.id, "❌ Использование: /give_sun USERNAME AMOUNT")

@bot.message_handler(commands=['user_info'])
def user_info(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        username = message.text.split()[1].replace('@', '')
        user_data = get_user_by_username(username)
        
        if user_data:
            text = (
                f"👤 Информация о пользователе:\n\n"
                f"ID: {user_data['user_id']}\n"
                f"Username: @{user_data['username']}\n"
                f"Рекорд: {user_data['best_score']}\n"
                f"Sun: {user_data['sun']}\n"
                f"Sun скин: {'✅' if user_data['has_sun_skin'] else '❌'}\n"
                f"Premium: {'✅' if user_data['has_premium_skin'] else '❌'}\n"
                f"Последняя игра: {user_data['last_game']}\n"
                f"Дата регистрации: {user_data['registration_date']}\n"
                f"Рефералов: {user_data.get('referral_count', 0)}"
            )
            bot.send_message(message.chat.id, text)
        else:
            bot.send_message(message.chat.id, "❌ Пользователь не найден")
    except:
        bot.send_message(message.chat.id, "❌ Использование: /user_info USERNAME")

@bot.message_handler(commands=['stats'])
def admin_stats(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        conn = sqlite3.connect('snake_game.db')
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*) FROM users')
        total_users = c.fetchone()[0]
        
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        c.execute('SELECT COUNT(*) FROM users WHERE last_game > ?', (yesterday,))
        active_users = c.fetchone()[0]
        
        c.execute('SELECT SUM(sun) FROM users')
        total_sun = c.fetchone()[0] or 0
        
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
    except:
        bot.send_message(
            message.chat.id,
            "❌ Использование: /broadcast ТЕКСТ"
        )

@bot.message_handler(commands=['clear_db'])
def clear_database(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        init_db()  # Пересоздаем базу данных
        bot.send_message(message.chat.id, "✅ База данных очищена")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")

# Обработчик данных от веб-приложения
@bot.message_handler(content_types=['web_app_data'])
def web_app_data(message):
    try:
        data = json.loads(message.web_app_data.data)
        user_id = str(message.from_user.id)
        user_data = get_user_data(user_id)
        
        # Получаем данные о заработанном sun
        earned_sun = data.get('sun', 0) - user_data.get('sun', 0)
        
        # Если есть реферер, начисляем ему 10%
        if user_data.get('referrer_id'):
            referrer_data = get_user_data(user_data['referrer_id'])
            if referrer_data.get('username') and earned_sun > 0:
                referral_bonus = int(earned_sun * 0.1)  # 10% от заработка
                referrer_data['sun'] = referrer_data.get('sun', 0) + referral_bonus
                update_user_data(user_data['referrer_id'], referrer_data)
                try:
                    bot.send_message(
                        user_data['referrer_id'],
                        f"💰 Ваш реферал заработал {earned_sun} ☀️\n"
                        f"Ваш бонус: +{referral_bonus} ☀️"
                    )
                except:
                    logger.error(f"Could not send referral bonus message to {user_data['referrer_id']}")
        
        # Обновляем данные пользователя
        user_data['best_score'] = max(user_data.get('best_score', 0), data.get('bestScore', 0))
        user_data['sun'] = data.get('sun', user_data.get('sun', 0))
        user_data['has_sun_skin'] = data.get('hasSunSkin', user_data.get('has_sun_skin', False))
        user_data['has_premium_skin'] = data.get('hasPremiumSkin', user_data.get('has_premium_skin', False))
        user_data['last_game'] = datetime.now().isoformat()
        
        update_user_data(user_id, user_data)
        
        # Отправляем статистику игры
        bot.send_message(
            message.chat.id,
            f"🎮 Игра завершена!\n\n"
            f"📊 Статистика:\n"
            f"🏆 Счёт: {data.get('score', 0)}\n"
            f"☀️ Заработано: {earned_sun}\n"
            f"💰 Всего sun: {data.get('sun', 0)}"
        )
        
    except Exception as e:
        logger.error(f"Error processing web app data: {e}\n{traceback.format_exc()}")
        bot.send_message(
            message.chat.id,
            "❌ Произошла ошибка при сохранении прогресса"
        )

# Функция резервного копирования для Windows
def backup_data():
    while True:
        try:
            os.system('copy snake_game.db snake_game_backup.db')
            logger.info("Database backup created")
        except Exception as e:
            logger.error(f"Backup error: {e}")
        time.sleep(3600)

# Запуск бота
if __name__ == '__main__':
    # Запускаем резервное копирование в отдельном потоке
    backup_thread = threading.Thread(target=backup_data)
    backup_thread.daemon = True
    backup_thread.start()
    
    # Запускаем бота
    logger.info("Bot started")
    bot.infinity_polling()