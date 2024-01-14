from datetime import datetime
import time
import os
from typing import Any, List, Optional, cast
from discord import DMChannel, Guild
from discord.ext import commands, tasks
from discord.ext.commands.bot import logging
from cogs.sm213 import SM213

class DMWiper(commands.Cog):
    '''Hidden Cog that wipes DMs periodically.'''

    def __init__(self, bot: commands.Bot, guild: Guild):
        self.bot = bot
        self.guild = guild
        self.wipe_dms.start()

    def get_cog(self) -> Optional[commands.Cog]:
        return self.bot.get_cog("SM213")

    @tasks.loop(minutes=5.0)
    async def wipe_dms(self):
        '''Clears old DMs'''
        if (sm213_cog:=self.get_cog()) is None:
            logging.warn(f"Could not get SM213 cog. This could happen if the DMWiper module is loaded before the SM213 module.")
            return

        # Bizarre incantation to satisfy the type-checker. isinstance(sm213_cog,SM213) fails every time
        sm213_cog=cast(SM213, sm213_cog)

        # Clear the old DMs from the queue
        sm213_cog.queue = list(filter(lambda x: time.time() - x[1] < 300,
                                 sm213_cog.queue))

        now = datetime.utcnow()
        for channel in filter(lambda c: c.name.startswith("213dm-"), self.guild.channels):
            if not isinstance(channel, DMChannel):
                raise RuntimeError(f"{channel} is not a DM")
            async for msg in channel.history(limit=1):
                if (now - msg.created_at).total_seconds() >= 86400:
                    await next(i for i in self.guild.roles if i.name == channel.name).delete()
                    await channel.delete()
                    break
            else:
                await next(i for i in self.guild.roles if i.name == channel.name).delete()
                await channel.delete()
        logging.debug("Cleared DMs")


async def setup(bot: commands.Bot):
    server_id = os.getenv("SERVER_ID")
    if server_id is None:
        raise Exception("SERVER_ID environment variable not found")
    
    guild = bot.get_guild(int(server_id))
    if guild is None:
        raise Exception("guild not found")

    await bot.add_cog(DMWiper(bot, guild))
