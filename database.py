import sqlite3
from datetime import datetime


DB_NAME = "rout_bot.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Таблица мероприятий
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            photo TEXT,
            price REAL,
            date TEXT,
            is_sale_active BOOLEAN,
            qr_template TEXT,
            photo_album_link TEXT
        )
    """)

    # Таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            university TEXT,
            phone_number TEXT
        )
    """)

    # Таблица билетов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            event_id INTEGER,
            qr_code TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (event_id) REFERENCES events (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS used_tickets (
            ticket_id INTEGER PRIMARY KEY,
            FOREIGN KEY (ticket_id) REFERENCES tickets (id)
        )
    """)

    # Таблица отзывов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            event_id INTEGER,
            text TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (event_id) REFERENCES events (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_notifications (
            admin_id INTEGER,
            message_id INTEGER,
            user_id INTEGER,
            PRIMARY KEY (admin_id, message_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            event_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (event_id) REFERENCES events (id)
        )
    """)

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_link (
            link TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

# Инициализация базы данных при старте
init_db()

def add_user(user_id: int, full_name: str, university: str, phone_number: str) -> int:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (id, full_name, university, phone_number)
        VALUES (?, ?, ?, ?)
    """, (user_id, full_name, university, phone_number))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id

# Функция для получения пользователя по ID
def get_user(user_id: int) -> dict:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return {
            "id": user[0],
            "full_name": user[1],
            "university": user[2],
            "phone_number": user[3]
        }
    return None

def update_user(user_id: int, full_name: str, university: str) -> bool:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users
        SET full_name = ?, university = ?
        WHERE id = ?
    """, (full_name, university, user_id))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0


# Функция для получения всех мероприятий
def get_events() -> list:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events")
    events = cursor.fetchall()
    conn.close()
    return [{
        "id": event[0],
        "name": event[1],
        "description": event[2],
        "photo": event[3],
        "price": event[4],
        "date": event[5],
        "is_sale_active": bool(event[6]),
        "qr_template": event[7],
        "photo_album_link": event[8]
    } for event in events]

# Функция для добавления мероприятия
def add_event(
    name: str,
    description: str,
    photo: str,
    price: float,
    date: str,
    is_sale_active: bool,
    qr_template: str,
    photo_album_link: str = None
) -> int:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO events (name, description, photo, price, date, is_sale_active, qr_template, photo_album_link)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, description, photo, price, date, is_sale_active, qr_template, photo_album_link))
    event_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return event_id

# Функция для удаления мероприятия
def delete_event(event_id: int) -> bool:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

# Функция для редактирования мероприятия
def update_event(event_id: int, **kwargs):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Формируем запрос для обновления только переданных полей
    updates = []
    params = []
    for key, value in kwargs.items():
        updates.append(f"{key} = ?")
        params.append(value)
    params.append(event_id)

    query = f"UPDATE events SET {', '.join(updates)} WHERE id = ?"
    cursor.execute(query, tuple(params))
    conn.commit()
    conn.close()


def get_active_events() -> list:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events")
    events = cursor.fetchall()
    conn.close()

    current_date = datetime.now()  # Получаем текущую дату и время

    active_events = []
    for event in events:
        # Используем формат "YYYY-MM-DD HH:MM" для даты
        event_date = datetime.strptime(event[5], "%Y-%m-%d %H:%M")  # Измененный формат
        if event_date > current_date and bool(event[6]):  # Проверяем, что событие еще не прошло
            active_events.append({
                "id": event[0],
                "name": event[1],
                "description": event[2],
                "photo": event[3],
                "price": event[4],
                "date": event[5],
                "is_sale_active": bool(event[6]),
                "qr_template": event[7],
                "photo_album_link": event[8]
            })

    return active_events

def add_feedback(user_id: int, event_id: int, text: str) -> int:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO feedback (user_id, event_id, text)
        VALUES (?, ?, ?)
    """, (user_id, event_id, text))
    feedback_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return feedback_id

def get_event_by_id(event_id: int) -> dict:
    """
    Получает данные о мероприятии по его ID.
    :param event_id: ID мероприятия
    :return: Словарь с данными о мероприятии или None, если мероприятие не найдено
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Выполняем запрос к базе данных
    cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    event = cursor.fetchone()  # Получаем первую строку результата

    conn.close()

    if event:
        # Преобразуем результат в словарь
        return {
            "id": event[0],
            "name": event[1],
            "description": event[2],
            "photo": event[3],
            "price": event[4],
            "date": event[5],
            "is_sale_active": bool(event[6]),
            "qr_template": event[7],
            "photo_album_link": event[8]
        }
    return None  # Если мероприятие не


def add_admin_notification(admin_id, message_id, user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO admin_notifications (admin_id, message_id, user_id)
        VALUES (?, ?, ?)
    """, (admin_id, message_id, user_id))
    conn.commit()
    conn.close()

def get_admin_notifications(admin_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT message_id, user_id FROM admin_notifications
        WHERE admin_id = ?
    """, (admin_id,))
    result = [{"message_id": row[0], "user_id": row[1]} for row in cursor.fetchall()]
    conn.close()
    return result

def delete_admin_notifications(admin_id, user_id=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if user_id:
        cursor.execute("""
            DELETE FROM admin_notifications
            WHERE admin_id = ? AND user_id = ?
        """, (admin_id, user_id))
    else:
        cursor.execute("""
            DELETE FROM admin_notifications
            WHERE admin_id = ?
        """, (admin_id,))
    conn.commit()
    conn.close()

def add_user_event(user_id: int, event_id: int) -> int:
    """
    Добавляет купленное мероприятие пользователю.
    :param user_id: ID пользователя
    :param event_id: ID мероприятия
    :return: ID записи
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_events (user_id, event_id)
        VALUES (?, ?)
    """, (user_id, event_id))
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return record_id

def get_user_events(user_id: int) -> list:
    """
    Получает список купленных мероприятий пользователя.
    :param user_id: ID пользователя
    :return: Список мероприятий
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT events.* FROM events
        JOIN user_events ON events.id = user_events.event_id
        WHERE user_events.user_id = ?
    """, (user_id,))
    events = cursor.fetchall()
    conn.close()

    return [{
        "id": event[0],
        "name": event[1],
        "description": event[2],
        "photo": event[3],
        "price": event[4],
        "date": event[5],
        "is_sale_active": bool(event[6]),
        "qr_template": event[7],
        "photo_album_link": event[8]
    } for event in events]

def add_ticket(user_id: int, event_id: int, qr_code: str) -> int:
    """
    Добавляет билет пользователю.
    :param user_id: ID пользователя
    :param event_id: ID мероприятия
    :param qr_code: Путь к файлу QR-кода
    :return: ID билета
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tickets (user_id, event_id, qr_code)
        VALUES (?, ?, ?)
    """, (user_id, event_id, qr_code))
    ticket_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return ticket_id

def get_user_tickets(user_id: int) -> list:
    """
    Получает список билетов пользователя.
    :param user_id: ID пользователя
    :return: Список билетов
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT tickets.*, events.name FROM tickets
        JOIN events ON tickets.event_id = events.id
        WHERE tickets.user_id = ?
    """, (user_id,))
    tickets = cursor.fetchall()
    conn.close()

    return [{
        "id": ticket[0],
        "user_id": ticket[1],
        "event_id": ticket[2],
        "qr_code": ticket[3],
        "event_name": ticket[4]
    } for ticket in tickets]


def add_payment_link(link: str):
    conn = sqlite3.connect('rout_bot.db')
    cursor = conn.cursor()

    cursor.execute('''
    INSERT INTO payment_link (link)
    VALUES (?)
    ''', (link,))

    conn.commit()
    conn.close()


def get_payment_link():
    conn = sqlite3.connect('rout_bot.db')
    cursor = conn.cursor()

    cursor.execute('''
    SELECT link FROM payment_link
    ''', )

    result = cursor.fetchone()
    conn.close()

    return result[0] if result else None


def update_payment_link(new_link: str):
    conn = sqlite3.connect('rout_bot.db')
    cursor = conn.cursor()

    cursor.execute('''
    UPDATE payment_link
    SET link = ?
    ''', (new_link, ))

    conn.commit()
    conn.close()

def add_used_ticket(ticket_id: int):
    conn = sqlite3.connect('rout_bot.db')
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO used_tickets (ticket_id)
        VALUES (?)
    """, (ticket_id,))

    conn.commit()
    conn.close()

def get_all_used_tickets():
    conn = sqlite3.connect('rout_bot.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ticket_id FROM used_tickets
    """)

    used_tickets = cursor.fetchall()
    conn.close()

    return list(used_tickets)


def get_ticket(user_id, event_id):
    conn = sqlite3.connect("rout_bot.db")
    cursor = conn.cursor()

    # Ищем билет по user_id и event_id
    cursor.execute("""
        SELECT id, qr_code FROM tickets
        WHERE user_id = ? AND event_id = ?
    """, (user_id, event_id))

    row = cursor.fetchone()
    conn.close()

    # Проверяем, найден ли билет
    if row:
        return row[0]
    return None


def get_ticket_by_id(ticket_id):
    conn = sqlite3.connect("rout_bot.db")
    cursor = conn.cursor()

    # Ищем билет по ticket_id
    cursor.execute("""
        SELECT id, user_id, event_id, qr_code FROM tickets
        WHERE id = ?
    """, (ticket_id,))

    row = cursor.fetchone()
    conn.close()

    # Проверяем, найден ли билет
    if row:
        return {
            "ticket_id": row[0],
            "user_id": row[1],
            "event_id": row[2],
            "qr_code": row[3]
        }
    return None