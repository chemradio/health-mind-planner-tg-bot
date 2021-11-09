from database_handler_postgres import db_handler as db
from pprint import pprint


print("________ notifications")
notified_users = db.get_notified_users()
if notified_users:
    for user in notified_users:
        pprint(user)


print("________ now for the users")
all_users = db.get_all_users()
if all_users:
    for user in all_users:
        pprint(user)