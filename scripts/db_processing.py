import sqlite3
import datetime
from collections import defaultdict
from numpy import percentile
from jsonschema import validate, ValidationError
import psycopg2


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class DBHelper(metaclass=Singleton):
    CITIZEN_SCHEMA = {"citizen_id": "number",
                      "town": "string",
                      "street": "string",
                      "building": "string",
                      "apartment": "number",
                      "name": "string",
                      "birth_date": "string",
                      "gender": "string",
                      "relatives": "array"}
    GENDER = {'male', 'female'}
    DB_ACCOUNT = {"user": "ybs_rest_user",
                  "password": "123456qwerty",
                  "host": "127.0.0.1",
                  "port": "5432",
                  "database": "ybs_rest_db"}

    def __init__(self):
        try:
            conn = psycopg2.connect(**self.DB_ACCOUNT)
            cursor = conn.cursor()
            cursor.execute("""
                        CREATE TABLE IF NOT EXISTS imports(
                            import_id SERIAL PRIMARY KEY,
                            import_time TIMESTAMP NOT NULL
                        );
    
                        CREATE TABLE IF NOT EXISTS citizens(
                            id SERIAL,
                            import_id INT NOT NULL,
                            citizen_id INT NOT NULL,
                            town VARCHAR(70) NOT NULL,
                            street VARCHAR(70) NOT NULL,
                            building VARCHAR(20) NOT NULL,
                            apartment INT NOT NULL,
                            name VARCHAR(50) NOT NULL,
                            birth_date DATE NOT NULL,
                            gender VARCHAR(6) NOT NULL CHECK(gender IN ('male', 'female')),
                            CONSTRAINT citizens_pk PRIMARY KEY (id),
                            CONSTRAINT citizens_fk FOREIGN KEY (import_id) REFERENCES imports(import_id),
                            CONSTRAINT citizens_uk UNIQUE (import_id, citizen_id)
                        );
    
                        CREATE TABLE IF NOT EXISTS relatives(
                            id1 INT NOT NULL,
                            id2 INT NOT NULL,
                            CONSTRAINT relatives_fk_id1 FOREIGN KEY (id1) REFERENCES citizens(id),
                            CONSTRAINT relatives_fk_id2 FOREIGN KEY (id2) REFERENCES citizens(id),
                            CONSTRAINT relatives_uk UNIQUE (id1, id2)
                        );
    
                        CREATE UNIQUE INDEX IF NOT EXISTS citizens_idx ON citizens (import_id, citizen_id);
                        CREATE INDEX IF NOT EXISTS relatives_idx_1 ON relatives (id1);
                        CREATE INDEX IF NOT EXISTS relatives_idx_2 ON relatives (id2);
                        """)
            cursor.close()
            conn.commit()
            conn.close()
        except psycopg2.Error:
            raise Exception("Failed to connect to database")

    @staticmethod
    def json_date_to_postrgesql_date(date: str) -> str:
        return datetime.datetime.strptime(date, "%d.%m.%Y").strftime("%Y-%m-%d")

    @staticmethod
    def postgresql_date_to_json_date(date: str) -> str:
        return datetime.datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y")

    @staticmethod
    def validate_json_date_format(date: str) -> bool:
        # validate birth_date dd.mm.yyyy
        try:
            datetime.datetime.strptime(date, "%d.%m.%Y")
        except ValueError:
            return False
        else:
            return True

    @classmethod
    def validate_citizen_json_schema(cls, citizen: dict) -> bool:
        # validate citizen json schema
        try:
            validate(instance=citizen, schema=cls.CITIZEN_SCHEMA)
        except ValidationError:
            return False
        else:
            return True

    def validate_import_id(self, import_id: int) -> bool:
        # validate if import_id exists
        conn = psycopg2.connect(self.DB_ACCOUNT)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM imports WHERE import_id = %s;", (import_id,))
        try:
            cursor.fetchone()
        except psycopg2.ProgrammingError:
            return False
        else:
            return True

    def validate_citizen_id(self, import_id: int, citizen_id: int) -> bool:
        # validate if citizen_id with import_id exists
        conn = psycopg2.connect(self.DB_ACCOUNT)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM citizens WHERE import_id = %s AND citizen_id = %s;", (import_id, citizen_id))
        try:
            cursor.fetchone()
        except psycopg2.ProgrammingError:
            return False
        else:
            return True

    @staticmethod
    def verify_citizen_data_types(citizen_data: dict) -> bool:
        integer_keys = ('import_id', 'citizen_id', 'apartment')
        string_keys = ('town', 'street', 'building', 'name', 'birth_date', 'gender')
        list_tuple_keys = ('relatives',)

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

        for key in list_tuple_keys:
            try:
                if not (isinstance(citizen_data[key], list) or isinstance(citizen_data[key], tuple)):
                    return False
            except KeyError:
                pass

        return True

    def import_citizens(self, citizens: list) -> None:
        # check citizen json schema and date format
        for citizen in citizens:
            if not (self.validate_citizen_json_schema(citizen) and
                    self.validate_json_date_format(citizen['birth_date'])):
                return None

        # check relatives
        relatives_ids = {citizen['citizen_id']: citizen['relatives'] for citizen in citizens}
        for citizen_id, citizen_relatives_ids in relatives_ids.items():
            for relative_id in citizen_relatives_ids:
                if citizen_id not in relatives_ids[relative_id]:
                    return None

        try:
            # INSERT INTO imports
            conn = psycopg2.connect(self.DB_ACCOUNT)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO imports (import_time) VALUES (%s) RETURNING import_id;",
                           (datetime.datetime.now().isoformat(' ', 'milliseconds'),))
            import_id = cursor.fetchone()[0]

            # INSERT INTO citizens
            for citizen in citizens:
                citizen['import_id'] = import_id
                citizen['birth_date'] = self.json_date_to_postrgesql_date(citizen['birth_date'])
                cursor.execute(
                    "INSERT INTO citizens (import_id, citizen_id, town, street, building, apartment, name, birth_date, gender)"
                    "VALUES (%(import_id)s, %(citizen_id)s, %(town)s, %(street)s, %(building)s, %(apartment)s, %(name)s, %(birth_date)s, %(gender)s);",
                    citizen)

            # INSERT INTO relatives
            worked_relatives = set()
            for citizen_id, citizen_relative_id in relatives_ids:
                for relative_id in citizen_relatives_ids:
                    if relative_id not in worked_relatives:
                        cursor.execute(
                            "INSERT INTO relatives (id1, id2) SELECT c1.id, c2.id FROM citizens c1, citizens c2 "
                            "WHERE c1.import_id = %(import_id)s AND c1.citizen_id = %(citizen_id)s AND "
                            "c2.import_id = %(import_id)s AND c2.citizen_id = %(relative_id)s;",
                            ({'import_id': import_id,
                              'citizen_id': citizen_id,
                              'relative_id': relative_id}))
                worked_relatives.add(citizen_id)
        except (psycopg2.DatabaseError, psycopg2.Warning) as e:
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
                       "FROM citizens WHERE import_id = %s;", (import_id,))
        citizens_data = cursor.fetchall()
        if not citizens_data:
            raise ValueError
        else:
            keys = ('id', 'citizen_id', 'town', 'street', 'building', 'apartment', 'name', 'birth_date', 'gender')
            citizens = [dict(zip(keys, values)) for values in citizens_data]
            for citizen in citizens:
                citizen['birth_date'] = self.postgresql_date_to_json_date(citizen['birth_date'])
                cursor.execute("SELECT c.citizen_id FROM citizens c, relatives r "
                               "WHERE r.id1 = :id AND r.id2 = c.id OR r.id1 = c.id AND r.id2 = :id",
                               {'id': citizen['id']})
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
            patch_citizen_data['birth_date'] = self.json_date_to_postrgesql_date(patch_citizen_data['birth_date'])
        except KeyError:
            pass

        try:
            new_relatives = patch_citizen_data.pop('relatives')
        except KeyError:
            new_relatives = None

        try:
            conn = sqlite3.connect(self.DB_PATH)
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM citizens WHERE import_id = %s AND citizen_id = %s;", (import_id, citizen_id))
            try:
                citizen_db_id = cursor.fetchone()[0]
            except TypeError:
                raise ValueError

            for key, value in patch_citizen_data.items():
                cursor.execute("UPDATE citizens SET {}=%s WHERE id = %s;".format(key), (value, citizen_db_id))

            if new_relatives is not None:
                cursor.execute("SELECT c.id FROM citizens c, relatives r "
                               "WHERE r.id1 = :id AND r.id2 = c.id OR r.id1 = c.id AND r.id2 = :id;",
                               {'id': citizen_db_id})
                old_relatives_db_id = [relative[0] for relative in cursor.fetchall()]

                new_relatives_db_id = list()
                for relative in new_relatives:
                    cursor.execute("SELECT id FROM citizens WHERE import_id = %s AND citizen_id = %s;",
                                   (import_id, relative))
                    new_relatives_db_id.append(cursor.fetchone()[0])

                # delete old deleted relative
                for relative_db_id in set(old_relatives_db_id) - (set(new_relatives_db_id) & set(old_relatives_db_id)):
                    cursor.execute("DELETE FROM relatives WHERE id1 = :citizen_db_id AND id2 = :relative_db_id OR "
                                   "id1 = :relative_db_id AND id2 = :citizen_db_id;",
                                   {'citizen_db_id': citizen_db_id, 'relative_db_id': relative_db_id})

                # add new added relatives
                for relative_db_id in set(new_relatives_db_id) - (set(new_relatives_db_id) & set(old_relatives_db_id)):
                    cursor.execute("INSERT INTO relatives VALUES (%s, %s);", (citizen_db_id, relative_db_id))

        except Exception as e:
            conn.rollback()
            raise e
        else:
            conn.commit()
            cursor.execute("SELECT citizen_id, town, street, building, apartment, name, birth_date, gender "
                           "FROM citizens WHERE id = %s;", (citizen_db_id,))
            keys = ('citizen_id', 'town', 'street', 'building', 'apartment', 'name', 'birth_date', 'gender')
            citizen_data = dict(zip(keys, cursor.fetchone()))
            citizen_data['birth_date'] = self.postgresql_date_to_json_date(citizen_data['birth_date'])
            cursor.execute("SELECT c.citizen_id FROM citizens c, relatives r "
                           "WHERE r.id1 = :id AND r.id2 = c.id OR r.id1 = c.id AND r.id2 = :id;",
                           {'id': citizen_db_id})
            citizen_data['relatives'] = [relative[0] for relative in cursor.fetchall()]
            return citizen_data
        finally:
            cursor.close()
            conn.close()

    def get_presents_num_per_month(self, import_id: int) -> dict:
        if not self.verify_import_id(import_id):
            raise ValueError

        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, citizen_id, birth_date FROM citizens WHERE import_id = %s;", (import_id,))
        citizens = {citizen_data[0]: {'citizen_id': citizen_data[1], 'birth_date': citizen_data[2]}
                    for citizen_data in cursor.fetchall()}
        presents_num_per_month = {month: defaultdict(lambda: 0) for month in range(1, 13)}
        for citizen_db_id in citizens.keys():
            cursor.execute("SELECT id1 FROM relatives WHERE id2 = :id "
                           "UNION "
                           "SELECT id2 FROM relatives WHERE id1 = :id;", {"id": citizen_db_id})
            relatives_db_id = [relative_db_id[0] for relative_db_id in cursor.fetchall()]
            for relative_db_id in relatives_db_id:
                relative_birth_date = datetime.datetime.strptime(citizens[relative_db_id]['birth_date'], "%Y-%m-%d")
                presents_num_per_month[relative_birth_date.month][citizens[citizen_db_id]['citizen_id']] += 1
        cursor.close()
        conn.close()

        presents_num_per_month_result = dict()
        for month in presents_num_per_month.keys():
            presents_num_per_month_result[str(month)] = [{'citizen_id': citizen_id,
                                                          'presents': presents_num_per_month[month][citizen_id]}
                                                         for citizen_id in presents_num_per_month[month].keys()]
        return presents_num_per_month_result

    @staticmethod
    def calculate_age(born: str) -> int:
        born = datetime.datetime.strptime(born, "%Y-%m-%d").date()
        today = datetime.date.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    def get_town_stat(self, import_id: int) -> list:
        if not self.verify_import_id(import_id):
            raise ValueError

        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT town FROM citizens WHERE import_id = %s;", (import_id,))
        towns = [town[0] for town in cursor.fetchall()]
        percentiles = (50, 75, 99)
        town_stat = list()
        for town in towns:
            cursor.execute("SELECT birth_date FROM citizens WHERE import_id = %s AND town = %s;", (import_id, town))
            ages = [self.calculate_age(birth_date[0]) for birth_date in cursor.fetchall()]
            age_percentiles = [int(age_percentile) + 1 for age_percentile in percentile(ages, percentiles)]
            keys = ["town"] + ["p" + str(count_percentile) for count_percentile in percentiles]
            values = [town] + age_percentiles
            town_stat.append(dict(zip(keys, values)))
        cursor.close()
        conn.close()

        return town_stat
