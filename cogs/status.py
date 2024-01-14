import logging
import random
import discord
from discord.ext import commands, tasks

class Status(commands.Cog, command_attrs=dict(hidden=True)):
    '''Hidden Cog that manages the status changing functionality.'''

    bot: commands.Bot

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.status_change.start()

    @tasks.loop(seconds = 60.0)
    async def status_change(self):
        await self.bot.wait_until_ready()

        online_members=0
        for guild in self.bot.guilds:
            for member in guild.members:
                if not member.bot and member.status != discord.Status.offline:
                    online_members += 1

        activities = {
            discord.ActivityType.playing: ["with the \"!help\" command", " ", "with your mind",
                                           "ƃuᴉʎɐlԀ", "...something?", "a game? Or am I?", "¯\_(ツ)_/¯",
                                           f"with {online_members} people", "with the Simple Machine"],
            discord.ActivityType.listening: ["smart music", "... wait I can't hear anything"],
            discord.ActivityType.watching: ["TV", "YouTube vids", "over you", "how to make a bot",
                                            "C tutorials", "sm213 execute", "I, Robot"]
        }

        activity_type = random.choice(list(activities.keys()))
        await self.bot.change_presence(activity=discord.Activity(type=activity_type,
                                                                 name=random.choice(activities[activity_type])))
        logging.debug(f"Changed status. type: {activity_type}, name: {random.choice(activities[activity_type])}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Status(bot))
