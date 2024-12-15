from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
# Настраиваем CORS для всех источников (для тестирования)
CORS(app)

# Функция для подключения к базе данных
def get_db():
    try:
        conn = sqlite3.connect('snake_game.db')
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

# Тестовый эндпоинт для проверки работы API
@app.route('/api/test')
def test_connection():
    return jsonify({'status': 'ok'})

# Главная страница с данными
@app.route('/')
def index():
    try:
        conn = get_db()
        if not conn:
            return "Ошибка подключения к базе данных"
            
        cur = conn.cursor()
        cur.execute('''SELECT 
                        username,
                        sun,
                        has_sun_skin,
                        has_premium_skin,
                        subscription_task_completed,
                        referral_count,
                        last_game
                    FROM users 
                    WHERE username IS NOT NULL 
                    ORDER BY sun DESC''')
        users = cur.fetchall()
        conn.close()
        
        if not users:
            return "Нет данных в базе"
        
        html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Star Snake Dashboard</title>
            <style>
                body {
                    background: #0a0a2e;
                    color: white;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    margin: 0;
                    padding: 20px;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                }
                h1 {
                    text-align: center;
                    color: #ffd700;
                    margin-bottom: 30px;
                }
                .stats {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }
                .stat-card {
                    background: rgba(255, 255, 255, 0.1);
                    padding: 20px;
                    border-radius: 10px;
                    text-align: center;
                }
                .stat-value {
                    font-size: 24px;
                    font-weight: bold;
                    color: #ffd700;
                }
                .users-table {
                    width: 100%;
                    border-collapse: collapse;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 10px;
                    overflow: hidden;
                }
                .users-table th, .users-table td {
                    padding: 15px;
                    text-align: left;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                }
                .users-table th {
                    background: rgba(255, 255, 255, 0.2);
                    font-weight: bold;
                }
                .users-table tr:hover {
                    background: rgba(255, 255, 255, 0.05);
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🐍 Star Snake Dashboard</h1>
                
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-value">''' + str(len(users)) + '''</div>
                        <div>Всего игроков</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">''' + str(sum(user[1] for user in users)) + '''</div>
                        <div>Всего sun</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">''' + str(sum(1 for user in users if user[2])) + '''</div>
                        <div>Sun скинов</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">''' + str(sum(1 for user in users if user[3])) + '''</div>
                        <div>Premium скинов</div>
                    </div>
                </div>

                <table class="users-table">
                    <tr>
                        <th>Игрок</th>
                        <th>Sun</th>
                        <th>Sun скин</th>
                        <th>Premium</th>
                        <th>Задание</th>
                        <th>Рефералов</th>
                        <th>Последняя игра</th>
                    </tr>
        '''
        
        for user in users:
            html += f'''
                    <tr>
                        <td>@{user[0]}</td>
                        <td>{user[1]} ☀️</td>
                        <td>{'✅' if user[2] else '❌'}</td>
                        <td>{'✅' if user[3] else '❌'}</td>
                        <td>{'✅' if user[4] else '❌'}</td>
                        <td>{user[5]}</td>
                        <td>{user[6] if user[6] else '-'}</td>
                    </tr>
            '''
        
        html += '''
                </table>
            </div>
            <script>
                // Автообновление каждые 30 секунд
                setInterval(() => {
                    location.reload();
                }, 30000);
            </script>
        </body>
        </html>
        '''
        
        return html
        
    except Exception as e:
        return f"Ошибка: {str(e)}"

# Получение данных пользователя
@app.route('/api/user/<user_id>')
def get_user(user_id):
    try:
        conn = get_db()
        if not conn:
            return jsonify({'error': 'Database connection error'}), 500
            
        cur = conn.cursor()
        cur.execute('''SELECT * FROM users WHERE user_id = ?''', (user_id,))
        user = cur.fetchone()
        conn.close()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        return jsonify({
            'user_id': user['user_id'],
            'username': user['username'],
            'sun': user['sun'],
            'has_sun_skin': bool(user['has_sun_skin']),
            'has_premium_skin': bool(user['has_premium_skin'])
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Обновление игровых данных
@app.route('/api/update_game', methods=['POST'])
def update_game():
    try:
        data = request.json
        user_id = data.get('user_id')
        score = data.get('score')
        earned_sun = data.get('earned_sun')
        
        conn = get_db()
        if not conn:
            return jsonify({'error': 'Database connection error'}), 500
            
        cur = conn.cursor()
        cur.execute('UPDATE users SET sun = sun + ?, last_game = ? WHERE user_id = ?',
                   (earned_sun, datetime.now().isoformat(), user_id))
        conn.commit()
        
        # Получаем обновленные данные
        cur.execute('SELECT sun FROM users WHERE user_id = ?', (user_id,))
        new_sun = cur.fetchone()['sun']
        conn.close()
        
        return jsonify({
            'success': True,
            'new_sun': new_sun,
            'score': score
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API для получения sun
@app.route('/api/get_sun/<user_id>')
def get_sun(user_id):
    try:
        conn = get_db()
        if not conn:
            return jsonify({'error': 'Database connection error'}), 500
            
        cur = conn.cursor()
        cur.execute('SELECT sun FROM users WHERE user_id = ?', (user_id,))
        result = cur.fetchone()
        conn.close()
        
        return jsonify({'sun': result['sun'] if result else 0})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API для обновления sun
@app.route('/api/update_sun', methods=['POST'])
def update_sun():
    try:
        data = request.json
        user_id = data.get('user_id')
        new_sun = data.get('sun')
        
        if not user_id or new_sun is None:
            return jsonify({'error': 'Missing data'}), 400
            
        conn = get_db()
        if not conn:
            return jsonify({'error': 'Database connection error'}), 500
            
        cur = conn.cursor()
        cur.execute('UPDATE users SET sun = ? WHERE user_id = ?', (new_sun, user_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Запуск сервера
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)