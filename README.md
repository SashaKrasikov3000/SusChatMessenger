# SusChat Messenger
> #### Simple. Upbeat. Sus.
## What is SusChat?
SusChat messenger is a lightweight REST API based messenger server app written in Python, which allows you to send and receive messages from other users. It's still under development.
> [!CAUTION]
> This app is just my pet project and is not aimed for serious usage. Use it on your own risk.
## How to use
SusChat uses `REST API`, which offers 4 request types (which are associated with **CRUD** operations):
* `GET` - Returns data in JSON format. Usually uses SQL **SELECT** query. 
* `POST` - Adds data to database.  Usually uses SQL **INSERT** query.
* `PUT` - Updates data in database. Usually uses SQL **UPDATE** query.
* `DELETE` - Deletes data from database. Usually uses SQL **DELETE** query.

### Operating with users
Examples of CRUD requests for operating with user table.
* `GET` request - takes target user's ID. Returns [JSON data](#get-response-example) or [error response](#error-response-example)
```
{
  "id": 17
}
```
* `POST` request - takes all data about new user. Returns [successful response](#successful-response-example) or [error response](#error-response-example)
```
{
  "name": "Sus",
  "password": "password"
}
```
* `PUT` request - takes target user's ID and data to modify. Returns [successful response](#successful-response-example) or [error response](#error-response-example)
```
{
  "id": 17,
  "name": "NewName",
  "password": "NewPass"
}
```
* `DELETE` request - takes target user's ID. Returns [successful response](#successful-response-example) or [error response](#error-response-example). Throws error if target user doesn't exist.
```
{
  "id": 17
}
```

### Response codes
SusChat API uses common [HTTP response codes](https://en.wikipedia.org/wiki/List_of_HTTP_status_codes)
Response examples:
<a name="successful-response-example"></a>
* Successful request
```
{
  "code": 200,
  "msg": "OK"
}
```
<a name="get-response-example"></a>
* `GET` request
```
{
  "id": 1,
  "name": "User",
  "password": "pass"
}
```
<a name="error-response-example"></a>
* Invalid request
```
{
  "code": 400,
  "msg": ""Incorrect request form""
}
```