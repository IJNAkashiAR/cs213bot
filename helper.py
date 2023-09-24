import time
import datetime
import json

def convert_pl_time_to_unix_time(pl_time):
    '''Returns the unix time given a Prairielearn formatted time string.'''
    return time.mktime(time.strptime(pl_time + "00", "%Y-%m-%dT%H:%M:%S%z"))


def convert_unix_time_to_readable(unix_time):
    '''Returns a readable time string from unix time.'''
    return datetime.datetime.utcfromtimestamp(unix_time).strftime("%H:%M PST, %a, %b, %d", )

def parse_schedule_data(schedule_data):
    '''Takes the schedule data for an assessment and returns the periods for that assessment.'''
    periods = []
    for period in schedule_data:
        if period["mode"] != "Public":
            continue

        starting_time = period["start_date"]
        credit = period["credit"]
        end_time = period["end_date"]
        uids = period["uids"]
        now = time.time()

        if uids is not None:
            continue

        if credit is None or credit == 0:
            continue

        # We shouldn't add any periods before the start date
        if starting_time:
            start_unix = convert_pl_time_to_unix_time(starting_time)
            if start_unix > now:
                continue

        # We shouldn't add anything that's ended already
        if end_time:
            end_unix = convert_pl_time_to_unix_time(end_time)
            if now > end_unix:
                continue
        else:
            end_unix = 0
            
        periods.append({
            "credit": credit,
            "start_unix": start_unix,
            "end_unix": end_unix,
        })

    return periods


def pretty_print_json(data):
    print(json.dumps(data, indent=2)) 
