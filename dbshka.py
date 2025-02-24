import sqlite3

# Создание базы данных и таблиц
def create_database():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            consent INTEGER DEFAULT 0
        )
    ''')

    # Таблица специалистов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS specialists (
            specialist_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            phone TEXT,
            approved INTEGER DEFAULT 0
        )
    ''')

    # Таблица заявок
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            category TEXT,
            description TEXT,
            status TEXT DEFAULT 'В ожидании',
            specialist_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (specialist_id) REFERENCES specialists (specialist_id)
        )
    ''')

    # Таблица отчетов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER,
            description TEXT,
            photo TEXT,
            FOREIGN KEY (request_id) REFERENCES requests (request_id)
        )
    ''')

    # Таблица отзывов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER,
            rating INTEGER,
            comment TEXT,
            FOREIGN KEY (request_id) REFERENCES requests (request_id)
        )
    ''')

    conn.commit()
    conn.close()

create_database()
