from discord.ext import commands
import logging
import os
import pandas as pd

from cogs.crawler import writeJSON

class PrairieLearnDashboard(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        @bot.event
        async def on_crawler_update(data: pd.DataFrame):
            logging.info("Updating dashboard")
            
            logging.info(data['assessment_access_rules'][0])
            data.to_json("data/data.json")
            data.to_html("data/data.html")
            # (data['assessment_access_rules']).to_html("data/aar.html")
            
            
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
