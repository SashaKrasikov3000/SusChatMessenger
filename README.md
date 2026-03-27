# SusChat Messenger
> #### Simple. Upbeat. Sus.
## What is SusChat?
SusChat messenger is a lightweight REST API based messenger server app written in Python, which allows you to send and receive messages from other users. It's still under development.
> [!CAUTION]
> This app is just my pet project and is not aimed for serious usage. Use it on your own risk.

### Upcoming updates:
- [x] Add API for managing users
- [x] Add API for managing messages
- [x] Make authentication using session data in database
- [ ] Add new fields to users:
- - [ ] Bio
- - [ ] Profile picture
- - [ ] Various settings
- [ ] Add new fields to messages:
- - [ ] Modified or not
- - [ ] Link to attached file

## How to use
SusChat uses `REST API`, which offers 4 request types (which are associated with **CRUD** operations):
* `GET` - Returns data in JSON format. Usually uses SQL **SELECT** query. 
* `POST` - Adds data to database.  Usually uses SQL **INSERT** query.
* `PUT` - Updates data in database. Usually uses SQL **UPDATE** query.
* `DELETE` - Deletes data from database. Usually uses SQL **DELETE** query.

### User authentication
API endpoint - `/api/login`  
`GET` request - returns `session_id` of new session for this user.
```
{
  "user_id": 17,
  "password": "amogus"
}
```

### Operating with users
API endpoint - `/api/user`  
Examples of CRUD requests for operating with `users` table.
* `GET` request - takes target `user_id` to get any user's public data or `session_id` to get all current user's data. Returns [JSON data](#get-response-example) or [error response](#error-response-example)
```
{
  "session_id": "cIeDxNiPGBCZ0Km0eP0W"
}
```
* `POST` request - create new user with given data. Returns [successful response](#successful-response-example) or [error response](#error-response-example)
```
{
  "name": "Sus",
  "password": "password"
}
```
* `PUT` request - change user data. Returns [successful response](#successful-response-example) or [error response](#error-response-example)
```
{
  "session_id": "cIeDxNiPGBCZ0Km0eP0W",
  "name": "NewName",
  "password": "NewPass"
}
```
* `DELETE` request - delete user and their sessions from database. Returns [successful response](#successful-response-example) or [error response](#error-response-example). Throws error if target user doesn't exist.
```
{
  "session_id": "cIeDxNiPGBCZ0Km0eP0W"
}
```

### Operating with messages
API endpoint - `/api/msg`
Examples of CRUD requests for operating with `messages` table.
* `GET` request - returns last `max_messages` messages from specified chat. Returns [JSON data](#get-user-response-example) or [error response](#error-response-example)
```
{
  "session_id": "cIeDxNiPGBCZ0Km0eP0W"
  "chat_id": 2,
  "max_messages": 200
}
```
* `POST` request - send message with given content to given chat. Returns [successful response](#successful-response-example) or [error response](#error-response-example)
```
{
  "session_id": "cIeDxNiPGBCZ0Km0eP0W"
  "chat_id": 1,
  "content": "Test message"
}
```
* `PUT` request - change message data. Returns [successful response](#successful-response-example) or [error response](#error-response-example)
```
{
  "session_id": "cIeDxNiPGBCZ0Km0eP0W",
  "msg_id": 4,
  "content": "Updated text"
}
```
* `DELETE` request - delete message. Returns [successful response](#successful-response-example) or [error response](#error-response-example). Throws error if target user doesn't exist.
```
{
  "session_id": "cIeDxNiPGBCZ0Km0eP0W",
  "msg_id": 17
}
```

## Response codes
SusChat API uses common [HTTP response codes](https://en.wikipedia.org/wiki/List_of_HTTP_status_codes)
Response examples:
<a name="successful-response-example"></a>
* Successful response
```
{
  "code": 200,
  "msg": "OK"
}
```
<a name="get-user-response-example"></a>
* `GET` user response
```
{
  "user_id": 1,
  "name": "User",
  "password": "pass"
}
```
<a name="get-messages-response-example"></a>
* `GET` messages response
```
{
  [
  {
    "chat_id": 1,
    "content": "Message",
    "datetime": "2026-03-22 11:56:21",
    "from_id": 1,
    "msg_id": 1
  },
  {
    "chat_id": 1,
    "content": "Another message",
    "datetime": "2026-03-22 15:02:50",
    "from_id": 1,
    "msg_id": 2
  },
  {
    "chat_id": 1,
    "content": "Text",
    "datetime": "2026-03-23 18:25:20",
    "from_id": 1,
    "msg_id": 3
  }
  ]
}
```
<a name="error-response-example"></a>
* Error response
```
{
  "code": 400,
  "msg": ""Incorrect request form""
}
```