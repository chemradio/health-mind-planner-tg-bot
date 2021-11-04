from database_handler_postgres import db_handler

db_handler.drop_pg_tables()
db_handler.create_pg_tables()
