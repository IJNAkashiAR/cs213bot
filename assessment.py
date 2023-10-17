from schedule import Period


class Assessment():
    def __init__(self, data):
        self.type = data["type"]
        self.title = data["title"]
        self.id = data["assessment_id"]
        self.name = data["assessment_name"]
        self.label = data["assessment_label"]
        self.number = data["assessment_number"]
        self.set_id = data["assessment_set_id"]
        self.order_by = data["assessment_order_by"]
        self.set_name = data["assessment_set_name"]
        self.set_color = data["assessment_set_color"]
        self.set_number = data["assessment_set_number"]
        self.set_heading = data["assessment_set_heading"]
        self.set_abbreviation = data["assessment_set_abbreviation"]
        self.schedule_list = [Period(**i) for i in data["schedule_data"]]

    def __str__(self):
        string = ""
        for i in self.__dict__:
            if i != "schedule_list":
                string += i + " " + str(self.__dict__[i]) + "\n"

        string += "schedule_list: \n"
        for i in self.schedule_list:
            string += str(i) + "\n"
        return string

    def get_latest_period(self):
        for i in self.scheduleList:
            print(i)
