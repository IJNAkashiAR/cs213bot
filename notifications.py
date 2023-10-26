from assessment import Assessment


class Notification:

    def __init__(self, notif_channel_id: int, bot):
        self.notif_channel = self.bot.get_channel(notif_channel_id)

    def send_notification(self, assessments: dict[str, Assessment],
                          new_assessments: dict[str, Assessment]):
        print("hello from send notification")
