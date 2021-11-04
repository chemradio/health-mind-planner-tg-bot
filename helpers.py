class TimeBase:
    def __init__(self, timestring: str="00:00", t_mins:int = None):
        if t_mins:
            self.total_minutes = t_mins
        else:
            self.total_minutes = int(timestring[:2]) * 60 + int(timestring[3:])
        
    @property
    def hours(self):
        return self.total_minutes // 60
        
    @property
    def minutes(self):
        return self.total_minutes % 60

    def __lt__(self, other):
        return self.total_minutes < other.total_minutes

    def __le__(self, other):
        return self.total_minutes <= other.total_minutes
        
    def __gt__(self, other):
        return self.total_minutes > other.total_minutes

    def __ge__(self, other):
        return self.total_minutes >= other.total_minutes

    def __eq__(self, other):
        return self.total_minutes == other.total_minutes

    def __add__(self, other):
        return TimeBase(t_mins=self.total_minutes + other.total_minutes)

    def __sub__(self, other):
        return TimeBase(t_mins=self.total_minutes - other.total_minutes)