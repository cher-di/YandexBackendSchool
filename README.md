# YandexBackendSchool  
Приложение на **Python** с **REST** архитектурой для Школы Бэкенд Разработки Яндекса

## Запуск сервера на машине с Ubuntu/Debian
1. Устанавливаем следующие пакеты:
    - Python (3.5+)
    - PostgreSQL (9.6+)
    - Git

2. После этого потребуется склонировать репозиторий на машину и создать виртуальное окружение Python
```console
foo@bar:~$ mkdir ybs_rest_app
foo@bar:~$ cd ybs_rest_app/
foo@bar:~/ybs_rest_app$ 
```
3. Устанавливаем в виртуальное окружение следующие Python пакеты:
    - psycopg2
    - fastjsonschema
    - flask
    - numpy
    - gunicorn
4. Создаем базу данных `ybs_rest_db` и пользователя `ybs_rest_user`
5. Активируем виртуальное окружение, переходим в папку `scripts/` и запускаем *gunicorn*:
```console
foo@bar:~$ gunicorn --bind=0.0.0.0:8080 server:app
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