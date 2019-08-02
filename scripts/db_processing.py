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
    DB_PATH = os.path.abspath(os.path.split(os.path.abspath(__file__))[0] + '/../citizens.db')

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

        self._conn: sqlite3.Connection
        self._conn = None

    def import_citizens(self, citizens: list) -> int:
        # check relatives
        relatives = dict()
        for citizen in citizens:
            relatives[citizen['citizen_id']] = citizen['relatives']
        for citizen, citizen_relatives in relatives.items():
            for relative in citizen_relatives:
                if citizen not in relatives[relative]:
                    raise ValueError

        # INSERT import
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO imports (import_time) VALUES (?);",
                       (datetime.datetime.now().isoformat(' ', 'milliseconds'),))
        import_rowid = cursor.lastrowid
        cursor.execute("SELECT import_id FROM imports WHERE ROWID=?;", (import_rowid,))
        import_id = cursor.fetchone()[0]

        try:
            # INSERT citizens
            for citizen in citizens:
                cursor.execute(
                    "INSERT INTO citizens (import_id, citizen_id, town, street, building, apartment, name, birth_date, gender)"
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);", (import_id, citizen['citizen_id'], citizen['town'],
                                                            citizen['street'], citizen['building'],
                                                            citizen['apartment'], citizen['name'],
                                                            datetime.datetime.strptime(citizen['birth_date'],
                                                                                       "%d.%m.%Y").strftime("%Y-%m-%d"),
                                                            citizen['gender']))

            # INSERT relatives
            worked_relatives = set()
            for citizen in citizens:
                for relative in citizen['relatives']:
                    if relative not in worked_relatives:
                        cursor.execute(
                            "INSERT INTO relatives (id1, id2) SELECT c1.id, c2.id FROM citizens c1, citizens c2 "
                            "WHERE c1.import_id = ? AND c1.citizen_id = ? AND c2.import_id = ? AND c2.citizen_id = ?;",
                            (import_id, citizen['citizen_id'], import_id, relative))
                worked_relatives.add(citizen['citizen_id'])
        except Exception as e:
            conn.rollback()
            raise e
        else:
            conn.commit()
            return import_id
        finally:
            cursor.close()
            conn.close()
