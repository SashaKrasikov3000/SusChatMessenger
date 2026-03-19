from flask import Flask, request
import sqlite3 as sqlt

app = Flask("SusChat")

class DatabaseManager:

    def __init__(self):
        self.con = sqlt.connect("database.db")
        self.cursor = self.con.cursor()

    def sql_query(self, query):
        self.cursor.execute(query)
        self.con.commit()
        return self.cursor.fetchall()

    def get_users(self):
        return self.sql_query("SELECT * FROM users")

    def add_user(self, name):
        return self.sql_query(f"INSERT INTO users (name) VALUES ('{name}')")


@app.route('/')
def home_page():
    # TODO: add home page
    return "<h1>Home page</h1>"


app.run(debug=True)