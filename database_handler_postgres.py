import os
import psycopg2
from psycopg2.extras import Json, DictCursor
# from pprint import pprint

PG_URI = os.environ.get('DATABASE_URL', 'localhost')
# print(f"PG_URI = {PG_URI}")

class DatabaseHandler:
    """Class containing all functions for operating with Postgresql db"""
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(DatabaseHandler, cls).__new__(cls)
        return cls.instance

    def __init__(self) -> None:
        # """THIS LINES FOR TESTING LOCALLY"""
        # self.conn = psycopg2.connect(
        #     host="localhost",
        #     database="postgres",
        #     user="postgres",
        #     password="12345"
        # )

        """THIS LINES FOR TESTING ON HEROKU"""
        self.conn = psycopg2.connect(PG_URI)
        
        self.users_keys = ('pg_ig', 'telegram_id', 'permission', 'credentials')
        self.notification_keys = ('pg_ig', 'telegram_id', 'first_name', 'wakeup', 'bedtime', 'activities', 'stage', 'notifications')


    def gen_purp_exec(self, string):
        with self.conn.cursor() as cur:
            cur.execute(string)
            return cur.fetchall()


    def get_pg_tables(self):
        """Get list of all available Postgres tables"""
        with self.conn.cursor() as cur:
            cur.execute("""SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'""")
            return cur.fetchall()

    def create_pg_tables(self):
        """Create default Postgres tables - namely USERS and NOTIFICATION"""
        with self.conn.cursor() as cur:
            cur.execute("""CREATE TABLE users (
                pg_ig SERIAL PRIMARY KEY,
                telegram_id BIGINT,
                permission VARCHAR,
                credentials VARCHAR
            )""")
            self.conn.commit()

        with self.conn.cursor() as cur:
            cur.execute("""CREATE TABLE notifications (
                pg_ig SERIAL PRIMARY KEY,
                telegram_id BIGINT,
                first_name VARCHAR,
                wakeup VARCHAR,
                bedtime VARCHAR,
                permission BOOL,
                activities JSONB,
                stage VARCHAR,
                notifications BOOL
            )""")
            self.conn.commit()

    def drop_pg_tables(self):
        """Delete all Postgres tables. To be used in conjunction with create_pg_tables"""
        tables = self.get_pg_tables()
        if tables:
            with self.conn.cursor() as cur:
                for table in tables:
                    cur.execute(f'DROP TABLE {table[0]}')
                    self.conn.commit()

    ################ users db ################
    def get_all_users(self):
        """Get all users from Permissions table. Only for Register-ON mode"""
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT * from users;")
            return cur.fetchall()


    def add_init_user(self, user_id):
        """Add user to DB with init status.
        Next step is to receive user provided credentials and set status to PENDING.
        PENDING is for awaiting approval from admin."""
        registered = self.check_user_registered(user_id)
        if not registered:
            with self.conn.cursor() as cur:
                cur.execute("INSERT INTO users (telegram_id, permission) VALUES (%s, %s);", (user_id, 'init',))
                self.conn.commit()
                return True
        else:
            return False


    def check_user_registered(self, user_id):
        """Checks if user in database and returns his entry. Otherwise returns False"""
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("select * from users where telegram_id = %s;", (user_id,))
            result = cur.fetchone()
            if result:
                return result
            else:
                return False


    def pend_user(self, user_id, data: dict):
        """Pend user which submitted credentials."""
        result = self.check_user_registered(user_id)
        if result:
            if result[self.users_keys.index('permission')] == 'init':
                with self.conn.cursor() as cur:
                    cur.execute("UPDATE users SET permission = %s, credentials = %s WHERE telegram_id = %s;", ('pending', data['credentials'], user_id,))
                self.conn.commit()
                return True
        else:
            return False

    
    def allow_user(self, user_id):
        """Allows user in database is it exists. Else returns False."""
        result = self.check_user_registered(user_id)
        if result:
            with self.conn.cursor() as cur:
                    cur.execute("UPDATE users SET permission = %s WHERE telegram_id = %s;", ('allowed', user_id,))
            self.conn.commit()
            return True
        else:
            return False


    def block_user(self, user_id):
        """Blocks user in database is it exists. Else returns False."""
        result = self.check_user_registered(user_id)
        if result:
            with self.conn.cursor() as cur:
                    cur.execute("UPDATE users SET permission = %s WHERE telegram_id = %s;", ('blocked', user_id,))
            self.conn.commit()
            return True
        else:
            return False


    def check_user_status(self, user_id) -> str:
        """If user is in database returns permission status in the form of string. If user never interacted with the bot before returns False"""
        result = self.check_user_registered(user_id)
        if result:
            return result[self.users_keys.index('permission')]
        else:
            return False


    ################ main db ################
    
    def check_user_in_db(self, user_id):
        """Check if notifications entry created for user"""
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT * from notifications WHERE telegram_id = %s;", (user_id,))
            result = cur.fetchone()
        if result:
            return result
        else:
            return False


    def add_db_entry(self, parameters):
        """Add notifications entry for user. Parameters is a strict dict."""
        if not self.check_user_in_db(parameters['telegram_id']):
            with self.conn.cursor() as cur:
                cur.execute("INSERT INTO notifications (telegram_id) VALUES (%s);", (parameters['telegram_id'],))

                cur.execute("UPDATE notifications SET first_name = %s WHERE telegram_id = %s;",
                (parameters['first_name'], parameters['telegram_id'],))
                cur.execute("UPDATE notifications SET wakeup = %s WHERE telegram_id = %s;",
                (parameters['wakeup'], parameters['telegram_id'],))
                cur.execute("UPDATE notifications SET bedtime = %s WHERE telegram_id = %s;",
                (parameters['bedtime'], parameters['telegram_id'],))
                cur.execute("UPDATE notifications SET permission = %s WHERE telegram_id = %s;",
                (parameters['permission'], parameters['telegram_id'],))
                cur.execute("UPDATE notifications SET stage = %s WHERE telegram_id = %s;",
                (parameters['stage'], parameters['telegram_id'],))
                cur.execute("UPDATE notifications SET notifications = %s WHERE telegram_id = %s;",
                (parameters['notifications'], parameters['telegram_id'],))

            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("UPDATE notifications SET activities = %s WHERE telegram_id = %s;", (Json(parameters['activities']), parameters['telegram_id']))
            
            self.conn.commit()
            return True
        else:
            return False


    def update_entry(self, user_id: int, parameters: dict):
        """Update user notifications entry"""
        datacell = self.check_user_in_db(user_id)
        if datacell:
            print("User in db passed")
            for key, value in parameters.items():
                print(f"Pushing key {key} with a value {value} to DB")
                if type(value) == dict:
                    with self.conn.cursor(cursor_factory=DictCursor) as cur:
                        cur.execute(f"UPDATE notifications SET {key} = %s WHERE telegram_id = %s;",
                        (Json(value), user_id,))
                else:
                    with self.conn.cursor() as cur:
                        cur.execute(f"UPDATE notifications SET {key} = %s WHERE telegram_id = %s;",
                        (value, user_id,))
            self.conn.commit()
            return True
        else:
            return False


    def remove_user(self, user_id: int):
        """Remove user's notifications entry"""
        datacell = self.check_user_in_db(user_id)
        if datacell:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM notifications WHERE telegram_id = %s;", (user_id,))
            self.conn.commit()
            return True
        else:
            return False


    def get_notified_users(self):
        """Fetch list of all users with notifications turned on"""
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT * FROM notifications WHERE notifications = %s", (True, ))
            results = cur.fetchall()

        if results:
            return results
        else:
            return False    


    def reset_pushed_notifications(self, tg_id=None):
        """Reset all pushed notifications for all users - Debugging.
        Or reset all pushed notifications for a single user in id is provided"""
        notified_users = self.get_notified_users()
        if notified_users:
            for user in notified_users:
                user_id = user['telegram_id']
                if tg_id:
                    if user_id != tg_id:
                        continue

                parameters = user['activities']
                for a_name in parameters.keys():
                    parameters[a_name]['today_check'] = False
                    parameters[a_name]['1h_before_pushed'] = False
                    parameters[a_name]['10m_before_pushed'] = False
                    parameters[a_name]['on_time_pushed'] = False
                    parameters[a_name]['5m_after_pushed'] = False

                self.update_entry(user_id, {'activities': parameters})

    ################ admin related ################
    
    def get_register_requests(self):
        """Get list of all approval pending users"""
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE permission = %s", ('pending',))
            results = cur.fetchall()
        if results:
            return results
        else:
            return False

    
    def get_allowed_users(self):
        """Get list of all allowed users"""
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE permission = %s", ('allowed',))
            results = cur.fetchall()
        if results:
            return results
        else:
            return False

    
    def get_blocked_users(self):
        """Get list of all blocked users"""
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE permission = %s", ('blocked',))
            results = cur.fetchall()
        if results:
            return results
        else:
            return False


db_handler = DatabaseHandler()