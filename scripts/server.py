from flask import Flask, request, Response, json
from db_processing import DBHelper

app = Flask(__name__)
db_helper: DBHelper


@app.route('/imports', methods=['POST'])
def import_data():
    import_id = db_helper.import_citizens(request.json['citizens'])
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
    if citizens in None:
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


if __name__ == '__main__':
    db_helper = DBHelper()
    app.run()
