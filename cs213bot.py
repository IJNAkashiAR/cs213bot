import asyncio
import json
import os
import random
import re
import requests
import time
import traceback
import sys

from collections import defaultdict
from datetime import datetime
from os.path import isfile, join
from helper import convert_pl_time_to_unix_time, convert_unix_time_to_readable

import discord
from discord.ext import commands
from dotenv import load_dotenv

from util.badargs import BadArgs
from prairiepy import PrairieLearn, colormap

load_dotenv()

# Environment variables
CS213BOT_KEY = os.getenv("CS213BOT_KEY")
PL_DASHBOARD_CHANNEL_ID = int(os.getenv("PL_DASHBOARD_CHANNEL"))
COURSE_ID = int(os.getenv("COURSE_ID"))
NOTIF_CHANNEL_ID = int(os.getenv("NOTIF_CHANNEL"))
PL_TOKEN = os.getenv("PLTOKEN")

bot = commands.Bot(command_prefix="!", help_command=None, intents=discord.Intents.all())
bot.pl_dict = defaultdict(list)
bot.due_tomorrow = []
bot.pl = PrairieLearn(PL_TOKEN, api_server_url= "https://ca.prairielearn.com/pl/api/v1")

for extension in filter(lambda f: isfile(join("cogs", f)) and f != "__init__.py", os.listdir("cogs")):
    bot.load_extension(f"cogs.{extension[:-3]}")
    print(f"{extension} module loaded")


def writeJSON(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


def readJSON(path):
    with open(path) as f:
        return json.load(f)


async def status_task():
    '''Starts a random status task.'''
    await bot.wait_until_ready()

    while not bot.is_closed():
        online_members = {member for guild in bot.guilds for member in guild.members if not member.bot and member.status != discord.Status.offline}

        play = ["with the \"help\" command", " ", "with your mind", "ƃuᴉʎɐlԀ", "...something?",
                "a game? Or am I?", "¯\_(ツ)_/¯", f"with {len(online_members)} people", "with the Simple Machine"]
        listen = ["smart music", "... wait I can't hear anything"]
        watch = ["TV", "YouTube vids", "over you",
                 "how to make a bot", "C tutorials", "sm213 execute", "I, Robot"]

        rng = random.randrange(0, 3)

        if rng == 0:
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=random.choice(play)))
        elif rng == 1:
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=random.choice(listen)))
        else:
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=random.choice(watch)))

        await asyncio.sleep(30)


async def wipe_dms():
    guild = bot.get_guild(int(os.getenv("SERVER_ID")))
    while True:
        await asyncio.sleep(300)
        bot.get_cog("SM213").queue = list(filter(lambda x: time.time() - x[1] < 300, bot.get_cog("SM213").queue))
        now = datetime.utcnow()
        for channel in filter(lambda c: c.name.startswith("213dm-"), guild.channels):
            async for msg in channel.history(limit=1):
                if (now - msg.created_at).total_seconds() >= 86400:
                    await next(i for i in guild.roles if i.name == channel.name).delete()
                    await channel.delete()
                    break
            else:
                await next(i for i in guild.roles if i.name == channel.name).delete()
                await channel.delete()

def get_local_assessments():
    ''''''
    names = []
    for header in bot.pl_dict:
        for entry in bot.pl_dict[header]:
            names.append(f"{entry['label']} {entry['name']}")
    return names

async def crawl_prairielearn():
    '''Asynchronous function to get PrairieLearn data.'''
    # Get Notification channel
    channel = bot.get_channel(NOTIF_CHANNEL_ID)

    while True:
        try:
            new_pl_dict = defaultdict(list)

            # Get list of assignments
            total_assignments = get_pl_data("get_assessments", {
                "course_instance_id": COURSE_ID
            })
            
            for assignment in total_assignments:
                assessment_id = assignment["assessment_id"]
                schedule_data = get_pl_data("get_assessment_access_rules",
                                            {
                                                "course_instance_id": COURSE_ID,
                                                "assessment_id": assessment_id
                                            })
                # print(json.dumps(schedule_data, indent=4))
                # exit(0)

                # The different time periods for how much available credit you can get
                periods = []

                not_started = False
                for period in schedule_data:
                    if period["uids"] is not None:
                        continue

                    starting_time = period["start_date"]
                    if starting_time and period["credit"] == 100:
                        start = convert_pl_time_to_unix_time(starting_time)
                        now = time.time()
                        if start > now:
                            not_started = True
                            continue

                    if not period["end_date"]:
                        end = None
                        end_unix = 0
                    else:
                        end_time = period["end_date"]
                        end_unix = convert_pl_time_to_unix_time(end_time)
                        end = convert_unix_time_to_readable(end_unix)

                    periods.append({
                        "credit": period["credit"],
                        "end":    end,
                        "end_unix": end_unix,
                        # "offset": timezone_offset
                    })

                if not_started:
                    continue

                field_data = {
                    "id": assessment_id,
                    "color": assignment["assessment_set_color"],
                    "label": assignment["assessment_label"],
                    "name":  assignment["title"],
                    "modes": periods
                }
                new_pl_dict[assignment["assessment_set_heading"]].append(field_data)

            seen_assessments = get_local_assessments()
            print(seen_assessments)
            sent = False

            # Sends available assignments
            for header in new_pl_dict:
                for entry in new_pl_dict[header]:
                    if entry not in bot.pl_dict[header]:
                        sent = True
                        print("entry label", entry['label'])
                        print("entry name", entry['name'])
                        
                        if f"{entry['label']} {entry['name']}" not in seen_assessments:
                            title = f"New {['Assignment', 'Quiz'][entry['label'].startswith('Q')]}"
                        else:
                            title = f"{['Assignment', 'Quiz'][entry['label'].startswith('Q')]} {entry['label']} Updated,"
                        for period in entry["modes"]:
                            if period["credit"] == 100 and period["end"]:
                                title += f" Due at {period['end']}"
                                break
                        else:
                            title += f" (No Due Date)"

                        embed = discord.Embed(color=int("%x%x%x" % colormap[entry["color"]], 16),
                                              title=title,
                                              description=f"[**{entry['label']}{entry['name']}**](https://ca.prairielearn.com/pl/course_instance/{COURSE_ID}/assessment/{entry['id']}/)")
                        embed.set_footer(text="CPSC 213 on PrairieLearn")
                        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/511797229913243649/803491233925169152/unknown.png")
                        await channel.send(embed=embed)

                    for period in entry["modes"]:
                        # If there's less than a day left then send this message
                        if period["credit"] == 100 and period["end"] and (period["end_unix"] - time.time()) < 86400 and entry["label"] + " " + entry["name"] not in bot.due_tomorrow:
                            print(bot.due_tomorrow)
                            bot.due_tomorrow.append(entry["label"]+" "+entry["name"])
                            hourcount = round(((period["end_unix"] + 60*period["offset"]) - time.time())/3600, 2)
                            if hourcount < 0:
                                continue
                            embed = discord.Embed(color=int("%x%x%x" % colormap[entry["color"]], 16),
                                                  title=f"{['Assignment', 'Quiz'][entry['label'].startswith('Q')]} {entry['label']} Due in < {hourcount} Hours\n({period['end']})",
                                                  description=f"[**{entry['label']} {entry['name']}**](https://ca.prairielearn.com/pl/course_instance/{os.getenv('COURSE_ID')}/assessment/{entry['id']}/)")
                            embed.set_footer(text="CPSC 213 on PrairieLearn")
                            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/511797229913243649/803491233925169152/unknown.png")
                            await channel.send(embed=embed)
                            sent = True
                            break

            #if sent:
                #await channel.send(f"<@&{os.getenv('NOTIF_ROLE')}>")

            bot.pl_dict = new_pl_dict
            writeJSON(dict(bot.pl_dict), "data/pl.json")
            writeJSON(bot.due_tomorrow, "data/tomorrow.json")

            current_time = datetime.utcfromtimestamp(time.time() - (7 * 60 * 60)).strftime('%Y-%m-%d %H:%M:%S')
            
            embed = discord.Embed(title=f'{"Current Assessments on CPSC 213 PrairieLearn"}',
                                  description=f'{"Updates every 30 minutes, last checked {current_time}"}',
                                  color=0x8effc1)

            # What channel is this?
            dashboard_channel = bot.get_channel(PL_DASHBOARD_CHANNEL_ID)

            for assigntype in bot.pl_dict:
                entrylist = bot.pl_dict[assigntype]
                formattedentries = []
                seenmodes = []
                for entry in entrylist:
                    skip = False
                    formatted = f"`{entry['label']}` **[{entry['name']}](https://ca.prairielearn.com/pl/course_instance/{os.getenv('COURSE_ID')}/assessment/{entry['id']}/)**\nCredit:\n"
                    for period in entry["modes"]:
                        if period['end'] and period['credit'] == 100:
                            timezone_offset = int(period["end"][-1])
                            now = time.time() - timezone_offset * 60
                            if period['end_unix'] < now:
                                skip = True
                                break

                        fmt = f"· {period['credit']}% until {period['end']}\n"
                        if fmt not in seenmodes:
                            formatted += fmt
                            seenmodes.append(fmt)

                    if skip: continue

                    formattedentries.append(formatted)
                embed.add_field(name = f"\u200b\n***{assigntype.upper()}***", value = "\n".join(formattedentries) + '\u200b', inline = False)
            
            embed.set_thumbnail(url = "https://cdn.discordapp.com/attachments/511797229913243649/803491233925169152/unknown.png")

            pl_dashboard_message = await dashboard_channel.send(embed=embed)
            # msg = await thechannel.fetch_message(pl_dashboard_message.id)

            # await msg.edit(embed = embed)
            await asyncio.sleep(1800)
        except Exception as error:
            await channel.send(str(error))
            etype = type(error)
            trace = error.__traceback__
            print(("".join(traceback.format_exception(etype, error, trace, 999))).replace("home/rq2/.local/lib/python3.9/site-packages/", ""))
            await asyncio.sleep(60)


def get_pl_data(method, options):
    # based on https://github.com/PrairieLearn/PrairieLearn/blob/master/tools/api_download.py
    
    start_time = time.time()
    retry_502_max = 30
    retry_502_i = 0
    while True:
        r = getattr(bot.pl, method)(options)
        if r.status_code == 200:
            break
        elif r.status_code == 502:
            retry_502_i += 1
            if retry_502_i >= retry_502_max:
                raise Exception(f'Maximum number of retries reached on 502 Bad Gateway Error')
            else:
                time.sleep(10)
                continue
        else:
            raise Exception(f'Invalid status returned: {r.status_code}')

    data = r.json()
    return data


@bot.event
async def on_ready():
    if len(sys.argv) >= 2:
        chx = bot.get_channel(int(sys.argv[1]))
        sys.stderr = sys.stdout
        await chx.send(f"Ready: {bot.user}")
    else:
        print(f"Ready: {bot.user}")
    if "data" not in os.listdir():
        os.mkdir("data")
    if "pl.json" not in os.listdir("data"):
        writeJSON({}, "data/pl.json")
    if "tomorrow.json" not in os.listdir("data"):
        writeJSON({}, "data/tomorrow.json")
    bot.pl_dict = defaultdict(list, readJSON("data/pl.json"))
    bot.due_tomorrow = readJSON("data/tomorrow.json")
    bot.loop.create_task(status_task())
    bot.loop.create_task(wipe_dms())
    bot.loop.create_task(crawl_prairielearn())


@bot.event
async def on_message_edit(before, after):
    await bot.process_commands(after)


@bot.event
async def on_message(message):
    if isinstance(message.channel, discord.abc.PrivateChannel):
        return
        
    if not message.author.bot:
        # debugging
        # with open("messages.txt", "a") as f:
        # 	print(f"{message.guild.name}: {message.channel.name}: {message.author.name}: \"{message.content}\" @ {str(datetime.datetime.now())} \r\n", file = f)
        # print(message.content)

        # this is some weird thing happening only with android users in certain servers and idk why it happens
        # but basically the '@' is screwed up
        if message.channel.id == 838103749690916902 and len(message.attachments):
            await message.add_reaction("⬆️")
        if re.findall(r"<<@&457618814058758146>&?\d{18}>", message.content):
            new = message.content.replace("<@&457618814058758146>", "@")
            await message.channel.send(new)

        if message.content.lower() == "cancel":
            bot.get_cog("SM213").queue.append([message.author.id, time.time()])

        await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound) or isinstance(error, discord.HTTPException) or isinstance(error, discord.NotFound) or isinstance(error, commands.errors.NotOwner):
        pass
    elif isinstance(error, BadArgs) or str(type(error)) == "<class 'cogs.meta.BadArgs'>":
        await error.print(ctx)
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"Oops! That command is on cooldown right now. Please wait **{round(error.retry_after, 3)}** seconds before trying again.", delete_after=error.retry_after)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"The required argument(s) {error.param} is/are missing.", delete_after=5)
    elif isinstance(error, commands.DisabledCommand):
        await ctx.send("This command is disabled.", delete_after=5)
    elif isinstance(error, commands.MissingPermissions) or isinstance(error, commands.BotMissingPermissions):
        await ctx.send(error, delete_after=5)
    else:
        etype = type(error)
        trace = error.__traceback__

        try:
            await ctx.send(("```python\n" + "".join(traceback.format_exception(etype, error, trace, 999)) + "```").replace("home/rq2/.local/lib/python3.9/site-packages/", ""))
        except Exception:
            print(("".join(traceback.format_exception(etype, error, trace, 999))).replace("home/rq2/.local/lib/python3.9/site-packages/", ""))


bot.run(CS213BOT_KEY)
