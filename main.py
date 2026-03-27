import random
import string
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
    UserUnauthorized = {"code": 401, "msg": "User is not authorized"}
    ForbiddenError = {"code": 403, "msg": "Forbidden action"}
    SqlError = {"code": 500, "msg": "Error while processing SQL request"}
    InternalError = {"code": 500, "msg": "Server error"}


class DatabaseManager:
    """Database manager object. Contains common CRUD operations for database."""
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

    def auth_user(self, session_id, user_id) -> SqlResponse:
        """Add user's session to database"""
        return self.sql_query(f"INSERT INTO sessions (session_id, user_id) VALUES ('{session_id}', {user_id})")

    def check_user_session(self, session_id) -> SqlResponse:
        """Check if session exists"""
        return self.sql_query(f"SELECT user_id FROM sessions WHERE session_id='{session_id}'", rows_num=1)

    def delete_user_session(self, user_id):
        """Delete all sessions from user"""
        return self.sql_query(f"DELETE FROM sessions WHERE user_id={user_id}")

    def get_all_users(self) -> SqlResponse:
        return self.sql_query("SELECT * FROM users")

    def get_user_data(self, user_id) -> SqlResponse:
        """Get ALL user data (including sensitive)"""
        return self.sql_query(f"SELECT * FROM users WHERE user_id={user_id}", rows_num=1)

    def get_user_public_data(self, user_id) -> SqlResponse:
        """Get only public user data"""
        return self.sql_query(f"SELECT name, last_seen FROM users WHERE user_id={user_id}", rows_num=1)

    def add_user(self, name, password) -> SqlResponse:
        """Add user to database"""
        return self.sql_query(f"INSERT INTO users (name, password) VALUES ('{name}', '{password}')")

    def update_user(self, user_id, name, password) -> SqlResponse:
        """Change user data in database"""
        return self.sql_query(f"UPDATE users SET name='{name}', password='{password}' WHERE user_id={user_id}")

    def update_user_last_seen(self, user_id):
        self.sql_query(f"UPDATE users SET last_seen=CURRENT_TIMESTAMP WHERE user_id={user_id}")

    def delete_user(self, user_id) -> SqlResponse:
        """Delete user from database"""
        return self.sql_query(f"DELETE FROM users WHERE user_id={user_id}")


    def get_messages_from_chat(self, user_id, chat_id, max_num) -> SqlResponse:
        """Get last messages from given chat"""
        self.update_user_last_seen(user_id)
        return self.sql_query(f"SELECT * FROM ("
                              f" SELECT * FROM messages WHERE chat_id={chat_id} ORDER BY msg_id DESC LIMIT {max_num}"
                              f") ORDER BY msg_id ASC")

    def check_message_exists(self, msg_id):
        """Check if message exists in database"""
        return self.sql_query(f"SELECT * FROM messages WHERE msg_id={msg_id}")

    def add_message(self, user_id, chat_id, msg_content) -> SqlResponse:
        """Add message to database"""
        return self.sql_query(f"INSERT INTO messages (chat_id, from_id, content) VALUES ({chat_id}, {user_id}, '{msg_content}')")

    def update_message(self, msg_id, msg_content) -> SqlResponse:
        """Change message data in database"""
        return self.sql_query(f"UPDATE messages SET content='{msg_content}' WHERE msg_id={msg_id}")

    def delete_message(self, msg_id) -> SqlResponse:
        """Delete message from database"""
        return self.sql_query(f"DELETE FROM messages WHERE msg_id={msg_id}")

    def get_user_chats(self, user_id) -> SqlResponse:
        """Get list of user's chats"""
        pass

    def get_chat_data(self, chat_id) -> SqlResponse:
        """Get chat data"""
        pass

    def add_user_to_chat(self, user_id, chat_id):
        """Add user to chat"""
        # Add chat to user's chats; add user to chat's users
        pass


def make_response(response):
    """Generate response code using ResponseCode values"""
    return jsonify({"code": response["code"], "msg": response["msg"]})

def request_has_fields(request_data: dict, fields: list[str]):
    """Check if request data has all necessary fields"""
    for field in fields:
        if field not in request_data:
            return False
    return True
def request_only_has_fields(request_data: dict, fields: list[str]):
    """Check if request data has ONLY specified fields"""
    return list(request_data.keys()) == fields

def generate_random_string(length=20):
    """Generating random sequence of letters and digits"""
    alph = string.ascii_letters + string.digits
    result = "".join([random.choice(alph) for _ in range(length)])
    return result


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

@app.route("/api/login", methods=['GET'])
def api_login():
    # Handling JSON errors
    try:
        request_data = request.get_json()
    except werkzeug.exceptions.BadRequest:
        return make_response(ResponseCode.BadRequest)

    if not request_has_fields(request_data, ["user_id", "password"]):
        return make_response(ResponseCode.BadRequest)
    user_id = request_data["user_id"]
    password = request_data["password"]

    # check if password is correct
    db_response = db_manager.get_user_data(user_id)
    if not db_response.success:
        return make_response(ResponseCode.SqlError)
    if not db_response.data:
        return make_response(ResponseCode.UserNotFound)
    if db_response.data["password"] != password:
        return make_response(ResponseCode.ForbiddenError)

    session_id = generate_random_string()
    db_response = db_manager.auth_user(session_id, user_id)
    if db_response.success:
        return jsonify({"session_id": session_id})
    return make_response(ResponseCode.SqlError)


# User managing: GET = get user data, POST = add new user, PUT = update user info, DELETE = delete user
@app.route("/api/user", methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_users():
    # Handling JSON errors
    try:
        request_data = request.get_json()
    except werkzeug.exceptions.BadRequest:
        return make_response(ResponseCode.BadRequest)

    # Creating user doesn't require auth
    if request.method == "POST":
        user_name = request_data["name"]
        password = request_data["password"]
        db_response = db_manager.add_user(user_name, password)
        if db_response.success:
            return make_response(ResponseCode.OK)
        return make_response(ResponseCode.SqlError)

    # Getting another user's public data by ID doesn't require auth as well
    if request.method == "GET":
        if request_has_fields(request_data, ["user_id"]):
            user_id = request_data["user_id"]
            db_response = db_manager.get_user_public_data(user_id)
            if not db_response.success:
                return make_response(ResponseCode.SqlError)
            if not db_response.data:
                return make_response(ResponseCode.UserNotFound)
            return jsonify(db_response.data)

    # Checking user auth
    if not request_has_fields(request_data, ["session_id"]):
        return make_response(ResponseCode.BadRequest)
    session_id = request_data["session_id"]
    db_response = db_manager.check_user_session(session_id)
    if not db_response.success:
        return make_response(ResponseCode.SqlError)
    if not db_response.data:
        return make_response(ResponseCode.UserUnauthorized)
    user_id = db_response.data["user_id"]

    # If session provided, getting current user data
    if request.method == "GET":
        db_response = db_manager.get_user_data(user_id)
        if not db_response.success:
            return make_response(ResponseCode.SqlError)
        if not db_response.data:
            return make_response(ResponseCode.UserNotFound)
        return jsonify(db_response.data)

    if request.method == "PUT":
        user_name = request_data["name"]
        password = request_data["password"]
        db_response = db_manager.update_user(user_id, user_name, password)
        if db_response.success:
            return make_response(ResponseCode.OK)
        return make_response(ResponseCode.SqlError)

    if request.method == "DELETE":
        # Checking if user exists
        db_response = db_manager.get_user_data(user_id)
        if not db_response.success:
            return make_response(ResponseCode.SqlError)
        if not db_response.data:
            return make_response(ResponseCode.UserNotFound)

        db_response = db_manager.delete_user(user_id)
        if not db_response.success:
            return make_response(ResponseCode.SqlError)
        db_response = db_manager.delete_user_session(user_id)
        if not db_response.success:
            return make_response(ResponseCode.SqlError)
        return make_response(ResponseCode.OK)


# Messages managing: GET = get messages for chat, POST = send new message, PUT = update message, DELETE = delete message
@app.route("/api/msg", methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_messages():
    # Handling JSON errors
    try:
        request_data = request.get_json()
    except werkzeug.exceptions.BadRequest:
        return make_response(ResponseCode.BadRequest)

    # Checking user auth
    if not request_has_fields(request_data, ["session_id"]):
        return make_response(ResponseCode.BadRequest)
    session_id = request_data["session_id"]
    db_response = db_manager.check_user_session(session_id)
    if not db_response.success:
        return make_response(ResponseCode.SqlError)
    if not db_response.data:
        return make_response(ResponseCode.UserUnauthorized)
    user_id = db_response.data["user_id"]

    if request.method == "GET":
        if not request_has_fields(request_data, ["chat_id", "max_messages"]):
            return make_response(ResponseCode.BadRequest)
        chat_id = request_data["chat_id"]
        max_messages = request_data["max_messages"]
        db_response = db_manager.get_messages_from_chat(user_id, chat_id, max_messages)
        if not db_response.success:
            return make_response(ResponseCode.SqlError)
        if not db_response.data:
            return make_response(ResponseCode.MessageNotFound)
        return jsonify(db_response.data)

    if request.method == "POST":
        if not request_has_fields(request_data, ["chat_id", "content"]):
            return make_response(ResponseCode.BadRequest)
        chat_id = request_data["chat_id"]
        msg_content = request_data["content"]
        db_response = db_manager.add_message(user_id, chat_id, msg_content)
        if db_response.success:
            return make_response(ResponseCode.OK)
        return make_response(ResponseCode.SqlError)

    if request.method == "PUT":
        if not request_has_fields(request_data, ["msg_id", "content"]):
            return make_response(ResponseCode.BadRequest)
        msg_id = request_data["msg_id"]
        msg_content = request_data["content"]
        db_response = db_manager.update_message(msg_id, msg_content)
        if db_response.success:
            return make_response(ResponseCode.OK)
        return make_response(ResponseCode.SqlError)

    if request.method == "DELETE":
        if not request_has_fields(request_data, ["msg_id"]):
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