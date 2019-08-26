import os
import psycopg2
from configparser import ConfigParser
from pathlib import Path
from argparse import ArgumentParser

CONFIG_FILE_PATH = str(Path(__file__).absolute().parent.parent) + '/config.ini'


def make_config_file():
    config = ConfigParser()
    config.add_section('main')

    config['main']['user'] = 'null'
    config['main']['password'] = 'null'
    config['main']['host'] = '127.0.0.1'
    config['main']['port'] = '5432'
    config['main']['database'] = 'null'
    config['main']['logs_dir_path'] = 'null'

    with open(CONFIG_FILE_PATH, 'w') as config_file:
        config.write(config_file)


def get_config() -> dict:
    config = ConfigParser()
    config.read(CONFIG_FILE_PATH)
    config_dict = dict(config['main'].items())
    config_dict['port'] = int(config_dict['port'])
    return config_dict


def get_db_requisites() -> dict:
    config_dict = get_config()
    keys = ('user', 'password', 'host', 'port', 'database')
    config_dict = {key: config_dict[key] for key in keys}
    return config_dict


def get_logs_dir_path() -> str:
    config_dict = get_config()
    return config_dict['logs_dir_path']


def test_ini_file():
    return os.path.exists(CONFIG_FILE_PATH)


def test_db_connection(**kwargs) -> bool:
    try:
        with psycopg2.connect(**kwargs):
            pass
    except psycopg2.Error:
        return False
    else:
        return True


def test_logs_dir_path(logs_dir_path: str) -> bool:
    return os.path.exists(logs_dir_path)


def test_config():
    printing_template = "{:30}{}"

    if not test_ini_file():
        print(printing_template.format("Found config file", "FAIL"))
    else:
        print(printing_template.format("Found config file", "OK"))

        if test_db_connection(**get_db_requisites()):
            print(printing_template.format("Test database connection", "OK"))
        else:
            print(printing_template.format("Test database connection", "FAIL"))

        if test_logs_dir_path(get_logs_dir_path()):
            print(printing_template.format("Found path for logs dir", "OK"))
        else:
            print(printing_template.format("Found path for logs dir", "FAIL"))


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('mode', help="mode of script: c - create config.ini, t - test config.ini", type=str)
    args = parser.parse_args()

    if args.mode == 'c':
        make_config_file()
    elif args.mode == 't':
        test_config()
    else:
        print("Unknown mode: {}".format(args.mode))
