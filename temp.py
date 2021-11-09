from database_handler_postgres import db_handler as db

notified_users = db.get_notified_users()

if notified_users:
    for user in notified_users:
        parameters = user['activities']
        for a_name in parameters.keys():
            parameters[a_name]['today_check'] = False
            parameters[a_name]['1h_before_pushed'] = False
            parameters[a_name]['10m_before_pushed'] = False
            parameters[a_name]['on_time_pushed'] = False
            parameters[a_name]['5m_after_pushed'] = False

        db.update_entry(user_id, {'activities': parameters})
