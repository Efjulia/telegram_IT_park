import telebot
import sqlite3
from telebot import types

import password
from password import bot_token, ADMIN_ID

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    # Создание таблиц
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT NOT NULL,
            address TEXT NOT NULL,
            consent INTEGER NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'В ожидании',
            specialist_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (specialist_id) REFERENCES specialists (specialist_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS specialists (
            specialist_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            approved INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT,
            FOREIGN KEY (request_id) REFERENCES requests (request_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            photo TEXT,
            FOREIGN KEY (request_id) REFERENCES requests (request_id)
        )
    ''')
    cursor.execute('PRAGMA journal_mode=WAL;')  # Включаем WAL-режим
    conn.commit()
    conn.close()

# Инициализация базы данных при запуске бота
init_db()
bot_token = password.bot_token
# Создание бота
bot = telebot.TeleBot(bot_token)

# Определяем ID администратора
ADMIN_ID = password.ADMIN_ID  # Замените на реальный ID администратора

# Главное меню
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('Создать заявку', 'Проверить статус заявки', 'Оставить отзыв', 'Регистрация')
    return markup

# Меню администратора
def admin_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('Назначить специалиста', 'Просмотреть заявки', 'Просмотреть специалистов', 'Статистика')
    return markup

# Меню специалиста
def specialist_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('Мои заявки', 'Отправить отчет', 'Главное меню')
    return markup

# Проверка, является ли пользователь специалистом
def is_specialist(user_id):
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT specialist_id FROM specialists WHERE specialist_id = ? AND approved = 1', (user_id,))
        specialist = cursor.fetchone()
        conn.close()
        return specialist is not None
    except sqlite3.Error as e:
        print(f"Ошибка при проверке специалиста: {e}")
        return False

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start_message(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, 'Привет, администратор! Выберите действие:', reply_markup=admin_menu())
    elif is_specialist(message.from_user.id):
        bot.send_message(message.chat.id, 'Привет, специалист! Выберите действие:', reply_markup=specialist_menu())
    else:
        bot.send_message(message.chat.id, 'Привет! Я бот для управления заявками. Выберите действие:', reply_markup=main_menu())

# Обработчик для регистрации
@bot.message_handler(func=lambda message: message.text == 'Регистрация')
def start_registration(message):
    bot.send_message(message.chat.id, 'Введи свое ФИО:')
    bot.register_next_step_handler(message, get_name)

def get_name(message):
    user_data = {'full_name': message.text}
    bot.send_message(message.chat.id, 'Отлично! Теперь введи свой контактный телефон:')
    bot.register_next_step_handler(message, get_phone, user_data)

def get_phone(message, user_data):
    user_data['phone'] = message.text
    bot.send_message(message.chat.id, 'Теперь введи свой e-mail:')
    bot.register_next_step_handler(message, get_email, user_data)

def get_email(message, user_data):
    user_data['email'] = message.text
    bot.send_message(message.chat.id, 'Введи свой адрес:')
    bot.register_next_step_handler(message, get_address, user_data)

def get_address(message, user_data):
    user_data['address'] = message.text
    bot.send_message(message.chat.id, 'Согласен ли ты на обработку персональных данных? (да/нет)')
    bot.register_next_step_handler(message, get_consent, user_data)

def get_consent(message, user_data):
    consent = message.text.lower()
    if consent == 'да':
        try:
            conn = sqlite3.connect('bot_database.db')
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (message.from_user.id,))
            existing_user = cursor.fetchone()

            if existing_user:
                cursor.execute('''
                    UPDATE users
                    SET full_name = ?, phone = ?, email = ?, address = ?, consent = ?
                    WHERE user_id = ?
                ''', (user_data['full_name'], user_data['phone'], user_data['email'], user_data['address'], 1, message.from_user.id))
                bot.send_message(message.chat.id, 'Ваши данные обновлены!', reply_markup=main_menu())
            else:
                cursor.execute('''
                    INSERT INTO users (user_id, full_name, phone, email, address, consent)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (message.from_user.id, user_data['full_name'], user_data['phone'], user_data['email'], user_data['address'], 1))
                bot.send_message(message.chat.id, 'Регистрация завершена! Теперь ты можешь создавать заявки.', reply_markup=main_menu())

            conn.commit()
        except sqlite3.Error as e:
            bot.send_message(message.chat.id, f'Ошибка при регистрации: {e}')
        finally:
            conn.close()
    else:
        bot.send_message(message.chat.id, 'Регистрация отменена.', reply_markup=main_menu())

# Обработчик для создания заявки
@bot.message_handler(func=lambda message: message.text == 'Создать заявку')
def create_request(message):
    categories = ["Проблема 1", "Проблема 2", "Проблема 3"]
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    for category in categories:
        markup.add(category)
    bot.send_message(message.chat.id, 'Выбери категорию проблемы:', reply_markup=markup)
    bot.register_next_step_handler(message, get_category)

def get_category(message):
    user_data = {'category': message.text}
    bot.send_message(message.chat.id, 'Опиши проблему:')
    bot.register_next_step_handler(message, get_description, user_data)

def get_description(message, user_data):
    user_data['description'] = message.text
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO requests (user_id, category, description)
            VALUES (?, ?, ?)
        ''', (message.from_user.id, user_data['category'], user_data['description']))
        conn.commit()
        bot.send_message(message.chat.id, 'Заявка создана! Мы свяжемся с тобой.', reply_markup=main_menu())
    except sqlite3.Error as e:
        bot.send_message(message.chat.id, f'Ошибка при создании заявки: {e}')
    finally:
        conn.close()

# Обработчик для проверки статуса заявки
@bot.message_handler(func=lambda message: message.text == 'Проверить статус заявки')
def check_status(message):
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT request_id, category, status FROM requests WHERE user_id = ?', (message.from_user.id,))
        requests = cursor.fetchall()

        if requests:
            for req in requests:
                bot.send_message(message.chat.id, f"Заявка #{req[0]}\nКатегория: {req[1]}\nСтатус: {req[2]}")
        else:
            bot.send_message(message.chat.id, "У вас нет активных заявок.", reply_markup=main_menu())
    except sqlite3.Error as e:
        bot.send_message(message.chat.id, f'Ошибка при проверке статуса заявок: {e}')
    finally:
        conn.close()

# Обработчик для оставления отзыва
@bot.message_handler(func=lambda message: message.text == 'Оставить отзыв')
def leave_feedback(message):
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT request_id FROM requests WHERE user_id = ? AND status = "Выполнено"', (message.from_user.id,))
        requests = cursor.fetchall()

        if requests:
            for req in requests:
                bot.send_message(message.chat.id, f"Заявка #{req[0]}")
            bot.send_message(message.chat.id, "Введи ID заявки, чтобы оставить отзыв:")
            bot.register_next_step_handler(message, get_feedback_rating)
        else:
            bot.send_message(message.chat.id, "У вас нет завершенных заявок.", reply_markup=main_menu())
    except sqlite3.Error as e:
        bot.send_message(message.chat.id, f'Ошибка при получении заявок: {e}')
    finally:
        conn.close()

def get_feedback_rating(message):
    try:
        request_id = int(message.text)
        bot.send_message(message.chat.id, "Оцените работу специалиста (от 1 до 5):")
        bot.register_next_step_handler(message, get_feedback_comment, request_id)
    except ValueError:
        bot.send_message(message.chat.id, "Некорректный ID заявки.", reply_markup=main_menu())

def get_feedback_comment(message, request_id):
    try:
        rating = int(message.text)
        if 1 <= rating <= 5:
            bot.send_message(message.chat.id, "Напишите комментарий:")
            bot.register_next_step_handler(message, save_feedback, request_id, rating)
        else:
            bot.send_message(message.chat.id, "Оценка должна быть от 1 до 5.", reply_markup=main_menu())
    except ValueError:
        bot.send_message(message.chat.id, "Некорректная оценка.", reply_markup=main_menu())

def save_feedback(message, request_id, rating):
    comment = message.text
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO feedback (request_id, rating, comment) VALUES (?, ?, ?)', (request_id, rating, comment))
        conn.commit()
        bot.send_message(message.chat.id, "Спасибо за ваш отзыв!", reply_markup=main_menu())
    except sqlite3.Error as e:
        bot.send_message(message.chat.id, f'Ошибка при сохранении отзыва: {e}')
    finally:
        conn.close()

# Обработчик для назначения специалиста (администратор)
@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID and message.text == 'Назначить специалиста')
def assign_specialist(message):
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT request_id, category, description FROM requests WHERE status = "В ожидании"')
        requests = cursor.fetchall()

        if requests:
            for req in requests:
                bot.send_message(message.chat.id, f"Заявка #{req[0]}\nКатегория: {req[1]}\nОписание: {req[2]}")
            bot.send_message(message.chat.id, "Введи ID заявки, чтобы назначить специалиста:")
            bot.register_next_step_handler(message, choose_specialist)
        else:
            bot.send_message(message.chat.id, "Нет заявок в статусе 'В ожидании'.", reply_markup=admin_menu())
    except sqlite3.Error as e:
        bot.send_message(message.chat.id, f'Ошибка при получении заявок: {e}')
    finally:
        conn.close()

def choose_specialist(message):
    try:
        request_id = int(message.text)
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT specialist_id, full_name FROM specialists WHERE approved = 1')
        specialists = cursor.fetchall()

        if specialists:
            for spec in specialists:
                bot.send_message(message.chat.id, f"Специалист #{spec[0]}\nИмя: {spec[1]}")
            bot.send_message(message.chat.id, "Введи ID специалиста, чтобы назначить его на заявку:")
            bot.register_next_step_handler(message, assign_specialist_to_request, request_id)
        else:
            bot.send_message(message.chat.id, "Нет доступных специалистов.", reply_markup=admin_menu())
    except ValueError:
        bot.send_message(message.chat.id, "Некорректный ID заявки.", reply_markup=admin_menu())
    except sqlite3.Error as e:
        bot.send_message(message.chat.id, f'Ошибка при получении специалистов: {e}')
    finally:
        conn.close()

def assign_specialist_to_request(message, request_id):
    try:
        specialist_id = int(message.text)
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE requests SET specialist_id = ?, status = "В работе" WHERE request_id = ?', (specialist_id, request_id))
        conn.commit()
        bot.send_message(message.chat.id, f"Специалист назначен на заявку #{request_id}.", reply_markup=admin_menu())
    except ValueError:
        bot.send_message(message.chat.id, "Некорректный ID специалиста.", reply_markup=admin_menu())
    except sqlite3.Error as e:
        bot.send_message(message.chat.id, f'Ошибка при назначении специалиста: {e}')
    finally:
        conn.close()

# Обработчик для просмотра заявок (администратор)
@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID and message.text == 'Просмотреть заявки')
def view_requests(message):
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT request_id, category, status FROM requests')
        requests = cursor.fetchall()

        if requests:
            for req in requests:
                bot.send_message(message.chat.id, f"Заявка #{req[0]}\nКатегория: {req[1]}\nСтатус: {req[2]}")
        else:
            bot.send_message(message.chat.id, "Нет заявок.", reply_markup=admin_menu())
    except sqlite3.Error as e:
        bot.send_message(message.chat.id, f'Ошибка при получении заявок: {e}')
    finally:
        conn.close()

# Обработчик для просмотра специалистов (администратор)
@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID and message.text == 'Просмотреть специалистов')
def view_specialists(message):
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT specialist_id, full_name, approved FROM specialists')
        specialists = cursor.fetchall()

        if specialists:
            for spec in specialists:
                bot.send_message(message.chat.id, f"Специалист #{spec[0]}\nИмя: {spec[1]}\nСтатус: {'Подтвержден' if spec[2] else 'Не подтвержден'}")
        else:
            bot.send_message(message.chat.id, "Нет специалистов.", reply_markup=admin_menu())
    except sqlite3.Error as e:
        bot.send_message(message.chat.id, f'Ошибка при получении специалистов: {e}')
    finally:
        conn.close()

# Обработчик для просмотра статистики (администратор)
@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID and message.text == 'Статистика')
def view_statistics(message):
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM requests')
        total_requests = cursor.fetchone()[0]
        cursor.execute('SELECT AVG(rating) FROM feedback')
        avg_rating = cursor.fetchone()[0]

        bot.send_message(message.chat.id, f"Общее количество заявок: {total_requests}\nСредний рейтинг специалистов: {avg_rating:.2f}", reply_markup=admin_menu())
    except sqlite3.Error as e:
        bot.send_message(message.chat.id, f'Ошибка при получении статистики: {e}')
    finally:
        conn.close()

# Обработчик для регистрации специалиста
@bot.message_handler(func=lambda message: message.text == 'Регистрация специалиста')
def register_specialist(message):
    bot.send_message(message.chat.id, "Введи свое ФИО:")
    bot.register_next_step_handler(message, get_specialist_name)

def get_specialist_name(message):
    user_data = {'full_name': message.text}
    bot.send_message(message.chat.id, "Введи свой контактный телефон:")
    bot.register_next_step_handler(message, get_specialist_phone, user_data)

def get_specialist_phone(message, user_data):
    user_data['phone'] = message.text
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO specialists (full_name, phone) VALUES (?, ?)', (user_data['full_name'], user_data['phone']))
        conn.commit()
        bot.send_message(message.chat.id, "Регистрация завершена! Ожидайте подтверждения администратора.", reply_markup=main_menu())
    except sqlite3.Error as e:
        bot.send_message(message.chat.id, f'Ошибка при регистрации специалиста: {e}')
    finally:
        conn.close()

# Обработчик для просмотра заявок специалиста
@bot.message_handler(func=lambda message: message.text == 'Мои заявки')
def view_my_requests(message):
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT request_id, category, description, status FROM requests WHERE specialist_id = ?', (message.from_user.id,))
        requests = cursor.fetchall()

        if requests:
            for req in requests:
                bot.send_message(message.chat.id, f"Заявка #{req[0]}\nКатегория: {req[1]}\nОписание: {req[2]}\nСтатус: {req[3]}")
        else:
            bot.send_message(message.chat.id, "У вас нет назначенных заявок.", reply_markup=specialist_menu())
    except sqlite3.Error as e:
        bot.send_message(message.chat.id, f'Ошибка при получении заявок: {e}')
    finally:
        conn.close()

# Обработчик для отправки отчета
@bot.message_handler(func=lambda message: message.text == 'Отправить отчет')
def submit_report(message):
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT request_id FROM requests WHERE specialist_id = ? AND status = "В работе"', (message.from_user.id,))
        requests = cursor.fetchall()

        if requests:
            for req in requests:
                bot.send_message(message.chat.id, f"Заявка #{req[0]}")
            bot.send_message(message.chat.id, "Введи ID заявки, чтобы отправить отчет:")
            bot.register_next_step_handler(message, get_report_description)
        else:
            bot.send_message(message.chat.id, "У вас нет заявок в работе.", reply_markup=specialist_menu())
    except sqlite3.Error as e:
        bot.send_message(message.chat.id, f'Ошибка при получении заявок: {e}')
    finally:
        conn.close()

def get_report_description(message):
    try:
        request_id = int(message.text)
        bot.send_message(message.chat.id, "Опишите выполненную работу:")
        bot.register_next_step_handler(message, get_report_photo, request_id)
    except ValueError:
        bot.send_message(message.chat.id, "Некорректный ID заявки.", reply_markup=specialist_menu())

def get_report_photo(message, request_id):
    description = message.text
    bot.send_message(message.chat.id, "Прикрепите фотоотчет (если есть):")
    bot.register_next_step_handler(message, save_report, request_id, description)

def save_report(message, request_id, description):
    try:
        photo_id = message.photo[-1].file_id if message.photo else None
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO reports (request_id, description, photo) VALUES (?, ?, ?)', (request_id, description, photo_id))
        cursor.execute('UPDATE requests SET status = "Выполнено" WHERE request_id = ?', (request_id,))
        conn.commit()
        bot.send_message(message.chat.id, "Отчет успешно отправлен!", reply_markup=specialist_menu())
    except sqlite3.Error as e:
        bot.send_message(message.chat.id, f'Ошибка при отправке отчета: {e}')
    finally:
        conn.close()

# Обработчик для возврата в главное меню
@bot.message_handler(func=lambda message: message.text == 'Главное меню')
def return_to_main_menu(message):
    bot.send_message(message.chat.id, 'Вы вернулись в главное меню.', reply_markup=main_menu())

# Запуск бота
bot.polling()