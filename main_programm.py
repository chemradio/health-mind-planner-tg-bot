import os
import time
import threading
import re
import zoneinfo
from datetime import datetime, timedelta
from collections import OrderedDict

import telegram

from pprint import pprint
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    ParseMode,
    replymarkup,

)

from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    CallbackQueryHandler,
)
from tinydb.utils import D

# CONSTANTS
from admin_ids import ADMIN_IDS
MESSAGE_DELIMITER = ''
MESSAGE_DELIMITER = '\n_______________'
REGISTER_REQUIRED = False


# ADDITIONAL HANDLER OBJECTS
from activity_config import Activity, activity_dict
from message_texts import message_texts as ms

from bot_instance import bot
from helpers import TimeBase

from database_handler_tiny_db import db_handler as db_tiny_db
from database_handler_postgres import db_handler as db_postgres


USE_POSTGRES = True
if USE_POSTGRES:
    db = db_postgres
else:
    db = db_tiny_db


os.system('clear')





############## SUPPORT FUNCTIONS ##############
def check_extract_time(time_input: str) -> str:
    # fmt = r'\d\d:\d\d'
    # fmt = r'[012]\d:[012345]\d'
    fmt = r'(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]'
    matches = re.match(fmt, time_input)
    if matches:
        return matches[0]
    else:
        return False


def check_activity_time_awake(user_id: int, activity_time: str='00:00'):
    is_owl = False
    user_data = db.check_user_in_db(user_id)
    wu = TimeBase(user_data['wakeup'])
    bt = TimeBase(user_data['bedtime']) + TimeBase("00:15")
    at = TimeBase(activity_time)

    if wu > bt:
        is_owl = True
    elif wu == bt:
        return None
    elif wu < bt:
        is_owl = False

    if not is_owl:
        return at > wu and at < bt
    else:
        return at > wu or at < bt


def check_user_activities(user_id):
    user_data = db.check_user_in_db(user_id)
    if user_data:
        return user_data.get('activities', False)


def check_all_activities_entered(user_id):
    user_activities = check_user_activities(user_id)
    if not user_activities:
        return

    entered_activities = [a_name for a_name, a_data in user_activities.items() if a_data['scheduled_time'] and a_name != "Сон"]
    if len(entered_activities) == (len(activity_dict) -1):
        return True
    else:
        return False


def check_user_permission(user_id):
    if not REGISTER_REQUIRED:
        return True
    db_query = db.check_user_registered(user_id)
    if db_query:
        if db_query['permission'] == 'allowed':
            return True

        elif db_query['permission'] == 'pending':
            bot.send_message(
                chat_id=user_id,
                text='Ваш запрос ещё не одобрен. Обратитесь к администратору телеграм-бота.'
            )
            return False

        elif db_query['permission'] == 'blocked':
            bot.send_message(
                chat_id=user_id,
                text='Ваш аккаунт заблокирован. Обратитесь к администратору телеграм-бота.'
            )
            return False
        else:
            return False
    else:
        bot_ask_register(user_id)
        return False
        


def push_register_request(user_id, credentials: str):
    for admin in ADMIN_IDS:
        approve_block_inline = InlineKeyboardMarkup([[
                        InlineKeyboardButton(f"Одобрить", callback_data=f'admin_allow_{user_id}'),
                        InlineKeyboardButton(f"Заблокировать", callback_data=f'admin_block_{user_id}')
                        ]])
        bot.send_message(
            chat_id=admin,
            text="Новая заявка на регистрацию!\n\n" + credentials,
            reply_markup=approve_block_inline
        )
        return


def push_notifications():
    while True:
        print("Sleeping 60 secs")
        time.sleep(60)
        print("Notification thread iteration")

        # not pushing on sunday
        if now.date().weekday() == 6:
            print("sunday... no notifications. Resetting notifications.")
            db.reset_pushed_notifications()
            continue

        notified_users = db.get_notified_users()
        now = datetime.now(zoneinfo.ZoneInfo("Europe/Moscow"))

        # iterate over notified users
        if notified_users:
            for user in notified_users:
                user_first_name = user['first_name']
                user_id = user['telegram_id']
                print(f"\n\nCheck notifications for user: {user_first_name}")

                # get wakeup and bedtime TimeBases + now TimeBase
                wu_time = TimeBase(user['wakeup'])
                bt_time = TimeBase(user['bedtime'])
                now_tb = TimeBase(now.strftime("%H:%M"))

                # check is owl?
                is_owl = False
                if wu_time > bt_time:
                    is_owl = True
                elif wu_time < bt_time:
                    is_owl = False
                else:
                    continue

                # log essential data
                print(f"{user_first_name} wakes up at {wu_time} and goes to bed at {bt_time}")
                print(f"{user_first_name} is owl?: {is_owl}")

                # check for trailing friday in saturday
                if now.weekday() == 5:
                    if is_owl:
                        if now_tb > bt_time:
                            print(f"No Friday trail for owl {user_first_name}... Resetting notifications.")
                            db.reset_pushed_notifications(tg_id=user_id)
                            continue
                        else:
                            # continue to notifications
                            pass
                    else:
                        continue
                
                # check for trailing sunday in monday
                if now.weekday() == 0:
                    if now_tb < wu_time:
                        print(f"{user_first_name} sunday tailing... Resetting notifications")
                        db.reset_pushed_notifications(tg_id=user_id)
                        continue

                pprint(user)
                print(f"Notifications: current time {now}")
                now_day_mins_passed = now.hour*60+now.minute
                wu_day_mins_passed = wu_time.total_minutes

                # check if user is asleep
                user_asleep = False if check_activity_time_awake(user_id, now.strftime("%H:%M")) else True
                if user_asleep :
                    db.reset_pushed_notifications(tg_id=user_id)
                    print(f"User {user['first_name']} is asleep... Resetting notifications")
                    continue
                
                # # check if user already woke up on monday
                # if now.weekday() == 0:
                #     if now_tb < wu_time:
                #         db.reset_pushed_notifications(tg_id=user_id)
                #         print(f"User {user['first_name']} sunday tailing... Resetting notifications")
                #         continue
                                    
                # reset activities to false on wakeup
                # if wu_day_mins_passed - now_day_mins_passed == 0:
                #     holiday_check = False
                #     if now.today().weekday() in (5,6):
                #         holiday_check = True

                #     parameters = user['activities']
                #     for a_name in parameters.keys():
                #         parameters[a_name]['today_check'] = False
                #         parameters[a_name]['1h_before_pushed'] = False
                #         parameters[a_name]['10m_before_pushed'] = False
                #         parameters[a_name]['on_time_pushed'] = False
                #         parameters[a_name]['5m_after_pushed'] = False

                #     db.update_entry(user_id, {'activities': parameters})
                #     print(f"Reset activities on wakeup for user {user['first_name']}")
                #     user['activities'] = parameters
                #     # continue

                for a_name, a_data in user['activities'].items():
                    if not a_data.get('scheduled_time'):
                        continue
                    if a_data['today_check']:
                        continue
                    
                    # print(f"Activity: {a_name}, data: {a_data}")
                    a_time = TimeBase(a_data['scheduled_time'])
                    a_day_mins_passed = a_time.total_minutes

                    # correct midnight offset
                    if now_day_mins_passed <= a_day_mins_passed:
                        calculation = a_day_mins_passed - now_day_mins_passed
                        five_min_calc = -9000
                    else:
                        calculation = a_day_mins_passed - now_day_mins_passed + 1440
                        five_min_calc = a_day_mins_passed - now_day_mins_passed

                    print(f"Time to activity {a_name}: {calculation//60} hrs {calculation%60} mins")
                    print(f"Five min calc: {five_min_calc} mins")

                    # markups
                    remind_markup = InlineKeyboardMarkup([[InlineKeyboardButton(f"В чём суть?",
                                                        callback_data=f'remind_activity_{a_name}')]])
                    confirm_act_start = InlineKeyboardMarkup([[InlineKeyboardButton(f"Подтверждаю",
                                                            callback_data=f'confirm_act_start_{a_name}')]])
                    confirm_remind_markup = InlineKeyboardMarkup([[
                        InlineKeyboardButton(f"Подтверждаю", callback_data=f'confirm_act_start_{a_name}'),
                        InlineKeyboardButton(f"В чём суть?", callback_data=f'remind_activity_{a_name}')
                        ]])

                    # check 1h notif conditions
                    if calculation in range(58, 61) and not a_data['1h_before_pushed']:
                        try:
                            msg = bot.send_message(
                                chat_id=user_id,
                                text=f"{ms.one_hour_before} <b>{a_name.lower()}</b>",
                                parse_mode=ParseMode.HTML,
                                reply_markup=remind_markup
                            )
                            print(msg)
                            if msg:
                                parameters = user['activities']

                                parameters[a_name]['1h_before_pushed'] = True

                                db.update_entry(user_id, {'activities': parameters})
                        except:
                            pass

                    # check 10m notif conditions
                    elif calculation in range(8, 11) and not a_data['10m_before_pushed']:
                        try:
                            msg = bot.send_message(
                                chat_id=user_id,
                                text=f"До начала запланированной активности <b>{a_name.lower()}</b> осталось 10 минут.",
                                parse_mode=ParseMode.HTML,
                                reply_markup=remind_markup
                            )
                            print(msg)
                            if msg:
                                parameters = user['activities']
                                parameters[a_name]['10m_before_pushed'] = True
                                db.update_entry(user_id, {'activities': parameters})
                        except:
                            pass

                    # check 00 time main notification to start
                    elif calculation in range(-2, 1) and not a_data['on_time_pushed']:
                        try:
                            msg = bot.send_message(
                                chat_id=user_id,
                                text=f"Время активности <b>{a_name.lower()}</b> наступило. Подтвердите, что Вы приступили к её выполнению.",
                                reply_markup=confirm_remind_markup,
                                parse_mode = ParseMode.HTML
                            )
                            print(msg)
                            if msg:
                                parameters = user['activities']
                                parameters[a_name]['on_time_pushed'] = True
                                db.update_entry(user_id, {'activities': parameters})
                        except:
                            pass

                    # check 5mafter notif conditions
                    elif five_min_calc in range(-7, -4) and not a_data['5m_after_pushed']:
                        confirm_act_start = InlineKeyboardMarkup([[InlineKeyboardButton(f"Подтверждаю", callback_data=f'confirm_act_start_{a_name}')]])
                        try:
                            msg = bot.send_message(
                                chat_id=user_id,
                                text=f"Время активности <b>{a_name.lower()}</b> наступило. Подтвердите, что Вы приступили к её выполнению.",
                                reply_markup=confirm_remind_markup,
                                parse_mode = ParseMode.HTML
                            )
                            print(msg)
                            if msg:
                                parameters = user['activities']
                                parameters[a_name]['5m_after_pushed'] = True
                                db.update_entry(user_id, {'activities': parameters})
                        except:
                            pass

        






############## BOT RESPONCES ##############

def bot_ask_start(user_id):
    bot.send_message(
        chat_id=user_id,
        text=ms.ask_start,
    )
    return

def bot_greet(user_id):
    bot.send_message(
        chat_id=user_id,
        text=ms.hello_text,
    )

def bot_ask_plan_ready(user_id):
    yes_no_keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(f"Да", callback_data='ready_to_plan'),
        InlineKeyboardButton(f"Нет", callback_data='not_ready_to_plan'),
            ]])
    bot.send_message(
        chat_id=user_id,
        text=ms.intro_text,
        reply_markup=yes_no_keyboard
    )
    return

def bot_ask_plan_activities_ready(user_id):
    yes_no_keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(f"Да", callback_data='ready_plan_activities'),
        InlineKeyboardButton(f"Нет", callback_data='not_ready_plan_activities'),
            ]])
    bot.send_message(
        chat_id=user_id,
        text=ms.ready_to_plan,
        reply_markup=yes_no_keyboard
    )
    return

def bot_remind_how_continue(user_id):
    bot.send_message(
        chat_id=user_id,
        text=ms.not_ready_plan_activities
    )
    return

def bot_ask_wakeup(user_id):
    bot.send_message(
        chat_id=user_id,
        text=ms.wakeup_question,
    )
    return

def bot_ask_bedtime(user_id):
    bot.send_message(
        chat_id=user_id,
        text=ms.bedtime_question,
    )
    return

def bot_time_entry_error(user_id):
    bot.send_message(
        chat_id=user_id,
        text="Время необходимо ввести в формате ЧЧ:ММ\n\nНапример, 15:30"
    )

def bot_gp_error(user_id):
    bot.send_message(
        chat_id=user_id,
        text="Что-то пошло не так..."
    )

def bot_ask_activity_start_time(user_id, specific_activity=None):
    if check_all_activities_entered(user_id):
        bot_ask_show_schedule(user_id)
        return
    user_activities = check_user_activities(user_id)

    if specific_activity:
        db.update_entry(user_id, {'stage': f"activity_{specific_activity}"})
        message = f"""<b>{specific_activity.title()}</b>
    <i>{activity_dict[specific_activity].description}</i>
    {ms.time_for_activity}"""
        bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode=ParseMode.HTML
        )
        return
    else:
        for a_name, a_data in user_activities.items():
            if a_name == "Сон":
                continue

            if not a_data['scheduled_time']:
                db.update_entry(user_id, {'stage': f"activity_{a_name}"})
                message = f"""<b>{a_name.title()}</b>
    <i>{activity_dict[a_name].description}</i>
    {ms.time_for_activity}"""
                bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode=ParseMode.HTML
                )
                return


def bot_ask_show_schedule(user_id):
    show_schedule_markup = InlineKeyboardMarkup([[InlineKeyboardButton(f"Да", callback_data='show_schedule'),InlineKeyboardButton(f"Нет", callback_data='dont_show_schedule')]])
    bot.send_message(
        chat_id=user_id,
        text=ms.schedule_see,
        reply_markup=show_schedule_markup
    )


def bot_check_schedule(user_id):
    # get user activities/ should work always
    user_activities = check_user_activities(user_id)
    if not user_activities:
        bot_gp_error(user_id)
        return
    user_activities_sorted = OrderedDict(sorted(
        user_activities.items(), key=lambda x:TimeBase(x[1]['scheduled_time']).total_minutes
    ))

    user_data = db.check_user_in_db(user_id)

    # stop notifications for user
    # db.update_entry(user_id, {'notifications': False})

    # show schedule with two inline buttons for save and edit
    change_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton(f"Сохранить", callback_data=f'save_schedule'),
        InlineKeyboardButton(f"Изменить", callback_data=f'change_schedule')
    ]])
    wakeup = user_data['wakeup'] if user_data['wakeup'] else 'не указано'
    bedtime = user_data['bedtime'] if user_data['bedtime'] else 'не указано'
    message_text = f"График Вашего ИДЕАЛЬНОГО ДНЯ.\n\nПодъем: {wakeup}\nОтбой: {bedtime}\n\n"

    for a_name, a_data in user_activities_sorted.items():
        if a_name == "Сон":
            continue

        sched_time = a_data['scheduled_time'] if a_data['scheduled_time'] else 'не указано'
        message_text += f"{a_name.title()}\nВремя старта {sched_time}\n\n"
    bot.send_message(
        chat_id=user_id,
        text=message_text,
        reply_markup=change_markup
    )


def bot_change_schedule(user_id):
    user_data = db.check_user_in_db(user_id)
    user_activities = check_user_activities(user_id)
    if not user_activities:
        bot_gp_error(user_id)
        return

    db.update_entry(user_id, {'notifications': False})

    wakeup = user_data['wakeup'] if user_data['wakeup'] else 'не указано'
    bedtime = user_data['bedtime'] if user_data['bedtime'] else 'не указано'
    change_markup = InlineKeyboardMarkup([[InlineKeyboardButton(f"Изменить время", callback_data=f'change_wakeup_bedtime')]])
    bot.send_message(
            chat_id=user_id,
            text=f"""Подъем: {wakeup}
Отбой: {bedtime}""",
            reply_markup=change_markup
    )

    if not user_data['wakeup'] or not user_data['bedtime']:
        return

    user_activities_sorted = OrderedDict(sorted(user_activities.items(), key=lambda x:TimeBase(x[1]['scheduled_time']).total_minutes))
    for a_name, a_data in user_activities_sorted.items():
        if a_name == "Сон":
            continue

        change_markup = InlineKeyboardMarkup([[InlineKeyboardButton(f"Изменить время", callback_data=f'change_{a_name}')]])
        bot.send_message(
            chat_id=user_id,
            text=f"""{a_name.title()}
Время выполнения: {a_data['scheduled_time']}""",
            reply_markup=change_markup
        )

    save_markup = InlineKeyboardMarkup([[InlineKeyboardButton(f"Сохранить график", callback_data=f'save_schedule')]])
    bot.send_message(
        chat_id=user_id,
        text=f"""Оставить график в текущем виде.""",
        reply_markup=save_markup
    )

def bot_incorrect_activity_time(user_id):
    bot.send_message(
        chat_id=user_id,
        text="В это время вы спите. Попробуйте еще раз."
    )


def bot_schedule_saved(user_id):
    if check_all_activities_entered(user_id):
        db.update_entry(user_id, {'notifications': True})
        bot.send_message(
            chat_id=user_id,
            text="Ваш график успешно сохранен.\n\nМолодец! Ведь мы теперь ещё на один шаг ближе к тому, чтобы прожить вместе ИДЕАЛЬНЫЙ ДЕНЬ!\nЯ буду напоминать Вам о времени старта каждой активности ровно за час, и потом за 10 минут!\n\nХорошего дня!\nВсегда Ваш CBSD-бот!"
        )
    else:
        bot.send_message(
            chat_id=user_id,
            text="Ваш график успешно сохранен, однако он не заполнен до конца.\n\nЯ буду напоминать Вам о времени старта каждой активности только если он будет полностью заполнен!\n\nХорошего дня!\nВсегда Ваш CBSD-бот!"
        )


def bot_remind_activity(user_id: int, activity: str):
    bot.send_message(
        chat_id=user_id,
        text=f"<b>{activity.title()}</b>\n<i>{activity_dict[activity].description}</i>",
        parse_mode=ParseMode.HTML
    )


def ask_credentials(user_id):
    bot.send_message(
        chat_id=user_id,
        text="Пожалуйста, введите ниже Ваше ФИО и e-mail в одном сообщении. Можно через запятую.\n\nПосле отправки сообщения его нельзя будет отредактировать. Будьте внимательны."
    )
    return


def bot_ask_register(user_id):
    bot.send_message(
        chat_id=user_id,
        text="Подайте заявку на регистрацию через команду /register"
    )
    return


def bot_notify_is_approved(user_id):
    bot.send_message(
        chat_id=user_id,
        text="Ваш запрос одобрен.\n\nСоздайте свой идеальный график через команду /start"
    )
    return





############## ADMIN FUNCTIONS ##############
def register_requests(update: Update, _: CallbackContext) -> None:
    requests = db.get_register_requests()
    if requests:
        for request in requests:
            approve_block_inline = InlineKeyboardMarkup([[
                        InlineKeyboardButton(f"Одобрить", callback_data=f'admin_allow_{request["telegram_id"]}'),
                        InlineKeyboardButton(f"Заблокировать", callback_data=f'admin_block_{request["telegram_id"]}')
                        ]])
            bot.send_message(
                chat_id=update.message.from_user.id,
                text=f"{request['credentials']}",
                reply_markup=approve_block_inline
            )
    else:
        bot.send_message(
                chat_id=update.message.from_user.id,
                text=f"Никого нет..."
            )
    return


def allowed_users(update: Update, _: CallbackContext) -> None:
    users = db.get_allowed_users()
    if users:
        for user in users:
            block_keyboard = InlineKeyboardMarkup([[
                        InlineKeyboardButton(f"Заблокировать", callback_data=f'admin_block_{user["telegram_id"]}')
                        ]])
            bot.send_message(
                chat_id=update.message.from_user.id,
                text=f"{user['credentials']}",
                reply_markup=block_keyboard
            )
    else:
        bot.send_message(
                chat_id=update.message.from_user.id,
                text=f"Никого нет..."
            )
    return


def blocked_users(update: Update, _: CallbackContext) -> None:
    users = db.get_blocked_users()
    if users:
        for user in users:
            allow_keyboard = InlineKeyboardMarkup([[
                        InlineKeyboardButton(f"Одобрить", callback_data=f'admin_allow_{user["telegram_id"]}')
                        ]])
            bot.send_message(
                chat_id=update.message.from_user.id,
                text=f"{user['credentials']}",
                reply_markup=allow_keyboard
            )
    else:
        bot.send_message(
                chat_id=update.message.from_user.id,
                text=f"Никого нет..."
            )
    return





















############## /START COMMAND ##############

def start(update: Update, _: CallbackContext) -> None:

    user_id = update.message.from_user.id
    # check allowed
    if not check_user_permission(user_id):

        return

    user_data = db.check_user_in_db(update.message.from_user.id)
    if not user_data:

        activities = {
            a_name: {
                'scheduled_time': None,
                'today_check': False,
                '1h_before_pushed': False,
                '10m_before_pushed': False,
                'on_time_pushed': False,
                '5m_after_pushed': False,
            }
            for a_name in activity_dict.keys()}

        parameters = {
            "telegram_id": update.message.from_user.id,
            "first_name": update.message.from_user.first_name,
            "register_timestamp": int(time.time()),
            "wakeup": None,
            'bedtime': None,
            "activities": activities,
            'permission': True,
            'stage': 'ready_to_plan',
            'notifications': False
        }

        db.add_db_entry(parameters)
        bot_greet(update.message.from_user.id)
        bot_ask_plan_ready(update.message.from_user.id)
        return
    elif user_data['stage'] == 'ready_plan_activities':
        bot_ask_plan_activities_ready(user_data['telegram_id'])
        return

    else:
        update.message.reply_text('Вы уже создали свой график. Просмотрите или отредактируйте его через команду /schedule')
        return


def schedule_command(update: Update, _: CallbackContext) -> None:
    if not check_user_permission(update.message.from_user.id):
        return
    if db.check_user_in_db(update.message.from_user.id):
        bot_check_schedule(update.message.from_user.id)
    return


def reset_command(update: Update, _: CallbackContext) -> None:
    if not check_user_permission(update.message.from_user.id):
        return
    db.remove_user(update.message.from_user.id)
    bot.send_message(
        chat_id=update.message.from_user.id,
        text=ms.reset_command_text
    )
    return 


def activities_command(update: Update, _: CallbackContext) -> None:
    if not check_user_permission(update.message.from_user.id):
        return

    message_text = '<b>Список активностей:</b>\n\n'
    for a_name, a_data in activity_dict.items():
        message_text += f"<b>{a_name.title()}</b>\n<i>{a_data.description}</i>\n\n"
    bot.send_message(
        chat_id=update.message.from_user.id,
        text=message_text,
        parse_mode=ParseMode.HTML
    )

    all_entered = check_all_activities_entered(update.message.from_user.id)
    if not all_entered:
        continue_entry_keyboard = InlineKeyboardMarkup([[
                        InlineKeyboardButton(f"Продолжить", callback_data=f'continue_entry'),
                        InlineKeyboardButton(f"Начать заново", callback_data=f'not_ready_to_plan')
                        ]])

        bot.send_message(
            chat_id = update.message.from_user.id,
            text="Вы готовы продолжить назначать время начала активностей?",
            reply_markup=continue_entry_keyboard
        )
        # display hint
        pass
    return


def help_command(update: Update, _: CallbackContext) -> None:
    if not check_user_permission(update.message.from_user.id):
        return

    admin_text = ''
    if update.message.from_user.id in ADMIN_IDS:
        admin_text = """\n\nКомманды администратора
/register_requests - просмотреть заявки на регистрацию
/allowed_users - список одобренных пользователей
/blocked_users - список заблокированных пользователей"""

    bot.send_message(
        chat_id = update.message.from_user.id,
        text = ms.help_text_text + admin_text
    )
    return


def register_command(update: Update, _: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if not db.check_user_registered(user_id):
        db.add_init_user(user_id)
        ask_credentials(user_id)
    return














############## TEXT HANDLER ##############
def text_handler(update: Update, _: CallbackContext) -> None:
    user_id = update.message.from_user.id

    if not check_user_permission(user_id):
        if db.check_user_status(user_id) == 'init':
            db.pend_user(user_id, {'credentials': update.message.text})
            bot.send_message(
                chat_id=user_id,
                text="Спасибо! Ваша заявка на рассмотрении."
            )
            push_register_request(user_id, update.message.text)
            return
        return



    user_data = db.check_user_in_db(update.message.from_user.id)
    if not user_data:
        update.message.reply_text("Сперва нажмите /start")
        return

    user_id = update.message.from_user.id
    current_stage = user_data['stage']

    if current_stage == 'wakeup':

        user_time = check_extract_time(update.message.text)
        if not user_time:
            bot_time_entry_error(user_id)
            return

        db.update_entry(user_id, {'wakeup': user_time})
        db.update_entry(user_id, {'stage': 'bedtime'})
        bot_ask_bedtime(user_id)
        return

    elif current_stage == 'bedtime':
        user_time = check_extract_time(update.message.text)
        if not user_time:
            bot_time_entry_error(user_id)
            return

        user_activities = user_data['activities']
        user_activities["Сон"]['scheduled_time'] = user_time

        db.update_entry(user_id, {'bedtime': user_time, 'stage': 'ready_plan_activities', 'activities': user_activities})
        bot_ask_plan_activities_ready(user_id)
        # bot_ask_activity_start_time(user_id)
        return

    elif 'activity_' in current_stage:
        user_time = check_extract_time(update.message.text)
        if not user_time:
            bot_time_entry_error(user_id)
            return

        if not check_activity_time_awake(user_id, user_time):
            bot_incorrect_activity_time(user_id)
            return
        
        current_activity = current_stage[9:]
        user_activities = user_data['activities']
        user_activities[current_activity]['scheduled_time'] = user_time
        db.update_entry(user_id, {'activities': user_activities})

        if not check_all_activities_entered(user_id):
            db.update_entry(user_id, {'stage': 'activities'})
            bot_ask_activity_start_time(user_id)
            return
        else:
            # show schedule
            db.update_entry(user_id, {'stage': 'show_schedule'})
            bot_ask_show_schedule(user_id)
            return
    return









############## INLINE BUTTON HANDLER ##############

def inline_button_handler(update: Update, _: CallbackContext) -> None:
    # pprint(update.to_dict())
    query = update.callback_query
    user_id = query.from_user.id


    try:
        # admin part
        if user_id in ADMIN_IDS:
            
            if 'admin_allow_' in query.data:
                query.answer()
                query.edit_message_text(text=query.message.text + "\n\n Одобрен!")
                target_user = int(query.data[12:])
                db.allow_user(target_user)
                bot_notify_is_approved(target_user)
                return

            elif 'admin_block_' in query.data:
                query.answer()
                query.edit_message_text(text=query.message.text + "\n\n Заблокирован!")
                target_user = int(query.data[12:])
                db.block_user(target_user)
                db.remove_user(target_user)
                return





        user_data = db.check_user_in_db(user_id)
        # print(user_data)

        if not user_data:
            bot_gp_error(user_id)
            return
        
        current_stage = user_data['stage']
        print(current_stage)

        # 1 ready to plan --- YES/NO
        # if current_stage == 'ready_to_plan':
        if query.data == 'ready_to_plan':
            query.answer()
            query.edit_message_text(text=query.message.text+MESSAGE_DELIMITER)
            db.update_entry(user_id, {'stage': 'wakeup'})
            bot_ask_wakeup(user_id)
        elif query.data == 'not_ready_to_plan':
            query.answer()
            query.edit_message_text(text=query.message.text)
            db.remove_user(user_id)
            bot_ask_start(user_id)
            return

        # elif current_stage == 'ready_plan_activities':
        if query.data == 'ready_plan_activities':
            query.answer()
            query.edit_message_text(text=query.message.text)
            db.update_entry(user_id, {'stage': 'activities'})
            bot_ask_activity_start_time(user_id)
        elif query.data == 'not_ready_plan_activities':
            query.answer()
            query.edit_message_text(text=query.message.text)
            bot_remind_how_continue(user_id)
            # db.update_entry(user_id, {'stage': 'activities'})
            pass

        # elif current_stage == "show_schedule":
        elif query.data == 'show_schedule':
            query.answer()
            query.edit_message_text(text=query.message.text)
            bot_check_schedule(user_id)
            return

        elif query.data == 'dont_show_schedule' or query.data == 'save_schedule':
            query.answer()
            query.edit_message_text(text=query.message.text)
            bot_schedule_saved(user_id)
            return

        elif query.data == 'change_schedule':
            print('got change schedule')
            bot_change_schedule(user_id)
            return

        elif query.data == 'change_wakeup_bedtime':
            query.answer()
            db.update_entry(user_id, {'stage': 'wakeup'})
            bot_ask_wakeup(user_id)
            return

        elif "change_" in query.data:
            change_activity = query.data[7:]
            user_activities = user_data['activities']
            user_activities[change_activity]['scheduled_time'] = None
            db.update_entry(user_id, {'stage': 'activities', 'activities': user_activities})
            bot_ask_activity_start_time(user_id, change_activity)

        elif 'confirm_act_start_' in query.data:
            a_name = query.data[18:]
            query.answer()
            query.edit_message_text(text=query.message.text)
            parameters = user_data['activities']
            parameters[a_name]['today_check'] = True
            parameters[a_name]['1h_before_pushed'] = False
            parameters[a_name]['10m_before_pushed'] = False
            parameters[a_name]['on_time_pushed'] = False
            parameters[a_name]['5m_after_pushed'] = False
            db.update_entry(user_id, {'activities': parameters})
            return

        elif 'remind_activity_' in query.data:
            query.answer()
            # query.edit_message_text(text=query.message.text)
            a_name = query.data[16:]
            bot_remind_activity(user_id, a_name)

        elif query.data == 'continue_entry':
            query.answer()
            query.edit_message_text(text=query.message.text)
            print(current_stage)
            if current_stage == 'ready_to_plan':
                query.answer()
                query.edit_message_text(text=query.message.text+MESSAGE_DELIMITER)
                db.update_entry(user_id, {'stage': 'wakeup'})
                bot_ask_wakeup(user_id)
                return

            elif current_stage == 'wakeup':
                bot_ask_wakeup(user_id)
                return
            elif current_stage == 'bedtime':
                bot_ask_bedtime(user_id)
                return
            elif current_stage == 'activities' or current_stage == 'ready_plan_activities' or "activity_" in current_stage:
                if current_stage == 'ready_plan_activities':
                    db.update_entry(user_id, {'stage': 'activities'})
                bot_ask_activity_start_time(user_id)
                return

        elif query.data == 'restart_session':
            query.answer()
            query.edit_message_text(text=query.message.text)

            db.remove_user(update.message.from_user.id)
            bot.send_message(
                chat_id=user_id,
                text=ms.reset_command_text
            )
        else:
            return

    except:
        # bot_gp_error(user_id)
        pass



