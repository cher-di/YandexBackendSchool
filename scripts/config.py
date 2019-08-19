from configparser import ConfigParser
from pathlib import Path


CONFIG_FILE_PATH = str(Path(__file__).absolute().parent.parent) + '/config.ini'


def make_config_file() -> None:
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


def get_db_config() -> dict:
    config_dict = get_config()
    keys = ('user', 'password', 'host', 'port', 'database')
    config_dict = {key: config_dict[key] for key in keys}
    return config_dict


def get_logs_dir_path_config() -> dict:
    config_dict = get_config()
    return config_dict['logs_dir_path']


if __name__ == '__main__':
    make_config_file()
