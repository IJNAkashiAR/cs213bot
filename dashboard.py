from assessment import Assessment


class Dashboard:
    async def __init__(self, dashboard_channel_id: int, bot):
        # Send a dummy message that will be replaced
        self.dashboard_channel = self.bot.get_channel(dashboard_channel_id)
        self.dashboard_message = await self.dashboard_channel.send("hello world")

    def update_dashboard(self, assessments: dict[str, Assessment],
                         new_assessments: dict[str, Assessment]):
        print("hello from update_dashboard")
        pass
