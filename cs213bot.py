import os
from pathlib import Path
import re
import time
import traceback
import logging
from os.path import isfile, join
import discord
from discord.ext import commands
from dotenv import load_dotenv
from util.badargs import BadArgs

# This file sets up the Discord bot and all of its extensions (the main way of adding functionality of the bot).

# Load the environment variables specified in .env
load_dotenv()
CS213BOT_KEY = os.getenv("CS213BOT_KEY")
if CS213BOT_KEY is None:
    logging.error("CS213BOT_KEY: Not found")
    exit(1)

bot = commands.Bot(command_prefix="!", help_command=None, intents=discord.Intents.all())

# Overload functions related to specific bot events.
# See https://discordpy.readthedocs.io/en/stable/api.html#discord.Client.event
@bot.event
async def on_ready() -> None:
    discord.utils.setup_logging(level=logging.DEBUG)

    # Load extensions in the cogs directory
    extensions=filter(lambda f: isfile(join("cogs", f)) and f != "__init__.py",
                      os.listdir("cogs"))
    for extension in extensions:
        try:
            await bot.load_extension(Path(f"cogs."+extension).stem)
        except Exception as e:
            logging.error(f"{extension} module could not be loaded. {e}")
            continue
        logging.info(f"{extension} module loaded")
    logging.info(f"Ready: {bot.user}")


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
        # log unknown error 
        logging.error(traceback.format_exception(etype, error, trace, 999))

@bot.event
async def on_message_edit(before, after):
    await bot.process_commands(after)

# TODO: Clean up this procedure
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

bot.run(CS213BOT_KEY)
