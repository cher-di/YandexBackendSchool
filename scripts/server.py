from flask import Flask, request, Response, json
from db_processing import DBHelper
from sqlite3 import DatabaseError

app = Flask(__name__)
db_helper: DBHelper


@app.route('/imports', methods=['POST'])
def import_data():
    try:
        citizens = request.json["citizens"]
        import_id = db_helper.import_citizens(citizens)
    except TypeError as e:
        return Response(response="{}: {}".format(e.__class__.__name__, e), status=400)
    except KeyError as e:
        return Response(response="{}: {}".format(e.__class__.__name__, e), status=400)
    except ValueError as e:
        return Response(response="{}: {}".format(e.__class__.__name__, e), status=400)
    except DatabaseError as e:
        return Response(response="{}: {}".format(e.__class__.__name__, e), status=400)
    else:
        return Response(response=json.dumps({"data": {"import_id": import_id}}),
                        status=201,
                        mimetype='application/json')


@app.route('/imports/<int:import_id>/citizens/<int:citizen_id>', methods=['PATCH'])
def change_citizen_data(import_id, citizen_id):
    pass


@app.route('/imports/<int:import_id>/citizens', methods=['GET'])
def get_citizens_data(import_id):
    try:
        citizens = db_helper.get_imported_citizens(import_id)
    except ValueError:
        return Response(response="Unknown import_id", status=400)
    else:
        return Response(response=json.dumps({"data": citizens}),
                        status=200,
                        mimetype='application/json')


@app.route('/imports/<int:import_id>/citizens/birthdays', methods=['GET'])
def get_citizens_and_presents_num(import_id):
    pass


@app.route('/imports/<int:import_id>/towns/stat/percentile/age', methods=['GET'])
def get_town_stat(import_id):
    pass


if __name__ == '__main__':
    db_helper = DBHelper()
    app.run()
