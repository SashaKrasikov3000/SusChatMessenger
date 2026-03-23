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
    MessageNotFound = {"code": 404, "msg": "Message not found in database"}
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
            if rows_num is None:
                return SqlResponse(True, [dict(i) for i in self.cursor.fetchall()])
            elif rows_num == 1:
                try:
                    return SqlResponse(True, dict(self.cursor.fetchone()))
                except TypeError:
                    return SqlResponse(True, None)
            else:
                return SqlResponse(True, [dict(i) for i in self.cursor.fetchmany(rows_num)])
        return SqlResponse(True)

    def get_all_users(self) -> SqlResponse:
        return self.sql_query("SELECT * FROM users")

    def get_user_by_id(self, user_id) -> SqlResponse:
        return self.sql_query(f"SELECT * FROM users WHERE user_id={user_id}", rows_num=1)

    def add_user(self, data) -> SqlResponse:
        params = params_for_insert_query(data)
        return self.sql_query(f"INSERT INTO users {params}")

    def update_user(self, data) -> SqlResponse:
        user_id = data.pop("user_id")
        params = params_for_update_query(data)
        return self.sql_query(f"UPDATE users SET {params} WHERE user_id={user_id}")

    def update_user_last_seen(self, user_id):
        self.sql_query(f"UPDATE users SET last_seen=CURRENT_TIMESTAMP WHERE user_id={user_id}")

    def delete_user(self, user_id) -> SqlResponse:
        return self.sql_query(f"DELETE FROM users WHERE user_id={user_id}")


    def get_messages_from_chat(self, user_id, chat_id, max_num) -> SqlResponse:
        self.update_user_last_seen(user_id)
        return self.sql_query(f"SELECT * FROM ("
                              f" SELECT * FROM messages WHERE chat_id={chat_id} ORDER BY msg_id DESC LIMIT {max_num}"
                              f") ORDER BY msg_id ASC")

    def check_message_exists(self, msg_id):
        return self.sql_query(f"SELECT * FROM messages WHERE msg_id={msg_id}")

    def add_message(self, data) -> SqlResponse:
        params = params_for_insert_query(data)
        return self.sql_query(f"INSERT INTO messages {params}")

    def update_message(self, data) -> SqlResponse:
        msg_id = data.pop("msg_id")
        params = params_for_update_query(data)
        return self.sql_query(f"UPDATE messages SET {params} WHERE msg_id={msg_id}")

    def delete_message(self, msg_id) -> SqlResponse:
        return self.sql_query(f"DELETE FROM messages WHERE msg_id={msg_id}")


def make_response(response):
    """Generate response code using ResponseCode values"""
    return {"code": response["code"], "msg": response["msg"]}

def request_has_fields(request: dict, fields: list[str]):
    """Check if request data has all necessary fields"""
    for field in fields:
        if field not in request:
            return False
    return True
def request_only_has_fields(request: dict, fields: list[str]):
    """Check if request data has ONLY specified fields"""
    return list(request.keys()) == fields


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
def api_users():
    # Handling JSON errors
    try:
        request_data = request.get_json()
    except werkzeug.exceptions.BadRequest:
        return make_response(ResponseCode.BadRequest)

    if request.method == "GET":
        if not request_has_fields(request_data, ["user_id"]):
            return make_response(ResponseCode.BadRequest)
        user_id = request_data["user_id"]
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
        if not request_has_fields(request_data, ["user_id"]):
            return make_response(ResponseCode.BadRequest)
        db_response = db_manager.update_user(request_data)
        if db_response.success:
            return make_response(ResponseCode.OK)
        return make_response(ResponseCode.SqlError)

    if request.method == "DELETE":
        if not request_only_has_fields(request_data, ["user_id"]):
            return make_response(ResponseCode.BadRequest)
        user_id = request_data["user_id"]
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


# Messages managing: GET = get messages for chat, POST = send new message, PUT = update message, DELETE = delete message
@app.route("/api/msg", methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_messages():
    # Handling JSON errors
    try:
        request_data = request.get_json()
    except werkzeug.exceptions.BadRequest:
        return make_response(ResponseCode.BadRequest)

    if request.method == "GET":
        if not request_has_fields(request_data, ["user_id", "chat_id", "max_messages"]):
            return make_response(ResponseCode.BadRequest)
        user_id = request_data["user_id"]
        chat_id = request_data["chat_id"]
        max_messages = request_data["max_messages"]
        db_response = db_manager.get_messages_from_chat(user_id, chat_id, max_messages)
        if not db_response.success:
            return make_response(ResponseCode.SqlError)
        if not db_response.data:
            return make_response(ResponseCode.MessageNotFound)
        return jsonify(db_response.data)

    if request.method == "POST":
        if not request_only_has_fields(request_data, ["chat_id", "from_id", "content"]):
            return make_response(ResponseCode.BadRequest)
        db_response = db_manager.add_message(request_data)
        if db_response.success:
            return make_response(ResponseCode.OK)
        return make_response(ResponseCode.SqlError)

    if request.method == "PUT":
        if not request_only_has_fields(request_data, ["msg_id", "content"]):
            return make_response(ResponseCode.BadRequest)
        db_response = db_manager.update_message(request_data)
        if db_response.success:
            return make_response(ResponseCode.OK)
        return make_response(ResponseCode.SqlError)

    if request.method == "DELETE":
        if not request_only_has_fields(request_data, ["msg_id"]):
            return make_response(ResponseCode.BadRequest)
        msg_id = request_data["msg_id"]
        # Checking if message exists
        db_response = db_manager.check_message_exists(msg_id)
        if not db_response.success:
            return make_response(ResponseCode.SqlError)
        if not db_response.data:
            return make_response(ResponseCode.MessageNotFound)

        db_response = db_manager.delete_message(msg_id)
        if db_response.success:
            return make_response(ResponseCode.OK)
        return make_response(ResponseCode.SqlError)


db_manager = DatabaseManager()  # singleton db manager object
app.run(debug=True)