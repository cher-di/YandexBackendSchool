from flask import Flask, request

app = Flask(__name__)


@app.route('/imports', methods=['POST'])
def import_data():
    pass


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
def open_db_connection():
    print("Before request")


@app.teardown_appcontext
def close_db_connection(*args):
    print("After request")


if __name__ == '__main__':
    from db_processing import DBHelper
    app.config['DATABASE'] = DBHelper()
    print(app.config['DATABASE'].DB_PATH)
    app.run()
