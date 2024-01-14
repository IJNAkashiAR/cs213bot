from collections import defaultdict
from discord.ext import commands
import logging
import os
import json

import pandas as pd

def writeJSON(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent = 4)

def readJSON(path):
    with open(path) as f:
        return json.load(f)

class PrairieLearnNotifications(commands.Cog):
    '''Cog to store related functionality for the Prairielearn notifications system.'''

    def __init__(self, bot: commands.Bot):
        
        # Initialize persistent data storage
        if "data" not in os.listdir():
            logging.info("data directory not found. Creating new file for persistent data...")
            os.mkdir("data")
        if "pl.json" not in os.listdir("data"):
            logging.info("pl.json not found. Creating new file for persistent data...")
            writeJSON({}, "data/pl.json")
        if "tomorrow.json" not in os.listdir("data"):
            logging.info("tomorrow.json not found. Creating new file for persistent data...")
            writeJSON({}, "data/tomorrow.json")

        self.due_tomorrow = readJSON("data/tomorrow.json")
        self.pl_dict = defaultdict(list, readJSON("data/pl.json"))
        env_var = os.getenv("NOTIF_CHANNEL")
        if env_var is None:
            logging.critical("Could not find notification channel environment variable. Unloading notifications cog...")
            return
        self.notif_channel_id = int(env_var)

        
        @bot.event
        async def on_crawler_update(data: pd.DataFrame):
            pass
