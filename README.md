# YandexBackendSchool  
Приложение на **Python** с **REST** архитектурой для Школы Бэкенд Разработки Яндекса

## Запуск сервера на машине с Ubuntu/Debian
1.Устанавливаем следующие пакеты:
   - Python (3.5+)  
   - PostgreSQL (9.6+)  
   - Git  
   - libpq-dev  
   - postgresql-server-dev-all
   
2.После этого потребуется склонировать репозиторий на машину и создать виртуальное окружение Python
```bash
foo@bar:~$ mkdir ybs
foo@bar:~$ cd ybs/
foo@bar:~$ sudo pip3 install virtualenv
foo@bar:~/ybs$ python3 -m venv ybs_venv
foo@bar:~/ybs$ git clone https_url
```
> Активировать виртуальное окружение Python: 
>```bash
>foo@bar~/ybs$ source ybs_venv/bin/activate
>```
> Декативировать виртуальное окружение Python:
>```bash
>foo@bar:~/ybs$ deacivate 
>```

3.Устанавливаем в виртуальное окружение следующие Python пакеты:
    - psycopg2
    - fastjsonschema
    - flask
    - numpy
    - gunicorn
```bash
(ybs_venv) foo@bar:~$ pip3 install psycopg2 fastjsonschema flask numpy gunicorn
```

4.Создаем базу данных `ybs_rest_db` и пользователя `ybs_rest_user`
```bash
foo@bar:~$ sudo -u postgres psql postgres
```
```postgresql
CREATE ROLE ybs_user LOGIN PASSWORD 'ybs_password' CREATEDB;
CREATE DATABASE ybs_db WITH owner = ybs_user;
```

5.Активируем виртуальное окружение и переходим в папку `scripts/`, после чего генерируем config.ini:
```bash
(ybs_venv) foo@bar:~/ybs/YandexBackendSchool/scripts$ python3 config.py
(ybs_venv) foo@bar:~/ybs/YandexBackendSchoolscripts$ gunicorn --bind=0.0.0.0:8080 server:app
```
> Сервер сам создаст таблицы для баз данных и папку для файлов логов

## Запуск *.sql файлов в терминале
Чтобы запустить `*.sql` файлы в терминале, необходимо открыть терминал в папке `sql_files/` и ввести следующую команду 
```console 
foo@bar:~$ psql -h localhost -d ybs_rest_db -U ybs_rest_user -p 5432 -a -q -f sql_file.sql
```
> Для создания таблиц необходимо использовать соотвественно: `create_tables.sql`  
> Для полной очистки базы данных (удаление всех данных и таблиц): `clear_databse.sql`  

За дополнительной информацией по поводу запуска `*.sql` файлов через терминал обратитесь на [сайт](https://www.postgresql.org/).