# Shape of schedule_data looks like this
#
# mode
# uids
# credit
# end_date
# password
# exam_uuid
# seb_config
# start_date
# assessment_id
# time_limit_min
# assessment_name
# assessment_label
# assessment_title
# assessment_number
# show_closed_assessment
# assessment_access_rule_id
# assessment_set_abbreviation
# show_closed_assessment_score
# assessment_access_rule_number    


class Period:
    def __init__(self, mode, uids, credit, end_date, password, exam_uuid, seb_config, start_date, assessment_id, time_limit_min, assessment_name, assessment_label, assessment_title, assessment_number, show_closed_assessment, assessment_access_rule_id, assessment_set_abbreviation, show_closed_assessment_score, assessment_access_rule_number):
        self.mode = mode
        self.uids = uids
        self.credit = credit
        self.end_date = end_date
        self.password = password
        self.exam_uuid = exam_uuid
        self.seb_config = seb_config
        self.start_date = start_date
        self.assessment_id = assessment_id
        self.time_limit_min = time_limit_min
        self.assessment_name = assessment_name
        self.assessment_label = assessment_label
        self.assessment_title = assessment_title
        self.assessment_number = assessment_number
        self.show_closed_assessment = show_closed_assessment
        self.assessment_access_rule_id = assessment_access_rule_id
        self.assessment_set_abbreviation = assessment_set_abbreviation
        self.show_closed_assessment_score = show_closed_assessment_score
        self.assessment_access_rule_number = assessment_access_rule_number

    def __str__(self):
        string = ""
        for i in self.__dict__:
            string += i + " " + str(self.__dict__[i]) + "\n"
        return string
