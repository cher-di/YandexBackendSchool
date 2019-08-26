import config
from flask import Flask, request, Response, json
from database import DBHelper, DBHelperError
from datetime import date, datetime

app = Flask(__name__)
db_helper = DBHelper(**config.get_db_requisites())
logs_dir_path = config.get_logs_dir_path()


@app.route('/imports', methods=['POST'])
def import_data():
    try:
        import_id = db_helper.import_citizens(request.json)
    except DBHelperError as e:
        return Response(response=str(e), status=400)
    else:
        return Response(response=json.dumps({"data": {"import_id": import_id}}),
                        status=201,
                        mimetype='application/json')


@app.route('/imports/<int:import_id>/citizens/<int:citizen_id>', methods=['PATCH'])
def change_citizen_data(import_id, citizen_id):
    try:
        citizen_data = db_helper.change_citizen(import_id, citizen_id, request.json)
    except DBHelperError as e:
        return Response(response=str(e), status=400)
    else:
        return Response(response=json.dumps({"data": citizen_data}),
                        status=200,
                        mimetype='application/json')


@app.route('/imports/<int:import_id>/citizens', methods=['GET'])
def get_citizens_data(import_id):
    try:
        citizens = db_helper.get_citizens(import_id)
    except DBHelperError as e:
        return Response(response=str(e), status=400)
    else:
        return Response(response=json.dumps({"data": citizens}),
                        status=200,
                        mimetype='application/json')


@app.route('/imports/<int:import_id>/citizens/birthdays', methods=['GET'])
def get_presents_num_per_month(import_id):
    try:
        presents_num_per_month = db_helper.get_presents_num_per_month(import_id)
    except DBHelperError as e:
        return Response(response=str(e), status=400)
    else:
        return Response(response=json.dumps({'data': presents_num_per_month}),
                        status=200,
                        mimetype='application/json')


@app.route('/imports/<int:import_id>/towns/stat/percentile/age', methods=['GET'])
def get_town_stat(import_id):
    try:
        town_stat = db_helper.get_town_stat(import_id)
    except DBHelperError as e:
        return Response(response=str(e), status=400)
    else:
        return Response(response=json.dumps({'data': town_stat}),
                        status=200,
                        mimetype='application/json')


@app.after_request
def save_logs(response):
    formatted_time = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    values_for_logging = tuple(map(str, (formatted_time, request.path, response.status_code)))
    with open(logs_dir_path + date.today().strftime("%Y-%m-%d") + '.log', 'a') as log_file:
        log_file.write("*".join(values_for_logging) + '\n')
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
