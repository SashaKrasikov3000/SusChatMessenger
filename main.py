from flask import Flask, request, jsonify
import sqlite3 as sqlt

app = Flask("SusChat")

class DatabaseManager:
    """Database manager object. Contains CRUD operation for users."""
    def __init__(self):
        self.con = sqlt.connect("database.db", check_same_thread=False)
        self.con.row_factory = sqlt.Row
        self.cursor = self.con.cursor()

    def __del__(self):
        self.con.close()

    def sql_query(self, query):
        """Make sql query to database. Return data (or True if it's not a GET request) on success, return exception otherwise"""
        try:
            self.cursor.execute(query)
            self.con.commit()
        except Exception as e:
            return e

        if "SELECT" in query:
            # Returning data as JSON
            return [dict(i) for i in self.cursor.fetchall()]
        return True

    def get_all_users(self):
        return self.sql_query("SELECT * FROM users")

    def get_user(self, user_id):
        users_found = self.sql_query(f"SELECT * FROM users WHERE id={user_id}")
        if users_found:
            return users_found[0]
        return error_responce("No users found")

    def add_user(self, name):
        return self.sql_query(f"INSERT INTO users (name) VALUES ('{name}')")


def success_responce(msg=""):
    """Generate success reponce code"""
    return {"code": 200, "msg": msg}
def error_responce(error):
    """Generate error responce code"""
    return {"code": 500, "msg": error}


@app.route('/')
def home_page():
    # TODO: add home page
    return "<h1>Home page</h1>"


# Api entry point, RESTful architecture

# User managing: GET = get user data, POST = add new user, PUT = update user info, DELETE = delete user
@app.route("/api/user", methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_main():
    request_data = request.get_json()

    if request.method == "GET":
        user_id = request_data["id"]
        user_info = db_manager.get_user(user_id)
        return jsonify(user_info)

    if request.method == "POST":
        user_name, = request_data.values()
        query_status = db_manager.add_user(user_name)
        if query_status:
            return success_responce()
        return error_responce(query_status)


db_manager = DatabaseManager()  # singleton db manager object
app.run(debug=True)