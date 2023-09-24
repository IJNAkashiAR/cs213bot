import time
import datetime


def convert_pl_time_to_unix_time(pl_time):
    '''Returns the unix time given a Prairielearn formatted time string.'''
    return time.mktime(time.strptime(pl_time + "00", "%Y-%m-%dT%H:%M:%S%z"))


def convert_unix_time_to_readable(unix_time):
    '''Returns a readable time string from unix time.'''
    return datetime.datetime.utcfromtimestamp(unix_time).strftime("%H:%M PST, %a, %b, %d", )
