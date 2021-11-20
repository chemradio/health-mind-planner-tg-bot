class Activity:
    # convenience class for accessing parameters via dot notation
    def __init__(self, name, description) -> None:
        self.name = name
        self.description = description

activities = {
    "Фокусировка": "Последовательное выполнение задач. Никакой многозадачности!", 
    "Плановый тупинг": "Время отвлечься от рабочих / домашних проблем, рассеянно посмотреть в окно, подумать о нейтральном.",
    "Приятное общение": "Разговоры с теми, кто приятен / обнимашки.",
    "Физическая активность": "Время для танцев и спорта, энергичных прогулок по помещению или по улице.", 
    "Игра с удовольствием": "Любимое приложение в телефоне, жонглирование, дартс, игра в прятки с коллегами.",
    "Рефлексия": "Обдумать все завершенные за день дела, похвалить себя мысленно за них. Лучше запланировать на конец дня!",
    "Сон": "Оптимальное лично для вас время сна согласно хронотипа."
}

# full activity dict. contains Activity objects for easy access.
activity_dict = {name: Activity(name, description) for name, description in activities.items()}