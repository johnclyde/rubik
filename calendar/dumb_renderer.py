class DumbRenderer(object):

    names_of_days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",     
    ]

    def render_week(self, week):
        print()
        print('time for another week')
        for d in week:
            dow = d.weekday()
            dow_name = self.names_of_days[dow]
            print("date is {date}".format(date=d))
            print("Day of week is {dow}.".format(dow=dow_name))
