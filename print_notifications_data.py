from database_handler_postgres import db_handler as db
from pprint import pprint
notified_users = db.get_notified_users()

if notified_users:
    for user in notified_users:
        parameters = user['activities']
        pprint(user)