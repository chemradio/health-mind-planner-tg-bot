ask_start = "Для продолжения нажмите /start"
hello_text = "Вас приветствует CBSD-бот. Я помогу спланировать Ваш ИДЕАЛЬНЫЙ ДЕНЬ!"

intro_text = "Вы готовы приступить к планированию ежедневного графика?"

lets_build_schedule = 'Давайте построим Ваш идеальный день в соответствии с Healthy Mind Platter!\nНапомнить, из каких активностей он состоит?'
wakeup_question = "Введите стандартное время подъема в будний день."
bedtime_question = "Введите стандартное время отбоя в будний день."
ready_to_plan = "Вы готовы спланировать время для 6 активностей между подъемом и ночным сном?\n\nОзнакомиться со списком активностей и их описанием можно по команде /activities"

not_ready_plan_activities = "Вы можете продолжить в любое время через команду /start\nОзнакомиться с активностями можно через команду /activities\nСбросить все ваши настройки можно через команду /reset"

time_for_activity = "Во сколько Вы готовы начать эту активность?"
schedule_see = "Хотите ли вы просмотреть свой график?"
save_button = "Сохранить"
change_button = "Исправить"

one_hour_before = "Ровно через час Вас ждёт"
ten_mins_before = "До начала запланированной активности осталось 10 минут."

remind_activity_description = "Напомнить о чём речь?"
reminder_start = "Суть активности в следующем:"

activity_start_confirm = "Время активности наступило. Подтвердите, что Вы приступили к её выполнению."

reset_command_text = "Ваш график удален. Можете начать сначала через команду /start"

help_text_text = """Вас приветствует CBSD-бот. Я помогу спланировать Ваш ИДЕАЛЬНЫЙ ДЕНЬ!

Нажмите /start, чтобы начать планирование

Ознакомиться с активностями можно через команду /activities
Просмотреть или изменить свой график можно через команду /schedule

Сбросить все ваши настройки можно через команду /reset"""


class MessageStore:
    def __init__(self):
        self.hello_text = hello_text
        self.intro_text = intro_text
        self.lets_build_schedule = lets_build_schedule
        self.wakeup_question = wakeup_question
        self.bedtime_question = bedtime_question
        self.ready_to_plan = ready_to_plan
        self.not_ready_plan_activities = not_ready_plan_activities
        self.time_for_activity = time_for_activity
        self.schedule_see = schedule_see
        self.save_button = save_button
        self.change_button = change_button
        self.one_hour_before = one_hour_before
        self.ten_mins_before = ten_mins_before
        self.remind_activity_description = remind_activity_description
        self.reminder_start = reminder_start
        self.activity_start_confirm = activity_start_confirm
        self.ask_start = ask_start
        self.reset_command_text = reset_command_text
        self.help_text_text = help_text_text


message_texts = MessageStore()