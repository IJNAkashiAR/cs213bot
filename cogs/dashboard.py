from datetime import datetime
from typing import Any, List, Optional
import discord
from discord.ext import commands
import logging
import os
import pandas as pd

from cogs.crawler import writeJSON

class PrairieLearnDashboard(commands.Cog):

    def format_assessments(self, data: pd.DataFrame) -> str:
        entries=""
        for idx, row in data.iterrows():
            credit = 0
            due_date = "None"
            if row['active_assessment'] is not None:
                logging.critical(row['active_assessment']['credit'])
                credit = row['active_assessment']['credit']
                due_date = row['active_assessment']['end_date']
            entries += f'''
            {row['assessment_label']}: **[{row['title']}](https://ca.prairielearn.com/pl/course_instance/{self.course_id}/assessment/{row['assessment_id']}/)**
            Credit: {credit}
            Due: {due_date}'''
        return entries

    def add_field(self, embed: discord.Embed, data: pd.DataFrame) -> None:
        # print(data)
        # print(data['assessment_set_heading'])
        # print(str(data['assessment_set_heading'].head(1)))
        heading_name = data['assessment_set_heading'].head(1).to_string(index=False)
        if 'not graded' in heading_name:
            return
        else:
            embed.add_field(name = f"\u200b\n***{heading_name}***",
                            value = self.format_assessments(data) + '\u200b',
                            inline = False)

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        dashboard_channel_id=os.getenv("DASHBOARD_CHANNEL")
        if dashboard_channel_id is None:
            raise Exception("Dashboard channel id not found")
        self.dashboard_channel: Any = self.bot.get_channel(int(dashboard_channel_id))
        self.message: Optional[discord.Message] = None
        self.course_id = os.getenv('COURSE_ID')
        
        @bot.event
        async def on_crawler_update(data: pd.DataFrame):
            # Await for the coroutine if there is no message yet
            if self.message is None:
                logging.info("Sending initial dashboard message")
                self.message = await self.dashboard_channel.send("hello world")

            logging.debug("Updating dashboard")
            time=datetime.now().strftime("%b %d, %H:%M:%S")
            embed=discord.Embed(title = f"Current Assessments on CPSC 213 PrairieLearn",
                                description = f"Updates every 30 minutes, last checked {time}", color = 0x8effc1)
            data.groupby("assessment_set_heading", group_keys=False).apply(lambda data: self.add_field(embed, data))
            embed.set_thumbnail(url = "https://cdn.discordapp.com/attachments/511797229913243649/803491233925169152/unknown.png")
            logging.critical(embed)
            await self.message.edit(embed=embed)
            # logging.info(data['assessment_access_rules'][0])
            # data.to_json("data/data.json")
            # data.to_html("data/data.html")
            data.to_html("data/aar.html")
            logging.debug("Finished updating dashboard")

            return 
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
        
    

async def setup(bot: commands.Bot):
    await bot.add_cog(PrairieLearnDashboard(bot))
