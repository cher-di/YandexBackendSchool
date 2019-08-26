import datetime
import psycopg2
from collections import defaultdict
from numpy import percentile, array, ceil
from fastjsonschema import validate, compile, JsonSchemaException
from psycopg2 import extras
from pathlib import Path


class DBHelperError(Exception):
    def __str__(self):
        return "Error"


class DBHelperJsonSchemaError(DBHelperError):
    def __str__(self):
        return "Error when validating data"


class DBHelperIDError(DBHelperError):
    def __str__(self):
        return "Unknown import_id or citizen_id"


class DBHelperRelativesError(DBHelperError):
    def __str__(self):
        return "Error with relations"


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class DBHelper(metaclass=Singleton):
    IMPORT_CITIZEN_SCHEMA = {
        "type": "object",
        "properties": {
            "citizen_id": {"type": "number"},
            "town": {"type": "string"},
            "street": {"type": "string"},
            "building": {"type": "string"},
            "apartment": {"type": "number"},
            "name": {"type": "string"},
            "birth_date": {"type": "string"},
            "gender": {
                "type": "string",
                "enum": ["male", "female"]
            },
            "relatives": {
                "type": "array",
                "items": {"type": "number"},
            }
        },
        "additionalProperties": False,
        "required": ["citizen_id", "town", "street", "building", "apartment", "name", "birth_date", "gender",
                     "relatives"]
    }
    CHANGE_CITIZEN_SCHEMA = {
        "type": "object",
        "properties": {
            "town": {"type": "string"},
            "street": {"type": "string"},
            "building": {"type": "string"},
            "apartment": {"type": "number"},
            "name": {"type": "string"},
            "birth_date": {"type": "string"},
            "gender": {
                "type": "string",
                "enum": ["male", "female"]
            },
            "relatives": {
                "type": "array",
                "items": {"type": "number"},
            }
        },
        "additionalProperties": False,
        "minProperties": 1
    }
    IMPORT_SCHEMA = {
        "type": "object",
        "properties": {
            "citizens": {
                "type": "array",
                "items": IMPORT_CITIZEN_SCHEMA
            }
        },
        "required": ["citizens"],
        "additionalProperties": False
    }
    SQL_FILES_DIR = str(Path(__file__).parent.parent.absolute()) + '/sql_files/'
    CITIZENS_COLUMNS = tuple(['id', 'import_id'] +
                             list(filter(lambda x: x != 'relatives', IMPORT_CITIZEN_SCHEMA['properties'])))

    def __init__(self, **kwargs):
        self.DB_REQUISITES = kwargs

        with psycopg2.connect(**self.DB_REQUISITES) as conn:
            with conn.cursor() as cursor:
                with open(self.SQL_FILES_DIR + 'create_tables.sql', 'r') as create_tables_sql_file:
                    cursor.execute(create_tables_sql_file.read())

        self._compiled_import_schema_validator = compile(self.IMPORT_SCHEMA)

    @staticmethod
    def json_date_to_postrgesql_date(date: str) -> str:
        return datetime.datetime.strptime(date, "%d.%m.%Y").strftime("%Y-%m-%d")

    @staticmethod
    def postgresql_date_to_json_date(date: datetime.date) -> str:
        return date.strftime("%d.%m.%Y")

    @staticmethod
    def validate_json_birth_date_format(date: str) -> bool:
        try:
            datetime.datetime.strptime(date, "%d.%m.%Y")
        except ValueError:
            return False
        else:
            return True

    def import_exists(self, import_id: int) -> bool:
        # validate if import_id exists
        with psycopg2.connect(**self.DB_REQUISITES) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM imports WHERE import_id = %s;", (import_id,))
                result = cursor.fetchone()
        return result is not None

    def citizen_exists(self, import_id: int, citizen_id: int) -> bool:
        # validate if citizen_id with import_id exists
        with psycopg2.connect(**self.DB_REQUISITES) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM citizens WHERE import_id = %s AND citizen_id = %s;",
                               (import_id, citizen_id))
                result = cursor.fetchone()
        return result is not None

    def import_citizens(self, citizens: dict) -> int:
        # check citizens
        try:
            self._compiled_import_schema_validator(citizens)
        except JsonSchemaException:
            raise DBHelperJsonSchemaError

        citizens = citizens['citizens']

        # check birth_date
        for citizen in citizens:
            if not self.validate_json_birth_date_format(citizen['birth_date']):
                raise DBHelperJsonSchemaError

        # check relatives
        relatives_ids = {citizen['citizen_id']: citizen['relatives'] for citizen in citizens}
        for citizen_id, citizen_relatives_ids in relatives_ids.items():
            for relative_id in citizen_relatives_ids:
                if citizen_id not in relatives_ids[relative_id]:
                    raise DBHelperRelativesError

        with psycopg2.connect(**self.DB_REQUISITES) as conn:
            with conn.cursor() as cursor:
                try:
                    # INSERT INTO imports
                    cursor.execute("INSERT INTO imports (import_time) VALUES (%s) RETURNING import_id;",
                                   (datetime.datetime.now().isoformat(' ', 'milliseconds'),))
                    import_id = cursor.fetchone()[0]

                    # INSERT INTO citizens
                    for citizen in citizens:
                        citizen['import_id'] = import_id
                        citizen['birth_date'] = self.json_date_to_postrgesql_date(citizen['birth_date'])
                    columns = tuple(filter(lambda x: x != 'id', self.CITIZENS_COLUMNS))
                    extras.execute_values(cursor,
                                          "INSERT INTO citizens ({}) VALUES %s;".format(','.join(columns)),
                                          citizens,
                                          "({})".format(','.join(map(lambda x: "%({})s".format(x), columns))))

                    # INSERT INTO relatives
                    cursor.execute("SELECT id, citizen_id FROM citizens WHERE import_id = %s;", (import_id,))
                    query_result = array(cursor.fetchall())
                    citizen_id_to_citizen_db_id = dict(zip(query_result[:, 1].tolist(), query_result[:, 0].tolist()))

                    worked_relatives = set()
                    relatives_db_ids = []
                    for citizen_id, citizen_relatives_ids in relatives_ids.items():
                        for relative_id in citizen_relatives_ids:
                            if relative_id not in worked_relatives:
                                relatives_db_ids.append((citizen_id_to_citizen_db_id[citizen_id],
                                                         citizen_id_to_citizen_db_id[relative_id]))
                        worked_relatives.add(citizen_id)
                    extras.execute_values(cursor,
                                          "INSERT INTO relatives (id1, id2) VALUES %s;",
                                          relatives_db_ids,
                                          "(%s, %s)")
                except (psycopg2.DatabaseError, psycopg2.Warning) as e:
                    conn.rollback()
                    print(e)
                    raise DBHelperJsonSchemaError
                else:
                    conn.commit()
                    return import_id

    def get_citizens(self, import_id: int) -> list:
        # check import_id
        if not self.import_exists(import_id):
            raise DBHelperIDError

        with psycopg2.connect(**self.DB_REQUISITES) as conn:
            with conn.cursor() as cursor:
                columns = tuple(filter(lambda x: x != 'import_id', self.CITIZENS_COLUMNS))
                cursor.execute("SELECT {} "
                               "FROM citizens WHERE import_id = %s;".format(','.join(columns)), (import_id,))
                citizens = [dict(zip(columns, values)) for values in cursor.fetchall()]

                for citizen in citizens:
                    citizen['relatives'] = []
                    citizen['birth_date'] = self.postgresql_date_to_json_date(citizen['birth_date'])
                keys = [citizen.pop('id') for citizen in citizens]
                citizen_by_db_id = dict(zip(keys, citizens))

                cursor.execute(
                    "SELECT c.id, r.id1 FROM citizens c, relatives r "
                    "WHERE c.id = r.id2 AND c.import_id = %(import_id)s "
                    "UNION "
                    "SELECT c.id, r.id2 FROM citizens c, relatives r "
                    "WHERE c.id = r.id1 AND c.import_id = %(import_id)s AND r.id1 != r.id2;",
                    {"import_id": import_id})
                for pair in cursor.fetchall():
                    citizen_by_db_id[pair[0]]['relatives'].append(citizen_by_db_id[pair[1]]['citizen_id'])

        return citizens

    def get_citizen(self, import_id: int, citizen_id: int) -> dict:
        # check if citizen exists
        if not self.citizen_exists(import_id, citizen_id):
            raise DBHelperIDError

        with psycopg2.connect(**self.DB_REQUISITES) as conn:
            with conn.cursor() as cursor:
                columns = self.CITIZENS_COLUMNS
                cursor.execute("SELECT {} "
                               "FROM citizens WHERE import_id = %s AND citizen_id = %s;".format(','.join(columns)),
                               (import_id, citizen_id))
                citizen_data = dict(zip(columns, cursor.fetchone()))

                citizen_data['birth_date'] = self.postgresql_date_to_json_date(citizen_data['birth_date'])

                cursor.execute("SELECT c.citizen_id FROM citizens c, relatives r "
                               "WHERE r.id1 = %(id)s AND r.id2 = c.id OR r.id1 = c.id AND r.id2 = %(id)s;",
                               {'id': citizen_data.pop('id')})
                citizen_data['relatives'] = [relative[0] for relative in cursor.fetchall()]

        return citizen_data

    def change_relatives(self, import_id: int, citizen_id: int, new_relatives: list):
        # check if citizen is exists
        if not self.citizen_exists(import_id, citizen_id):
            raise DBHelperIDError

        # check if relatives are exist
        for relative_id in new_relatives:
            if not self.citizen_exists(import_id, relative_id):
                raise DBHelperRelativesError

        with psycopg2.connect(**self.DB_REQUISITES) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM citizens WHERE import_id = %s AND citizen_id = %s;",
                               (import_id, citizen_id))
                citizen_db_id = cursor.fetchone()

                cursor.execute("SELECT c.id FROM citizens c, relatives r "
                               "WHERE r.id1 = %(id)s AND r.id2 = c.id OR r.id1 = c.id AND r.id2 = %(id)s;",
                               {'id': citizen_db_id})
                try:
                    old_relatives_db_id = [relative[0] for relative in cursor.fetchall()]
                except psycopg2.ProgrammingError:
                    old_relatives_db_id = []

                if new_relatives:
                    cursor.execute("SELECT id FROM citizens WHERE import_id = %s AND citizen_id IN %s;",
                                   (import_id, tuple(new_relatives)))
                    new_relatives_db_id = [relative_db_id[0] for relative_db_id in cursor.fetchall()]
                else:
                    new_relatives_db_id = []

                # delete old relatives
                delete_relatives_db_ids = [{'citizen_db_id': citizen_db_id,
                                            'relative_db_id': relative_db_id}
                                           for relative_db_id in set(old_relatives_db_id) - (
                                                   set(new_relatives_db_id) & set(old_relatives_db_id))]
                if delete_relatives_db_ids:
                    extras.execute_batch(cursor,
                                         "DELETE FROM relatives WHERE "
                                         "id1 = %(citizen_db_id)s AND id2 = %(relative_db_id)s OR "
                                         "id1 = %(relative_db_id)s AND id2 = %(citizen_db_id)s;",
                                         delete_relatives_db_ids)

                # insert new relatives
                insert_relatives_db_ids = [{'citizen_db_id': citizen_db_id,
                                            'relative_db_id': relative_db_id}
                                           for relative_db_id in set(new_relatives_db_id) - (
                                                   set(new_relatives_db_id) & set(old_relatives_db_id))]
                if insert_relatives_db_ids:
                    extras.execute_values(cursor,
                                          "INSERT INTO relatives VALUES %s;",
                                          insert_relatives_db_ids,
                                          "(%(citizen_db_id)s, %(relative_db_id)s)")

            # commit changes
            conn.commit()

    def change_citizen(self, import_id: int, citizen_id: int, patch_citizen_data: dict) -> dict:
        # check if citizen exists
        if not self.citizen_exists(import_id, citizen_id):
            raise DBHelperIDError

        # check patch_citizen_data
        try:
            validate(self.CHANGE_CITIZEN_SCHEMA, patch_citizen_data)
        except JsonSchemaException:
            raise DBHelperJsonSchemaError

        # check if patch_citizen_data have field "citizen_id" or not
        if 'citizen_id' in patch_citizen_data.keys():
            raise DBHelperJsonSchemaError
        # NOTE временная заплата

        # get and change relatives, if patch_citizen_data contains relatives
        try:
            new_relatives = patch_citizen_data.pop('relatives')
        except KeyError:
            pass
        else:
            self.change_relatives(import_id, citizen_id, new_relatives)

        # check birth_date and change to postgresql format, if patch_citizen_data contains birth_date
        try:
            patch_citizen_data['birth_date'] = self.json_date_to_postrgesql_date(patch_citizen_data['birth_date'])
        except KeyError:
            pass
        # same as validate_birth_date
        except ValueError:
            raise DBHelperJsonSchemaError

        # if patch_citizen_data is not empty, change citizen data in database
        if patch_citizen_data:
            with psycopg2.connect(**self.DB_REQUISITES) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id FROM citizens WHERE import_id = %s AND citizen_id = %s;",
                                   (import_id, citizen_id))
                    citizen_db_id = cursor.fetchone()[0]

                    update_text = "UPDATE citizens SET " + \
                                  ",".join(map(lambda key: "{0}=%({0})s".format(key), patch_citizen_data.keys())) + \
                                  "WHERE id = %(id)s;"
                    cursor.execute(update_text, {**patch_citizen_data, **{"id": citizen_db_id}})
                conn.commit()

        return self.get_citizen(import_id, citizen_id)

    def get_presents_num_per_month(self, import_id: int) -> dict:
        if not self.import_exists(import_id):
            raise DBHelperIDError

        with psycopg2.connect(**self.DB_REQUISITES) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, citizen_id, birth_date FROM citizens WHERE import_id = %s;", (import_id,))
                citizens = {
                    citizen_data[0]: {'citizen_id': citizen_data[1], 'birth_date': citizen_data[2], 'relatives': []}
                    for citizen_data in cursor.fetchall()}

                cursor.execute(
                    "SELECT c.id, r.id1 FROM citizens c, relatives r "
                    "WHERE c.id = r.id2 AND c.import_id = %(import_id)s "
                    "UNION "
                    "SELECT c.id, r.id2 FROM citizens c, relatives r "
                    "WHERE c.id = r.id1 AND c.import_id = %(import_id)s AND r.id1 != r.id2;",
                    {"import_id": import_id})
                for pair in cursor.fetchall():
                    citizens[pair[0]]['relatives'].append(pair[1])

                presents_num_per_month = {month: defaultdict(lambda: 0) for month in range(1, 13)}
                for citizen_db_id, citizen in citizens.items():
                    for relative_db_id in citizen['relatives']:
                        relative_birth_date = citizens[relative_db_id]['birth_date']
                        presents_num_per_month[relative_birth_date.month][citizens[citizen_db_id]['citizen_id']] += 1

        presents_num_per_month_result = dict()
        for month in presents_num_per_month.keys():
            presents_num_per_month_result[str(month)] = [{'citizen_id': citizen_id,
                                                          'presents': presents_num_per_month[month][citizen_id]}
                                                         for citizen_id in presents_num_per_month[month].keys()]
        return presents_num_per_month_result

    @staticmethod
    def calculate_age(born: datetime.date) -> int:
        today = datetime.date.today()
        if (today.month, today.day) < (born.month, born.day):
            return today.year - born.year - 1
        else:
            return today.year - born.year

    def get_town_stat(self, import_id: int) -> list:
        if not self.import_exists(import_id):
            raise DBHelperIDError

        with psycopg2.connect(**self.DB_REQUISITES) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT DISTINCT town FROM citizens WHERE import_id = %s;", (import_id,))
                towns = [town[0] for town in cursor.fetchall()]
                percentiles = (50, 75, 99)
                town_stat = []
                for town in towns:
                    cursor.execute("SELECT birth_date FROM citizens WHERE import_id = %s AND town = %s;",
                                   (import_id, town))
                    ages = [self.calculate_age(birth_date[0]) for birth_date in cursor.fetchall()]
                    age_percentiles = ceil(percentile(ages, percentiles)).astype(int).tolist()
                    keys = ["town"] + list(map(lambda x: "p" + str(x), percentiles))
                    values = [town] + age_percentiles
                    town_stat.append(dict(zip(keys, values)))

        return town_stat
