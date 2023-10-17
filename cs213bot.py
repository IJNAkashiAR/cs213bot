import asyncio
import json
import os
import random
import re
import requests
import time
import traceback
import sys
from assessment import Assessment
from schedule import Period
from dashboard import Dashboard

from collections import defaultdict
from datetime import datetime
from os.path import isfile, join
from helper import convert_pl_time_to_unix_time, convert_unix_time_to_readable, parse_schedule_data, pretty_print_json, writeJSON, readJSON

import discord
from discord.ext import commands

from util.badargs import BadArgs
from prairiepy import PrairieLearn, colormap
from globals import CS213BOT_KEY, PL_DASHBOARD_CHANNEL_ID, COURSE_ID, NOTIF_CHANNEL_ID, PL_TOKEN, SERVER_ID


bot = commands.Bot(command_prefix="!",
                   help_command=None,
                   intents=discord.Intents.all())

bot.pl_dict = defaultdict(list)
current_assessments = {}
bot.due_tomorrow = []
pl = PrairieLearn(PL_TOKEN,
                  api_server_url="https://ca.prairielearn.com/pl/api/v1")

for extension in filter(lambda f: isfile(join("cogs", f)) and f != "__init__.py", os.listdir("cogs")):
    bot.load_extension(f"cogs.{extension[:-3]}")
    print(f"{extension} module loaded")


def get_assignment_embed(title, entry):
    embed = discord.Embed(color=int("%x%x%x" % colormap[entry['color']], 16),
                          title=title,
                          description=f"[**{entry['label']}: {entry['name']}**](https://ca.prairielearn.com/pl/course_instance/{COURSE_ID}/assessment/{entry['id']}/)")
    embed.set_footer(text="CPSC 213 on PrairieLearn")
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/511797229913243649/803491233925169152/unknown.png")
    return embed


def get_assessments_from_prairielearn(pl: PrairieLearn) -> list[Assessment]:
    '''Download assessment data from Prairielearn.'''
    assessments_data = pl.get_pl_data("get_assessments", {
        "course_instance_id": COURSE_ID
    })

    results = {}

    for ass_data in assessments_data:
        ass_data["schedule_data"] = pl.get_pl_data("get_assessment_access_rules",
                                                   {
                                                       "course_instance_id": COURSE_ID,
                                                       "assessment_id": ass_data["assessment_id"]
                                                   })
        results[ass_data["assessment_id"]] = Assessment(**ass_data)
    return results


async def status_task():
    '''Starts a random status task.'''
    await bot.wait_until_ready()

    while not bot.is_closed():
        online_members = {member for guild in bot.guilds for member in guild.members if not member.bot and member.status != discord.Status.offline}

        play = ["with the \"help\" command",
                " ",
                "with your mind",
                "ƃuᴉʎɐlԀ", "...something?",
                "a game? Or am I?",
                "¯\\_(ツ)_/¯",
                f"with {len(online_members)} people",
                "with the Simple Machine"]

        listen = ["smart music",
                  "... wait I can't hear anything"]

        watch = ["TV",
                 "YouTube vids",
                 "over you",
                 "how to make a bot",
                 "C tutorials",
                 "sm213 execute",
                 "I, Robot"]

        rng = random.randrange(0, 3)

        if rng == 0:
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=random.choice(play)))
        elif rng == 1:
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=random.choice(listen)))
        else:
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=random.choice(watch)))

        await asyncio.sleep(1)


async def wipe_dms():
    guild = bot.get_guild(SERVER_ID)
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


def check_new_assessments(assessments: dict[str, Assessment],
                          cur_assessments: dict[str, Assessment]) -> list[Assessment]:
    '''Returns a list of new assessments'''
    pass


def send_notification(assessment):
    pass


async def crawl_prairielearn():
    '''Asynchronous function to get PrairieLearn data.'''
    # Get Notification channel
    channel = bot.get_channel(NOTIF_CHANNEL_ID)

    while True:
        try:
            # Get list of assignments
            assessments = get_assessments_from_prairielearn(pl)
            new_assessments = check_new_assessments(assessments, current_assessments)

            if new_assessments is not None:
                for new_ass in new_assessments:
                    send_notification(new_ass)

            current_assessments = assessments

            # for header in assessments:
            #     for entry in assessments[header]:
            #         # TODO: This code won't actually send a notification if a new due date is updated.

            #         # Send a message for new assessments
            #         if entry['id'] not in pl_dict:
            #             title = f"New {entry['type']}"
            #             sent=True

            #         found_idx = None
            #         # If ID already exists, check if a different period is now active
            #         for assessment_i in range(len(bot.pl_dict[header])):
            #             if bot.pl_dict[header][assessment_i]['id'] == entry['id']:
            #                 found_idx = assessment_i

            #         if found_idx is not None:
            #             # Check length
            #             if len(bot.pl_dict[header][found_idx]['modes']) != len(entry["modes"]):
            #                 title = f"{entry['type']} {entry['label']} updated, now"
            #             else:
            #                 continue

            #         for period in entry["modes"]:
            #             if period["credit"] == 100:
            #                 title += f" due at {convert_unix_time_to_readable(period['end_unix'])}"
            #                 break
            #         else:
            #             title += f" (No due date)"

            #         await channel.send(embed=get_assignment_embed(title, entry))

            #         # If there's less than a day left then send this message
            #         for period in entry["modes"]:
            #             if period["credit"] == 100 and (period["end_unix"] - time.time()) < 86400 and entry["id"] not in bot.due_tomorrow:
            #                 bot.due_tomorrow.append(entry["id"])
            #                 hourcount = round((period["end_unix"] - time.time()) / 3600, 2)

            #                 if hourcount < 0:
            #                     continue

            #                 title = f"{entry['type']} {entry['label']} due in < {hourcount} Hours\n({convert_unix_time_to_readable(period['end_unix'])})"
            #                 await channel.send(embed=get_assignment_embed(title, entry))
            #                 sent = True
            #                 break

            # if sent is True:
                # await channel.send(f"<@&{os.getenv('NOTIF_ROLE')}>")

            # Write the new dictionary to the bot dictionary
            bot.pl_dict = assessments
            writeJSON(dict(bot.pl_dict), "data/pl.json")
            # writeJSON(bot.due_tomorrow, "data/tomorrow.json")

            current_time = convert_unix_time_to_readable(time.time())

            embed = discord.Embed(title=f'{"Current Assessments on CPSC 213 PrairieLearn"}',
                                  description=f"Updates every 30 minutes, last checked {current_time}.\n\n This dashboard may not accurately reflect the actual due dates. Always check the **[Prairielearn website](https://ca.prairielearn.com/pl/course_instance/4486)**!",
                                  color=0x8effc1)

            for assessment_type in bot.pl_dict:
                entrylist = bot.pl_dict[assessment_type]
                formatted_entries = []
                for entry in entrylist:
                    skip = False
                    formatted = f"**[{entry['label']}: {entry['name']}](https://ca.prairielearn.com/pl/course_instance/{os.getenv('COURSE_ID')}/assessment/{entry['id']}/)**\nCredit:\n"
                    for period in entry["modes"]:
                        fmt = f"· {period['credit']}% until {convert_unix_time_to_readable(period['end_unix'])}\n"
                        formatted += fmt

                    formatted_entries.append(formatted)
                embed.add_field(name=f"\u200b\n***{assessment_type.upper()}***", value = "\n".join(formatted_entries) + '\u200b', inline = False)
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/511797229913243649/803491233925169152/unknown.png")

            await bot.pl_dashboard_message.edit(content=None, embed=embed)
            await asyncio.sleep(1800)

        except Exception as error:
            await channel.send(str(error))
            etype = type(error)
            trace = error.__traceback__
            print(("".join(traceback.format_exception(etype, error, trace, 999))).replace("home/rq2/.local/lib/python3.9/site-packages/", ""))
            await asyncio.sleep(60)


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
    # bot.due_tomorrow = readJSON("data/tomorrow.json")

    await bot.add_cog(Dashboard(bot, PL_DASHBOARD_CHANNEL_ID))
    await bot.add_cog(Dashboard(bot, PL_DASHBOARD_CHANNEL_ID))

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
