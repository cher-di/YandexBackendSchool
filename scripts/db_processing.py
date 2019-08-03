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
                CONSTRAINT citizens_fk FOREIGN KEY (import_id) REFERENCES imports(import_id),
                CONSTRAINT citizens_uk UNIQUE (import_id, citizen_id)
            );
                
            CREATE TABLE  relatives(
                id1 INTEGER NOT NULL,
                id2 INTEGER NOT NULL,
                CONSTRAINT relatives_fk_id1 FOREIGN KEY (id1) REFERENCES citizens(id),
                CONSTRAINT relatives_fk_id2 FOREIGN KEY (id2) REFERENCES citizens(id)
            );
            
            CREATE UNIQUE INDEX citizens_idx ON citizens (import_id, citizen_id);
            CREATE INDEX relatives_idx_1 ON relatives (id1);
            CREATE INDEX relatives_idx_2 ON relatives (id2);
            """)
            cursor.close()
            conn.commit()
            conn.close()

        self._conn: sqlite3.Connection
        self._conn = None

    def verify_citizen_data_types(self, citizen_data: dict) -> bool:
        integer_keys = ('import_id', 'citizen_id', 'apartment')
        string_keys = ('town', 'street', 'building', 'name', 'birth_date', 'gender')

        for key in integer_keys:
            try:
                if not isinstance(citizen_data[key], int):
                    return False
            except KeyError:
                pass

        for key in string_keys:
            try:
                if not isinstance(citizen_data[key], str):
                    return False
            except KeyError:
                pass

        return True

    def import_citizens(self, citizens: list) -> int:
        # check relatives
        relatives_ids = dict()
        for citizen in citizens:
            relatives_ids[citizen['citizen_id']] = citizen['relatives']
        for citizen_id, citizen_relatives_ids in relatives_ids.items():
            for relative_id in citizen_relatives_ids:
                if citizen_id not in relatives_ids[relative_id] or citizen_id == relative_id:
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
                citizen['import_id'] = import_id
                citizen['birth_date'] = datetime.datetime.strptime(citizen['birth_date'], "%d.%m.%Y").strftime(
                    "%Y-%m-%d")
                if not self.verify_citizen_data_types(citizen):
                    raise TypeError
                cursor.execute(
                    "INSERT INTO citizens (import_id, citizen_id, town, street, building, apartment, name, birth_date, gender)"
                    "VALUES (:import_id, :citizen_id, :town, :street, :building, :apartment, :name, :birth_date, :gender);",
                    citizen)

            # INSERT relatives
            worked_relatives = set()
            for citizen in citizens:
                for relative_id in citizen['relatives']:
                    if relative_id not in worked_relatives:
                        cursor.execute(
                            "INSERT INTO relatives (id1, id2) SELECT c1.id, c2.id FROM citizens c1, citizens c2 "
                            "WHERE c1.import_id = ? AND c1.citizen_id = ? AND c2.import_id = ? AND c2.citizen_id = ?;",
                            (import_id, citizen['citizen_id'], import_id, relative_id))
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

    def get_imported_citizens(self, import_id: int) -> list:
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT id, citizen_id, town, street, building, apartment, name, birth_date, gender "
                       "FROM citizens WHERE import_id = ?;", (import_id,))
        citizens_data = cursor.fetchall()
        if not citizens_data:
            raise ValueError
        else:
            keys = ('id', 'citizen_id', 'town', 'street', 'building', 'apartment', 'name', 'birth_date', 'gender')
            citizens = [dict(zip(keys, values)) for values in citizens_data]
            for citizen in citizens:
                citizen['birth_date'] = datetime.datetime.strptime(citizen['birth_date'], "%Y-%m-%d").strftime(
                    "%d.%m.%Y")
                cursor.execute("SELECT c.citizen_id FROM citizens c, relatives r "
                               "WHERE r.id1 = :id AND r.id2 = c.id "
                               "UNION "
                               "SELECT c.citizen_id FROM citizens c, relatives r "
                               "WHERE r.id1 = c.id AND r.id2 = :id;", {'id': citizen['id']})
                citizen['relatives'] = [relative[0] for relative in cursor.fetchall()]
                citizen.pop('id')
        return citizens

    def change_citizen_data(self, import_id: int, citizen_id: int, patch_citizen_data: dict) -> dict:
        template_citizen_data_keys = {'citizen_id', 'town', 'street', 'building', 'apartment', 'name', 'birth_date',
                                      'gender', 'relatives'}
        patch_citizen_data_keys = set(patch_citizen_data.keys())
        if not patch_citizen_data_keys <= template_citizen_data_keys or 'citizen_id' in patch_citizen_data_keys:
            raise KeyError

        if not self.verify_citizen_data_types(patch_citizen_data):
            raise TypeError

        try:
            patch_citizen_data['birth_date'] = datetime.datetime.strptime(
                patch_citizen_data['birth_date'], "%d.%m.%Y").strftime("%Y-%m-%d")
        except KeyError:
            pass

        try:
            new_relatives = patch_citizen_data.pop('relatives')
        except KeyError:
            new_relatives = None

        try:
            conn = sqlite3.connect(self.DB_PATH)
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM citizens WHERE import_id = ? AND citizen_id = ?;", (import_id, citizen_id))
            try:
                citizen_db_id = cursor.fetchone()[0]
            except TypeError:
                raise ValueError

            for key, value in patch_citizen_data.items():
                cursor.execute("UPDATE citizens SET {}=? WHERE id = ?;".format(key), (value, citizen_db_id))

            if new_relatives is not None:
                if citizen_id in new_relatives:
                    raise ValueError

                cursor.execute("SELECT c.id FROM citizens c, relatives r "
                               "WHERE r.id1 = :id AND r.id2 = c.id OR r.id1 = c.id AND r.id2 = :id;",
                               {'id': citizen_db_id})
                old_relatives_db_id = [relative[0] for relative in cursor.fetchall()]

                new_relatives_db_id = list()
                for relative in new_relatives:
                    cursor.execute("SELECT id FROM citizens WHERE import_id = ? AND citizen_id = ?;",
                                   (import_id, relative))
                    new_relatives_db_id.append(cursor.fetchone()[0])

                # delete old deleted relative
                for relative_db_id in set(old_relatives_db_id) - (set(new_relatives_db_id) & set(old_relatives_db_id)):
                    cursor.execute("DELETE FROM relatives WHERE id1 = :citizen_db_id AND id2 = :relative_db_id OR "
                                   "id1 = :relative_db_id AND id2 = :citizen_db_id;",
                                   {'citizen_db_id': citizen_db_id, 'relative_db_id': relative_db_id})

                # add new added relatives
                for relative_db_id in set(new_relatives_db_id) - (set(new_relatives_db_id) & set(old_relatives_db_id)):
                    cursor.execute("INSERT INTO relatives VALUES (?, ?);", (citizen_db_id, relative_db_id))

        except Exception as e:
            conn.rollback()
            raise e
        else:
            conn.commit()
            cursor.execute("SELECT citizen_id, town, street, building, apartment, name, birth_date, gender "
                           "FROM citizens WHERE id = ?;", (citizen_db_id, ))
            keys = ('citizen_id', 'town', 'street', 'building', 'apartment', 'name', 'birth_date', 'gender')
            citizen_data = dict(zip(keys, cursor.fetchone()))
            citizen_data['birth_date'] = datetime.datetime.strptime(citizen_data['birth_date'], "%Y-%m-%d").strftime(
                "%d.%m.%Y")
            cursor.execute("SELECT c.citizen_id FROM citizens c, relatives r "
                           "WHERE r.id1 = :id AND r.id2 = c.id OR r.id1 = c.id AND r.id2 = :id;",
                           {'id': citizen_db_id})
            citizen_data['relatives'] = [relative[0] for relative in cursor.fetchall()]
            return citizen_data
        finally:
            cursor.close()
            conn.close()
