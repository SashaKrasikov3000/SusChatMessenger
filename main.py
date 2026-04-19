import os
import random
import string
import werkzeug.exceptions
from flask import Flask, request, jsonify, send_file
import sqlite3 as sqlt

app = Flask("SusChat")

data_path = "/data/" if "AMVERA" in os.environ else "data/"
port = 8080 if "AMVERA" in os.environ else 5000

class SqlResponse:
    """DatabaseManager.sql_query() returns this"""
    def __init__(self, success, data=None):
        self.success = success
        self.data = data

class ResponseCode:
    """Response code values for passing to make_response()"""
    OK = {"code": 200, "msg": "OK"}
    UserNotFound = {"code": 404, "msg": "User not found in database"}
    ChatNotFound = {"code": 404, "msg": "Chat not found in database"}
    MessageNotFound = {"code": 404, "msg": "Message not found in database"}
    BadRequest = {"code": 400, "msg": "Incorrect request form"}
    UserUnauthorized = {"code": 401, "msg": "User is not authorized"}
    ForbiddenError = {"code": 403, "msg": "Forbidden action"}
    SqlError = {"code": 500, "msg": "Error while processing SQL request"}
    InternalError = {"code": 500, "msg": "Server error"}

class Request:
    """Request data object"""
    request_data = {}

    def __init__(self, request: Flask.request_class):
        self.request_data = request.get_json()

    def __getitem__(self, item):
        return self.request_data[item]

    def has_fields(self, fields: list[str]):
        """Check if request data has all necessary fields"""
        for field in fields:
            if field not in self.request_data:
                return False
        return True

    def has_field(self, field: str):
        """Check if request data has given field"""
        return field in self.request_data

    def is_auth(self) -> bool:
        """Check user auth (session_id)"""
        db_manager = DatabaseManager()
        # Checking user auth
        if "session_id" not in self.request_data:
            return False
        session_id = self.request_data["session_id"]
        db_response = db_manager.check_user_session(session_id)
        if not db_response.success or not db_response.data:
            return False
        # Adding user_id to request data
        if "user_id" not in self.request_data:
            user_id = db_response.data["user_id"]
            self.request_data["user_id"] = user_id
        return True

class DatabaseManager:
    """Database manager object. Contains common CRUD operations for database."""
    def __init__(self):
        database_path = data_path + "database.db"
        self.con = sqlt.connect(database_path, check_same_thread=False)
        self.con.row_factory = sqlt.Row
        self.cursor = self.con.cursor()

    def __del__(self):
        self.con.close()

    def sql_query(self, query, rows_num=None) -> SqlResponse:
        """Make sql query to database. Return SqlResponse object"""
        # TODO: remake method to use placeholders to avoid SQL injections
        try:
            print(query)
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
        return self.sql_query(f"INSERT INTO sessions (session_id, user_id) VALUES ('{session_id}', '{user_id}')")

    def check_user_session(self, session_id) -> SqlResponse:
        """Check if session exists"""
        return self.sql_query(f"SELECT user_id FROM sessions WHERE session_id='{session_id}'", rows_num=1)

    def delete_user_session(self, user_id):
        """Delete all sessions from user"""
        return self.sql_query(f"DELETE FROM sessions WHERE user_id='{user_id}'")

    def get_all_users(self) -> SqlResponse:
        return self.sql_query("SELECT * FROM users")

    def get_user_data(self, user_id) -> SqlResponse:
        """Get ALL user data (including sensitive)"""
        return self.sql_query(f"SELECT * FROM users WHERE user_id='{user_id}'", rows_num=1)

    def get_user_public_data(self, user_id) -> SqlResponse:
        """Get only public user data"""
        return self.sql_query(f"SELECT user_id, name, last_seen FROM users WHERE user_id='{user_id}'", rows_num=1)

    def create_user(self, user_id, name, password) -> SqlResponse:
        """Add user to database"""
        return self.sql_query(f"INSERT INTO users (user_id, name, password) VALUES ('{user_id}', '{name}', '{password}')")

    def update_user(self, user_id, name, password) -> SqlResponse:
        """Change user data in database"""
        return self.sql_query(f"UPDATE users SET name='{name}', password='{password}' WHERE user_id='{user_id}'")

    def update_user_last_seen(self, user_id):
        self.sql_query(f"UPDATE users SET last_seen=CURRENT_TIMESTAMP WHERE user_id='{user_id}'")

    def delete_user(self, user_id) -> SqlResponse:
        """Delete user from database"""
        return self.sql_query(f"DELETE FROM users WHERE user_id='{user_id}'")

    def get_messages_from_chat(self, user_id, chat_id, max_num) -> SqlResponse:
        """Get last messages from given chat"""
        self.update_user_last_seen(user_id)
        return self.sql_query(f"SELECT * FROM ("
                              f" SELECT * FROM messages WHERE chat_id='{chat_id}' ORDER BY msg_id DESC LIMIT {max_num}"
                              f") ORDER BY msg_id ASC")

    def get_message_data(self, msg_id) -> SqlResponse:
        """Check if message exists in database"""
        return self.sql_query(f"SELECT * FROM messages WHERE msg_id={msg_id}")

    def create_message(self, user_id, chat_id, msg_content) -> SqlResponse:
        """Add message to database"""
        return self.sql_query(f"INSERT INTO messages (chat_id, from_id, content) VALUES ('{chat_id}', '{user_id}', '{msg_content}')")

    def update_message(self, msg_id, msg_content) -> SqlResponse:
        """Change message data in database"""
        return self.sql_query(f"UPDATE messages SET content='{msg_content}' WHERE msg_id={msg_id}")

    def delete_message(self, msg_id) -> SqlResponse:
        """Delete message from database"""
        return self.sql_query(f"DELETE FROM messages WHERE msg_id={msg_id}")

    def get_chat_data(self, chat_id) -> SqlResponse:
        """Get chat data"""
        return self.sql_query(f"SELECT * FROM chats WHERE chat_id='{chat_id}'", rows_num=1)

    def create_chat(self, chat_id, chat_name, chat_description) -> SqlResponse:
        """Create new chat"""
        return self.sql_query(f"INSERT INTO chats (chat_id, name, description) VALUES ('{chat_id}', '{chat_name}', '{chat_description}')")

    def update_chat(self, chat_id, chat_name, chat_description) -> SqlResponse:
        """Change chat info"""
        return self.sql_query(f"UPDATE chats SET name='{chat_name}', description='{chat_description}' WHERE chat_id='{chat_id}'")

    def delete_chat(self, chat_id) -> SqlResponse:
        """Delete chat from database"""
        return self.sql_query(f"DELETE FROM chats WHERE chat_id='{chat_id}'")

    def get_user_chats(self, user_id):
        """Get list of user's chats"""
        return self.sql_query(f"SELECT chat_id FROM user_chat WHERE user_id='{user_id}'")

    def get_chat_users(self, chat_id):
        """Get list of users in chat"""
        return self.sql_query(f"SELECT user_id FROM user_chat WHERE chat_id='{chat_id}'")

    def add_user_to_chat(self, user_id, chat_id) -> SqlResponse:
        return self.sql_query(f"INSERT INTO user_chat (user_id, chat_id, role_id) VALUES ('{user_id}', '{chat_id}', 0)")

    def delete_user_from_chat(self, user_id, chat_id) -> SqlResponse:
        return self.sql_query(f"DELETE FROM user_chat WHERE user_id='{user_id}' AND chat_id='{chat_id}'")

    def delete_chat_from_all_users(self, chat_id) -> SqlResponse:
        """Delete chat from all users"""
        return self.sql_query(f"DELETE FROM user_chat WHERE chat_id='{chat_id}'")

    def delete_user_from_all_chats(self, user_id) -> SqlResponse:
        """Delete user from all chats"""
        return self.sql_query(f"DELETE FROM user_chat WHERE user_id='{user_id}'")

    def check_user_in_chat(self, user_id, chat_id) -> SqlResponse:
        """Check if user is in given chat"""
        return self.sql_query(f"SELECT * FROM user_chat WHERE user_id='{user_id}' AND chat_id='{chat_id}'")


def make_response(response):
    """Generate response code using ResponseCode values"""
    return jsonify({"code": response["code"], "msg": response["msg"]})

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
    return "<h1>Home page</h1>"

@app.route('/download/android')
def download_android():
    return send_file(data_path + "SusChat.apk", as_attachment=True)



@app.route('/api/version', methods=['GET'])
def api_version():
    return jsonify({"version": os.environ["APP_VERSION"], "description": os.environ["UPDATE_DESCRIPTION"]})

@app.route("/api/login", methods=['GET'])
def api_login():
    # Handling JSON errors
    try:
        request_data = Request(request)
    except werkzeug.exceptions.BadRequest:
        return make_response(ResponseCode.BadRequest)
    db_manager = DatabaseManager()

    if not request_data.has_fields(["user_id", "password"]):
        return make_response(ResponseCode.BadRequest)
    user_id = request_data["user_id"]
    password = request_data["password"]

    # Check if password is correct
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
        return jsonify({"code": 200, "session_id": session_id})
    return make_response(ResponseCode.SqlError)


# Add or delete user from chat
@app.route("/api/user-chat", methods=['GET', 'POST', 'DELETE'])
def add_user_to_chat():
    print(request.data)
    # Handling JSON errors
    try:
        request_data = Request(request)
    except werkzeug.exceptions.BadRequest:
        return make_response(ResponseCode.BadRequest)
    db_manager = DatabaseManager()

    # Check user auth, get user_id
    if not request_data.is_auth():
        return make_response(ResponseCode.UserUnauthorized)
    user_id = request_data["user_id"]

    # Getting list of chats or users
    if request.method == "GET":
        if request_data.has_field("chat_id"):
            # Getting list of all users in given chat
            chat_id = request_data["chat_id"]
            db_response = db_manager.get_chat_users(chat_id)
            if not db_response.success:
                return make_response(ResponseCode.SqlError)
            return jsonify(db_response.data)
        else:
            # Getting list of all chats for current user
            db_response = db_manager.get_user_chats(user_id)
            if not db_response.success:
                return make_response(ResponseCode.SqlError)
            return jsonify(db_response.data)

    if not request_data.has_field("chat_id"):
        return make_response(ResponseCode.BadRequest)
    chat_id = request_data["chat_id"]

    # Check whether user is in chat
    db_response = db_manager.check_user_in_chat(user_id, chat_id)
    if not db_response.success:
        return make_response(ResponseCode.SqlError)
    user_in_chat = bool(db_response.data)

    if request.method == "POST":
        # Check if user already in chat
        if user_in_chat:
            return make_response(ResponseCode.ForbiddenError)

        # Check if chat exists
        db_response = db_manager.get_chat_data(chat_id)
        if not db_response.success:
            return make_response(ResponseCode.SqlError)
        if not db_response.data:
            return make_response(ResponseCode.ChatNotFound)

        db_response = db_manager.add_user_to_chat(user_id, chat_id)
        if db_response.success:
            return make_response(ResponseCode.OK)
        return make_response(ResponseCode.SqlError)

    if request.method == "DELETE":
        # Check if user not in chat
        if not user_in_chat:
            return make_response(ResponseCode.ForbiddenError)

        db_response = db_manager.delete_user_from_chat(user_id, chat_id)
        if db_response.success:
            return make_response(ResponseCode.OK)
        return make_response(ResponseCode.SqlError)


# User managing: GET = get user data, POST = add new user, PUT = update user info, DELETE = delete user
@app.route("/api/user", methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_users():
    print(request.data)
    # Handling JSON errors
    try:
        request_data = Request(request)
    except werkzeug.exceptions.BadRequest:
        return make_response(ResponseCode.BadRequest)
    db_manager = DatabaseManager()

    # Creating user doesn't require auth
    if request.method == "POST":
        if not request_data.has_fields(["name", "password"]):
            return make_response(ResponseCode.BadRequest)
        user_name = request_data["name"]
        password = request_data["password"]
        user_id = generate_random_string(7)
        db_response = db_manager.create_user(user_id, user_name, password)
        if db_response.success:
            return jsonify({"code": 200, "user_id": user_id})
        return make_response(ResponseCode.SqlError)

    # Getting another user's public data by ID doesn't require auth as well
    if request.method == "GET":
        if request_data.has_field("user_id"):
            user_id = request_data["user_id"]
            db_response = db_manager.get_user_public_data(user_id)
            if not db_response.success:
                return make_response(ResponseCode.SqlError)
            if not db_response.data:
                return make_response(ResponseCode.UserNotFound)
            return jsonify(db_response.data)

    # Check user auth, get user_id
    if not request_data.is_auth():
        return make_response(ResponseCode.UserUnauthorized)
    user_id = request_data["user_id"]

    # If session provided, getting current user data
    if request.method == "GET":
        db_response = db_manager.get_user_data(user_id)
        if not db_response.success:
            return make_response(ResponseCode.SqlError)
        if not db_response.data:
            return make_response(ResponseCode.UserNotFound)
        return jsonify(db_response.data)

    if request.method == "PUT":
        if not request_data.has_fields(["name", "password"]):
            return make_response(ResponseCode.BadRequest)
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

        # Deleting user, sessions and chats
        db_response = db_manager.delete_user(user_id)
        if not db_response.success:
            return make_response(ResponseCode.SqlError)
        db_response = db_manager.delete_user_session(user_id)
        if not db_response.success:
            return make_response(ResponseCode.SqlError)
        db_response = db_manager.delete_user_from_all_chats(user_id)
        if not db_response.success:
            return make_response(ResponseCode.SqlError)
        return make_response(ResponseCode.OK)


# Messages managing: GET = get messages for chat, POST = send new message, PUT = update message, DELETE = delete message
@app.route("/api/msg", methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_messages():
    print(request.data)
    # Handling JSON errors
    try:
        request_data = Request(request)
    except werkzeug.exceptions.BadRequest:
        return make_response(ResponseCode.BadRequest)
    db_manager = DatabaseManager()

    # Check user auth, get user_id
    if not request_data.is_auth():
        return make_response(ResponseCode.UserUnauthorized)
    user_id = request_data["user_id"]

    if request.method == "GET":
        if not request_data.has_fields(["chat_id", "max_messages"]):
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
        if not request_data.has_fields(["chat_id", "content"]):
            return make_response(ResponseCode.BadRequest)
        chat_id = request_data["chat_id"]
        msg_content = request_data["content"]
        db_response = db_manager.create_message(user_id, chat_id, msg_content)
        if db_response.success:
            return make_response(ResponseCode.OK)
        return make_response(ResponseCode.SqlError)

    if request.method == "PUT":
        if not request_data.has_fields(["msg_id", "content"]):
            return make_response(ResponseCode.BadRequest)
        msg_id = request_data["msg_id"]
        msg_content = request_data["content"]
        db_response = db_manager.update_message(msg_id, msg_content)
        if db_response.success:
            return make_response(ResponseCode.OK)
        return make_response(ResponseCode.SqlError)

    if request.method == "DELETE":
        if not request_data.has_field("msg_id"):
            return make_response(ResponseCode.BadRequest)
        msg_id = request_data["msg_id"]
        # Checking if message exists
        db_response = db_manager.get_message_data(msg_id)
        if not db_response.success:
            return make_response(ResponseCode.SqlError)
        if not db_response.data:
            return make_response(ResponseCode.MessageNotFound)

        db_response = db_manager.delete_message(msg_id)
        if db_response.success:
            return make_response(ResponseCode.OK)
        return make_response(ResponseCode.SqlError)

# Chat managing: GET = get chat info, POST = create new chat, PUT = update chat info, DELETE = delete chat
@app.route("/api/chat", methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_chats():
    print(request.data)
    # Handling JSON errors
    try:
        request_data = Request(request)
    except werkzeug.exceptions.BadRequest:
        return make_response(ResponseCode.BadRequest)
    db_manager = DatabaseManager()

    # Check user auth, get user_id
    if not request_data.is_auth():
        return make_response(ResponseCode.UserUnauthorized)
    user_id = request_data["user_id"]

    if request.method == "GET":
        if not request_data.has_field("chat_id"):
            return make_response(ResponseCode.BadRequest)
        chat_id = request_data["chat_id"]
        db_response = db_manager.get_chat_data(chat_id)
        if not db_response.success:
            return make_response(ResponseCode.SqlError)
        if not db_response.data:
            return make_response(ResponseCode.MessageNotFound)
        return jsonify(db_response.data)

    if request.method == "POST":
        if not request_data.has_fields(["name", "description"]):
            return make_response(ResponseCode.BadRequest)
        chat_name = request_data["name"]
        chat_description = request_data["description"]
        # TODO: add ability to create chats with other users
        chat_id = generate_random_string(7)
        db_response = db_manager.create_chat(chat_id, chat_name, chat_description)
        # Adding creator of chat to the chat
        db_response2 = db_manager.add_user_to_chat(user_id, chat_id)
        if db_response.success and db_response2.success:
            return make_response(ResponseCode.OK)
        return make_response(ResponseCode.SqlError)

    if request.method == "PUT":
        if not request_data.has_fields(["chat_id", "name", "description"]):
            return make_response(ResponseCode.BadRequest)
        chat_id = request_data["chat_id"]
        chat_name = request_data["name"]
        chat_description = request_data["description"]
        db_response = db_manager.update_chat(chat_id, chat_name, chat_description)
        if db_response.success:
            return make_response(ResponseCode.OK)
        return make_response(ResponseCode.SqlError)

    if request.method == "DELETE":
        if not request_data.has_field("chat_id"):
            return make_response(ResponseCode.BadRequest)
        chat_id = request_data["chat_id"]
        # Checking if chat exists
        db_response = db_manager.get_chat_data(chat_id)
        if not db_response.success:
            return make_response(ResponseCode.SqlError)
        if not db_response.data:
            return make_response(ResponseCode.ChatNotFound)

        # Deleting chat from database and from all users
        db_response = db_manager.delete_chat(chat_id)
        db_response2 = db_manager.delete_chat_from_all_users(chat_id)
        if db_response.success and db_response2.success:
            return make_response(ResponseCode.OK)
        return make_response(ResponseCode.SqlError)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=port)