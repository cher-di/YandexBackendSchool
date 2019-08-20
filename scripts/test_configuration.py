import psycopg2
import os
import config


def test_ini_file():
    return os.path.exists(config.CONFIG_FILE_PATH)


def test_db_connection(**kwargs) -> bool:
    try:
        conn = psycopg2.connect(**kwargs)
    except psycopg2.Error:
        return False
    else:
        return True
    finally:
        conn.close()


def test_logs_dir_path(logs_dir_path: str) -> bool:
    return os.path.exists(logs_dir_path)


if __name__ == '__main__':
    if not test_ini_file():
        print("Config file not generated\nExecute config.py to generate config file")
    else:
        print("Found config file: {}\n".format(config.CONFIG_FILE_PATH))

        if test_db_connection(**config.get_db_requisites()):
            print("Database connection success")
        else:
            print("Failed to connect to database")
        print("Requisites:")
        for key, value in config.get_db_requisites().items():
            print("{}: {}".format(key, value))
        print()

        if test_logs_dir_path(config.get_logs_dir_path()):
            print("Found path for logs dir:", config.get_logs_dir_path())
        else:
            print("Failed to find path for logs dir:", config.get_logs_dir_path())
