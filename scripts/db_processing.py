import sqlite3
import json
import os
import datetime


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class DBHelper(metaclass=Singleton):
    DB_FILENAME = 'citizens.db'
    DB_PATH = os.path.abspath(os.path.split(os.path.abspath(__file__))[0] + '/../resources/citizens.db')
    START_IMPORT_ID = 1

    def __init__(self):
        if not os.path.exists(self.DB_PATH):
            open(self.DB_PATH, 'w').close()

            conn = sqlite3.connect(self.DB_PATH)
            cursor = conn.cursor()
            cursor.executescript("""
            CREATE TABLE imports(
                import_id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_time TEXT NOT NULL
            );
            
            CREATE TABLE citizens(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_id INTEGER NOT NULL,
                citizen_id INTEGER NOT NULL,
                town TEXT NOT NULL,
                street TEXT NOT NULL,
                building TEXT NOT NULL,
                apartment INTEGER NOT NULL,
                name TEXT NOT NULL,
                birth_date TEXT NOT NULL,
                gender TEXT NOT NULL CHECK(gender IN ('male', 'female')),
                CONSTRAINT citizens_fk FOREIGN KEY (import_id) REFERENCES imports(import_id)
            );
                
            CREATE TABLE  relatives(
                id1 INTEGER NOT NULL,
                id2 INTEGER NOT NULL,
                CONSTRAINT relatives_pk PRIMARY KEY (id1, id2),
                CONSTRAINT relatives_fk_id1 FOREIGN KEY (id1) REFERENCES citizens(id),
                CONSTRAINT relatives_fk_id2 FOREIGN KEY (id2) REFERENCES citizens(id)
            );
            """)
            cursor.close()
            conn.commit()
            conn.close()

    def import_data(self, citizens: tuple) -> int:
        pass
