# YandexBackendSchool  
Приложение на **Python** с **REST** архитектурой для Школы Бэкенд Разработки Яндекса

## Запуск сервера на машине с Ubuntu/Debian
1.Устанавливаем следующие пакеты:
   - Python (3.6+)  
   - PostgreSQL (9.6+)  
   - Git  
   - libpq-dev  
   - postgresql-server-dev-all
   
2.Клонируем репозиторий на машину
```console
user@machine:~$ mkdir YandexBackendSchool
user@machine:~$ cd YandexBackendSchool/
user@machine:~/YandexBackendSchool$ git clone https://github.com/cher-di/YandexBackendSchool.git
```

3.Создаем вирутальное окржение Python и устанавливаем в него все необходимые модули:
  - psycopg2
  - fastjsonschema
  - flask
  - numpy
  - gunicorn
```console
user@machine:~/YandexBackendSchool$ pip3 install virtualenv
user@machine:~/YandexBackendSchool$ python3 -m venv ybs_venv
user@machine:~/YandexBackendSchool$ source ybs_venv/bin/activate
(ybs_venv) user@machine:~/YandexBackendSchool$ pip3 install --upgrade pip setuptools
(ybs_venv) user@machine:~/YandexBackendSchool$ pip3 install psycopg2 fastjsonschema flask numpy gunicorn
```

4.Создаем базу пользователя и базу данных:
```console
user@machine:~$ sudo -u postgres psql postgres
```
```postgresql
CREATE ROLE ybs_user LOGIN PASSWORD 'ybs_password' CREATEDB;
CREATE DATABASE ybs_db WITH owner = ybs_user;
```

5.Чтобы сгенерировать файл конфигурации */home/user/YandexBackendSchool/YandexBackendSchool/config.ini*, запускаем скрипт *config.py* с режимом **g**:
```console
(ybs_venv) user@machine:~/YandexBackendSchool/YandexBackendSchool/scripts$ python3 config.py g
```
После того, как файл конфигурации будет сгенерирован, записываем в него верные значения вместо значений по умолчанию.

6.Проверяем конфигурацию - запускаем скрипт *config.py* c режимом **t**:
```console
(ybs_venv) user@machine:~/YandexBackendSchool/YandexBackendSchool/scripts$ python3 config.py t
```
Если результат исполнения скрипта выдал везде **OK**, то можно приступать к следующему шагу.  
В противном случае скрипт выдаст ошибку **FAIL**.

7.Тестируем сервер:
```console
(ybs_venv) user@machine:~/YandexBackendSchool/YandexBackendSchool/scripts$ gunicorn -c gunicorn_configuration.py server:app
```
Если все нормально, то переходим к следующему шагу.  
Не забываем отключить виртуальное окружение:
```console
(ybs_venv) user@machine:~/YandexBackendSchool/YandexBackendSchool/scripts$ deactivate
```
8.Создаем файл */etc/systemd/system/ybs.service*, для запуска демона нашего приложения:
```text
[Unit]
Description=Gunicorn instance to server YandexBackendSchoolApp
After=network.target
[Service]
User=dmitry
Group=www-data
WorkingDirectory=/home/user/YandexBackendSchool/YandexBackendSchool/scripts
Environment="PATH=/home/user/YandexBackendSchool/ybs_venv/bin"
ExecStart=/home/user/YandexBackendSchool/ybs_venv/bin/gunicorn -c gunicorn_config.py server:app
[Install]
WantedBy=multi-user.target
```
9.Запускаем демона и делаем его автозапускаемым при запуске машины
```console
user@machine:~$ sudo systemctl daemon-reload
user@machine:~$ sudo systemctl start ybs
user@machine:~$ sudo systemctl enable ybs
```
После этого сервер развернут и готов к работе

## Запуск *.sql файлов в терминале
Чтобы запустить *\*.sql* файлы в терминале, необходимо открыть терминал в папке *sql_files/* и ввести следующую команду 
```console 
user@machine:~$ psql -h localhost -d ybs_rest_db -U ybs_rest_user -p 5432 -a -q -f sql_file.sql
```
> Для создания таблиц необходимо использовать соотвественно: *create_tables.sql*  
> Для полной очистки базы данных (удаление всех данных и таблиц): *clear_databse.sql*  

За дополнительной информацией по поводу запуска *\*.sql* файлов через терминал обратитесь на [сайт](https://www.postgresql.org/).