from wtforms.fields import Field
from wtforms.widgets import TextInput
from datetime import timedelta
import re


WEEKS       = r'(?P<weeks>[\d.]+)\s*(?:w|wks?|weeks?)'
DAYS        = r'(?P<days>[\d.]+)\s*(?:d|dys?|days?)'
HOURS       = r'(?P<hours>[\d.]+)\s*(?:h|hrs?|hours?)'
MINS        = r'(?P<minutes>[\d.]+)\s*(?:m|(mins?)|(minutes?))'
SECS        = r'(?P<seconds>[\d.]+)\s*(?:s|secs?|seconds?)'

TIME_FORMAT = r'(?:{weeks})?\s*(?:{days})?\s*(?:{hours})?\s*(?:{mins})?\s*(?:{secs})?'.format(
    weeks=WEEKS,
    days=DAYS,
    hours=HOURS,
    mins=MINS,
    secs=SECS
)

TIME_REGEX = re.compile(TIME_FORMAT)

def parse_duration(time_str, time_regex=TIME_REGEX):
    parts = time_regex.fullmatch(time_str)
    if not parts:
        return
    grouped = parts.groupdict()
    print(grouped)
    time_params = {}
    for (name, param) in grouped.items():
        if param:
            time_params[name] = int(param)
    print(time_params)
    return timedelta(**time_params)


class DurationField(Field):
    widget = TextInput()

    def _value(self):
        if self.data is None:
            self.data = timedelta()
        days = self.data.days
        seconds = self.data.seconds
        
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return u'{days}d {hours}h {minutes}m {seconds}s'.format(
            days=days, hours=hours, minutes=minutes, seconds=seconds)


    def process_formdata(self, duration):
        self.data = parse_duration(duration[0])
