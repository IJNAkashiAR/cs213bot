from collections import defaultdict
from datetime import datetime, timezone
import time
import json
import os
import traceback
from typing import Any, Optional
from discord.ext import commands, tasks
import logging

from prairiepy import colormap
import pandas as pd
from prairiepy import PrairieLearn

def writeJSON(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent = 4)

def readJSON(path):
    with open(path) as f:
        return json.load(f)


def get_latest_active_access(access_rules: pd.DataFrame) -> Optional[pd.Series]:
    '''Get the latest active access rule if it exists, otherwise return None.'''

    # The typechecker must be satisfied.
    latest:Any=None

    for index, row in access_rules.iterrows():
        if row['start_date'] is None:
            continue

        start_date = datetime.strptime(row['start_date']+"00", "%Y-%m-%dT%H:%M:%S%z")
        # now() is not timezone aware
        current_time = datetime.now(timezone.utc)
        if start_date > current_time:
            continue

        # Skip any 0 credit assignments as those are probably past their due date and are not active.
        # if row['credit'] == 0:
            # continue
        
        if latest is None or latest['start_datetime'] < start_date:
            latest = row
            # Add a start_datetime column to the row, makes it convenient to compare times
            latest['start_datetime']=start_date
            continue
        
    return latest


def get_active_assessments(data: pd.DataFrame) -> pd.DataFrame:
    '''Return a new DataFrame an active_assessment column. Active assessments are any assessments that have an active period with a non-zero credit. If there are no active assessments, then the entry will be None.'''

    # Filter for graded assessments
    graded_filter=data['assessment_set_heading'].map(lambda hdng: 'not graded' not in hdng)
    graded = data.loc[graded_filter]
    data['active_assessment'] = graded['assessment_access_rules'].map(get_latest_active_access)
    data.loc[~graded_filter, 'active_assessment'] = None

    return data


class Crawler(commands.Cog):
    '''Crawler for PrairieLearn data. Stores persistent data in the data directory.'''

    def __init__(self, bot: commands.Bot, prl: PrairieLearn):
        self.bot = bot
        self.prl = prl

        if (cid_str := os.getenv("COURSE_ID")) is None:
            raise Exception("Could not get COURSE_ID environment variable")

        self.CID = int(cid_str)

        self.crawl_prairielearn.start()

    def get_pl_data(self, method, options) -> tuple[Any, Optional[float]]:
        '''Returns Prairielearn data. '''
        # based on https://github.com/PrairieLearn/PrairieLearn/blob/master/tools/api_download.py

        start_time = time.time()
        retry_502_max = 30
        retry_502_i = 0
        while True:
            r = getattr(self.prl, method)(options)
            if r.status_code == 200:
                break
            elif r.status_code == 502:
                retry_502_i += 1
                if retry_502_i >= retry_502_max:
                    logging.critical('Maximum number of retries reached on 502 Bad Gateway Error, retrying later')
                    return None, None
                else:
                    logging.warn('502 Bad Gateway Error returned, retrying in 10 seconds...')
                    time.sleep(10)
                    continue
            else:
                logging.critical(f'Invalid status returned: {r.status_code}, retrying later')
                return None, None

        data = r.json()
        return data, start_time

    def get_local_assessments(self):
        names = []
        for header in self.bot.pl_dict:
            for entry in self.bot.pl_dict[header]:
                names.append(f"{entry['label']} {entry['name']}")
        return names


    def notify(self, data: pd.DataFrame, time: float):
        self.bot.dispatch("crawler_update", data)


    @tasks.loop(seconds=100.0)
    async def crawl_prairielearn(self):
        '''Gets new data from the Prairielearn API and parses it. Then sends the data to subscribed functions.

        Any functions that to subscribe to the data should be named "on_crawler_update" and have the decorator @bot.event. 
        
        Based off of https://stackoverflow.com/questions/64810905/how-do-i-emit-custom-discord-py-events'''

        logging.debug("Crawling PrairieLearn...")

        data, time = self.get_pl_data("get_assessments", {"course_instance_id": self.CID})
        if data is None or time is None:
            return

        data_frame = pd.json_normalize(data)

        def get_access_rules(aid: int):
            data,time=self.get_pl_data("get_assessment_access_rules", {
                "course_instance_id": self.CID,
                "assessment_id": aid
            })
            if data is None:
                return None
            else:
                return pd.json_normalize(data)

        data_frame['assessment_access_rules'] = data_frame['assessment_id'].map(get_access_rules)
        data_frame = get_active_assessments(data_frame)

        self.notify(data_frame, time)

        logging.debug("Crawling finished.")
        return 
        
        channel = self.bot.get_channel(int(os.getenv("NOTIF_CHANNEL")))
        try: 
            new_pl_dict = defaultdict(list)
            total_assignments = self.get_pl_data("get_assessments", {"course_instance_id": int(os.getenv("COURSE_ID"))})
            for assignment in total_assignments:
                assessment_id = assignment["assessment_id"]
                schedule_data = self.get_pl_data("get_assessment_access_rules", {"course_instance_id": int(os.getenv("COURSE_ID")), "assessment_id": assessment_id})
                modes = []
                not_started = False
                for mode in schedule_data:
                    if mode["uids"] != None: continue
                    if mode["start_date"]:
                        offset = int(mode["start_date"][-1])
                    else:
                        offset = 0

                    if mode["start_date"] and mode["credit"] == 100:
                        start = time.mktime(time.strptime("-".join(mode["start_date"].split("-")[:-1]), "%Y-%m-%dT%H:%M:%S"))
                        now = time.time() - offset * 60
                        if start > now: 
                            not_started = True
                            break

                    if not mode["end_date"]: 
                        end = None
                        end_unix = 0
                    else: 
                        end_unix = time.strptime("-".join(mode["end_date"].split("-")[:-1]), "%Y-%m-%dT%H:%M:%S")
                        end = time.strftime("%H:%M PST, %a, %b, %d", end_unix)
                        end_unix = time.mktime(end_unix)

                    modes.append({
                        "credit": mode["credit"],
                        "end":    end,
                        "end_unix": end_unix,
                        "offset": offset
                    })

                if not_started:
                    continue

                fielddata = {
                    "id": assessment_id,
                    "color": assignment["assessment_set_color"], 
                    "label": assignment["assessment_label"],
                    "name":  assignment["title"],
                    "modes": modes
                }
                new_pl_dict[assignment["assessment_set_heading"]].append(fielddata)

            seen_assessments = self.get_local_assessments()
            sent = False
            for header in new_pl_dict:
                for entry in new_pl_dict[header]:
                    if entry not in self.bot.pl_dict[header]:
                        sent = True
                        if f"{entry['label']} {entry['name']}" not in seen_assessments:
                            title = f"New {['Assignment', 'Quiz'][entry['label'].startswith('Q')]}"
                        else:
                            title = f"{['Assignment', 'Quiz'][entry['label'].startswith('Q')]} {entry['label']} Updated,"
                        for mode in entry["modes"]:
                            if mode["credit"] == 100 and mode["end"]:
                                title += f" Due at {mode['end']}"
                                break
                        else:
                            title += f" (No Due Date)"

                        embed = discord.Embed(color = int("%x%x%x" % colormap[entry["color"]], 16), title = title, description = f"[**{entry['label']} {entry['name']}**](https://ca.prairielearn.com/pl/course_instance/{os.getenv('COURSE_ID')}/assessment/{entry['id']}/)")
                        embed.set_footer(text = "CPSC 213 on PrairieLearn")
                        embed.set_thumbnail(url = "https://cdn.discordapp.com/attachments/511797229913243649/803491233925169152/unknown.png")
                        # await channel.send(embed = embed)

                    for mode in entry["modes"]:
                        if mode["credit"] == 100 and mode["end"] and (mode["end_unix"] + 60*mode["offset"]) - time.time() < 86400 and entry["label"] + " " + entry["name"] not in bot.due_tomorrow:
                            # bot.due_tomorrow.append(entry["label"]+" "+entry["name"])
                            hourcount = round(((mode["end_unix"] + 60*mode["offset"]) - time.time())/3600, 2)
                            if hourcount < 0: continue
                            embed = discord.Embed(color = int("%x%x%x" % colormap[entry["color"]], 16), title = f"{['Assignment', 'Quiz'][entry['label'].startswith('Q')]} {entry['label']} Due in < {hourcount} Hours\n({mode['end']})", description = f"[**{entry['label']} {entry['name']}**](https://ca.prairielearn.com/pl/course_instance/{os.getenv('COURSE_ID')}/assessment/{entry['id']}/)")
                            embed.set_footer(text = "CPSC 213 on PrairieLearn")
                            embed.set_thumbnail(url = "https://cdn.discordapp.com/attachments/511797229913243649/803491233925169152/unknown.png")
                            # await channel.send(embed = embed)
                            sent = True
                            break

            #if sent:
                #await channel.send(f"<@&{os.getenv('NOTIF_ROLE')}>")

            self.bot.pl_dict = new_pl_dict
            writeJSON(dict(self.bot.pl_dict), "data/pl.json")
            writeJSON(self.bot.due_tomorrow, "data/tomorrow.json")
            thetime = datetime.utcfromtimestamp(time.time() - (7 * 60 * 60)).strftime('%Y-%m-%d %H:%M:%S')
            embed = discord.Embed(title = f"Current Assessments on CPSC 213 PrairieLearn", description = f"Updates every 30 minutes, last checked {thetime}", color = 0x8effc1)
            thechannel = self.bot.get_channel(884874356654735413)
            for assigntype in self.bot.pl_dict:
                entrylist = self.bot.pl_dict[assigntype]
                formattedentries = []
                seenmodes = []
                for entry in entrylist:
                    skip = False
                    formatted = f"`{entry['label']}` **[{entry['name']}](https://ca.prairielearn.com/pl/course_instance/{os.getenv('COURSE_ID')}/assessment/{entry['id']}/)**\nCredit:\n"
                    for mode in entry["modes"]:
                        if mode['end'] and mode['credit'] == 100:
                            offset = int(mode["end"][-1])
                            now = time.time() - offset * 60
                            if mode['end_unix'] < now:
                                skip = True
                                break

                        fmt = f"· {mode['credit']}% until {mode['end']}\n"
                        if fmt not in seenmodes:
                            formatted += fmt
                            seenmodes.append(fmt)

                    if skip: continue

                    formattedentries.append(formatted)
                embed.add_field(name = f"\u200b\n***{assigntype.upper()}***", value = "\n".join(formattedentries) + '\u200b', inline = False)

            embed.set_thumbnail(url = "https://cdn.discordapp.com/attachments/511797229913243649/803491233925169152/unknown.png")
            # msg = await thechannel.fetch_message(886048835183460384)
            # await msg.edit(embed = embed)
            await asyncio.sleep(1800)
        except Exception as error:
            await channel.send(str(error))
            etype = type(error)
            trace = error.__traceback__
            print(("".join(traceback.format_exception(etype, error, trace, 999))).replace("home/rq2/.local/lib/python3.9/site-packages/", ""))
            await asyncio.sleep(60)



async def setup(bot: commands.Bot):
    prl = PrairieLearn(os.getenv("PLTOKEN"),
                       api_server_url = "https://ca.prairielearn.com/pl/api/v1")
    await bot.add_cog(Crawler(bot,prl))
