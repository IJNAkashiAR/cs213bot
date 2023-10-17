from discord.ext import tasks, commands
import discord
from assessment import Assessment
from prairiepy import PrairieLearn
from globals import COURSE_ID, PL_TOKEN


class PrairieLearnCrawler(commands.Cog):
    def __init__(self, bot, dashboard_channel_id: int, notif_channel_id: int, course_id: int):
        self.bot = bot

        # Send a dummy message that will be replaced
        dashboard_channel = self.bot.get_channel(dashboard_channel_id)
        self.dashboard_message = await dashboard_channel.send("hello world")

        self.notif_channel_id = notif_channel_id
        self.crawler.start()
        self.some_state = 0
        self.current_assessments = {}
        self.prairielearn = PrairieLearn(PL_TOKEN, api_server_url="https://ca.prairielearn.com/pl/api/v1")

        self._last_member = None

    def send_notification(self, assessment: Assessment) -> bool:
        pass

    def get_assessments_from_prairielearn(pl: PrairieLearn) -> dict[str, Assessment]:
        '''Download assessment data from Prairielearn.'''
        assessments_data = pl.get_pl_data("get_assessments", {
            "course_instance_id": COURSE_ID
        })

        results = {}

        for ass_data in assessments_data:
            id = ass_data["assessment_id"]
            ass_data["schedule_data"] = pl.get_pl_data("get_assessment_access_rules",
                                                       {
                                                           "course_instance_id": COURSE_ID,
                                                           "assessment_id": id
                                                       })
            results[id] = Assessment(ass_data)
        return results

    @tasks.loop(seconds=1.0)
    async def crawler(self):
        assessments = self.get_assessments_from_prairielearn(self.prairielearn)
        new_assessments = self.check_new_assessments(assessments, current_assessments)

        if new_assessments is not None:
            for new_ass in new_assessments:
                self.send_notification(new_ass)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = member.guild.system_channel
        if channel is not None:
            await channel.send(f'Welcome {member.mention}.')

    @commands.command()
    async def hello(self, ctx, *, member: discord.Member = None):
        """Says hello"""
        member = member or ctx.author
        if self._last_member is None or self._last_member.id != member.id:
            await ctx.send(f'Hello {member.name}~')
        else:
            await ctx.send(f'Hello {member.name}... This feels familiar.')
        self._last_member = member
