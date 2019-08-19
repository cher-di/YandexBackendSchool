import logging
import os
from pathlib import Path
from flask import Flask, request, Response, json
from db_processing import DBHelper
from datetime import date, datetime

app = Flask(__name__)
db_helper = DBHelper(user="ybs_rest_user",
                     password="123456qwerty",
                     host="127.0.0.1",
                     port="5432",
                     database="ybs_rest_db")

# logging
logs_dir_path = str(Path(__file__).parent.parent.absolute()) + '/logs/'
if not os.path.exists(logs_dir_path):
    os.mkdir(logs_dir_path)
logging.basicConfig(filename=logs_dir_path + date.today().strftime("%Y-%m-%d") + '.log',
                    level=logging.INFO)


@app.route('/imports', methods=['POST'])
def import_data():
    import_id = db_helper.import_citizens(request.json)
    if import_id is None:
        return Response(status=400)
    else:
        return Response(response=json.dumps({"data": {"import_id": import_id}}),
                        status=201,
                        mimetype='application/json')


@app.route('/imports/<int:import_id>/citizens/<int:citizen_id>', methods=['PATCH'])
def change_citizen_data(import_id, citizen_id):
    citizen_data = db_helper.change_citizen_data(import_id, citizen_id, request.json)
    if citizen_data is None:
        return Response(status=400)
    else:
        return Response(response=json.dumps({"data": citizen_data}),
                        status=200,
                        mimetype='application/json')


@app.route('/imports/<int:import_id>/citizens', methods=['GET'])
def get_citizens_data(import_id):
    citizens = db_helper.get_imported_citizens(import_id)
    if citizens is None:
        return Response(status=400)
    else:
        return Response(response=json.dumps({"data": citizens}),
                        status=200,
                        mimetype='application/json')


@app.route('/imports/<int:import_id>/citizens/birthdays', methods=['GET'])
def get_presents_num_per_month(import_id):
    presents_num_per_month = db_helper.get_presents_num_per_month(import_id)
    if presents_num_per_month is None:
        return Response(status=400)
    else:
        return Response(response=json.dumps({'data': presents_num_per_month}),
                        status=200,
                        mimetype='application/json')


@app.route('/imports/<int:import_id>/towns/stat/percentile/age', methods=['GET'])
def get_town_stat(import_id):
    town_stat = db_helper.get_town_stat(import_id)
    if town_stat is None:
        return Response(status=400)
    else:
        return Response(response=json.dumps({'data': town_stat}),
                        status=200,
                        mimetype='application/json')


@app.after_request
def save_logs(response):
    formatted_time = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    values_for_logging = tuple(map(str, (formatted_time, request.path, response.status_code)))
    logging.info("*".join(values_for_logging))
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
