import datetime


names_of_days = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",     
]



def render_week(week):
    print()
    print('time for another week')
    for d in week:
        dow = d.weekday()
        dow_name = names_of_days[dow]
        print("date is {date}".format(date=d))
        print("Day of week is {dow}.".format(dow=dow_name))


def main():
    startdate = datetime.date(2019, 8, 1)
    enddate = datetime.date(2020, 4, 30)
    week = []

    d = startdate
    while d <= enddate:
        dow = d.weekday()
        dow_name = names_of_days[dow]

        if dow_name == "Sunday":
            render_week(week)
            week = []

        week.append(d) 
        d = d + datetime.timedelta(1)

    render_week(week)

if __name__ == "__main__":
    main()
