from flask import Flask, request, Response, json
from db_processing import DBHelper
from sqlite3 import DatabaseError

app = Flask(__name__)


class JSONResponse(Response):
    default_mimetype = 'application/json'


@app.route('/imports', methods=['POST'])
def import_data():
    try:
        citizens = request.json["citizens"]
        import_id = app.config['DBHelper'].import_citizens(citizens)
    except KeyError as e:
        return JSONResponse(response=json.dumps("{}: {}".format(e.__class__.__name__, e)),
                            status=400)
    except ValueError as e:
        return JSONResponse(response=json.dumps("{}: {}".format(e.__class__.__name__, e)),
                            status=400)
    except DatabaseError as e:
        return JSONResponse(response=json.dumps("{}: {}".format(e.__class__.__name__, e)),
                            status=400)
    else:
        return JSONResponse(response=json.dumps({"data": {"import_id": import_id}}),
                            status=201)


@app.route('/imports/<int:import_id>/citizens/<int:citizen_id>', methods=['PATCH'])
def change_citizen_data(import_id, citizen_id):
    pass


@app.route('/imports/<int:import_id>/citizens', methods=['GET'])
def get_citizens_data(import_id):
    pass


@app.route('/imports/<int:import_id>/citizens/birthdays', methods=['GET'])
def get_citizens_and_presents_num(import_id):
    pass


@app.route('/imports/<int:import_id>/towns/stat/percentile/age', methods=['GET'])
def get_town_stat(import_id):
    pass


@app.before_request
def check_request_mimetype():
    if request.mimetype != 'application/json':
        return JSONResponse(response=json.dumps("Not 'application/json' mimetype"),
                            status=400)


@app.before_first_request
def init_db_helper():
    app.config['DBHelper'] = DBHelper()


if __name__ == '__main__':
    app.run()
