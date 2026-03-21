import werkzeug.exceptions
from flask import Flask, request, jsonify
import sqlite3 as sqlt

app = Flask("SusChat")

class SqlResponse:
    """DatabaseManager.sql_query() returns this"""
    def __init__(self, success, data=None):
        self.success = success
        self.data = data

class ResponseCode:
    """Response code values for passing to make_response()"""
    OK = {"code": 200, "msg": "OK"}
    UserNotFound = {"code": 404, "msg": "User not found in database"}
    BadRequest = {"code": 400, "msg": "Incorrect request form"}
    SqlError = {"code": 500, "msg": "Error while processing SQL request"}
    InternalError = {"code": 500, "msg": "Server error"}


class DatabaseManager:
    """Database manager object. Contains common CRUD operation for database."""
    def __init__(self):
        self.con = sqlt.connect("database.db", check_same_thread=False)
        self.con.row_factory = sqlt.Row
        self.cursor = self.con.cursor()

    def __del__(self):
        self.con.close()

    def sql_query(self, query, rows_num=None) -> SqlResponse:
        """Make sql query to database. Return SqlResponse object"""
        try:
            self.cursor.execute(query)
            self.con.commit()
        except Exception as e:
            # TODO: add error logging
            print("Sql Error: ", e)
            return SqlResponse(False)

        if "SELECT" in query:
            # Returning data as JSON depending on number of rows required
            if rows_num == 1:
                try:
                    return SqlResponse(True, dict(self.cursor.fetchone()))
                except TypeError:
                    return SqlResponse(True, None)
            elif rows_num > 1:
                return SqlResponse(True, [dict(i) for i in self.cursor.fetchmany(rows_num)])
            else:
                return SqlResponse(True, [dict(i) for i in self.cursor.fetchall()])
        return SqlResponse(True)

    def get_all_users(self) -> SqlResponse:
        return self.sql_query("SELECT * FROM users")

    def get_user_by_id(self, user_id) -> SqlResponse:
        return self.sql_query(f"SELECT * FROM users WHERE id={user_id}", rows_num=1)

    def add_user(self, data) -> SqlResponse:
        params = params_for_insert_query(data)
        return self.sql_query(f"INSERT INTO users {params}")

    def update_user(self, data) -> SqlResponse:
        user_id = data.pop("id")
        params = params_for_update_query(data)
        return self.sql_query(f"UPDATE users SET {params} WHERE id={user_id}")

    def delete_user(self, user_id) -> SqlResponse:
        return self.sql_query(f"DELETE FROM users WHERE id={user_id}")


def make_response(response):
    """Generate response code using ResponseCode values"""
    return {"code": response["code"], "msg": response["msg"]}


def params_for_update_query(data):
    """Generate parameters string for UPDATE SQL query as following: param1='str1', param2=num2"""
    params = ""
    for key, val in zip(data.keys(), data.values()):
        if isinstance(val, int):
            params += f"{key}={val}, "
        else:
            params += f"{key}='{val}', "
    return params[:-2]

def params_for_insert_query(data):
    """Generate parameters string for INSERT SQL query as following: (param1, param2) VALUES ('str1', num2)"""
    vals = []
    for val in data.values():
        if isinstance(val, int):
            vals.append(str(val))
        else:
            vals.append(f"'{val}'")
    return f"({', '.join(data.keys())}) VALUES ({', '.join(vals)})"

@app.route('/')
def home_page():
    # TODO: add home page
    return "<h1>Home page</h1>"


# Api entry point, RESTful architecture

# User managing: GET = get user data, POST = add new user, PUT = update user info, DELETE = delete user
@app.route("/api/user", methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_main():
    # Handling JSON errors
    try:
        request_data = request.get_json()
    except werkzeug.exceptions.BadRequest:
        return make_response(ResponseCode.BadRequest)

    if request.method == "GET":
        if "id" not in request_data:
            return make_response(ResponseCode.BadRequest)
        user_id = request_data["id"]
        db_response = db_manager.get_user_by_id(user_id)
        if not db_response.success:
            return make_response(ResponseCode.SqlError)
        if not db_response.data:
            return make_response(ResponseCode.UserNotFound)
        return jsonify(db_response.data)

    if request.method == "POST":
        db_response = db_manager.add_user(request_data)
        if db_response.success:
            return make_response(ResponseCode.OK)
        return make_response(ResponseCode.SqlError)

    if request.method == "PUT":
        if "id" not in request_data:
            return make_response(ResponseCode.BadRequest)
        db_response = db_manager.update_user(request_data)
        if db_response.success:
            return make_response(ResponseCode.OK)
        return make_response(ResponseCode.SqlError)

    if request.method == "DELETE":
        if "id" not in request_data:
            return make_response(ResponseCode.BadRequest)
        user_id = request_data["id"]
        # Checking if user exists
        db_response = db_manager.get_user_by_id(user_id)
        if not db_response.success:
            return make_response(ResponseCode.SqlError)
        if not db_response.data:
            return make_response(ResponseCode.UserNotFound)

        db_response = db_manager.delete_user(user_id)
        if db_response.success:
            return make_response(ResponseCode.OK)
        return make_response(ResponseCode.SqlError)


db_manager = DatabaseManager()  # singleton db manager object
app.run(debug=True)