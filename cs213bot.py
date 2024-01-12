import asyncio
from collections.abc import Awaitable
import json
import os
from pathlib import Path
import random
import re
import time
import traceback
import sys
import logging

from collections import defaultdict
from datetime import datetime
from os.path import isfile, join

import discord
from discord.abc import GuildChannel
from discord.ext import commands
from discord.ext.commands.bot import logging
from bot_init import create_bot, setup_events, setup_loops
from dotenv import load_dotenv

from util.badargs import BadArgs
from prairiepy import PrairieLearn, colormap

load_dotenv()
CS213BOT_KEY = os.getenv("CS213BOT_KEY")
if CS213BOT_KEY is None:
    print("CS213BOT_KEY: Not found")
    exit(1)

bot = commands.Bot(command_prefix="!", help_command=None, intents=discord.Intents.all())

@bot.event
async def on_ready() -> None:
    if len(sys.argv) >= 2:
        chx = bot.get_channel(int(sys.argv[1]))
        sys.stderr = sys.stdout
        await chx.send(f"Ready: {bot.user}")
    else:
        print(f"Ready: {bot.user}")

    discord.utils.setup_logging()
    extensions=filter(lambda f: isfile(join("cogs", f)) and f != "__init__.py",
                      os.listdir("cogs"))

    # Load extensions in the cogs directory
    for extension in extensions:
        try:
            await bot.load_extension(Path(f"cogs."+extension).stem)
        except Exception as e:
            logging.error(f"{extension} module could not be loaded. {e}")
            continue
        logging.info(f"{extension} module loaded")


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



bot.pl_dict = defaultdict(list)
bot.due_tomorrow = []
bot.pl = PrairieLearn(os.getenv("PLTOKEN"), api_server_url = "https://ca.prairielearn.com/pl/api/v1")

bot.run(CS213BOT_KEY)

# @bot.event
# async def on_ready():
    
#     if "data" not in os.listdir():
#         os.mkdir("data")
#     if "pl.json" not in os.listdir("data"):
#         writeJSON({}, "data/pl.json")
#     if "tomorrow.json" not in os.listdir("data"):
#         writeJSON({}, "data/tomorrow.json")

#     bot.pl_dict = defaultdict(list, readJSON("data/pl.json"))
#     bot.due_tomorrow = readJSON("data/tomorrow.json")
#     bot.loop.create_task(status_task())
#     bot.loop.create_task(wipe_dms())
#     bot.loop.create_task(crawl_prairielearn())

# @bot.event
# async def on_message_edit(before, after):
#     await bot.process_commands(after)


# @bot.event
# async def on_message(message):
#     if isinstance(message.channel, discord.abc.PrivateChannel):
#         return
        
#     if not message.author.bot:
#         # debugging
#         # with open("messages.txt", "a") as f:
#         # 	print(f"{message.guild.name}: {message.channel.name}: {message.author.name}: \"{message.content}\" @ {str(datetime.datetime.now())} \r\n", file = f)
#         # print(message.content)

#         # this is some weird thing happening only with android users in certain servers and idk why it happens
#         # but basically the '@' is screwed up
#         if message.channel.id == 838103749690916902 and len(message.attachments):
#             await message.add_reaction("⬆️")
#         if re.findall(r"<<@&457618814058758146>&?\d{18}>", message.content):
#             new = message.content.replace("<@&457618814058758146>", "@")
#             await message.channel.send(new)

#         if message.content.lower() == "cancel":
#             bot.get_cog("SM213").queue.append([message.author.id, time.time()])

#         await bot.process_commands(message)
