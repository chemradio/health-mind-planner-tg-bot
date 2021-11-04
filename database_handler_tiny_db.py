from tinydb import TinyDB, Query
from threading import RLock
from pprint import pformat, pprint
import time

stages = [
    'ready_to_plan',
    'wakeup',
    'bedtime',
    'activities',
    'check',
    'processed'
]

main_db_lock = RLock()

def thread_safe(func):
    def wrapper_thread_safe(*args, **kwargs):
        with main_db_lock:
            value = func(*args, **kwargs)
            return value
    return wrapper_thread_safe


class DatabaseEntry:
    def __init__(self):
        pass


class DatabaseHandler:
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(DatabaseHandler, cls).__new__(cls)
        return cls.instance

    def __init__(self) -> None:
        self.db = TinyDB('db.json')
        self.db_users = TinyDB('users.json')

    ################ main db ################
    @thread_safe
    def check_user_in_db(self, telegram_id):
        db_query = Query()
        results = self.db.search(db_query.telegram_id == telegram_id)
        if results:
            return results[0]
        else:
            return False

    @thread_safe
    def add_db_entry(self, parameters):
        if not self.check_user_in_db(parameters['telegram_id']):
            return self.db.insert(parameters)
        else:
            return False

    @thread_safe
    def update_entry(self, telegram_id: int, parameters: dict):
        datacell = self.check_user_in_db(telegram_id)
        if datacell:
            for key, value in parameters.items():
                self.db.update({key:value}, doc_ids=[datacell.doc_id])
        else:
            return False

    @thread_safe
    def remove_user(self, telegram_id: int):
        datacell = self.check_user_in_db(telegram_id)
        if not datacell:
            return False
        db_query = Query()
        self.db.remove(db_query.telegram_id == telegram_id)
        return True

    @thread_safe
    def get_notified_users(self):
        db_query = Query()
        results = self.db.search(db_query.notifications == True)
        if results:
            return results
        else:
            return False

    ################ activity times db ################
    @thread_safe
    def add_notification_time(self, user_id, act_name: str="Some Activity", timestr: str="00:00", one_h_b=False, ten_m_b=False, five_m_f=False):
        parameters = {
            "telegram_id": user_id,
            'activity_name': act_name,
            'notification_time': timestr,
            '1h_before_pushed': one_h_b,
            '10m_before_pushed': ten_m_b,
            '5m_after_pushed': five_m_f
        }
        self.db_act_times.insert(parameters)



    ################ users db ################
    @thread_safe
    def check_user_registered(self, user_id):
        """Checks if user in database and returns his entry. Otherwise returns False"""
        db_query = Query()
        results = self.db_users.search((db_query.telegram_id == user_id))
        if results:
            return results[0] # ['permission'] # can be one of 'allowed' 'pending' 'blocked'
        else:
            return False

    @thread_safe
    def add_init_user(self, user_id):
        """Adds init user in the database to ask for credentials."""
        result = self.check_user_registered(user_id)
        if not result:
            self.db_users.insert({'telegram_id': user_id, 'permission': 'init'})
            return True
        else:
            return False

    @thread_safe
    def pend_user(self, user_id, data: dict):
        """Pend user which submitted credentials."""
        result = self.check_user_registered(user_id)
        if result:
            if result['permission'] == 'init':
                for key, value in data.items():
                    self.db_users.update({key: value, 'permission': 'pending'}, doc_ids=[result.doc_id])

        if not result:
            data['permission'] = 'pending'
            self.db_users.insert(data)
        else:
            return False

    @thread_safe
    def allow_user(self, user_id):
        """Allows user in database is it exists. Else returns False."""
        result = self.check_user_registered(user_id)
        if result:
            self.db_users.update({'permission': 'allowed'}, doc_ids=[result.doc_id])
        else:
            return False

    @thread_safe
    def block_user(self, user_id):
        """Blocks user in database is it exists. Else returns False."""
        result = self.check_user_registered(user_id)
        if result:
            self.db_users.update({'permission': 'blocked'}, doc_ids=[result.doc_id])
        else:
            return False

    @thread_safe
    def check_user_status(self, user_id) -> str:
        """If user is in database returns permission status in the form of string. If user never interacted with the bot before returns False"""
        result = self.check_user_registered(user_id)
        if result:
            return result['permission']
        else:
            return False



    ################ admin related ################
    @thread_safe
    def get_register_requests(self):
        db_query = Query()
        results = self.db_users.search(db_query.permission == 'pending')
        if results:
            return results
        else:
            return False

    @thread_safe
    def get_allowed_users(self):
        db_query = Query()
        results = self.db_users.search(db_query.permission == 'allowed')
        if results:
            return results
        else:
            return False

    @thread_safe
    def get_blocked_users(self):
        db_query = Query()
        results = self.db_users.search(db_query.permission == 'blocked')
        if results:
            return results
        else:
            return False




db_handler = DatabaseHandler()