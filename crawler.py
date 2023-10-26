from discord.ext import tasks, commands
import discord
from assessment import Assessment
from prairiepy import PrairieLearn
from globals import PL_TOKEN
from typing import Callable, List


class PrairieLearnCrawler(commands.Cog):
    def __init__(self, bot, callbacks: List[Callable], course_id: int):
        self.bot = bot

        self.callbacks = callbacks

        self.crawler.start()
        self.current_assessments = {}
        self.prairielearn = PrairieLearn(PL_TOKEN,
                                         "https://ca.prairielearn.com/pl/api/v1")
        self._last_member = None

    def send_notification(self, assessment: Assessment) -> bool:
        pass

    def get_assessments_from_prairielearn(self,
                                          pl: PrairieLearn) -> dict[str, Assessment]:
        '''Download assessment data from Prairielearn.'''
        assessments_data = pl.get_pl_data("get_assessments", {
            "course_instance_id": self.course_id
        })

        results = {}

        for ass_data in assessments_data:
            id = ass_data["assessment_id"]
            ass_data["schedule_data"] = pl.get_pl_data("get_assessment_access_rules",
                                                       {
                                                           "course_instance_id": self.course_id,
                                                           "assessment_id": id
                                                       })
            results[id] = Assessment(ass_data)
        return results

    def check_new_assessments(assessments: Assessment, current_assessments: Assessment):
        pass

    def add_new_callback(self, callback: Callable):
        self.callbacks.append(callback)

    @tasks.loop(seconds=1.0)
    async def crawler(self):
        assessments = self.get_assessments_from_prairielearn(self.prairielearn)
        new_assessments = self.check_new_assessments(assessments,
                                                     self.current_assessments)

        for callback in self.callbacks:
            callback(assessments, new_assessments)

        # if new_assessments is not None:
        #     for new_ass in new_assessments:
        #         self.send_notification(new_ass)

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
