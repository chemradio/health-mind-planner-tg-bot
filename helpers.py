class TimeBase:
    """Class for handling time objects. Creates instances from 00:00 format string"""
    def __init__(self, timestring: str="00:00", t_mins:int = None):
        if t_mins:
            self.total_minutes = t_mins
        else:
            try:
                self.total_minutes = int(timestring[:2]) * 60 + int(timestring[3:])
            except:
                self.total_minutes = int(timestring.split(':')[0]) * 60 + int(timestring.split(':')[1])

    def __str__(self):
        return f"total mins: {self.total_minutes}, time: {self.hours}:{self.minutes}"
        
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