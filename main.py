from flask import Flask, request
import sqlite3 as sqlt

app = Flask("SusChat")


@app.route('/')
def home_page():
    # TODO: add home page
    return "<h1>Home page</h1>"


app.run(debug=True)